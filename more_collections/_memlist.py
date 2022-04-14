from __future__ import annotations
import collections.abc
import pickle
import sys
from itertools import chain, islice
from pathlib import Path
from typing import Any, ClassVar, Generic, Optional, TypeVar, Union, overload

if sys.version_info < (3, 9):
    from typing import Iterable, Iterator, MutableSequence, List as list, Set as set
else:
    from collections.abc import Iterable, Iterator, MutableSequence

__all__ = ["MemList"]

T = TypeVar("T")

reprs_seen: set[int] = {*()}

CHUNKSIZE: int = 1 << 16

FOLDER = Path.home() / "_more_collections"
FOLDER.mkdir(exist_ok=True)
FOLDER /= "_mem_list"
FOLDER.mkdir(exist_ok=True)


class MemList(MutableSequence[T], Generic[T]):
    _cache: Optional[list[T]]
    _fenwick: Optional[list[int]]
    _file: Optional[str]
    _filenames: list[str]
    _len: int
    _lens: list[int]
    _uid_counter: ClassVar[int] = 0

    __slots__ = {
        "_cache":
            "Cache the contents of a file.",
        "_fenwick":
            "The length of each individual segment is stored"
            " via a Fenwick tree when needed. `None` while"
            " indexing is not needed or if the Fenwick tree"
            " needs to be reconstructed.",
        "_file":
            "The currently cached file.",
        "_filenames":
            "The file names for each segment.",
        "_len":
            "The total length is maintained as an attribute.",
        "_lens":
            "The length of each file's list is tracked so that"
            " the file does not need to be read for indexing.",
    }

    @classmethod
    def _get_filename(cls: Type[MemList[Any]], /) -> str:
        cls._uid_counter += 1
        return f"{cls._uid_counter}.txt"

    def __init__(self: MemList[T], iterable: Optional[Iterable[T]] = None, /) -> None:
        if iterable is not None and not isinstance(iterable, Iterable):
            raise TypeError(f"{type(self).__name__} expected an iterable, got {iterable!r}")
        self._cache = None
        self._fenwick = None
        self._file = None
        self._filenames = []
        self._lens = []
        cls = type(self)
        if iterable is not None:
            iterator = iter(iterable)
            for chunk in iter(lambda: [*islice(iterator, CHUNKSIZE)], []):
                self._filenames.append(cls._get_filename())
                with open(FOLDER / self._filenames[-1], mode="wb") as file:
                    pickle.dump(chunk, file)
                self._lens.append(len(chunk))
        if len(self._lens) == 0:
            self._len = 0
        else:
            self._len = CHUNKSIZE * (len(self._lens) - 1) + self._lens[-1]

    def __del__(self: MemList[Any], /) -> None:
        self.clear()

    def __delitem__(self: MemList[T], index: Union[int, slice], /) -> None:
        if isinstance(index, slice):
            len_ = self._len
            range_ = range(len_)[index]
            size = len(range_)
            if range_.step < 0:
                range_ = range_[::-1]
            if self._len == size:
                self.clear()
                return
            elif range_.step == 1 and range_.start == 0:
                for i in range(len(self._lens)):
                    if size < self._lens[i]:
                        break
                    else:
                        size -= self._lens[i]
                        self._del_chunk(i)
                if size == 0:
                    pass
                elif self._file == self._filenames[0]:
                    del self._cache[:size]
                    if len(self._lens) > 1 and len(self._cache) < CHUNKSIZE // 2:
                        self._cache.extend(self._pop_chunk(1))
                elif len(self._lens) == 1 or self._lens[0] - size > CHUNKSIZE // 2:
                    del self._cache_chunk(0)[:size]
                else:
                    data = self._pop_chunk(1)[:-size]
                    self._cache_chunk(0).extend(data)
                self._lens[0] = len(self._cache)
            elif range_.step == 1 and range_.stop == self._len:
                for i in reversed(range(len(self._lens))):
                    if size < self._lens[i]:
                        break
                    else:
                        size -= self._lens[i]
                        self._del_chunk(i)
                if size == 0:
                    pass
                elif self._file == self._filenames[-1]:
                    del self._cache[-size:]
                    if len(self._lens) > 1 and len(self._cache) < CHUNKSIZE // 2:
                        cache = self._cache
                        self._cache_chunk(-2).extend(cache)
                        self._del_chunk(-1)
                elif len(self._lens) == 1 or self._lens[-1] - size > CHUNKSIZE // 2:
                    del self._cache_chunk(-1)[-size:]
                else:
                    data = self._pop_chunk(-1)[:-size]
                    self._cache_chunk(-2).extend(data)
                self._lens[-1] = len(self._cache)
            else:
                for i in reversed(range_):
                    del self[i]
                return
            self._fenwick = None
            self._len = len_ - len(range_)
        try:
            index = range(self._len)[index]
        except TypeError:
            raise TypeError(f"indices must be integers or slices, not {type(index).__name__}") from None
        except IndexError:
            raise IndexError("index out of range") from None
        if index < self._lens[0]:
            if self._lens[0] == 1:
                self._del_chunk(0)
                return
            del self._cache_chunk(0)[index]
            self._fenwick_update(0, -1)
            if len(self._lens) > 1 and len(self._cache) < CHUNKSIZE // 2:
                self._cache.extend(self._pop_chunk(1))
            self._lens[0] = len(self._cache)
            return
        elif index >= self._len - self._lens[-1]:
            if self._lens[-1] == 1:
                self._del_chunk(-1)
                return
            del self._cache_chunk(-1)[index - self._len + self._lens[-1]]
            self._fenwick_update(-1, -1)
            return
        i, j = self._fenwick_index(index)
        if self._lens > CHUNKSIZE // 2:
            del self._cache_chunk(i)[j]
            self._update_fenwick(i, -1)
            self._lens[i] = len(self._cache)
        elif self._lens[i - 1] < self._lens[i + 1]:
            cache = self._pop_chunk(i)
            self._cache_chunk(i - 1).extend(cache)
            self._lens[i - 1] = len(self._cache)
        else:
            cache = self._pop_chunk(i + 1)
            self._cache_chunk(i).extend(cache)
            self._lens[i] = len(self._cache)
        self._len -= 1

    @overload
    def __getitem__(self: MemList[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: MemList[T], index: slice, /) -> MemList[T]:
        ...

    def __getitem__(self, index, /):
        if isinstance(index, slice):
            range_ = range(self._len)[index]
            # Empty slice.
            if len(range_) == 0:
                return type(self)()
            # Entire slice.
            elif len(range_) == self._len:
                return self.copy() if range_.step > 0 else type(self)(reversed(self))
            # Start from the beginning.
            elif range_.step == 1 and range_.start == 0:
                return type(self)(islice(self, range_.stop))
            # Start from the end and reverse it.
            elif range_.step == 1 and range_.stop == self._len:
                i, j = self._fenwick_index(range_.start)
                return type(self)(chain.from_iterable(chain(
                    islice(self._cache_chunk(i), j, None),
                    (self._cache_chunk(k) for k in range(i + 1, len(self._lens))),
                )))
            # Start from the end.
            elif range_.step == -1 and range_.start == self._len - 1:
                return type(self)(islice(reversed(self), len(range_)))
            # Start from the beginning and reverse it.
            elif range_.step == -1 and range_.stop == -1:
                i, j = self._fenwick_index(range_.start)
                return type(self)(chain.from_iterable(chain(
                    self._cache_chunk(i)[j::-1],
                    (reversed(self._cache_chunk(k)) for k in reversed(range(i))),
                )))
            # Use random access indexing if it's small.
            elif self._len > 16 * len(range_):
                return type(self)(self[i] for i in range_)
            # Loop forward and check if the index matches if it's a lot.
            elif range_.step > 0:
                return type(self)(x for i, x in enumerate(self) if i in range_)
            else:
                return type(self)(x for i, x in enumerate(reversed(self), 1 - self._len) if -i in range_)
        try:
            index = range(self._len)[index]
        except TypeError:
            raise TypeError(f"indices must be integers or slices, not {type(index).__name__}") from None
        except IndexError:
            raise IndexError("index out of range") from None
        if index < self._lens[0]:
            return self._cache_chunk(0)[index]
        elif index >= self._len - self._lens[-1]:
            return self._cache_chunk(-1)[index - self._len + self._lens[-1]]
        else:
            i, j = self._fenwick_index()
            return self._cache_chunk(i)[j]

    def __iter__(self: MemList[T], /) -> Iterator[T]:
        return chain.from_iterable(
            self._cache_chunk(i)
            for i, _ in enumerate(self._lens)
        )

    def __len__(self: MemList[Any], /) -> int:
        return self._len

    def __reversed__(self: MemList[T], /) -> Iterator[T]:
        return chain.from_iterable(
            reversed(self._cache_chunk(-i))
            for i, _ in enumerate(self._lens, 1)
        )

    @overload
    def __setitem__(self: MemList[T], index: int, value: T, /) -> None:
        ...

    @overload
    def __setitem__(self: MemList[T], index: slice, value: Iterable[T], /) -> None:
        ...

    def __setitem__(self, index, value, /):
        if isinstance(index, slice):
            raise NotImplementedError("Seglists currently do not support slice assignments")
        try:
            index = range(self._len)[index]
        except TypeError:
            raise TypeError(f"indices must be integers or slices, not {type(index).__name__}") from None
        except IndexError:
            raise IndexError("index out of range") from None
        if index < self._lens[0]:
            self._cache_chunk(0)[index] = value
        elif index >= self._len - self._lens[-1]:
            self._cache_chunk(-1)[index - self._len + self._lens[-1]] = value
        else:
            i, j = self._fenwick_index(index)
            self._cache_chunk(i)[j] = value

    def __str__(self: MemList[Any], /) -> str:
        return f"{type(self).__name__}(...)"

    def _cache_chunk(self: MemList[T], index: int, /) -> list[T]:
        if self._file != self._filenames[index]:
            self._commit_chunk()
            self._cache = self._load_chunk(index)
            self._file = self._filenames[index]
        return self._cache

    def _commit_chunk(self: MemList[Any], /) -> None:
        if self._file is not None:
            with open(FOLDER / self._file, mode="wb") as file:
                pickle.dump(self._cache, file)

    def _del_chunk(self: MemList[Any], index: int, /) -> None:
        index = range(len(self._filenames))[index]
        (FOLDER / self._filenames[index]).unlink()
        if self._file == self._filenames.pop(index):
            self._cache = None
            self._file = None
        self._lens -= self._lens.pop(index)
        if self._fenwick is None:
            pass
        elif index == len(self._filenames):
            del self._fenwick[-1]
        else:
            self._fenwick = None

    def _fenwick_index(self: MemList[Any], index: int, /) -> tuple[int, int]:
        if self._fenwick is None:
            self._fenwick = self._lens.copy()
            self._fenwick.insert(0, 0)
            fenwick_len = len(self._fenwick)
            for i in range(1, fenwick_len):
                j = i + (i & -i)
                if j < fenwick_len:
                    self._fenwick[j] += self._fenwick[i]
            self._fenwick = self._fenwick
        else:
            fenwick_len = len(self._fenwick)
        i = 0
        j = 2048
        while j < fenwick_len:
            j *= 2
        while j > 0:
            if i + j < fenwick_len and self._fenwick[i + j] <= index:
                i += j
                index -= self._fenwick[i]
            j //= 2
        return i, index

    def _fenwick_update(self: MemList[Any], index: int, value: int, /) -> None:
        index = range(self._len)[index] + 1
        self._len += value
        if self._fenwick is None:
            return
        elif index & (index - 1) == 0:
            fenwick_len = len(self._fenwick)
            while index < fenwick_len:
                self._fenwick[index] += value
                index *= 2
        else:
            fenwick_len = len(self._fenwick)
            while index < fenwick_len:
                self._fenwick[index] += value
                index += index & -index

    def _load_chunk(self: MemList[T], index: int, /) -> list[T]:
        if self._file == self._filenames[index]:
            return self._cache
        with open(FOLDER / self._filenames[index], mode="rb") as file:
            return pickle.load(file)

    def _pop_chunk(self: MemList[T], index: int, /) -> list[T]:
        data = self._load_chunk(index)
        self._del_chunk(index)
        return data

    def clear(self: MemList[Any], /) -> None:
        for filename in self._filenames:
            (FOLDER / filename).unlink()
        self._cache = None
        self._fenwick = None
        self._file = None
        self._filenames.clear()
        self._len = 0
        self._lens.clear()

    def insert(self: MemList[T], index: int, value: T, /) -> None:
        if not isinstance(index, SupportsIndex):
            raise TypeError(f"index could not be interpreted as an integer, got {index!r}")
        index = operator.index(index)
        if self._len == 0:
            self._cache = [value]
            self._fenwick = None
            self._file = type(self)._get_filename()
            self._filenames.append(self._file)
            self._len = 1
            self._lens.append(1)
            self._commit_chunk()
            return
        elif index < 0:
            index += self._len
        if index <= self._lens[0]:
            if self._lens[0] > 2 * CHUNKSIZE:
                self._fenwick = None
                self._filenames.insert(1, type(self)._get_filename())
                data = self._cache_chunk(0)[self._lens[0] // 2:]
                del self._cache[self._lens[0] // 2:]
                if index <= self._lens[0] // 2:
                    self._cache.insert(index, value)
                else:
                    data.insert(index - self._lens[0] // 2, value)
                self._lens[0] = len(self._cache)
                self._lens.insert(1, len(data))
                self._commit_chunk()
                self._cache = data
                self._file = self._filenames[1]
            else:
                self._cache_chunk(0).insert(index, value)
                self._fenwick_update(0, 1)
        elif index >= self._len - self._lens[-1]:
            index += self._lens[-1] - self._len
            if self._lens[-1] > 2 * CHUNKSIZE:
                self._fenwick_update(-1, self._lens[-1] // 2 - self._lens[-1])
                self._filenames.append(type(self)._get_filename())
                data = self._cache_chunk(-1)[self._lens[-1] // 2:]
                del self._cache[self._lens[-1] // 2:]
                if index <= self._lens[-1] // 2:
                    self._cache.insert(index, value)
                else:
                    data.insert(index - self._lens[-1] // 2, value)
                self._lens[-1] = len(self._cache)
                self._lens.append(len(data))
                self._commit_chunk()
                self._cache = data
                self._file = self._filenames[-1]
                if self._fenwick is not None:
                    i = len(self._fenwick)
                    j = i & -i
                    self._fenwick.append(len(data))
                    self._fenwick[-2] -= self._fenwick[-1]
                    while j > 1:
                        j //= 2
                        self._fenwick[i] += self._fenwick[i - j]
            else:
                self._cache_chunk(-1).insert(index, value)
                self._fenwick_update(-1, 1)
        else:
            i, j = self._fenwick_index(index)
            if self._lens[i] > 2 * CHUNKSIZE:
                self._filenames.insert(i + 1, type(self)._get_filename())
                data = self._cache_chunk(i)[self._lens[i] // 2:]
                del self._cache[self._lens[i] // 2:]
                if index <= self._lens[i]:
                    self._cache.insert(index, value)
                else:
                    data.insert(index - self._lens[i] // 2, value)
                self._lens[i] = len(self._cache)
                self._lens.insert(i + 1, len(data))
                self._commit_chunk()
                self._cache = data
                self._file = self._filenames[i + 1]
        self._len += 1

if sys.version_info < (3, 9):
    collections.abc.MutableSequence.register(MemList)
