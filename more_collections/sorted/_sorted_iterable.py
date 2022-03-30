from __future__ import annotations
import sys
from typing import Generic, TypeVar

if sys.version_info < (3, 9):
    from typing import Iterable, Iterator
else:
    from collections.abc import Iterable, Iterator

from ._abc_iterable import SortedIterable, SortedIterator

__all__ = ["SortedUserIterable", "SortedUserIterator"]

T = TypeVar("T")


class SortedUserIterable(SortedIterable[T], Generic[T]):
    __iterable: Iterable[T]

    def __init__(self: SortedUserIterable[T], iterable: Iterable[T], /) -> None:
        if isinstance(iterable, Iterable):
            self.__iterable = iterable
        else:
            raise TypeError(f"{type(self).__name__} expected an iterable, got {iterable!r}")

    def __iter__(self: SortedUserIterable[T], /) -> SortedUserIterator[T]:
        return SortedUserIterator(self.__iterable)


class SortedUserIterator(SortedIterator[T], Generic[T]):
    __iterator: Iterator[T]

    def __init__(self: SortedUserIterator[T], iterable: Iterable[T], /) -> None:
        if isinstance(iterable, Iterable):
            self.__iterator = iter(iterable)
        else:
            raise TypeError(f"{type(self).__name__} expected an iterable, got {iterable!r}")

    def __next__(self: SortedUserIterator[T], /) -> T:
        return next(self.__iterator)
