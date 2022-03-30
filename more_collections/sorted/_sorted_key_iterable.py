from __future__ import annotations
import sys
from typing import Generic, TypeVar

if sys.version_info < (3, 9):
    from typing import Iterable, Iterator
else:
    from collections.abc import Iterable, Iterator

from ._abc_key_iterable import SortedKeyIterable, SortedKeyIterator

__all__ = ["SortedKeyUserIterable", "SortedKeyUserIterator"]

T = TypeVar("T")


class SortedKeyUserIterable(SortedKeyIterable[T], Generic[T]):
    __iterable: Iterable[T]

    def __init__(self: SortedKeyUserIterable[T], iterable: Iterable[T], /) -> None:
        if isinstance(iterable, Iterable):
            self.__iterable = iterable
        else:
            raise TypeError(f"{type(self).__name__} expected an iterable, got {iterable!r}")

    def __iter__(self: SortedKeyUserIterable[T], /) -> SortedKeyUserIterator[T]:
        return SortedKeyUserIterator(self.__iterable)


class SortedKeyUserIterator(SortedKeyIterator[T], Generic[T]):
    __iterator: Iterator[T]

    def __init__(self: SortedKeyUserIterator[T], iterable: Iterable[T], /) -> None:
        if isinstance(iterable, Iterable):
            self.__iterator = iter(iterable)
        else:
            raise TypeError(f"{type(self).__name__} expected an iterable, got {iterable!r}")

    def __next__(self: SortedKeyUserIterator[T], /) -> T:
        return next(self.__iterator)
