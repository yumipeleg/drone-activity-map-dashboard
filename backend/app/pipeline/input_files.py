"""Safe resolution and listing of pipeline input files.

Shared by the FastAPI route (pre-enqueue validation) and the pipeline runner
(worker-side resolution). No FastAPI or Celery imports — plain pathlib only.
"""

import re
from pathlib import Path

SUPPORTED_EXTENSIONS = {".json", ".csv"}

_DRIVE_PREFIX = re.compile(r"^[a-zA-Z]:")


class InputFileError(Exception):
    """Base class for input-file resolution errors."""


class UnsafeInputFilenameError(InputFileError):
    """The requested filename is not a single safe logical name."""


class UnsupportedInputExtensionError(InputFileError):
    """The filename extension is not .json or .csv."""


class InputFileNotFoundError(InputFileError):
    """The resolved path is missing or not a regular file."""


def list_available_input_files(input_dir: str | Path) -> list[str]:
    """Return sorted logical filenames for safe, contained .json/.csv regular files.

    Skips symlinks and any entry whose resolved path would fall outside
    ``input_dir`` — the same containment rules as ``resolve_input_file``.
    """
    directory = Path(input_dir)
    if not directory.is_dir():
        return []

    resolved_directory = directory.resolve()
    names: list[str] = []

    for entry in directory.iterdir():
        if entry.is_symlink() or not entry.is_file():
            continue

        name = entry.name
        if Path(name).suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            _validate_filename_string(name)
            resolved = entry.resolve()
            resolved.relative_to(resolved_directory)
        except (UnsafeInputFilenameError, ValueError):
            continue

        names.append(name)

    return sorted(names)


def resolve_input_file(input_dir: str | Path, filename: str) -> Path:
    """Resolve a logical filename to an absolute path inside ``input_dir``.

    Raises ``UnsafeInputFilenameError`` for path traversal or escape attempts,
    ``UnsupportedInputExtensionError`` for disallowed extensions, and
    ``InputFileNotFoundError`` when the file is missing or not a regular file.
    """
    candidate = _resolve_contained_path(input_dir, filename)

    if candidate.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise UnsupportedInputExtensionError(
            f"Unsupported input file extension '{candidate.suffix}' for '{filename}'"
        )

    if candidate.is_symlink() or not candidate.is_file():
        raise InputFileNotFoundError(f"Input file '{filename}' was not found")

    return candidate


def _validate_filename_string(filename: str) -> None:
    if not filename or filename in (".", ".."):
        raise UnsafeInputFilenameError(f"Unsafe input filename '{filename}'")

    if "/" in filename or "\\" in filename:
        raise UnsafeInputFilenameError(f"Unsafe input filename '{filename}'")

    if _DRIVE_PREFIX.match(filename):
        raise UnsafeInputFilenameError(f"Unsafe input filename '{filename}'")


def _resolve_contained_path(input_dir: str | Path, filename: str) -> Path:
    _validate_filename_string(filename)

    directory = Path(input_dir).resolve()
    candidate = (directory / filename).resolve()

    try:
        candidate.relative_to(directory)
    except ValueError as exc:
        raise UnsafeInputFilenameError(
            f"Input file '{filename}' resolves outside the configured input directory"
        ) from exc

    return candidate
