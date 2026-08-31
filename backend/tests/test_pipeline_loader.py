"""Unit tests for app/pipeline/loader.py."""

import json
from pathlib import Path

import pytest

from app.pipeline.loader import InputLoadError, load_raw_records


def test_load_json_records_valid_array(tmp_path: Path) -> None:
    records = [{"drone_id": "DRONE-001", "value": 1}]
    path = tmp_path / "input.json"
    path.write_text(json.dumps(records), encoding="utf-8")

    assert load_raw_records(path) == records


def test_load_json_records_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(InputLoadError, match="Could not read"):
        load_raw_records(tmp_path / "missing.json")


def test_load_json_records_invalid_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(InputLoadError, match="not valid JSON"):
        load_raw_records(path)


def test_load_json_records_non_array_raises(tmp_path: Path) -> None:
    path = tmp_path / "object.json"
    path.write_text('{"drone_id": "x"}', encoding="utf-8")

    with pytest.raises(InputLoadError, match="JSON array"):
        load_raw_records(path)


def test_load_csv_records_valid_rows(tmp_path: Path) -> None:
    path = tmp_path / "input.csv"
    path.write_text(
        "drone_id,drone_type\nDRONE-001,Quadcopter\n",
        encoding="utf-8",
    )

    rows = load_raw_records(path)

    assert rows == [
        {"drone_id": "DRONE-001", "drone_type": "Quadcopter"},
    ]


def test_load_csv_records_empty_numeric_value_kept_as_string(tmp_path: Path) -> None:
    path = tmp_path / "input.csv"
    path.write_text("drone_id,battery_percent\nDRONE-001,\n", encoding="utf-8")

    rows = load_raw_records(path)

    assert rows == [{"drone_id": "DRONE-001", "battery_percent": ""}]


def test_load_csv_records_missing_header_column(tmp_path: Path) -> None:
    path = tmp_path / "input.csv"
    path.write_text("drone_id\nDRONE-001\n", encoding="utf-8")

    rows = load_raw_records(path)

    assert rows == [{"drone_id": "DRONE-001"}]


def test_load_csv_records_malformed_csv_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text('drone_id\n"unterminated\n', encoding="utf-8")

    with pytest.raises(InputLoadError, match="not valid CSV"):
        load_raw_records(path)


def test_load_raw_records_unsupported_extension_raises(tmp_path: Path) -> None:
    path = tmp_path / "input.txt"
    path.write_text("hello", encoding="utf-8")

    with pytest.raises(InputLoadError, match="Unsupported input file extension"):
        load_raw_records(path)
