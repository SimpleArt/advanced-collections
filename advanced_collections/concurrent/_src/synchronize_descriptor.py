import asyncio
import multiprocessing
import sys
import threading
from types import FunctionType, MethodType
from typing import Any, ClassVar, Protocol, Type, TypeVar, Union

if sys.version_info < (3, 9):
    from typing import Callable
else:
    from collections.abc import Callable

GT = TypeVar("GT")
ST = TypeVar("ST")
T = TypeVar("T")
Self = TypeVar("Self", bound="SynchronizedDescriptor")


class DataDescriptor(Protocol[GT, ST, T]):

    def __get__(self, instance: T, owner: Optional[Type[T]] = None) -> GT:
        ...

    def __set__(self, instance: T, value: ST) -> None:
        ...

    def __delete__(self, instance: T) -> None:
        ...


def locked_function(self, func, *args, **kwargs):
    if 


def synchronized(func: DataDescriptor[GT, KT, T], /) -> DataDescriptor[GT, KT, T]:


    class SynchronizedDescriptor(DataDescriptor[GT, KT, T]):

        __slots__ = ()

        def __get__(self: Self, instance: T, owner: Optional[Type[T]] = None) -> GT:
            if isinstance(func, FunctionType):
                return MethodType(locked_func, self)


    SynchronizedDescriptor.__doc__ = func.__doc__
    return SynchronizedDescriptor
