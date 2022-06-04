import sys
from typing import Any, Protocol, TypeVar, runtime_checkable

if sys.version_info < (3, 9):
    from typing import Hashable
else:
    from collections.abc import Hashable

Self = TypeVar("Self", bound="SupportsRichHashableComparison")


@runtime_checkable
class SupportsRichHashableComparison(Hashable, Protocol):

    def __eq__(self: Self, other: Any) -> bool: ...
    def __ge__(self: Self, other: Any) -> bool: ...
    def __gt__(self: Self, other: Any) -> bool: ...
    def __le__(self: Self, other: Any) -> bool: ...
    def __lt__(self: Self, other: Any) -> bool: ...
    def __ne__(self: Self, other: Any) -> bool: ...
