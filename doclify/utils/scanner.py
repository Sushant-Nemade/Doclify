import fnmatch
import os
from importlib.resources import files as resource_files
from pathlib import Path, PurePosixPath

from pathspec import GitIgnoreSpec

from doclify.utils.file_utils import is_link, project_path

MAX_FILES = 128
MAX_ENTRIES = 10_000
SOURCE_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".ipynb",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".yaml",
    ".yml",
    ".toml",
    ".json",
    ".html",
    ".css",
    ".sql",
    ".sh",
}
PRIVATE_PATTERNS = (
    ".env*",
    "*.pem",
    "*.key",
    "*credentials*",
    "*secret*",
    "id_rsa*",
    ".git",
    ".doclify",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    "doclify.yaml",
    "README.generated.md",
    "README-prev*",
)


def sensitive_path(value: str) -> bool:
    return any(
        fnmatch.fnmatch(part.lower(), pattern.lower())
        for part in PurePosixPath(value).parts
        for pattern in PRIVATE_PATTERNS
    )


def ignored_path(value: str, *, directory: bool = False, exclude=None) -> bool:
    root = Path.cwd()
    builtin = (
        resource_files("doclify.resources").joinpath("Python.gitignore").read_text(encoding="utf-8")
    )
    builtin_spec = GitIgnoreSpec.from_lines(builtin.splitlines() + list(exclude or []))
    result = builtin_spec.check_file(value + ("/" if directory else ""))
    ignored = result.include is True
    relative = PurePosixPath(value)
    parent_parts = relative.parts[:-1]
    bases = [PurePosixPath(".")] + [
        PurePosixPath(*parent_parts[:length]) for length in range(1, len(parent_parts) + 1)
    ]
    for base in bases:
        local = root.joinpath(*base.parts, ".gitignore")
        if is_link(local):
            raise ValueError("Linked ignore files are not supported")
        if not local.is_file():
            continue
        if local.stat().st_size > 64_000:
            raise ValueError("Ignore file exceeds size limit")
        spec = GitIgnoreSpec.from_lines(local.read_text(encoding="utf-8").splitlines())
        local_name = (
            relative.as_posix()
            if base == PurePosixPath(".")
            else relative.relative_to(base).as_posix()
        )
        result = spec.check_file(local_name + ("/" if directory else ""))
        if result.include is not None:
            ignored = result.include
    return ignored


def validate_source(value: str) -> Path:
    path = project_path(value, must_exist=True)
    parts = PurePosixPath(value).parts
    if (
        sensitive_path(value)
        or path.name.lower() == "readme.md"
        or path.suffix.lower() not in SOURCE_SUFFIXES
    ):
        raise ValueError("Sensitive, generated or unsupported source file rejected")
    for length in range(1, len(parts)):
        if ignored_path(PurePosixPath(*parts[:length]).as_posix(), directory=True):
            raise ValueError("Ignored source directory rejected")
    if ignored_path(value):
        raise ValueError("Ignored source file rejected")
    return path


def scan_repo(include=None, exclude=None) -> dict:
    selected = []
    entries = 0
    root = Path.cwd()
    for directory, directories, filenames in os.walk(root, followlinks=False):
        parent = Path(directory)
        allowed_directories = []
        for name in sorted(directories):
            child = parent / name
            relative = child.relative_to(root).as_posix()
            if (
                not is_link(child)
                and not sensitive_path(relative)
                and not ignored_path(relative, directory=True, exclude=exclude)
            ):
                allowed_directories.append(name)
        directories[:] = allowed_directories
        entries += len(filenames) + len(directories)
        if entries > MAX_ENTRIES:
            raise ValueError("Repository discovery limit exceeded; use a smaller project root")
        for name in sorted(filenames):
            path = parent / name
            relative = path.relative_to(root).as_posix()
            if (
                is_link(path)
                or sensitive_path(relative)
                or name.lower() == "readme.md"
                or path.suffix.lower() not in SOURCE_SUFFIXES
            ):
                continue
            if ignored_path(relative, exclude=exclude):
                continue
            if include and not any(
                relative == entry or relative.startswith(entry.rstrip("/") + "/")
                for entry in include
            ):
                continue
            selected.append(relative)
            if len(selected) > MAX_FILES:
                raise ValueError("Manifest exceeds 128 files; use a smaller project root")
    return {"project": root.name, "structure": sorted(selected)}
