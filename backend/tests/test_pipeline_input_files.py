"""Unit tests for app/pipeline/input_files.py."""

import os
from pathlib import Path

import pytest

from app.pipeline.input_files import (
    InputFileNotFoundError,
    UnsupportedInputExtensionError,
    UnsafeInputFilenameError,
    list_available_input_files,
    resolve_input_file,
)


def _write_file(directory: Path, name: str, content: str = "x") -> Path:
    path = directory / name
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "unsafe_name",
    [
        "../secrets.json",
        "..\\secrets.json",
        "/etc/passwd",
        "C:\\Windows\\x.json",
        "\\\\server\\share\\x.json",
        "C:foo.json",
        "sub/dir.json",
        ".",
        "..",
        "",
    ],
)
def test_resolve_input_file_rejects_unsafe_filenames(
    tmp_path: Path, unsafe_name: str
) -> None:
    _write_file(tmp_path, "sample.json", "[]")

    with pytest.raises(UnsafeInputFilenameError):
        resolve_input_file(tmp_path, unsafe_name)


def test_resolve_input_file_accepts_valid_filename(tmp_path: Path) -> None:
    _write_file(tmp_path, "sample.json", "[]")

    resolved = resolve_input_file(tmp_path, "sample.json")

    assert resolved.is_file()
    assert resolved.name == "sample.json"


def test_resolve_input_file_rejects_unsupported_extension(tmp_path: Path) -> None:
    _write_file(tmp_path, "notes.txt")

    with pytest.raises(UnsupportedInputExtensionError):
        resolve_input_file(tmp_path, "notes.txt")


def test_resolve_input_file_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(InputFileNotFoundError):
        resolve_input_file(tmp_path, "missing.json")


def test_resolve_input_file_rejects_directory(tmp_path: Path) -> None:
    (tmp_path / "folder.json").mkdir()

    with pytest.raises(InputFileNotFoundError):
        resolve_input_file(tmp_path, "folder.json")


def test_resolve_input_file_rejects_symlink(tmp_path: Path) -> None:
    target = _write_file(tmp_path, "real.json", "[]")
    link = tmp_path / "linked.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation not supported in this environment")

    with pytest.raises(InputFileNotFoundError):
        resolve_input_file(tmp_path, "linked.json")


def test_list_available_input_files_returns_sorted_json_and_csv(tmp_path: Path) -> None:
    _write_file(tmp_path, "b.csv", "h\n")
    _write_file(tmp_path, "a.json", "[]")
    _write_file(tmp_path, "ignore.txt")

    assert list_available_input_files(tmp_path) == ["a.json", "b.csv"]


def test_list_available_input_files_returns_empty_when_directory_missing(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "does-not-exist"
    assert list_available_input_files(missing) == []


def test_list_available_input_files_skips_symlinks(tmp_path: Path) -> None:
    _write_file(tmp_path, "real.json", "[]")
    outside = tmp_path.parent / "outside.json"
    outside.write_text("[]", encoding="utf-8")
    try:
        (tmp_path / "linked.json").symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation not supported in this environment")

    assert list_available_input_files(tmp_path) == ["real.json"]


@pytest.mark.skipif(os.name != "posix", reason="POSIX symlink containment test")
def test_list_available_input_files_skips_symlink_that_escapes_directory(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / "outside.json"
    outside.write_text("[]", encoding="utf-8")
    (tmp_path / "escape.json").symlink_to(outside)
    _write_file(tmp_path, "safe.json", "[]")

    assert list_available_input_files(tmp_path) == ["safe.json"]


def test_resolve_input_file_rejects_resolved_path_outside_directory(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / "outside.json"
    outside.write_text("[]", encoding="utf-8")
    link_name = "escape.json"
    try:
        (tmp_path / link_name).symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation not supported in this environment")

    with pytest.raises(InputFileNotFoundError):
        resolve_input_file(tmp_path, link_name)
