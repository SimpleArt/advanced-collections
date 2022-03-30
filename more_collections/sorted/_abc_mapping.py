from __future__ import annotations
import collections.abc
import sys
from abc import ABC, abstractmethod
from copy import copy, deepcopy
from typing import Any, Generic, Optional, Type, TypeVar, Union, overload

if sys.version_info < (3, 9):
    from typing import AbstractSet, ItemsView, Iterable, Iterator, KeysView, Mapping, MappingView, MutableMapping, Sequence, ValuesView, Set as set, Tuple as tuple
else:
    from collections.abc import Set as AbstractSet, ItemsView, Iterable, Iterator, KeysView, Mapping, MappingView, MutableMapping, Sequence, ValuesView

from ._abc_iterable import SortedIterable, SortedIterator
from ._abc_sequence import SortedSequence, SortedMutableSequence
from ._abc_set import SortedSet, SortedMutableSet

__all__ = ["SortedMappingView", "SortedItemsView", "SortedKeysView", "SortedValuesView", "SortedMapping", "SortedMutableMapping"]

Self = TypeVar("Self", bound="SortedMapping")
T = TypeVar("T")
KT = TypeVar("KT")
VT = TypeVar("VT")
KT_co = TypeVar("KT_co", covariant=True)
VT_co = TypeVar("VT_co", covariant=True)

reprs_seen: set[int] = {*()}


class SortedMappingView(MappingView, Generic[KT_co, VT_co]):
    __mapping: SortedMapping[KT_co, VT_co]

    __slots__ = ("__mapping",)

    def __init__(self: SortedMappingView[KT_co, VT_co], mapping: SortedMapping[KT_co, VT_co], /) -> None:
        if not isinstance(mapping, SortedMapping):
            raise TypeError(f"sorted mapping view requires a sorted mapping, got {mapping!r}")
        self.__mapping = mapping

    def __len__(self: SortedMappingView[Any, Any], /) -> int:
        return len(self._mapping)

    def __repr__(self: SortedMappingView[Any, Any], /) -> str:
        if id(self) in reprs_seen:
            return "..."
        reprs_seen.add(id(self))
        try:
            return f"{type(self).__name__}({self._mapping!r})"
        finally:
            reprs_seen.remove(id(self))

    @property
    def _mapping(self: SortedMappingView[KT_co, VT_co], /) -> SortedMapping[KT_co, VT_co]:
        return self.__mapping


