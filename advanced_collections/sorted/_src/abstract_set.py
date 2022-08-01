import copy
from abc import ABC, abstractmethod
from collections import OrderedDict
from collections.abc import Set as AbstractSet, Iterable, Iterator, Mapping, Sized
from heapq import merge
from inspect import isabstract
from itertools import chain, groupby, islice
from operator import length_hint
from typing import Any, Generic, Type, TypeVar, Union, overload

from advanced_collections._src.comparable import SupportsRichHashableComparison
from .collection import SortedCollection
from .mapping import SortedMapping
from .sequence import SortedSequence

S = TypeVar("S")
T = TypeVar("T", bound=SupportsRichHashableComparison)
T_co = TypeVar("T_co", bound=SupportsRichHashableComparison, covariant=True)

Self = TypeVar("Self", bound="SortedAbstractSet")


class SortedAbstractSet(SortedSequence[T_co], AbstractSet[T_co], ABC, Generic[T_co]):

    __slots__ = ()

    @overload
    def __add__(self: Self, other: "SortedAbstractSet[T]", /) -> "SortedAbstractSet[Union[T, T_co]]": ...

    @overload
    def __add__(self: Self, other: AbstractSet[S], /) -> AbstractSet[Union[S, T_co]]: ...

    def __add__(self, other, /):
        return type(self).__or__(self, other)

    def __radd__(self: Self, other: AbstractSet[S], /) -> AbstractSet[Union[S, T_co]]:
        return type(self).__ror__(self, other)

    def __and__(self: Self, other: AbstractSet[Any], /) -> "SortedAbstractSet[T_co]":
        # Find common non-abstract parent class.
        for cls in type(self).mro():
            if isinstance(other, cls) and issubclass(cls, SortedAbstractSet) and not isabstract(cls):
                if len(self) < len(other) // 8:
                    return cls.__from_sorted__(x for x in self if x in other)
                elif len(other) < len(self) // 8:
                    return cls.__from_sorted__(x for x in other if x in self)
                else:
                    return cls.__from_sorted__(
                        key
                        for key, group in groupby(merge(self, other))
                        if sum(1 for _ in group) == 2
                    )
        return NotImplemented

    def __rand__(self: Self, other: AbstractSet[Any], /) -> "SortedAbstractSet[T_co]":
        return NotImplemented

    def __copy__(self: Self, /) -> Self:
        return type(self).__from_sorted__(self)

    def __deepcopy__(self: Self, /) -> Self:
        return type(self).__from_sorted__(copy.deepcopy(x) for x in self)

    def __eq__(self: Self, other: Any, /) -> bool:
        return SortedSequence.__eq__(self, other)

    @classmethod
    def __from_iterable__(cls: Type[Self], iterable: Iterable[T_co], /) -> "SortedAbstractSet[T_co]":
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
    def __from_sorted__(cls: Type[Self], iterable: Iterable[T_co], /) -> "SortedAbstractSet[T_co]":
        raise NotImplementedError("__from_sorted__ is a required method for sorted abstract sets")

    def __ge__(self: Self, other: Any, /) -> bool:
        if isinstance(other, SortedAbstractSet):
            i1 = ((x, 0) for x in self)
            i2 = ((x, 1) for x in other)
            return len(self) >= len(other) and 1 not in (
                next(group)[1]
                for key, group in groupby(merge(i1, i2), key=lambda xi: xi[0])
            )
        if isinstance(other, AbstractSet):
            return type(other).__le__(other, self)
        else:
            return NotImplementedsets")

    def __gt__(self: Self, other: Any, /) -> bool:
        if isinstance(other, SortedAbstractSet):
            i1 = ((x, 0) for x in self)
            i2 = ((x, 1) for x in other)
            return len(self) > len(other) and 1 not in (
                next(group)[1]
                for key, group in groupby(merge(i1, i2), key=lambda xi: xi[0])
            )
        if isinstance(other, AbstractSet):
            return type(other).__lt__(other, self)
        else:
            return NotImplemented

    def __iter__(self: Self, /) -> Iterator[T_co]:
        return iter(self._sequence)

    def __le__(self: Self, other: Any, /) -> bool:
        if isinstance(other, SortedAbstractSet):
            i1 = ((x, 1) for x in self)
            i2 = ((x, 0) for x in other)
            return len(self) <= len(other) and 1 not in (
                next(group)[1]
                for key, group in groupby(merge(i1, i2), key=lambda xi: xi[0])
            )
        elif isinstance(other, AbstractSet):
            return type(other).__ge__(other, self)
        else:
            return NotImplementedsets")

    def __len__(self: Self, /) -> int:
        return len(self._sequence)

    def __lt__(self: Self, other: Any, /) -> bool:
        if isinstance(other, SortedAbstractSet):
            i1 = ((x, 1) for x in self)
            i2 = ((x, 0) for x in other)
            return len(self) < len(other) and 1 not in (
                next(group)[1]
                for key, group in groupby(merge(i1, i2), key=lambda xi: xi[0])
            )
        elif isinstance(other, AbstractSet):
            return type(other).__gt__(other, self)
        else:
            return NotImplemented

    def __ne__(self: Self, other: Any, /) -> bool:
        return SortedSequence.__ne__(self, other)

    @overload
    def __or__(self: Self, other: "SortedAbstractSet[T]", /) -> "SortedAbstractSet[Union[T, T_co]]": ...

    @overload
    def __or__(self: Self, other: AbstractSet[S], /) -> AbstractSet[Union[S, T_co]]: ...

    def __or__(self, other, /):
        # Find common non-abstract parent class.
        for cls in type(self).mro():
            if isinstance(other, cls) and issubclass(cls, SortedAbstractSet) and not isabstract(cls):
                return cls.__from_sorted__(key for key, _ in groupby(merge(self, other)))
        return NotImplemented

    def __ror__(self: Self, other: AbstractSet[S], /) -> AbstractSet[Union[S, T_co]]:
        return NotImplemented

    def __reversed__(self: Self, /) -> Iterator[T_co]:
        return reversed(self._sequence)

    def __sub__(self: Self, other: AbstractSet[Any], /) -> "SortedAbstractSet[T_co]":
        # Find common non-abstract parent class.
        for cls in type(self).mro():
            if isinstance(other, cls) and issubclass(cls, SortedAbstractSet) and not isabstract(cls):
                return cls.__from_sorted__(key for key in self if key not in other)
        return NotImplemented

    def __rsub__(self: Self, other: AbstractSet[S], /) -> AbstractSet[S]:
        return NotImplemented

    @overload
    def __xor__(self: Self, other: "SortedAbstractSet[T]", /) -> "SortedAbstractSet[Union[T, T_co]]": ...

    @overload
    def __xor__(self: Self, other: AbstractSet[S], /) -> AbstractSet[Union[S, T_co]]: ...

    def __xor__(self, other, /):
        # Find common non-abstract parent class.
        for cls in type(self).mro():
            if isinstance(other, cls) and issubclass(cls, SortedAbstractSet) and not isabstract(cls):
                return cls.__from_sorted__(
                    key
                    for key, group in groupby(merge(self, other))
                    if sum(1 for _ in group) == 1
                )
        return NotImplemented

    def __rxor__(self: Self, other: AbstractSet[S], /) -> AbstractSet[Union[S, T_co]]:
        return NotImplemented

    def copy(self: Self, /) -> Self:
        return copy.copy(self)

    def difference(self: Self, /, *iterables: Iterable[T], /) -> "SortedAbstractSet[T_co]":
        if len(iterables) == 0:
            return self.copy()
        s = set()
        sets = [s]
        for iterable in iterables:
            if isinstance(iterable, (AbstractSet, Mapping, SortedCollection)):
                sets.append(iterable)
            elif isinstance(iterable, Iterable):
                s.update(x for x in iterable if x in self)
            else:
                raise TypeError(f"expected iterables, got {iterable!r}")
        del iterables
        return type(self).__from_sorted__(
            x
            for x in self
            if not any((x in s) for s in sets)
        )

    def intersection(self: Self, /, *iterables: Iterable[T], /) -> "SortedAbstractSet[T_co]":
        if len(iterables) == 0:
            return self.copy()
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
            return type(self).__from_sorted__(
                key
                for key, group in groupby(merge(*shorts))
                if all(False for _ in islice(group, len(shorts), None))
                if all((key in s) for s in sets)
            )
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
            return type(self).__from_iterable__(
                x
                for x in iterable
                if all((x in s) for s in sets)
            )

    def isdisjoint(self: Self, iterable: Iterable[T], /) -> bool:
        if isinstance(iterable, SortedCollection):
            if len(self) < len(iterable):
                return not any((x in other) for x in self)
            else:
                return not any((x in self) for x in other)
        elif isinstance(iterable, AbstractSet):
            return iterable.isdisjoint(self)
        elif isinstance(iterable, Iterable):
            return not any((x in self) for x in other)
        else:
            raise TypeError(f"isdisjoint expected an iterable, got {iterable!r}")

    def issubset(self: Self, iterable: Iterable[T], /) -> bool:
        if isinstance(iterable, SortedCollection):
            if len(self) < len(iterable) // 8:
                return all((x in iterable) for x in self)
            else:
                i1 = ((x, 1) for x in self)
                i2 = ((x, 0) for x in iterable)
                return 1 not in (
                    next(group)[1]
                    for _, group in groupby(merge(i1, i2), key=lambda xi: xi[0])
                )
        elif isinstance(iterable, AbstractSet):
            return iterable.issuperset(self)
        elif isinstance(iterable, Iterable):
            return len({x for x in iterable if x in self}) == len(self)
        else:
            raise TypeError(f"issubset expected an iterable, got {iterable!r}")

    def issuperset(self: Self, iterable: Iterable[T], /) -> bool:
        if isinstance(iterable, SortedCollection):
            if len(iterable) < len(self) // 8:
                return all((x in self) for x in iterable)
            else:
                i1 = ((x, 0) for x in self)
                i2 = ((x, 1) for x in iterable)
                return 1 not in (
                    next(group)[1]
                    for _, group in groupby(merge(i1, i2), key=lambda xi: xi[0])
                )
        elif isinstance(iterable, Iterable):
            return all((x in self) for x in iterable)
        else:
            raise TypeError(f"issuperset expected an iterable, got {iterable!r}")

    def symmetric_difference(self: Self, /, *iterables: Iterable[T], /) -> "SortedAbstractSet[Union[T, T_co]]":
        if len(iterables) == 0:
            return self.copy()
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
        return type(self).__from_sorted__(
            key
            for key, group in groupby(merge(*sorteds))
            if (sum(1 for _ in group) + sum(1 for s in sets if key in s)) % 2 == 1
        )

    def union(self: Self, /, *iterables: Iterable[T], /) -> "SortedAbstractSet[Union[T, T_co]]":
        if len(iterables) == 0:
            return self.copy()
        others = []
        sorteds = [self]
        for iterable in iterables:
            if isinstance(iterable, SortedCollection):
                sorteds.append(iterable)
            elif not isinstance(iterable, Iterable):
                others.append(iterable)
            else:
                raise TypeError(f"expected iterables, got {iterable!r}")
        del iterables
        if len(others) == 0:
            return type(self).__from_sorted__(
                key
                for key, _ in groupby(merge(*sorteds))
            )
        else:
            iterator = (key for key, _ in groupby(merge(*sorteds)))
            return type(self).__from_iterable__(chain(iterator, *others))

    @property
    @abstractmethod
    def _sequence(self: Self, /) -> SortedSequence[T_co]:
        raise NotImplementedError("_sequence is a required property for sorted abstract sets")
