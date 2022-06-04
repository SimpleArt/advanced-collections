from __future__ import annotations
import sys
from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar, overload

if sys.version_info < (3, 9):
    from typing import Iterator, Sequence
else:
    from collections.abc import Iterator, Sequence

from .sequence_islice_proxy import SequenceIsliceProxy

__all__ = ["ViewableSequence"]

Self = TypeVar("Self", bound="ViewableSequence")
T_co = TypeVar("T_co", covariant=True)


class ViewableSequence(Sequence[T_co], ABC, Generic[T_co]):

    __slots__ = ()

    @overload
    def __getitem__(self: Self, index: int, /) -> T_co: ...

    @overload
    def __getitem__(self: Self, index: slice, /) -> ViewableSequence[T_co]: ...

    @abstractmethod
    def __getitem__(self, index, /):
        raise NotImplementedError(f"__getitem__ is a required method for viewable sequences")

    def __islice__(self: Self, start: Optional[int], stop: Optional[int], step: Optional[int], /) -> Iterator[T_co]:
        len_ = len(self)
        range_ = range(len_)[start:stop:step]
        if len(range_) == 0:
            return (self[i] for i in range_)
        elif range_.step == 1 and len(range_) == len_:
            return iter(self)
        elif range_.step == 1 and range_.start == 0:
            return islice(self, range_.stop)
        elif range_.step == 1 and range_.start < range_.stop // 2:
            return islice(self, range_.start, range_.stop)
        elif range_.step == -1 and len(range_) == len_:
            return reversed(self)
        elif range_.step == -1 and range_.start + 1 == len_:
            return islice(reversed(self), len(range_))
        elif range_.step == -1 and (len_ - range_.start) < (len_ - range_.stop) // 2:
            return islice(reversed(self), len_ - range_.start - 1, len_ - range_.stop - 1)
        elif len(range_) < len_ // 8:
            return (self[i] for i in range_)
        elif range_.step > 0:
            return islice(self, range_.start, range_.stop, range_.step)
        else:
            return islice(reversed(self), len_ - range_.start - 1, len_ - range_.stop - 1, -range_.step)

    @property
    def islice(self: Self, /) -> SequenceIsliceProxy[T_co]:
        return SequenceIsliceProxy(self)
