from __future__ import annotations
import sys
from typing import Any, Generic, Optional, Type, TypeVar, Union, overload

if sys.version_info < (3, 9):
    from typing import Callable, Iterable, Mapping, Dict as dict, Set as set, Tuple as tuple
else:
    from collections.abc import Callable, Iterable, Mapping

from ._abc_mapping import SortedMutableMapping
from ._sorted_list import SortedList

__all__ = ["SortedDict"]

KT = TypeVar("KT")
VT = TypeVar("VT")
KT_co = TypeVar("KT_co", covariant=True)
VT_co = TypeVar("VT_co", covariant=True)

reprs_seen: set[int] = {*()}


class SortedDict(SortedMutableMapping[KT_co, VT_co], Generic[KT_co, VT_co]):
    __mapping: dict[KT_co, VT_co]
    __sequence: SortedList[KT_co]

    __slots__ = {
        "__mapping":
            "Maps keys to values using a hashed dict.",
        "__sequence":
            "Stores the keys in order using a sorted list.",
    }

    @overload
    def __init__(self: SortedDict[KT, VT], iterable: Optional[Union[Mapping[KT, VT], Iterable[tuple[KT, VT]]]] = ..., /) -> None:
        ...

    @overload
    def __init__(self: SortedDict[str, VT], iterable: Optional[Union[Mapping[str, VT], Iterable[tuple[str, VT]]]] = ..., /, **kwargs: VT) -> None:
        ...

    def __init__(self, iterable=None, /, **kwargs) -> None:
        if iterable is None:
            self.__mapping = kwargs
            self.__sequence = SortedList(kwargs)
        elif isinstance(iterable, Iterable):
            self.__mapping = {}
            self.__mapping.update(iterable, **kwargs)
            self.__sequence = SortedList(self.__mapping)
        else:
            raise TypeError(f"{type(self).__name__} expected a mapping or iterable, got {iterable!r}")

    def __repr__(self: SortedDict[Any, Any], /) -> str:
        if id(self) in reprs_seen:
            return "..."
        elif len(self) == 0:
            return f"{type(self).__name__}()"
        reprs_seen.add(id(self))
        try:
            data = ", ".join([f"{key!r}: {value!r}" for key, value in self.items()])
            return f"{type(self).__name__}({{{data}}})"
        finally:
            reprs_seen.remove(id(self))

    @classmethod
    def from_iterable(cls: Type[SortedDict[KT, VT]], iterable: Union[Mapping[KT, VT], Iterable[tuple[KT, VT]]], /) -> SortedDict[KT, VT]:
        if isinstance(iterable, Iterable):
            return cls(iterable)  # type: ignore
        else:
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")

    @classmethod
    def from_sorted(cls: Type[SortedDict[KT, VT]], iterable: Union[Mapping[KT, VT], Iterable[tuple[KT, VT]]], /) -> SortedDict[KT, VT]:
        if isinstance(iterable, Iterable):
            return cls(iterable)  # type: ignore
        else:
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")

    @property
    def _mapping(self: SortedMapping[KT, VT], /) -> dict[KT, VT]:
        return self.__mapping

    @property
    def _sequence(self: SortedMapping[KT, VT], /) -> SortedList[KT]:
        return self.__sequence
