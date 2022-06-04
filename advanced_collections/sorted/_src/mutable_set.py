from __future__ import annotations
import operator
import sys
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any, Generic, SupportsIndex, Type, TypeVar, overload

if sys.version_info < (3, 9):
    from typing import AbstractSet, Iterable, MutableSet
else:
    from collections.abc import Set as AbstractSet, Iterable, MutableSet

from advanced_collections._src.comparable import SupportsRichHashableComparison
from .collection import SortedCollection
from .mapping import SortedMapping
from .mutable_sequence import SortedMutableSequence
from .set import SortedAbstractSet

__all__ = ["SortedMutableSet"]

Self = TypeVar("Self", bound="SortedMutableSet")
S = TypeVar("S")
T = TypeVar("T", bound=SupportsRichHashableComparison)
T_ = TypeVar("T_", bound=SupportsRichHashableComparison)


class SortedMutableSet(SortedAbstractSet[T], MutableSet[T], ABC, Generic[T]):

    __slots__ = ()

    @overload
    def __add__(self: Self, other: SortedMutableSet[T_], /) -> SortedMutableSet[Union[T, T_]]: ...

    @overload
    def __add__(self: Self, other: SortedAbstractSet[T_], /) -> SortedAbstractSet[Union[T, T_]]: ...

    @overload
    def __add__(self: Self, other: AbstractSet[S], /) -> AbstractSet[Union[S, T]]: ...

    def __add__(self, other, /):
        return type(self).__or__(self, other)

    @overload
    def __and__(self: Self, other: SortedMutableSet[Any], /) -> SortedMutableSet[T]: ...

    @overload
    def __and__(self: Self, other: AbstractSet[Any], /) -> SortedAbstractSet[T]: ...

    def __and__(self, other, /):
        return super().__and__(other)

    @classmethod
    def __from_iterable__(cls: Type[Self], iterable: Iterable[T], /) -> SortedMutableSet[T]:
        if isinstance(iterable, (SortedAbstractSet, SortedMapping)):
            pass
        elif isinstance(iterable, SortedCollection):
            iterable = (element for element, group in groupby(iterable))
        elif isinstance(iterable, (AbstractSet, Mapping)):
            iterable = sorted(iterable)
        else:
            iterable = sorted(OrderedDict.fromkeys(iterable))
        return cls.__from_sorted__(iterable)

    @classmethod
    @abstractmethod
    def __from_sorted__(cls: Type[Self], iterable: Iterable[T], /) -> SortedMutableSet[T]:
        raise NotImplementedError("__from_sorted__ is a required method for sorted mutable sets")

    def __iadd__(self: Self, other: Iterable[T_], /) -> Self:
        return type(self).__ior__(self, other)

    def __iand__(self: Self, other: Iterable[Any], /) -> Self:
        if isinstance(other, Iterable):
            self.intersection_update(self)
            return self
        else:
            return NotImplemented

    def __ior__(self: Self, other: Iterable[T_], /) -> Self:
        if isinstance(other, Iterable):
            self.update(other)
            return self
        else:
            return NotImplemented

    def __isub__(self: Self, other: Iterable[Any], /) -> Self:
        if isinstance(other, Iterable):
            self.difference_update(self)
            return self
        else:
            return NotImplemented

    def __ixor__(self: Self, other: Iterable[T_], /) -> Self:
        if isinstance(other, Iterable):
            self.symmetric_difference_update(self)
            return self
        else:
            return NotImplemented

    @overload
    def __or__(self: Self, other: SortedMutableSet[T_], /) -> SortedMutableSet[Union[T, T_]]: ...

    @overload
    def __or__(self: Self, other: SortedAbstractSet[T_], /) -> SortedAbstractSet[Union[T, T_]]: ...

    @overload
    def __or__(self: Self, other: AbstractSet[S], /) -> AbstractSet[Union[S, T]]: ...

    def __or__(self, other, /):
        return SortedAbstractSet.__or__(self, other)

    @overload
    def __sub__(self: Self, other: SortedMutableSet[Any], /) -> SortedMutableSet[T]: ...

    @overload
    def __sub__(self: Self, other: AbstractSet[Any], /) -> SortedAbstractSet[T]: ...

    def __sub__(self, other, /):
        return SortedAbstractSet.__sub__(self, other)

    @overload
    def __xor__(self: Self, other: SortedMutableSet[T_], /) -> SortedMutableSet[Union[T, T_]]: ...

    @overload
    def __xor__(self: Self, other: SortedAbstractSet[T_], /) -> SortedAbstractSet[Union[T, T_]]: ...

    @overload
    def __xor__(self: Self, other: AbstractSet[S], /) -> AbstractSet[Union[S, T]]: ...

    def __xor__(self, other, /):
        return SortedAbstractSet.__xor__(self, other)

    def add(self: Self, element: T, /) -> None:
        self._sequence.add(element)

    def clear(self: Self, /) -> None:
        self._sequence.clear()

    def difference(self: Self, /, *iterables: Iterable[T_]) -> SortedMutableSet[T]:
        return super().difference(*iterables)

    def difference_update(self: Self, /, *iterables: Iterable[T_]) -> None:
        others = []
        sets = []
        for iterable in iterables:
            if isinstance(iterable, (AbstractSet, Mapping)) and len(iterable) > len(self) // len(iterables):
                sets.append(iterable)
            elif isinstance(iterable, Iterable):
                others.append(iterable)
            else:
                raise TypeError(f"difference_udpate expected iterables, got {iterable!r}")
        del iterables
        for iterable in others:
            for x in iterable:
                self.discard(x)
        for x in [x for x in self if any((x in s) for s in sets)]:
            self.remove(x)

    def discard(self: Self, element: T, /) -> None:
        self._sequence.discard(element)

    def intersection(self: Self, /, *iterables: Iterable[T_]) -> SortedMutableSet[T]:
        return super().intersection(*iterables)

    def intersection_update(self: Self, /, *iterables: Iterable[T_]) -> None:
        if len(iterables) == 0:
            return
        others = []
        sets = []
        sorteds = [self]
        for iterable in iterables:
            if isinstance(iterable, SortedCollection):
                sorteds.append(iterable)
            elif isinstance(iterable, (AbstractSet, Mapping)):
                sets.append(iterable)
            elif not isinstance(iterable, Iterable):
                others.append(iterable)
            else:
                raise TypeError(f"expected iterables, got {iterable!r}")
        del iterables
        if len(others) == 0:
            sorteds.sort(key=len)
            shorts = [
                (key for key, _ in groupby(s))
                for s in sorteds
                if len(sorteds[0]) >= len(s) // 8
            ]
            sets.extend(sorteds[len(shorts):])
            del others, sorteds
            for x in [
                key
                for key, group in groupby(merge(*shorts))
                if any(True for _ in islice(group, len(shorts), None)) or not all((key in s) for s in sets)
            ]:
                self.discard(x)
        else:
            sets.extend(sorteds)
            shortest = min(sets, key=len)
            sets = [s for s in sets if s is not shortest]
            iterable = max(others, key=length_hint)
            sets.append({
                x
                for s in others
                if s is not iterable
                for x in s
                if x in shortest
            })
            del others, sorteds
            for x in [
                x
                for x in iterable
                if not all((x in s) for s in sets)
            ]:
                self.discard(x)

    def pop(self: Self, index: int = -1, /) -> T:
        return self._sequence.pop(index)

    def remove(self: Self, element: T, /) -> None:
        len_ = len(self)
        self.discard(element)
        if len(self) == len_:
            raise KeyError(element)

    def symmetric_difference(self: Self, /, *iterables: Iterable[T_]) -> SortedMutableSequence[Union[T, T_]]:
        return super().symmetric_difference(*iterables)

    def symmetric_difference_update(self: Self, /, *iterables: Iterable[T_]) -> None:
        if len(iterables) == 0:
            return
        sets = []
        sorteds = [self]
        for iterable in iterables:
            if isinstance(iterable, (AbstractSet, Mapping)):
                sorteds.extend(iterable)
            elif isinstance(iterable, SortedCollection):
                sorteds.append(key for key, _ in groupby(iterable))
            elif isinstance(iterable, (AbstractSet, Mapping)):
                sets.append(iterable)
            elif not isinstance(iterable, Iterable):
                sets.append({*iterable})
            else:
                raise TypeError(f"expected iterables, got {iterable!r}")
        del iterables
        for x in [
            key
            for key, group in groupby(merge(*sorteds))
            if (sum(1 for _ in group) + sum(1 for s in sets if key in s)) % 2 == 1
        ]:
            len_ = len(self)
            self.discard(x)
            if len(self) == len_:
                self.add(x)

    @property
    @abstractmethod
    def _sequence(self: Self, /) -> SortedMutableSequence[T]:
        raise NotImplementedError("_sequence is a required property for sorted mutable sequences")
