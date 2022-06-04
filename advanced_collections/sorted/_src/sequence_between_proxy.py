from __future__ import annotations
import sys
from typing import Generic, TypeVar, Union

if sys.version_info < (3, 9):
    from typing import Tuple as tuple

import advanced_collections.sorted
from advanced_collections._src.comparable import SupportsRichHashableComparison

__all__ = ["SortedSequenceBetweenProxy"]

Self = TypeVar("Self", bound="SortedSequenceBetweenProxy")
T_co = TypeVar("T_co", bound=SupportsRichHashableComparison, covariant=True)


class SortedSequenceBetweenProxy(Generic[T_co]):
    _sequence: advanced_collections.sorted.SortedSequence[T_co]

    __slots__ = {
        "_sequence":
            "A sorted sequence instance.",
    }

    def __init__(self: Self, sequence: advanced_collections.sorted.SortedSequence[T_co], /) -> None:
        self._sequence = sequence

    def __getitem__(self: Self, index: Union[slice, tuple[slice, slice]], /) -> advanced_collections.sorted.SortedSequenceBetween[T_co]:
        if isinstance(index, slice):
            if index.step is not None:
                raise TypeError("expected sorted_sequence[start:stop, inclusive:exclusive], got a step argument")
            return advanced_collections.sorted.SortedSequenceBetween(self._sequence, index.start, index.stop)
        elif not isinstance(index, tuple):
            raise TypeError(f"expected sorted_sequence[start:stop, inclusive:exclusive], got sorted_sequence[{index!r}]")
        elif len(index) == 0:
            raise TypeError(f"expected sorted_sequence[start:stop, inclusive:exclusive], got sorted_sequence[{index!r}]")
        elif len(index) == 1:
            raise TypeError(f"expected sorted_sequence[start:stop, inclusive:exclusive], got sorted_sequence[{index!r}]")
        elif len(index) != 2:
            raise TypeError(f"expected sorted_sequence[start:stop, inclusive:exclusive], got sorted_sequence[{index!r}]")
        elif not isinstance(index[0], slice) or not isinstance(index[1], slice):
            raise TypeError(f"expected sorted_sequence[start:stop, inclusive:exclusive], got sorted_sequence[{index[0]!r}, {index[1]!r}]")
        elif not (index[0].step is None is index[1].step):
            raise TypeError("expected sorted_sequence[start:stop, inclusive:exclusive], got a step argument")
        elif index[1].start not in (None, "<", "<="):
            raise TypeError(
                f"expected sorted_sequence[..., :exclusive], sorted_sequence[..., '<':exclusive],"
                f" or sorted_sequence[..., '<=':exclusive], got sorted_sequence[..., {index[1].start!r}:{index[1].stop!r}]"
            )
        elif index[1].stop not in (None, "<", "<="):
            raise TypeError(
                f"expected sorted_sequence[..., inclusive:], sorted_sequence[..., inclusive:'<']",
                f" or sorted_sequence[..., inclusive:'<='], got sorted_sequence[..., {index[1].start!r}:{index[1].stop!r}]"
            )
        else:
            indices, bounds = index
            return advanced_collections.sorted.SortedSequenceBetween(self._sequence, indices.start, indices.stop, bounds.start != "<=", bounds.stop != "<")
