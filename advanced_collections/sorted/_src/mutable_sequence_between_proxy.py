from typing import Final, Generic, TypeVar, Union

import advanced_collections.sorted._src as src
from advanced_collections._src.comparable import SupportsRichHashableComparison
from .sequence_between import SortedSequenceBetween

T_co = TypeVar("T_co", bound=SupportsRichHashableComparison, covariant=True)

Self = TypeVar("Self", bound="SortedMutableSequenceBetweenProxy")


class SortedMutableSequenceBetweenProxy(SortedSequenceBetween[T_co], Generic[T_co]):
    _sequence: Final["src.mutable_sequence.SortedMutableSequence[T_co]"]

    __slots__ = ()

    def __init__(self: Self, sequence: "src.mutable_sequence.SortedMutableSequence[T_co]", /) -> None:
        self._sequence = sequence

    def __delitem__(self: Self, index: Union[slice, tuple[slice, slice]], /) -> None:
        if isinstance(index, slice):
            if index.step is not None:
                raise TypeError("expected sorted_sequence[start:stop, inclusive:exclusive], got a step argument")
            start = self._sequence.index(index.start, mode="left")
            stop = self._sequence.index(index.stop, start, mode="right")
            del self._sequence[start:stop]
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
            start = self._sequence.index(index.start, mode=("left" if bounds.start != "<=" else "right"))
            stop = self._sequence.index(index.stop, start, mode=("left" if bounds.stop != "<" else "right"))
            del self._sequence[start:stop]
