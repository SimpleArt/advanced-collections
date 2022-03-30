from __future__ import annotations
import collections.abc
import sys
from abc import ABC, abstractmethod
from bisect import bisect_left, bisect_right
from itertools import islice
from typing import Any, Generic, Literal, Optional, Type, TypeVar, Union, overload

if sys.version_info < (3, 9):
    from typing import Iterable, Iterator, MutableSequence, Sequence
else:
    from collections.abc import Iterable, Iterator, MutableSequence, Sequence

from ._abc_constructor import SortedConstructor
from ._abc_iterable import SortedIterable, SortedIterator

__all__ = ["SortedSequence", "SortedMutableSequence"]

T = TypeVar("T")

def iter_until(iterable: SortedIterable[T], stop_at: T, /) -> Iterator[T]:
    for x in iterable:
        if x < stop_at:  # type: ignore
            yield x
        else:
            break


class SortedInterval(Generic[T]):
    _sequence: SortedSequence[T]

    def __init__(self: SortedInterval[T], sequence: SortedSequence[T], /) -> None:
        if not isinstance(sequence, SortedSequence):
            raise TypeError(f"{type(self).__name__} expected a sorted sequence, got {sequence!r}")
        self._sequence = sequence

    def __getitem__(self: SortedInterval[T], interval: slice, /) -> SortedIterator[T]:
        if not isinstance(interval, slice):
            raise TypeError("sorted intervals only support slicing")
        elif interval.step is not None:
            raise ValueError("step sizes are not supported by sorted intervals")
        elif interval.start is interval.stop is None:
            return iter(self._sequence)
        elif interval.start is None:
            from more_collections.sorted import SortedUserIterator
            return SortedUserIterator(iter_until(self._sequence, interval.stop))
        elif interval.stop is None:
            start = self._sequence.index(interval.start, mode="left")
            if len(self._sequence) * 7 // 8 < start:
                iterator = iter(self._sequence)
                for _ in range(start):
                    next(iterator)
                return iterator
            else:
                from more_collections.sorted import SortedUserIterator
                return SortedUserIterator(self._sequence[i] for i in range(start, len(self._sequence)))
        else:
            from more_collections.sorted import SortedUserIterator
            start = self._sequence.index(interval.start, mode="left")
            stop = self._sequence.index(interval.stop, mode="left")
            if len(self._sequence) // 8 < stop - start:
                iterator = iter(self._sequence)
                for _ in range(start):
                    next(iterator)
                return SortedUserIterator(islice(iterator, stop - start))
            else:
                return SortedUserIterator(self._sequence[i] for i in range(start, stop))


