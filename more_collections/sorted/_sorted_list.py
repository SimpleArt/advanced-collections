from __future__ import annotations
import operator
import sys
from itertools import islice
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

reprs_seen: set[int] = {*()}


class SortedList(SortedMutableSequence[T], Generic[T]):
    _data: list[list[list[T]]]
    _len0: int
    _len1: list[int]
    __rng: Random

    __slots__ = ("_data", "_len0", "_len1", "__rng")

    def __init__(self: SortedList[T], iterable: Optional[Iterable[T]] = None, /) -> None:
        data: list[T]
        # Sort the data.
        if iterable is None:
            data = []
        elif isinstance(iterable, Iterable):
            data = sorted(iterable)  # type: ignore
        else:
            raise TypeError(f"{type(self).__name__} expected an iterable, got {iterable!r}")
        # The chunksize is used to guarantee roughly O(n^(1/3)) worst-case time complexities.
        chunksize = max(750, round(len(data) ** (1/3)))
        self._len0 = len(data)
        # Segment the data from:
        #     data = [0, 1, 2, 3, ...]
        # to a 3D list:
        #     data = [[[0, 1], [2, 3]], [...], ...]
        self._data = [
            [
                data[i2 : i2 + chunksize]
                for i2 in range(i1, min(i1 + chunksize ** 2, len(data)), chunksize)
            ]
            for i1 in range(0, len(data), chunksize ** 2)
        ]
        self._len1 = [chunksize ** 2] * (len(data) // chunksize ** 2)
        if len(data) % (chunksize ** 2) != 0:
            self._len1.append(sum(len(L2) for L2 in self._data[-1]))
        self.__rng = Random()

    def __delitem__(self: SortedList[T], index: Union[int, slice], /) -> None:
        if isinstance(index, slice):
            range_ = range(len(self))[index]
            if range_.step > 0:
                range_ = range_[::-1]
            for i in range_:
                del self[i]
            return
        elif not isinstance(index, SupportsIndex):
            raise TypeError(f"index could not be interpreted as an integer or slice, got {index!r}")
        index = operator.index(index)
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError("index out of range")
        L0 = self._data
        if index < len(self) // 2:
            for i1, (L1, len1) in enumerate(zip(L0, self._len1)):
                if len1 <= index:
                    index -= len1
                else:
                    break
            else:
                assert False, "index out of range, despite being checked"
        else:
            index = len(self) - index - 1
            for i1, (L1, len1) in enumerate(zip(reversed(L0), reversed(self._len1))):
                if len1 <= index:
                    index -= len1
                else:
                    break
            else:
                assert False, "index out of range, despite being checked"
            i1 = len(L0) - i1 - 1
            index = len1 - index - 1
        if index < len1 // 2:
            for i2, L2 in enumerate(L1):
                if len(L2) <= index:
                    index -= len(L2)
                else:
                    break
            else:
                assert False, "index out of range, despite being checked"
        else:
            index = len1 - index - 1
            for i2, L2 in enumerate(reversed(L1)):
                if len(L2) <= index:
                    index -= len(L2)
                else:
                    break
            else:
                assert False, "index out of range, despite being checked"
            i2 = len(L1) - i2 - 1
            index = len(L2) - index - 1
        i3 = index
        # The chunksize is used to guarantee roughly O(n^(1/3)) worst-case time complexities.
        chunksize = max(750, round(len(self) ** (1/3)))
        rng = chunksize * chunksize * self.__rng.random()
        len1 = len(L1) // 2
        len2 = len(L2) // 2
        # Low probability that `[[x], [y]] -> [[x, y]]`.
        if rng < 1 and len(self._data) > 1:
            if i1 == 0 or i1 < len(L0) - 1 and len(L0[i1 - 1]) < len(L0[i1 + 1]):
                self._len1[i1] += self._len1.pop(i1 + 1)
                L1.extend(L0.pop(i1 + 1))
            else:
                L1 = L0[i1 - 1]
                i2 += len(L1)
                self._len1[i1 - 1] += self._len1.pop(i1)
                L1.extend(L0.pop(i1))
        # Medium probability that `[[[x], [y]]] -> [[[x, y]]]`.
        if rng < chunksize:
            if i2 == 0 or i2 < len(L1) - 1 and len(L1[i2 - 1]) < len(L1[i2 + 1]):
                L2.extend(L1.pop(i1 + 1))
            else:
                L2 = L1[i2 - 1]
                i3 += len(L2)
                L2.extend(L1.pop(i2))
        # Delete the indexed item.
        del L2[i3]
        self._len0 -= 1
        self._len1[i1] -= 1

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
                return type(self).from_sorted(self[i] for i in reversed(range_))
            else:
                return type(self).from_sorted(self[i] for i in range_)
        elif not isinstance(index, SupportsIndex):
            raise TypeError(f"index could not be interpreted as an integer or slice, got {index!r}")
        index = operator.index(index)
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError("index out of range")
        if index < len(self) // 2:
            for L1, len1 in zip(self._data, self._len1):
                if len1 <= index:
                    index -= len1
                else:
                    break
            else:
                assert False, "index out of range, despite being checked"
        else:
            index = len(self) - index - 1
            for L1, len1 in zip(reversed(self._data), reversed(self._len1)):
                if len1 <= index:
                    index -= len1
                else:
                    break
            else:
                assert False, "index out of range, despite being checked"
            index = len1 - index - 1
        if index < len1 // 2:
            for L2 in L1:
                if len(L2) <= index:
                    index -= len(L2)
                else:
                    break
            else:
                assert False, "index out of range, despite being checked"
        else:
            index = len1 - index - 1
            for L2 in reversed(L1):
                if len(L2) <= index:
                    index -= len(L2)
                else:
                    break
            else:
                assert False, "index out of range, despite being checked"
            index = len(L2) - index - 1
        return L2[index]

    def __iter__(self: SortedList[T], /) -> SortedIterator[T]:
        return SortedUserIterator(
            x
            for L1 in self._data
            for L2 in L1
            for x in L2
        )

    def __len__(self: SortedList[Any], /) -> int:
        return self._len0

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
            for L1 in reversed(self._data)
            for L2 in reversed(L1)
            for x in reversed(L2)
        )

    def append(self: SortedList[T], value: T, /) -> None:
        if len(self) == 0:
            self._data.append([[value]])
            self._len0 = 1
            self._len1 = [1]
            return
        L0 = self._data
        left = 0
        right = len(L0)
        while left < right:
            middle = (left + right) // 2
            if L0[middle][0][0] > value:  # type: ignore
                right = middle
            else:
                left = middle + 1
        i1 = 0 if left == 0 else left - 1
        L1 = L0[i1]
        left = 0
        right = len(L1)
        while left < right:
            middle = (left + right) // 2
            if L1[middle][0] > value:  # type: ignore
                right = middle
            else:
                left = middle + 1
        i2 = 0 if left == 0 else left - 1
        L2 = L1[i2]
        left = 0
        right = len(L2)
        while left < right:
            middle = (left + right) // 2
            if L2[middle] > value:  # type: ignore
                right = middle
            else:
                left = middle + 1
        i3 = left
        # The chunksize is used to guarantee roughly O(n^(1/3)) worst-case time complexities.
        chunksize = max(750, round(len(self) ** (1/3)))
        rng = chunksize * chunksize * self.__rng.random()
        len1 = len(L1) // 2
        len2 = len(L2) // 2
        if rng < 1:
            self._len1.insert(i1 + 1, self._len1[i1] - len1)
            self._len1[i1] = len1
            L0.insert(i1 + 1, L1[len1:])
            del L1[len1:]
            if i2 >= len1:
                i2 -= len1
                L1 = L0[i1 + 1]
        if rng < chunksize:
            L1.insert(i2 + 1, L2[len2:])
            del L2[len2:]
            if i3 >= len2:
                i3 -= len2
                L2 = L1[i2 + 1]
        L2.insert(i3, value)
        self._len0 += 1
        self._len1[i1] += 1

    def discard(self: SortedList[T], value: T, /) -> None:
        if len(self) == 0:
            return
        L0 = self._data
        left = 0
        right = len(L0)
        while left < right:
            middle = (left + right) // 2
            if L0[middle][0][0] > value:  # type: ignore
                right = middle
            else:
                left = middle + 1
        i1 = 0 if left == 0 else left - 1
        L1 = L0[i1]
        left = 0
        right = len(L1)
        while left < right:
            middle = (left + right) // 2
            if L1[middle][0] > value:  # type: ignore
                right = middle
            else:
                left = middle + 1
        i2 = 0 if left == 0 else left - 1
        L2 = L1[i2]
        left = 0
        right = len(L2)
        while left < right:
            middle = (left + right) // 2
            if L2[middle] > value:  # type: ignore
                right = middle
            else:
                left = middle + 1
        i3 = left - 1
        # Value not found.
        if i3 < 0 or value is not L2[i3] != value:
            return
        # Empty list remaining is removed.
        elif len(self) == 1:
            L0.clear()
            self._len0 = 0
            self._len1.clear()
            return
        elif self._len1[i1] == 1:
            del self._len1[i1]
            self._len0 -= 1
            del self._len1[i1]
            return
        elif len(L2) == 1:
            del L1[i2]
            self._len0 -= 1
            self._len1[i1] -= 1
            return
        # The chunksize is used to guarantee roughly O(n^(1/3)) worst-case time complexities.
        chunksize = max(750, round(len(self) ** (1/3)))
        rng = chunksize * chunksize * self.__rng.random()
        len1 = len(L1) // 2
        len2 = len(L2) // 2
        if rng < 1 and len(self._data) > 1:
            if i1 == 0 or i1 < len(L0) - 1 and len(L0[i1 - 1]) < len(L0[i1 + 1]):
                self._len1[i1] += self._len1.pop(i1 + 1)
                L1.extend(L0.pop(i1 + 1))
            else:
                L1 = L0[i1 - 1]
                i2 += len(L1)
                self._len1[i1 - 1] += self._len1.pop(i1)
                L1.extend(L0.pop(i1))
        if rng < chunksize:
            if i2 == 0 or i2 < len(L1) - 1 and len(L1[i2 - 1]) < len(L1[i2 + 1]):
                L2.extend(L1.pop(i1 + 1))
            else:
                L2 = L1[i2 - 1]
                i3 += len(L2)
                L2.extend(L1.pop(i2))
        del L2[i3]
        self._len0 -= 1
        self._len1[i1] -= 1

    @classmethod
    def from_iterable(cls: Type[SortedList[T]], iterable: Iterable[T], /) -> SortedList[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"{cls.__name__} expected an iterable, got {iterable!r}")
        return cls(iterable)

    @classmethod
    def from_sorted(cls: Type[SortedList[T]], iterable: Iterable[T], /) -> SortedList[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"{cls.__name__} expected an iterable, got {iterable!r}")
        self = cls()
        # The chunksize is used to guarantee roughly O(n^(1/3)) worst-case time complexities.
        chunksize = 750
        if isinstance(iterable, Sized):
            chunksize = max(chunksize, round(len(iterable) ** (1 / 3)))
        if isinstance(iterable, list):
            self._data = [
                [
                    iterable[i2 : i2 + chunksize]
                    for i2 in range(i1, min(i1 + chunksize ** 2, len(iterable)), chunksize)
                ]
                for i1 in range(0, len(iterable), chunksize ** 2)
            ]
        else:
            iterator = iter(iterable)
            self._data = [*iter(lambda: [*iter(lambda: [*islice(iterator, chunksize)], [])], [])]
        self._len1 = [chunksize ** 2] * (len(self._data) - 1)
        if len(self._data) > 0:
            self._len1.append(sum(len(L2) for L2 in self._data[-1]))
        self._len0 = sum(self._len1)
        return self


