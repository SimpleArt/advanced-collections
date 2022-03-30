from __future__ import annotations
import collections.abc
import sys
from abc import ABC, abstractmethod
from bisect import bisect_left, bisect_right
from itertools import islice
from typing import Any, Generic, Literal, Optional, Type, TypeVar, Union, overload

if sys.version_info < (3, 9):
    from typing import Callable, Iterable, Iterator, MutableSequence, Sequence
else:
    from collections.abc import Callable, Iterable, Iterator, MutableSequence, Sequence

from ._abc_key_constructor import SortedKeyConstructor
from ._abc_key_iterable import SortedKeyIterable, SortedKeyIterator

__all__ = ["SortedKeySequence", "SortedKeyMutableSequence"]

T = TypeVar("T")

def iter_until(iterable: SortedKeyIterable[T], stop_at: Any, key: Callable[[T], Any], /) -> Iterator[T]:
    for x in iterable:
        if key(x) < stop_at:  # type: ignore
            yield x
        else:
            break


class SortedKeyInterval(Generic[T]):
    _sequence: SortedKeySequence[T]

    def __init__(self: SortedKeyInterval[T], sequence: SortedKeySequence[T], /) -> None:
        if not isinstance(sequence, SortedKeySequence):
            raise TypeError(f"{type(self).__name__} expected a sorted key sequence, got {sequence!r}")
        self._sequence = sequence

    def __getitem__(self: SortedKeyInterval[T], interval: slice, /) -> SortedKeyIterator[T]:
        if not isinstance(interval, slice):
            raise TypeError("sorted key intervals only support slicing")
        elif interval.step is not None:
            raise ValueError("step sizes are not supported by sorted key intervals")
        elif interval.start is interval.stop is None:
            return iter(self._sequence)
        elif interval.start is None:
            from more_collections.sorted import SortedKeyUserIterator
            return SortedKeyUserIterator(iter_until(self._sequence, self._sequence.key(interval.stop), self._sequence.key))
        elif interval.stop is None:
            start = self._sequence.index(interval.start, mode="left")
            if len(self._sequence) * 7 // 8 < start:
                iterator = iter(self._sequence)
                for _ in range(start):
                    next(iterator)
                return iterator
            else:
                from more_collections.sorted import SortedKeyUserIterator
                return SortedKeyUserIterator(self._sequence[i] for i in range(start, len(self._sequence)))
        else:
            from more_collections.sorted import SortedKeyUserIterator
            start = self._sequence.index(interval.start, mode="left")
            stop = self._sequence.index(interval.stop, mode="left")
            if len(self._sequence) // 8 < stop - start:
                iterator = iter(self._sequence)
                for _ in range(start):
                    next(iterator)
                return SortedKeyUserIterator(islice(iterator, stop - start))
            else:
                return SortedKeyUserIterator(self._sequence[i] for i in range(start, stop))


