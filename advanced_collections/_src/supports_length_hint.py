from __future__ import annotations
from typing import Protocol, TypeVar, runtime_checkable

__all__ = ["SupportsLengthHint"]

Self = TypeVar("Self", bound="SupportsLengthHint")


@runtime_checkable
class SupportsLengthHint(Protocol):

    def __length_hint__(self: Self, /) -> int:
        ...
