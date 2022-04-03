from __future__ import annotations
import operator
import sys
from bisect import bisect, insort
from itertools import chain, islice
from random import Random
from typing import Any, Generic, Optional, SupportsIndex, Type, TypeVar, Union, overload

if sys.version_info < (3, 9):
    from typing import Callable, Iterable, Iterator, Sequence, Sized, List as list, Set as set
else:
    from collections.abc import Callable, Iterable, Iterator, Sequence, Sized

from ._abc_iterable import SortedIterator
from ._abc_sequence import SortedMutableSequence
from ._sorted_iterable import SortedUserIterator
from ._abc_key_iterable import SortedKeyIterator
from ._abc_key_sequence import SortedKeyMutableSequence
from ._sorted_key_iterable import SortedKeyUserIterator

T = TypeVar("T")

CHUNKSIZE = 1024
reprs_seen: set[int] = {*()}


class SortedList(SortedMutableSequence[T], Generic[T]):
    _data: list[list[T]]
    _len: int
    _lens: Optional[list[int]]
    _mins: list[T]

    __slots__ = ("_data", "_len", "_lens", "_mins")

    def __init__(self: SortedList[T], iterable: Optional[Iterable[T]] = None, /) -> None:
        data: list[T]
        # Sort the data.
        if iterable is None:
            data = []
        elif isinstance(iterable, Iterable):
            data = sorted(iterable)  # type: ignore
        else:
            raise TypeError(f"{type(self).__name__} expected an iterable, got {iterable!r}")
        self._len = len(data)
        self._lens = None
        # Segment the data from:
        #     data = [0, 1, 2, 3, ...]
        # to a 2D list:
        #     data = [[0, 1], [2, 3], [...], ...]
        self._data = [data[i : i + CHUNKSIZE] for i in range(0, len(data), CHUNKSIZE)]
        self._mins = [L[0] for L in self._data]

    def __contains__(self: SortedList[Any], value: Any, /) -> bool:
        if len(self) == 0:
            return False
        data = self._data
        mins = self._mins
        if value < mins[0]:
            return False
        elif value >= mins[-1]:
            L = data[-1]
        else:
            L = data[bisect(mins, value, 0, len(mins) - 1) - 1]
        i = bisect(L, value) - 1
        return 0 <= i < len(L) and not (value is not L[i] != value)

    def __delitem__(self: SortedList[T], index: Union[int, slice], /) -> None:
        if isinstance(index, slice):
            range_ = range(len(self))[index]
            if len(self) == len(range_):
                self.clear()
                return
            elif len(self) > 8 * len(range_):
                if range_.step > 0:
                    range_ = range_[::-1]
                for i in range_:
                    del self[i]
                return
            if range_.step < 0:
                range_ = range_[::-1]
            self._len -= len(range_)
            if range_.step == 1 and range_.start == 0:
                iterator = islice(self, range_.stop, None)
            elif range_.step == 1 and range_.stop == len(self):
                iterator = islice(self, range_.start)
            else:
                iterator = (x for i, x in enumerate(self) if i not in range_)
            self._data = [*iter(lambda: [*islice(iterator, CHUNKSIZE)], [])]
            self._mins = [L[0] for L in self._data]
            return
        elif not isinstance(index, SupportsIndex):
            raise TypeError(f"index could not be interpreted as an integer or slice, got {index!r}")
        data = self._data
        lens = self._lens
        mins = self._mins
        index = operator.index(index)
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError("index out of range")
        elif index < len(data[0]):
            if len(data[0]) == 1:
                del data[0]
                del mins[0]
                self._lens = None
                self._len -= 1
                return
            del data[0][index]
            if index == 0:
                mins[0] = data[0][0]
            if len(data) > 1 and len(data[0]) < CHUNKSIZE // 2:
                data[0].extend(data.pop(1))
                del mins[1]
                self._lens = None
            else:
                i = 1
                while i < len(lens):
                    lens[i] -= 1
                    i *= 2
            self._len -= 1
            return
        elif index >= len(self) - len(data[-1]):
            if len(data[-1]) == 1:
                del data[-1]
                del lens[-1]
                del mins[-1]
                self._len -= 1
                return
            index += len(data[-1]) - len(self)
            del data[-1][index]
            if index == 0:
                mins[-1] = data[-1][0]
            if len(data) > 1 and len(data[-1]) < CHUNKSIZE // 2:
                data[-2].extend(data.pop(-1))
                del mins[-1]
                del lens[-1]
            else:
                lens[-1] -= 1
            self._len -= 1
            return
        self._ensure_lens()
        lens = self._lens
        i = 0
        j = 2048
        while j < len(lens):
            j *= 2
        while j > 0:
            if i + j < len(lens) and lens[i + j] <= index:
                i += j
                index -= lens[i]
            j //= 2
        L = data[i]
        len2 = len(L) // 2
        del L[index]
        self._len -= 1
        if len(data) < 2 or len2 > CHUNKSIZE // 4:
            mins[i] = L[0]
            i += 1
            while i < len(lens):
                lens[i] -= 1
                i += i & -i
        elif len(data[i - 1]) < len(data[i + 1]):
            data[i - 1].extend(data.pop(i))
            del mins[i]
            self._lens = None
        else:
            L.extend(data.pop(i + 1))
            mins[i] = L[0]
            del mins[i + 1]
            self._lens = None

    @overload
    def __getitem__(self: SortedList[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: SortedList[T], index: slice, /) -> SortedList[T]:
        ...

    def __getitem__(self, index, /):
        if isinstance(index, slice):
            range_ = range(len(self))[index]
            if range_.step < 0:
                range_ = range_[::-1]
            result = type(self)()
            result._len = len(range_)
            if result._len < len(self) // 8:
                result._data = [[self[i] for i in range_[j : j + CHUNKSIZE]] for j in range(0, len(range_), CHUNKSIZE)]
            else:
                iterator = islice(self, result.start, result.stop, result.step)
                result._data = [[*islice(iterator, CHUNKSIZE)] for _ in range(0, len(range_), CHUNKSIZE)]
            result._mins = [L[0] for L in result._data]
            return result
        elif not isinstance(index, SupportsIndex):
            raise TypeError(f"index could not be interpreted as an integer or slice, got {index!r}")
        index = operator.index(index)
        data = self._data
        mins = self._mins
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError("index out of range")
        elif index < len(data[0]):
            return data[0][index]
        elif index >= len(self) - len(data[-1]):
            return data[-1][index - len(self) + len(data[-1])]
        self._ensure_lens()
        lens = self._lens
        i = 0
        j = 2048
        len_lens = len(lens)
        while j < len_lens:
            j *= 2
        while j >= len_lens:
            j //= 2
        while j > 0:
            if i + j < len_lens and lens[i + j] <= index:
                i += j
                index -= lens[i]
            j //= 2
        return data[i][index]

    def __iter__(self: SortedList[T], /) -> SortedIterator[T]:
        return SortedUserIterator(chain.from_iterable(self._data))

    def __len__(self: SortedList[Any], /) -> int:
        return self._len

    def __repr__(self: SortedList[Any], /) -> str:
        if id(self) in reprs_seen:
            return "..."
        reprs_seen.add(id(self))
        try:
            if len(self) == 0:
                return f"{type(self).__name__}()"
            else:
                data = ", ".join([repr(x) for x in self])
                return f"{type(self).__name__}([{data}])"
        finally:
            reprs_seen.remove(id(self))

    def __reversed__(self: SortedList[T], /) -> Iterator[T]:
        return (
            x
            for L in reversed(self._data)
            for x in reversed(L)
        )

    def _ensure_lens(self: SortedList[Any], /) -> None:
        lens = self._lens
        if lens is None:
            lens = [len(L) for L in self._data]
            lens.insert(0, 0)
            for i in range(1, len(lens)):
                j = i + (i & -i)
                if j < len(lens):
                    lens[j] += lens[i]
            self._lens = lens

    def append(self: SortedList[T], value: T, /) -> None:
        if len(self) == 0:
            self._data.append([value])
            self._mins.append(value)
            self._len = 1
            return
        data = self._data
        lens = self._lens
        mins = self._mins
        if value < mins[0]:
            L = data[0]
            len2 = len(L) // 2
            if len2 > CHUNKSIZE:
                data.insert(1, L[len2:])
                mins.insert(1, L[len2])
                del L[len2:]
                self._lens = None
            elif lens is not None:
                i = 1
                while i < len(lens):
                    lens[i] += 1
                    i *= 2
            L.insert(0, value)
            mins[0] = value
        elif value >= mins[-1]:
            L = data[-1]
            len2 = len(L) // 2
            if len2 > CHUNKSIZE:
                data.append(L[len2:])
                mins.append(L[len2])
                del L[len2:]
                if lens is not None:
                    if len(data) == 2:
                        lens.append(len(data[0]) + len(data[1]))
                        lens[0] = len(data[0])
                    else:
                        lens.append(len(data[-1]))
                        lens[-2] -= lens[-1]
                        i = len(data)
                        j = i & -i
                        while j > 1:
                            j //= 2
                            lens[i] += lens[i - j]
                if mins[-1] < value:
                    insort(data[-1], value)
                    if lens is not None:
                        lens[-1] += 1
                else:
                    j = bisect(L, value)
                    L.insert(j, value)
                    if j == 0:
                        mins[-2] = value
                    if lens is not None:
                        lens[-2] += 1
                        if len(data) == 2:
                            lens[-1] += 1
            else:
                j = bisect(L, value)
                L.insert(j, value)
                if j == 0:
                    mins[-1] = value
                if lens is not None:
                    lens[-1] += 1
        else:
            i = bisect(mins, value, 0, len(mins) - 1)
            L = data[i - 1]
            len2 = len(L) // 2
            if len2 > CHUNKSIZE:
                data.insert(i, L[len2:])
                mins.insert(i, L[len2])
                del L[len2:]
                if data[i][0] < value:
                    insort(data[i], value)
                else:
                    j = bisect(L, value)
                    L.insert(j, value)
                    if j == 0:
                        mins[i - 1] = value
                self._lens = None
            else:
                j = bisect(L, value)
                L.insert(j, value)
                if j == 0:
                    mins[i - 1] = value
                if lens is not None:
                    while i < len(lens):
                        lens[i] += 1
                        i += i & -i
        self._len += 1

    def clear(self: SortedList[Any], /) -> None:
        self._len = 0
        self._lens = None
        self._data.clear()
        self._mins.clear()

    def discard(self: SortedList[T], value: T, /) -> None:
        if len(self) == 0:
            return
        data = self._data
        lens = self._lens
        mins = self._mins
        if not mins[0] <= value <= data[-1][-1]:
            return
        elif value >= mins[-1]:
            i = len(mins) - 1
        else:
            i = bisect(mins, value, 1, len(mins) - 1) - 1
        L = data[i]
        if len(L) == 1:
            if not (value is not L[0] != value):
                del data[i]
                del mins[i]
                self._len -= 1
                if lens is not None:
                    if i == len(mins) - 1:
                        del lens[-1]
                    else:
                        self._lens = None
            return
        j = bisect(L, value) - 1
        if not 0 <= j < len(L) or value is not L[j] != value:
            return
        del L[j]
        self._len -= 1
        if len(data) < 2 or len(L) > CHUNKSIZE // 2:
            if j == 0:
                mins[i] = L[0]
            if lens is not None:
                j = i + 1
                while j < len(lens):
                    lens[j] -= 1
                    j += j & -j
        elif i > 0 and (i == len(data) - 1 or len(data[i - 1]) < len(data[i + 1])):
            data[i - 1].extend(data.pop(i))
            del mins[i]
            self._lens = None
        else:
            if j == 0:
                mins[i] = L[0]
            L.extend(data.pop(i + 1))
            del mins[i + 1]
            self._lens = None

    def extend(self: SortedList[T], iterable: Iterable[T], /) -> None:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"extend expected an iterable, got {iterable!r}")
        sorted_data = sorted(iterable)  # type: ignore
        if len(sorted_data) > len(self) // 8:
            if len(self) > 0:
                sorted_data.extend(self)
                sorted_data.sort()  # type: ignore
            self._data = [sorted_data[i : i + CHUNKSIZE] for i in range(0, len(sorted_data), CHUNKSIZE)]
            self._len = len(sorted_data)
            self._lens = None
            self._mins = [L[0] for L in self._data]
        else:
            for value in sorted_data:
                self.append(value)

    @classmethod
    def from_iterable(cls: Type[SortedList[T]], iterable: Iterable[T], /) -> SortedList[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"{cls.__name__} expected an iterable, got {iterable!r}")
        return cls(iterable)

    @classmethod
    def from_sorted(cls: Type[SortedList[T]], iterable: Iterable[T], /) -> SortedList[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"{cls.__name__} expected an iterable, got {iterable!r}")
        self = cls(iterable)


