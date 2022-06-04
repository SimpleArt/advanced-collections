import sys
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

if sys.version_info < (3, 9):
    from typing import MutableSequence
else:
    from collections.abc import MutableSequence

from .mutable_sequence_islice_proxy import MutableSequenceIsliceProxy
from .viewable_sequence import ViewableSequence

__all__ = ["ViewableMutableSequence"]

Self = TypeVar("Self", bound="ViewableMutableSequence")
T = TypeVar("T")


class ViewableMutableSequence(ViewableSequence[T], MutableSequence[T], ABC, Generic[T]):

    __slots__ = ()

    @overload
    def __getitem__(self: Self, index: int, /) -> T: ...

    @overload
    def __getitem__(self: Self, index: slice, /) -> ViewableMutableSequence[T]: ...

    @abstractmethod
    def __getitem__(self, index, /):
        raise NotImplementedError(f"__getitem__ is a required method for viewable mutable sequences")

    @property
    def islice(self: Self, /) -> MutableSequenceIsliceProxy[T]:
        return MutableSequenceIsliceProxy(self)
