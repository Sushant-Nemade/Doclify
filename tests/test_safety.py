import json
import os

import pytest

from doclify.utils.extract import read_source
from doclify.utils.file_utils import atomic_write, load_cache, pipeline_lock, project_path
from doclify.utils.scanner import scan_repo


@pytest.fixture(autouse=True)
def project_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def test_discovery_respects_nested_ignores_and_private_paths(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/.gitignore").write_text("hidden.py\n", encoding="utf-8")
    for name in ["src/hidden.py", "src/main.py", ".env", "credentials.json", "README.md"]:
        (tmp_path / name).write_text("safe\n", encoding="utf-8")
    assert scan_repo()["structure"] == ["src/main.py"]


@pytest.mark.parametrize(
    "path", ["../outside.py", "/outside.py", "C:/outside.py", "src/../main.py", "src\\main.py"]
)
def test_unsafe_paths_are_rejected(path):
    with pytest.raises(ValueError):
        project_path(path)


def test_corrupt_cache_is_preserved(tmp_path):
    atomic_write(".doclify/cache.json", "{broken")
    with pytest.raises(ValueError, match="corrupt"):
        load_cache()
    assert (tmp_path / ".doclify/cache.json").read_text() == "{broken"


def test_failed_atomic_replace_keeps_old_file(tmp_path, monkeypatch):
    atomic_write("state.json", "old")

    def fail_replace(*args):
        raise OSError("injected failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError):
        atomic_write("state.json", "new")
    assert (tmp_path / "state.json").read_text() == "old"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["state.json"]


def test_lock_prevents_concurrent_writer():
    with pipeline_lock():
        with pytest.raises(ValueError, match="Another operation"):
            with pipeline_lock():
                pytest.fail("Second writer entered")


def test_linked_sources_are_rejected(tmp_path):
    target = tmp_path / "actual.py"
    target.write_text("print('safe')", encoding="utf-8")
    link = tmp_path / "link.py"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Creating symlinks requires permission on this host")
    with pytest.raises(ValueError, match="links"):
        read_source("link.py")


@pytest.mark.parametrize(
    "content",
    [b"\x00binary", b"\xff", b"a" * 256_001, b"gsk_" + b"X" * 24],
    ids=["binary", "non_utf8", "oversized", "credential"],
)
def test_unsafe_content_is_rejected(tmp_path, content):
    (tmp_path / "main.py").write_bytes(content)
    with pytest.raises(ValueError):
        read_source("main.py")


def test_notebook_outputs_are_not_processed(tmp_path):
    document = {
        "cells": [
            {
                "cell_type": "code",
                "source": ["print('safe')"],
                "outputs": [{"text": "private output"}],
            }
        ]
    }
    (tmp_path / "demo.ipynb").write_text(json.dumps(document), encoding="utf-8")
    content, _ = read_source("demo.ipynb")
    assert content == "print('safe')"
