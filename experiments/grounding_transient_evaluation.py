"""Causal count hints, transient equal-count drift, and collection phase."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from experiments.grounding_benefit_evaluation import run_worker

CONFIGS={n:dict(interval=i,capacity=8,seed=0)
         for n,i in (('every1',1),('every4',4),('count4',4))}


def worker(repeat=0,densities=(128,),phases=(1,4)):
    rows=[]
    for phase in phases:
        for burst in (False,True):
            result=run_worker(repeat,densities,
                variants={n:dict(reuse=True,max_reuses=2) for n in CONFIGS},
                cadence_configs=CONFIGS,tail_shift=True,transient_block=phase,
                count_burst=burst,count_trigger_arms=('count4',))
            for row in result['rows']:
                row.update(phase=phase,count_burst=burst)
            rows.extend(result['rows'])
    return dict(hash_seed=os.environ.get('PYTHONHASHSEED'),repeat=repeat,rows=rows)


def audit(results):
    groups={}
    for process in results:
        for row in process['rows']:
            key=(row['world'],row['density'],row['phase'],row['count_burst'])
            groups.setdefault(key,[]).append(row)
    assert groups
    for rows in groups.values():
        assert len(rows)==len(results)
        assert len({r['saved_content_sha256'] for r in rows})==1
        assert len({json.dumps([t['result_sha256'] for t in r['trace']]) for r in rows})==1
        # Collection decisions use only counts and should not depend on timings/hash.
        assert len({json.dumps([[t[n]['collected'] for n in CONFIGS] for t in r['trace']]) for r in rows})==1
    return dict(processes=results,results_and_saved_contents_equal=True,
                allocation_determinism_expected=False,cadence=CONFIGS)


def run_processes(output):
    results=[]
    with TemporaryDirectory() as directory:
        for seed in (0,1,42):
            for repeat in range(5):
                path=Path(directory)/f'{seed}-{repeat}.json'
                subprocess.run([sys.executable,'-m','experiments.grounding_transient_evaluation',
                    '--worker','--repeat',str(repeat),'--output',str(path)],check=True,
                    env={**os.environ,'PYTHONHASHSEED':str(seed)})
                results.append(json.loads(path.read_text()))
                Path(output).write_text(json.dumps(dict(processes=results),indent=2)+'\n')
                print(f'finished seed={seed} repeat={repeat}',flush=True)
    return audit(results)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--worker',action='store_true')
    parser.add_argument('--repeat',type=int,default=0)
    parser.add_argument('--output',default='docs/g3-grounding-transient-results-2026-10-28.json')
    args=parser.parse_args()
    result=worker(args.repeat) if args.worker else run_processes(args.output)
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
