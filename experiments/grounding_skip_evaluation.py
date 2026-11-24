"""Compare random draws, collector CPU and charged whole-world costs."""
import json
import hashlib
import random
import os
import subprocess
import sys
from pathlib import Path
from time import process_time

from experiments.grounding_benefit_evaluation import audit, run_worker
from risa.engine.grounding_sampling import GroundingSampleWindow

POLICIES = ('reservoir', 'skip')


class DrawCounter:
    """Count high-level RNG requests in a separate, untimed replay."""
    def __init__(self, rng):
        self.rng, self.calls = rng, 0

    def randrange(self, stop):
        self.calls += 1
        return self.rng.randrange(stop)

    def random(self):
        self.calls += 1
        return self.rng.random()


def collect(policy, length, seed, count=False):
    sampler = GroundingSampleWindow(policy=policy, seed=seed)
    for i in range(length):
        sampler.observe('p', ('a',), i, i, ('t',))
        if count and i == sampler.capacity - 1:
            rng_seed = int.from_bytes(hashlib.sha256(f'{seed}\0p'.encode()).digest(), 'big')
            counter = DrawCounter(random.Random(rng_seed))
            sampler._streams['p']['rng'] = counter
    sampler.samples()
    return counter.calls if count else None


def worker(order):
    run = run_worker(order, variants={p:dict(reuse=True) for p in POLICIES},
                     sample_configs={p:dict(policy=p) for p in POLICIES},
                     calibration_blocks=(0,1,2), tail_shift=True, time_observer_setup=True)
    micro = {}
    for n in (32, 8192):
        micro[n] = {}
        for p in POLICIES[::1 if order % 2 == 0 else -1]:
            tick = process_time()
            for seed in range(64):
                collect(p, n, seed)
            cpu = (process_time() - tick) / 64
            calls = sum(collect(p, n, seed, True) for seed in range(64)) / 64
            micro[n][p] = dict(cpu=cpu, rng_calls=calls)
    run['collector'] = micro
    return run


if __name__ == '__main__':
    if len(sys.argv) == 2:
        print(json.dumps(worker(int(sys.argv[1]))))
    else:
        runs = []
        for seed in (0, 1, 42):
            for order in range(4):
                runs.append(json.loads(subprocess.check_output(
                    [sys.executable, '-m', 'experiments.grounding_skip_evaluation', str(order)],
                    env={**os.environ, 'PYTHONHASHSEED':str(seed)})))
        result = audit(runs)
        Path('docs/g3-grounding-skip-results-2026-11-02.json').write_text(json.dumps(result, indent=2)+'\n')
