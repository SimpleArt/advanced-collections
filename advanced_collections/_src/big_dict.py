import pickle
from bisect import bisect
from collections import OrderedDict
from collections.abc import Hashable, Iterable, Iterator, MutableMapping
from heapq import nlargest, nsmallest
from itertools import chain, islice
from pathlib import Path
from types import TracebackType
from typing import Any, Generic, Optional, SupportsIndex, Type, TypeVar, Union, overload

__all__ = ["BigDict"]

ET = TypeVar("ET", bound=BaseException)
KT = TypeVar("KT", bound=Hashable)
VT = TypeVar("VT")

Self = TypeVar("Self", bound="BigDict")

CHUNKSIZE = 4096

def ensure_file(path: Path, default: VT) -> VT:
    if not path.exists():
        with open(path, mode="wb") as file:
            pickle.dump(default, file)
        return default
    with open(path, mode="rb") as file:
        return pickle.load(file)


class BigDict(MutableMapping[KT, VT], Generic[KT, VT]):
    _cache: OrderedDict[str, dict[KT, VT]]
    _filenames: list[str]
    _len: int
    _lens: list[int]
    _mins: list[tuple[int, KT]]
    _path: Path

    __slots__ = {
        "_cache":
            "A cache containing the 4 most recently accessed segments.",
        "_filenames":
            "The file names for each segment.",
        "_len":
            "The total length of the dict.",
        "_lens":
            "The length of each segment.",
        "_mins":
            "The minimum hash-key pair of each segment.",
        "_path":
            "The folder containing all of the files.",
    }

    def __init__(self: Self, path: Union[Path, str], /) -> None:
        self._path = Path(path)
        self._path.mkdir(exist_ok=True)
        self._cache = OrderedDict()
        self._filenames = ensure_file(self._path / "filenames.txt", [])
        self._lens = ensure_file(self._path / "lens.txt", [])
        self._mins = ensure_file(self._path / "mins.txt", [])
        assert len(self._filenames) == len(self._lens) == len(self._mins), "broken database files"
        self._len = sum(self._lens)
        ensure_file(self._path / "counter.txt", 0)

    def __del__(self: Self, /) -> None:
        with open(self._path / "filenames.txt", mode="wb") as file:
            pickle.dump(self._filenames, file)
        with open(self._path / "lens.txt", mode="wb") as file:
            pickle.dump(self._lens, file)
        for filename, segment in self._cache.items():
            self._commit_chunk(filename, segment)

    def __delitem__(self: Self, key: KT, /) -> None:
        index = bisect(self._mins, (hash(key), key))
        if index == 0:
            raise KeyError(key)
        index -= 1
        MISSING = object()
        result = self._cache_chunk(index).pop(key, MISSING)
        if result is MISSING:
            raise KeyError(key)
        self._lens[index] -= 1
        self._len -= 1
        if key == self._mins[index][1]:
            self._mins[index] = min(
                (hash(k), k)
                for k in self._cache_chunk(index)
            )
        self._balance(index)

    def __enter__(self: Self, /) -> Self:
        return self

    def __exit__(
        self: Self,
        exc_type: Optional[Type[ET]],
        exc_val: Optional[ET],
        exc_traceback: Optional[TracebackType],
        /,
    ) -> None:
        with open(self._path / "filenames.txt", mode="wb") as file:
            pickle.dump(self._filenames, file)
        with open(self._path / "lens.txt", mode="wb") as file:
            pickle.dump(self._lens, file)
        for filename, segment in self._cache.items():
            self._commit_chunk(filename, segment)

    def __getitem__(self: Self, key: KT, /) -> VT:
        index = bisect(self._mins, (hash(key), key))
        if index == 0:
            raise KeyError(key)
        index -= 1
        MISSING = object()
        result = self._cache_chunk(index).get(key, MISSING)
        if result is MISSING:
            raise KeyError(key)
        return result

    def __iter__(self: Self, /) -> Iterator[KT]:
        return chain.from_iterable(
            self._cache_chunk(i)
            for i, _ in enumerate(self._lens)
        )

    def __len__(self: Self, /) -> int:
        return self._len

    def __reversed__(self: Self, /) -> Iterator[KT]:
        return chain.from_iterable(
            reversed(self._cache_chunk(~i))
            for i, _ in enumerate(self._lens)
        )

    def __setitem__(self: Self, key: KT, value: VT, /) -> None:
        hkey = hash(key)
        index = bisect(self._mins, (hkey, key))
        if index > 0:
            index -= 1
        if self._len == 0:
            self._filenames.append(self._get_filename())
            self._cache[self._filenames[0]] = {}
            self._lens.append(0)
            self._mins.append((hkey, key))
        chunk = self._cache_chunk(index)
        len_ = len(chunk)
        chunk[key] = value
        self._lens[index] += len(chunk) - len_
        self._len += len(chunk) - len_
        if (hkey, key) < self._mins[index]:
            self._mins[index] = (hkey, key)

    def __str__(self: Self, /) -> str:
        return f"{type(self).__name__}({self._path})"

    def _balance(self: Self, index: int, /) -> None:
        lens = self._lens
        if len(lens) == 0:
            return
        elif len(lens) != 1:
            pass
        elif lens[0] > 2 * CHUNKSIZE:
            chunk = self._cache_chunk(0)
            keys = [(hash(key), key) for key in chunk]
            keys.sort()
            self._filenames.append(self._get_filename())
            self._cache[self._filenames[-1]] = {key: chunk.pop(key) for _, key in keys[:len(keys) // 2]}
            self._lens[0] = len(chunk)
            self._lens.append(len(self._cache_chunk(-1)))
            self._mins[:] = [keys[0], keys[len(chunk)]]
            return
        else:
            return
        index = range(len(lens))[index]
        if index == 0:
            if lens[0] + lens[1] < CHUNKSIZE:
                self._len += lens[1]
                self._lens[0] += lens[1]
                self._cache_chunk(0).update(self._pop_chunk(1))
            elif lens[0] + lens[1] > 4 * CHUNKSIZE:
                chunk = {
                    **self._cache_chunk(0),
                    **self._cache_chunk(1),
                }
                keys = [(hash(key), key) for key in chunk]
                keys.sort()
                self._cache_chunk(0).clear()
                self._cache_chunk(0).update({
                    key: chunk[key]
                    for _, key in keys[:len(keys) // 3]
                })
                self._cache_chunk(1).clear()
                self._cache_chunk(1).update({
                    key: chunk[key]
                    for _, key in keys[len(keys) // 3 : 2 * len(keys) // 3]
                })
                self._filenames.insert(2, self._get_filename())
                self._free_cache()
                self._cache[self._filenames[2]] = {
                    key: chunk[key]
                    for _, key in keys[2 * len(keys) // 3:]
                }
                lens[:2] = [
                    len(keys) // 3,
                    2 * len(keys) // 3 - len(keys) // 3,
                    len(keys) - 2 * len(keys) // 3,
                ]
                self._mins[1:2] = [
                    keys[len(keys) // 3],
                    keys[2 * len(keys) // 3],
                ]
            elif (
                CHUNKSIZE // 2 < lens[0] < CHUNKSIZE * 2
                and 3 * CHUNKSIZE // 2 < lens[0] + lens[1] < 3 * CHUNKSIZE
            ):
                pass
            elif lens[0] > lens[1]:
                diff = lens[0] - lens[1]
                chunk = self._cache_chunk(0)
                keys = nlargest(
                    diff // 2,
                    (
                        (hash(key), key)
                        for key in chunk
                    ),
                )
                self._cache_chunk(1).update({
                    key: chunk.pop(key) for _, key in keys
                })
                self._mins[1] = keys[-1]
                lens[0] -= diff // 2
                lens[1] += diff // 2
            else:
                diff = lens[1] - lens[0]
                chunk = self._cache_chunk(1)
                keys = nsmallest(
                    diff // 2 + 1,
                    (
                        (hash(key), key)
                        for key in chunk
                    ),
                )
                self._mins[1] = keys.pop()
                self._cache_chunk(0).update({
                    key: chunk.pop(key)
                    for _, key in keys
                })
                lens[0] += diff // 2
                lens[1] -= diff // 2
        elif index + 1 == len(lens):
            if lens[-1] + lens[-2] < CHUNKSIZE:
                self._len += lens[-1]
                self._cache_chunk(-2).update(self._pop_chunk(-1))
            elif lens[-1] + lens[-2] > 4 * CHUNKSIZE:
                chunk = {
                    **self._cache_chunk(-2),
                    **self._cache_chunk(-1),
                }
                keys = [(hash(key), key) for key in chunk]
                keys.sort()
                self._cache_chunk(-2).clear()
                self._cache_chunk(-2).update({
                    key: chunk[key]
                    for _, key in keys[:len(keys) // 3]
                })
                self._cache_chunk(-1).clear()
                self._cache_chunk(-1).update({
                    key: chunk[key]
                    for _, key in keys[len(keys) // 3 : 2 * len(keys) // 3]
                })
                self._filenames.append(self._get_filename())
                self._free_cache()
                self._cache[self._filenames[-1]] = {
                    key: chunk[key]
                    for _, key in keys[2 * len(keys) // 3:]
                }
                lens[-2:] = [
                    len(keys) // 3,
                    2 * len(keys) // 3 - len(keys) // 3,
                    len(keys) - 2 * len(keys) // 3,
                ]
                self._mins[-1:] = [
                    keys[len(keys) // 3],
                    keys[2 * len(keys) // 3],
                ]
            elif (
                CHUNKSIZE // 2 < lens[-1] < CHUNKSIZE * 2
                and 3 * CHUNKSIZE // 2 < lens[-1] + lens[-2] < 3 * CHUNKSIZE
            ):
                pass
            elif lens[-2] > lens[-1]:
                diff = lens[-2] - lens[-1]
                chunk = self._cache_chunk(-2)
                keys = nlargest(
                    diff // 2,
                    (
                        (hash(key), key)
                        for key in chunk
                    ),
                )
                self._cache_chunk(-1).update({key: chunk.pop(key) for _, key in keys})
                self._mins[-1] = keys[-1]
                lens[-2] -= diff // 2
                lens[-1] += diff // 2
            else:
                diff = lens[-1] - lens[-2]
                chunk = self._cache_chunk(-1)
                keys = nsmallest(
                    diff // 2 + 1,
                    (
                        (hash(key), key)
                        for key in chunk
                    ),
                )
                self._mins[-1] = keys.pop()
                self._cache_chunk(-2).update({key: chunk.pop(key) for _, key in keys})
                lens[-2] += diff // 2
                lens[-1] -= diff // 2
        else:
            if lens[index - 1] + lens[index] + lens[index + 1] < 3 * CHUNKSIZE // 2:
                chunk = {
                    **self._cache_chunk(index - 1),
                    **self._cache_chunk(index),
                    **self._pop_chunk(index + 1),
                }
                keys = [(hash(key), key) for key in chunk]
                keys.sort()
                self._cache_chunk(index - 1).clear()
                self._cache_chunk(index - 1).update({
                    key: chunk[key]
                    for _, key in keys[:len(keys) // 2]
                })
                self._cache_chunk(index).clear()
                self._cache_chunk(index).update({
                    key: chunk[key]
                    for _, key in keys[len(keys) // 2:]
                })
                lens[index - 1 : index + 1] = [
                    len(keys) // 2,
                    (len(keys) + 1) // 2,
                ]
                self._mins[index] = keys[len(key) // 2]
            elif lens[index - 1] + lens[index] + lens[index + 1] > 6 * CHUNKSIZE:
                chunk = {
                    **self._cache_chunk(index - 1),
                    **self._cache_chunk(index),
                    **self._cache_chunk(index + 1),
                }
                keys = [(hash(key), key) for key in chunk]
                keys.sort()
                self._cache_chunk(index - 1).clear()
                self._cache_chunk(index - 1).update({
                    key: chunk[key]
                    for _, key in keys[:len(keys) // 4]
                })
                self._cache_chunk(index).clear()
                self._cache_chunk(index).update({
                    key: chunk[key]
                    for _, key in keys[len(keys) // 4 : len(keys) // 2]
                })
                self._cache_chunk(index + 1).clear()
                self._cache_chunk(index + 1).update({
                    key: chunk[key]
                    for _, key in keys[len(keys) // 2 : 3 * len(keys) // 4]
                })
                self._filenames.insert(index + 2, self._get_filename())
                self._free_cache()
                self._cache[self._filenames[index + 2]] = {
                    key: chunk[key]
                    for _, key in keys[3 * len(keys) // 4:]
                }
                self._lens[index - 1 : index + 2] = [
                    len(keys) // 4,
                    len(keys) // 2 - len(keys) // 4,
                    3 * len(keys) // 4 - len(keys) // 2,
                    len(keys) - 3 * len(keys) // 4,
                ]
                self._mins[index : index + 2] = [
                    keys[len(keys) // 4],
                    keys[len(keys) // 2],
                    keys[3 * len(keys) // 4],
                ]
            elif not all(
                CHUNKSIZE // 2 < 2 * L // 3 < CHUNKSIZE
                for L in lens[index - 1 : index + 2]
            ):
                chunk = {
                    **self._cache_chunk(index - 1),
                    **self._cache_chunk(index),
                    **self._cache_chunk(index + 1),
                }
                keys = [(hash(key), key) for key in chunk]
                keys.sort()
                self._cache_chunk(index - 1).clear()
                self._cache_chunk(index - 1).update({
                    key: chunk[key]
                    for _, key in keys[:len(keys) // 3]
                })
                self._cache_chunk(index).clear()
                self._cache_chunk(index).update({
                    key: chunk[key]
                    for _, key in keys[len(keys) // 3 : 2 * len(keys) // 3]
                })
                self._cache_chunk(index + 1).clear()
                self._cache_chunk(index + 1).update({
                    key: chunk[key]
                    for _, key in keys[2 * len(keys) // 3:]
                })
                self._lens[index - 1 : index + 2] = [
                    len(keys) // 3,
                    2 * len(keys) // 3 - len(keys) // 3,
                    len(keys) - 2 * len(keys) // 3,
                ]
                self._mins[index : index + 2] = [
                    keys[len(keys) // 3],
                    keys[2 * len(keys) // 3],
                ]

    def _cache_chunk(self: Self, index: int, /) -> dict[KT, VT]:
        filename = self._filenames[index]
        if filename in self._cache:
            self._cache.move_to_end(filename)
        else:
            self._free_cache()
            with open(self._path / filename, mode="rb") as file:
                self._cache[filename] = pickle.load(file)
        return self._cache[filename]

    def _commit_chunk(self: Self, filename: str, segment: dict[KT, VT], /) -> None:
        with open(self._path / filename, mode="wb") as file:
            pickle.dump(segment, file)

    def _del_chunk(self: Self, index: int, /) -> None:
        index = range(len(self._filenames))[index]
        filename = self._filenames.pop(index)
        (self._path / filename).unlink()
        self._len -= self._lens.pop(index)
        self._cache.pop(filename, None)
        del self._mins[index]

    def _free_cache(self: Self, /) -> None:
        if len(self._cache) == 4:
            self._commit_chunk(*self._cache.popitem(last=False))

    def _get_filename(self: Self, /) -> str:
        path = self._path / "counter.txt"
        with open(path, mode="rb") as file:
            uid = pickle.load(file)
        with open(path, mode="wb") as file:
            pickle.dump(uid + 1, file)
        with open(self._path / f"{uid}.txt", mode="wb") as file:
            pickle.dump({}, file)
        return f"{uid}.txt"

    def _pop_chunk(self: Self, index: int, /) -> dict[KT, VT]:
        filename = self._filenames[index]
        if filename in self._cache:
            segment = self._cache.pop(filename)
        else:
            with open(self._path / filename, mode="rb") as file:
                segment = pickle.load(file)
        self._del_chunk(index)
        return segment

    def clear(self: Self, /) -> None:
        path = self._path
        for filename in self._filenames:
            (path / filename).unlink()
        with open(path / "counter.txt", mode="wb") as file:
            pickle.dump(0, file)
        for filename in ("filenames.txt", "lens.txt", "mins.txt"):
            with open(path / filename, mode="wb") as file:
                pickle.dump([], file)
        self._cache.clear()
        self._filenames.clear()
        self._len = 0
        self._lens.clear()
        self._mins.clear()
