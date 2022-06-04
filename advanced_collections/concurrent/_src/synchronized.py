from __future__ import annotations
import asyncio as _asyncio
import multiprocessing as _multiprocessing
import threading as _threading
from typing import Any, ClassVar, Optional, Type, TypeVar

Self = TypeVar("Self", bound="Synchronized")


class Synchronized:
    _cls_asyncio_lock: ClassVar[Optional[asyncio.Lock]]
    _cls_multiprocessing_lock: ClassVar[Optional[multiprocessing.Lock]]
    _cls_threading_lock: ClassVar[Optional[threading.Lock]]

    __slots__ = ()

    def __init_subclass__(
        cls: Type[Self],
        *,
        asyncio: bool = False,
        multiprocessing: bool = False,
        threading: bool = False,
        **kwargs: Any,
    ) -> None:
        asyncio = bool(asyncio)
        multiprocessing = bool(multiprocessing)
        threading = bool(threading)
        if not (asyncio or multiprocessing or threading):
            raise ValueError("use `class MyClass(Synchronized, asyncio=True, multiprocessing=True, threading=True):` to setup")
        cls._cls_asyncio_lock = _asyncio.Lock() if asyncio else None
        cls._cls_multiprocessing_lock = _multiprocessing.Lock() if asyncio else None
        cls._cls_threading_lock = _threading.Lock() if asyncio else None
