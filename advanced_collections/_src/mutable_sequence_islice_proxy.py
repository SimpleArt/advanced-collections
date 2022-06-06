from __future__ import annotations
from typing import Generic, TypeVar, Union, overload

import advanced_collections
from .sequence_islice_proxy import SequenceIsliceProxy

__all__ = ["MutableSequenceIsliceProxy"]

Self = TypeVar("Self", bound="MutableSequenceIsliceProxy")
T = TypeVar("T")


class MutableSequenceIsliceProxy(SequenceIsliceProxy[T], Generic[T]):
    _sequence: advanced_collections._src.viewable_mutable_sequence.ViewableMutableSequence[T]

    __slots__ = ()

    def __init__(self: Self, sequence: advanced_collections._src.viewable_mutable_sequence.ViewableMutableSequence[T], /) -> None:
        assert isinstance(sequence, advanced_collections._src.viewable_mutable_sequence.ViewableMutableSequence)
        self._sequence = sequence

    def __getitem__(self: Self, index: slice, /) -> advanced_collections._src.mutable_sequence_islice.MutableSequenceIslice[T]:
        if not isinstance(index, slice):
            raise TypeError(f"expected sequence.islice[start:stop:step], got sequence.islice[{index!r}]")
        # Cast integer-like indices to integers.
        range_ = range(len(self._sequence))[index]
        # Collect None or integers.
        start = None if index.start is None else range_.start
        stop = None if index.stop is None else range_.stop
        step = None if index.step is None else range_.step
        return advanced_collections._src.mutable_sequence_islice.MutableSequenceIslice(self._sequence, start, stop, step)
