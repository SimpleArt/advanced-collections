from collections.abc import Iterable, Iterator
from itertools import islice
from typing import Any, Generic, Literal, Optional, Type, TypeVar, overload

from advanced_collections._src.comparable import SupportsRichHashableComparison

import advanced_collections.sorted._src as src
from .sequence import SortedSequence
from .sequence_islice import SortedSequenceIslice

T = TypeVar("T", bound=SupportsRichHashableComparison)
T_co = TypeVar("T_co", bound=SupportsRichHashableComparison)

Self = TypeVar("Self", bound="SortedSequenceBetween")


class SortedSequenceBetween(SortedSequence[T_co], Generic[T_co]):
    _sequence: SortedSequence[T_co]
    _start: Optional[T_co]
    _stop: Optional[T_co]
    _start_mode: Literal["left", "right"]
    _stop_mode: Literal["left", "right"]

    __slots__ = {
        "_sequence":
            "A sorted sequence instance.",
        "_start":
            "The starting value.",
        "_stop":
            "The stopping value.",
        "_start_mode":
            "The indexing mode for the start.",
        "_stop_mode":
            "The indexing mode for the stop.",
    }

    def __init__(
        self: Self,
        sequence: SortedSequence[T_co],
        start: Optional[T_co],
        stop: Optional[T_co],
        include_start: bool = True,
        exclude_stop: bool = True,
        /,
    ) -> None:
        # Type-check if it's the right type of values.
        if start is not None:
            sequence.index(start, mode=("left" if include_start else "right"))
        if stop is not None:
            sequence.index(stop, mode=("left" if exclude_stop else "right"))
        self._sequence = sequence
        self._start = start
        self._stop = stop
        self._start_mode = "left" if include_start else "right"
        self._stop_mode = "left" if exclude_stop else "right"

    def __between_iter__(self: Self, start: Optional[T_co], stop: Optional[T_co], inclusive: bool, exclusive: bool, /) -> Iterator[T_co]:
        if start is None or inclusive == (self._start_mode == "left") and None is not self._start > start:
            start = self._start
            inclusive = self._start_mode == "left"
        if stop is None or exclusive == (self._stop_mode == "left") and None is not self._stop > stop:
            stop = self._stop
            exclusive = self._stop_mode == "left"
        return self._sequence.__between_iter__(start, stop, inclusive, exclusive)

    def __between_reversed__(self: Self, start: Optional[T_co], stop: Optional[T_co], inclusive: bool, exclusive: bool, /) -> Iterator[T_co]:
        if start is None or inclusive == (self._start_mode == "left") and None is not self._start > start:
            start = self._start
            inclusive = self._start_mode == "left"
        if stop is None or exclusive == (self._stop_mode == "left") and None is not self._stop > stop:
            stop = self._stop
            exclusive = self._stop_mode == "left"
        return self._sequence.__between_reversed__(start, stop, inclusive, exclusive)

    @classmethod
    def __from_iterable__(cls: Type[Self], iterable: Iterable[T], /) -> "src.list.SortedList[T]":
        return src.list.SortedList(iterable)

    @classmethod
    def __from_sorted__(cls: Type[Self], iterable: Iterable[T], /) -> "src.list.SortedList[T]":
        return src.list.SortedList.__from_sorted__(iterable)

    @overload
    def __getitem__(self: Self, index: int, /) -> T_co: ...

    @overload
    def __getitem__(self: Self, index: slice, /) -> SortedSequenceIslice[T_co]: ...

    def __getitem__(self, index, /):
        """Returns an element in the slice by index."""
        if not isinstance(index, SupportsIndex):
            raise TypeError(f"could not interpret index as an integer, got {index!r}")
        if self._start is None:
            start = 0
        else:
            start = self._sequence.index(self._start, mode=self._start_mode)
        if self._stop is None:
            stop = len(self._sequence)
        else:
            stop = self._sequence.index(self._stop, mode=self._stop_mode)
        range_ = range(start, stop)[index]
        start_ = range_.start
        stop_ = range_.stop
        step_ = range_.step
        if step_ > 0:
            if start_ == 0:
                start_ = None
            if stop_ >= len(self._sequence):
                stop_ = None
            elif stop_ > stop:
                stop_ = stop
        else:
            if start_ + 1 == len(self._sequence):
                start_ = None
            if stop_ < 0:
                stop_ = None
            elif stop_ + 1 < start:
                stop_ = start - 1
        return self._sequence[start_:stop_:step_]

    def __islice__(self: Self, start: Optional[int], stop: Optional[int], step: Optional[int], /) -> Iterator[T_co]:
        if self._start is None:
            _start = 0
        else:
            _start = self._sequence.index(self._start, mode=self._start_mode)
        if self._stop is None:
            _stop = len(self._sequence)
        else:
            _stop = self._sequence.index(self._stop, mode=self._stop_mode)
        range_ = range(_start, _stop)[start:stop:step]
        start_ = range_.start
        stop_ = range_.stop
        step_ = range_.step
        if step_ > 0:
            if start_ == 0:
                start_ = None
            if stop_ >= len(self._sequence):
                stop_ = None
            elif stop_ > stop:
                stop_ = stop
        else:
            if start_ + 1 == len(self._sequence):
                start_ = None
            if stop_ < 0:
                stop_ = None
            elif stop_ + 1 < start:
                stop_ = start - 1
        return self._sequence.__islice__(start_, stop_, step_)

    def __iter__(self: Self, /) -> Iterator[T_co]:
        """Iteratates through the slice in order."""
        return self._sequence.__between_iter__(self._start, self._stop, self._start_mode == "left", self._stop_mode == "right")

    def __len__(self: Self, /) -> int:
        """Returns the number of elements in the slice."""
        if self._start is not None is not self._stop < self._start:
            return 0
        if self._start is None:
            start = 0
        else:
            start = self._sequence.index(self._start, mode=self._start_mode)
        if self._stop is None:
            stop = len(self._sequence)
        else:
            stop = self._sequence.index(self._stop, mode=self._stop_mode)
        return max(stop - start, 0)

    def __repr__(self: Self, /) -> str:
        start = "" if self._start is None else repr(self._start)
        stop = "" if self._stop is None else repr(self._stop)
        start_mode = "" if self._start_mode == "left" else "<"
        stop_mode = "" if self._stop_mode == "left" else "<="
        mode = "" if start_mode == "" == stop_mode else f", {start_mode}:{stop_mode}"
        return f"{self._sequence!r}.between[{start}:{stop}{mode}]"

    def __reversed__(self: Self, /) -> Iterator[T_co]:
        """Iteratates through the slice in reversed order."""
        return self._sequence.__between_reversed__(self._start, self._stop, self._start_mode == "left", self._stop_mode == "right")

    def index(self: Self, value: Any, /, start: int = 0, stop: Optional[int] = None, *, mode: Literal["left", "exact", "right"] = "exact") -> int:
        if isinstance(start, int):
            pass
        elif isinstance(start, SupportsIndex):
            start = operator.index(start)
        else:
            raise TypeError(f"could not interpret the start as an integer, got {start!r}")
        if stop is None:
            stop = len(self)
        elif isinstance(stop, int):
            pass
        elif isinstance(stop, SupportsIndex):
            stop = operator.index(stop)
        else:
            raise TypeError(f"could not interpret the stop as an integer, got {stop!r}")
        if not isinstance(mode, str):
            raise TypeError(f"expected 'left', 'exact', or 'right' for the mode, got {mode!r}")
        elif mode not in ("left", "exact", "right"):
            raise ValueError(f"expected 'left', 'exact', or 'right' for the mode, got {mode!r}")
        if self._start is None:
            pass
        elif self._start_mode == "left" and value < self._start:
            if mode == "exact":
                raise IndexError(f"must be greater than or equal to {self._start!r}, got {value!r}")
            else:
                return 0
        elif self._start_mode == "right" and value <= self._start:
            if mode == "exact":
                raise IndexError(f"must be greater than {self._start!r}, got {value!r}")
            else:
                return 0
        if self._stop is None:
            pass
        elif self._stop_mode == "left" and self._stop <= value:
            if mode == "exact":
                raise IndexError(f"must be less than {self._stop!r}, got {value!r}")
            else:
                return len(self)
        elif self._stop_mode == "right" and self._stop < value:
            if mode == "exact":
                raise IndexError(f"must be less than or equal to to {self._stop!r}, got {value!r}")
            else:
                return len(self)
        if self._start is not None:
            offset = self._sequence.index(self._start, mode=self._start_mode)
            start += offset
            stop += offset
        return self._sequence.index(value, start, stop, mode=mode)
