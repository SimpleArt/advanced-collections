from __future__ import annotations
import operator
import sys
from bisect import bisect, insort
from itertools import chain, islice
from operator import length_hint
from typing import Any, Generic, Literal, Optional, Protocol, SupportsIndex, Type, TypeVar, overload, runtime_checkable

if sys.version_info < (3, 9):
    from typing import Iterable, Iterator, Sequence, Sized, List as list, Tuple as tuple
else:
    from collections.abc import Iterable, Iterator, Sequence, Sized

from advanced_collections._src.comparable import SupportsRichHashableComparison
from .collection import SortedCollection
from .mutable_sequence import SortedMutableSequence

__all__ = ["SortedList"]

Self = TypeVar("Self", bound="SortedList")
T = TypeVar("T", bound=SupportsRichHashableComparison)

reprs_seen = {0} - {0}

CHUNKSIZE: int = 1024


@runtime_checkable
class SupportsLengthHint(Protocol):

    def __length_hint__(self) -> int:
        ...


class SortedList(SortedMutableSequence[T], Generic[T]):
    _data: list[list[T]]
    _fenwick: Optional[list[int]]
    _len: int
    _mins: list[T]

    __slots__ = {
        "_data":
            "The data is stored in chunks.",
        "_fenwick":
            "The length of each individual segment is stored via a"
            " Fenwick tree when needed.",
        "_len":
            "The total length of the list.",
        "_mins":
            "The smallest element of each chunk.",
    }

    def __init__(self: Self, iterable: Optional[Iterable[T]] = None, /) -> None:
        data: list[T]
        # Sort the data.
        if iterable is None:
            data = []
        elif isinstance(iterable, Iterable):
            data = sorted(iterable)
        else:
            raise TypeError(f"{type(self).__name__} expected an iterable, got {iterable!r}")
        self._len = len(data)
        self._fenwick = None
        self._data = [data[i : i + CHUNKSIZE] for i in range(0, len(data), CHUNKSIZE)]
        if len(self._data) > 1 and len(self._data[-1]) < CHUNKSIZE // 2:
            self._data[-2].extend(self._data.pop())
            self._mins = data[:-CHUNKSIZE:CHUNKSIZE]
        else:
            self._mins = data[::CHUNKSIZE]

    def __contains__(self: Self, element: Any, /) -> bool:
        if self._len == 0:
            return False
        data = self._data
        mins = self._mins
        if element < mins[0]:
            return False
        elif element >= mins[-1]:
            chunk = data[-1]
        else:
            chunk = data[bisect(mins, element, 0, len(mins) - 1) - 1]
        i = bisect(chunk, element)
        return i > 0 and not (element is not chunk[i - 1] != element)

    def __delitem__(self: Self, index: Union[int, slice], /) -> None:
        data = self._data
        mins = self._mins
        if isinstance(index, slice):
            range_ = range(self._len)[index]
            if len(range_) == self._len:
                self.clear()
                return
            elif len(range_) == 0:
                return
            if range_.step < 0:
                range_ = range_[ ::-1]
            if range_.step == 1 and range_.start == 0:
                i, j = self._fenwick_index(range_.stop)
                if i > 0:
                    del data[:i - 1]
                    del mins[:i - 1]
                if j > 0:
                    del data[0][:j]
                    mins[0] = data[0][0]
                if len(data) > 1 and len(data[0]) < CHUNKSIZE // 2:
                    data[0].extend(data.pop(1))
                    del mins[1]
                self._fenwick = None
                self._len -= len(range_)
            elif range_.step == 1 and range_.stop == self._len:
                i, j = self._fenwick_index(range_.start)
                if j == 0:
                    del data[i:]
                    del mins[i:]
                    del self._fenwick[i + 1:]
                else:
                    del data[i + 1:]
                    del data[i][j:]
                    if i > 0 and len(data[i]) < CHUNKSIZE // 2:
                        data[i - 1].extend(data.pop())
                        del mins[i:]
                        del self._fenwick[i:]
                    else:
                        del mins[i + 1:]
                        del self._fenwick[i + 1:]
                self._len -= len(range_)
            elif range_.step == 1:
                start_chunk, start_index = self._fenwick_index(range_.start)
                stop_chunk, stop_index = self._fenwick_index(range_.stop)
                len_ = len(data[start_chunk + 1])
                del data[start_chunk + 1 : stop_chunk]
                del mins[start_chunk + 1 : stop_chunk]
                if start_chunk == stop_chunk:
                    del data[start_chunk][start_index:stop_index]
                    self._fenwick_update(-1, start_index - stop_index)
                    if len(data) == 1:
                        mins[0] = data[0][0]
                        self._fenwick = None
                    elif len(data[start_chunk]) > CHUNKSIZE // 2:
                        mins[start_chunk] = data[start_chunk][0]
                    elif start_chunk > 0 and (
                        start_chunk + 1 == len(data)
                        or len(data[start_chunk - 1]) < len(data[start_chunk + 1])
                    ):
                        if start_chunk + 1 == len(data):
                            self._fenwick_update(-2, len(data[-1]))
                            del self._fenwick[-1]
                        else:
                            self._fenwick = None
                        data[start_chunk - 1].extend(data.pop(start_chunk))
                    else:
                        if stop_chunk + 2 == len(data):
                            self._fenwick_update(-2, len(data[-1]))
                            del self._fenwick[-1]
                        else:
                            self._fenwick = None
                        data[start_chunk].extend(data.pop(start_chunk + 1))
                elif stop_chunk + 2 == len(self._fenwick):
                    self._fenwick_update(start_chunk, start_index - len(data[-2]))
                    del data[-2][start_index:]
                    del data[-1][:stop_index]
                    self._fenwick_update(start_chunk + 1, len(data[-1]) - len_)
                    del self._fenwick[start_chunk + 3:]
                    if len(data[-2]) > CHUNKSIZE // 2 < len(data[-1]):
                        mins[-1] = data[-1][0]
                    else:
                        self._fenwick_update(-2, len(data[-1]))
                        del self._fenwick[-1]
                        data[-2].extend(data.pop())
                        del mins[-1]
                        if len(data) > 1 and len(data[-1]) < CHUNKSIZE // 2:
                            self._fenwick_update(-2, len(data[-1]))
                            del self._fenwick[-1]
                            data[-2].extend(data.pop())
                            del mins[-1]
                else:
                    self._fenwick = None
                    del data[start_chunk][start_index:]
                    del data[start_chunk + 1][:stop_index]
                    if len(data[start_chunk]) > CHUNKSIZE // 2 < len(data[start_chunk + 1]):
                        mins[start_chunk + 1] = data[start_chunk + 1][0]
                    else:
                        data[start_chunk].extend(data.pop(start_chunk + 1))
                        del mins[start_chunk + 1]
                        if len(data) == 1 or len(data[start_chunk]) > CHUNKSIZE // 2:
                            pass
                        elif start_chunk > 0 and (
                            start_chunk + 1 == len(data)
                            or len(data[start_chunk - 1]) < len(data[start_chunk + 1])
                        ):
                            data[start_chunk - 1].extend(data.pop(start_chunk))
                        else:
                            data[start_chunk].extend(data.pop(start_chunk + 1))
                self._len -= len(range_)
            elif len(range_) < self._len // 8:
                for i in reversed(range_):
                    del self[i]
            else:
                for _ in range(1, len(data)):
                    data[0].extend(data.pop(1))
                del data[0][range_.start:range_.stop:range_.step]
                self._len = len(data[0])
                for i in reversed(range(0, len(data[0]), CHUNKSIZE)):
                    data.append(data[0][i : i + CHUNKSIZE])
                    del data[0][i : i + CHUNKSIZE]
                data.reverse()
                del data[-1]
                if len(data) > 1 and len(data[-1]) < CHUNKSIZE // 2:
                    data[-2].extend(data.pop())
                mins[:] = [chunk[0] for chunk in data]
                self._fenwick = None
            return
        index = range(self._len)[index]
        i, j = self._fenwick_index(index)
        del data[i][j]
        self._fenwick_update(i, -1)
        self._len -= 1
        if len(data[i]) == 0:
            del data[i]
            del mins[i]
            if i == len(data):
                del self._fenwick[-1]
            else:
                self._fenwick = None
        elif len(data) == 1 or len(data[i]) > CHUNKSIZE // 2:
            if j == 0:
                mins[i] = data[i][0]
        elif i + 1 == len(data):
            self._fenwick_update(-2, len(data[-1]))
            data[-2].extend(data.pop())
            del self._fenwick[-1]
            del mins[-1]
        elif i > 0 and len(data[i - 1]) < len(data[i + 1]):
            data[i - 1].extend(data.pop(i))
            self._fenwick = None
            del mins[i]
        elif i + 2 == len(data):
            self._fenwick_update(-2, len(data[-1]))
            data[-2].extend(data.pop())
            del self._fenwick[-1]
            del mins[-1]
        else:
            data[i].extend(data.pop(i + 1))
            self._fenwick = None
            mins[i : i + 2] = data[i][:1]

    @classmethod
    def __from_iterable__(cls: Type[Self], iterable: Iterable[T], /) -> Self:
        return cls(iterable)

    @classmethod
    def __from_sorted__(cls: Type[Self], iterable: Iterable[T], /) -> Self:
        data: list[T]
        # Sort the data.
        if iterable is None:
            data = []
        elif isinstance(iterable, list):
            data = iterable
        elif isinstance(iterable, Iterable):
            data = [*iterable]
        else:
            raise TypeError(f"{type(self).__name__} expected an iterable, got {iterable!r}")
        self = cls()
        self._len = len(data)
        self._fenwick = None
        self._data = [data[i : i + CHUNKSIZE] for i in range(0, len(data), CHUNKSIZE)]
        if len(self._data) > 1 and len(self._data[-1]) < CHUNKSIZE // 2:
            self._data[-2].extend(self._data.pop())
            self._mins = data[:-CHUNKSIZE:CHUNKSIZE]
        else:
            self._mins = data[::CHUNKSIZE]
        return self

    @overload
    def __getitem__(self: Self, index: int, /) -> T: ...

    @overload
    def __getitem__(self: Self, index: slice, /) -> Self: ...

    def __getitem__(self, index, /):
        data = self._data
        if isinstance(index, slice):
            range_ = range(self._len)[index]
            if range_.step < 0:
                range_ = range_[::-1]
            if len(range_) == 0:
                return type(self)()
            elif len(range_) == self._len:
                return self.copy()
            elif range_.step == 1 and range_.start == 0:
                return type(self).__from_sorted__(islice(self, range_.stop))
            elif range_.step == 1 and range_.stop == self._len:
                data_ = [*islice(reversed(self), len(range_))]
                data_.reverse()
                return type(self).__from_sorted__(data_)
            elif range_.step == 1:
                start_chunk, start_index = self._fenwick_index(range_.start)
                stop_chunk, stop_index = self._fenwick_index(range_.stop)
                if start_chunk == stop_chunk:
                    return type(self).__from_sorted__(data[start_chunk][start_index:stop_index])
                elif start_index == 0:
                    data_ = [
                        x
                        for i in range(start_chunk, stop_chunk)
                        for x in data[i]
                    ]
                    data_.extend(data[stop_chunk][:stop_index])
                    return type(self).__from_sorted__(data_)
                else:
                    data_ = data[start_chunk][start_index:]
                    for i in range(start_chunk + 1, stop_chunk):
                        data_.extend(data[i])
                    data_.extend(data[stop_chunk][:stop_index])
                    return type(self).__from_sorted__(data_)
            elif len(range_) > self._len // 8:
                return type(self).__from_sorted__([x for i, x in enumerate(self) if i in range_])
            else:
                return type(self).__from_sorted__([self[i] for i in range_])
        index = range(self._len)[index]
        if index < len(data[0]):
            return data[0][index]
        elif index >= self._len - len(data[-1]):
            return data[-1][index - self._len + len(data[-1])]
        else:
            i, j = self._fenwick_index(index)
            return data[i][j]

    def __imul__(self: Self, other: int, /) -> Self:
        try:
            range_ = range(other)
        except TypeError:
            return NotImplemented
        data = self._data
        mins = self._mins
        if self._len == 0:
            pass
        elif len(range_) == 0:
            self.clear()
        elif len(range_) > 1:
            results = [
                x
                for _ in range(len(data))
                for x in reversed(data.pop())
                for _ in range_
            ]
            self._fenwick = None
            self._len = len(results)
            mins[:] = results[::-CHUNKSIZE]
            for i in range(0, self._len, CHUNKSIZE):
                data.append(results[-1:~CHUNKSIZE:-1])
                del results[-CHUNKSIZE:]
            if len(data) > 1 and len(data[-1]) < CHUNKSIZE // 2:
                data[-2].extend(data.pop())
                del mins[-1]
        return self

    def __islice(self: Self, start: int, stop: int, step: int, /) -> Iterator[T]:
        data = self._data
        start_chunk, start_index = self._fenwick_index(start)
        stop_chunk, stop_index = self._fenwick_index(stop - step)
        if step > 0:
            for i in range(start_chunk, stop_chunk):
                chunk = data[i]
                while start_index < len(chunk):
                    yield chunk[start_index]
                    start_index += step
                start_index -= len(chunk)
            chunk = data[stop_chunk]
            for i in range(start_index, stop_index + 1, step):
                yield chunk[i]
        else:
            start_index -= len(data[start_chunk])
            for i in range(start_chunk, stop_chunk, -1):
                chunk = data[i]
                while start_index > -len(chunk):
                    yield chunk[start_index]
                    start_index += step
                start_index += len(chunk)
            chunk = data[stop_chunk]
            stop_index -= len(chunk)
            for i in range(start_index, stop_index - 1, step):
                yield chunk[i]

    def __islice__(self: Self, start: Optional[int], stop: Optional[int], step: Optional[int], /) -> Iterator[T]:
        data = self._data
        range_ = range(self._len)[start:stop:step]
        if len(range_) == self._len:
            return iter(self) if range_.step == 1 else reversed(self)
        elif len(range_) == 0:
            return (self[i] for i in range_)
        elif range_.step == 1 and range_.start == 0:
            return islice(self, range_.stop)
        elif range_.step == 1 and range_.stop == self._len:
            start_fenwick = self._fenwick_index(range_.start)
            if start_fenwick[1] == 0:
                return (x for i in range(start_fenwick[0], len(data)) for x in data[i])
            else:
                return chain(
                    data[start_fenwick[0]][start_fenwick[1]:],
                    (
                        x
                        for i in range(start_fenwick[0] + 1, len(data))
                        for x in data[i]
                    ),
                )
        elif range_.step == 1:
            start_fenwick = self._fenwick_index(range_.start)
            stop_fenwick = self._fenwick_index(range_.stop)
            if start_fenwick[0] == stop_fenwick[0]:
                return iter(data[start_fenwick[0]][start_fenwick[1]:stop_fenwick[1]])
            elif start_fenwick[1] == 0 == stop_fenwick[1]:
                return (
                    x
                    for i in range(start_fenwick[0], stop_fenwick[0])
                    for x in data[i]
                )
            elif start_fenwick[1] == 0:
                return chain(
                    (
                        x
                        for i in range(start_fenwick[0], stop_fenwick[0])
                        for x in data[i]
                    ),
                    data[stop_fenwick[0]][:stop_fenwick[1]],
                )
            elif stop_fenwick[1] == 0:
                return chain(
                    data[start_fenwick[0]][start_fenwick[1]:],
                    (
                        x
                        for i in range(start_fenwick[0] + 1, stop_fenwick[0])
                        for x in data[i]
                    ),
                )
            else:
                return chain(
                    data[start_fenwick[0]][start_fenwick[1]:],
                    (
                        x
                        for i in range(start_fenwick[0] + 1, stop_fenwick[0])
                        for x in data[i]
                    ),
                    data[stop_fenwick[0]][:stop_fenwick[1]],
                )
        elif range_.step == -1 and range_.start + 1 == self._len:
            return islice(reversed(self), len(range_))
        elif range_.step == -1 and range_.stop + 1 == 0:
            start_fenwick = self._fenwick_index(range_.start)
            if start_fenwick[1] + 1 == len(data[start_fenwick[0]]):
                return (x for i in range(start_fenwick[0], -1, -1) for x in reversed(data[i]))
            else:
                return chain(
                    data[start_fenwick[0]][start_fenwick[1]::-1],
                    (
                        x
                        for i in range(start_fenwick[0] - 1, -1, -1)
                        for x in reversed(data[i])
                    ),
                )
        elif range_.step == -1:
            start_fenwick = self._fenwick_index(range_.start)
            stop_fenwick = self._fenwick_index(range_.stop)
            if start_fenwick[0] == stop_fenwick[0]:
                return reversed(data[start_fenwick[0]][start_fenwick[1]:stop_fenwick[1]:-1])
            elif start_fenwick[1] + 1 == len(data[start_fenwick[0]]) and stop_fenwick[1] + 1 == len(data[stop_fenwick[1]]):
                return (
                    x
                    for i in range(start_fenwick[0], stop_fenwick[0], -1)
                    for x in reversed(data[i])
                )
            elif start_fenwick[1] + 1 == len(data[start_fenwick[0]]):
                return chain(
                    (
                        x
                        for i in range(start_fenwick[0], stop_fenwick[0], -1)
                        for x in reversed(data[i])
                    ),
                    data[stop_fenwick[0]][:stop_fenwick[1]:-1],
                )
            elif stop_fenwick[1] + 1 == len(data[stop_fenwick[1]]):
                return chain(
                    data[start_fenwick[0]][start_fenwick[1]::-1],
                    (
                        x
                        for i in range(start_fenwick[0] - 1, stop_fenwick[0], -1)
                        for x in reversed(data[i])
                    ),
                )
            else:
                return chain(
                    data[start_fenwick[0]][start_fenwick[1]::-1],
                    (
                        x
                        for i in range(start_fenwick[0] - 1, stop_fenwick[0], -1)
                        for x in reversed(data[i])
                    ),
                    data[stop_fenwick[0]][:stop_fenwick[1]:-1],
                )
        elif abs(range_.step) < CHUNKSIZE * 2:
            return self.__islice(range_.start, range_.stop, range_.step)
        else:
            return (self[i] for i in range_)

    def __iter__(self: Self, /) -> Iterator[T]:
        return chain.from_iterable(self._data)

    def __len__(self: Self, /) -> int:
        return self._len

    def __mul__(self: Self, other: int, /) -> Self:
        try:
            range_ = range(other)
        except TypeError:
            return NotImplemented
        if len(range_) == 0:
            return type(self).__from_sorted__([])
        elif len(range_) == 1:
            return self.copy()
        else:
            return type(self).__from_sorted__([x for x in self for _ in range_])

    __rmul__ = __mul__

    def __repr__(self: Self, /) -> str:
        if id(self) in reprs_seen:
            return "..."
        elif len(self) == 0:
            return f"{type(self).__name__}()"
        reprs_seen.add(id(self))
        try:
            data = ", ".join([repr(x) for x in self])
            return f"{type(self).__name__}([{data}])"
        finally:
            reprs_seen.remove(id(self))

    def __reversed__(self: Self, /) -> Iterator[T]:
        return (x for chunk in reversed(self._data) for x in reversed(chunk))

    def _fenwick_index(self: Self, index: int, /) -> tuple[int, int]:
        if self._fenwick is None:
            fenwick = [0]
            fenwick.extend(map(len, self._data))
            len_ = len(fenwick)
            for i in range(1, len_):
                j = i + (i & -i)
                if j < len_:
                    fenwick[j] += fenwick[i]
            self._fenwick = fenwick
        else:
            fenwick = self._fenwick
            len_ = len(fenwick)
        i = 0
        j = 2048
        while j < len_:
            j *= 2
        while j > 0:
            if i + j < len_ and fenwick[i + j] <= index:
                i += j
                index -= fenwick[i]
            j //= 2
        return (i, index)

    def _fenwick_update(self: Self, index: int, value: int, /) -> None:
        fenwick = self._fenwick
        if fenwick is None:
            return
        index = range(len(self._data))[index] + 1
        len_ = len(fenwick)
        if index & (index - 1) == 0:
            while index < len_:
                fenwick[index] += value
                index *= 2
        else:
            while index < len_:
                fenwick[index] += value
                index += index & -index

    def add(self: Self, element: T, /) -> None:
        data = self._data
        fenwick = self._fenwick
        mins = self._mins
        if self._len == 0:
            data.append([element])
            self._fenwick = None
            mins.append(element)
        elif element < mins[0]:
            chunk = data[0]
            len2 = len(chunk) // 2
            if len2 > CHUNKSIZE:
                data.insert(1, chunk[len2:])
                mins.insert(1, chunk[len2])
                del chunk[len2:]
                self._fenwick = None
            elif fenwick is not None:
                self._fenwick_update(0, 1)
            chunk.insert(0, element)
            mins[0] = element
        elif element >= mins[-1]:
            chunk = data[-1]
            len2 = len(chunk) // 2
            if len2 > CHUNKSIZE:
                data.append(chunk[len2:])
                mins.append(chunk[len2])
                del chunk[len2:]
                if fenwick is not None:
                    fenwick.append(len(data[-1]))
                    fenwick[-2] -= fenwick[-1]
                    i = len(data)
                    j = i & -i
                    while j > 1:
                        j //= 2
                        fenwick[i] += fenwick[i - j]
            if mins[-1] < element:
                j = bisect(data[-1], element)
                if j > 0 and not (element is not data[-1][j - 1] != element):
                    return
                data[-1].insert(j, element)
                if fenwick is not None:
                    fenwick[-1] += 1
            else:
                j = bisect(chunk, element)
                if j > 0 and not (element is not chunk[j - 1] != element):
                    return
                chunk.insert(j, element)
                if j == 0:
                    mins[-2] = element
                if fenwick is not None:
                    fenwick[-2] += 1
                    if len(data) == 2:
                        fenwick[-1] += 1
        else:
            i = bisect(mins, element, 0, len(mins) - 1)
            chunk = data[i - 1]
            len2 = len(chunk) // 2
            if len2 > CHUNKSIZE:
                data.insert(i, chunk[len2:])
                mins.insert(i, chunk[len2])
                del chunk[len2:]
                self._fenwick = None
                if data[i][0] < element:
                    j = bisect(data[i], element)
                    if j > 0 and not (element is not data[i][j] != element):
                        return
                    data[i].insert(j, element)
                else:
                    j = bisect(chunk, element)
                    if j > 0 and not (element is not chunk[j] != element):
                        return
                    chunk.insert(j, element)
                    if j == 0:
                        mins[i - 1] = element
            else:
                j = bisect(chunk, element)
                if j > 0 and not (element is not chunk[j] != element):
                    return
                chunk.insert(j, element)
                if j == 0:
                    mins[i - 1] = element
                self._fenwick_update(i - 1, 1)
        self._len += 1

    def append(self: Self, element: T, /) -> None:
        data = self._data
        fenwick = self._fenwick
        mins = self._mins
        if self._len == 0:
            data.append([element])
            self._fenwick = None
            mins.append(element)
        elif element < mins[0]:
            chunk = data[0]
            len2 = len(chunk) // 2
            if len2 > CHUNKSIZE:
                data.insert(1, chunk[len2:])
                mins.insert(1, chunk[len2])
                del chunk[len2:]
                self._fenwick = None
            elif fenwick is not None:
                self._fenwick_update(0, 1)
            chunk.insert(0, element)
            mins[0] = element
        elif element >= mins[-1]:
            chunk = data[-1]
            len2 = len(chunk) // 2
            if len2 > CHUNKSIZE:
                data.append(chunk[len2:])
                mins.append(chunk[len2])
                del chunk[len2:]
                if fenwick is not None:
                    fenwick.append(len(data[-1]))
                    fenwick[-2] -= fenwick[-1]
                    i = len(data)
                    j = i & -i
                    while j > 1:
                        j //= 2
                        fenwick[i] += fenwick[i - j]
            if mins[-1] < element:
                insort(data[-1], element)
                if fenwick is not None:
                    fenwick[-1] += 1
            else:
                insort(chunk, element)
                mins[-2] = chunk[0]
                if fenwick is not None:
                    fenwick[-2] += 1
                    if len(data) == 2:
                        fenwick[-1] += 1
        else:
            i = bisect(mins, element, 0, len(mins) - 1)
            chunk = data[i - 1]
            len2 = len(chunk) // 2
            if len2 > CHUNKSIZE:
                data.insert(i, chunk[len2:])
                mins.insert(i, chunk[len2])
                del chunk[len2:]
                self._fenwick = None
                if data[i][0] < element:
                    insort(data[i], element)
                else:
                    insort(chunk, element)
                    mins[i - 1] = chunk[0]
            else:
                insort(chunk, element)
                mins[i - 1] = chunk[0]
                self._fenwick_update(i - 1, 1)
        self._len += 1

    def clear(self: Self, /) -> None:
        self._data.clear()
        self._fenwick = None
        self._len = 0
        self._mins.clear()

    def discard(self: Self, element: T, /) -> None:
        data = self._data
        fenwick = self._fenwick
        mins = self._mins
        if self._len == 0:
            return
        elif self._len == 1:
            if not (element is not mins[0] != element):
                self.clear()
            return
        elif not (mins[0] <= element <= data[-1][-1]):
            return
        elif element < data[0][-1]:
            i = 0
        elif element >= mins[-1]:
            i = len(mins) - 1
        else:
            i = bisect(mins, element, 1, len(mins) - 1) - 1
        chunk = data[i]
        j = bisect(chunk, element) - 1
        if j < 0 or (element is not chunk[j] != element):
            return
        del chunk[j]
        self._len -= 1
        if len(data) == 1 or len(chunk) > CHUNKSIZE // 2:
            if j == 0:
                mins[i] = chunk[0]
            self._fenwick_update(i, -1)
        elif i > 0 and (
            i + 1 == len(data)
            or len(data[i - 1]) < len(data[i + 1])
        ):
            if fenwick is not None and i + 1 == len(data):
                self._fenwick_update(i - 1, len(chunk))
                del fenwick[-1]
            else:
                self._fenwick = None
            data[i - 1].extend(data.pop(i))
            del mins[i]
        else:
            if fenwick is not None and i + 2 == len(data):
                self._fenwick_update(i, len(data[i + 1]) - 1)
                del fenwick[-1]
            else:
                self._fenwick = None
            if j == 0:
                mins[i : i + 2] = chunk[:1]
            chunk.extend(data.pop(i + 1))

    def extend(self: Self, iterable: Iterable[T], /) -> None:
        data = self._data
        mins = self._mins
        if not isinstance(iterable, Iterable):
            raise TypeError(f"extend expected an iterable, got {iterable!r}")
        elif iterable is self:
            self *= 2
        elif isinstance(iterable, (Sized, SupportsLengthHint)) and length_hint(iterable) < self._len // 8:
            for x in iterable:
                self.append(x)
        elif isinstance(iterable, SortedCollection):
            results = [*merge(
                reversed(iterable),
                (x for _ in range(len(data)) for x in reversed(data.pop()))
            )]
            del iterable
            self._fenwick = None
            self._len = len(results)
            mins[:] = results[::-CHUNKSIZE]
            for i in range(0, self._len, CHUNKSIZE):
                data.append(results[-1:~CHUNKSIZE:-1])
                del results[-CHUNKSIZE:]
            if len(data) > 1 and len(data[-1]) < CHUNKSIZE // 2:
                data[-2].extend(data.pop())
                del mins[-1]
        else:
            if not isinstance(iterable, (Sized, SupportsLengthHint)):
                iterable = iter(iterable)
                for i, x in enumerate(iterable):
                    self.append(x)
                    if i >= self._len // 16:
                        break
                else:
                    return
            results = sorted(iterable)
            del iterable
            results.reverse()
            for _ in range(len(data)):
                results.extend(reversed(data.pop()))
            self._fenwick = None
            self._len = len(results)
            results.sort(reverse=True)
            mins[:] = results[::-CHUNKSIZE]
            for i in range(0, self._len, CHUNKSIZE):
                data.append(results[-1:~CHUNKSIZE:-1])
                del results[-CHUNKSIZE:]
            if len(data) > 1 and len(data[-1]) < CHUNKSIZE // 2:
                data[-2].extend(data.pop())
                del mins[-1]
