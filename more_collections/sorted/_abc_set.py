from __future__ import annotations
import collections.abc
import operator
import sys
from abc import ABC, abstractmethod
from copy import copy, deepcopy
from typing import Any, Generic, Literal, Optional, SupportsIndex, Type, TypeVar, Union, overload

if sys.version_info < (3, 9):
    from typing import AbstractSet, Iterable, Iterator, MutableSet, Sequence, Set as set
else:
    from collections.abc import Set as AbstractSet, Iterable, Iterator, MutableSet, Sequence

from ._abc_iterable import SortedIterator
from ._abc_sequence import SortedSequence, SortedMutableSequence

__all__ = ["SortedSet", "SortedMutableSet"]

Self = TypeVar("Self", bound="SortedMutableSet")
S = TypeVar("S")
T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


class SortedSet(AbstractSet[T], SortedSequence[T], ABC, Generic[T]):

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
    def __getitem__(self: SortedSet[T], index: slice, /) -> SortedSet[T]:
        ...

    def __getitem__(self, index, /):
        if isinstance(index, slice):
            range_ = range(len(self))[index]
            if range_.step < 0:
                return type(self).from_sorted(self._sequence[i] for i in reversed(range_))
            else:
                return type(self).from_sorted(self._sequence[i] for i in range_)
        else:
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
        set_: set[T]
        if isinstance(self._set, set):
            set_ = self._set.difference(*iterables)
        else:
            set_ = {*self._set}
            set_.difference_update(*iterables)
        return type(self).from_iterable(set_)

    @classmethod
    def from_iterable(cls: Type[SortedSet[T]], iterable: Iterable[T], /) -> SortedSet[T]:
        if isinstance(iterable, Iterable):
            return cls.from_sorted(sorted({*iterable}))  # type: ignore
        else:
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")

    @abstractmethod
    @classmethod
    def from_sorted(cls: Type[SortedSet[T]], iterable: Iterable[T], /) -> SortedSet[T]:
        raise NotImplementedError("from_sorted is a required method for sorted sets")

    def index(self: SortedSet[Any], value: Any, /, start: int = 0, stop: Optional[int] = None, *, mode: Literal["exact", "left", "right"] = "exact") -> int:
        return self._sequence.index(value, start, stop, mode=mode)

    def intersection(self: SortedSet[T], /, *iterables: Iterable[Any]) -> SortedSet[T]:
        if len(iterables) == 0:
            return self.copy()
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"intersection argument is not iterable, got {iterable!r}")
        set_: set[T]
        if isinstance(self._set, set):
            set_ = self._set.intersection(*iterables)
        else:
            set_ = {*self._set}
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
            return self.copy()  # type: ignore
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"symmetric_difference argument is not iterable, got {iterable!r}")
        set_: set[Union[T, S]]
        if isinstance(self._set, set):
            set_ = self._set.symmetric_difference(iterables[0])
        else:
            set_ = {*self._set}
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


class SortedMutableSet(SortedSet[T_co], set[T_co], ABC, Generic[T_co]):

    __slots__ = ()

    def __and__(self: SortedMutableSet[T_co], other: Iterable[Any], /) -> SortedMutableSet[T_co]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)
        else:
            return NotImplemented

    def __copy__(self: Self, /) -> Self:
        return type(self).from_sorted(self, self.key)  # type: ignore

    def __deepcopy__(self: Self, /) -> Self:
        return type(self).from_sorted((deepcopy(x) for x in self), self.key)  # type: ignore

    @overload
    def __getitem__(self: SortedMutableSet[T_co], index: int, /) -> T_co:
        ...

    @overload
    def __getitem__(self: SortedMutableSet[T_co], index: slice, /) -> SortedMutableSet[T_co]:
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
            self.update(other)  # type: ignore
            return self  # type: ignore
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
            self.symmetric_difference_update(other)  # type: ignore
            return self  # type: ignore
        else:
            return NotImplemented

    def __or__(self: SortedMutableSet[T_co], other: Iterable[T], /) -> SortedMutableSet[Union[T_co, T]]:
        if isinstance(other, AbstractSet):
            return self.union(other)
        else:
            return NotImplemented

    __ror__ = __or__

    def __rand__(self: SortedMutableSet[Any], other: Iterable[T], /) -> SortedMutableSet[T]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)  # type: ignore
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
            return self.symmetric_difference(other)
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

    def copy(self: Self, /) -> Self:
        return copy(self)

    def difference(self: SortedMutableSet[T_co], /, *iterables: Iterable[Any]) -> SortedMutableSet[T_co]:
        return super().difference(*iterables)  # type: ignore

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
            return cls.from_sorted(sorted({*iterable}))  # type: ignore
        else:
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")

    @abstractmethod
    @classmethod
    def from_sorted(cls: Type[SortedMutableSet[T]], iterable: Iterable[T], /) -> SortedMutableSet[T]:
        raise NotImplementedError("from_sorted is a required method for sorted mutable sets")

    def intersection(self: SortedMutableSet[T_co], /, *iterables: Iterable[Any]) -> SortedMutableSet[T_co]:
        return super().intersection(*iterables)  # type: ignore

    def intersection_update(self: SortedMutableSet[Any], /, *iterables: Iterable[Any]) -> None:
        if len(iterables) == 0:
            self.clear()
            return
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"intersection_update argument is not iterable, got {iterable!r}")
        set_: set[T_co]
        if isinstance(self._set, set):
            set_ = self._set.intersection(*iterables)
        else:
            set_ = {*self._set}
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
        return super().symmetric_difference(*iterables)  # type: ignore

    def symmetric_difference_update(self: SortedMutableSet[T_co], /, *iterables: Iterable[T_co]) -> None:
        if len(iterables) == 0:
            return
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"symmetric_difference_update argument is not iterable, got {iterable!r}")
        set_: set[T_co] = {*iterables[0]}
        for i in range(1, len(iterables)):
            set_.symmetric_difference_update(iterables[i])
        for x in set_:
            if x in self:
                self.remove(x)
            else:
                self.add(x)

    def union(self: SortedMutableSet[T_co], /, *iterables: Iterable[T]) -> SortedMutableSet[Union[T_co, T]]:
        return super().union(*iterables)  # type: ignore

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


if sys.version_info < (3, 9):
    collections.abc.Set.register(SortedSet)
    collections.abc.MutableSet.register(SortedMutableSet)
