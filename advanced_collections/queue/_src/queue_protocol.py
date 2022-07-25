from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")

Self = TypeVar("Self", bound="QueueProtocol")


@runtime_checkable
class QueueProtocol(Protocol[T]):

    def get(self: Self, /) -> T: ...
    def put(self: Self, item: T, /) -> None: ...
