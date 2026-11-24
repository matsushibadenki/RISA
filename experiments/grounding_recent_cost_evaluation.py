"""Compare equivalent recency collectors at matched byte budgets."""
import json
import os
import subprocess
import sys
import tracemalloc
from pathlib import Path
from time import process_time, perf_counter

from experiments.grounding_benefit_evaluation import run_worker, audit
from experiments.grounding_recent_evaluation import stream, quality
from risa.engine.grounding_sampling import GroundingSampleWindow, collector_bytes


class OriginalRecent(GroundingSampleWindow):
    _recent_fast = False


def collect(cls, rows, budget):
    w = cls(policy='recent', budget_bytes=budget)
    for row in rows:
        w.observe(*row)
    w.samples()
    return w


def worker(order):
    configs = {n:dict(policy='recent', budget_bytes=b) for n,b in
               (('old',4096),('fast',4096),('wide_old',32768),('wide_fast',32768))}
    result = run_worker(order, variants={n:dict(reuse=True) for n in configs},
        sample_configs=configs, sample_factories={n:OriginalRecent for n in ('old','wide_old')},
        calibration_blocks=(0,1,2), tail_shift=True, time_observer_setup=True)
    for row in result['rows']:
        for t in row['trace']:
            for a,b in (('old','fast'),('wide_old','wide_fast')):
                if 'sample_digest' in t[a]:
                    assert t[a]['sample_digest']==t[b]['sample_digest']
                    assert t[a]['sample_tv']==t[b]['sample_tv']
    result['micro']=[]
    for kind in ('stationary','binding_shift','key_shift','return'):
        rows=stream(kind)
        for budget in (4096,32768):
            samples=[]
            for cls in (OriginalRecent,GroundingSampleWindow)[::1 if order%2==0 else -1]:
                cpu,wall=process_time(),perf_counter()
                w=collect(cls,rows,budget)
                cpu,wall=process_time()-cpu,perf_counter()-wall
                samples.append(w.samples())
                tracemalloc.start()
                replay=collect(cls,rows,budget)
                _,peak=tracemalloc.get_traced_memory()
                tracemalloc.stop()
                assert replay.samples()==w.samples()
                result['micro'].append(dict(kind=kind,budget=budget,arm=cls.__name__,cpu=cpu,wall=wall,
                    retained=collector_bytes(w._streams),peak=peak,
                    full_tv=quality(w.samples(),rows),tail_tv=quality(w.samples(),rows[-128:])))
            assert samples[0]==samples[1]
    return result


if __name__=='__main__':
    if len(sys.argv)>1:
        print(json.dumps(worker(int(sys.argv[1]))))
    else:
        runs=[]
        for seed in (0,1,42):
            for order in range(2):
                runs.append(json.loads(subprocess.check_output(
                    [sys.executable,'-m','experiments.grounding_recent_cost_evaluation',str(order)],
                    env={**os.environ,'PYTHONHASHSEED':str(seed)})))
                print(f'completed hash={seed} order={order}',flush=True)
        Path('docs/g3-grounding-recent-cost-results-2026-11-19.json').write_text(
            json.dumps(audit(runs),indent=2)+'\n')
