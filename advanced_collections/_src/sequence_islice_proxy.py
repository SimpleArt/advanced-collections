from __future__ import annotations
import sys
from typing import Generic, TypeVar

if sys.version_info < (3, 9):
    from typing import Iterator
else:
    from collections.abc import Iterator

import advanced_collections.abc

__all__ = ["SequenceIsliceProxy"]

Self = TypeVar("Self", bound="SequenceIsliceProxy")
T_co = TypeVar("T_co", covariant=True)


class SequenceIsliceProxy(Generic[T_co]):
    _sequence: advanced_collections.abc.ViewableSequence[T_co]

    __slots__ = {
        "_sequence":
            "The viewable sequence.",
    }

    def __init__(self: Self, sequence: advanced_collections.abc.ViewableSequence[T_co], /) -> None:
        assert isinstance(sequence, advanced_collections.abc.ViewableSequence)
        self._sequence = sequence

    def __getitem__(self: Self, index: slice, /) -> advanced_collections.abc.SequenceIslice[T_co]:
        if not isinstance(index, slice):
            raise TypeError(f"expected sequence.islice[start:stop:step], got sequence.islice[{index!r}]")
        # Cast integer-like indices to integers.
        range_ = range(len(self._sequence))[index]
        # Collect None or integers.
        start = None if index.start is None else range_.start
        stop = None if index.stop is None else range_.stop
        step = None if index.step is None else range_.step
        return advanced_collections.abc.SequenceIslice(self._sequence, start, stop, step)
