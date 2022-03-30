from __future__ import annotations
import collections.abc
import sys
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

if sys.version_info < (3, 9):
    from typing import Iterable, Iterator
else:
    from collections.abc import Iterable, Iterator

__all__ = ["SortedIterable", "SortedIterator"]

Self = TypeVar("Self", bound="SortedIterator")
T = TypeVar("T")


class SortedIterable(Iterable[T], ABC, Generic[T]):

    __slots__ = ()

    @abstractmethod
    def __iter__(self: SortedIterable[T], /) -> SortedIterator[T]:
        raise NotImplementedError("__iter__ is a required method for sorted iterables")


class SortedIterator(Iterator[T], SortedIterable[T], ABC, Generic[T]):

    __slots__ = ()

    def __iter__(self: Self, /) -> Self:
        return self

    @abstractmethod
    def __next__(self: SortedIterator[T], /) -> T:
        raise NotImplementedError("__next__ is a required method for sorted iterators")


if sys.version_info < (3, 9):
    collections.abc.Iterable.register(SortedIterable)
    collections.abc.Iterator.register(SortedIterator)
