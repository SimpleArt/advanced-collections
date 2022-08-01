from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Reversible, Sized
from typing import Any, Protocol, Type, TypeVar, Union, runtime_checkable

from advanced_collections._src.comparable import SupportsRichHashableComparison

T1_co = TypeVar("T1_co", bound=SupportsRichHashableComparison)
T2_co = TypeVar("T2_co", bound=SupportsRichHashableComparison)

Self = TypeVar("Self", bound="SortedCollection")


@runtime_checkable
class SortedCollection(Reversible[T2_co], Sized, Protocol[T1_co, T2_co]):

    @classmethod
    def __from_iterable__(cls: Type[Self], iterable: Iterable[T1_co], /) -> "SortedCollection[T1_co, T2_co]": ...

    @classmethod
    def __from_sorted__(cls: Type[Self], iterable: Iterable[T1_co], /) -> "SortedCollection[T1_co, T2_co]": ...