class SortedKeyList(SortedKeyMutableSequence[T], Generic[T]):
    __key: Callable[[T], Any]
    _data: list[list[T]]
    _len: int
    _lens: Optional[list[int]]
    _mins: list[Any]

    __slots__ = ("__key", "_data", "_len", "_lens", "_mins")

    def __init__(self: SortedKeyList[T], iterable: Optional[Iterable[T]] = None, /, *, key: Callable[[T], Any]) -> None:
        data: list[T]
        # Sort the data.
        if iterable is None:
            if not callable(key):
                raise TypeError(f"{type(self).__name__} expected a callable key, got {key!r}")
            data = []
        elif isinstance(iterable, Iterable):
            if not callable(key):
                raise TypeError(f"{type(self).__name__} expected a callable key, got {key!r}")
            data = sorted(iterable, key=key)  # type: ignore
        else:
            raise TypeError(f"{type(self).__name__} expected an iterable, got {iterable!r}")
        self._len = len(data)
        self._lens = None
        # Segment the data from:
        #     data = [0, 1, 2, 3, ...]
        # to a 2D list:
        #     data = [[0, 1], [2, 3], [...], ...]
        self._data = [data[i : i + CHUNKSIZE] for i in range(0, len(data), CHUNKSIZE)]
        self._mins = [key(L[0]) for L in self._data]
        self.__key = key  # type: ignore

    def __contains__(self: SortedKeyList[Any], value: Any, /) -> bool:
        if len(self) == 0:
            return False
        data = self._data
        mins = self._mins
        key = self.__key
        kv = key(value)
        if kv < key(mins[0]):
            return False
        elif kv >= key(mins[-1]):
            L = data[-1]
        else:
            L = data[bisect(mins, kv, 0, len(mins) - 1, key=key) - 1]
        i = bisect(L, kv, key=key) - 1
        return 0 <= i < len(L) and not (value is not L[i] != value)

    def __delitem__(self: SortedKeyList[T], index: Union[int, slice], /) -> None:
        key = self.__key
        if isinstance(index, slice):
            range_ = range(len(self))[index]
            if len(self) == len(range_):
                self.clear()
                return
            elif len(self) > 8 * len(range_):
                if range_.step > 0:
                    range_ = range_[::-1]
                for i in range_:
                    del self[i]
                return
            if range_.step < 0:
                range_ = range_[::-1]
            self._len -= len(range_)
            if range_.step == 1 and range_.start == 0:
                iterator = islice(self, range_.stop, None)
            elif range_.step == 1 and range_.stop == len(self):
                iterator = islice(self, range_.start)
            else:
                iterator = (x for i, x in enumerate(self) if i not in range_)
            self._data = [*iter(lambda: [*islice(iterator, CHUNKSIZE)], [])]
            self._mins = [key(L[0]) for L in self._data]
            return
        elif not isinstance(index, SupportsIndex):
            raise TypeError(f"index could not be interpreted as an integer or slice, got {index!r}")
        data = self._data
        lens = self._lens
        mins = self._mins
        index = operator.index(index)
        if index < 0:
            index += len(self)
        elif not 0 <= index < len(self):
            raise IndexError("index out of range")
        elif index < len(data[0]):
            if len(data[0]) == 1:
                del data[0]
                del mins[0]
                self._lens = None
                self._len -= 1
                return
            del data[0][index]
            if index == 0:
                mins[0] = key(data[0][0])
            if len(data) > 1 and len(data[0]) < CHUNKSIZE // 2:
                data[0].extend(data.pop(1))
                del mins[1]
                self._lens = None
            else:
                i = 1
                while i < len(lens):
                    lens[i] -= 1
                    i *= 2
            self._len -= 1
            return
        elif index >= len(self) - len(data[-1]):
            if len(data[-1]) == 1:
                del data[-1]
                del lens[-1]
                del mins[-1]
                self._len -= 1
                return
            index += len(data[-1]) - len(self)
            del data[-1][index]
            if index == 0:
                mins[-1] = key(data[-1][0])
            if len(data) > 1 and len(data[-1]) < CHUNKSIZE // 2:
                data[-2].extend(data.pop(-1))
                del mins[-1]
                del lens[-1]
            else:
                lens[-1] -= 1
            self._len -= 1
            return
        self._ensure_lens()
        lens = self._lens
        i = 0
        j = 2048
        while j < len(lens):
            j *= 2
        while j > 0:
            if i + j < len(lens) and lens[i + j] <= index:
                i += j
                index -= lens[i]
            j //= 2
        L = data[i]
        len2 = len(L) // 2
        del L[index]
        self._len -= 1
        if len(data) < 2 or len2 > CHUNKSIZE // 4:
            mins[i] = key(L[0])
            i += 1
            while i < len(lens):
                lens[i] -= 1
                i += i & -i
        elif len(data[i - 1]) < len(data[i + 1]):
            data[i - 1].extend(data.pop(i))
            del mins[i]
            self._lens = None
        else:
            L.extend(data.pop(i + 1))
            mins[i] = key(L[0])
            del mins[i + 1]
            self._lens = None

    @overload
    def __getitem__(self: SortedKeyList[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: SortedKeyList[T], index: slice, /) -> SortedKeyList[T]:
        ...

    def __getitem__(self, index, /):
        key = self.__key
        if isinstance(index, slice):
            range_ = range(len(self))[index]
            if range_.step < 0:
                range_ = range_[::-1]
            result = type(self)(key=key)
            result._len = len(range_)
            if result._len < len(self) // 8:
                result._data = [[self[i] for i in range_[j : j + CHUNKSIZE]] for j in range(0, len(range_), CHUNKSIZE)]
            else:
                iterator = islice(self, result.start, result.stop, result.step)
                result._data = [[*islice(iterator, CHUNKSIZE)] for _ in range(0, len(range_), CHUNKSIZE)]
            result._mins = [key(L[0]) for L in result._data]
            return result
        elif not isinstance(index, SupportsIndex):
            raise TypeError(f"index could not be interpreted as an integer or slice, got {index!r}")
        index = operator.index(index)
        data = self._data
        mins = self._mins
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError("index out of range")
        elif index < len(data[0]):
            return data[0][index]
        elif index >= len(self) - len(data[-1]):
            return data[-1][index - len(self) + len(data[-1])]
        self._ensure_lens()
        lens = self._lens
        i = 0
        j = 2048
        len_lens = len(lens)
        while j < len_lens:
            j *= 2
        while j >= len_lens:
            j //= 2
        while j > 0:
            if i + j < len_lens and lens[i + j] <= index:
                i += j
                index -= lens[i]
            j //= 2
        return data[i][index]

    def __iter__(self: SortedKeyList[T], /) -> SortedKeyIterator[T]:
        return SortedKeyUserIterator(chain.from_iterable(self._data))

    def __len__(self: SortedKeyList[Any], /) -> int:
        return self._len

    def __repr__(self: SortedKeyList[Any], /) -> str:
        if id(self) in reprs_seen:
            return "..."
        reprs_seen.add(id(self))
        try:
            if len(self) == 0:
                return f"{type(self).__name__}(key={self.key!r})"
            else:
                data = ", ".join([repr(x) for x in self])
                return f"{type(self).__name__}([{data}], key={self.key!r})"
        finally:
            reprs_seen.remove(id(self))

    def __reversed__(self: SortedKeyList[T], /) -> Iterator[T]:
        return (
            x
            for L in reversed(self._data)
            for x in reversed(L)
        )

    def _ensure_lens(self: SortedKeyList[Any], /) -> None:
        lens = self._lens
        if lens is None:
            lens = [len(L) for L in self._data]
            lens.insert(0, 0)
            for i in range(1, len(lens)):
                j = i + (i & -i)
                if j < len(lens):
                    lens[j] += lens[i]
            self._lens = lens

    def append(self: SortedKeyList[T], value: T, /) -> None:
        data = self._data
        lens = self._lens
        mins = self._mins
        key = self.__key
        kv = key(value)
        if len(self) == 0:
            self._data.append([value])
            self._mins.append(kv)
            self._len = 1
            return
        if kv < mins[0]:
            L = data[0]
            len2 = len(L) // 2
            if len2 > CHUNKSIZE:
                data.insert(1, L[len2:])
                mins.insert(1, key(L[len2]))
                del L[len2:]
                self._lens = None
            elif lens is not None:
                i = 1
                while i < len(lens):
                    lens[i] += 1
                    i *= 2
            L.insert(0, value)
            mins[0] = kv
        elif kv >= mins[-1]:
            L = data[-1]
            len2 = len(L) // 2
            if len2 > CHUNKSIZE:
                data.append(L[len2:])
                mins.append(key(L[len2]))
                del L[len2:]
                if lens is not None:
                    if len(data) == 2:
                        lens.append(len(data[0]) + len(data[1]))
                        lens[0] = len(data[0])
                    else:
                        lens.append(len(data[-1]))
                        lens[-2] -= lens[-1]
                        i = len(data)
                        j = i & -i
                        while j > 1:
                            j //= 2
                            lens[i] += lens[i - j]
                if mins[-1] < kv:
                    insort(data[-1], value, key=key)
                    if lens is not None:
                        lens[-1] += 1
                else:
                    j = bisect(L, kv, key=key)
                    L.insert(j, value)
                    if j == 0:
                        mins[-2] = kv
                    if lens is not None:
                        lens[-2] += 1
                        if len(data) == 2:
                            lens[-1] += 1
            else:
                j = bisect(L, kv, key=key)
                L.insert(j, value)
                if j == 0:
                    mins[-1] = kv
                if lens is not None:
                    lens[-1] += 1
        else:
            i = bisect(mins, kv, 0, len(mins) - 1)
            L = data[i - 1]
            len2 = len(L) // 2
            if len2 > CHUNKSIZE:
                data.insert(i, L[len2:])
                mins.insert(i, key(L[len2]))
                del L[len2:]
                if data[i][0] < value:
                    insort(data[i], value, key=key)
                else:
                    j = bisect(L, kv, key=key)
                    L.insert(j, value)
                    if j == 0:
                        mins[i - 1] = kv
                self._lens = None
            else:
                j = bisect(L, kv, key=key)
                L.insert(j, value)
                if j == 0:
                    mins[i - 1] = kv
                if lens is not None:
                    while i < len(lens):
                        lens[i] += 1
                        i += i & -i
        self._len += 1

    def clear(self: SortedKeyList[Any], /) -> None:
        self._len = 0
        self._lens = None
        self._data.clear()
        self._mins.clear()

    def discard(self: SortedKeyList[T], value: T, /) -> None:
        if len(self) == 0:
            return
        data = self._data
        lens = self._lens
        mins = self._mins
        key = self.__key
        kv = key(value)
        if not mins[0] <= kv <= key(data[-1][-1]):
            return
        elif kv >= mins[-1]:
            i = len(mins) - 1
        else:
            i = bisect(mins, kv, 1, len(mins) - 1) - 1
        L = data[i]
        if len(L) == 1:
            if not (value is not L[0] != value):
                del data[i]
                del mins[i]
                self._len -= 1
                if lens is not None:
                    if i == len(mins) - 1:
                        del lens[-1]
                    else:
                        self._lens = None
            return
        j = bisect(L, kv, key=key) - 1
        if not 0 <= j < len(L) or value is not L[j] != value:
            return
        del L[j]
        self._len -= 1
        if len(data) < 2 or len(L) > CHUNKSIZE // 2:
            if j == 0:
                mins[i] = key(L[0])
            if lens is not None:
                j = i + 1
                while j < len(lens):
                    lens[j] -= 1
                    j += j & -j
        elif i > 0 and (i == len(data) - 1 or len(data[i - 1]) < len(data[i + 1])):
            data[i - 1].extend(data.pop(i))
            del mins[i]
            self._lens = None
        else:
            if j == 0:
                mins[i] = key(L[0])
            L.extend(data.pop(i + 1))
            del mins[i + 1]
            self._lens = None

    def extend(self: SortedKeyList[T], iterable: Iterable[T], /) -> None:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"extend expected an iterable, got {iterable!r}")
        key = self.__key
        sorted_data = sorted(iterable, key=key)  # type: ignore
        if len(sorted_data) > len(self) // 8:
            if len(self) > 0:
                sorted_data.extend(self)
                sorted_data.sort(key=key)  # type: ignore
            self._data = [sorted_data[i : i + CHUNKSIZE] for i in range(0, len(sorted_data), CHUNKSIZE)]
            self._len = len(sorted_data)
            self._lens = None
            self._mins = [key(L[0]) for L in self._data]
        else:
            for value in sorted_data:
                self.append(value)

    @classmethod
    def from_iterable(cls: Type[SortedKeyList[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeyList[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"{cls.__name__} expected an iterable, got {iterable!r}")
        elif not callable(key):
            raise TypeError(f"{cls.__name__} expected a callable key, got {key!r}")
        return cls(iterable, key=key)

    @classmethod
    def from_sorted(cls: Type[SortedKeyList[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeyList[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"{cls.__name__} expected an iterable, got {iterable!r}")
        elif not callable(key):
            raise TypeError(f"{cls.__name__} expected a callable key, got {key!r}")
        return cls(iterable, key=key)

    @property
    def key(self: SortedKeyList[T], /) -> Callable[[T], Any]:
        return self.__key  # type: ignore
