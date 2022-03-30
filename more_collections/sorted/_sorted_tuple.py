from __future__ import annotations
import sys
from typing import Any, Generic, Optional, Type, TypeVar, overload

if sys.version_info < (3, 9):
    from typing import AbstractSet, Callable, Iterable, Iterator, Tuple as tuple
else:
    from collections.abc import Set as AbstractSet, Callable, Iterable, Iterator

from ._abc_iterable import SortedIterable, SortedIterator
from ._abc_sequence import SortedMutableSequence, SortedSequence
from ._abc_key_iterable import SortedKeyIterable, SortedKeyIterator
from ._abc_key_sequence import SortedKeyMutableSequence, SortedKeySequence
from ._sorted_iterable import SortedUserIterator
from ._sorted_key_iterable import SortedKeyUserIterator

Self = TypeVar("Self", bound="SortedTuple")
T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


class SortedTuple(SortedSequence[T], Generic[T]):
    _sequence: tuple[T, ...]

    __slots__ = ("_sequence",)

    def __init__(self: SortedTuple[T], iterable: Optional[Iterable[T]] = None, /) -> None:
        if iterable is None:
            self._sequence = ()
        elif isinstance(iterable, SortedIterable):
            self._sequence = (*iterable,)
        elif isinstance(iterable, Iterable):
            self._sequence = (*sorted(iterable),)
        else:
            raise TypeError(f"{type(self).__name__} expected iterable or None, got {iterable!r}")

    @overload
    def __getitem__(self: SortedTuple[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: SortedTuple[T], index: slice, /) -> SortedTuple[T]:
        ...

    def __getitem__(self, index, /):
        if not isinstance(index, slice):
            return self._sequence[index]
        elif index.step is None or index.step > 0:
            return type(self).from_sorted(self._sequence[index])
        else:
            return type(self).from_iterable(self._sequence[index])

    def __iter__(self: SortedTuple[T], /) -> SortedIterator[T]:
        return SortedUserIterator(self._sequence)

    def __len__(self: SortedTuple[Any], /) -> int:
        return len(self._sequence)

    def __reversed__(self: SortedTuple[T], /) -> Iterator[T]:
        return reversed(self._sequence)

    @classmethod
    def from_iterable(cls: Type[SortedTuple[T]], iterable: Iterable[T], /) -> SortedTuple[T]:
        if isinstance(iterable, Iterable):
            return cls(iterable)
        else:
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")

    @classmethod
    def from_sorted(cls: Type[SortedTuple[T]], iterable: Iterable[T], /) -> SortedTuple[T]:
        if isinstance(iterable, Iterable):
            self = cls()
            self._sequence = (*iterable,)
            return self
        else:
            raise TypeError(f"from_sorted expects an iterable, got {iterable!r}")


class SortedKeyTuple(SortedKeySequence[T], Generic[T]):
    _key: Callable[[T], Any]
    _sequence: tuple[T, ...]

    __slots__ = ("_sequence",)

    def __init__(self: SortedKeyTuple[T], iterable: Optional[Iterable[T]] = None, /, *, key: Callable[[T], Any]) -> None:
        if not callable(key):
            raise TypeError(f"{type(self).__name__} expected a callable key, got {key!r}")
        if iterable is None:
            self._sequence = ()
        elif isinstance(iterable, SortedKeyIterable) and iterable.key == key:
            self._sequence = (*iterable,)
        elif isinstance(iterable, Iterable):
            self._sequence = (*sorted(iterable, key=key),)  # type: ignore
        else:
            raise TypeError(f"{type(self).__name__} expected iterable or None, got {iterable!r}")
        self._key = key  # type: ignore

    def __copy__(self: Self, /) -> Self:
        return self

    @overload
    def __getitem__(self: SortedKeyTuple[T], index: int, /) -> T:
        ...

    @overload
    def __getitem__(self: SortedKeyTuple[T], index: slice, /) -> SortedKeyTuple[T]:
        ...

    def __getitem__(self, index, /):
        if not isinstance(index, slice):
            return self._sequence[index]
        elif index.step is None or index.step > 0:
            return type(self).from_sorted(self._sequence[index], self.key)
        else:
            return type(self).from_iterable(self._sequence[index], self.key)

    def __iter__(self: SortedKeyTuple[T], /) -> SortedKeyIterator[T]:
        return SortedKeyUserIterator(self._sequence)

    def __len__(self: SortedKeyTuple[Any], /) -> int:
        return len(self._sequence)

    def __reversed__(self: SortedKeyTuple[T], /) -> Iterator[T]:
        return reversed(self._sequence)

    @classmethod
    def from_iterable(cls: Type[SortedKeyTuple[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeyTuple[T]:
        if not isinstance(iterable, Iterable):
            raise TypeError(f"from_iterable expects an iterable, got {iterable!r}")
        elif not callable(key):
            raise TypeError(f"from_iterable expects a callable key, got {key!r}")
        else:
            return cls(iterable, key=key)

    @classmethod
    def from_sorted(cls: Type[SortedKeyTuple[T]], iterable: Iterable[T], /, key: Callable[[T], Any]) -> SortedKeyTuple[T]:
        if isinstance(iterable, Iterable):
            self = cls(key=key)
            self._sequence = iterable if isinstance(iterable, tuple) else (*iterable,)
            return self
        else:
            raise TypeError(f"from_sorted expects an iterable, got {iterable!r}")

    @property
    def key(self: SortedKeyTuple[T], /) -> Callable[[T], Any]:
        return self._key
