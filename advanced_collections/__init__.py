"""
Extends the builtin collections with advanced collections, including
database sized lists, better queues, and more. Written in Python 3,
this library also includes annotations/type-hints to make usage with an
IDE easier and abstract base classes for easily creating custom
implementations.
"""
from . import abc
from ._src.big_dict import BigDict
from ._src.big_list import BigList

__version__ = "1.0.0"
