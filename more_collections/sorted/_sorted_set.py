from __future__ import annotations
import sys
from typing import Any, Generic, Optional, Type, TypeVar

if sys.version_info < (3, 9):
    from typing import Callable, Iterable, Set as set
else:
    from collections.abc import Callable, Iterable

from ._abc_set import SortedMutableSet
from ._abc_key_set import SortedKeyMutableSet
from ._sorted_list import SortedList, SortedKeyList

__all__ = ["SortedSet", "SortedKeySet"]

T = TypeVar("T")

reprs_seen: set[int] = {*()}


class SortedSet(SortedMutableSet[T], set[T], Generic[T]):
    __sequence: SortedList[T]
    __set: set[T]

    __slots__ = {
        "__sequence":
            "Stores the data in order using a sorted list.",
        "__set":
            "Stores unique elements using fast hashing.",
    }

    def __init__(self: SortedSet[T], iterable: Optional[Iterable[T]] = None, /) -> None:
        if iterable is None:
            self.__set = {*()}
            self.__sequence = SortedList()
        elif isinstance(iterable, Iterable):
            self.__set = {*iterable}
            self.__sequence = SortedList(self.__set)
        else:
            raise TypeError(f"{type(self).__name__} expected an iterable, got {iterable!r}")

    @classmethod
    def from_iterable(cls: Type[SortedSet[T]], iterable: Iterable[T], /) -> SortedSet[T]:
        if isinstance(iterable, Iterable):
            return cls(iterable)  # type: ignore
        else:
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")

    def __repr__(self: SortedSet[Any], /) -> str:
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

    @classmethod
    def from_sorted(cls: Type[SortedSet[T]], iterable: Iterable[T], /) -> SortedSet[T]:
        if isinstance(iterable, Iterable):
            return cls(iterable)  # type: ignore
        else:
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")

    @property
    def _sequence(self: SortedSet[T], /) -> SortedList[T]:
        return self.__sequence

    @property
    def _set(self: SortedSet[T], /) -> set[T]:
        return self.__set


class SortedKeySet(SortedKeyMutableSet[T], set[T], Generic[T]):
    __sequence: SortedKeyList[T]
    __set: set[T]

    __slots__ = {
        "__sequence":
            "Stores the data in order using a sorted key list.",
        "__set":
            "Stores unique elements using fast hashing.",
    }

    def __init__(self: SortedKeySet[T], iterable: Optional[Iterable[T]] = None, /, *, key: Callable[[T], Any]) -> None:
        if iterable is not None and not isinstance(iterable, Iterable):
            raise TypeError(f"{type(self).__name__} expected an iterable, got {iterable!r}")
        elif not callable(key):
            raise TypeError(f"{type(self).__name__} expected a callable key, got {key!r}")
        elif iterable is None:
            self.__set = {*()}
            self.__sequence = SortedKeyList(key=key)
        else:
            self.__set = {*iterable}
            self.__sequence = SortedKeyList(self.__set, key=key)

    def __repr__(self: SortedKeySet[Any], /) -> str:
        if id(self) in reprs_seen:
            return "..."
        elif len(self) == 0:
            return f"{type(self).__name__}(key={self.key!r})"
        reprs_seen.add(id(self))
        try:
            data = ", ".join([repr(x) for x in self])
            return f"{type(self).__name__}([{data}], key={self.key!r})"
        finally:
            reprs_seen.remove(id(self))

    @classmethod
    def from_iterable(cls: Type[SortedKeySet[T]], iterable: Iterable[T], /) -> SortedKeySet[T]:
        if isinstance(iterable, Iterable):
            return cls(iterable)
        else:
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")

    @classmethod
    def from_sorted(cls: Type[SortedKeySet[T]], iterable: Iterable[T], /) -> SortedKeySet[T]:
        if isinstance(iterable, Iterable):
            return cls(iterable)
        else:
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")

    @property
    def key(self: SortedKeySet[T], /) -> Callable[[T], Any]:
        return self.__sequence.key

    @property
    def _sequence(self: SortedKeySet[T], /) -> SortedKeyList[T]:
        return self.__sequence

    @property
    def _set(self: SortedKeySet[T], /) -> set[T]:
        return self.__set
