"""Opt-in retained-byte cap, count-cap baseline, and lazy RNG cost audit."""
import hashlib
import json
import os
import random
import subprocess
import sys
import tracemalloc
from pathlib import Path
from time import process_time, perf_counter

from experiments.grounding_benefit_evaluation import run_worker, audit
from risa.engine.grounding_sampling import GroundingSampleWindow, collector_bytes


class EagerWindow(GroundingSampleWindow):
    def _observe(self, key, *args):
        super()._observe(key, *args)
        stream = self._streams[key]
        if stream['seen'] == 1:
            seed = int.from_bytes(hashlib.sha256(f'{self.seed}\0{key}'.encode()).digest(), 'big')
            stream['rng'] = random.Random(seed)


def collect(factory, streams, length):
    window = factory()
    for i in range(length):
        for k in range(streams):
            window.observe(str(k), ('actor', str(k % 7)), str(i), str(i if i % 2 else -i), ('target',))
    window.samples()
    return window


def micro(order):
    rows = []
    factories = dict(eager=EagerWindow, lazy=GroundingSampleWindow,
                     count=lambda: GroundingSampleWindow(max_streams=16),
                     bytes=lambda: GroundingSampleWindow(budget_bytes=32768))
    for streams, length in ((256, 4), (4, 512), (64, 32)):
        for name in list(factories)[order % 4:] + list(factories)[:order % 4]:
            cpu, wall = process_time(), perf_counter()
            w = collect(factories[name], streams, length)
            cpu, wall = process_time() - cpu, perf_counter() - wall
            tracemalloc.start()
            peak_window = collect(factories[name], streams, length)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            assert w.samples() == peak_window.samples()
            rows.append(dict(streams=streams, length=length, arm=name, cpu=cpu, wall=wall,
                retained_bytes=collector_bytes(w._streams), traced_peak_bytes=peak,
                sampled_keys=len(w.samples()), coverage=len(w.samples()) / streams,
                exhausted=w.exhausted))
    return rows


def worker(order):
    configs = dict(lazy={}, count=dict(max_streams=2), bytes=dict(budget_bytes=4096))
    result = run_worker(order, variants={k: dict(reuse=True) for k in configs},
                        sample_configs=configs, calibration_blocks=(0, 1, 2),
                        tail_shift=True, time_observer_setup=True)
    result['micro'] = micro(order)
    return result


if __name__ == '__main__':
    if len(sys.argv) > 1:
        print(json.dumps(worker(int(sys.argv[1]))))
    else:
        runs = []
        for seed in (0, 1, 42):
            for order in range(2):
                runs.append(json.loads(subprocess.check_output(
                    [sys.executable, '-m', 'experiments.grounding_collector_budget_evaluation', str(order)],
                    env={**os.environ, 'PYTHONHASHSEED': str(seed)})))
                print(f'completed hash={seed} order={order}', flush=True)
        result = audit(runs)
        Path('docs/g3-grounding-collector-budget-results-2026-11-19.json').write_text(json.dumps(result, indent=2)+'\n')
