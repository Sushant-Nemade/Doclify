import json
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

CACHE_DIR = Path(".doclify")
CACHE_FILE = CACHE_DIR / "cache.json"
MAX_CACHE_BYTES = 2_000_000


def is_link(path: Path) -> bool:
    junction_check = getattr(path, "is_junction", lambda: False)
    if path.is_symlink() or junction_check():
        return True
    if path.exists():
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    return False


def project_path(value: str, *, must_exist: bool = False) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or ":" in value
        or any(ord(character) < 32 or character in "`<>|?*" for character in value)
    ):
        raise ValueError("Paths must be nonempty project-relative POSIX paths")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts or str(relative) != value:
        raise ValueError("Noncanonical or out-of-project path rejected")
    root = Path.cwd().resolve()
    target = root
    for part in relative.parts:
        target = target / part
        if is_link(target):
            raise ValueError("Symbolic links, junctions and reparse points are excluded")
    if not target.resolve().is_relative_to(root):
        raise ValueError("Out-of-project path rejected")
    if must_exist and not target.is_file():
        raise ValueError("A selected project file is missing or is not a regular file")
    return target


def atomic_write(value: str, content: str) -> None:
    target = project_path(value)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".doclify-", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        project_path(value)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def pipeline_lock():
    directory = project_path(".doclify")
    directory.mkdir(mode=0o700, exist_ok=True)
    lock = project_path(".doclify/pipeline.lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError(
            "Another operation holds .doclify/pipeline.lock; inspect stale locks manually"
        ) from error
    try:
        os.close(descriptor)
        yield
    finally:
        lock.unlink()


def load_cache() -> dict:
    path = project_path(CACHE_FILE.as_posix())
    if not path.exists():
        return {"version": 2, "files": {}}
    if path.stat().st_size > MAX_CACHE_BYTES:
        raise ValueError("Cache exceeds the size limit")
    try:
        cache = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as error:
        raise ValueError(
            "Cache is corrupt; preserve it and restore or remove it explicitly"
        ) from error
    if (
        not isinstance(cache, dict)
        or cache.get("version") != 2
        or not isinstance(cache.get("files"), dict)
    ):
        raise ValueError("Unsupported cache format; preserve old cache before removing it")
    for name, record in cache["files"].items():
        project_path(name)
        if not isinstance(record, dict) or set(record) != {"hash", "context", "summary"}:
            raise ValueError("Invalid cache record")
        if (
            not all(isinstance(value, str) for value in record.values())
            or not record["summary"].strip()
        ):
            raise ValueError("Invalid cache summary")
    return cache


def clean_cache(cache: dict, valid_files: list[str]) -> dict:
    return {
        "version": 2,
        "files": {name: record for name, record in cache["files"].items() if name in valid_files},
    }


def save_cache(cache: dict) -> None:
    content = json.dumps(cache, indent=2, ensure_ascii=False) + "\n"
    if len(content.encode("utf-8")) > MAX_CACHE_BYTES:
        raise ValueError("Cache exceeds the size limit")
    atomic_write(CACHE_FILE.as_posix(), content)
