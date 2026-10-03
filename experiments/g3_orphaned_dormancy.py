"""Paired development test of unchanged-parent reactivation after expiry."""
import hashlib
import json
from pathlib import Path

from experiments.g3_role_online_ablation import run_online_ablation


def run_orphaned_dormancy(manifest):
    controls = []
    for enabled in (False, True):
        result = run_online_ablation({**manifest, 'reactivate_validated_orphaned_ancestors': enabled})
        controls.append({'reactivation_enabled': enabled, 'result': result})
    before, after = (control['result']['rows'] for control in controls)
    comparisons = []
    for old, new in zip(before, after):
        if (old['seed'], old['arm']) != (new['seed'], new['arm']):
            raise AssertionError('unpaired rows')
        if old['labels_consumed'] != new['labels_consumed']:
            raise AssertionError('reactivation consumed extra supervision')
        if old['adoption_decisions'] != new['adoption_decisions']:
            raise AssertionError('reactivation changed the adoption panel')
        comparisons.append({'seed': old['seed'], 'arm': old['arm'],
            'labels_consumed_equal': True, 'adoption_decisions_equal': True,
            'checkpoint_A_correct_delta': {a['boundary']: b['nuisance_A_correct'] - a['nuisance_A_correct']
                                          for a, b in zip(old['checkpoints'], new['checkpoints'])},
            'B_recovery_equal': old['outcome']['B']['recovery_events'] == new['outcome']['B']['recovery_events'],
            'A2_recovery_equal': old['outcome']['A2']['recovery_events'] == new['outcome']['A2']['recovery_events']})
    return {'benchmark_version': manifest['benchmark_version'],
            'manifest_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
            'status': 'development_orphaned_dormancy_control_only',
            'controls': controls, 'comparisons': comparisons}


if __name__ == '__main__':
    manifest = json.loads(Path('experiments/g3_orphaned_dormancy_manifest.json').read_text())
    result = run_orphaned_dormancy(manifest)
    Path('docs/g3-orphaned-dormancy-results.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'paired_rows': len(result['comparisons'])}))
