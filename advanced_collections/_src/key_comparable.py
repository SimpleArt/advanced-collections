from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from .comparable import SupportsRichHashableComparison

__all__ = ["KeyComparable"]

Self = TypeVar("Self", bound="KeyComparable")
T_co = TypeVar("T_co", bound=SupportsRichHashableComparison, covariant=True)


class KeyComparable(SupportsRichHashableComparison, Generic[T_co]):

    __slots__ = ()

    def __hash__(self: Self, /) -> int:
        return hash(type(self).__key__(self))

    @abstractmethod
    def __key__(self: Self, /) -> T_co:
        raise NotImplementedError("__key__ is a required method for key comparable classes")

    def __eq__(self: Self, other: Any, /) -> bool:
        key = type(self).__key__(self)
        result = None
        if hasattr(type(other), "__eq__"):
            result = type(other).__eq__(other, key)
            if result is not NotImplemented:
                return result
        if hasattr(type(key), "__eq__"):
            result = type(key).__eq__(key, other)
            if result is not NotImplemented:
                return result
        if result is None:
            return key is other
        else:
            return NotImplemented

    def __ge__(self: Self, other: Any, /) -> bool:
        key = type(self).__key__(self)
        if hasattr(type(other), "__le__"):
            result = type(other).__le__(other, key)
            if result is not NotImplemented:
                return result
        if hasattr(type(key), "__ge__"):
            result = type(key).__ge__(key, other)
            if result is not NotImplemented:
                return result
        return NotImplemented

    def __gt__(self: Self, other: Any, /) -> bool:
        key = type(self).__key__(self)
        if hasattr(type(other), "__lt__"):
            result = type(other).__lt__(other, key)
            if result is not NotImplemented:
                return result
        if hasattr(type(key), "__gt__"):
            result = type(key).__gt__(key, other)
            if result is not NotImplemented:
                return result
        return NotImplemented

    def __le__(self: Self, other: Any, /) -> bool:
        key = type(self).__key__(self)
        if hasattr(type(other), "__ge__"):
            result = type(other).__ge__(other, key)
            if result is not NotImplemented:
                return result
        if hasattr(type(key), "__le__"):
            result = type(key).__le__(key, other)
            if result is not NotImplemented:
                return result
        return NotImplemented

    def __lt__(self: Self, other: Any, /) -> bool:
        key = type(self).__key__(self)
        if hasattr(type(other), "__gt__"):
            result = type(other).__gt__(other, key)
            if result is not NotImplemented:
                return result
        if hasattr(type(key), "__lt__"):
            result = type(key).__lt__(key, other)
            if result is not NotImplemented:
                return result
        return NotImplemented

    def __ne__(self: Self, other: Any, /) -> bool:
        key = type(self).__key__(self)
        result = None
        if hasattr(type(other), "__ne__"):
            result = type(other).__ne__(other, key)
            if result is not NotImplemented:
                return result
        elif hasattr(type(other), "__eq__"):
            result = type(other).__eq__(other, key)
            if result is not NotImplemented:
                return not result
        if hasattr(type(key), "__ne__"):
            result = type(key).__ne__(key, other)
            if result is not NotImplemented:
                return result
        elif hasattr(type(key), "__eq__"):
            result = type(key).__eq__(key, other)
            if result is not NotImplemented:
                return not result
        if result is None:
            return key is not other
        else:
            return NotImplemented
