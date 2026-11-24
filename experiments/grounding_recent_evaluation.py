"""Equal-byte freezing versus recency, with full-window and tail quality."""
from collections import Counter
import hashlib
import json
import os
import subprocess
import sys
import tracemalloc
from pathlib import Path
from time import process_time, perf_counter

from experiments.grounding_benefit_evaluation import run_worker, audit
from risa.engine.grounding_sampling import GroundingSampleWindow, collector_bytes


def stream(kind):
    rows = []
    for i in range(512):
        if kind == 'stationary':
            key, value = str(i % 16), str(i % 4)
        elif kind == 'binding_shift':
            key, value = 'same', 'old' if i < 256 else 'new'
        elif kind == 'key_shift':
            key, value = str(i % 8 + (0 if i < 256 else 8)), str(i % 3)
        else:  # A -> B -> A, with changing joint identity and role pairs.
            key, value = ('a' if i < 128 or i >= 384 else 'b'), str(i % 3)
        roles = ('actor', value)
        rows.append((key, roles, value, value if i % 2 else 'other', ('target', value)))
    return rows


def quality(samples, rows):
    full = {}
    for key, *args in rows:
        full.setdefault(key, []).append(tuple(args))
    weighted = 0.
    for key, values in full.items():
        truth, estimated = Counter(values), Counter(samples.get(key, []))
        n, m = len(values), sum(estimated.values())
        tv = .5 * sum(abs(truth[v]/n - estimated[v]/m) for v in truth.keys() | estimated.keys()) if m else 1.
        weighted += n * tv
    return weighted / len(rows)


def collect(rows, policy, budget):
    w = GroundingSampleWindow(policy=policy, budget_bytes=budget)
    for args in rows:
        w.observe(*args)
    w.samples()
    return w


def worker(order):
    configs = {name: dict(policy=policy, budget_bytes=budget) for name, policy, budget in
               (('freeze', 'reservoir', 4096), ('recent', 'recent', 4096),
                ('wide_freeze', 'reservoir', 32768), ('wide_recent', 'recent', 32768))}
    result = run_worker(order, variants={n: dict(reuse=True) for n in configs},
                        sample_configs=configs, calibration_blocks=(0,1,2),
                        tail_shift=True, time_observer_setup=True)
    result['micro'] = []
    for kind in ('stationary','binding_shift','key_shift','return'):
        rows = stream(kind)
        for budget in (4096,32768):
            for policy in ('reservoir','recent')[::1 if order % 2 == 0 else -1]:
                cpu, wall = process_time(), perf_counter()
                w = collect(rows, policy, budget)
                cpu, wall = process_time()-cpu, perf_counter()-wall
                samples = w.samples()
                tracemalloc.start()
                traced = collect(rows, policy, budget)
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                assert samples == traced.samples()
                assert collector_bytes(w._streams) <= budget
                result['micro'].append(dict(kind=kind, budget=budget, policy=policy,
                    cpu=cpu, wall=wall, retained=collector_bytes(w._streams), peak=peak,
                    full_tv=quality(samples, rows), tail_tv=quality(samples, rows[-128:]),
                    keys=len(samples), exhausted=w.exhausted,
                    sample_digest=hashlib.sha256(repr(sorted(samples.items())).encode()).hexdigest()))
    return result


if __name__ == '__main__':
    if len(sys.argv) > 1:
        print(json.dumps(worker(int(sys.argv[1]))))
    else:
        runs = []
        for seed in (0,1,42):
            for order in range(2):
                runs.append(json.loads(subprocess.check_output(
                    [sys.executable, '-m', 'experiments.grounding_recent_evaluation', str(order)],
                    env={**os.environ, 'PYTHONHASHSEED':str(seed)})))
                print(f'completed hash={seed} order={order}', flush=True)
        for kind in ('stationary','binding_shift','key_shift','return'):
            for budget in (4096,32768):
                for policy in ('reservoir','recent'):
                    assert len({m['sample_digest'] for p in runs for m in p['micro']
                                if (m['kind'],m['budget'],m['policy'])==(kind,budget,policy)})==1
        Path('docs/g3-grounding-recent-results-2026-11-19.json').write_text(
            json.dumps(audit(runs), indent=2)+'\n')
