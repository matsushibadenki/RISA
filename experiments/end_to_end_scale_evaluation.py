"""Budgeted G3.3 profiling through the real training and persistence paths."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import resource
import subprocess
import sys
import tempfile
from time import perf_counter

from risa.core.models import Event, GoalSpecification, PredictionQuery
from risa.core.state import RisaState
from risa.engine.persistence import load_state, save_state
from risa.engine.planner import plan_counterfactuals
from risa.engine.predictor import predict_next_effect
from risa.engine.readout_compaction import compact_adopted_candidate_readouts
from risa.engine.runtime import TrainingOptions, train_events


def validate_manifest(manifest):
    for key in ('event_scales', 'seeds'):
        if not manifest.get(key):
            raise ValueError(f'{key} must not be empty')
    for value in manifest['event_scales']:
        if type(value) is not int or value < 1:
            raise ValueError('event scales must be positive integers')
    for key in ('chunk_size', 'replay_budget', 'queries_per_scale', 'scale_time_budget_seconds'):
        if manifest.get(key, 0) <= 0:
            raise ValueError(f'{key} must be positive')
    return manifest


def profile_scale(manifest, seed, scale, progress_path=None):
    state = RisaState()
    stages = {}
    row = {'seed': seed, 'event_scale': scale, 'ingested_events': 0,
           'status': 'running', 'stage_seconds': stages}
    started = perf_counter()
    summaries = []
    options = TrainingOptions(stage_seconds=stages, replay_max_events=manifest['replay_budget'],
                              replay_summaries=summaries)
    def checkpoint():
        row['elapsed_seconds'] = perf_counter() - started
        row['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)
        if progress_path:
            Path(progress_path).write_text(json.dumps(row), encoding='utf-8')
    for offset in range(0, scale, manifest['chunk_size']):
        events = [Event(id=f'e-{seed}-{i:09d}', timestamp=i + 1,
                        actor=f'actor-{i % 8}', action=f'action-{i % 4}',
                        observed_effects=[f'effect-{i % 4}'],
                        context_tags=[f'context-{i % 3}'],
                        episode_id=f'episode-{seed}-{i // 12}', source=f'source-{i % 2}')
                  for i in range(offset, min(scale, offset + manifest['chunk_size']))]
        train_events(state, events, options)
        row['ingested_events'] += len(events)
        checkpoint()
    queries = [PredictionQuery(actor=f'actor-{i % 8}', action=f'action-{i % 4}',
                               context_tags=[f'context-{i % 3}'])
               for i in range(manifest['queries_per_scale'])]
    def measure(name, operation):
        begin = perf_counter()
        result = operation()
        stages[name] = perf_counter() - begin
        checkpoint()
        return result
    predictions = measure('prediction', lambda: [predict_next_effect(state, q).to_dict() for q in queries])
    measure('compaction', lambda: compact_adopted_candidate_readouts(state, queries))
    compacted = [predict_next_effect(state, q).to_dict() for q in queries]
    report = measure('planning', lambda: plan_counterfactuals(
        state, 'action-0', GoalSpecification(required_states=['effect-0']), [], max_steps=2))
    row['planner_expanded_candidates'] = sum(
        outcome.evaluation.search_diagnostics.get('expanded_candidate_count', 0) for outcome in report.outcomes)
    with tempfile.TemporaryDirectory(prefix='risa-g3-e2e-') as directory:
        measure('save', lambda: save_state(state, directory))
        row['stored_bytes'] = (Path(directory) / 'state.json').stat().st_size
        restored = measure('load', lambda: load_state(directory))
        reloaded = [predict_next_effect(restored, q).to_dict() for q in queries]
    row.update(status='complete',
               prediction_mismatches_after_compaction=sum(a != b for a, b in zip(predictions, compacted)),
               prediction_mismatches_after_reload=sum(a != b for a, b in zip(compacted, reloaded)),
               prediction_correct=sum(p['predicted_effects'] == [f'effect-{i % 4}'] for i, p in enumerate(predictions)),
               query_count=len(queries), graph_nodes=len(state.graph.nodes_by_id),
               graph_edges=len(state.graph.edges_by_key), primitives=len(state.structural_primitives),
               candidates=len(state.unnamed_concept_candidates),
               active_structures=sum(p.adopted for p in state.structural_primitives.values()),
               replayed_events=sum(s.replayed_events for s in summaries))
    row['bytes_per_event'] = row['stored_bytes'] / scale
    row['stage_seconds_per_event'] = {name: elapsed / scale for name, elapsed in stages.items()}
    row['candidates_per_event'] = row['candidates'] / scale
    row['active_graph_nodes'] = sum(not n.dormant for n in state.graph.nodes_by_id.values())
    row['active_candidates'] = sum(not c.dormant for c in state.unnamed_concept_candidates.values())
    row['seconds_per_event'] = (perf_counter() - started) / scale
    row['candidate_description_length_delta'] = sum(c.description_length_delta for c in state.unnamed_concept_candidates.values())
    checkpoint()
    return row


def run_evaluation(manifest):
    validate_manifest(manifest)
    rows = []
    with tempfile.TemporaryDirectory(prefix='risa-g3-profile-') as directory:
        config = Path(directory) / 'manifest.json'
        config.write_text(json.dumps(manifest), encoding='utf-8')
        for seed in manifest['seeds']:
            for scale in manifest['event_scales']:
                progress = Path(directory) / f'{seed}-{scale}.json'
                command = [sys.executable, '-m', 'experiments.end_to_end_scale_evaluation',
                           '--manifest', str(config), '--worker', '--seed', str(seed),
                           '--scale', str(scale), '--output', str(progress)]
                worker_started = perf_counter()
                try:
                    completed = subprocess.run(command, capture_output=True, text=True,
                                               timeout=manifest['scale_time_budget_seconds'])
                    status = 'complete' if completed.returncode == 0 else 'error'
                except subprocess.TimeoutExpired:
                    status = 'time_budget_exceeded'
                    completed = None
                row = json.loads(progress.read_text()) if progress.exists() else {
                    'seed': seed, 'event_scale': scale, 'ingested_events': 0, 'stage_seconds': {}}
                row['status'] = status
                row['worker_wall_seconds'] = perf_counter() - worker_started
                if status == 'time_budget_exceeded':
                    row['progress_note'] = 'Last completed chunk/stage; unfinished chunk work is excluded from stage totals.'
                if status == 'error':
                    row['error'] = completed.stderr[-4000:]
                rows.append(row)
    complete = all(r['status'] == 'complete' for r in rows)
    exact = complete and all(r['prediction_mismatches_after_reload'] == 0 and
                            r['prediction_mismatches_after_compaction'] == 0 for r in rows)
    return {'benchmark_version': 'g3.3-e2e-v1', 'manifest': manifest,
            'manifest_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
            'environment': {'python': platform.python_version(), 'platform': platform.platform()},
            'rows': rows, 'decision': 'profile_complete' if exact else 'scale_gate_incomplete',
            'million_event_decision': 'defer_pending_dedicated_capacity_review' if exact else 'do_not_attempt',
            'note': 'Synthetic bounded-vocabulary workload; no structural-generalization claim.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', default='experiments/g3_end_to_end_manifest.json')
    parser.add_argument('--output', default='docs/g3-end-to-end-results.json')
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--seed', type=int)
    parser.add_argument('--scale', type=int)
    args = parser.parse_args()
    manifest = validate_manifest(json.loads(Path(args.manifest).read_text()))
    result = (profile_scale(manifest, args.seed, args.scale, args.output) if args.worker
              else run_evaluation(manifest))
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'output': args.output, 'decision': result.get('decision', result.get('status'))}))


if __name__ == '__main__':
    main()
