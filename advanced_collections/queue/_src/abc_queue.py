import operator
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from .queue_protocol import QueueProtocol

T = TypeVar("T")

Self = TypeVar("Self", bound="AbstractQueue")


class AbstractQueue(QueueProtocol[T], ABC, Generic[T]):

    __slots__ = ()

    def __add__(self: Self, other: "AbstractQueue[T]", /) -> Self:
        return NotImplemented

    def __radd__(self: Self, other: Any, /) -> Self:
        return type(self).__add__(self, other)

    def __iadd__(self: Self, other: Iterable[T], /) -> Self:
        if not isinstance(other, Iterable):
            return NotImplemented
        self.extend(other)
        return self

    def __imul__(self: Self, other: int, /) -> Self:
        try:
            other = operator.index(other)
        except TypeError:
            return NotImplemented
        if other <= 0:
            self.clear()
        elif other > 1:
            self.extend(
                x
                for x in [*self]
                for _ in range(other - 1)
            )
        return self

    def __mul__(self: Self, other: int, /) -> Self:
        try:
            other = operator.index(other)
        except TypeError:
            return NotImplemented
        if other == 1:
            return self.copy()
        else:
            result = self.copy()
            result *= other
            return result

    def __rmul__(self: Self, other: int, /) -> Self:
        return type(self).__mul__(self, other)

    @abstractmethod
    def __iter__(self: Self, /) -> Iterator[T]:
        raise NotImplementedError

    @abstractmethod
    def __len__(self: Self, /) -> int:
        raise NotImplementedError

    @abstractmethod
    def append(self: Self, element: T, /) -> None:
        raise NotImplementedError

    def clear(self: Self, /) -> None:
        try:
            while True:
                self.pop()
        except IndexError:
            pass

    def extend(self: Self, iterable: Iterable[T], /) -> None:
        if isinstance(iterable, Iterable):
            for element in iterable:
                self.append(element)
        else:
            raise TypeError(f"expected iterable, got {iterable!r}")

    def get(self: Self, /) -> T:
        return self.pop()

    @abstractmethod
    def peek(self: Self, /) -> T:
        raise NotImplementedError

    @abstractmethod
    def pop(self: Self, /) -> T:
        raise NotImplementedError

    def push(self: Self, element: T, /) -> None:
        self.append(element)

    def pushpop(self: Self, element: T, /) -> T:
        self.append(element)
        return self.pop()

    def put(self: Self, element: T, /) -> None:
        self.append(element)

    def replace(self: Self, item: T, /) -> T:
        if len(self) == 0:
            raise IndexError(f"cannot replace top element of empty queue")
        result = self.pop()
        self.append(item)
        return result
