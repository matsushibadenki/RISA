import json
from pathlib import Path

from experiments.g3_scope_expiry_audit import run_scope_expiry_audit


def test_scope_expiry_contract_passes_all_registered_seeds():
    manifest = json.loads(Path("experiments/g3_scope_expiry_audit_manifest.json").read_text())
    result = run_scope_expiry_audit(manifest)
    assert result["status"] == "passed"
    assert len(result["rows"]) == 5
    assert all(row["out_of_scope_revalidation_labels"] == 0 for row in result["rows"])
    assert all(all(row["in_scope_mutations_rejected"].values()) for row in result["rows"])


def test_scope_expiry_manifest_hash_changes_with_protocol():
    manifest = json.loads(Path("experiments/g3_scope_expiry_audit_manifest.json").read_text())
    first = run_scope_expiry_audit(manifest)
    changed = {**manifest, "benchmark_version": "changed"}
    second = run_scope_expiry_audit(changed)
    assert first["manifest_sha256"] != second["manifest_sha256"]