class SortedItemsView(SortedMappingView[KT_co, VT_co], SortedSet[tuple[KT_co, VT_co]], ItemsView[KT_co, VT_co], Generic[KT_co, VT_co]):
    __sequence: Optional[SortedSequence[tuple[KT_co, VT_co]]]

    __slots__ = ("__sequence",)

    def __init__(self: SortedItemsView[KT_co, VT_co], mapping: SortedMapping[KT_co, VT_co], /) -> None:
        if not isinstance(mapping, SortedMapping):
            raise TypeError(f"sorted items view requires a sorted mapping, got {mapping!r}")
        super().__init__(mapping)
        self.__sequence = None
        self.__set = None

    def __and__(self: SortedItemsView[KT_co, VT_co], other: Iterable[Any], /) -> SortedMutableSet[tuple[KT_co, VT_co]]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)
        else:
            return NotImplemented

    def __contains__(self: SortedItemsView[Any, Any], item: Any, /) -> bool:
        return item in self._mapping.items()

    def __eq__(self: SortedItemsView[Any, Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set == other
        else:
            return NotImplemented

    def __ge__(self: SortedItemsView[Any, Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set >= other
        else:
            return NotImplemented

    def __gt__(self: SortedItemsView[Any, Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set > other
        else:
            return NotImplemented

    def __iter__(self: SortedItemsView[KT_co, VT_co], /) -> SortedIterator[tuple[KT_co, VT_co]]:
        import more_collections.sorted as mcs
        return mcs.SortedUserIterator((key, self._mapping[key]) for key in self._mapping)

    def __le__(self: SortedItemsView[Any, Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set <= other
        else:
            return NotImplemented

    def __lt__(self: SortedItemsView[Any, Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set < other
        else:
            return NotImplemented

    def __ne__(self: SortedItemsView[Any, Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set != other
        else:
            return NotImplemented

    def __or__(self: SortedItemsView[KT_co, VT_co], other: Iterable[T], /) -> SortedMutableSet[Union[tuple[KT_co, VT_co], T]]:
        if isinstance(other, AbstractSet):
            return self.union(other)
        else:
            return NotImplemented

    __ror__ = __or__

    def __rand__(self: SortedItemsView[Any, Any], other: Iterable[T], /) -> SortedMutableSet[T]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)  # type: ignore
        else:
            return NotImplemented

    def __reversed__(self: SortedItemsView[KT_co, VT_co], /) -> Iterator[tuple[KT_co, VT_co]]:
        return ((key, self._mapping[key]) for key in reversed(self._mapping))

    def __rsub__(self: SortedItemsView[Any, Any], other: Iterable[T], /) -> SortedMutableSet[T]:
        if isinstance(other, AbstractSet):
            return type(self).from_iterable(x for x in other if x not in self)
        else:
            return NotImplemented

    def __sub__(self: SortedItemsView[KT_co, VT_co], other: Iterable[Any], /) -> SortedMutableSet[tuple[KT_co, VT_co]]:
        if isinstance(other, AbstractSet):
            return self.difference(other)
        else:
            return NotImplemented

    def __xor__(self: SortedItemsView[KT_co, VT_co], other: Iterable[T], /) -> SortedMutableSet[Union[tuple[KT_co, VT_co], T]]:
        if isinstance(other, AbstractSet):
            return self.symmetric_difference(other)
        else:
            return NotImplemented

    __rxor__ = __xor__

    def difference(self: SortedItemsView[KT_co, VT_co], /, *iterables: Iterable[Any]) -> SortedMutableSet[tuple[KT_co, VT_co]]:
        import more_collections.sorted as mcs
        set_ = mcs.SortedSet.from_sorted(self)
        set_.difference_update(*iterables)
        return set_

    def isdisjoint(self: SortedItemsView[Any, Any], iterable: Iterable[Any], /) -> bool:
        if isinstance(iterable, AbstractSet):
            return iterable.isdisjoint(self)
        elif isinstance(iterable, Iterable):
            return self._set.isdisjoint(iterable)
        else:
            raise TypeError(f"isdisjoint argument is not iterable, got {iterable!r}")

    def issubset(self: SortedItemsView[Any, Any], iterable: Iterable[Any], /) -> bool:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"issubset argument is not iterable, got {iterable!r}")
        elif isinstance(iterable, set):
            return iterable.issuperset(self)
        elif isinstance(iterable, AbstractSet):
            return all(x in iterable for x in self)
        else:
            return len({x for x in iterable if x in self}) == len(self)

    def issuperset(self: SortedItemsView[Any, Any], iterable: Iterable[Any], /) -> bool:
        if isinstance(iterable, Iterable):
            return all(x in self for x in iterable)
        else:
            raise TypeError(f"issuperset argument is not iterable, got {iterable!r}")

    @classmethod
    def from_iterable(cls: Type[SortedItemsView[Any, Any]], iterable: Iterable[T], /) -> SortedMutableSet[T]:
        import more_collections.sorted as mcs
        return mcs.SortedSet.from_iterable(iterable)  # type: ignore

    @classmethod
    def from_sorted(cls: Type[SortedItemsView[Any, Any]], iterable: Iterable[T], /) -> SortedMutableSet[T]:
        import more_collections.sorted as mcs
        return mcs.SortedSet.from_sorted(iterable)  # type: ignore

    def intersection(self: SortedItemsView[KT_co, VT_co], /, *iterables: Iterable[Any]) -> SortedMutableSet[tuple[KT_co, VT_co]]:
        import more_collections.sorted as mcs
        set_ = mcs.SortedSet.from_sorted(self)
        set_.intersection_update(*iterables)
        return set_

    def symmetric_difference(self: SortedItemsView[KT_co, VT_co], /, *iterables: Iterable[T]) -> SortedMutableSet[Union[tuple[KT_co, VT_co], T]]:
        import more_collections.sorted as mcs
        set_ = mcs.SortedSet.from_sorted(self)
        set_.symmetric_difference_update(*iterables)
        return set_

    def union(self: SortedItemsView[KT_co, VT_co], /, *iterables: Iterable[T]) -> SortedMutableSet[Union[tuple[KT_co, VT_co], T]]:
        import more_collections.sorted as mcs
        return mcs.SortedSet.from_iterable(chain(self, *iterables))  # type: ignore

    @property
    def _sequence(self: SortedItemsView[KT_co, VT_co], /) -> SortedSequence[tuple[KT_co, VT_co]]:
        if self.__sequence is None:
            import more_collections.sorted as mcs
            sequence = mcs.SortedList.from_sorted(self)
            self.__sequence = sequence
            return sequence
        else:
            return self.__sequence

    @property
    def _set(self: SortedItemsView[KT_co, VT_co], /) -> AbstractSet[tuple[KT_co, VT_co]]:
        return self._mapping._mapping.items()


class SortedKeysView(SortedMappingView[KT_co, Any], SortedSet[KT_co], KeysView[KT_co], Generic[KT_co]):

    __slots__ = ()

    def __init__(self: SortedKeysView[KT_co], mapping: SortedMapping[KT_co, Any], /) -> None:
        if not isinstance(mapping, SortedMapping):
            raise TypeError(f"sorted keys view requires a sorted mapping, got {mapping!r}")
        super().__init__(mapping)

    def __and__(self: SortedKeysView[KT_co], other: Iterable[Any], /) -> SortedMutableSet[KT_co]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)
        else:
            return NotImplemented

    def __eq__(self: SortedKeysView[Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set == other
        else:
            return NotImplemented

    def __ge__(self: SortedKeysView[Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set >= other
        else:
            return NotImplemented

    def __gt__(self: SortedKeysView[Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set > other
        else:
            return NotImplemented

    def __le__(self: SortedKeysView[Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set <= other
        else:
            return NotImplemented

    def __lt__(self: SortedKeysView[Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set < other
        else:
            return NotImplemented

    def __ne__(self: SortedKeysView[Any], other: Any, /) -> bool:
        if isinstance(other, AbstractSet):
            return self._set != other
        else:
            return NotImplemented

    def __iter__(self: SortedKeysView[KT_co], /) -> SortedIterator[KT_co]:
        return iter(self._mapping)

    def __or__(self: SortedKeysView[KT_co], other: Iterable[T], /) -> SortedMutableSet[Union[KT_co, T]]:
        if isinstance(other, AbstractSet):
            return self.union(other)
        else:
            return NotImplemented

    __ror__ = __or__

    def __rand__(self: SortedKeysView[Any], other: Iterable[T], /) -> SortedMutableSet[T]:
        if isinstance(other, AbstractSet):
            return self.intersection(other)
        else:
            return NotImplemented

    def __rsub__(self: SortedKeysView[Any], other: Iterable[T], /) -> SortedMutableSet[T]:
        if isinstance(other, AbstractSet):
            import more_collections.sorted as mcs
            set_: SortedMutableSet[T] = mcs.SortedSet.from_iterable(other)
            set_ -= self
            return set_
        else:
            return NotImplemented

    def __sub__(self: SortedKeysView[KT_co], other: Iterable[T], /) -> SortedMutableSet[KT_co]:
        if isinstance(other, AbstractSet):
            return self.difference(other)
        else:
            return NotImplemented

    def __xor__(self: SortedKeysView[KT_co], other: Iterable[T], /) -> SortedMutableSet[Union[KT_co, T]]:
        if isinstance(other, AbstractSet):
            return self.symmetric_difference(other)
        else:
            return NotImplemented

    __rxor__ = __xor__

    def difference(self: SortedKeysView[KT_co], /, *iterables: Iterable[Any]) -> SortedMutableSet[KT_co]:
        import more_collections.sorted as mcs
        set_ = mcs.SortedSet.from_sorted(self)
        set_.difference_update(*iterables)
        return set_

    @classmethod
    def from_iterable(cls: Type[SortedKeysView[Any]], iterable: Iterable[T], /) -> SortedMutableSet[T]:
        import more_collections.sorted as mcs
        return mcs.SortedSet.from_iterable(iterable)  # type: ignore

    @classmethod
    def from_sorted(cls: Type[SortedKeysView[Any]], iterable: Iterable[T], /) -> SortedMutableSet[T]:
        import more_collections.sorted as mcs
        return mcs.SortedSet.from_sorted(iterable)  # type: ignore

    def intersection(self: SortedKeysView[KT_co], /, *iterables: Iterable[Any]) -> SortedMutableSet[KT_co]:
        import more_collections.sorted as mcs
        set_ = mcs.SortedSet.from_sorted(self)
        set_.intersection_update(*iterables)
        return set_

    def symmetric_difference(self: SortedKeysView[KT_co], /, *iterables: Iterable[T]) -> SortedMutableSet[Union[KT_co, T]]:
        import more_collections.sorted as mcs
        set_ = mcs.SortedSet.from_sorted(self)
        set_.symmetric_difference_update(*iterables)
        return set_

    def union(self: SortedKeysView[KT_co], /, *iterables: Iterable[T]) -> SortedMutableSet[Union[KT_co, T]]:
        import more_collections.sorted as mcs
        return mcs.SortedSet.from_iterable(chain(self, *iterables))  # type: ignore

    @property
    def _sequence(self: SortedKeysView[KT_co], /) -> SortedSequence[KT_co]:
        return self._mapping._sequence

    @property
    def _set(self: SortedKeysView[KT_co], /) -> AbstractSet[KT_co]:
        return self._mapping._mapping.keys()


class SortedValuesView(SortedMappingView[Any, VT_co], Sequence[VT_co], ValuesView[VT_co], Generic[VT_co]):

    __slots__ = ()

    def __init__(self: SortedValuesView[VT_co], mapping: SortedMapping[Any, VT_co], /) -> None:
        if not isinstance(mapping, SortedMapping):
            raise TypeError(f"sorted keys view requires a sorted mapping, got {mapping!r}")
        super().__init__(mapping)

    @overload
    def __getitem__(self: SortedValuesView[VT_co], index: int, /) -> VT_co:
        ...

    @overload
    def __getitem__(self: SortedValuesView[VT_co], index: slice, /) -> Sequence[VT_co]:
        ...

    def __getitem__(self, index, /):
        if isinstance(index, slice):
            return (self._mapping[key] for key in self._mapping._set[index])
        else:
            return self._mapping[self._mapping._set[index]]

    def __iter__(self: SortedValuesView[VT_co], /) -> Iterator[VT_co]:
        return (self._mapping[key] for key in self._mapping)

    def __reversed__(self: SortedValuesView[VT_co], /) -> Iterator[VT_co]:
        return (self._mapping[key] for key in reversed(self._mapping))


class SortedMapping(Mapping[KT_co, VT_co], SortedIterable[KT_co], Generic[KT_co, VT_co]):

    __slots__ = ()

    def __copy__(self: Self, /) -> Self:
        return type(self).from_sorted(self)  # type: ignore

    def __deepcopy__(self: Self, /) -> Self:
        return type(self).from_sorted((deepcopy(key), deepcopy(value)) for key, value in self.items())  # type: ignore

    def __getitem__(self: SortedMapping[KT, VT_co], key: KT, /) -> VT_co:
        return self._mapping[key]

    def __iter__(self: SortedMapping[KT_co, Any], /) -> SortedIterator[KT_co]:
        return iter(self._sequence)

    def __len__(self: SortedMapping[Any, Any], /) -> int:
        return len(self._mapping)

    def __repr__(self: SortedMapping[Any, Any], /) -> str:
        if id(self) in reprs_seen:
            return "..."
        reprs_seen.add(id(self))
        try:
            cls = type(self)
            data = "{" + ", ".join([f"{key!r}: {value!r}" for key, value in self.items()]) + "}"
            return f"{cls.__name__}.from_iterable({data})"
        finally:
            reprs_seen.remove(id(self))

    def __reversed__(self: SortedMapping[KT_co, Any], /) -> Iterator[KT_co]:
        return reversed(self._sequence)

    def copy(self: Self, /) -> Self:
        return copy(self)

    @classmethod
    def from_iterable(cls: Type[SortedMapping[KT_co, VT_co]], mapping: Union[Mapping[KT_co, VT_co], Iterable[tuple[KT_co, VT_co]]], /) -> SortedMapping[KT_co, VT_co]:
        if isinstance(mapping, Mapping):
            return cls.from_sorted(sorted(mapping.items()))  # type: ignore
        elif isinstance(mapping, Iterable):
            return cls.from_sorted(sorted(mapping, key=lambda x: x[0]))  # type: ignore
        else:
            raise TypeError(f"from_iterable expects a mapping, got {mapping!r}")

    @abstractmethod
    @classmethod
    def from_sorted(cls: Type[SortedMapping[KT_co, VT_co]], mapping: Union[Mapping[KT_co, VT_co], Iterable[tuple[KT_co, VT_co]]], /) -> SortedMapping[KT_co, VT_co]:
        raise NotImplementedError("from_sorted is a required method for sorted mappings")

    def items(self: SortedMapping[KT_co, VT_co], /) -> SortedItemsView[KT_co, VT_co]:
        return SortedItemsView(self)

    def keys(self: SortedMapping[KT_co, Any], /) -> SortedKeysView[KT_co]:
        return SortedKeysView(self)

    def values(self: SortedMapping[Any, VT_co], /) -> SortedValuesView[VT_co]:
        return SortedValuesView(self)

    @property
    @abstractmethod
    def _mapping(self: SortedMapping[KT_co, VT_co], /) -> Mapping[KT_co, VT_co]:
        raise NotImplementedError("_mapping is a required property for sorted mappings")

    @property
    @abstractmethod
    def _sequence(self: SortedMapping[KT_co, Any], /) -> SortedSequence[KT_co]:
        raise NotImplementedError("_sequence is a required property for sorted mappings")


class SortedMutableMapping(MutableMapping[KT_co, VT_co], SortedMapping[KT_co, VT_co], Generic[KT_co, VT_co]):

    __slots__ = ()

    def __delitem__(self: SortedMutableMapping[KT, Any], key: KT, /) -> None:
        del self._mapping[key]
        self._sequence.remove(key)

    def __setitem__(self: SortedMutableMapping[KT, VT], key: KT, value: VT, /) -> None:
        len_ = len(self)
        self._mapping[key] = value
        if len(self._mapping) != len_:
            self._sequence.append(key)

    def clear(self: SortedMutableMapping[Any, Any], /) -> None:
        self._mapping.clear()
        self._sequence.clear()

    @classmethod
    def from_iterable(cls: Type[SortedMutableMapping[KT_co, VT_co]], mapping: Union[Mapping[KT_co, VT_co], Iterable[tuple[KT_co, VT_co]]], /) -> SortedMutableMapping[KT_co, VT_co]:
        if isinstance(mapping, Mapping):
            return cls.from_sorted(sorted(mapping.items(), key=lambda x: x[0]))  # type: ignore
        elif isinstance(mapping, Iterable):
            return cls.from_sorted(sorted(mapping, key=lambda x: x[0]))  # type: ignore
        else:
            raise TypeError(f"from_iterable expects a mapping, got {mapping!r}")

    @abstractmethod
    @classmethod
    def from_sorted(cls: Type[SortedMutableMapping[KT_co, VT_co]], mapping: Union[Mapping[KT_co, VT_co], Iterable[tuple[KT_co, VT_co]]], /) -> SortedMutableMapping[KT_co, VT_co]:
        raise NotImplementedError("from_sorted is a required method for sorted mutable mappings")

    @property
    @abstractmethod
    def _mapping(self: SortedMutableMapping[KT_co, VT_co], /) -> MutableMapping[KT_co, VT_co]:
        raise NotImplementedError("_mapping is a required property for sorted mutable mappings")

    @property
    @abstractmethod
    def _sequence(self: SortedMutableMapping[KT_co, Any], /) -> SortedMutableSequence[KT_co]:
        raise NotImplementedError("_sequence is a required property for sorted mutable mappings")


if sys.version_info < (3, 9):
    collections.abc.MappingView.register(SortedMappingView)
    collections.abc.ItemsView.register(SortedItemsView)
    collections.abc.KeysView.register(SortedKeysView)
    collections.abc.ValuesView.register(SortedValuesView)
    collections.abc.Mapping.register(SortedMapping)
    collections.abc.MutableMapping.register(SortedMutableMapping)
