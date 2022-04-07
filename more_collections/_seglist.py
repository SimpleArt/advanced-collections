from __future__ import annotations
import collections.abc
import sys
from itertools import chain, islice
from typing import Generic, Optional, TypeVar, Union, overload

if sys.version_info < (3, 9):
    from typing import Iterable, Iterator, MutableSequence, List as list, Set as set
else:
    from collections.abc import Iterable, Iterator, MutableSequence

T = TypeVar("T")

reprs_seen: set[int] = {*()}

CHUNKSIZE = 1024


class SegList(MutableSequence[T], Generic[T]):
    _data: list[list[T]]
    _len: int
    _lens: Optional[list[int]]

    __slots__ = {
        "_data":
            "The data is stored as segments.",
        "_len":
            "The total length is maintained as an attribute.",
        "_lens":
            "The length of each individual segment is stored via a Fenwick tree when needed."
            " `None` while indexing is not needed or if the Fenwick tree needs to be reconstructed.",
    }

    def __init__(self: SegList[T], iterable: Optional[Iterable[T]] = None, /) -> None:
        if iterable is None:
            self._data = []
        elif type(iterable) is type([]):
            self._data = [iterable[i : i + CHUNKSIZE] for i in range(0, len(iterable), CHUNKSIZE)]
        elif isinstance(iterable, Iterable):
            iterator = iter(iterable)
            self._data = [*iter(lambda: [*islice(iterator, CHUNKSIZE)], [])]
        else:
            raise TypeError(f"{type(self).__name__} expected an iterable, got {iterable!r}")
        if len(self._data) == 0:
            self._len = 0
        else:
            self._len = CHUNKSIZE * (len(self._data) - 1) + len(self._data[-1])
        self._lens = None

    def __delitem__(self: SegList[T], index: Union[int, slice], /) -> None:
        if isinstance(index, slice):
            range_ = range(self._len)[index]
            if self._len == len(range_):
                self.clear()
                return
            elif self._len > 8 * len(range_):
                if range_.step > 0:
                    range_ = range_[::-1]
                for i in range_:
                    del self[i]
                return
            if range_.step < 0:
                range_ = range_[::-1]
            if range_.step == 1 and range_.start == 0:
                data = list(islice(reversed(self), self._len - len(range_)))
                self._data = [data[i : i - CHUNKSIZE : -1] for i in range(-1, -len(data), -CHUNKSIZE)]
            elif range_.step == 1 and range_.stop == self._len:
                iterator = islice(self, range_.start)
                self._data = [*iter(lambda: [*islice(iterator, CHUNKSIZE)], [])]
            else:
                iterator = (x for i, x in enumerate(self) if i not in range_)
                self._data = [*iter(lambda: [*islice(iterator, CHUNKSIZE)], [])]
            self._len -= len(range_)
            self._lens = None
            return
        try:
            index = range(self._len)[index]
        except TypeError:
            raise TypeError(f"indices must be integers or slices, not {type(index).__name__}") from None
        except IndexError:
            raise IndexError("index out of range") from None
        data = self._data
        lens = self._lens
        if index < len(data[0]):
            if len(data[0]) == 1:
                del data[0]
                self._lens = None
                self._len -= 1
                return
            del data[0][index]
            if len(data) > 1 and len(data[0]) < CHUNKSIZE // 2:
                data[0].extend(data.pop(1))
                self._lens = None
            elif lens is not None:
                i = 1
                len_lens = len(lens)
                while i < len_lens:
                    lens[i] -= 1
                    i *= 2
            self._len -= 1
            return
        elif index >= self._len - len(data[-1]):
            if len(data[-1]) == 1:
                del data[-1]
                if lens is not None:
                    del lens[-1]
                self._len -= 1
                return
            index += len(data[-1]) - self._len
            del data[-1][index]
            if len(data) > 1 and len(data[-1]) < CHUNKSIZE // 2:
                data[-2].extend(data.pop(-1))
                if lens is not None:
                    del lens[-1]
            elif lens is not None:
                lens[-1] -= 1
            self._len -= 1
            return
        self._ensure_lens()
        lens = self._lens
        i = 0
        j = 2048
        len_lens = len(lens)
        while j < len_lens:
            j *= 2
        while j > 0:
            if i + j < len_lens and lens[i + j] <= index:
                i += j
                index -= lens[i]
            j //= 2
        assert 0 < i < len(data) - 1
        L = data[i]
        len2 = len(L) // 2
        del L[index]
        self._len -= 1
        if len(data) < 2 or len2 > CHUNKSIZE // 4:
            i += 1
            while i < len_lens:
                lens[i] -= 1
                i += i & -i
        elif len(data[i - 1]) < len(data[i + 1]):
            data[i - 1].extend(data.pop(i))
            self._lens = None
        else:
            L.extend(data.pop(i + 1))
            self._lens = None

    @overload
    def __getitem__(self: SegList[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: SegList[T], index: slice, /) -> SegList[T]:
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
                result = type(self)()
                result._len = len(range_)
                data = list(islice(reversed(self), result._len))
                result._data = [data[i : i - CHUNKSIZE : -1] for i in range(-1, -result._len, -CHUNKSIZE)]
                return result
            # Start from the end.
            elif range_.step == -1 and range_.start == self._len - 1:
                return type(self)(islice(reversed(self), len(range_)))
            # Start from the beginning and reverse it.
            elif range_.step == -1 and range_.stop == -1:
                result = type(self)()
                result._len = len(range_)
                data = list(islice(self, result._len))
                result._data = [data[i : i - CHUNKSIZE : -1] for i in range(-1, -result._len, -CHUNKSIZE)]
                return result
            # Use random access indexing if it's small.
            elif self._len > 8 * len(range_):
                return type(self)([self[i] for i in range_])
            # Loop forward and check if the index matches if it's a lot.
            elif range_.step > 0:
                return type(self)([x for i, x in enumerate(self) if i in range_])
            else:
                return type(self)([x for i, x in enumerate(reversed(self), 1 - self._len) if -i in range_])
        try:
            index = range(self._len)[index]
        except TypeError:
            raise TypeError(f"indices must be integers or slices, not {type(index).__name__}") from None
        except IndexError:
            raise IndexError("index out of range") from None
        data = self._data
        if index < len(data[0]):
            return data[0][index]
        elif index >= self._len - len(data[-1]):
            return data[-1][index - self._len + len(data[-1])]
        self._ensure_lens()
        lens = self._lens
        i = 0
        j = 2048
        len_lens = len(lens)
        while j < len_lens:
            j *= 2
        while j > 0:
            if i + j < len_lens and lens[i + j] <= index:
                i += j
                index -= lens[i]
            j //= 2
        return data[i][index]

    def __iter__(self: SegList[T], /) -> Iterator[T]:
        return chain.from_iterable(self._data)

    def __len__(self: SegList[Any], /) -> int:
        return self._len

    def __repr__(self: SegList[Any], /) -> str:
        if id(self) in reprs_seen:
            return "..."
        reprs_seen.add(id(self))
        try:
            if self._len == 0:
                return f"{type(self).__name__}()"
            else:
                data = ", ".join([repr(x) for x in self])
                return f"{type(self).__name__}([{data}])"
        finally:
            reprs_seen.remove(id(self))

    def __reversed__(self: SegList[T], /) -> Iterator[T]:
        return (
            x
            for L in reversed(self._data)
            for x in reversed(L)
        )

    @overload
    def __setitem__(self: SegList[T], index: int, value: T, /) -> None:
        ...

    @overload
    def __setitem__(self: SegList[T], index: slice, value: Iterable[T], /) -> None:
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
        data = self._data
        if index < len(data[0]):
            data[0][index] = value
            return
        elif index >= self._len - len(data[-1]):
            data[-1][index - self._len + len(data[-1])] = value
            return
        self._ensure_lens()
        lens = self._lens
        i = 0
        j = 2048
        len_lens = len(lens)
        while j < len_lens:
            j *= 2
        while j > 0:
            if i + j < len_lens and lens[i + j] <= index:
                i += j
                index -= lens[i]
            j //= 2
        data[i][index] = value

    def _ensure_lens(self: SegList[Any], /) -> None:
        lens = self._lens
        if lens is None:
            lens = [len(L) for L in self._data]
            lens.insert(0, 0)
            len_lens = len(lens)
            for i in range(1, len_lens):
                j = i + (i & -i)
                if j < len_lens:
                    lens[j] += lens[i]
            self._lens = lens

    def append(self: SegList[T], value: T, /) -> None:
        data = self._data
        lens = self._lens
        if self._len == 0:
            self._data.append([value])
            self._len = 1
            self._lens = None
            return
        L = data[-1]
        len2 = len(L) // 2
        if len2 > CHUNKSIZE:
            data.append(L[len2:])
            del L[len2:]
            data[-1].append(value)
            if lens is not None:
                lens.append(len(data[-1]))
                lens[-2] -= lens[-1]
                i = len(data)
                j = i & -i
                while j > 1:
                    j //= 2
                    lens[i] += lens[i - j]
        else:
            L.append(value)
            if lens is not None:
                lens[-1] += 1
        self._len += 1

    def clear(self: SegList[Any], /) -> None:
        self._len = 0
        self._lens = None
        self._data.clear()

    def extend(self: SegList[T], iterable: Iterable[T], /) -> None:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"extend expected an iterable, got {iterable!r}")
        data = self._data
        self._lens = None
        if type(iterable) is type([]):
            if self._len == 0:
                self._data = [iterable[i : i + CHUNKSIZE] for i in range(0, len(iterable), CHUNKSIZE)]
            else:
                remainder = CHUNKSIZE - len(data[-1])
                data[-1].extend(iterable[:remainder])
                data.extend(iterable[i : i + CHUNKSIZE] for i in range(remainder, len(iterable), CHUNKSIZE))
            self._len += len(iterable)
        else:
            iterator = iter(iterable)
            if self._len == 0:
                self._data = [*iter(lambda: [*islice(iterator, CHUNKSIZE)], [])]
                if len(self._data) != 0:
                    self._len = CHUNKSIZE * (len(self._data) - 1) + len(self._data[-1])
            else:
                i = len(data)
                j = len(data[-1])
                data[-1].extend(islice(iterator, CHUNKSIZE - j))
                data.extend(iter(lambda: [*islice(iterator, CHUNKSIZE)], []))
                self._len += len(data[-1]) - j
                if i > len(data):
                    self._len += CHUNKSIZE * (len(data) - i - 1) + len(data[-1])

    def insert(self: SegList[T], index: int, value: T, /) -> None:
        if not isinstance(index, SupportsIndex):
            raise TypeError(f"index could not be interpreted as an integer, got {index!r}")
        index = operator.index(index)
        if self._len == 0:
            self._data.append([value])
            self._len = 1
            self._lens = None
            return
        if index < 0:
            index += self._len
        data = self._data
        lens = self._lens
        if index <= len(data[0]):
            L = data[0]
            len2 = len(L) // 2
            if len2 > CHUNKSIZE:
                data.insert(1, L[len2:])
                del L[len2:]
                if index <= len2:
                    L.insert(index, value)
                else:
                    data[1].insert(index - len2, value)
                self._lens = None
            else:
                L.insert(index, value)
                if lens is not None:
                    i = 1
                    len_lens = len(lens)
                    while i < len_lens:
                        lens[i] += 1
                        i *= 2
        elif index >= self._len - len(data[-1]):
            index += len(data[-1]) - self._len
            L = data[-1]
            len2 = len(L) // 2
            if len2 > CHUNKSIZE:
                data.append(L[len2:])
                del L[len2:]
                if index <= len2:
                    L.insert(index, value)
                else:
                    data[-1].insert(index - len2, value)
                if lens is not None:
                    lens.append(len(data[-1]))
                    lens[-2] -= lens[-1]
                    i = len(data)
                    j = i & -i
                    while j > 1:
                        j //= 2
                        lens[i] += lens[i - j]
            else:
                L.insert(index, value)
                if lens is not None:
                    i = 1
                    len_lens = len(lens)
                    while i < len_lens:
                        lens[i] += 1
                        i *= 2
        else:
            self._ensure_lens()
            lens = self._lens
            i = 0
            j = 2048
            len_lens = len(lens)
            while j < len_lens:
                j *= 2
            while j > 0:
                if i + j < len_lens and lens[i + j] <= index:
                    i += j
                    index -= lens[i]
                j //= 2
            L = data[i]
            len2 = len(L) // 2
            if len2 > CHUNKSIZE:
                data.insert(i + 1, L[len2:])
                del L[len2:]
                if index <= len2:
                    L.insert(index, value)
                else:
                    data[i + 1].insert(index - len2, value)
                self._lens = None
            else:
                L.insert(index, value)
                i += 1
                len_lens = len(lens)
                while i < len_lens:
                    lens[i] += 1
                    i += i & -i
        self._len += 1

if sys.version_info < (3, 9):
    collections.abc.MutableSequence.register(SegList)
