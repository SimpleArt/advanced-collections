from __future__ import annotations
import sys
from abc import ABC, abstractmethod
from copy import copy, deepcopy
from typing import Any, Generic, Type, TypeVar

if sys.version_info < (3, 9):
    from typing import Iterable
else:
    from collections.abc import Iterable

from ._abc_iterable import SortedIterable

__all__ = ["SortedConstructor"]

Self = TypeVar("Self", bound="SortedConstructor")
T = TypeVar("T")

reprs_seen: set[int] = {*()}


class SortedConstructor(SortedIterable[T], ABC, Generic[T]):

    __slots__ = ()

    def __copy__(self: Self, /) -> Self:
        return type(self).from_sorted(self)  # type: ignore

    def __deepcopy__(self: Self, /) -> Self:
        return type(self).from_sorted(deepcopy(x) for x in self)  # type: ignore

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

    def copy(self: Self, /) -> Self:
        return copy(self)

    @classmethod
    def from_iterable(cls: Type[SortedConstructor[T]], iterable: Iterable[T], /) -> SortedConstructor[T]:
        if isinstance(iterable, Iterable):
            return cls.from_sorted(sorted(iterable))  # type: ignore
        else:
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")

    @classmethod
    @abstractmethod
    def from_sorted(cls: Type[SortedConstructor[T]], iterable: Iterable[T], /) -> SortedConstructor[T]:
        raise NotImplementedError("from_sorted is a required method for sorted constructors")
