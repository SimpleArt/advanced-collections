from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from .queue_protocol import QueueProtocol

T = TypeVar("T")

Self = TypeVar("Self", bound="AbstractQueue")


class AbstractQueue(QueueProtocol[T], ABC, Generic[T]):

    def __len__(self: Self, /) -> int:
        return len(self)

    @abstractmethod
    def append(self: Self, element: T, /) -> None:
        raise NotImplementedError

    def get(self: Self, /) -> T:
        return self.pop()

    @abstractmethod
    def peek(self: Self, /) -> T:
        item = self.pop()
        self.append(item)
        return item

    @abstractmethod
    def pop(self: Self, /) -> T:
        raise NotImplementedError

    def put(self: Self, item: T, /) -> None:
        self.append(item)
