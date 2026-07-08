from __future__ import annotations

import json
from pathlib import Path

from risa.core.state import RisaState


def save_state(state: RisaState, output_dir: str | Path) -> None:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "state.json").write_text(
        json.dumps(state.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def load_state(output_dir: str | Path) -> RisaState:
    path = Path(output_dir) / "state.json"
    if not path.exists():
        return RisaState()
    return RisaState.from_dict(json.loads(path.read_text(encoding="utf-8")))

