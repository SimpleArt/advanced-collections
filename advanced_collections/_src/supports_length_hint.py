from typing import Protocol, TypeVar, runtime_checkable

Self = TypeVar("Self", bound="SupportsLengthHint")


@runtime_checkable
class SupportsLengthHint(Protocol):

    def __length_hint__(self: Self, /) -> int:
        ...
