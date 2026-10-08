"""Paired bounded Replay ablation, preserving state and summary exactly."""
import argparse
import cProfile
import hashlib
import json
from pathlib import Path
import platform
import pstats
import resource
import subprocess
import sys
import sysconfig
from time import perf_counter, process_time
import tracemalloc

from risa.core.state import RisaState
from risa.engine.persistence import load_state
from risa.engine.replay import replay_structural_memory
from experiments.references.replay_before_20261008 import replay_structural_memory as replay_before
from experiments.persistence_optimization import summarize


def worker(args):
    if not (args.fixture/'state.json').is_file():
        raise ValueError('prepare fixture first')
    state = load_state(args.fixture)
    initial = state.to_dict()
    replay = replay_before if args.implementation == 'before' else replay_structural_memory
    profile = cProfile.Profile() if args.profile else None
    if profile:
        tracemalloc.start()
        profile.enable()
    usage_before = resource.getrusage(resource.RUSAGE_SELF)
    wall, cpu = perf_counter(), process_time()
    result = replay(state, max_events=32)
    wall, cpu = perf_counter()-wall, process_time()-cpu
    usage = resource.getrusage(resource.RUSAGE_SELF)
    current = peak = blocks = None
    if profile:
        profile.disable()
        current, peak = tracemalloc.get_traced_memory()
        blocks = sum(s.count for s in tracemalloc.take_snapshot().statistics('filename'))
        tracemalloc.stop()
    reference = RisaState.from_dict(initial)
    expected = replay_before(reference, max_events=32)
    snapshot = state.to_dict()
    equal = snapshot == reference.to_dict() and result == expected
    if not equal:
        raise AssertionError('Replay state or summary differs')
    row = {'implementation':args.implementation,'events':len(state.events_by_id),'operation':'replay',
           'wall_seconds':wall,'cpu_seconds':cpu,'peak_rss_bytes':usage.ru_maxrss*(1 if sys.platform=='darwin' else 1024),
           'instrumented':bool(profile),'traced_peak_bytes':peak,'traced_retained_bytes':current,
           'live_allocation_blocks':blocks,'state_equal':equal,'summary':result.to_dict(),
           'voluntary_context_switches':usage.ru_nvcsw-usage_before.ru_nvcsw,
           'involuntary_context_switches':usage.ru_nivcsw-usage_before.ru_nivcsw,
           'snapshot_sha256':hashlib.sha256(json.dumps(snapshot,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
    if profile:
        stats = pstats.Stats(profile)
        row['total_calls'] = stats.total_calls
        row['profile'] = [{'function':f'{k[0]}:{k[1]}:{k[2]}','calls':v[1],'cumulative_seconds':v[3]}
                         for k,v in sorted(stats.stats.items(),key=lambda item:item[1][3],reverse=True)[:20]]
    return row


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--worker',action='store_true')
    p.add_argument('--profile',action='store_true')
    p.add_argument('--implementation',choices=['before','after'],default='before')
    p.add_argument('--fixture',type=Path,default=Path('/tmp/risa-optimization-fixtures/10000'))
    p.add_argument('--samples',type=int,default=9)
    p.add_argument('--output',type=Path,default=Path('/tmp/replay-results.json'))
    args=p.parse_args()
    if args.samples<1:p.error('samples must be positive')
    if args.worker:
        print(json.dumps(worker(args)))
        return
    rows=[]
    for sample in range(args.samples):
        pair=[]
        for impl in (('before','after') if sample%2==0 else ('after','before')):
            command=[sys.executable,'-m','experiments.replay_optimization','--worker','--implementation',impl,'--fixture',str(args.fixture)]
            row=json.loads(subprocess.run(command,check=True,capture_output=True,text=True,timeout=180).stdout)
            row['sample']=sample
            rows.append(row)
            pair.append(row)
        assert pair[0]['snapshot_sha256']==pair[1]['snapshot_sha256'] and pair[0]['summary']==pair[1]['summary']
    for impl in ('before','after'):
        command=[sys.executable,'-m','experiments.replay_optimization','--worker','--profile','--implementation',impl,'--fixture',str(args.fixture)]
        rows.append(json.loads(subprocess.run(command,check=True,capture_output=True,text=True,timeout=180).stdout))
    args.output.write_text(json.dumps({'environment':{'python':platform.python_version(),'platform':platform.platform(),
                                     'python_debug_build':bool(sysconfig.get_config_var('Py_DEBUG'))},
                                     'rows':rows,'summary':{impl:summarize([r for r in rows if r['implementation']==impl],('replay',))
                                                          for impl in ('before','after')},
                                     'note':'Alternating paired fresh subprocesses; Replay bound fixed at 32. Instrumentation separate; snapshots compared outside timing. Empirical tails only, no cumulative-allocation or direct-energy claim.'},indent=2)+'\n')
    print(json.dumps({'output':str(args.output),'pairs':args.samples}))

if __name__=='__main__':main()
