import operator
from abc import ABC, abstractmethod
from collections.abc import Iterable, MutableSequence
from typing import Any, Generic, Type, TypeVar, overload

from advanced_collections._src.comparable import SupportsRichHashableComparison
from .sequence import SortedSequence
from .mutable_sequence_between_proxy import SortedMutableSequenceBetweenProxy
from .mutable_sequence_islice_proxy import SortedMutableSequenceIsliceProxy

T = TypeVar("T", bound=SupportsRichHashableComparison)

Self = TypeVar("Self", bound="SortedMutableSequence")


class SortedMutableSequence(SortedSequence[T], MutableSequence[T], ABC, Generic[T]):

    __slots__ = ()

    def __add__(self: Self, other: SortedSequence[T], /) -> "SortedMutableSequence[T]":
        # Find common parent class.
        for cls in type(self).mro():
            if isinstance(other, cls) and issubclass(cls, SortedMutableSequence):
                try:
                    return cls.__from_sorted__(merge(self, other))
                except NotImplementedError:
                    pass
        return NotImplemented

    __radd__ = __add__

    @classmethod
    def __from_iterable__(cls: Type[Self], iterable: Iterable[T], /) -> Self:
        if isinstance(iterable, Iterable):
            return cls.from_sorted(sorted(iterable))
        else:
            raise TypeError(f"{cls.__name__}.__from_iterable__ expected an iterable, got {iterable!r}")

    @classmethod
    @abstractmethod
    def __from_sorted__(cls: Type[Self], iterable: Iterable[T], /) -> Self:
        raise NotImplementedError(f"__from_sorted__ is a required method for sorted mutable sequences")

    @overload
    def __getitem__(self: Self, index: int, /) -> T: ...

    @overload
    def __getitem__(self: Self, index: slice, /) -> Self: ...

    @abstractmethod
    def __getitem__(self, index, /):
        raise NotImplementedError(f"__getitem__ is a required method for sorted mutable sequences")

    def __iadd__(self: Self, other: Iterable[T], /) -> Self:
        if not isinstance(other, Iterable):
            return NotImplemented
        self.extend(other)
        return self

    def __imul__(self: Self, other: int, /) -> Self:
        try:
            range_ = range(other)
        except TypeError:
            return NotImplemented
        if len(range_) == 0:
            self.clear()
        elif len(range_) > 1:
            range_ = range_[1:]
            self.extend(
                x
                for i in reversed(range(len(self)))
                for x in [self[i]]
                for _ in range_
            )
        return self

    def __mul__(self: Self, other: int, /) -> "SortedMutableSequence[T]":
        try:
            range_ = range(other)
        except TypeError:
            return NotImplemented
        if len(range_) == 0:
            return type(self).__from_sorted__(self[i] for i in range_)
        elif len(range_) == 1:
            return self.copy()
        else:
            return type(self).__from_sorted__(x for x in self for _ in range_)

    __rmul__ = __mul__

    @overload
    def __setitem__(self: Self, index: int, element: T, /) -> None: ...

    @overload
    def __setitem__(self: Self, index: slice, element: Iterable[T], /) -> None: ...

    def __setitem__(self, index, element, /):
        raise NotImplementedError(f"sorted mutable sequences do not support indexed assignments")

    def add(self: Self, element: T, /) -> None:
        if element not in self:
            self.append(element)

    @abstractmethod
    def append(self: Self, element: T, /) -> None:
        raise NotImplementedError(f"append is a required method for sorted mutable sequences")

    @abstractmethod
    def discard(self: Self, element: T, /) -> None:
        raise NotImplementedError(f"discard is a required method for sorted mutable sequences")

    def insert(self: Self, index: int, element: T, /) -> None:
        raise NotImplementedError(
            f"sorted mutable sequences do not support indexed insertion, use"
            f" {type(self).__name__}.append or {type(self).__name__}.add instead"
        )

    def remove(self: Self, element: T, /) -> None:
        len_ = len(self)
        self.discard(element)
        if len(self) == len_:
            raise KeyError(element)

    @property
    def between(self: Self, /) -> SortedMutableSequenceBetweenProxy[T]:
        return SortedMutableSequenceBetweenProxy(self)

    @property
    def between(self: Self, /) -> SortedMutableSequenceIsliceProxy[T]:
        return SortedMutableSequenceIsliceProxy(self)
