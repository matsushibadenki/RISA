"""Serial repetitions of the unchanged G3.3 gate, preserving every outcome."""
import argparse
import json
import math
from pathlib import Path
import statistics
from experiments.end_to_end_scale_evaluation import run_evaluation, validate_manifest


def summarize_runs(runs):
    scales = sorted({row['event_scale'] for run in runs for row in run['rows']})
    summaries = []
    for scale in scales:
        rows = [row for run in runs for row in run['rows'] if row['event_scale'] == scale]
        completed = [row for row in rows if row['status'] == 'complete']
        walls = sorted(row['worker_wall_seconds'] for row in completed)
        summaries.append({'event_scale':scale,'attempts':len(rows),'completed':len(completed),
                          'timeouts':sum(row['status']=='time_budget_exceeded' for row in rows),
                          'errors':sum(row['status']=='error' for row in rows),
                          'correct_predictions':sum(row.get('prediction_correct',0) for row in completed) if completed else None,
                          'queries':sum(row.get('query_count',0) for row in completed) if completed else None,
                          'reload_mismatches':sum(row.get('prediction_mismatches_after_reload',0) for row in completed) if completed else None,
                          'compaction_mismatches':sum(row.get('prediction_mismatches_after_compaction',0) for row in completed) if completed else None,
                          'completed_worker_wall_median_seconds':statistics.median(walls) if walls else None,
                          'completed_worker_wall_p95_seconds':walls[math.ceil(.95*len(walls))-1] if walls else None,
                          'completed_worker_wall_p99_seconds':walls[math.ceil(.99*len(walls))-1] if walls else None,
                          'completed_worker_wall_max_seconds':max(walls) if walls else None})
    return summaries


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',default='experiments/g3_end_to_end_manifest.json')
    parser.add_argument('--repetitions',type=int,default=3)
    parser.add_argument('--output',default='docs/g3-stability-results-2026-10-09.json')
    args=parser.parse_args()
    if args.repetitions<1:
        parser.error('repetitions must be positive')
    manifest=validate_manifest(json.loads(Path(args.manifest).read_text()))
    result={'requested_repetitions':args.repetitions,'runs':[],
            'note':'Serial fresh workers, unchanged manifest and 45s budget. Every outcome retained. Completed-only quantiles exclude censored timeouts and are not production tail guarantees.'}
    for repeat in range(args.repetitions):
        result['runs'].append(run_evaluation(manifest))
        result['summary']=summarize_runs(result['runs'])
        result['decision']='measurement_in_progress' if repeat+1<args.repetitions else (
            'all_repeated_gates_complete' if all(run['decision']=='profile_complete' for run in result['runs']) else 'repeated_gate_incomplete')
        Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'repetition':repeat+1,'decision':result['runs'][-1]['decision'],'summary':result['summary']}),flush=True)

if __name__=='__main__':main()
