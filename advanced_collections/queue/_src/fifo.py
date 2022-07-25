import operator
from collections.abc import Iterable, Iterator, Reversible
from copy import deepcopy
from itertools import chain
from typing import Any, Generic, Optional, TypeVar, Union, overload

from advanced_collections._src.viewable_mutable_sequence import ViewableMutableSequence

from .abc_queue import AbstractQueue

__all__ = ["FifoQueue"]

T = TypeVar("T")

Self = TypeVar("Self", bound="FifoQueue")

reprs_seen: set[int] = set()


class FifoQueue(AbstractQueue[T], ViewableMutableSequence[T], Generic[T]):
    _back: list[T]
    _front: list[T]

    __slots__ = {
        "_back":
            "A list that contains the back of the data in order.",
        "_front":
            "A list that contains the front of the data in reversed order.",
    }

    def __init__(self: Self, iterable: Optional[Iterable[T]] = None, /) -> None:
        if iterable is None:
            self._back = []
            self._front = []
        elif isinstance(iterable, Reversible):
            self._back = []
            self._front = iterable[::-1] if type(iterable) is list else [*reversed(iterable)]
        elif isinstance(iterable, Iterable):
            self._back = [*iterable]
            self._front = []
        else:
            raise TypeError(f"expected an iterable or None, got {iterable!r}")

    def __add__(self: Self, other: "FifoQueue[T]", /) -> Self:
        if isinstance(other, FifoQueue) and type(other).__add__ is Fifo.__add__:
            result = type(self)()
            result._front = self._back[::-1]
            result._front.extend(self._front)
            result._back = other._front[::-1]
            result._back.extend(other._back)
            return result
        else:
            return NotImplemented

    def __contains__(self: Self, element: Any, /) -> bool:
        return element in self._front or element in self._back

    def __deepcopy__(self: Self, /) -> Self:
        return type(self)(map(deepcopy, self))

    def __copy__(self: Self, /) -> Self:
        return self.copy()

    def __delitem__(self: Self, index: Union[int, slice], /) -> None:
        if isinstance(index, slice):
            range_ = range(len(self))[index]
            if len(range_) == 0:
                return
            elif len(range_) == len(self):
                self.clear()
                return
            elif range_.step < 0:
                range_ = range_[::-1]
            index = slice(range_.start, range_.stop, range_.step)
            if len(self._front) == 0:
                del self._back[index]
            else:
                front = range(len(self._front))[::-1][index][::-1]
                if len(front) < len(range_):
                    start = range(len(self._front))[index][-1] + index.step - len(self._front)
                    stop = index.stop - len(self._front)
                    step = index.step
                    del self._back[start : stop : step]
                del self._front[front.start : front.stop : front.step]
        else:
            index = range(len(self))[index]
            if index == 0:
                self.popleft()
                return
            elif index + 1 == len(self):
                self.pop()
                return
            elif len(self) < 32 or len(self._back) < 2 * len(self._front) < 4 * len(self._back):
                pass
            elif len(self._back) > len(self._front):
                diff = len(self._back) - len(self._front)
                self._front[:0] = self._back[diff // 2::-1]
                del self._back[diff // 2::-1]
            else:
                diff = len(self._front) - len(self._back)
                self._back[:0] = self._front[diff // 2::-1]
                del self._front[diff // 2::-1]
            if index < len(self._front):
                del self._front[~index]
            else:
                del self._back[index - len(self._front)]

    @overload
    def __getitem__(self: Self, index: int, /) -> T: ...

    @overload
    def __getitem__(self: Self, index: slice, /) -> Self: ...

    def __getitem__(self, index):
        if isinstance(index, slice):
            range_ = range(len(self))[index]
            if len(range_) == 0:
                return type(self)()
            elif len(range_) == len(self):
                if range_.step > 0:
                    return self.copy()
                else:
                    result = self.copy()
                    result.reverse()
                    return result
            is_reversed = range_.step < 0
            if is_reversed:
                range_ = range_[::-1]
            result = type(self)()
            index = slice(range_.start, range_.stop, range_.step)
            if len(self._front) == 0:
                if is_reversed:
                    result._front = self._back[index]
                else:
                    result._back = self._back[index]
            else:
                front = range(len(self._front))[::-1][index][::-1]
                if len(front) < len(range_):
                    start = range(len(self._front))[index][-1] + index.step - len(self._front)
                    stop = index.stop - len(self._front)
                    step = index.step
                    if is_reversed:
                        result._front = self._back[start : stop : step]
                    else:
                        result._back = self._back[start : stop : step]
                if is_reversed:
                    result._back = self._front[front.start : front.stop : front.step]
                else:
                    result._front = self._front[front.start : front.stop : front.step]
            return result
        index = range(len(self))[index]
        if index < len(self._front):
            return self._front[~index]
        else:
            return self._back[index - len(self._front)]

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
        elif len(range_) == 1:
            pass
        elif len(self._back) > len(self._front):
            len_ = len(self._back)
            self._back.extend(reversed(self._front))
            self._back *= len(range_) - 1
            self._back.extend(islice(self._back, len_))
        else:
            len_ = len(self._front)
            self._front.extend(reversed(self._back))
            self._front *= len(range_) - 1
            self._front.extend(islice(self._front, len_))
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
        return chain(reversed(self._front), self._back)

    def __len__(self: Self, /) -> int:
        return len(self._front) + len(self._back)

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
            result._front *= len(range_)
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
        return chain(reversed(self._back), self._front)

    @overload
    def __setitem__(self: Self, index: int, element: T, /) -> None: ...

    @overload
    def __setitem__(self: Self, index: slice, element: Iterable[T], /) -> None: ...

    def __setitem__(self, index, element, /):
        if isinstance(index, slice):
            raise NotImplementedError("__setitem__ is not implemented for deques")
        index = range(len(self))[index]
        if index < len(self._front):
            self._front[~index] = element
        else:
            self._back[index - len(self._front)] = element

    def append(self: Self, element: T, /) -> None:
        self._back.append(element)

    def appendleft(self: Self, element: T, /) -> None:
        self._front.append(element)

    def clear(self: Self, /) -> None:
        self._back.clear()
        self._front.clear()

    def copy(self: Self, /) -> None:
        result = type(self)()
        result._front.extend(reversed(self._back))
        result._front.extend(self._front)
        return result

    def extend(self: Self, iterable: Iterable[T], /) -> None:
        if not isinstance(other, Reversible) or len(self._back) != 0 or len(self._front) > 2 * len(other):
            self._back.extend(other)
        elif len(self._front) == 0:
            self._front = other[::-1] if type(other) is list else [*reversed(other)]
        else:
            self._front[:0] = reversed(other)

    def extendleft(self: Self, iterable: Iterable[T], /) -> None:
        self._front.extend(iterable)

    def index(self: Self, element: Any, start: int = 0, stop: Optional[int] = None, /) -> int:
        start = operator.index(start)
        return start + operator.indexOf(self.islice[start:stop], element)

    def insert(self: Self, index: int, element: T, /) -> None:
        index = operator.index(index)
        if index < 0:
            index += len(self)
        if index <= 0:
            self._front.append(element)
            return
        elif index >= len(self):
            self._back.append(element)
            return
        elif len(self) < 32 or len(self._back) < 2 * len(self._front) < 4 * len(self._back):
            pass
        elif len(self._back) > len(self._front):
            diff = len(self._back) - len(self._front)
            self._front[:0] = self._back[diff // 2::-1]
            del self._back[diff // 2::-1]
        else:
            diff = len(self._front) - len(self._back)
            self._back[:0] = self._front[diff // 2::-1]
            del self._front[diff // 2::-1]
        if index < len(self._front):
            self._front.insert(len(self._front) - index, element)
        else:
            self._back.insert(index - len(self._front), element)

    def peek(self: Self, /) -> T:
        if len(self._front) > 0:
            return self._front[-1]
        elif len(self._back) > 0:
            return self._back[0]
        else:
            raise IndexError("cannot peek from empty queue")

    def pop(self: Self, index: int = 0, /) -> T:
        if isinstance(index, slice):
            raise TypeError(f"could not interpret index as an integer, got {index!r}")
        index = range(len(self))[index]
        if index == 0:
            if len(self._front) == 0:
                self.reverse()
                self._front.reverse()
            return self._front.pop()
        elif index + 1 == len(self):
            return self.popright()
        elif not 0 < index < len(self):
            raise IndexError("pop index out of range")
        elif len(self) < 32 or len(self._back) < 2 * len(self._front) < 4 * len(self._back):
            pass
        elif len(self._back) > len(self._front):
            diff = len(self._back) - len(self._front)
            self._front[:0] = self._back[diff // 2 :: -1]
            del self._back[diff // 2 :: -1]
        else:
            diff = len(self._front) - len(self._back)
            self._back[:0] = self._front[diff // 2 :: -1]
            del self._front[diff // 2 :: -1]
        if index < len(self._front):
            return self._front.pop(~index)
        else:
            return self._back.pop(index - len(self._front))

    def popright(self: Self, /) -> T:
        if len(self._back) > 0:
            return self._back.pop()
        elif len(self._front) == 0:
            raise IndexError("cannot peek from empty queue")
        elif len(self._front) < 4:
            return self._front.pop(0)
        else:
            self._back = self._front[len(self._front) // 4 :: -1]
            return self._back.pop()

    def reverse(self: Self, /) -> None:
        self._back, self._front = self._front, self._back

    def rotate(self: Self, n: int = 1, /) -> None:
        n = (-operator.index(n)) % len(self)
        if n == 0:
            return
        elif n < len(self) - n:
            n = len(self) - n
            self._front.extend(
                self._back.pop()
                for _ in range(min(n, len(self._back)))
            )
            n -= len(self._back)
            if n > 0:
                self._front.extend(self._front[:n])
                del self._front[:n]
        else:
            self._back.extend(
                self._front.pop()
                for _ in range(min(n, len(self._front)))
            )
            n -= len(self._front)
            if n > 0:
                self._back.extend(self._back[:n])
                del self._back[:n]