class SortedKeyList(SortedKeyMutableSequence[T], Generic[T]):
    _data: list[list[list[T]]]
    _len0: int
    _len1: list[int]
    __key: Callable[[T], Any]
    __rng: Random

    __slots__ = ("_data", "_len0", "_len1", "__rng")

    def __init__(self: SortedKeyList[T], iterable: Optional[Iterable[T]] = None, /, *, key: Callable[[T], Any]) -> None:
        data: list[T]
        # Sort the data.
        if iterable is None:
            data = []
        elif isinstance(iterable, Iterable):
            if not callable(key):
                raise TypeError(f"{type(self).__name__} expected a callable key, got {key!r}")
            data = sorted(iterable, key=key)  # type: ignore
        else:
            raise TypeError(f"{type(self).__name__} expected an iterable, got {iterable!r}")
        # The chunksize is used to guarantee roughly O(n^(1/3)) worst-case time complexities.
        chunksize = max(750, round(len(data) ** (1/3)))
        self._len0 = len(data)
        # Segment the data from:
        #     data = [0, 1, 2, 3, ...]
        # to a 3D list:
        #     data = [[[0, 1], [2, 3]], [...], ...]
        self._data = [
            [
                data[i2 : i2 + chunksize]
                for i2 in range(i1, min(i1 + chunksize ** 2, len(data)), chunksize)
            ]
            for i1 in range(0, len(data), chunksize ** 2)
        ]
        self._len1 = [chunksize ** 2] * (len(data) // chunksize ** 2)
        if len(data) % (chunksize ** 2) != 0:
            self._len1.append(sum(len(L2) for L2 in self._data[-1]))
        self.__key = key  # type: ignore
        self.__rng = Random()

    def __delitem__(self: SortedKeyList[T], index: Union[int, slice], /) -> None:
        if isinstance(index, slice):
            range_ = range(len(self))[index]
            if range_.step > 0:
                range_ = range_[::-1]
            for i in range_:
                del self[i]
            return
        elif not isinstance(index, SupportsIndex):
            raise TypeError(f"index could not be interpreted as an integer or slice, got {index!r}")
        index = operator.index(index)
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError("index out of range")
        L0 = self._data
        if index < len(self) // 2:
            for i1, (L1, len1) in enumerate(zip(L0, self._len1)):
                if len1 <= index:
                    index -= len1
                else:
                    break
            else:
                assert False, "index out of range, despite being checked"
        else:
            index = len(self) - index - 1
            for i1, (L1, len1) in enumerate(zip(reversed(L0), reversed(self._len1))):
                if len1 <= index:
                    index -= len1
                else:
                    break
            else:
                assert False, "index out of range, despite being checked"
            i1 = len(L0) - i1 - 1
            index = len1 - index - 1
        if index < len1 // 2:
            for i2, L2 in enumerate(L1):
                if len(L2) <= index:
                    index -= len(L2)
                else:
                    break
            else:
                assert False, "index out of range, despite being checked"
        else:
            index = len1 - index - 1
            for i2, L2 in enumerate(reversed(L1)):
                if len(L2) <= index:
                    index -= len(L2)
                else:
                    break
            else:
                assert False, "index out of range, despite being checked"
            i2 = len(L1) - i2 - 1
            index = len(L2) - index - 1
        i3 = index
        # The chunksize is used to guarantee roughly O(n^(1/3)) worst-case time complexities.
        chunksize = max(750, round(len(self) ** (1/3)))
        rng = chunksize * chunksize * self.__rng.random()
        len1 = len(L1) // 2
        len2 = len(L2) // 2
        # Low probability that `[[x], [y]] -> [[x, y]]`.
        if rng < 1 and len(self._data) > 1:
            if i1 == 0 or i1 < len(L0) - 1 and len(L0[i1 - 1]) < len(L0[i1 + 1]):
                self._len1[i1] += self._len1.pop(i1 + 1)
                L1.extend(L0.pop(i1 + 1))
            else:
                L1 = L0[i1 - 1]
                i2 += len(L1)
                self._len1[i1 - 1] += self._len1.pop(i1)
                L1.extend(L0.pop(i1))
        # Medium probability that `[[[x], [y]]] -> [[[x, y]]]`.
        if rng < chunksize:
            if i2 == 0 or i2 < len(L1) - 1 and len(L1[i2 - 1]) < len(L1[i2 + 1]):
                L2.extend(L1.pop(i1 + 1))
            else:
                L2 = L1[i2 - 1]
                i3 += len(L2)
                L2.extend(L1.pop(i2))
        # Delete the indexed item.
        del L2[i3]
        self._len0 -= 1
        self._len1[i1] -= 1

    @overload
    def __getitem__(self: SortedKeyList[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: SortedKeyList[T], index: slice, /) -> SortedKeyList[T]:
        ...

    def __getitem__(self, index, /):
        if isinstance(index, slice):
            range_ = range(len(self))[index]
            if range_.step < 0:
                return type(self).from_sorted(self[i] for i in reversed(range_))
            else:
                return type(self).from_sorted(self[i] for i in range_)
        elif not isinstance(index, SupportsIndex):
            raise TypeError(f"index could not be interpreted as an integer or slice, got {index!r}")
        index = operator.index(index)
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError("index out of range")
        if index < len(self) // 2:
            for L1, len1 in zip(self._data, self._len1):
                if len1 <= index:
                    index -= len1
                else:
                    break
            else:
                assert False, "index out of range, despite being checked"
        else:
            index = len(self) - index - 1
            for L1, len1 in zip(reversed(self._data), reversed(self._len1)):
                if len1 <= index:
                    index -= len1
                else:
                    break
            else:
                assert False, "index out of range, despite being checked"
            index = len1 - index - 1
        if index < len1 // 2:
            for L2 in L1:
                if len(L2) <= index:
                    index -= len(L2)
                else:
                    break
            else:
                assert False, "index out of range, despite being checked"
        else:
            index = len1 - index - 1
            for L2 in reversed(L1):
                if len(L2) <= index:
                    index -= len(L2)
                else:
                    break
            else:
                assert False, "index out of range, despite being checked"
            index = len(L2) - index - 1
        return L2[index]

    def __iter__(self: SortedKeyList[T], /) -> SortedKeyIterator[T]:
        return SortedKeyUserIterator(
            x
            for L1 in self._data
            for L2 in L1
            for x in L2
        )

    def __len__(self: SortedKeyList[Any], /) -> int:
        return self._len0

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
            for L1 in reversed(self._data)
            for L2 in reversed(L1)
            for x in reversed(L2)
        )

    def append(self: SortedKeyList[T], value: T, /) -> None:
        if len(self) == 0:
            self._data.append([[value]])
            self._len0 = 1
            self._len1 = [1]
            return
        key = self.key
        kv = key(value)
        L0 = self._data
        left = 0
        right = len(L0)
        while left < right:
            middle = (left + right) // 2
            if key(L0[middle][0][0]) > kv:  # type: ignore
                right = middle
            else:
                left = middle + 1
        i1 = 0 if left == 0 else left - 1
        L1 = L0[i1]
        left = 0
        right = len(L1)
        while left < right:
            middle = (left + right) // 2
            if key(L1[middle][0]) > kv:  # type: ignore
                right = middle
            else:
                left = middle + 1
        i2 = 0 if left == 0 else left - 1
        L2 = L1[i2]
        left = 0
        right = len(L2)
        while left < right:
            middle = (left + right) // 2
            if key(L2[middle]) > kv:  # type: ignore
                right = middle
            else:
                left = middle + 1
        i3 = left
        # The chunksize is used to guarantee roughly O(n^(1/3)) worst-case time complexities.
        chunksize = max(750, round(len(self) ** (1/3)))
        rng = chunksize * chunksize * self.__rng.random()
        len1 = len(L1) // 2
        len2 = len(L2) // 2
        if rng < 1:
            self._len1.insert(i1 + 1, self._len1[i1] - len1)
            self._len1[i1] = len1
            L0.insert(i1 + 1, L1[len1:])
            del L1[len1:]
            if i2 >= len1:
                i2 -= len1
                L1 = L0[i1 + 1]
        if rng < chunksize:
            L1.insert(i2 + 1, L2[len2:])
            del L2[len2:]
            if i3 >= len2:
                i3 -= len2
                L2 = L1[i2 + 1]
        L2.insert(i3, value)
        self._len0 += 1
        self._len1[i1] += 1

    def discard(self: SortedKeyList[T], value: T, /) -> None:
        if len(self) == 0:
            return
        key = self.key
        kv = key(value)
        L0 = self._data
        left = 0
        right = len(L0)
        while left < right:
            middle = (left + right) // 2
            if key(L0[middle][0][0]) > kv:  # type: ignore
                right = middle
            else:
                left = middle + 1
        i1 = 0 if left == 0 else left - 1
        L1 = L0[i1]
        left = 0
        right = len(L1)
        while left < right:
            middle = (left + right) // 2
            if key(L1[middle][0]) > kv:  # type: ignore
                right = middle
            else:
                left = middle + 1
        i2 = 0 if left == 0 else left - 1
        L2 = L1[i2]
        left = 0
        right = len(L2)
        while left < right:
            middle = (left + right) // 2
            if key(L2[middle]) > kv:  # type: ignore
                right = middle
            else:
                left = middle + 1
        i3 = left - 1
        # Value not found.
        if i3 < 0 or value is not L2[i3] != value:
            return
        # Empty list remaining is removed.
        elif len(self) == 1:
            L0.clear()
            self._len0 = 0
            self._len1.clear()
            return
        elif self._len1[i1] == 1:
            del self._len1[i1]
            self._len0 -= 1
            del self._len1[i1]
            return
        elif len(L2) == 1:
            del L1[i2]
            self._len0 -= 1
            self._len1[i1] -= 1
            return
        # The chunksize is used to guarantee roughly O(n^(1/3)) worst-case time complexities.
        chunksize = max(750, round(len(self) ** (1/3)))
        rng = chunksize * chunksize * self.__rng.random()
        len1 = len(L1) // 2
        len2 = len(L2) // 2
        if rng < 1 and len(self._data) > 1:
            if i1 == 0 or i1 < len(L0) - 1 and len(L0[i1 - 1]) < len(L0[i1 + 1]):
                self._len1[i1] += self._len1.pop(i1 + 1)
                L1.extend(L0.pop(i1 + 1))
            else:
                L1 = L0[i1 - 1]
                i2 += len(L1)
                self._len1[i1 - 1] += self._len1.pop(i1)
                L1.extend(L0.pop(i1))
        if rng < chunksize:
            if i2 == 0 or i2 < len(L1) - 1 and len(L1[i2 - 1]) < len(L1[i2 + 1]):
                L2.extend(L1.pop(i1 + 1))
            else:
                L2 = L1[i2 - 1]
                i3 += len(L2)
                L2.extend(L1.pop(i2))
        del L2[i3]
        self._len0 -= 1
        self._len1[i1] -= 1

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
        self = cls(key=key)
        chunksize = 750
        if isinstance(iterable, Sized):
            chunksize = max(chunksize, round(len(iterable) ** (1 / 3)))
        if isinstance(iterable, list):
            self._data = [
                [
                    iterable[i2 : i2 + chunksize]
                    for i2 in range(i1, min(i1 + chunksize ** 2, len(iterable)), chunksize)
                ]
                for i1 in range(0, len(iterable), chunksize ** 2)
            ]
        else:
            iterator = iter(iterable)
            self._data = [*iter(lambda: [*iter(lambda: [*islice(iterator, chunksize)], [])], [])]
        self._len1 = [chunksize ** 2] * (len(self._data) - 1)
        if len(self._data) > 0:
            self._len1.append(sum(len(L2) for L2 in self._data[-1]))
        self._len0 = sum(self._len1)
        return self

    @property
    def key(self: SortedKeyList[T], /) -> Callable[[T], Any]:
        return self.__key  # type: ignore
