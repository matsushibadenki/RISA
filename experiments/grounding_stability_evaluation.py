"""Equal-budget stability gates; fresh serial processes, CPU and wall costs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from experiments.grounding_frequency_evaluation import run_worker

GATES = dict(id={}, frequency=dict(probe_cold_candidates=True),
             confirmed=dict(confirmation_windows=2, probe_cold_candidates=True),
             resident=dict(minimum_residency_windows=2, probe_cold_candidates=True))
DENSITIES = (8, 64, 256)


def run_processes():
    results = []
    with TemporaryDirectory() as directory:
        for seed in (0, 1, 42):
            for repeat in range(4):
                path = Path(directory) / f'{seed}-{repeat}.json'
                subprocess.run([sys.executable, '-m', 'experiments.grounding_stability_evaluation',
                    '--worker', '--repeat', str(repeat), '--output', str(path)],
                    env={**os.environ, 'PYTHONHASHSEED': str(seed)}, check=True)
                results.extend(json.loads(path.read_text()))
                print(f'finished seed={seed} repeat={repeat}', flush=True)
    assert len({row['saved_sha256'] for proc in results for row in proc['rows']}) == 1
    for density in DENSITIES:
        for workload in ('stationary', 'shifting', 'rapid'):
            rows = [row for proc in results if proc['queries'] == density
                    for row in proc['rows'] if row['workload'] == workload]
            assert len({json.dumps([[b[n]['selected'] for n in GATES] for b in r['trace']]) for r in rows}) == 1
            assert len({json.dumps([b['result_sha256'] for b in r['trace']]) for r in rows}) == 1
    return dict(processes=results, cross_process_saved_results_allocations_equal=True,
                gates=GATES, densities=DENSITIES)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--repeat', type=int, default=0)
    parser.add_argument('--output', default='docs/g3-grounding-stability-results-2026-10-15.json')
    args = parser.parse_args()
    result = ([run_worker(args.repeat, density, GATES) for density in DENSITIES]
              if args.worker else run_processes())
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
