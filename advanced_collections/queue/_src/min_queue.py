from collections.abc import Iterable, Sequence
from copy import deepcopy
from heapq import heapify, heappop, heappush, heappushpop, heapreplace
from operator import length_hint
from typing import Optional, TypeVar

from advanced_collections._src.comparable import SupportsRichHashableComparison

from .abc_queue import AbstractQueue

T = TypeVar("T", bound=SupportsRichHashableComparison)
Self = TypeVar("Self", "MinPriorityQueue")

reprs_seen: set[int] = set()


class MinPriorityQueue(AbstractQueue[T]):
    _heap: list[T]

    __slots__ = {
        "_heap":
            "A list that stores the heap.",
    }

    def __init__(self: Self, iterable: Optional[Iterable[T]] = None, /) -> None:
        if iterable is None:
            self._heap = []
        elif isinstance(iterable, Iterable):
            self._heap = [*iterable]
            heapify(self._heap)
        else:
            raise TypeError(f"expected None or iterable, got {iterable!r}")

    def __add__(self: Self, other: "MinPriorityQueue[T]", /) -> Self:
        if isinstance(other, MinPriorityQueue) and type(other).__add__ is MinPriorityQueue.__add__:
            result = type(self)()
            if len(other) <= len(self) // 8:
                result._heap = self._heap.copy()
                result += other
            elif len(self) <= len(other) // 8:
                result._heap = other._heap.copy()
                result += self
            else:
                result._heap = [*self, *other]
                heapify(result._heap)
            return result
        else:
            return NotImplemented

    def __contains__(self: Self, element: Any, /) -> bool:
        return element in self._heap

    def __copy__(self: Self, /) -> Self:
        return self.copy()

    def __deepcopy__(self: Self, /) -> Self:
        result = type(self)()
        result._heap = deepcopy(self._heap)
        return result

    def __iadd__(self: Self, other: Iterable[T], /) -> Self:
        heap = self._heap
        if not isinstance(other, Iterable):
            return NotImplemented
        elif hasattr(type(other), "__len__") or hasattr(type(other), "__length_hint__"):
            if length_hint(other) <= len(heap) // 8:
                for element in other:
                    heappush(heap, element)
            else:
                heap.extend(other)
                heapify(heap)
        else:
            L1 = len(heap)
            heap.extend(other)
            L2 = len(heap) - L1
            if L2 <= L1 // 8:
                other = heap[L1:]
                del heap[L1:]
                for element in other:
                    heappush(heap, element)
            else:
                heapify(heap)
        return self

    def __imul__(self: Self, other: int, /) -> Self:
        try:
            other = operator.index(other)
        except TypeError:
            return NotImplemented
        if other == 0:
            self.clear()
        elif other > 1:
            self._heap *= other
            heapify(self._heap)
        return self

    def __iter__(self: Self, /) -> Iterator[T]:
        return iter(self._heap)

    def __len__(self: Self, /) -> int:
        return len(self._heap)

    def __mul__(self: Self, other: int, /) -> Self:
        try:
            other = operator.index(other)
        except TypeError:
            return NotImplemented
        if other == 0:
            self.clear()
        elif other > 1:
            self._heap *= other
            heapify(self._heap)
        return self

    def __repr__(self: Self, /) -> str:
        if id(self) in reprs_seen:
            return "..."
        reprs_seen.add(id(self))
        try:
            heap = "" if len(self._heap) == 0 else repr(self._heap)
            return f"{type(self).__name__}({heap})"
        finally:
            reprs_seen.remove(id(self))

    def append(self: Self, element: T, /) -> None:
        heappush(self._heap, element)

    def clear(self: Self, /) -> None:
        self._heap.clear()

    def copy(self: Self, /) -> Self:
        result = type(self)()
        result._heap = self._heap.copy()
        return result

    def extend(self: Self, iterable: Iterable[T], /) -> None:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"expected iterable, got {iterable!r}")
        self += iterable

    def peek(self: Self, /) -> T:
        if len(self._heap) == 0:
            raise IndexError("cannot peek from empty heap")
        return self._heap[0]

    def pop(self: Self, /) -> T:
        if len(self._heap) == 0:
            raise IndexError("cannot pop from empty heap")
        return heappop(self._heap)

    push = append

    def pushpop(self: Self, element: T, /) -> T:
        return heappushpop(self._heap, element)

    put = append

    def replace(self: Self, element: T, /) -> T:
        if len(self._heap) == 0:
            raise IndexError("cannot replace top element from empty heap")
        return heapreplace(self._heap, element)
