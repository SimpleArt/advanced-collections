import operator
import pickle
from collections import OrderedDict
from collections.abc import Iterable, Iterator
from itertools import chain, islice
from pathlib import Path
from types import TracebackType
from typing import Any, Generic, Optional, SupportsIndex, Type, TypeVar, Union, overload

from .mutable_sequence_islice import MutableSequenceIslice
from .viewable_mutable_sequence import ViewableMutableSequence

__all__ = ["BigList"]

ET = TypeVar("ET", bound=BaseException)
Self = TypeVar("Self", bound="BigList")
T = TypeVar("T")

CHUNKSIZE = 4096

def ensure_file(path: Path, default: T) -> T:
    if not path.exists():
        with open(path, mode="wb") as file:
            pickle.dump(default, file)
        return default
    with open(path, mode="rb") as file:
        return pickle.load(file)


class BigList(ViewableMutableSequence[T], Generic[T]):
    _cache: OrderedDict[str, list[T]]
    _fenwick: Optional[list[int]]
    _filenames: list[str]
    _len: int
    _lens: list[int]
    _path: Path

    __slots__ = {
        "_cache":
            "A cache containing the 4 most recently accessed segments.",
        "_fenwick":
            "A fenwick tree for fast repeated indexing.",
        "_filenames":
            "The file names for each segment.",
        "_len":
            "The total length of the list.",
        "_lens":
            "The length of each segment.",
        "_path":
            "The folder containing all of the files.",
    }

    def __init__(self: Self, path: Union[Path, str], /) -> None:
        self._path = Path(path)
        self._path.mkdir(exist_ok=True)
        self._path /= "list"
        self._path.mkdir(exist_ok=True)
        self._fenwick = None
        self._cache = OrderedDict()
        ensure_file(self._path / "counter.txt", 0)
        self._filenames = ensure_file(self._path / "filenames.txt", [])
        self._lens = ensure_file(self._path / "filenames.txt", [])
        self._len = sum(self._lens)

    def __del__(self: Self, /) -> None:
        with open(self._path / "filenames.txt", mode="wb") as file:
            pickle.dump(self._filenames, file)
        with open(self._path / "lens.txt", mode="wb") as file:
            pickle.dump(self._lens, file)
        for filename, segment in self._cache.items():
            self._commit_chunk(filename, segment)

    def __delitem__(self: Self, index: Union[int, slice], /) -> None:
        if isinstance(index, slice):
            len_ = self._len
            range_ = range(len_)[index]
            size = len(range_)
            if range_.step < 0:
                range_ = range_[::-1]
            if size == len_:
                self.clear()
                return
            elif size == 0:
                return
            elif range_.step == 1 and range_.start == 0:
                for _ in range(len(self._lens)):
                    if size < self._lens[0]:
                        break
                    else:
                        size -= self._lens[0]
                        self._del_chunk(0)
                if size != 0:
                    del self._cache_chunk(0)[:size]
                    self._fenwick_update(0, -size)
                    self._balance(0)
            elif range_.step == 1 and range_.stop == self._len:
                for _ in reversed(range(len(self._lens))):
                    if size < self._lens[-1]:
                        break
                    else:
                        size -= self._lens[-1]
                        self._del_chunk(-1)
                if size != 0:
                    del self._cache_chunk(-1)[:size]
                    self._fenwick_update(-1, -size)
                    self._balance(-1)
            elif range_.step == 1:
                start = self._fenwick_index(range_.start)
                stop = self._fenwick_index(range_.stop)
                if start[0] == stop[0] or start[0] + 1 == stop[0] and stop[1] == 0:
                    del self._cache_chunk(start[0])[start[1]:start[1] + size]
                    self._fenwick_update(start[0], -size)
                    self._balance(start[0])
                    return
                for i in reversed(range(start[0] + 1, stop[0])):
                    (self._path / self._filenames[i]).unlink()
                    if self._filenames[i] in self._cache:
                        del self._cache[self._filenames[i]]
                del self._filenames[start[0] + 1 : stop[0]]
                del self._lens[start[0] + 1 : stop[0]]
                self._fenwick = None
                del self._cache_chunk(start[0])[start[1]:]
                self._lens[start[0]] = start[1]
                del self._cache_chunk(start[0] + 1)[:stop[1]]
                self._lens[start[0] + 1] -= stop[1]
                self._balance(start[0])
            else:
                for i in reversed(range_):
                    del self[i]
            return
        index = range(self._len)[index]
        if index + self._lens[-1] >= self._len:
            index += self._lens[-1] - self._len
            del self._cache_chunk(-1)[index]
            self._fenwick_udpate(-1, -1)
            self._balance(-1)
        elif index >= self._lens[0]:
            i, j = self._fenwick_index(index)
            del self._cache_chunk(i)[j]
            self._fenwick_update(i, -1)
            self._balance(i)
        elif self._len == 1:
            self._del_chunk(0)
            self._fenwick = None
            self._len = 0
        else:
            del self._cache_chunk(0)[index]
            self._fenwick_update(0, -1)
            self._balance(0)

    def __enter__(self: Self, /) -> Self:
        return self

    def __exit__(
        self: Self,
        exc_type: Optional[Type[ET]],
        exc_val: Optional[ET],
        exc_traceback: Optional[TracebackType],
        /,
    ) -> None:
        with open(self._path / "filenames.txt", mode="wb") as file:
            pickle.dump(self._filenames, file)
        with open(self._path / "lens.txt", mode="wb") as file:
            pickle.dump(self._lens, file)
        for filename, segment in self._cache.items():
            self._commit_chunk(filename, segment)

    @overload
    def __getitem__(self: Self, index: int, /) -> T: ...

    @overload
    def __getitem__(self: Self, index: slice, /) -> MutableSequenceIslice[T]: ...

    def __getitem__(self, index, /):
        if isinstance(index, slice):
            range_ = range(self._len)[index]
            return self.islice[index]
        index = range(self._len)[index]
        if index < self._lens[0]:
            return self._cache_chunk(0)[index]
        elif index + self._lens[-1] >= self._len:
            return self._cache_chunk(-1)[index - self._len + self._lens[-1]]
        else:
            i, j = self._fenwick_index(index)
            return self._cache_chunk(i)[j]

    def __islice(self: Self, start: int, stop: int, step: int, /) -> Iterator[T]:
        f_start = self._fenwick_index(start)
        f_stop = self._fenwick_index(stop)
        if step > 0:
            n = f_start[1]
            for i in range(f_start[0], f_stop[0]):
                chunk = self._cache_chunk(i)
                while n < len(chunk):
                    yield chunk[n]
                    n += step
                n -= len(chunk)
            chunk = self._cache_chunk(f_stop[0])
            for i in range(n, f_stop[1] + 1, step):
                yield chunk[i]
        else:
            chunk = self._cache_chunk(f_start[0])
            n = f_start[1] - len(chunk)
            for i in reversed(range(f_stop[0], f_start[0])):
                while n > -len(chunk):
                    yield chunk[n]
                    n += step
                n += len(chunk)
                chunk = self._cache_chunk(i)
            for i in range(n, f_stop[1] - len(chunk) - 1, step):
                yield chunk[i]

    def __islice__(self: Self, start: Optional[int], stop: Optional[int], step: Optional[int], /) -> Iterator[T]:
        range_ = range(self._len)[start:stop:step]
        if len(range_) == self._len:
            return iter(self) if range_.step == 1 else reversed(self)
        elif len(range_) == 0:
            return (self[i] for i in range_)
        elif range_.step == 1 and range_.start == 0:
            return islice(self, range_.stop)
        elif range_.step == 1 and range_.stop == self._len:
            f_start = self._fenwick_index(range_.start)
            if f_start[1] == 0:
                return chain.from_iterable(
                    self._cache_chunk(i)
                    for i in range(f_start[0], len(self._lens))
                )
            else:
                return chain(
                    self._cache_chunk(f_start[0])[f_start[1]:],
                    chain.from_iterable(
                        self._cache_chunk(i)
                        for i in range(f_start[0] + 1, len(self._lens))
                    ),
                )
        elif range_.step == 1:
            f_start = self._fenwick_index(range_.start)
            f_stop = self._fenwick_index(range_.stop)
            if f_start[0] == f_stop[0]:
                return iter(self._cache_chunk(f_start[0])[f_start[1]:f_stop[1]])
            elif f_start[1] == 0 == f_stop[1]:
                return chain.from_iterable(self._cache_chunk(i) for i in range(f_start[0], f_stop[0]))
            elif f_start[1] == 0:
                return chain(
                    chain.from_iterable(
                        self._cache_chunk(i)
                        for i in range(f_start[0], f_stop[0])
                    ),
                    self._cache_chunk(f_stop[0])[:f_stop[1]],
                )
            elif f_stop == 0:
                return chain(
                    self._cache_chunk(f_start[0])[f_start[1]:],
                    chain.from_iterable(
                        self._cache_chunk(i)
                        for i in range(f_start[0] + 1, f_stop[0])
                    ),
                )
            else:
                return chain(
                    self._cache_chunk(f_start[0])[f_start[1]:],
                    chain.from_iterable(
                        self._cache_chunk(i)
                        for i in range(f_start[0] + 1, f_stop[0])
                    ),
                    self._cache_chunk(f_stop[0])[:f_stop[1]],
                )
        elif range_.step == -1 and range_.start + 1 == self._len:
            return islice(reversed(self), len(range_))
        elif range_.step == -1 and range_.stop + 1 == 0:
            f_start = self._fenwick_index(range_.start)
            if f_start[1] + 1 == self._lens[f_start[0]]:
                return chain.from_iterable(reversed(self._cache_chunk(i)) for i in range(f_start[0], -1, -1))
            else:
                return chain(
                    self._cache_chunk(f_start[0])[f_start[1]::-1],
                    chain.from_iterable(
                        reversed(self._cache_chunk(i))
                        for i in reversed(range(f_start[0]))
                    ),
                )
        elif range_.step == -1:
            f_start = self._fenwick_index(range_.start)
            f_stop = self._fenwick_index(range_.stop)
            if f_start[0] == f_stop[0]:
                return iter(self._cache_chunk(f_start[0])[f_start[1]:f_stop[1]:-1])
            elif f_start[1] + 1 == self._lens[f_start[0]] and f_stop[1] + 1 == self._lens[f_stop[0]]:
                return chain.from_iterable(
                    reversed(self._cache_chunk(i))
                    for i in range(f_start[0], f_stop[0], -1)
                )
            elif f_start[1] + 1 == self._lens[f_start[0]]:
                return chain(
                    chain.from_iterable(
                        reversed(self._cache_chunk(i))
                        for i in range(f_start[0], f_stop[0], -1)
                    ),
                    self._cache_chunk(f_stop[0])[:f_stop[1]:-1],
                )
            elif f_stop + 1 == self._lens[f_stop[0]]:
                return chain(
                    self._cache_chunk(f_start[0])[f_start[1]::-1],
                    chain.from_iterable(
                        reversed(self._cache_chunk(i))
                        for i in range(f_start[0] - 1, f_stop[0], -1)
                    ),
                )
            else:
                return chain(
                    self._cache_chunk(f_start[0])[f_start[1]::-1],
                    chain.from_iterable(
                        reversed(self._cache_chunk(i))
                        for i in range(f_start[0] - 1, f_stop[0], -1)
                    ),
                    self._cache_chunk(f_stop[0])[:f_stop[1]:-1],
                )
        elif abs(range_.step) < CHUNKSIZE * 2:
            return self.__islice(range_.start, range_.stop, range_.step)
        else:
            return super().__islice__(range_.start, range_.stop, range_.step)

    def __iter__(self: Self, /) -> Iterator[T]:
        return chain.from_iterable(
            self._cache_chunk(i)
            for i, _ in enumerate(self._lens)
        )

    def __len__(self: Self, /) -> int:
        return self._len

    def __repr__(self: Self, /) -> str:
        return f"{type(self).__name__}({self._path.parent})"

    def __reversed__(self: Self, /) -> Iterator[T]:
        return chain.from_iterable(
            reversed(self._cache_chunk(~i))
            for i, _ in enumerate(self._lens)
        )

    @overload
    def __setitem__(self: Self, index: int, value: T, /) -> None: ...

    @overload
    def __setitem__(self: Self, index: slice, value: Iterable[T], /) -> None: ...

    def __setitem__(self, index, value, /):
        if isinstance(index, slice):
            raise NotImplementedError("big lists do not support slice assignments")
        index = range(self._len)[index]
        if index < self._lens[0]:
            self._cache_chunk(0)[index] = value
        elif index + self._lens[-1] >= self._len:
            self._cache_chunk(-1)[index - self._len + self._lens[-1]] = value
        else:
            i, j = self._fenwick_index(index)
            self._cache_chunk(i)[j] = value

    def _balance(self: Self, index: int, /) -> None:
        lens = self._lens
        if len(lens) == 0:
            return
        elif len(lens) != 1:
            pass
        elif lens[0] > 2 * CHUNKSIZE:
            chunk = self._cache_chunk(0)
            self._filenames.append(self._get_filename())
            self._cache[self._filenames[-1]] = chunk[len(chunk) // 2:]
            del chunk[len(chunk) // 2:]
            self._fenwick = None
            self._lens[0] = len(chunk)
            self._lens.append(len(self._cache_chunk(-1)))
            return
        else:
            return
        index = range(len(lens))[index]
        if index == 0:
            if lens[0] + lens[1] < CHUNKSIZE:
                self._len += lens[1]
                self._fenwick_update(0, lens[1])
                self._cache_chunk(0).extend(self._pop_chunk(1))
            elif lens[0] + lens[1] > 4 * CHUNKSIZE:
                chunk = [
                    *self._cache_chunk(0),
                    *self._cache_chunk(1),
                ]
                self._cache_chunk(0)[:] = chunk[:len(chunk) // 3]
                self._cache_chunk(1)[:] = chunk[len(chunk) // 3 : 2 * len(chunk) // 3]
                del chunk[: 2 * len(chunk) // 3]
                self._filenames.insert(2, self._get_filename())
                self._free_cache()
                self._cache[self._filenames[2]] = chunk
                if len(self._lens) == 2:
                    self._fenwick_append(len(chunk))
                else:
                    self._fenwick = None
                    self._lens.insert(2, len(chunk))
                self._fenwick_update(0, len(self._cache_chunk(0)) - self._lens[0])
                self._fenwick_update(1, len(self._cache_chunk(1)) - self._lens[1])
            elif CHUNKSIZE // 2 < lens[0] < CHUNKSIZE * 2 and 3 * CHUNKSIZE // 2 < lens[0] + lens[1] < 3 * CHUNKSIZE:
                pass
            elif lens[0] > lens[1]:
                diff = lens[0] - lens[1]
                self._cache_chunk(1)[:0] = self._cache_chunk(0)[-diff // 2:]
                del self._cache_chunk(0)[-diff // 2:]
                self._fenwick_update(0, len(self._cache_chunk(0)) - lens[0])
                self._fenwick_update(1, len(self._cache_chunk(1)) - lens[1])
            elif lens[0] < lens[1]:
                diff = lens[1] - lens[0]
                self._cache_chunk(0).extend(self._cache_chunk(1)[:diff // 2])
                del self._cache_chunk(1)[:diff // 2]
                self._fenwick_update(0, len(self._cache_chunk(0)) - lens[0])
                self._fenwick_update(1, len(self._cache_chunk(1)) - lens[1])
        elif index + 1 == len(lens):
            if lens[-1] + lens[-2] < CHUNKSIZE:
                self._len += lens[-1]
                self._fenwick_update(-2, lens[-1])
                self._cache_chunk(-2).extend(self._pop_chunk(-1))
            elif lens[-1] + lens[-2] > 4 * CHUNKSIZE:
                chunk = [
                    *self._cache_chunk(-2),
                    *self._cache_chunk(-1),
                ]
                self._cache_chunk(-2)[:] = chunk[:len(chunk) // 3]
                self._cache_chunk(-1)[:] = chunk[len(chunk) // 3 : 2 * len(chunk) // 3]
                del chunk[: 2 * len(chunk) // 3]
                self._filenames.append(self._get_filename())
                self._free_cache()
                self._cache[self._filenames[-1]] = chunk
                self._fenwick_update(-2, len(self._cache_chunk(-2)) - self._lens[-2])
                self._fenwick_update(-1, len(self._cache_chunk(-1)) - self._lens[-1])
                self._fenwick_append(len(chunk))
            elif CHUNKSIZE // 2 < lens[-1] < CHUNKSIZE * 2 and 3 * CHUNKSIZE // 2 < lens[-1] + lens[-2] < 3 * CHUNKSIZE:
                pass
            elif lens[-1] < lens[-2]:
                diff = lens[-2] - lens[-1]
                self._cache_chunk(-1)[:0] = self._cache_chunk(-2)[-diff // 2:]
                del self._cache_chunk(-2)[-diff // 2:]
                self._fenwick_update(-1, len(self._cache_chunk(-1)) - lens[-1])
                self._fenwick_update(-2, len(self._cache_chunk(-2)) - lens[-2])
            elif lens[-2] < lens[-1]:
                diff = lens[-1] - lens[-2]
                self._cache_chunk(-2).extend(self._cache_chunk(-1)[:diff // 2])
                del self._cache_chunk(-1)[:diff // 2]
                self._fenwick_update(-1, len(self._cache_chunk(-1)) - lens[-1])
                self._fenwick_update(-2, len(self._cache_chunk(-2)) - lens[-2])
        else:
            if lens[index - 1] + lens[index] + lens[index + 1] < 3 * CHUNKSIZE // 2:
                chunk = [
                    *self._cache_chunk(index - 1),
                    *self._cache_chunk(index),
                    *self._pop_chunk(index + 1),
                ]
                self._cache_chunk(index - 1)[:] = chunk[:len(chunk) // 2]
                self._cache_chunk(index)[:] = chunk[len(chunk) // 2:]
                self._fenwick_update(index, (len(chunk) + 1) // 2 - lens[index])
                self._fenwick_update(index + 1, len(chunk) // 2 - lens[index + 1])
            elif lens[index - 1] + lens[index] + lens[index + 1] > 6 * CHUNKSIZE:
                chunk = [
                    *self._cache_chunk(index - 1),
                    *self._cache_chunk(index),
                    *self._cache_chunk(index + 1),
                ]
                self._filenames.insert(index + 2, self._get_filename())
                self._free_cache()
                self._cache_chunk(index - 1)[:] = chunk[:len(chunk) // 4]
                self._cache_chunk(index)[:] = chunk[len(chunk) // 4 : len(chunk) // 2]
                self._cache_chunk(index + 1)[:] = chunk[len(chunk) // 2 : 3 * len(chunk) // 4]
                del chunk[: 3 * len(chunk) // 4]
                self._cache[self._filenames[index + 2]] = chunk
                if index + 3 == len(self._filenames):
                    self._fenwick_append(len(chunk))
                else:
                    self._fenwick = None
                    self._lens.insert(index + 2, len(chunk))
                self._fenwick_update(index - 1, len(self._cache_chunk(index - 1)) - lens[index - 1])
                self._fenwick_update(index, len(self._cache_chunk(index)) - lens[index])
                self._fenwick_update(index + 1, len(self._cache_chunk(index + 1)) - lens[index + 1])
            elif not all(CHUNKSIZE // 2 < 2 * L // 3 < CHUNKSIZE for L in lens[index - 1 : index + 2]):
                chunk = [
                    *self._cache_chunk(index - 1),
                    *self._cache_chunk(index),
                    *self._cache_chunk(index + 1),
                ]
                self._cache_chunk(index - 1)[:] = chunk[:len(chunk) // 3]
                self._cache_chunk(index)[:] = chunk[len(chunk) // 3 : 2 * len(chunk) // 3]
                self._cache_chunk(index + 1)[:] = chunk[2 * len(chunk) // 3:]
                self._fenwick_update(index - 1, len(self._cache_chunk(index - 1)) - lens[index - 1])
                self._fenwick_update(index, len(self._cache_chunk(index)) - lens[index])
                self._fenwick_update(index + 1, len(self._cache_chunk(index + 1)) - lens[index + 1])

    def _cache_chunk(self: Self, index: int, /) -> list[T]:
        filename = self._filenames[index]
        if filename in self._cache:
            self._cache.move_to_end(filename)
        else:
            self._free_cache()
            with open(self._path / filename, mode="rb") as file:
                self._cache[filename] = pickle.load(file)
        return self._cache[filename]

    def _commit_chunk(self: Self, filename: str, segment: list[T], /) -> None:
        with open(self._path / filename, mode="wb") as file:
            pickle.dump(segment, file)

    def _del_chunk(self: Self, index: int, /) -> None:
        index = range(len(self._filenames))[index]
        filename = self._filenames.pop(index)
        (self._path / filename).unlink()
        self._len -= self._lens.pop(index)
        if self._fenwick is None or index < len(self._filenames):
            self._fenwick = None
        else:
            del self._fenwick[-1]
        self._cache.pop(filename, None)

    def _fenwick_append(self: Self, value: int, /) -> None:
        fenwick = self._fenwick
        self._lens.append(value)
        if fenwick is None:
            return
        i = len(fenwick)
        j = i & -i
        fenwick.append(value)
        while j > 1:
            j //= 2
            fenwick[i] += fenwick[i - j]

    def _fenwick_index(self: Self, index: int, /) -> tuple[int, int]:
        if self._fenwick is None:
            fenwick = [0, *self._lens]
            fenwick_len = len(fenwick)
            for i in range(1, fenwick_len):
                j = i + (i & -i)
                if j < fenwick_len:
                    fenwick[j] += fenwick[i]
            self._fenwick = fenwick
        else:
            fenwick = self._fenwick
            fenwick_len = len(self._fenwick)
        i = 0
        j = 2048
        while j < fenwick_len:
            j *= 2
        while j > 0:
            i += j
            if i < fenwick_len and self._fenwick[i] <= index:
                index -= self._fenwick[i]
            else:
                i -= j
            j //= 2
        return (i, index)

    def _fenwick_update(self: Self, index: int, value: int, /) -> None:
        if value == 0:
            return
        index = range(len(self._lens))[index] + 1
        self._lens[index - 1] += value
        fenwick = self._fenwick
        if fenwick is not None:
            fenwick_len = len(fenwick)
            if index & (index - 1) == 0:
                while index < fenwick_len:
                    fenwick[index] += value
                    index *= 2
            else:
                while index < fenwick_len:
                    fenwick[index] += value
                    index += index & -index

    def _free_cache(self: Self, /) -> None:
        if len(self._cache) == 4:
            self._commit_chunk(*self._cache.popitem(last=False))

    def _get_filename(self: Self, /) -> str:
        path = self._path / "counter.txt"
        uid = int(path.read_text())
        path.write_text(str(uid + 1))
        (self._path / f"{uid}.txt").touch()
        with open(self._path / f"{uid}.txt", mode="wb") as file:
            pickle.dump([], file)
        return f"{uid}.txt"

    def _pop_chunk(self: Self, index: int, /) -> list[T]:
        filename = self._filenames[index]
        if filename in self._cache:
            segment = self._cache.pop(filename)
        else:
            with open(self._path / filename, mode="rb") as file:
                segment = pickle.load(file)
        self._del_chunk(index)
        return segment

    def append(self: Self, value: T, /) -> None:
        if self._len == 0:
            self._fenwick = None
            self._filenames.append(self._get_filename())
            self._cache[self._filenames[-1]] = [value]
            self._len = 1
            self._lens.append(1)
            return
        else:
            self._cache_chunk(-1).append(value)
            self._len += 1
            self._fenwick_update(-1, 1)
            self._balance(-1)

    def clear(self: Self, /) -> None:
        path = self._path
        for filename in self._filenames:
            (path / filename).unlink()
        (path / "counter.txt").write_text("0")
        with open(path / "filenames.txt", mode="wb") as file:
            pickle.dump([], file)
        with open(path / "lens.txt", mode="wb") as file:
            pickle.dump([], file)
        self._cache.clear()
        self._fenwick = None
        self._filenames.clear()
        self._len = 0
        self._lens.clear()

    def extend(self: Self, iterable: Iterable[T], /) -> None:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"extend expected iterable, got {iterable!r}")
        if not isinstance(iterable, list):
            iterable = [*iterable]
        offset = 0
        if len(iterable) == 0:
            return
        elif len(self._lens) == 1 and self._lens[0] < CHUNKSIZE:
            offset = CHUNKSIZE - self._lens[0]
            self._cache_chunk(0).extend(iterable[:offset])
            self._len += len(self._cache_chunk(0)) - self._lens[0]
            self._fenwick_update(0, len(self._cache_chunk(0)) - self._lens[0])
        else:
            offset = 0
        for i in range(offset, len(iterable), CHUNKSIZE):
            self._free_cache()
            filename = self._get_filename()
            self._filenames.append(filename)
            chunk = iterable[i : i + CHUNKSIZE]
            self._cache[filename] = chunk
            self._len += len(chunk)
            self._fenwick_append(len(chunk))

    def insert(self: Self, index: int, value: T, /) -> None:
        index = operator.index(index)
        if self._len == 0:
            self._fenwick = None
            self._filenames.append(self._get_filename())
            self._cache[self._filenames[-1]] = [value]
            self._len = 1
            self._lens.append(1)
            return
        elif index < 0:
            index += self._len
            if index < 0:
                index = 0
        elif index >= self._len:
            return self.append(value)
        if index <= self._lens[0]:
            self._cache_chunk(0).insert(index, value)
            self._len += 1
            self._fenwick_update(0, 1)
            self._balance(0)
        elif index + self._lens[-1] >= self._len:
            self._cache_chunk(-1).insert(index - self._len + self._lens[-1], value)
            self._len += 1
            self._fenwick_update(-1, 1)
            self._balance(-1)
        else:
            i, j = self._fenwick_index(index)
            self._cache_chunk(i).insert(j, value)
            self._len += 1
            self._fenwick_update(i, 1)
            self._balance(i)

    def reverse(self: Self, /) -> None:
        for i, _ in enumerate(self._lens):
            self._cache_chunk(i).reverse()
        self._fenwick = None
        self._filenames.reverse()
        self._lens.reverse()
