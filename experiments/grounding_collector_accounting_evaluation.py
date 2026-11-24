"""Matched-byte full audits versus conservative headroom, identical coverage."""
import json
import os
import subprocess
import sys
import tracemalloc
from pathlib import Path
from time import process_time

from experiments.grounding_benefit_evaluation import run_worker, audit
from experiments.grounding_collector_budget_evaluation import collect
from risa.engine.grounding_sampling import GroundingSampleWindow, collector_bytes


class FullAccountingWindow(GroundingSampleWindow):
    # Exact pre-headroom path, without paying for a failed bound calculation.
    _use_headroom = False


def worker(order):
    configs = {name: dict(budget_bytes=budget) for name, budget in
               (('full', 32768), ('headroom', 32768), ('tight_full', 4096), ('tight_headroom', 4096))}
    result = run_worker(order, variants={n: dict(reuse=True) for n in configs},
                        sample_configs=configs,
                        sample_factories={n: FullAccountingWindow for n in ('full', 'tight_full')},
                        calibration_blocks=(0, 1, 2), tail_shift=True, time_observer_setup=True)
    for row in result['rows']:
        for trace in row['trace']:
            for a, b in (('full', 'headroom'), ('tight_full', 'tight_headroom')):
                if 'sample_digest' in trace[a]:
                    assert trace[a]['sample_digest'] == trace[b]['sample_digest']
                    assert trace[a]['sample_tv'] == trace[b]['sample_tv']
                    assert trace[a]['collector_exhausted'] == trace[b]['collector_exhausted']
    result['micro'] = []
    for streams, length in ((256, 4), (4, 512), (64, 32)):
        samples = []
        for cls in (FullAccountingWindow, GroundingSampleWindow)[::1 if order % 2 == 0 else -1]:
            factory = lambda: cls(budget_bytes=32768)
            start = process_time()
            w = collect(factory, streams, length)
            cpu = process_time() - start
            samples.append(w.samples())
            tracemalloc.start()
            traced = collect(factory, streams, length)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            assert traced.samples() == w.samples()
            result['micro'].append(dict(streams=streams, length=length, arm=cls.__name__,
                                        cpu=cpu, retained=collector_bytes(w._streams), peak=peak))
        assert samples[0] == samples[1]
    return result


if __name__ == '__main__':
    if len(sys.argv) > 1:
        print(json.dumps(worker(int(sys.argv[1]))))
    else:
        runs = []
        for seed in (0, 1, 42):
            for order in range(2):
                runs.append(json.loads(subprocess.check_output(
                    [sys.executable, '-m', 'experiments.grounding_collector_accounting_evaluation', str(order)],
                    env={**os.environ, 'PYTHONHASHSEED': str(seed)})))
                print(f'completed hash={seed} order={order}', flush=True)
        Path('docs/g3-grounding-collector-accounting-results-2026-11-19.json').write_text(
            json.dumps(audit(runs), indent=2)+'\n')
