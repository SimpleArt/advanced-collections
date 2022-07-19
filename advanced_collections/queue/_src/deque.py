import operator
from collections.abc import Iterable, Iterator, Reversible
from copy import deepcopy
from itertools import chain, islice
from typing import Any, Generic, Optional, TypeVar, Union, overload

from advanced_collections._src.viewable_mutable_sequence import ViewableMutableSequence

__all__ = ["Deque"]

T = TypeVar("T")

Self = TypeVar("Self", bound="Deque")

reprs_seen: set[int] = {0} - {0}


class Deque(ViewableMutableSequence[T], Generic[T]):
    _forward: list[T]
    _reversed: list[T]

    __slots__ = {
        "_forward":
            "A list that contains the end of the data in order.",
        "_reversed":
            "A list that contains the start of the data in reversed order.",
    }

    def __init__(self: Self, iterable: Optional[Iterable[T]] = None, /) -> None:
        if iterable is None:
            self._forward = []
            self._reversed = []
        elif isinstance(iterable, Iterable):
            self._forward = [*iterable]
            self._reversed = []
        else:
            raise TypeError(f"expected an iterable or None, got {iterable!r}")

    def __add__(self: Self, other: "FifoQueue[T]", /) -> Self:
        if isinstance(other, FifoQueue) and type(other).__add__ is Fifo.__add__:
            result = type(self)()
            result._reversed = self._forward[::-1]
            result._reversed.extend(self._reversed)
            result._forward = other._reversed[::-1]
            result._forward.extend(other._forward)
            return result
        else:
            return NotImplemented

    def __contains__(self: Self, element: Any, /) -> bool:
        return element in self._reversed or element in self._forward

    def __deepcopy__(self: Self, /) -> Self:
        return type(self)(map(deepcopy, self))

    def __copy__(self: Self, /) -> Self:
        return self.copy()

    def __delitem__(self: Self, index: Union[int, slice], /) -> None:
        if isinstance(index, slice):
            range_ = range(len(self))[index]
            if range_.step < 0:
                range_ = range_[::-1]
            index = slice(range_.start, range_.stop, range_.step)
            reversed = range(len(self._reversed))[::-1][index]
            range_ = range_[len(reversed):]
            del self._forward[range_.start - len(self._reversed) : range_.stop - len(self._reversed) : range_.step]
            del self._reversed[reversed.start : reversed.stop : reversed.step]
        else:
            index = range(len(self))[index]
            if len(self) < 32 or len(self._forward) < 2 * len(self._reversed) < 4 * len(self._forward):
                pass
            elif len(self._forward) > len(self._reversed):
                diff = len(self._forward) - len(self._reversed)
                self._reversed[:0] = self._forward[diff // 2::-1]
                del self._forward[diff // 2::-1]
            else:
                diff = len(self._reversed) - len(self._forward)
                self._forward[:0] = self._reversed[diff // 2::-1]
                del self._reversed[diff // 2::-1]
            if index < len(self._reversed):
                del self._reversed[~index]
            else:
                del self._forward[index - len(self._reversed)]

    @overload
    def __getitem__(self: Self, index: int, /) -> T: ...

    @overload
    def __getitem__(self: Self, index: slice, /) -> Self: ...

    def __getitem__(self, index):
        if isinstance(index, slice):
            range_ = range(len(self))[index]
            index = slice(range_.start, range_.stop, range_.step)
            if range_.step < 0:
                range_ = range_[::-1]
                reversed = range(len(self._reversed))[::-1][index][::-1]
                range_ = range_[len(reversed):]
                result = type(self)()
                result._reversed = self._forward[range_.start - len(self._reversed) : range_.stop - len(self._reversed) : range_.step]
                result._forward = self._reversed[reversed.start : reversed.stop : reversed.step]
            else:
                reversed = range(len(self._reversed))[::-1][index][::-1]
                range_ = range_[len(reversed):]
                result = type(self)()
                result._forward = self._forward[range_.start - len(self._reversed) : range_.stop - len(self._reversed) : range_.step]
                result._reversed = self._reversed[reversed.start : reversed.stop : reversed.step]
            return result
        index = range(len(self))[index]
        if index < len(self._reversed):
            return self._reversed[~index]
        else:
            return self._reversed[index - len(self._reversed)]

    def __imul__(self: Self, other: int, /) -> Self:
        try:
            range_ = range(other)
        except TypeError:
            return NotImplemented
        if len(range_) == 0:
            self.clear()
        elif len(range_) == 1:
            pass
        elif len(self._forward) > len(self._reversed):
            len_ = len(self._forward)
            self._forward.extend(reversed(self._reversed))
            self._forward *= len(range_) - 1
            self._forward.extend(islice(self._forward, len_))
        else:
            len_ = len(self._reversed)
            self._reversed.extend(reversed(self._forward))
            self._reversed *= len(range_) - 1
            self._reversed.extend(islice(self._reversed, len_))
        return self

    def __islice__(self: Self, start: Optional[int], stop: Optional[int], step: Optional[int], /) -> Iterator[T]:
        range_ = range(len(self))[start:stop:step]
        if len(range_) == len(self):
            return iter(self) if range_.step == 1 else reversed(self)
        elif len(range_) == 0:
            return (self[i] for i in range_)
        elif range_.step == 1 and range_.start == 0:
            return islice(self, range_.stop)
        elif range_.step == -1 and range_.start + 1 == len(self):
            return islice(reversed(self), len(range_))
        else:
            return (self[i] for i in range_)

    def __iter__(self: Self, /) -> Iterator[T]:
        return chain(reversed(self._reversed), self._forward)

    def __len__(self: Self, /) -> int:
        return len(self._reversed) + len(self._forward)

    def __mul__(self: Self, other: int, /) -> Self:
        try:
            range_ = range(other)
        except TypeError:
            return NotImplemented
        if len(range_) == 0:
            return type(self)()
        elif len(range_) == 1:
            return self.copy()
        else:
            result = self.copy()
            result._reversed *= len(range_)
            return result

    __rmul__ = __mul__

    def __repr__(self: Self, /) -> str:
        if id(self) in reprs_seen:
            return "..."
        elif len(self) == 0:
            return f"{type(self).__name__}()"
        reprs_seen.add(id(self))
        try:
            data = ", ".join([repr(x) for x in self])
            return f"{type(self).__name__}([{data}])"
        finally:
            reprs_seen.remove(id(self))

    def __reversed__(self: Self, /) -> Iterator[T]:
        return chain(reversed(self._forward), self._reversed)

    @overload
    def __setitem__(self: Self, index: int, element: T, /) -> None: ...

    @overload
    def __setitem__(self: Self, index: slice, element: Iterable[T], /) -> None: ...

    def __setitem__(self, index, element, /):
        if isinstance(index, slice):
            raise NotImplementedError("__setitem__ is not implemented for deques")
        index = range(len(self))[index]
        if index < len(self._reversed):
            self._reversed[~index] = element
        else:
            self._forward[index - len(self._reversed)] = element

    def append(self: Self, element: T, /) -> None:
        self._forward.append(element)

    def appendleft(self: Self, element: T, /) -> None:
        self._reversed.append(element)

    def clear(self: Self, /) -> None:
        self._forward.clear()
        self._reversed.clear()

    def copy(self: Self, /) -> None:
        result = type(self)()
        result._reversed.extend(reversed(self._forward))
        result._reversed.extend(self._reversed)
        return result

    def extend(self: Self, iterable: Iterable[T], /) -> None:
        self._forward.extend(iterable)

    def extendleft(self: Self, iterable: Iterable[T], /) -> None:
        self._reversed.extend(iterable)

    def index(self: Self, element: Any, start: int = 0, stop: Optional[int] = None, /) -> int:
        start = operator.index(start)
        return start + operator.indexOf(self.islice[start:stop], element)

    def insert(self: Self, index: int, element: T, /) -> None:
        index = operator.index(index)
        if index < 0:
            index += len(self)
        if index <= 0:
            self._reversed.append(element)
        elif index >= len(self):
            self._forward.append(element)
        else:
            if len(self) < 32 or len(self._forward) < 2 * len(self._reversed) < 4 * len(self._forward):
                pass
            elif len(self._forward) > len(self._reversed):
                diff = len(self._forward) - len(self._reversed)
                self._reversed[:0] = self._forward[diff // 2::-1]
                del self._forward[diff // 2::-1]
            else:
                diff = len(self._reversed) - len(self._forward)
                self._forward[:0] = self._reversed[diff // 2::-1]
                del self._reversed[diff // 2::-1]
            if index < len(self._reversed):
                self._reversed.insert(len(self._reversed) - index, element)
            else:
                self._forward.insert(index - len(self._reversed), element)

    def pop(self: Self, index: int = -1, /) -> T:
        index = operator.index(index)
        if index < 0:
            index += len(self)
        if index == 0 < len(self._reversed):
            return self._reversed.pop()
        elif index + 1 == len(self) and len(self._forward) > 0:
            return self._forward.pop()
        elif not 0 <= index < len(self):
            raise IndexError("pop index out of range")
        else:
            if len(self) < 32 or len(self._forward) < 2 * len(self._reversed) < 4 * len(self._forward):
                pass
            elif len(self._forward) > len(self._reversed):
                diff = len(self._forward) - len(self._reversed)
                self._reversed[:0] = self._forward[diff // 2::-1]
                del self._forward[diff // 2::-1]
            else:
                diff = len(self._reversed) - len(self._forward)
                self._forward[:0] = self._reversed[diff // 2::-1]
                del self._reversed[diff // 2::-1]
            if index < len(self._reversed):
                return self._reversed.pop(~index)
            else:
                return self._forward.pop(index - len(self._reversed))

    def popleft(self: Self, /) -> T:
        if len(self) == 0:
            raise IndexError("cannot pop from empty deque")
        elif len(self._reversed) > 0:
            return self._reversed.pop()
        elif len(self) < 32 or len(self._forward) < 2 * len(self._reversed) < 4 * len(self._forward):
            pass
        elif len(self._forward) > len(self._reversed):
            diff = len(self._forward) - len(self._reversed)
            self._reversed[:0] = self._forward[diff // 2::-1]
            del self._forward[diff // 2::-1]
        else:
            diff = len(self._reversed) - len(self._forward)
            self._forward[:0] = self._reversed[diff // 2::-1]
            del self._reversed[diff // 2::-1]
        if len(self._forward) > 0:
            return self._reversed.pop()
        else:
            return self._forward.pop(0)

    def reverse(self: Self, /) -> None:
        self._forward, self._reversed = self._reversed, self._forward

    def rotate(self: Self, n: int = 1, /) -> None:
        n = (-operator.index(n)) % len(self)
        if n == 0:
            return
        elif n < len(self) - n:
            n = len(self) - n
            self._reversed.extend(
                self._forward.pop()
                for _ in range(min(n, len(self._forward)))
            )
            n -= len(self._forward)
            if n > 0:
                self._reversed.extend(self._reversed[:n])
                del self._reversed[:n]
        else:
            self._forward.extend(
                self._reversed.pop()
                for _ in range(min(n, len(self._reversed)))
            )
            n -= len(self._reversed)
            if n > 0:
                self._forward.extend(self._forward[:n])
                del self._forward[:n]
