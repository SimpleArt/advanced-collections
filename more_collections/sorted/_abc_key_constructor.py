from __future__ import annotations
import sys
from abc import ABC, abstractmethod
from copy import copy, deepcopy
from typing import Any, Generic, Type, TypeVar

if sys.version_info < (3, 9):
    from typing import Callable, Iterable
else:
    from collections.abc import Callable, Iterable

from ._abc_key_iterable import SortedKeyIterable

__all__ = ["SortedKeyConstructor"]

Self = TypeVar("Self", bound="SortedKeyConstructor")
T = TypeVar("T")

reprs_seen: set[int] = {*()}


class SortedKeyConstructor(SortedKeyIterable[T], ABC, Generic[T]):

    def __copy__(self: Self, /) -> Self:
        return type(self).from_sorted(self, self.key)  # type: ignore

    def __deepcopy__(self: Self, /) -> Self:
        return type(self).from_sorted((deepcopy(x) for x in self), self.key)  # type: ignore

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

    def copy(self: Self, /) -> Self:
        return copy(self)

    @classmethod
    def from_iterable(cls: Type[SortedKeyConstructor[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeyConstructor[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")
        elif not callable(key):
            raise TypeError(f"from_iterable expects a callable key, got {key!r}")
        else:
            return cls.from_sorted(sorted(iterable, key=key), key)

    @abstractmethod
    @classmethod
    def from_sorted(cls: Type[SortedKeyConstructor[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeyConstructor[T]:
        raise NotImplementedError("from_sorted is a required method for sorted key constructors")

    @property
    @abstractmethod
    def key(self: SortedKeyConstructor[T], /) -> Callable[[T], Any]:
        raise NotImplementedError("key is a required property for sorted key constructors")
