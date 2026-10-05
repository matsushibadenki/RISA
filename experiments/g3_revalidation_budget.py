"""Development lifetime/cost control with independent online re-adoption."""
import hashlib
import json
from pathlib import Path

from experiments.g3_role_online_ablation import run_online_ablation


def summarize_controls(controls):
    summaries = []
    for control in controls:
        for arm in dict.fromkeys(row['arm'] for row in control['result']['rows']):
            rows = [r for r in control['result']['rows'] if r['arm'] == arm]
            summaries.append({'label_cap': control['label_cap'], 'policy': control['policy'], 'arm': arm,
                'seed_count': len(rows), 'labels_consumed': sum(r['labels_consumed'] for r in rows),
                'A2_correct_probe_exposures': sum(r['A2_nuisance_correct_probe_exposures'] for r in rows),
                'A2_probe_exposures': sum(r['A2_nuisance_probe_exposures'] for r in rows),
                'A2_exit_A_correct': sum(next(c['nuisance_A_correct'] for c in r['checkpoints']
                                            if c['boundary'] == 'A2') for r in rows),
                'A2_exit_A_probes': sum(next(c['probes_per_regime'] for c in r['checkpoints']
                                           if c['boundary'] == 'A2') for r in rows),
                'budget_blocked_opportunities': sum(t['status'] == 'budget_reservation_exhausted'
                                                   for r in rows for t in r['revalidation_budget_trace'])})
    return summaries


def run_revalidation_budget(manifest):
    controls = []
    for cap in manifest['label_caps']:
        for policy in ('expiry_only', 'reactivation_only', 'scheduled_revalidation'):
            config = {**manifest, 'label_cap': cap,
                'reactivate_validated_orphaned_ancestors': policy != 'expiry_only',
                'revalidation_after_A2_events': manifest['schedule'] if policy == 'scheduled_revalidation' else []}
            result = run_online_ablation(config)
            controls.append({'label_cap': cap, 'policy': policy, 'result': result})
    return {'benchmark_version': manifest['benchmark_version'],
        'manifest_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
        'status': 'development_revalidation_budget_only', 'controls': controls,
        'summaries': summarize_controls(controls)}


if __name__ == '__main__':
    manifest = json.loads(Path('experiments/g3_revalidation_budget_manifest.json').read_text())
    result = run_revalidation_budget(manifest)
    Path('docs/g3-revalidation-budget-results.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'controls': len(result['controls']),
                      'rows': sum(len(c['result']['rows']) for c in result['controls'])}))
