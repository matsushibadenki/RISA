"""Run a preregistered RISA comparative benchmark manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from risa.evaluation import load_manifest, run_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(prog="python3 -m experiments.comparative_evaluation")
    parser.add_argument("--manifest", default="experiments/g1_manifest.json")
    parser.add_argument("--output", default="docs/g1-comparative-results.json")
    args = parser.parse_args()

    result = run_benchmark(load_manifest(args.manifest))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output_path), "rows": len(result["rows"])}, indent=2))


if __name__ == "__main__":
    main()
