"""Paired fresh/reused calibration; all controls retain identical query windows."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from experiments.grounding_benefit_evaluation import run_worker, audit

VARIANTS = dict(fresh=dict(reuse=False), reuse=dict(reuse=True,max_reuses=2))


def worker(repeat=0, densities=(32,512)):
    # One initial measurement, an identical window, then an append window.
    # Append leaves joint rows unchanged on small worlds, adds one on wide world.
    return run_worker(repeat,densities,variants=VARIANTS,calibration_blocks=(0,1,2))


def run_processes(output):
    results=[]
    with TemporaryDirectory() as directory:
        for seed in (0,1,42):
            for repeat in range(4):
                path=Path(directory)/f'{seed}-{repeat}.json'
                subprocess.run([sys.executable,'-m','experiments.grounding_reuse_evaluation','--worker',
                    '--repeat',str(repeat),'--output',str(path)],env={**os.environ,'PYTHONHASHSEED':str(seed)},check=True)
                results.append(json.loads(path.read_text()))
                Path(output).write_text(json.dumps(dict(processes=results),indent=2)+'\n')
                print(f'finished seed={seed} repeat={repeat}',flush=True)
    result=audit(results)
    result['variants']=VARIANTS
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true')
    p.add_argument('--repeat',type=int,default=0)
    p.add_argument('--output',default='docs/g3-grounding-reuse-results-2026-10-22.json')
    args=p.parse_args()
    result=worker(args.repeat) if args.worker else run_processes(args.output)
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
