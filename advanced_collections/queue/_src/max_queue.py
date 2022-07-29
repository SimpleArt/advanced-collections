from collections.abc import Iterable, Iterator, MutableSequence
from copy import deepcopy
from operator import length_hint
from typing import Any, Optional, TypeVar

from advanced_collections._src.comparable import SupportsRichHashableComparison

from .abc_queue import AbstractQueue

T = TypeVar("T", bound=SupportsRichHashableComparison)

try:
    from heapq import _siftdown_max as siftdown
except ImportError:
    def siftdown(heap: MutableSequence[Any], startpos: int, pos: int, /) -> None:
        newitem = heap[pos]
        # Follow the path to the root, moving parents down until
        # finding a place newitem fits.
        while pos > startpos:
            parentpos = (pos - 1) >> 1
            parent = heap[parentpos]
            if parent < newitem:
                heap[pos] = parent
                pos = parentpos
            else:
                break
        heap[pos] = newitem

try:
    from heapq import _siftup_max as siftup
except ImportError:
    def siftup(heap: MutableSequence[Any], pos: int, /) -> None:
        endpos = len(heap)
        startpos = pos
        newitem = heap[pos]
        # Bubble up the larger child until hitting a leaf.
        childpos = 2 * pos + 1  # leftmost child position
        while childpos < endpos:
            # Set childpos to index of larger child.
            rightpos = childpos + 1
            if rightpos < endpos and not heap[rightpos] < heap[childpos]:
                childpos = rightpos
            # Move the larger child up.
            heap[pos] = heap[childpos]
            pos = childpos
            childpos = 2 * pos + 1
        # The leaf at pos is empty now. Put newitem there, and bubble it up
        # to its final resting place (by sifting its parents down).
        heap[pos] = newitem
        siftdown(heap, startpos, pos)

try:
    from heapq import _heapify_max as heapify
except ImportError:
    def heapify(heap: MutableSequence[Any], /) -> None:
        for i in reversed(range(len(heap) // 2)):
            siftup(heap, i)

try:
    from heapq import _heappop_max as heappop
except ImportError:
    def heappop(heap: MutableSequence[T], /) -> T:
        if len(heap) > 1:
            return heapreplace(heap, heap.pop())
        else:
            return heap.pop()

try:
    from heapq import _heapreplace_max as heapreplace
except ImportError:
    def heapreplace(heap: MutableSequence[T], item: T, /) -> T:
        returnitem = heap[0]
        heap[0] = item
        siftup(heap, 0)
        return returnitem

def heappush(heap: MutableSequence[T], item: T, /) -> None:
    heap.append(item)
    siftdown(heap, 0, len(heap) - 1)

def heappushpop(heap: MutableSequence[T], item: T, /) -> T:
    if len(heap) > 0 and heap[0] < item:
        item, heap[0] = heap[0], item
        siftup(heap, 0)
    return item

Self = TypeVar("Self", bound="MaxPriorityQueue")

reprs_seen: set[int] = set()


class MaxPriorityQueue(AbstractQueue[T]):
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

    def __add__(self: Self, other: "MaxPriorityQueue[T]", /) -> Self:
        if isinstance(other, MaxPriorityQueue) and type(other).__add__ is MaxPriorityQueue.__add__:
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
