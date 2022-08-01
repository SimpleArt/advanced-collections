import copy
import operator
from abc import ABC, abstractmethod
from bisect import bisect_left, bisect_right
from collections.abc import Iterable, Iterator, Sequence
from heapq import merge
from inspect import isabstract
from itertools import islice
from typing import Any, Generic, Literal, Optional, SupportsIndex, Type, TypeVar, overload

from advanced_collections._src.comparable import SupportsRichHashableComparison
from advanced_collections._src.viewable_sequence import ViewableSequence
from .collection import SortedCollection
from .sequence_between_proxy import SortedSequenceBetweenProxy

T_co = TypeVar("T_co", bound=SupportsRichHashableComparison, covariant=True)

Self = TypeVar("Self", bound="SortedSequence")

reprs_seen: set[int] = set()


class SortedSequence(ViewableSequence[T_co], ABC, Generic[T_co]):

    __slots__ = ()

    def __add__(self: Self, other: "SortedSequence[T_co]", /) -> "SortedSequence[T_co]":
        # Find common non-abstract parent class.
        for cls in type(self).mro():
            if isinstance(other, cls) and issubclass(cls, SortedSequence) and not isabstract(cls):
                return cls.__from_sorted__(merge(self, other))
        return NotImplemented

    def __radd__(self: Self, other: Sequence[T_co], /) -> "SortedSequence[T_co]":
        return NotImplemented

    def __between_iter__(self: Self, start: Optional[T_co], stop: Optional[T_co], inclusive: bool, exclusive: bool, /) -> Iterator[T_co]:
        if start is None:
            i = 0
        else:
            i = self.index(start, mode=("left" if inclusive else "right"))
        if stop is None:
            j = len(self)
        else:
            j = self.index(stop, mode=("left" if exclusive else "right"))
        return iter(self.islice[i:j])

    def __between_reversed__(self: Self, start: Optional[T_co], stop: Optional[T_co], inclusive: bool, exclusive: bool, /) -> Iterator[T_co]:
        if start is None:
            i = 0
        else:
            i = self.index(start, mode=("left" if inclusive else "right"))
        if stop is None:
            j = len(self)
        else:
            j = self.index(stop, mode=("left" if exclusive else "right"))
        return reversed(self.islice[i:j])

    def __contains__(self: Self, element: T_co, /) -> bool:
        i = bisect_left(self, value)
        return 0 <= i < len(self) and not (value is not self[i] != value)

    def __copy__(self: Self, /) -> Self:
        return type(self).__from_sorted__(self)

    def __deepcopy__(self: Self, /) -> Self:
        return type(self).__from_sorted__(map(copy.deepcopy, self))

    @classmethod
    def __from_iterable__(cls: Type[Self], iterable: Iterable[T_co], /) -> "SortedSequence[T_co]":
        if isinstance(iterable, Iterable):
            return cls.from_sorted(sorted(iterable))
        else:
            raise TypeError(f"{cls.__name__}.__from_iterable__ expected an iterable, got {iterable!r}")

    @classmethod
    @abstractmethod
    def __from_sorted__(cls: Type[Self], iterable: Iterable[T_co], /) -> "SortedSequence[T_co]":
        raise NotImplementedError(f"__from_sorted__ is a required method for sorted sequences")

    @overload
    def __getitem__(self: Self, index: int, /) -> T_co: ...

    @overload
    def __getitem__(self: Self, index: slice, /) -> "SortedSequence[T_co]": ...

    @abstractmethod
    def __getitem__(self, index, /):
        raise NotImplementedError(f"__getitem__ is a required method for sorted sequences")

    def __mul__(self: Self, other: int, /) -> "SortedSequence[T_co]":
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

    def __repr__(self: Self, /) -> str:
        if id(self) in reprs_seen:
            return "..."
        elif len(self) == 0:
            return f"{type(self).__name__}.__from_iterable__([])"
        reprs_seen.add(id(self))
        try:
            data = ", ".join([repr(x) for x in self])
            return f"{type(self).__name__}.__from_iterable__([{data}])"
        finally:
            reprs_seen.remove(id(self))

    def copy(self: Self, /) -> Self:
        return copy.copy(self)

    def count(self: Self, value: Any, /) -> int:
        lo = self.index(value, mode="left")
        hi = self.index(value, start=lo, mode="right")
        return hi - lo

    def index(self: Self, value: Any, /, start: int = 0, stop: Optional[int] = None, *, mode: Literal["left", "exact", "right"] = "exact") -> int:
        if isinstance(start, int):
            pass
        elif isinstance(start, SupportsIndex):
            start = operator.index(start)
        else:
            raise TypeError(f"could not interpret the start as an integer, got {start!r}")
        if stop is None:
            stop = len(self)
        elif isinstance(stop, int):
            pass
        elif isinstance(stop, SupportsIndex):
            stop = operator.index(stop)
        else:
            raise TypeError(f"could not interpret the stop as an integer, got {stop!r}")
        if not isinstance(mode, str):
            raise TypeError(f"expected 'left', 'exact', or 'right' for the mode, got {mode!r}")
        elif mode == "left":
            return bisect_left(self, value, start, stop)
        elif mode == "right":
            return bisect_right(self, value, start, stop)
        elif mode == "exact":
            i = bisect_left(self, value, start, stop)
            if not start <= i < stop or value is not self[i] != value:
                raise ValueError(f"{value!r} is not in the sorted sequence")
            else:
                return i
        else:
            raise ValueError(f"expected 'left', 'exact', or 'right' for the mode, got {mode!r}")

    @property
    def between(self: Self, /) -> SortedSequenceBetweenProxy[T_co]:
        return SortedSequenceBetweenProxy(self)
