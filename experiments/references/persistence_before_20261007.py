from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from risa.core.state import RisaState


def save_state(state: RisaState, output_dir: str | Path) -> None:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    state_path = path / "state.json"
    backup_path = path / "state.json.bak"
    encoded = json.dumps(state.to_dict(), indent=2, sort_keys=True)
    RisaState.from_dict(json.loads(encoded))

    if state_path.exists():
        existing = state_path.read_text(encoding="utf-8")
        try:
            RisaState.from_dict(json.loads(existing))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        else:
            _atomic_write(backup_path, existing)
    _atomic_write(state_path, encoded)


def load_state(output_dir: str | Path) -> RisaState:
    directory = Path(output_dir)
    state_path = directory / "state.json"
    backup_path = directory / "state.json.bak"
    if not state_path.exists() and not backup_path.exists():
        return RisaState()

    primary_error: Exception | None = None
    if state_path.exists():
        try:
            return RisaState.from_dict(json.loads(state_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            primary_error = error
    if backup_path.exists():
        return RisaState.from_dict(json.loads(backup_path.read_text(encoding="utf-8")))
    assert primary_error is not None
    raise primary_error


def _atomic_write(path: Path, content: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
