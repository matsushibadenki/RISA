"""A→B→A development negative control with unseen nuisance contexts."""
import hashlib
import json
from pathlib import Path

from experiments.g3_drift_candidate_primed import (
    nuisance_transfer_probe_panels, run_candidate_primed_preflight,
)
from experiments.g3_drift_preflight import _events
from risa.evaluation.grounded_role_baseline import (
    GroundedRoleSubsetTransitionBaseline, GroundedRoleSubsetCountBaseline,
    GroundedRoleTransitionBaseline, GroundedRoleCountBaseline, run_grounded_role_aba,
)
from dataclasses import replace


def run_transfer_drift(manifest):
    if not manifest.get('nuisance_context_probes'):
        raise ValueError('nuisance_context_probes must be enabled')
    result = run_candidate_primed_preflight(manifest)
    baseline_rows = []
    for seed in manifest['seeds']:
        a_probes, b_probes = nuisance_transfer_probe_panels(seed, manifest['probes_per_phase'])
        for name, model in (
            ('latest_exact', GroundedRoleTransitionBaseline),
            ('count_exact', GroundedRoleCountBaseline),
            ('latest_subset', GroundedRoleSubsetTransitionBaseline),
            ('count_subset', GroundedRoleSubsetCountBaseline),
        ):
            baseline_rows.append({'seed': seed, 'model': name,
                'supervised_adoption_labels': 0,
                'outcome': run_grounded_role_aba(
                    _events(seed, 'A1', 6), _events(seed, 'B', manifest['phase_observations']),
                    _events(seed, 'A2', manifest['phase_observations']), a_probes, b_probes,
                    [replace(p, id=f'transfer:{p.id}') for p in a_probes],
                    [replace(p, id=f'transfer:{p.id}') for p in b_probes],
                    recovery_window=manifest['recovery_window'], model_factory=model),
            })
    return {**result, 'status': 'development_negative_control_only',
            'manifest_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
            'return_cue': 'none', 'baselines': baseline_rows}


if __name__ == '__main__':
    manifest = json.loads(Path('experiments/g3_nuisance_transfer_drift_manifest.json').read_text())
    result = run_transfer_drift(manifest)
    Path('docs/g3-nuisance-transfer-drift-results.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'risa_rows': len(result['rows']), 'baseline_rows': len(result['baselines']),
                      'opportunity_gate': result['mechanism_opportunity_gate']}))
