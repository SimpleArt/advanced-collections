from __future__ import annotations
import sys
from abc import ABC, abstractmethod
from collections.abc import Sized
from typing import Any, Generic, Type, TypeVar, Union

if sys.version_info < (3, 9):
    from typing import Callable, Iterable, Reversible
else:
    from collections.abc import Callable, Iterable, Reversible

from advanced_collections._src.comparable import SupportsRichHashableComparison

__all__ = ["SortedCollection"]

Self = TypeVar("Self", bound="SortedCollection")
T1_co = TypeVar("T1_co", bound=SupportsRichHashableComparison)
T2_co = TypeVar("T2_co", bound=SupportsRichHashableComparison)


class SortedCollection(Iterable[T2_co], Reversible[T2_co], Sized, ABC, Generic[T1_co, T2_co]):

    __slots__ = ()

    @classmethod
    def __from_iterable__(cls: Type[Self], iterable: Iterable[T1_co], /) -> SortedCollection[T1_co, T2_co]:
        if isinstance(iterable, Iterable):
            return cls.from_sorted(sorted(iterable))
        else:
            raise TypeError(f"{cls.__name__}.__from_iterable__ expected an iterable, got {iterable!r}")

    @classmethod
    @abstractmethod
    def __from_sorted__(cls: Type[Self], iterable: Iterable[T1_co], /) -> SortedCollection[T1_co, T2_co]:
        raise NotImplementedError(f"__from_sorted__ is a required method for sorted collections")
