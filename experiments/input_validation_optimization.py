"""Paired exact input-validation ablation, profiling separate from timing."""
import cProfile
import json
import platform
import statistics
from time import perf_counter, process_time
import tracemalloc
from risa.core.models import Event
from risa.core.state import RisaState
from risa.engine.runtime import _validate_and_filter_events as after
from experiments.references.runtime_before_history_20261008 import _validate_and_filter_events as before


def main():
    rows=[]
    for scale in (4,1000,10000,100000):
        for scenario in ('episodes','single-episode'):
            def event(i):
                return Event(id=f'e{i:09d}',timestamp=i+1,actor=f'a{i%8}',action='go',
                             episode_id=f'ep{i//12}' if scenario=='episodes' else None)
            state=RisaState()
            state.events_by_id={e.id:e for e in map(event,range(scale))}
            incoming=list(map(event,range(scale,scale+min(scale,1000))))
            expected=before(state,incoming)
            for sample in range(15):
                for name in (('before','after') if sample%2==0 else ('after','before')):
                    function=before if name=='before' else after
                    wall,cpu=perf_counter(),process_time()
                    actual=function(state,incoming)
                    wall,cpu=perf_counter()-wall,process_time()-cpu
                    assert actual==expected
                    rows.append(dict(scale=scale,scenario=scenario,implementation=name,wall_seconds=wall,cpu_seconds=cpu,equal=True))
            for name,function in (('before',before),('after',after)):
                tracemalloc.start()
                profile=cProfile.Profile();profile.enable()
                actual=function(state,incoming)
                profile.disable()
                retained,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                assert actual==expected
                rows.append(dict(scale=scale,scenario=scenario,implementation=name,instrumented=True,
                                 traced_peak_bytes=peak,traced_retained_bytes=retained,
                                 total_calls=sum(entry.callcount for entry in profile.getstats())))
    summary=[]
    for scale in (4,1000,10000,100000):
        for scenario in ('episodes','single-episode'):
            for name in ('before','after'):
                samples=[r for r in rows if r['scale']==scale and r['scenario']==scenario and r['implementation']==name and not r.get('instrumented')]
                wall=sorted(r['wall_seconds'] for r in samples)
                summary.append(dict(scale=scale,scenario=scenario,implementation=name,median_seconds=statistics.median(wall),
                                    p95_seconds=wall[-1],p99_seconds=wall[-1],max_seconds=wall[-1],
                                    cpu_median_seconds=statistics.median(r['cpu_seconds'] for r in samples)))
    output='docs/input-validation-results-2026-10-09.json'
    with open(output,'w') as f:json.dump(dict(environment=dict(python=platform.python_version(),platform=platform.platform()),
                                           rows=rows,summary=summary,note='15 alternating in-process pairs; preparation/equality outside timing; separate profiling. Synthetic fixtures, empirical tails.'),f,indent=2)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
