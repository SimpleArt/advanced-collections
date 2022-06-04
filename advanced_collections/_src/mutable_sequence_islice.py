from typing import Generic, TypeVar, Union

from .viewable_mutable_sequence import ViewableMutableSequence
from .sequence_islice import SequenceIslice

__all__ = ["MutableSequenceIslice"]

Self = TypeVar("Self", bound="MutableSequenceIslice")
T = TypeVar("T")


class MutableSequenceIslice(SequenceIslice[T], Generic[T]):
    _sequence: ViewableMutableSequence[T]

    __slots__ = ()

    def __init__(
        self: Self,
        sequence: ViewableMutableSequence[T],
        start: Optional[int],
        stop: Optional[int],
        step: Optional[int],
        /,
    ) -> None:
        assert isinstance(sequence, ViewableMutableSequence)
        self._sequence = sequence
        self._start = start
        self._stop = stop
        self._step = step

    def __delitem__(self: Self, index: Union[int, slice], /) -> None:
        if isinstance(index, slice):
            range_ = range(len(self._sequence))[index]
            start = None if index.start is None else range_.start
            stop = None if index.stop is None else range_.stop
            step = None if index.step is None else range_.step
            del self._sequence[start:stop:step]
        else:
            index = range(len(self._sequence))[self._start:self._stop:self._step][index]
            del self._sequence[index]
