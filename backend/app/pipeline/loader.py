"""Raw JSON input loading for the drone telemetry pipeline.

Only responsible for turning a file path into a list of raw dicts, or
raising `InputLoadError` if the *file itself* can't be read or parsed.
Whether an individual record is a valid drone telemetry record is not this
module's concern — that's the Pydantic schema's job (see
app/schemas/drone_telemetry.py) and the runner's counting logic.

Kept narrow on purpose: a future CSV (or other source) loader could be
added later as a sibling function with the same `-> list[dict]` return
shape, without touching validation or persistence code.
"""

import json
from pathlib import Path


class InputLoadError(Exception):
    """The input source itself could not be read or parsed as a JSON array.

    Distinct from an individual record being invalid — that never raises
    an exception, it's simply counted by the pipeline runner.
    """


def load_raw_records(path: str | Path) -> list[dict]:
    path = Path(path)

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputLoadError(f"Could not read input file '{path}': {exc}") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise InputLoadError(f"Input file '{path}' is not valid JSON: {exc}") from exc

    if not isinstance(data, list):
        raise InputLoadError(
            f"Input file '{path}' must contain a JSON array of records, "
            f"got {type(data).__name__}"
        )

    return data
