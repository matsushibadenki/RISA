"""Periodic collection versus skipped-window drift, with full charged costs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from experiments.grounding_benefit_evaluation import run_worker, audit

CONFIGS={f'every{i}':dict(interval=i,capacity=8,seed=0) for i in (1,2,4)}


def worker(repeat=0,densities=(32,512)):
    return run_worker(repeat,densities,
        variants={n:dict(reuse=True,max_reuses=2) for n in CONFIGS},
        cadence_configs=CONFIGS, tail_shift=True)


def run_processes(output):
    results=[]
    with TemporaryDirectory() as directory:
        for seed in (0,1,42):
            for repeat in range(5):
                path=Path(directory)/f'{seed}-{repeat}.json'
                subprocess.run([sys.executable,'-m','experiments.grounding_cadence_evaluation',
                    '--worker','--repeat',str(repeat),'--output',str(path)],check=True,
                    env={**os.environ,'PYTHONHASHSEED':str(seed)})
                results.append(json.loads(path.read_text()))
                Path(output).write_text(json.dumps(dict(processes=results),indent=2)+'\n')
                print(f'finished seed={seed} repeat={repeat}',flush=True)
    result=audit(results);result['cadence']=CONFIGS
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true')
    p.add_argument('--repeat',type=int,default=0)
    p.add_argument('--output',default='docs/g3-grounding-cadence-results-2026-10-26.json')
    args=p.parse_args()
    result=worker(args.repeat) if args.worker else run_processes(args.output)
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
