from __future__ import annotations
import collections.abc
import operator
import sys
from abc import ABC, abstractmethod
from copy import copy, deepcopy
from typing import Any, Generic, Literal, Optional, SupportsIndex, Type, TypeVar, Union, overload

if sys.version_info < (3, 9):
    from typing import AbstractSet, Callable, Iterable, Iterator, MutableSet, Sequence, Set as set
else:
    from collections.abc import Set as AbstractSet, Callable, Iterable, Iterator, MutableSet, Sequence

from ._abc_key_iterable import SortedKeyIterator
from ._abc_key_sequence import SortedKeySequence, SortedKeyMutableSequence

__all__ = ["SortedKeySet", "SortedKeyMutableSet"]

Self = TypeVar("Self", bound="SortedKeyMutableSet")
S = TypeVar("S")
T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


class SortedKeySet(AbstractSet[T], SortedKeySequence[T], ABC, Generic[T]):

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
        if isinstance(index, slice):
            range_ = range(len(self))[index]
            if range_.step < 0:
                return type(self).from_sorted((self._sequence[i] for i in reversed(range_)), self.key)
            else:
                return type(self).from_sorted((self._sequence[i] for i in range_), self.key)
        else:
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
            return self.union(other)
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
            return self.symmetric_difference(other)
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
        set_: set[T]
        if isinstance(self._set, set):
            set_ = self._set.difference(*iterables)
        else:
            set_ = {*self._set}
            set_.difference_update(*iterables)
        return type(self).from_iterable(set_, self.key)

    @classmethod
    def from_iterable(cls: Type[SortedKeySet[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeySet[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")
        elif not callable(key):
            raise TypeError(f"from_iterable expects a callable key, got {key!r}")
        else:
            return cls.from_sorted(sorted(set(iterable), key=key), key)

    @classmethod
    @abstractmethod
    def from_sorted(cls: Type[SortedKeySet[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeySet[T]:
        raise NotImplementedError("from_sorted is a required method for sorted key sets")

    def index(self: SortedKeySet[Any], value: Any, start: int = 0, stop: Optional[int] = None, /, mode: Literal["exact", "left", "right"] = "exact") -> int:
        return self._sequence.index(value, start, stop, mode=mode)

    def intersection(self: SortedKeySet[T], /, *iterables: Iterable[Any]) -> SortedKeySet[T]:
        if len(iterables) == 0:
            return self.copy()
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"intersection argument is not iterable, got {iterable!r}")
        set_: set[T]
        if isinstance(self._set, set):
            set_ = self._set
        else:
            set_ = {*self._set}
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


class SortedKeyMutableSet(SortedKeySet[T_co], set[T_co], ABC, Generic[T_co]):

    __slots__ = ()

    def __and__(self: SortedKeyMutableSet[T_co], other: Iterable[Any], /) -> SortedKeyMutableSet[T_co]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)
        else:
            return NotImplemented

    def __copy__(self: Self, /) -> Self:
        return type(self).from_sorted(self, self.key)  # type: ignore

    def __deepcopy__(self: Self, /) -> Self:
        return type(self).from_sorted((deepcopy(x) for x in self), self.key)  # type: ignore

    @overload
    def __getitem__(self: SortedKeyMutableSet[T_co], index: int, /) -> T_co:
        ...

    @overload
    def __getitem__(self: SortedKeyMutableSet[T_co], index: slice, /) -> SortedKeyMutableSet[T_co]:
        ...

    def __getitem__(self, index, /):
        if isinstance(index, slice):
            range_ = range(len(self))[index]
            if range_.step < 0:
                range_ = range_[::-1]
                index = slice(range_.start, range_.stop, range_.step)
            return self._sequence[index]
        else:
            return self._sequence[index]

    def __iand__(self: SortedKeyMutableSet[T_co], other: Iterable[Any], /) -> SortedKeyMutableSet[T_co]:
        if isinstance(other, Iterable):
            self.intersection_update(other)
            return self
        else:
            return NotImplemented

    def __ior__(self: SortedKeyMutableSet[T_co], other: Iterable[T], /) -> SortedKeyMutableSet[Union[T_co, T]]:
        if isinstance(other, Iterable):
            self.update(other)  # type: ignore
            return self  # type: ignore
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
            self.symmetric_difference_update(other)  # type: ignore
            return self  # type: ignore
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

    def copy(self: Self, /) -> Self:
        return copy(self)

    def difference(self: SortedKeyMutableSet[T_co], /, *iterables: Iterable[Any]) -> SortedKeyMutableSet[T_co]:
        return super().difference(*iterables)  # type: ignore

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

    @classmethod
    @abstractmethod
    def from_sorted(cls: Type[SortedKeyMutableSet[T_co]], iterable: Iterable[T_co], /, key: Callable[[T_co], Any]) -> SortedKeyMutableSet[T_co]:
        raise NotImplementedError("from_sorted is a required method for sorted key mutable sets")

    def intersection(self: SortedKeyMutableSet[T_co], /, *iterables: Iterable[Any]) -> SortedKeyMutableSet[T_co]:
        return super().intersection(*iterables)  # type: ignore

    def intersection_update(self: SortedKeyMutableSet[Any], /, *iterables: Iterable[Any]) -> None:
        if len(iterables) == 0:
            self.clear()
            return
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"intersection_update argument is not iterable, got {iterable!r}")
        set_: set[Any]
        if len(iterables) == 1:
            if isinstance(self._set, set):
                set_ = self._set.symmetric_difference(iterables[0])
            elif isinstance(iterables[0], set):
                set_ = iterables[0].symmetric_difference(self._set)
            else:
                set_ = {*self._set}
                set_.symmetric_difference_update(iterables[0])
        else:
            if isinstance(self._set, set):
                set_ = self._set.intersection(*iterables)
            else:
                set_ = {*self._set}
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
        return super().symmetric_difference(*iterables)  # type: ignore

    def symmetric_difference_update(self: SortedKeyMutableSet[T_co], /, *iterables: Iterable[T_co]) -> None:
        if len(iterables) == 0:
            return
        for iterable in iterables:
            if not isinstance(iterable, Iterable):
                raise TypeError(f"symmetric_difference_update argument is not iterable, got {iterable!r}")
        set_: set[Any] = {*iterables[0]}
        for i in range(1, len(iterables)):
            set_.symmetric_difference_update(iterables[i])
        for x in set_:
            if x in self:
                self.remove(x)
            else:
                self.add(x)

    def union(self: SortedKeyMutableSet[T_co], /, *iterables: Iterable[T]) -> SortedKeyMutableSet[Union[T_co, T]]:
        return super().union(*iterables)  # type: ignore

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


if sys.version_info < (3, 9):
    collections.abc.Set.register(SortedKeySet)
    collections.abc.MutableKeySet.register(SortedKeyMutableSet)
