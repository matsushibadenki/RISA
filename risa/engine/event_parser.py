from __future__ import annotations

import json
from pathlib import Path

from risa.core.models import Event


def _validate_event(data: dict) -> Event:
    required = ["id", "timestamp", "actor", "action", "observed_effects"]
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"Missing required event fields: {', '.join(missing)}")
    if not data["observed_effects"]:
        raise ValueError("observed_effects must contain at least one effect")
    return Event(
        id=str(data["id"]),
        timestamp=int(data["timestamp"]),
        actor=str(data["actor"]),
        action=str(data["action"]),
        target=None if data.get("target") is None else str(data.get("target")),
        observed_effects=[str(effect) for effect in data.get("observed_effects", [])],
        context_tags=[str(tag) for tag in data.get("context_tags", [])],
    )


def parse_events(path: str | Path) -> list[Event]:
    input_path = Path(path)
    text = input_path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    if text.startswith("["):
        payload = json.loads(text)
        return [_validate_event(item) for item in payload]

    events: list[Event] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(_validate_event(json.loads(line)))
    return events

