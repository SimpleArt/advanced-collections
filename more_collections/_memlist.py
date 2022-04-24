from __future__ import annotations
import collections.abc
import operator
import pickle
import sys
from itertools import chain, islice
from pathlib import Path
from types import TracebackType
from typing import Any, ClassVar, Generic, Optional, SupportsIndex, Type, TypeVar, Union, overload

if sys.version_info < (3, 9):
    from typing import Iterable, Iterator, MutableSequence, List as list, Set as set
else:
    from collections.abc import Iterable, Iterator, MutableSequence

__all__ = ["MemList"]

ET = TypeVar("ET", bound=BaseException)
T = TypeVar("T")

reprs_seen: set[int] = {*()}

CHUNKSIZE: int = 1 << 14

FOLDER = Path.home() / "_more_collections"
FOLDER.mkdir(exist_ok=True)
FOLDER /= "_mem_list"
FOLDER.mkdir(exist_ok=True)
(FOLDER / "_counter.txt").touch()
(FOLDER / "_counter.txt").write_text("0")
(FOLDER / "_metadata.txt").touch()
(FOLDER / "_metadata.txt").write_text("MemList")


class MemList(MutableSequence[T], Generic[T]):
    _cache: Optional[list[T]]
    _is_closed: bool
    _fenwick: Optional[list[int]]
    _file: Optional[str]
    _filenames: list[str]
    _folder: Optional[Path]
    _len: int
    _lens: list[int]

    __slots__ = {
        "_cache":
            "Cache the contents of a file.",
        "_is_closed":
            "Checks if the mem list is closed.",
        "_fenwick":
            "The length of each individual segment is stored"
            " via a Fenwick tree when needed. `None` while"
            " indexing is not needed or if the Fenwick tree"
            " needs to be reconstructed.",
        "_file":
            "The currently cached file.",
        "_filenames":
            "The file names for each segment.",
        "_folder":
            "The folder storing all of the data.",
        "_len":
            "The total length is maintained as an attribute.",
        "_lens":
            "The length of each file's list is tracked so that"
            " the file does not need to be read for indexing.",
    }

    def __init__(self: MemList[T], iterable: Optional[Iterable[T]] = None, /) -> None:
        if iterable is not None and not isinstance(iterable, Iterable):
            raise TypeError(f"{type(self).__name__} expected an iterable, got {iterable!r}")
        self._cache = None
        self._is_closed = False
        self._fenwick = None
        self._file = None
        self._filenames = []
        self._folder = None
        self._lens = []
        cls = type(self)
        if iterable is not None:
            iterator = iter(iterable)
            for chunk in iter(lambda: [*islice(iterator, CHUNKSIZE)], []):
                self._filenames.append(self._get_filename())
                with open((FOLDER if self._folder is None else self._folder) / self._filenames[-1], mode="wb") as file:
                    pickle.dump(chunk, file)
                self._lens.append(len(chunk))
        if len(self._lens) == 0:
            self._len = 0
        else:
            self._len = CHUNKSIZE * (len(self._lens) - 1) + self._lens[-1]

    def __del__(self: MemList[Any], /) -> None:
        if self._folder is None:
            self.clear()

    def __delitem__(self: MemList[Any], index: Union[int, slice], /) -> None:
        if self._is_closed:
            raise RuntimeError("mem list used outside of with block")
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
                for _ in range(len(self._lens)):
                    if size < self._lens[0]:
                        break
                    else:
                        size -= self._lens[0]
                        self._del_chunk(0)
                if size == 0:
                    pass
                elif self._file == self._filenames[0]:
                    del self._cache[:size]
                    if len(self._lens) > 1 and len(self._cache) < CHUNKSIZE // 2:
                        self._cache.extend(self._pop_chunk(1))
                elif len(self._lens) == 1 or self._lens[0] - size > CHUNKSIZE // 2:
                    del self._cache_chunk(0)[:size]
                else:
                    data = self._pop_chunk(1)
                    del self._cache_chunk(0)[:size]
                    self._cache.extend(data)
                self._lens[0] = len(self._cache)
            elif range_.step == 1 and range_.stop == self._len:
                for _ in reversed(range(len(self._lens))):
                    if size < self._lens[-1]:
                        break
                    else:
                        size -= self._lens[-1]
                        self._del_chunk(-1)
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
            return
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
        elif index >= self._len - self._lens[-1]:
            if self._lens[-1] == 1:
                self._del_chunk(-1)
                return
            index += self._lens[-1] - self._len
            del self._cache_chunk(-1)[index]
            self._fenwick_update(-1, -1)
            if len(self._lens) > 1 and self._lens[-1] < CHUNKSIZE // 2:
                cache = self._pop_chunk(-1)
                self._cache_chunk(-1).extend(cache)
                self._fenwick_update(-1, len(cache))
        else:
            i, j = self._fenwick_index(index)
            if self._lens > CHUNKSIZE // 2:
                del self._cache_chunk(i)[j]
                self._update_fenwick(i, -1)
            elif self._lens[i - 1] < self._lens[i + 1]:
                cache = self._pop_chunk(i)
                del cache[j]
                self._cache_chunk(i - 1).extend(cache)
                self._lens[i - 1] = len(self._cache)
                self._len -= 1
            else:
                cache = self._pop_chunk(i + 1)
                del self._cache_chunk(i)[j]
                self._cache.extend(cache)
                self._lens[i] = len(self._cache)
                self._len -= 1

    @overload
    def __getitem__(self: MemList[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: MemList[T], index: slice, /) -> MemList[T]:
        ...

    def __getitem__(self, index, /):
        if self._is_closed:
            raise RuntimeError("mem list used outside of with block")
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
            # Start from the middle.
            elif range_.step == 1 and range_.stop == self._len:
                i, j = self._fenwick_index(range_.start)
                return type(self)(chain.from_iterable(chain(
                    islice(self._cache_chunk(i), j, None),
                    (self._cache_chunk(k) for k in range(i + 1, len(self._lens))),
                )))
            # Start from the end.
            elif range_.step == -1 and range_.start == self._len - 1:
                return type(self)(islice(reversed(self), len(range_)))
            # Start from the middle.
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
        if self._is_closed:
            raise RuntimeError("mem list used outside of with block")
        return chain.from_iterable(
            self._cache_chunk(i)
            for i, _ in enumerate(self._lens)
        )

    def __len__(self: MemList[Any], /) -> int:
        if self._is_closed:
            raise RuntimeError("mem list used outside of with block")
        return self._len

    def __repr__(self: MemList[Any], /) -> str:
        return object.__repr__(self)

    def __reversed__(self: MemList[T], /) -> Iterator[T]:
        if self._is_closed:
            raise RuntimeError("mem list used outside of with block")
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
        if self._is_closed:
            raise RuntimeError("mem list used outside of with block")
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
            with open((FOLDER if self._folder is None else self._folder) / self._file, mode="wb") as file:
                pickle.dump(self._cache, file)

    def _del_chunk(self: MemList[Any], index: int, /) -> None:
        index = range(len(self._filenames))[index]
        ((FOLDER if self._folder is None else self._folder) / self._filenames[index]).unlink()
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
        self._lens[index - 1] += value
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

    def _get_filename(self: MemList[Any], /) -> str:
        file = FOLDER if self._folder is None else self._folder
        file /= "_counter.txt"
        uid = int((file).read_text())
        file.write_text(str(uid + 1))
        return f"{uid}.txt"

    def _load_chunk(self: MemList[T], index: int, /) -> list[T]:
        if self._file == self._filenames[index]:
            return self._cache
        with open((FOLDER if self._folder is None else self._folder) / self._filenames[index], mode="rb") as file:
            return pickle.load(file)

    def _pop_chunk(self: MemList[T], index: int, /) -> list[T]:
        data = self._load_chunk(index)
        self._del_chunk(index)
        return data

    def clear(self: MemList[Any], /) -> None:
        if self._is_closed:
            raise RuntimeError("mem list used outside of with block")
        folder = FOLDER if self._folder is None else self._folder
        for filename in self._filenames:
            (folder / filename).unlink()
        if self._folder is not None:
            (folder / "_counter.txt").unlink()
            (folder / "_filenames.txt").unlink()
            (folder / "_lens.txt").unlink()
            (folder / "_metadata.txt").unlink()
        self._cache = None
        self._fenwick = None
        self._file = None
        self._filenames.clear()
        self._len = 0
        self._lens.clear()

    def insert(self: MemList[T], index: int, value: T, /) -> None:
        if self._is_closed:
            raise RuntimeError("mem list used outside of with block")
        if not isinstance(index, SupportsIndex):
            raise TypeError(f"index could not be interpreted as an integer, got {index!r}")
        index = operator.index(index)
        if self._len == 0:
            self._cache = [value]
            self._fenwick = None
            self._file = self._get_filename()
            self._filenames.append(self._file)
            self._len = 1
            self._lens.append(1)
            return
        elif index < 0:
            index += self._len
        if index <= self._lens[0]:
            if self._lens[0] > 2 * CHUNKSIZE:
                self._fenwick = None
                self._filenames.insert(1, self._get_filename())
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
                self._len += 1
            else:
                self._cache_chunk(0).insert(index, value)
                self._fenwick_update(0, 1)
        elif index >= self._len - self._lens[-1]:
            index += self._lens[-1] - self._len
            if self._lens[-1] > 2 * CHUNKSIZE:
                data = self._cache_chunk(-1)[self._lens[-1] // 2:]
                del self._cache[self._lens[-1] // 2:]
                if index <= self._lens[-1] // 2:
                    self._cache.insert(index, value)
                else:
                    data.insert(index - self._lens[-1] // 2, value)
                self._len += 1
                self._lens[-1] = len(self._cache)
                self._commit_chunk()
                self._cache = data
                self._file = self._get_filename()
                self._filenames.append(self._file)
                self._lens.append(len(data))
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
                self._filenames.insert(i + 1, self._get_filename())
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
            else:
                self._cache_chunk(i).insert(j, value)
                self._fenwick_update(i, 1)

    def reverse(self: MemList[Any], /) -> None:
        if len(self._lens) > 1:
            for i in range(len(self._lens)):
                self._cache_chunk(i).reverse()
            self._fenwick = None
            self._filenames.reverse()
            self._lens.reverse()
        elif self._cache is None:
            for i in range(len(self._lens)):
                self._cache_chunk(i).reverse()
        else:
            self._cache.reverse()

    @classmethod
    def open(cls: Type[MemList[Any]], directory: Union[Path, str], /) -> MemListProxy:
        return MemListProxy(Path(directory))


class MemListProxy:
    _mem_list: MemList[Any]

    __slots__ = {"_mem_list": "The mem list used."}

    def __init__(self: MemListProxy, folder: Path, /) -> None:
        self._mem_list = MemList()
        self._mem_list._folder = folder
        if not self._mem_list._folder.exists():
            self._mem_list._folder.mkdir()
        elif not self._mem_list._folder.is_dir():
            raise ValueError("a directory must be given")
        if not (self._mem_list._folder / "_counter.txt").exists():
            (self._mem_list._folder / "_counter.txt").touch()
            (self._mem_list._folder / "_counter.txt").write_text("0")
            (self._mem_list._folder / "_filenames.txt").touch()
            with open((self._mem_list._folder / "_filenames.txt"), mode="wb") as file:
                pickle.dump([], file)
            (self._mem_list._folder / "_lens.txt").touch()
            with open((self._mem_list._folder / "_lens.txt"), mode="wb") as file:
                pickle.dump([], file)
            (self._mem_list._folder / "_metadata.txt").touch()
            (self._mem_list._folder / "_metadata.txt").write_text("MemList")
        elif not (self._mem_list._folder / "_counter.txt").is_file():
            raise ValueError(f"{(self._mem_list._folder / '_counter.txt')} must be a file")
        elif not (self._mem_list._folder / "_filenames.txt").is_file():
            raise ValueError(f"{(self._mem_list._folder / '_filenames.txt')} must be a file")
        elif not (self._mem_list._folder / "_lens.txt").is_file():
            raise ValueError(f"{(self._mem_list._folder / '_lens.txt')} must be a file")
        elif not (self._mem_list._folder / "_metadata.txt").is_file():
            raise ValueError(f"{(self._mem_list._folder / '_metadata.txt')} must be a file")
        elif (self._mem_list._folder / "_metadata.txt").read_text() != "MemList":
            raise ValueError(f"{self._mem_list._folder} is not for a MemList")
        else:
            with open((self._mem_list._folder / "_filenames.txt"), mode="rb") as file:
                self._mem_list._filenames = pickle.load(file)
            assert type(self._mem_list._filenames) is type([]), self._mem_list._filenames
            assert all(isinstance(x, str) for x in self._mem_list._filenames), self._mem_list._filenames
            with open((self._mem_list._folder / "_lens.txt"), mode="rb") as file:
                self._mem_list._lens = pickle.load(file)
            assert type(self._mem_list._lens) is type([]), self._mem_list._lens
            assert all(isinstance(x, int) for x in self._mem_list._lens), self._mem_list._lens
            self._mem_list._len = sum(self._mem_list._lens)

    def __enter__(self: MemListProxy, /) -> MemList[Any]:
        return self._mem_list

    def __exit__(self: MemListProxy, exc_type: Type[ET], exc_val: ET, exc_traceback: TracebackType, /) -> None:
        self._mem_list._commit_chunk()
        with open((self._mem_list._folder / "_filenames.txt"), mode="wb") as file:
            pickle.dump(self._mem_list._filenames, file)
        with open((self._mem_list._folder / "_lens.txt"), mode="wb") as file:
            pickle.dump(self._mem_list._lens, file)
        self._mem_list._is_closed = True


if sys.version_info < (3, 9):
    collections.abc.MutableSequence.register(MemList)
