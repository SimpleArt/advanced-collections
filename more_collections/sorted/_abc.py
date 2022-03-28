"""
Sorted containers are structurally equivalent to their unsorted
counterparts. As such, sorted classes are nominally typed to create
distinction.
"""
from __future__ import annotations
import collections.abc
import operator
import sys
import typing
from abc import ABC, abstractmethod
from bisect import bisect_left, bisect_right
from copy import copy, deepcopy
from itertools import chain
from typing import Any, Callable, Generic, Literal, Optional, Protocol, SupportsIndex, Tuple, Type, TypeVar, Union, cast, overload

if sys.version_info < (3, 9):
    from typing import (
        AbstractSet,
        ItemsView,
        Iterable,
        Iterator,
        KeysView,
        Mapping,
        MappingView,
        MutableMapping,
        MutableSequence,
        MutableSet,
        Sequence,
        ValuesView,
    )
else:
    from collections.abc import (
        ItemsView,
        Iterable,
        Iterator,
        KeysView,
        Mapping,
        MappingView,
        MutableMapping,
        MutableSequence,
        MutableSet,
        Sequence,
        Set as AbstractSet,
        ValuesView,
    )

__all__ = [
    "SortedIterable",
    "SortedIterator",
    "SortedSequence",
    "SortedMutableSequence",
    "SortedSet",
    "SortedMutableSet",
    "SortedMappingView",
    "SortedItemsView",
    "SortedKeysView",
    "SortedValuesView",
    "SortedMapping",
    "SortedMutableMapping",
    "SortedKeyIterable",
    "SortedKeyIterator",
    "SortedKeySequence",
    "SortedKeyMutableSequence",
    "SortedKeySet",
    "SortedKeyMutableSet",
]


class SupportsRichComparison(Protocol):

    def __eq__(self: SupportsRichComparison, other: Any, /) -> bool:
        ...

    def __ge__(self: SupportsRichComparison, other: Any, /) -> bool:
        ...

    def __gt__(self: SupportsRichComparison, other: Any, /) -> bool:
        ...

    def __lt__(self: SupportsRichComparison, other: Any, /) -> bool:
        ...

    def __le__(self: SupportsRichComparison, other: Any, /) -> bool:
        ...

    def __ne__(self: SupportsRichComparison, other: Any, /) -> bool:
        ...


Self = TypeVar("Self")

T = TypeVar("T")
S = TypeVar("S")
T1 = TypeVar("T1")
T2 = TypeVar("T2")
T3 = TypeVar("T3")
T4 = TypeVar("T4")
T5 = TypeVar("T5")
KT = TypeVar("KT")
VT = TypeVar("VT")
T_co = TypeVar("T_co", covariant=True)
KT_co = TypeVar("KT_co", covariant=True)
VT_co = TypeVar("VT_co", covariant=True)

reprs_seen: typing.Set[int] = set()


class SortedIterable(Iterable[T], ABC, Generic[T]):

    __slots__ = ()

    @abstractmethod
    def __iter__(self: SortedIterable[T], /) -> SortedIterator[T]:
        raise NotImplementedError("__iter__ is a required method for sorted iterables")


class SortedIterator(Iterator[T], SortedIterable[T], ABC, Generic[T]):

    __slots__ = ()

    def __iter__(self: SortedIterator[T], /) -> SortedIterator[T]:
        return self

    @abstractmethod
    def __next__(self: SortedIterator[T], /) -> T:
        raise NotImplementedError("__next__ is a required method for sorted iterators")


class SortedKeyIterable(Iterable[T], ABC, Generic[T]):

    __slots__ = ()

    @abstractmethod
    def __iter__(self: SortedKeyIterable[T], /) -> SortedKeyIterator[T]:
        raise NotImplementedError("__iter__ is a required method for sorted key iterables")


class SortedKeyIterator(Iterator[T], SortedKeyIterable[T], ABC, Generic[T]):

    __slots__ = ()

    def __iter__(self: SortedKeyIterator[T], /) -> SortedKeyIterator[T]:
        return self

    @abstractmethod
    def __next__(self: SortedKeyIterator[T], /) -> T:
        raise NotImplementedError("__next__ is a required method for sorted key iterators")


class SortedConstructor(SortedIterable[T], ABC, Generic[T]):

    def __repr__(self: SortedConstructor[Any], /) -> str:
        if id(self) in reprs_seen:
            return "..."
        reprs_seen.add(id(self))
        try:
            cls = type(self)
            data = ", ".join([repr(x) for x in self])
            return f"{cls.__name__}.from_iterable([{data}])"
        finally:
            reprs_seen.remove(id(self))

    @classmethod
    def from_iterable(cls: Type[SortedConstructor[T]], iterable: Iterable[T], /) -> SortedConstructor[T]:
        if isinstance(iterable, Iterable):
            return cls.from_sorted(sorted(iterable))  # type: ignore
        else:
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")

    @abstractmethod
    @classmethod
    def from_sorted(cls: Type[SortedConstructor[T]], iterable: Iterable[T], /) -> SortedConstructor[T]:
        raise NotImplementedError("from_sorted is a required method for sorted constructors")


