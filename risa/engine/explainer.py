from __future__ import annotations

from risa.core.models import PredictionResult


def format_prediction(result: PredictionResult) -> str:
    lines = [
        f"Predicted effects: {', '.join(result.predicted_effects) if result.predicted_effects else 'none'}",
        f"Score: {result.score}",
        f"Explanation: {result.explanation}",
    ]
    if result.supporting_paths:
        lines.append("Supporting paths:")
        for path in result.supporting_paths:
            lines.append(f"  - {' -> '.join(path)}")
    if result.evidence_event_ids:
        lines.append(f"Evidence events: {', '.join(result.evidence_event_ids)}")
    return "\n".join(lines)

