from typing import Final, TypeVar

import advanced_collections.sorted._src as src
from advanced_collections._src.comparable import SupportsRichHashableComparison
from advanced_collections._src.sequence_islice_proxy import SequenceIsliceProxy

T_co = TypeVar("T_co", bound=SupportsRichHashableComparison, covariant=True)

Self = TypeVar("Self", bound="SortedSequenceIsliceProxy")


class SortedSequenceIsliceProxy(SequenceIsliceProxy[T_co], Generic[T_co]):
    _sequence: Final["src.sequence.SortedSequence[T_co]"]

    __slots__ = ()

    def __init__(self: Self, sequence: "src.sequence.SortedSequence[T_co]", /) -> None:
        assert isinstance(sequence, src.sequence.SortedSequence)
        self._sequence = sequence

    def __getitem__(self: Self, index: slice, /) -> "src.sequence_islice.SortedSequenceIslice[T_co]":
        if not isinstance(index, slice):
            raise TypeError(f"expected sequence.islice[start:stop:step], got sequence.islice[{index!r}]")
        # Cast integer-like indices to integers.
        range_ = range(len(self._sequence))[index]
        # Collect None or integers.
        start = None if index.start is None else range_.start
        stop = None if index.stop is None else range_.stop
        step = None if index.step is None else range_.step
        
