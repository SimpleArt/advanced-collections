from __future__ import annotations
import collections.abc
import sys
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

if sys.version_info < (3, 9):
    from typing import Iterable, Iterator
else:
    from collections.abc import Iterable, Iterator

__all__ = ["SortedKeyIterable", "SortedKeyIterator"]

Self = TypeVar("Self", bound="SortedKeyIterator")
T = TypeVar("T")


class SortedKeyIterable(Iterable[T], ABC, Generic[T]):

    __slots__ = ()

    @abstractmethod
    def __iter__(self: SortedKeyIterable[T], /) -> SortedKeyIterator[T]:
        raise NotImplementedError("__iter__ is a required method for sorted key iterables")


class SortedKeyIterator(Iterator[T], SortedKeyIterable[T], ABC, Generic[T]):

    __slots__ = ()

    def __iter__(self: Self, /) -> Self:
        return self

    @abstractmethod
    def __next__(self: SortedKeyIterator[T], /) -> T:
        raise NotImplementedError("__next__ is a required method for sorted key iterators")


if sys.version_info < (3, 9):
    collections.abc.Iterable.register(SortedKeyIterable)
    collections.abc.Iterator.register(SortedKeyIterator)