class SortedKeySequence(Sequence[T], SortedKeyConstructor[T], ABC, Generic[T]):

    __slots__ = ()

    def __contains__(self: SortedKeySequence[Any], value: Any, /) -> bool:
        i = bisect_left(self, value, key=self.key)  # type: ignore
        return 0 <= i < len(self) and not (value is not self[i] != value)

    @overload
    def __getitem__(self: SortedKeySequence[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: SortedKeySequence[T], index: slice, /) -> Sequence[T]:
        ...

    @abstractmethod
    def __getitem__(self, index, /):
        raise NotImplementedError("__getitem__ is a required method for sorted key sequences")

    @abstractmethod
    def __iter__(self: SortedKeySequence[T], /) -> SortedKeyIterator[T]:
        raise NotImplementedError("__iter__ is a required method for sorted key sequences")

    @abstractmethod
    def __len__(self: SortedKeySequence[Any], /) -> int:
        raise NotImplementedError("__len__ is a required method for sorted key sequences")

    @abstractmethod
    def __reversed__(self: SortedKeySequence[T], /) -> Iterator[T]:
        raise NotImplementedError("__reversed__ is a required method for sorted key sequences")

    def count(self: SortedKeySequence[Any], value: Any, /) -> int:
        hi = bisect_right(self, value, key=self.key)  # type: ignore
        lo = bisect_left(self, value, 0, hi, key=self.key)  # type: ignore
        return hi - lo

    @classmethod
    def from_iterable(cls: Type[SortedKeySequence[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeySequence[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")
        elif not callable(key):
            raise TypeError(f"from_iterable expects a callable key, got {key!r}")
        else:
            return cls.from_sorted(sorted(iterable, key=key), key)

    @classmethod
    @abstractmethod
    def from_sorted(cls: Type[SortedKeySequence[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeySequence[T]:
        raise NotImplementedError(f"from_sorted is a required method for sorted key sequences")

    def index(self: SortedKeySequence[Any], value: Any, /, start: int = 0, stop: Optional[int] = None, *, mode: Literal["left", "exact", "right"] = "exact") -> int:
        if mode == "left":
            return bisect_left(self, value, start, stop, key=self.key)  # type: ignore
        elif mode == "right":
            return bisect_right(self, value, start, stop, key=self.key)  # type: ignore
        elif mode == "exact":
            i = bisect_left(self, value, start, stop, key=self.key)  # type: ignore
            if not 0 <= i < len(self) or value is not self[i] != value:
                raise ValueError(f"{value!r} is not in the sorted sequence")
            else:
                return i
        else:
            raise ValueError(f"index expected left/exact/right for the mode, got {mode!r}")

    @property
    def interval(self: SortedKeySequence[T], /) -> SortedKeyInterval[T]:
        return SortedKeyInterval(self)

    @property
    @abstractmethod
    def key(self: SortedKeySequence[T], /) -> Callable[[T], Any]:
        raise NotImplementedError("key is a required property for sorted key sequences")


class SortedKeyMutableSequence(MutableSequence[T], SortedKeySequence[T], ABC, Generic[T]):

    __slots__ = ()

    @abstractmethod
    def __delitem__(self: SortedKeyMutableSequence[Any], index: Union[int, slice], /) -> None:
        raise NotImplementedError("__delitem__ is a required method for sorted key mutable sequences")

    @overload
    def __getitem__(self: SortedKeyMutableSequence[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: SortedKeyMutableSequence[T], index: slice, /) -> MutableSequence[T]:
        ...

    @abstractmethod
    def __getitem__(self, index, /):
        raise NotImplementedError("__getitem__ is a required method for sorted key mutable sequences")

    @abstractmethod
    def __iter__(self: SortedKeyMutableSequence[T], /) -> SortedKeyIterator[T]:
        raise NotImplementedError("__iter__ is a required method for sorted key mutable sequences")

    @abstractmethod
    def __len__(self: SortedKeyMutableSequence[Any], /) -> int:
        raise NotImplementedError("__len__ is a required method for sorted key mutable sequences")

    @abstractmethod
    def __reversed__(self: SortedKeyMutableSequence[T], /) -> Iterator[T]:
        raise NotImplementedError("__reversed__ is a required method for sorted key mutable sequences")

    def __setitem__(self: SortedKeyMutableSequence[T], index: Union[int, slice], value: Union[T, Iterable[T]], /) -> None:
        raise NotImplementedError("__setitem__ is not usable for sorted key mutable sequences")

    @abstractmethod
    def append(self: SortedKeyMutableSequence[T], value: T, /) -> None:
        raise NotImplementedError("append is a required method for sorted key mutable sequences")

    def discard(self: SortedKeyMutableSequence[Any], value: Any, /) -> None:
        i = bisect_left(self, value, key=self.key)  # type: ignore
        if 0 <= i < len(self) and not (value is not self[i] != value):
            del self[i]

    @classmethod
    def from_iterable(cls: Type[SortedKeyMutableSequence[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeyMutableSequence[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")
        elif not callable(key):
            raise TypeError(f"from_iterable expects a callable key, got {key!r}")
        else:
            return cls.from_sorted(sorted(iterable, key=key), key)

    @classmethod
    @abstractmethod
    def from_sorted(cls: Type[SortedKeyMutableSequence[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeyMutableSequence[T]:
        raise NotImplementedError("from_sorted is a required method for sorted key mutable sequences")

    def insert(self: SortedKeyMutableSequence[T], index: int, value: T, /) -> None:
        raise NotImplementedError("insert is not usable for sorted key mutable sequences, use append instead")

    def reverse(self: SortedKeyMutableSequence[Any], /) -> None:
        raise NotImplementedError("reverse is not usable for sorted key mutable sequences")

    def remove(self: SortedKeyMutableSequence[Any], value: Any, /) -> None:
        len_ = len(self)
        self.discard(value)
        if len(self) == len_:
            raise ValueError(f"value not in sequence, got {value!r}")

    @property
    @abstractmethod
    def key(self: SortedKeyMutableSequence[T], /) -> Callable[[T], Any]:
        raise NotImplementedError("key is a required property for sorted key sequences")


if sys.version_info < (3, 9):
    collections.abc.MutableSequence.register(SortedKeyMutableSequence)
    collections.abc.Sequence.register(SortedKeySequence)