class SortedKeyConstructor(SortedKeyIterable[T], ABC, Generic[T]):

    def __repr__(self: SortedKeyConstructor[Any], /) -> str:
        if id(self) in reprs_seen:
            return "..."
        reprs_seen.add(id(self))
        try:
            cls = type(self)
            data = ", ".join([repr(x) for x in self])
            return f"{cls.__name__}.from_iterable([{data}], key={self.key!r})"
        finally:
            reprs_seen.remove(id(self))

    @classmethod
    def from_iterable(cls: Type[SortedKeyConstructor[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeyConstructor[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")
        elif not callable(key):
            raise TypeError(f"key expects a callable, got {key!r}")
        else:
            return cls.from_sorted(sorted(iterable, key=key), key)

    @abstractmethod
    @classmethod
    def from_sorted(cls: Type[SortedKeyConstructor[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeyConstructor[T]:
        raise NotImplementedError("from_sorted is a required method for sorted key constructors")

    @property
    @abstractmethod
    def key(self: SortedKeyConstructor[T], /) -> Callable[[T], Any]:
        raise NotImplementedError("key is a required property for sorted key sequences")


class SortedSequence(Sequence[T], SortedConstructor[T], ABC, Generic[T]):

    __slots__ = ()

    def __contains__(self: SortedSequence[Any], value: Any, /) -> bool:
        i = bisect_left(self, value)
        return 0 <= i < len(self) and not (value is not self[i] != value)

    def __copy__(self: Self, /) -> Self:
        return type(self).from_sorted(self)

    def __deepcopy__(self: Self, /) -> Self:
        return type(self).from_sorted(deepcopy(x) for x in self)

    @overload
    def __getitem__(self: SortedSequence[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: SortedSequence[T], index: slice, /) -> Sequence[T]:
        ...

    @abstractmethod
    def __getitem__(self, index, /):
        raise NotImplementedError("__getitem__ is a required method for sorted sequences")

    @abstractmethod
    def __iter__(self: SortedSequence[T], /) -> SortedIterator[T]:
        raise NotImplementedError("__iter__ is a required method for sorted sequences")

    @abstractmethod
    def __len__(self: SortedSequence[Any], /) -> int:
        raise NotImplementedError("__len__ is a required method for sorted sequences")

    @abstractmethod
    def __reversed__(self: SortedSequence[T], /) -> Iterator[T]:
        raise NotImplementedError("__reversed__ is a required method for sorted sequences")

    def copy(self: Self, /) -> Self:
        return copy(self)

    def count(self: SortedSequence[Any], value: Any, /) -> int:
        hi = bisect_right(self, value)
        lo = bisect_left(self, value, 0, hi)
        return hi - lo

    @classmethod
    def from_iterable(cls: Type[SortedSequence[T]], iterable: Iterable[T], /) -> SortedSequence[T]:
        if isinstance(iterable, Iterable):
            return cls.from_sorted(sorted(iterable))  # type: ignore
        else:
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")

    @classmethod
    def from_sorted(cls: Type[SortedSequence[T]], iterable: Iterable[T], /) -> SortedSequence[T]:
        if isinstance(iterable, Iterable):
            import more_collections.sorted as mcs
            return mcs.SortedList(iterable)
        else:
            raise TypeError(f"from_sorted expects an iterable, got {iterable!r}")

    def index(self: SortedSequence[Any], value: Any, start: int = 0, stop: Optional[int] = None, /) -> int:
        i = bisect_left(self, value, start, stop)
        if not 0 <= i < len(self) or value is not self[i] != value:
            raise ValueError(f"{value!r} is not in the sorted sequence")
        else:
            return i


class SortedKeySequence(Sequence[T], SortedKeyConstructor[T], ABC, Generic[T]):

    __slots__ = ()

    def __contains__(self: SortedSequence[Any], value: Any, /) -> bool:
        i = bisect_left(self, value, key=self.key)
        return 0 <= i < len(self) and not (value is not self[i] != value)

    def __copy__(self: Self, /) -> Self:
        return type(self).from_sorted(self, self.key)

    def __deepcopy__(self: Self, /) -> Self:
        return type(self).from_sorted((deepcopy(x) for x in self), self.key)

    @overload
    def __getitem__(self: SortedKeySequence[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: SortedKeySequence[T], index: slice, /) -> Sequence[T]:
        ...

    @abstractmethod
    def __getitem__(self, index, /):
        raise NotImplementedError("__getitem__ is a required method for sorted key sequences")

    @abstractmethod
    def __iter__(self: SortedKeySequence[T], /) -> SortedKeyIterator[T]:
        raise NotImplementedError("__iter__ is a required method for sorted key sequences")

    @abstractmethod
    def __len__(self: SortedKeySequence[Any], /) -> int:
        raise NotImplementedError("__len__ is a required method for sorted key sequences")

    @abstractmethod
    def __reversed__(self: SortedKeySequence[T], /) -> Iterator[T]:
        raise NotImplementedError("__reversed__ is a required method for sorted key sequences")

    def copy(self: Self, /) -> Self:
        return copy(self)

    def count(self: SortedKeySequence[Any], value: Any, /) -> int:
        hi = bisect_right(self, value, key=self.key)
        lo = bisect_left(self, value, 0, hi, key=self.key)
        return hi - lo

    @classmethod
    def from_iterable(cls: Type[SortedKeySequence[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeySequence[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")
        elif not callable(key):
            raise TypeError(f"key expects a callable, got {key!r}")
        else:
            return cls.from_sorted(sorted(iterable, key=key), key)

    @classmethod
    def from_sorted(cls: Type[SortedKeySequence[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeySequence[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"from_sorted expects an iterable, got {iterable!r}")
        elif not callable(key):
            raise TypeError(f"key expects a callable, got {key!r}")
        else:
            import more_collections.sorted as mcs
            return mcs.SortedKeyList.from_sorted(iterable, key)

    def index(self: SortedKeySequence[Any], value: Any, start: int = 0, stop: Optional[int] = None, /) -> int:
        i = bisect_left(self, value, start, stop, key=self.key)
        if not 0 <= i < len(self) or value is not self[i] != value:
            raise ValueError(f"{value!r} is not in the sorted sequence")
        else:
            return i

    @property
    @abstractmethod
    def key(self: SortedKeySequence[T], /) -> Callable[[T], Any]:
        raise NotImplementedError("key is a required property for sorted key sequences")


class SortedMutableSequence(MutableSequence[T], SortedSequence[T], ABC, Generic[T]):

    __slots__ = ()

    @abstractmethod
    def __delitem__(self: SortedMutableSequence[Any], index: Union[int, slice], /) -> None:
        raise NotImplementedError("__delitem__ is a required method for sorted mutable sequences")

    @overload
    def __getitem__(self: SortedMutableSequence[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: SortedMutableSequence[T], index: slice, /) -> MutableSequence[T]:
        ...

    @abstractmethod
    def __getitem__(self, index, /):
        raise NotImplementedError("__getitem__ is a required method for sorted mutable sequences")

    @abstractmethod
    def __iter__(self: SortedMutableSequence[T], /) -> SortedIterator[T]:
        raise NotImplementedError("__iter__ is a required method for sorted mutable sequences")

    @abstractmethod
    def __len__(self: SortedMutableSequence[Any], /) -> int:
        raise NotImplementedError("__len__ is a required method for sorted mutable sequences")

    @abstractmethod
    def __reversed__(self: SortedMutableSequence[T], /) -> Iterator[T]:
        raise NotImplementedError("__reversed__ is a required method for sorted mutable sequences")

    def __setitem__(self: SortedMutableSequence[T], index: Union[int, slice], value: Union[T, Iterable[T]], /) -> None:
        raise NotImplementedError("__setitem__ is not usable for sorted mutable sequences")

    @abstractmethod
    def append(self: SortedMutableSequence[T], value: T, /) -> None:
        raise NotImplementedError("append is a required method for sorted mutable sequences")

    @classmethod
    def from_iterable(cls: Type[SortedMutableSequence[T]], iterable: Iterable[T], /) -> SortedMutableSequence[T]:
        if isinstance(iterable, Iterable):
            return cls.from_sorted(sorted(iterable))  # type: ignore
        else:
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")

    @classmethod
    def from_sorted(cls: Type[SortedMutableSequence[T]], iterable: Iterable[T], /) -> SortedMutableSequence[T]:
        if isinstance(iterable, Iterable):
            import more_collections.sorted as mcs
            return mcs.SortedList(iterable)
        else:
            raise TypeError(f"from_sorted expects an iterable, got {iterable!r}")

    def insert(self: SortedMutableSequence[T], index: int, value: T, /) -> None:
        raise NotImplementedError("insert is not usable for sorted mutable sequences")

    def reverse(self: SortedMutableSequence[Any], /) -> None:
        raise NotImplementedError("reverse is not usable for sorted mutable sequences")


class SortedKeyMutableSequence(MutableSequence[T], SortedKeySequence[T], ABC, Generic[T]):

    __slots__ = ()

    @abstractmethod
    def __delitem__(self: SortedKeyMutableSequence[Any], index: Union[int, slice], /) -> None:
        raise NotImplementedError("__delitem__ is a required method for sorted key mutable sequences")

    @overload
    def __getitem__(self: SortedKeyMutableSequence[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: SortedKeyMutableSequence[T], index: slice, /) -> MutableSequence[T]:
        ...

    @abstractmethod
    def __getitem__(self, index, /):
        raise NotImplementedError("__getitem__ is a required method for sorted key mutable sequences")

    @abstractmethod
    def __iter__(self: SortedKeyMutableSequence[T], /) -> SortedKeyIterator[T]:
        raise NotImplementedError("__iter__ is a required method for sorted key mutable sequences")

    @abstractmethod
    def __len__(self: SortedKeyMutableSequence[Any], /) -> int:
        raise NotImplementedError("__len__ is a required method for sorted key mutable sequences")

    @abstractmethod
    def __reversed__(self: SortedKeyMutableSequence[T], /) -> Iterator[T]:
        raise NotImplementedError("__reversed__ is a required method for sorted key mutable sequences")

    def __setitem__(self: SortedKeyMutableSequence[T], index: Union[int, slice], value: Union[T, Iterable[T]], /) -> None:
        raise NotImplementedError("__setitem__ is not usable for sorted key mutable sequences")

    @abstractmethod
    def append(self: SortedKeyMutableSequence[T], value: T, /) -> None:
        raise NotImplementedError("append is a required method for sorted key mutable sequences")

    @classmethod
    def from_iterable(cls: Type[SortedKeyMutableSequence[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeyMutableSequence[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")
        elif not callable(key):
            raise TypeError(f"key expects a callable, got {key!r}")
        else:
            return cls.from_sorted(sorted(iterable, key=key), key)

    @classmethod
    def from_sorted(cls: Type[SortedKeyMutableSequence[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeyMutableSequence[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"from_sorted expects an iterable, got {iterable!r}")
        elif not callable(key):
            raise TypeError(f"key expects a callable, got {key!r}")
        else:
            import more_collections.sorted as mcs
            return mcs.SortedKeyList.from_sorted(iterable, key)

    def insert(self: SortedKeyMutableSequence[T], index: int, value: T, /) -> None:
        raise NotImplementedError("insert is not usable for sorted key mutable sequences, use append instead")

    def reverse(self: SortedKeyMutableSequence[Any], /) -> None:
        raise NotImplementedError("reverse is not usable for sorted key mutable sequences")

    @property
    @abstractmethod
    def key(self: SortedKeySequence[T], /) -> Callable[[T], Any]:
        raise NotImplementedError("key is a required property for sorted key sequences")


class SortedSet(typing.Set[T], AbstractSet[T], SortedSequence[T], ABC, Generic[T]):

    __slots__ = ()

    def __and__(self: SortedSet[T], other: Iterable[Any], /) -> SortedSet[T]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)
        else:
            return NotImplemented

    def __contains__(self: SortedSet[Any], element: Any, /) -> bool:
        return element in self._set

    def __eq__(self: SortedSet[Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set == other
        else:
            return NotImplemented

    def __ge__(self: SortedSet[Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set >= other
        else:
            return NotImplemented

    @overload
    def __getitem__(self: SortedSet[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: SortedSet[T], index: slice, /) -> Sequence[T]:
        ...

    def __getitem__(self, index, /):
        return self._sequence[index]

    def __gt__(self: SortedSet[Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set > other
        else:
            return NotImplemented

    def __iter__(self: SortedSet[T], /) -> SortedIterator[T]:
        return iter(self._sequence)

    def __le__(self: SortedSet[Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set <= other
        else:
            return NotImplemented

    def __len__(self: SortedSet[Any], /) -> int:
        return len(self._set)

    def __lt__(self: SortedSet[Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set < other
        else:
            return NotImplemented

    def __ne__(self: SortedSet[T], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set != other
        else:
            return NotImplemented

    def __or__(self: SortedSet[T], other: Iterable[S], /) -> SortedSet[Union[T, S]]:
        if isinstance(other, AbstractSet):
            return self.union(other)
        else:
            return NotImplemented

    __ror__ = __or__

    def __rand__(self: SortedSet[Any], other: Iterable[S], /) -> SortedSet[S]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)
        else:
            return NotImplemented

    def __reversed__(self: SortedSet[T], /) -> Iterator[T]:
        return reversed(self._sequence)

    def __rsub__(self: SortedSet[Any], other: Iterable[S], /) -> SortedSet[S]:
        if isinstance(other, AbstractSet):
            import more_collections.sorted as mcs
            set_: SortedMutableSet[S] = mcs.SortedSet.from_iterable(other)
            set_ -= self
            return set_
        else:
            return NotImplemented

    def __sub__(self: SortedSet[T], other: Iterable[Any], /) -> SortedSet[T]:
        if isinstance(other, AbstractSet):
            return self.difference(other)
        else:
            return NotImplemented

    def __xor__(self: SortedSet[T], other: Iterable[S], /) -> SortedSet[Union[T, S]]:
        if isinstance(other, AbstractSet):
            return self.symmetric_difference(other)
        else:
            return NotImplemented

    __rxor__ = __xor__

    def count(self: SortedSet[Any], value: Any, /) -> Literal[0, 1]:
        return 1 if value in self else 0

    def difference(self: SortedSet[T], /, *iterables: Iterable[Any]) -> SortedSet[T]:
        if len(iterables) == 0:
            return self.copy()
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"difference argument is not iterable, got {iterable!r}")
        set_: typing.Set[T]
        if isinstance(self._set, set):
            set_ = self._set.difference(*iterables)
        else:
            set_ = set(self._set)
            set_.difference_update(*iterables)
        return type(self).from_iterable(set_)

    @classmethod
    def from_iterable(cls: Type[SortedSet[T]], iterable: Iterable[T], /) -> SortedSet[T]:
        if isinstance(iterable, Iterable):
            return cls.from_sorted(sorted(set(iterable)))  # type: ignore
        else:
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")

    @classmethod
    def from_sorted(cls: Type[SortedSet[T]], iterable: Iterable[T], /) -> SortedSet[T]:
        if isinstance(iterable, Iterable):
            import more_collections.sorted as mcs
            return mcs.SortedSet(iterable)
        else:
            raise TypeError(f"from_sorted expects an iterable, got {iterable!r}")

    def index(self: SortedSet[Any], value: Any, start: int = 0, stop: Optional[int] = None, /) -> int:
        return self._sequence.index(value, start, stop)

    def intersection(self: SortedSet[T], /, *iterables: Iterable[Any]) -> SortedSet[T]:
        if len(iterables) == 0:
            return self.copy()
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"intersection argument is not iterable, got {iterable!r}")
        set_: typing.Set[T]
        if isinstance(self._set, set):
            set_ = self._set.intersection(*iterables)
        else:
            set_ = set(self._set)
            set_.intersection_update(*iterables)
        return type(self).from_iterable(set_)

    def isdisjoint(self: SortedSet[Any], iterable: Iterable[Any], /) -> bool:
        if isinstance(iterable, Iterable):
            return self._set.isdisjoint(iterable)
        else:
            raise TypeError(f"isdisjoint argument is not iterable, got {iterable!r}")

    def issubset(self: SortedSet[Any], iterable: Iterable[Any], /) -> bool:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"issubset argument is not iterable, got {iterable!r}")
        elif isinstance(iterable, set):
            return iterable.issuperset(self)
        elif isinstance(iterable, AbstractSet):
            return all(x in iterable for x in self)
        elif isinstance(self._set, set):
            return len(self._set.intersection(iterable)) == len(self)
        else:
            return len({x for x in iterable if x in self}) == len(self)

    def issuperset(self: SortedSet[Any], iterable: Iterable[Any], /) -> bool:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"issuperset argument is not iterable, got {iterable!r}")
        elif isinstance(self._set, set):
            return self._set.issuperset(iterable)
        else:
            return all(x in self for x in iterable)

    def symmetric_difference(self: SortedSet[T], /, *iterables: Iterable[S]) -> SortedSet[Union[T, S]]:
        if len(iterables) == 0:
            return cast(SortedSet[Union[T, S]], self.copy())
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"symmetric_difference argument is not iterable, got {iterable!r}")
        set_: typing.Set[Union[T, S]]
        if isinstance(self._set, set):
            set_ = self._set.symmetric_difference(iterables[0])
        else:
            set_ = set(self._set)
            set_.symmetric_difference_update(iterables[0])
        for i in range(1, len(iterables)):
            set_.symmetric_difference_update(iterables[i])
        return type(self).from_iterable(set_)  # type: ignore

    def union(self: SortedSet[T], /, *iterables: Iterable[S]) -> SortedSet[Union[T, S]]:
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"union argument is not iterable, got {iterable!r}")
        return type(self).from_iterable(chain(self, *iterables))  # type: ignore

    @property
    @abstractmethod
    def _sequence(self: SortedSet[T], /) -> SortedSequence[T]:
        raise NotImplementedError("_sequence is a required property of sorted sets")

    @property
    @abstractmethod
    def _set(self: SortedSet[T], /) -> AbstractSet[T]:
        raise NotImplementedError("_set is a required property of sorted sets")


class SortedKeySet(typing.Set[T], AbstractSet[T], SortedKeySequence[T], ABC, Generic[T]):

    __slots__ = ()

    def __and__(self: SortedKeySet[T], other: Iterable[Any], /) -> SortedKeySet[T]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)
        else:
            return NotImplemented

    def __contains__(self: SortedKeySet[Any], value: Any, /) -> bool:
        return value in self._set

    def __eq__(self: SortedKeySet[Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set == other
        else:
            return NotImplemented

    def __ge__(self: SortedKeySet[Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set >= other
        else:
            return NotImplemented

    @overload
    def __getitem__(self: SortedKeySet[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: SortedKeySet[T], index: slice, /) -> Sequence[T]:
        ...

    def __getitem__(self, index, /):
        return self._sequence[index]

    def __gt__(self: SortedKeySet[Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set > other
        else:
            return NotImplemented

    def __iter__(self: SortedKeySet[T], /) -> SortedKeyIterator[T]:
        return iter(self._sequence)

    def __le__(self: SortedKeySet[Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set <= other
        else:
            return NotImplemented

    def __len__(self: SortedKeySet[Any], /) -> int:
        return len(self._set)

    def __lt__(self: SortedKeySet[Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set < other
        else:
            return NotImplemented

    def __ne__(self: SortedKeySet[Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set != other
        else:
            return NotImplemented

    def __or__(self: SortedKeySet[T], other: Iterable[S], /) -> SortedKeySet[Union[T, S]]:
        if isinstance(other, AbstractSet):
            return cast(SortedKeySet[Union[T, S]], self.union(other))
        else:
            return NotImplemented

    __ror__ = __or__

    def __rand__(self: SortedKeySet[Any], other: Iterable[S], /) -> SortedKeySet[S]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)
        else:
            return NotImplemented

    def __reversed__(self: SortedKeySet[T], /) -> Iterator[T]:
        return reversed(self._sequence)

    def __rsub__(self: SortedKeySet[Any], other: Iterable[S], /) -> SortedKeySet[S]:
        if isinstance(other, AbstractSet):
            import more_collections.sorted as mcs
            set_: SortedKeyMutableSet[S] = mcs.SortedKeySet.from_iterable(other, self.key)
            set_ -= self
            return set_
        else:
            return NotImplemented

    def __sub__(self: SortedKeySet[T], other: Iterable[Any], /) -> SortedKeySet[T]:
        if isinstance(other, AbstractSet):
            return self.difference(other)
        else:
            return NotImplemented

    def __xor__(self: SortedKeySet[T], other: Iterable[S], /) -> SortedKeySet[Union[T, S]]:
        if isinstance(other, AbstractSet):
            return cast(SortedKeySet[Union[T, S]], self.symmetric_difference(other))
        else:
            return NotImplemented

    __rxor__ = __xor__

    def count(self: SortedKeySet[Any], value: Any, /) -> Literal[0, 1]:
        return 1 if value in self else 0

    def difference(self: SortedKeySet[T], /, *iterables: Iterable[Any]) -> SortedKeySet[T]:
        if len(iterables) == 0:
            return self.copy()
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"difference argument is not iterable, got {iterable!r}")
        set_: typing.Set[T]
        if isinstance(self._set, set):
            set_ = self._set.difference(*iterables)
        else:
            set_ = set(self._set)
            set_.difference_update(*iterables)
        return type(self).from_iterable(set_, self.key)

    @classmethod
    def from_iterable(cls: Type[SortedKeySet[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeySet[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")
        elif not callable(key):
            raise TypeError(f"key expects a callable, got {key!r}")
        else:
            return cls.from_sorted(sorted(set(iterable), key=key), key)

    @classmethod
    def from_sorted(cls: Type[SortedKeySet[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeySet[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"from_sorted expects an iterable, got {iterable!r}")
        elif not callable(key):
            raise TypeError(f"key expects a callable, got {key!r}")
        else:
            import more_collections.sorted as mcs
            return mcs.SortedKeySet.from_sorted(iterable, key=key)

    def index(self: SortedKeySet[Any], value: Any, start: int = 0, stop: Optional[int] = None, /) -> int:
        return self._sequence.index(value, start, stop)

    def intersection(self: SortedKeySet[T], /, *iterables: Iterable[Any]) -> SortedKeySet[T]:
        if len(iterables) == 0:
            return self.copy()
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"intersection argument is not iterable, got {iterable!r}")
        set_: typing.Set[T]
        if isinstance(self._set, set):
            set_ = self._set
        else:
            set_ = set(self._set)
        return type(self).from_iterable(set_.intersection(*iterables), self.key)

    def isdisjoint(self: SortedKeySet[Any], iterable: Iterable[Any], /) -> bool:
        if isinstance(iterable, Iterable):
            return self._set.isdisjoint(iterable)
        else:
            raise TypeError(f"isdisjoint argument is not iterable, got {iterable!r}")

    def issubset(self: SortedKeySet[Any], iterable: Iterable[Any], /) -> bool:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"issubset argument is not iterable, got {iterable!r}")
        elif isinstance(iterable, set):
            return iterable.issuperset(self)
        elif isinstance(iterable, AbstractSet):
            return all(x in iterable for x in self)
        elif isinstance(self._set, set):
            return len(self._set.intersection(iterable)) == len(self)
        else:
            return len({x for x in iterable if x in self}) == len(self)

    def issuperset(self: SortedKeySet[Any], iterable: Iterable[Any], /) -> bool:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"issuperset argument is not iterable, got {iterable!r}")
        elif isinstance(self._set, set):
            return self._set.issuperset(iterable)
        else:
            return all(x in self for x in iterable)

    def symmetric_difference(self: SortedKeySet[T], /, *iterables: Iterable[S]) -> SortedKeySet[Union[T, S]]:
        if len(iterables) == 0:
            return cast(SortedKeySet[Union[T, S]], self.copy())
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"symmetric_difference argument is not iterable, got {iterable!r}")
        set_: typing.Set[Union[T, S]]
        if isinstance(self._set, set):
            set_ = self._set.symmetric_difference(iterables[0])
        else:
            set_ = set(self._set)
            set_.symmetric_difference_update(iterables[0])
        for i in range(1, len(iterables)):
            set_.symmetric_difference_update(iterables[i])
        return type(self).from_iterable(set_, self.key)  # type: ignore

    def union(self: SortedKeySet[T], /, *iterables: Iterable[S]) -> SortedKeySet[Union[T, S]]:
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"union argument is not iterable, got {iterable!r}")
        return type(self).from_iterable(chain(self, *iterables), self.key)  # type: ignore

    @property
    def key(self: SortedKeySet[T], /) -> Callable[[T], Any]:
        return self._sequence.key

    @property
    @abstractmethod
    def _sequence(self: SortedKeySet[T], /) -> SortedKeySequence[T]:
        raise NotImplementedError("_sequence is a required property of sorted key sets")

    @property
    @abstractmethod
    def _set(self: SortedKeySet[T], /) -> AbstractSet[T]:
        raise NotImplementedError("_set is a required property of sorted key sets")


class SortedMutableSet(SortedSet[T_co], MutableSet[T_co], ABC, Generic[T_co]):

    __slots__ = ()

    def __and__(self: SortedMutableSet[T_co], other: Iterable[Any], /) -> SortedMutableSet[T_co]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)
        else:
            return NotImplemented

    @overload
    def __getitem__(self: SortedMutableSet[T_co], index: int, /) -> T_co:
        ...

    @overload
    def __getitem__(self: SortedMutableSet[T_co], index: slice, /) -> MutableSequence[T_co]:
        ...

    def __getitem__(self, index, /):
        return self._sequence[index]

    def __iand__(self: SortedMutableSet[T_co], other: Iterable[Any], /) -> SortedMutableSet[T_co]:
        if isinstance(other, Iterable):
            self.intersection_update(other)
            return self
        else:
            return NotImplemented

    def __ior__(self: SortedMutableSet[T_co], other: Iterable[T], /) -> SortedMutableSet[Union[T_co, T]]:
        if isinstance(other, Iterable):
            self.update(cast(Iterable[T_co], other))
            return cast(SortedMutableSet[Union[T_co, T]], self)
        else:
            return NotImplemented

    def __iter__(self: SortedMutableSet[T_co], /) -> SortedIterator[T_co]:
        return iter(self._sequence)

    def __isub__(self: SortedMutableSet[T_co], other: Iterable[Any], /) -> SortedMutableSet[T_co]:
        if isinstance(other, Iterable):
            self.difference_update(other)
            return self
        else:
            return NotImplemented

    def __ixor__(self: SortedMutableSet[T_co], other: Iterable[T], /) -> SortedMutableSet[Union[T_co, T]]:
        if isinstance(other, Iterable):
            self.symmetric_difference_update(cast(Iterable[T_co], other))
            return cast(SortedMutableSet[Union[T_co, T]], self)
        else:
            return NotImplemented

    def __or__(self: SortedMutableSet[T_co], other: Iterable[T], /) -> SortedMutableSet[Union[T_co, T]]:
        if isinstance(other, AbstractSet):
            return cast(SortedMutableSet[Union[T_co, T]], self.union(other))
        else:
            return NotImplemented

    __ror__ = __or__

    def __rand__(self: SortedMutableSet[Any], other: Iterable[T], /) -> SortedMutableSet[T]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)
        else:
            return NotImplemented

    def __rsub__(self: SortedMutableSet[Any], other: Iterable[T], /) -> SortedMutableSet[T]:
        if isinstance(other, AbstractSet):
            import more_collections.sorted as mcs
            set_ = mcs.SortedSet.from_iterable(other)
            set_ -= self
            return set_
        else:
            return NotImplemented

    def __sub__(self: SortedMutableSet[T_co], other: Iterable[Any], /) -> SortedMutableSet[T_co]:
        if isinstance(other, AbstractSet):
            return self.difference(other)
        else:
            return NotImplemented

    def __xor__(self: SortedMutableSet[T_co], other: Iterable[T], /) -> SortedMutableSet[Union[T_co, T]]:
        if isinstance(other, AbstractSet):
            return cast(SortedMutableSet[Union[T_co, T]], self.symmetric_difference(other))
        else:
            return NotImplemented

    __rxor__ = __xor__

    def add(self: SortedMutableSet[T], value: T, /) -> None:
        len_ = len(self._set)
        self._set.add(value)
        if len(self._set) != len_:
            self._sequence.append(value)

    def clear(self: SortedMutableSet[Any], /) -> None:
        self._sequence.clear()
        self._set.clear()

    def copy(self: SortedMutableSet[T_co], /) -> SortedMutableSet[T_co]:
        return cast(SortedMutableSet[T_co], super().copy())

    def difference(self: SortedMutableSet[T_co], /, *iterables: Iterable[Any]) -> SortedMutableSet[T_co]:
        return cast(SortedMutableSet[T_co], super().difference(*iterables))

    def difference_update(self: SortedMutableSet[Any], /, *iterables: Iterable[Any]) -> None:
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"difference_update argument is not iterable, got {iterable!r}")
        for iterable in iterables:
            for x in iterable:
                self.discard(x)

    def discard(self: SortedMutableSet[Any], value: Any, /) -> None:
        len_ = len(self._set)
        self._set.discard(value)
        if len(self._set) != len_:
            self._sequence.remove(value)

    @classmethod
    def from_iterable(cls: Type[SortedMutableSet[T_co]], iterable: Iterable[T_co], /) -> SortedMutableSet[T_co]:
        if isinstance(iterable, Iterable):
            return cls.from_sorted(sorted(set(iterable)))  # type: ignore
        else:
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")

    @classmethod
    def from_sorted(cls: Type[SortedMutableSet[T_co]], iterable: Iterable[T_co], /) -> SortedMutableSet[T_co]:
        if isinstance(iterable, Iterable):
            import more_collections.sorted as mcs
            return mcs.SortedSet(iterable)
        else:
            raise TypeError(f"from_sorted expects an iterable, got {iterable!r}")

    def intersection(self: SortedMutableSet[T_co], /, *iterables: Iterable[Any]) -> SortedMutableSet[T_co]:
        return cast(SortedMutableSet[T_co], super().intersection(*iterables))

    def intersection_update(self: SortedMutableSet[Any], /, *iterables: Iterable[Any]) -> None:
        if len(iterables) == 0:
            self.clear()
            return
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"intersection_update argument is not iterable, got {iterable!r}")
        set_: typing.Set[T_co]
        if isinstance(self._set, set):
            set_ = self._set.intersection(*iterables)
        else:
            set_ = set(self._set)
            set_.intersection_update(*iterables)
        set_.symmetric_difference_update(self._set)
        self.difference_update(set_)

    def pop(self: SortedMutableSet[T_co], index: int = -1, /) -> T_co:
        if not isinstance(index, SupportsIndex):
            raise TypeError(f"pop could not interpret index as an integer, got {index!r}")
        index = operator.index(index)
        len_ = len(self._set)
        if index < 0:
            index += len_
        if not 0 <= index < len_:
            raise IndexError("index out of range")
        value = self._sequence.pop(index)
        self._set.remove(value)
        return value

    def remove(self: SortedMutableSet[Any], value: Any, /) -> None:
        len_ = len(self._set)
        self._set.discard(value)
        if len(self._set) == len_:
            raise KeyError(value)
        self._sequence.remove(value)

    def symmetric_difference(self: SortedMutableSet[T_co], /, *iterables: Iterable[T]) -> SortedMutableSet[Union[T_co, T]]:
        return cast(SortedMutableSet[T_co], super().symmetric_difference(*iterables))

    def symmetric_difference_update(self: SortedMutableSet[T_co], /, *iterables: Iterable[T_co]) -> None:
        if len(iterables) == 0:
            return
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"symmetric_difference_update argument is not iterable, got {iterable!r}")
        set_: typing.Set[T_co] = set(iterables[0])
        for i in range(1, len(iterables)):
            set_.symmetric_difference_update(iterables[i])
        for x in set_:
            if x in self:
                self.remove(x)
            else:
                self.add(x)

    def union(self: SortedMutableSet[T_co], /, *iterables: Iterable[T]) -> SortedMutableSet[Union[T_co, T]]:
        return cast(SortedMutableSet[T_co], super().union(*iterables))

    def update(self: SortedMutableSet[T_co], /, *iterables: Iterable[T_co]) -> None:
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"update argument is not iterable, got {iterable!r}")
        for iterable in iterables:
            for x in iterable:
                self.add(x)

    @property
    @abstractmethod
    def _sequence(self: SortedMutableSet[T_co], /) -> SortedMutableSequence[T_co]:
        raise NotImplementedError("_sequence is a required property of sorted mutable sets")

    @property
    @abstractmethod
    def _set(self: SortedMutableSet[T_co], /) -> MutableSet[T_co]:
        raise NotImplementedError("_set is a required property of sorted mutable sets")


class SortedKeyMutableSet(SortedKeySet[T_co], MutableSet[T_co], ABC, Generic[T_co]):

    __slots__ = ()

    def __and__(self: SortedKeyMutableSet[T_co], other: Iterable[Any], /) -> SortedKeyMutableSet[T_co]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)
        else:
            return NotImplemented

    @overload
    def __getitem__(self: SortedKeyMutableSet[T_co], index: int, /) -> T_co:
        ...

    @overload
    def __getitem__(self: SortedKeyMutableSet[T_co], index: slice, /) -> MutableSequence[T_co]:
        ...

    def __getitem__(self, index, /):
        return self._sequence[index]

    def __iand__(self: SortedKeyMutableSet[T_co], other: Iterable[Any], /) -> SortedKeyMutableSet[T_co]:
        if isinstance(other, Iterable):
            self.intersection_update(other)
            return self
        else:
            return NotImplemented

    def __ior__(self: SortedKeyMutableSet[T_co], other: Iterable[T], /) -> SortedKeyMutableSet[Union[T_co, T]]:
        if isinstance(other, Iterable):
            self.update(cast(Iterable[T_co], other))
            return cast(SortedKeyMutableSet[Union[T_co, T]], self)
        else:
            return NotImplemented

    def __isub__(self: SortedKeyMutableSet[T_co], other: Iterable[Any], /) -> SortedKeyMutableSet[T_co]:
        if isinstance(other, Iterable):
            self.difference_update(other)
            return self
        else:
            return NotImplemented

    def __iter__(self: SortedKeyMutableSet[T_co], /) -> SortedKeyIterator[T_co]:
        return iter(self._sequence)

    def __ixor__(self: SortedKeyMutableSet[T_co], other: Iterable[T], /) -> SortedKeyMutableSet[Union[T_co, T]]:
        if isinstance(other, Iterable):
            self.symmetric_difference_update(cast(Iterable[T_co], other))
            return cast(SortedKeyMutableSet[Union[T_co, T]], self)
        else:
            return NotImplemented

    def __or__(self: SortedKeyMutableSet[T_co], other: Iterable[T], /) -> SortedKeyMutableSet[Union[T_co, T]]:
        if isinstance(other, AbstractSet):
            return self.union(other)
        else:
            return NotImplemented

    __ror__ = __or__

    def __rand__(self: SortedKeyMutableSet[Any], other: Iterable[T], /) -> SortedKeyMutableSet[T]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)
        else:
            return NotImplemented

    def __rsub__(self: SortedKeyMutableSet[Any], other: Iterable[T], /) -> SortedKeyMutableSet[T]:
        if isinstance(other, AbstractSet):
            import more_collections.sorted as mcs
            set_ = mcs.SortedSet.from_iterable(other)
            set_ -= self
            return set_
        else:
            return NotImplemented

    def __sub__(self: SortedKeyMutableSet[T_co], other: Iterable[Any], /) -> SortedKeyMutableSet[T_co]:
        if isinstance(other, AbstractSet):
            return self.difference(other)
        else:
            return NotImplemented

    def __xor__(self: SortedKeyMutableSet[T_co], other: Iterable[T], /) -> SortedKeyMutableSet[Union[T_co, T]]:
        if isinstance(other, AbstractSet):
            return self.symmetric_difference(other)
        else:
            return NotImplemented

    __rxor__ = __xor__

    def add(self: SortedKeyMutableSet[T], value: T, /) -> None:
        len_ = len(self._set)
        self._set.add(value)
        if len(self._set) != len_:
            self._sequence.append(value)

    def clear(self: SortedKeyMutableSet[Any], /) -> None:
        self._sequence.clear()
        self._set.clear()

    def difference(self: SortedKeyMutableSet[T_co], /, *iterables: Iterable[Any]) -> SortedKeyMutableSet[T_co]:
        return cast(SortedKeyMutableSet[T_co], super().difference(*iterables))

    def difference_update(self: SortedKeyMutableSet[Any], /, *iterables: Iterable[Any]) -> None:
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"difference_update argument is not iterable, got {iterable!r}")
        for iterable in iterables:
            for x in iterable:
                self.discard(x)

    def discard(self: SortedKeyMutableSet[Any], value: Any, /) -> None:
        len_ = len(self._set)
        self._set.discard(value)
        if len(self._set) != len_:
            self._sequence.remove(value)

    @abstractmethod
    @classmethod
    def from_sorted(cls: Type[SortedKeyMutableSet[T_co]], iterable: Iterable[T_co], /, key: Callable[[T_co], Any]) -> SortedKeyMutableSet[T_co]:
        raise NotImplementedError("from_sorted is a required method for sorted key mutable sets")

    def intersection(self: SortedKeyMutableSet[T_co], /, *iterables: Iterable[Any]) -> SortedKeyMutableSet[T_co]:
        return cast(SortedKeyMutableSet[T_co], super().intersection(*iterables))

    def intersection_update(self: SortedKeyMutableSet[Any], /, *iterables: Iterable[Any]) -> None:
        if len(iterables) == 0:
            self.clear()
            return
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"intersection_update argument is not iterable, got {iterable!r}")
        set_: typing.Set[Any]
        if len(iterables) == 1:
            if isinstance(self._set, set):
                set_ = self._set.symmetric_difference(iterables[0])
            elif isinstance(iterables[0], set):
                set_ = iterables[0].symmetric_difference(self._set)
            else:
                set_ = set(self._set)
                set_.symmetric_difference_update(iterables[0])
        else:
            if isinstance(self._set, set):
                set_ = self._set.intersection(*iterables)
            else:
                set_ = set(self._set)
                set_.intersection_update(*iterables)
            set_.symmetric_difference_update(self._set)
        self.difference_update(set_)

    def pop(self: SortedKeyMutableSet[T_co], index: int = -1, /) -> T_co:
        if not isinstance(index, SupportsIndex):
            raise TypeError(f"pop could not interpret index as an integer, got {index!r}")
        index = operator.index(index)
        len_ = len(self._set)
        if index < 0:
            index += len_
        if not 0 <= index < len_:
            raise IndexError("index out of range")
        value = self._sequence.pop(index)
        self._set.remove(value)
        return value

    def remove(self: SortedKeyMutableSet[Any], value: Any, /) -> None:
        len_ = len(self._set)
        self._set.discard(value)
        if len(self._set) == len_:
            raise KeyError(value)
        self._sequence.remove(value)

    def symmetric_difference(self: SortedKeyMutableSet[T_co], /, *iterables: Iterable[T]) -> SortedKeyMutableSet[Union[T_co, T]]:
        return cast(SortedKeyMutableSet[Union[T_co, T]], super().symmetric_difference(*iterables))

    def symmetric_difference_update(self: SortedKeyMutableSet[T_co], /, *iterables: Iterable[T_co]) -> None:
        if len(iterables) == 0:
            return
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"symmetric_difference_update argument is not iterable, got {iterable!r}")
        set_: typing.Set[Any] = set(iterables[0])
        for i in range(1, len(iterables)):
            set_.symmetric_difference_update(iterables[i])
        for x in set_:
            if x in self:
                self.remove(x)
            else:
                self.add(x)

    def union(self: SortedKeyMutableSet[T_co], /, *iterables: Iterable[T]) -> SortedKeyMutableSet[Union[T_co, T]]:
        return cast(SortedKeyMutableSet[Union[T_co, T]], super().union(*iterables))

    def update(self: SortedKeyMutableSet[T_co], /, *iterables: Iterable[T_co]) -> None:
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"update argument is not iterable, got {iterable!r}")
        for iterable in iterables:
            for x in iterable:
                self.add(x)

    @property
    @abstractmethod
    def _sequence(self: SortedKeyMutableSet[T_co], /) -> SortedKeyMutableSequence[T_co]:
        raise NotImplementedError("_sequence is a required property of sorted key mutable sets")

    @property
    @abstractmethod
    def _set(self: SortedKeyMutableSet[T_co], /) -> MutableSet[T_co]:
        raise NotImplementedError("_set is a required property of sorted key mutable sets")


class SortedMappingView(MappingView, Generic[KT_co, VT_co]):
    __mapping: SortedMapping[KT_co, VT_co]

    __slots__ = ("__mapping",)

    def __init__(self: SortedMappingView[KT_co, VT_co], mapping: SortedMapping[KT_co, VT_co], /) -> None:
        if not isinstance(mapping, SortedMapping):
            raise TypeError(f"sorted mapping view requires a sorted mapping, got {mapping!r}")
        self.__mapping = mapping

    def __len__(self: SortedMappingView[Any, Any], /) -> int:
        return len(self._mapping)

    def __repr__(self: SortedMappingView[Any, Any], /) -> str:
        if id(self) in reprs_seen:
            return "..."
        reprs_seen.add(id(self))
        try:
            return f"{type(self).__name__}({self._mapping!r})"
        finally:
            reprs_seen.remove(id(self))

    @property
    def _mapping(self: SortedMappingView[KT_co, VT_co], /) -> SortedMapping[KT_co, VT_co]:
        return self.__mapping


class SortedItemsView(SortedMappingView[KT_co, VT_co], SortedKeySet[Tuple[KT_co, VT_co]], ItemsView[KT_co, VT_co], Generic[KT_co, VT_co]):
    __sequence: Optional[SortedKeySequence[Tuple[KT_co, VT_co]]]
    __set: Optional[AbstractSet[Tuple[KT_co, VT_co]]]

    __slots__ = ("__sequence", "__set")

    def __init__(self: SortedItemsView[KT_co, VT_co], mapping: SortedMapping[KT_co, VT_co], /) -> None:
        if not isinstance(mapping, SortedMapping):
            raise TypeError(f"sorted items view requires a sorted mapping, got {mapping!r}")
        super().__init__(mapping)
        self.__sequence = None
        self.__set = None

    def __and__(self: SortedItemsView[KT_co, VT_co], other: Iterable[Any], /) -> SortedKeySet[Tuple[KT_co, VT_co]]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)
        else:
            return NotImplemented

    def __contains__(self: SortedItemsView[Any, Any], item: Any, /) -> bool:
        if not isinstance(item, tuple) or len(item) != 2:
            return False
        MISSING = object()
        return MISSING is not self._mapping.get(item[0], MISSING) == item[1]

    def __eq__(self: SortedItemsView[Any, Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return len(self) == len(other) and all(item in self for item in other)
        else:
            return NotImplemented

    def __ge__(self: SortedItemsView[Any, Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return len(self) >= len(other) and all(item in self for item in other)
        else:
            return NotImplemented

    def __gt__(self: SortedItemsView[Any, Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return len(self) > len(other) and all(item in self for item in other)
        else:
            return NotImplemented

    def __iter__(self: SortedItemsView[KT_co, VT_co], /) -> SortedKeyIterator[Tuple[KT_co, VT_co]]:
        import more_collections.sorted as mcs
        return mcs.SortedKeyUserIterator((key, self._mapping[key]) for key in self._mapping)  # type: ignore

    def __le__(self: SortedItemsView[Any, Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return len(self) <= len(other) and all(item in other for item in self)
        else:
            return NotImplemented

    def __lt__(self: SortedItemsView[Any, Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return len(self) < len(other) and all(item in other for item in self)
        else:
            return NotImplemented

    def __ne__(self: SortedItemsView[Any, Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return len(self) != len(other) or not all(item in self for item in other)
        else:
            return NotImplemented

    def __or__(self: SortedItemsView[KT_co, VT_co], other: Iterable[T], /) -> SortedKeySet[Union[Tuple[KT_co, VT_co], T]]:
        if isinstance(other, AbstractSet):
            return self.union(other)
        else:
            return NotImplemented

    __ror__ = __or__

    def __rand__(self: SortedItemsView[Any, Any], other: Iterable[T], /) -> SortedKeySet[T]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)  # type: ignore
        else:
            return NotImplemented

    def __reversed__(self: SortedItemsView[KT_co, VT_co], /) -> Iterator[Tuple[KT_co, VT_co]]:
        return ((key, self._mapping[key]) for key in reversed(self._mapping))

    def __rsub__(self: SortedItemsView[Any, Any], other: Iterable[T], /) -> SortedKeySet[T]:
        if isinstance(other, AbstractSet):
            import more_collections.sorted as mcs
            set_: SortedKeyMutableSet[T] = mcs.SortedKeySet.from_iterable(other, self.key)
            set_ -= self
            return set_
        else:
            return NotImplemented

    def __sub__(self: SortedItemsView[KT_co, VT_co], other: Iterable[Any], /) -> SortedKeySet[Tuple[KT_co, VT_co]]:
        if isinstance(other, AbstractSet):
            return self.difference(other)
        else:
            return NotImplemented

    def __xor__(self: SortedItemsView[KT_co, VT_co], other: Iterable[T], /) -> SortedKeySet[Union[Tuple[KT_co, VT_co], T]]:
        if isinstance(other, AbstractSet):
            return self.symmetric_difference(other)
        else:
            return NotImplemented

    __rxor__ = __xor__

    def difference(self: SortedItemsView[KT_co, VT_co], /, *iterables: Iterable[Any]) -> SortedKeySet[Tuple[KT_co, VT_co]]:
        import more_collections.sorted as mcs
        set_: SortedKeyMutableSet[Tuple[KT_co, VT_co]] = mcs.SortedKeySet.from_sorted(self)
        set_.difference_update(*iterables)
        return set_

    def isdisjoint(self: SortedItemsView[Any, Any], iterable: Iterable[Any], /) -> bool:
        if isinstance(iterable, AbstractSet):
            return iterable.isdisjoint(self)
        elif isinstance(iterable, Iterable):
            return self._set.isdisjoint(iterable)
        else:
            raise TypeError(f"isdisjoint argument is not iterable, got {iterable!r}")

    def issubset(self: SortedItemsView[Any, Any], iterable: Iterable[Any], /) -> bool:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"issubset argument is not iterable, got {iterable!r}")
        elif isinstance(iterable, set):
            return iterable.issuperset(self)
        elif isinstance(iterable, AbstractSet):
            return all(x in iterable for x in self)
        else:
            return len({x for x in iterable if x in self}) == len(self)

    def issuperset(self: SortedItemsView[Any, Any], iterable: Iterable[Any], /) -> bool:
        if isinstance(iterable, Iterable):
            return all(x in self for x in iterable)
        else:
            raise TypeError(f"issuperset argument is not iterable, got {iterable!r}")

    @classmethod
    def from_iterable(cls: Type[SortedItemsView[Any, Any]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeySet[T]:
        import more_collections.sorted as mcs
        return mcs.SortedKeySet.from_iterable(iterable, key)  # type: ignore

    @classmethod
    def from_sorted(cls: Type[SortedItemsView[Any, Any]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeySet[T]:
        import more_collections.sorted as mcs
        return mcs.SortedKeySet.from_sorted(iterable, key)  # type: ignore

    def intersection(self: SortedItemsView[KT_co, VT_co], /, *iterables: Iterable[Any]) -> SortedKeySet[Tuple[KT_co, VT_co]]:
        import more_collections.sorted as mcs
        set_ = mcs.SortedKeySet[Tuple[KT, VT]].from_sorted(self)
        set_.intersection_update(*iterables)
        return set_

    def symmetric_difference(self: SortedItemsView[KT_co, VT_co], /, *iterables: Iterable[T]) -> SortedKeySet[Union[Tuple[KT_co, VT_co], T]]:
        import more_collections.sorted as mcs
        set_: SortedKeyMutableSet[Union[Tuple[KT_co, VT_co], T]] = mcs.SortedKeySet.from_sorted(self)
        set_.symmetric_difference_update(*iterables)
        return set_

    def union(self: SortedItemsView[KT_co, VT_co], /, *iterables: Iterable[T]) -> SortedKeySet[Union[Tuple[KT_co, VT_co], T]]:
        import more_collections.sorted as mcs
        return mcs.SortedKeySet.from_iterable(chain(self, *iterables))  # type: ignore

    @classmethod
    def __key(cls: Type[SortedItemsView[KT_co, VT_co]], item: Tuple[KT_co, VT_co], /) -> KT_co:
        return item[0]

    @property
    def key(self: SortedItemsView[KT_co, VT_co], /) -> Callable[[Tuple[KT_co, VT_co]], KT_co]:
        return type(self).__key

    @property
    def _sequence(self: SortedItemsView[KT_co, VT_co], /) -> SortedKeySequence[Tuple[KT_co, VT_co]]:
        if self.__sequence is None:
            import more_collections.sorted as mcs
            sequence: SortedKeySequence[Tuple[KT_co, VT_co]] = mcs.SortedKeyList.from_sorted(self, key=self.key)
            self.__sequence = sequence
            return sequence
        else:
            return self.__sequence

    @property
    def _set(self: SortedItemsView[KT_co, VT_co], /) -> AbstractSet[Tuple[KT_co, VT_co]]:
        if self.__set is None:
            set_: typing.Set[Tuple[KT_co, VT_co]] = set(self)
            self.__set = set_
            return set_
        else:
            return self.__set


class SortedKeysView(SortedMappingView[KT_co, Any], SortedSet[KT_co], KeysView[KT_co], Generic[KT_co]):

    __slots__ = ()

    def __init__(self: SortedKeysView[KT_co], mapping: SortedMapping[KT_co, Any], /) -> None:
        if not isinstance(mapping, SortedMapping):
            raise TypeError(f"sorted keys view requires a sorted mapping, got {mapping!r}")
        super().__init__(mapping)

    def __and__(self: SortedKeysView[KT_co], other: Iterable[Any], /) -> SortedSet[KT_co]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)
        else:
            return NotImplemented

    def __iter__(self: SortedKeysView[KT_co], /) -> SortedIterator[KT_co]:
        return iter(self._mapping)

    def __or__(self: SortedKeysView[KT_co], other: Iterable[T], /) -> SortedSet[Union[KT_co, T]]:
        if isinstance(other, AbstractSet):
            return self.union(other)
        else:
            return NotImplemented

    __ror__ = __or__

    def __rand__(self: SortedKeysView[Any], other: Iterable[T], /) -> SortedSet[T]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)
        else:
            return NotImplemented

    def __rsub__(self: SortedKeysView[Any], other: Iterable[T], /) -> SortedSet[T]:
        if isinstance(other, AbstractSet):
            import more_collections.sorted as mcs
            set_: SortedMutableSet[T] = mcs.SortedSet.from_iterable(other)
            set_ -= self
            return set_
        else:
            return NotImplemented

    def __sub__(self: SortedKeysView[KT_co], other: Iterable[T], /) -> SortedSet[KT_co]:
        if isinstance(other, AbstractSet):
            return self.difference(other)
        else:
            return NotImplemented

    def __xor__(self: SortedKeysView[KT_co], other: Iterable[T], /) -> SortedSet[Union[KT_co, T]]:
        if isinstance(other, AbstractSet):
            return self.symmetric_difference(other)
        else:
            return NotImplemented

    __rxor__ = __xor__

    @property
    def _sequence(self: SortedKeysView[KT_co], /) -> SortedSequence[KT_co]:
        return self._mapping._set._sequence

    @property
    def _set(self: SortedKeysView[KT_co], /) -> AbstractSet[KT_co]:
        return self._mapping._set._set


class SortedValuesView(SortedMappingView[Any, VT_co], Sequence[VT_co], ValuesView[VT_co], Generic[VT_co]):

    __slots__ = ()

    def __init__(self: SortedValuesView[VT_co], mapping: SortedMapping[Any, VT_co], /) -> None:
        if not isinstance(mapping, SortedMapping):
            raise TypeError(f"sorted keys view requires a sorted mapping, got {mapping!r}")
        super().__init__(mapping)

    @overload
    def __getitem__(self: SortedValuesView[VT_co], index: int, /) -> VT_co:
        ...

    @overload
    def __getitem__(self: SortedValuesView[VT_co], index: slice, /) -> Sequence[VT_co]:
        ...

    def __getitem__(self, index, /):
        if isinstance(index, slice):
            return (self._mapping[key] for key in self._mapping._set[index])
        else:
            return self._mapping[self._mapping._set[index]]

    def __iter__(self: SortedValuesView[VT_co], /) -> Iterator[VT_co]:
        return (self._mapping[key] for key in self._mapping)

    def __reversed__(self: SortedValuesView[VT_co], /) -> Iterator[VT_co]:
        return (self._mapping[key] for key in reversed(self._mapping))


class SortedMapping(Mapping[KT_co, VT_co], SortedIterable[KT_co], Generic[KT_co, VT_co]):

    __slots__ = ()

    def __getitem__(self: SortedMapping[KT, VT_co], key: KT, /) -> VT_co:
        return self._mapping[key]

    def __iter__(self: SortedMapping[KT_co, Any], /) -> SortedIterator[KT_co]:
        return iter(self._set)

    def __len__(self: SortedMapping[Any, Any], /) -> int:
        return len(self._mapping)

    def __repr__(self: SortedMapping[Any, Any], /) -> str:
        if id(self) in reprs_seen:
            return "..."
        reprs_seen.add(id(self))
        try:
            cls = type(self)
            data = "{" + ", ".join([f"{key!r}: {value!r}" for key, value in self.items()]) + "}"
            return f"{cls.__name__}.from_iterable({data})"
        finally:
            reprs_seen.remove(id(self))

    def __reversed__(self: SortedMapping[KT_co, Any], /) -> Iterator[KT_co]:
        return reversed(self._set)

    @classmethod
    def from_iterable(cls: Type[SortedMapping[KT_co, VT_co]], mapping: Union[Mapping[KT_co, VT_co], Iterable[Tuple[KT_co, VT_co]]], /) -> SortedMapping[KT_co, VT_co]:
        if isinstance(mapping, Mapping):
            return cls.from_sorted(sorted(mapping.items(), key=lambda x: x[0]))  # type: ignore
        elif isinstance(mapping, Iterable):
            return cls.from_sorted(sorted(mapping, key=lambda x: x[0]))  # type: ignore
        else:
            raise TypeError(f"from_iterable expects a mapping, got {mapping!r}")

    @abstractmethod
    @classmethod
    def from_sorted(cls: Type[SortedMapping[KT_co, VT_co]], mapping: Union[Mapping[KT_co, VT_co], Iterable[Tuple[KT_co, VT_co]]], /) -> SortedMapping[KT_co, VT_co]:
        raise NotImplementedError("from_sorted is a required method for sorted mappings")

    def items(self: SortedMapping[KT_co, VT_co], /) -> SortedItemsView[KT_co, VT_co]:
        return SortedItemsView(self)

    def keys(self: SortedMapping[KT_co, Any], /) -> SortedKeysView[KT_co]:
        return SortedKeysView(self)

    def values(self: SortedMapping[Any, VT_co], /) -> SortedValuesView[VT_co]:
        return SortedValuesView(self)

    @property
    @abstractmethod
    def _mapping(self: SortedMapping[KT_co, VT_co], /) -> Mapping[KT_co, VT_co]:
        raise NotImplementedError("_mapping is a required property for sorted mappings")

    @property
    @abstractmethod
    def _set(self: SortedMapping[KT_co, Any], /) -> SortedSet[KT_co]:
        raise NotImplementedError("_set is a required property for sorted mappings")


class SortedMutableMapping(MutableMapping[KT_co, VT_co], SortedMapping[KT_co, VT_co], Generic[KT_co, VT_co]):

    __slots__ = ()

    def __delitem__(self: SortedMutableMapping[KT, Any], key: KT, /) -> None:
        del self._mapping[key]
        self._set.remove(key)

    def __setitem__(self: SortedMutableMapping[KT, VT], key: KT, value: VT, /) -> None:
        len_ = len(self)
        self._mapping[key] = value
        if len(self._mapping) != len_:
            self._set.add(key)

    def clear(self: SortedMutableMapping[Any, Any], /) -> None:
        self._mapping.clear()
        self._set.clear()

    @classmethod
    def from_iterable(cls: Type[SortedMutableMapping[KT_co, VT_co]], mapping: Union[Mapping[KT_co, VT_co], Iterable[Tuple[KT_co, VT_co]]], /) -> SortedMutableMapping[KT_co, VT_co]:
        if isinstance(mapping, Mapping):
            return cls.from_sorted(sorted(mapping.items(), key=lambda x: x[0]))  # type: ignore
        elif isinstance(mapping, Iterable):
            return cls.from_sorted(sorted(mapping, key=lambda x: x[0]))  # type: ignore
        else:
            raise TypeError(f"from_iterable expects a mapping, got {mapping!r}")

    @abstractmethod
    @classmethod
    def from_sorted(cls: Type[SortedMutableMapping[KT_co, VT_co]], mapping: Union[Mapping[KT_co, VT_co], Iterable[Tuple[KT_co, VT_co]]], /) -> SortedMutableMapping[KT_co, VT_co]:
        raise NotImplementedError("from_sorted is a required method for sorted mutable mappings")

    @property
    @abstractmethod
    def _mapping(self: SortedMutableMapping[KT_co, VT_co], /) -> MutableMapping[KT_co, VT_co]:
        raise NotImplementedError("_mapping is a required property for sorted mutable mappings")

    @property
    @abstractmethod
    def _set(self: SortedMutableMapping[KT_co, Any], /) -> SortedMutableSet[KT_co]:
        raise NotImplementedError("_set is a required property for sorted mutable mappings")


if sys.version_info < (3, 9):
    collections.abc.AbstractSet.register(SortedSet)
    collections.abc.ItemsView.register(SortedItemsView)
    collections.abc.Iterable.register(SortedIterable)
    collections.abc.Iterator.register(SortedIterator)
    collections.abc.KeysView.register(SortedKeysView)
    collections.abc.Mapping.register(SortedMapping)
    collections.abc.MappingView.register(SortedMappingView)
    collections.abc.MutableMapping.register(SortedMutableMapping)
    collections.abc.MutableSequence.register(SortedMutableSequence)
    collections.abc.MutableSet.register(SortedMutableSet)
    collections.abc.Sequence.register(SortedSequence)
