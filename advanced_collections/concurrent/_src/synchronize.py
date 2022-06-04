import asyncio
import multiprocessing
import sys
import threading
from typing import Any, ClassVar, Type, TypeVar

if sys.version_info < (3, 9):
    from typing import Callable
else:
    from collections.abc import Callable

FT = TypeVar("FT", bound=Callable)
Self = TypeVar("SynchronizedDescriptor")