class SortedSequence(Sequence[T], SortedConstructor[T], ABC, Generic[T]):

    __slots__ = ()

    def __contains__(self: SortedSequence[Any], value: Any, /) -> bool:
        i = bisect_left(self, value)
        return 0 <= i < len(self) and not (value is not self[i] != value)

    @overload
    def __getitem__(self: SortedSequence[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: SortedSequence[T], index: slice, /) -> Sequence[T]:
        ...

    @abstractmethod
    def __getitem__(self, index, /):
        raise NotImplementedError("__getitem__ is a required method for sorted sequences")

    @abstractmethod
    def __iter__(self: SortedSequence[T], /) -> SortedIterator[T]:
        raise NotImplementedError("__iter__ is a required method for sorted sequences")

    @abstractmethod
    def __len__(self: SortedSequence[Any], /) -> int:
        raise NotImplementedError("__len__ is a required method for sorted sequences")

    @abstractmethod
    def __reversed__(self: SortedSequence[T], /) -> Iterator[T]:
        raise NotImplementedError("__reversed__ is a required method for sorted sequences")

    def count(self: SortedSequence[Any], value: Any, /) -> int:
        hi = bisect_right(self, value)
        lo = bisect_left(self, value, 0, hi)
        return hi - lo

    @classmethod
    def from_iterable(cls: Type[SortedSequence[T]], iterable: Iterable[T], /) -> SortedSequence[T]:
        if isinstance(iterable, Iterable):
            return cls.from_sorted(sorted(iterable))  # type: ignore
        else:
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")

    @classmethod
    @abstractmethod
    def from_sorted(cls: Type[SortedSequence[T]], iterable: Iterable[T], /) -> SortedSequence[T]:
        raise NotImplementedError(f"from_sorted is a required method for sorted sequences")

    def index(self: SortedSequence[Any], value: Any, /, start: int = 0, stop: Optional[int] = None, *, mode: Literal["left", "exact", "right"] = "exact") -> int:
        if mode == "left":
            return bisect_left(self, value, start, stop)
        elif mode == "right":
            return bisect_right(self, value, start, stop)
        elif mode == "exact":
            i = bisect_left(self, value, start, stop)
            if not 0 <= i < len(self) or value is not self[i] != value:
                raise ValueError(f"{value!r} is not in the sorted sequence")
            else:
                return i
        else:
            raise ValueError(f"index expected left/exact/right for the mode, got {mode!r}")

    @property
    def interval(self: SortedSequence[T], /) -> SortedInterval[T]:
        return SortedInterval(self)


class SortedMutableSequence(MutableSequence[T], SortedSequence[T], ABC, Generic[T]):

    __slots__ = ()

    @abstractmethod
    def __delitem__(self: SortedMutableSequence[Any], index: Union[int, slice], /) -> None:
        raise NotImplementedError("__delitem__ is a required method for sorted mutable sequences")

    @overload
    def __getitem__(self: SortedMutableSequence[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: SortedMutableSequence[T], index: slice, /) -> MutableSequence[T]:
        ...

    @abstractmethod
    def __getitem__(self, index, /):
        raise NotImplementedError("__getitem__ is a required method for sorted mutable sequences")

    @abstractmethod
    def __iter__(self: SortedMutableSequence[T], /) -> SortedIterator[T]:
        raise NotImplementedError("__iter__ is a required method for sorted mutable sequences")

    @abstractmethod
    def __len__(self: SortedMutableSequence[Any], /) -> int:
        raise NotImplementedError("__len__ is a required method for sorted mutable sequences")

    @abstractmethod
    def __reversed__(self: SortedMutableSequence[T], /) -> Iterator[T]:
        raise NotImplementedError("__reversed__ is a required method for sorted mutable sequences")

    def __setitem__(self: SortedMutableSequence[T], index: Union[int, slice], value: Union[T, Iterable[T]], /) -> None:
        raise NotImplementedError("__setitem__ is not usable for sorted mutable sequences")

    @abstractmethod
    def append(self: SortedMutableSequence[T], value: T, /) -> None:
        raise NotImplementedError("append is a required method for sorted mutable sequences")

    def discard(self: SortedMutableSequence[Any], value: Any, /) -> None:
        i = bisect_left(self, value)
        if 0 <= i < len(self) and not (value is not self[i] != value):
            del self[i]

    @classmethod
    def from_iterable(cls: Type[SortedMutableSequence[T]], iterable: Iterable[T], /) -> SortedMutableSequence[T]:
        if isinstance(iterable, Iterable):
            return cls.from_sorted(sorted(iterable))  # type: ignore
        else:
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")

    @classmethod
    @abstractmethod
    def from_sorted(cls: Type[SortedMutableSequence[T]], iterable: Iterable[T], /) -> SortedMutableSequence[T]:
        raise NotImplementedError(f"from_sorted is a required method for sorted mutable sequences")

    def insert(self: SortedMutableSequence[T], index: int, value: T, /) -> None:
        raise NotImplementedError("insert is not usable for sorted mutable sequences")

    def remove(self: SortedMutableSequence[Any], value: Any, /) -> None:
        len_ = len(self)
        self.discard(value)
        if len(self) == len_:
            raise ValueError(f"value not in sequence, got {value!r}")

    def reverse(self: SortedMutableSequence[Any], /) -> None:
        raise NotImplementedError("reverse is not usable for sorted mutable sequences")


if sys.version_info < (3, 9):
    collections.abc.MutableSequence.register(SortedMutableSequence)
    collections.abc.Sequence.register(SortedSequence)
