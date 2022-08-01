import operator
from collections.abc import Iterable
from typing import Generic, Optional, Type, TypeVar, overload

import advanced_collections.sorted._src as src
from advanced_collections._src.comparable import SupportsRichHashableComparison
from advanced_collections._src.sequence_islice import SequenceIslice
from .sequence import SortedSequence

T = TypeVar("T", bound=SupportsRichHashableComparison)
T_co = TypeVar("T_co", bound=SupportsRichHashableComparison)

Self = TypeVar("Self", bound="SortedSequenceIslice")


class SortedSequenceIslice(SequenceIslice[T_co], SortedSequence[T_co], Generic[T_co]):
    _sequence: SortedSequence[T_co]
    _start: Optional[int]
    _stop: Optional[int]
    _step: Optional[int]

    __slots__ = {
        "_sequence":
            "A sorted sequence instance.",
        "_start":
            "The starting index.",
        "_stop":
            "The stopping index.",
        "_step":
            "The step size.",
    }

    def __init__(self: Self, sequence: SortedSequence[T_co], start: Optional[int], stop: Optional[int], step: Optional[int], /) -> None:
        assert step is None or step > 0
        self._sequence = sequence
        self._start = start
        self._stop = stop
        self._step = step

    @classmethod
    def __from_iterable__(cls: Type[Self], iterable: Iterable[T], /) -> "src.list.SortedList[T]":
        return src.list.SortedList(iterable)

    @classmethod
    def __from_sorted__(cls: Type[Self], iterable: Iterable[T], /) -> "src.list.SortedList[T]":
        return src.list.SortedList.__from_sorted__(iterable)

    @overload
    def __getitem__(self: Self, index: int, /) -> T_co: ...

    @overload
    def __getitem__(self: Self, index: slice, /) -> SequenceIslice[T_co]: ...

    def __getitem__(self, index):
        if isinstance(index, slice):
            range_ = range(len(self._sequence))[self._start:self._stop:self._step][index]
            start = None if index.start is None else range_.start
            stop = None if index.stop is None else range_.stop
            step = None if index.step is None else range_.step
            if range_.step < 0:
                return SequenceIslice(self, start, stop, step)
            else:
                return type(self)(self, start, stop, step)
        else:
            index = range(len(self._sequence))[self._start:self._stop:self._step][index]
            return self._sequence[index]
