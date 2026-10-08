"""Isolate predecessor selection; instrumentation is separate from paired timing."""
import cProfile
import json
import platform
import pstats
import statistics
from time import perf_counter, process_time
import tracemalloc
from risa.core.models import Event
from risa.engine.graph_builder import normalize_label
from risa.engine.runtime import _previous_events


def before(history, incoming, filter_output=True):
    global_previous, actor_previous = {}, {}
    for event in sorted(history, key=lambda e: (e.timestamp, e.id)):
        episode = event.episode_id or '__default__'
        global_previous[episode] = event
        actor_previous[(episode, normalize_label(event.actor))] = event
    if not filter_output:
        return global_previous, actor_previous
    episodes = {e.episode_id or '__default__' for e in incoming}
    actors = {(e.episode_id or '__default__', normalize_label(e.actor)) for e in incoming}
    return ({k:v for k,v in global_previous.items() if k in episodes},
            {k:v for k,v in actor_previous.items() if k in actors})


def main():
    rows = []
    for scale in (4, 1000, 10000, 100000):
        for scenario in ('episodes', 'single-episode'):
            history = [Event(id=f'e{i:09d}', timestamp=i+1, actor=f'actor-{i%8}', action='go',
                             episode_id=f'episode-{i//12}' if scenario=='episodes' else None)
                       for i in range(scale)]
            incoming = [Event(id=f'e{i:09d}', timestamp=i+1, actor=f'actor-{i%8}', action='go',
                              episode_id=f'episode-{i//12}' if scenario=='episodes' else None)
                        for i in range(scale, scale+min(scale,1000))]
            expected = before(history, incoming)
            for sample in range(15):
                for name in (('before','after') if sample%2==0 else ('after','before')):
                    function = before if name=='before' else _previous_events
                    wall, cpu = perf_counter(), process_time()
                    actual = function(history, incoming, False) if name=='before' else function(history, incoming)
                    wall, cpu = perf_counter()-wall, process_time()-cpu
                    assert all(all(actual[i][k] is v for k,v in mapping.items()) for i,mapping in enumerate(expected))
                    rows.append(dict(scale=scale, scenario=scenario, implementation=name,
                                     wall_seconds=wall, cpu_seconds=cpu, equal=True))
            for name, function in (('before',before),('after',_previous_events)):
                profile=cProfile.Profile()
                tracemalloc.start()
                profile.enable()
                actual=function(history,incoming,False) if name=='before' else function(history,incoming)
                profile.disable()
                retained,peak=tracemalloc.get_traced_memory()
                tracemalloc.stop()
                assert all(all(actual[i][k] is v for k,v in mapping.items()) for i,mapping in enumerate(expected))
                stats=pstats.Stats(profile)
                rows.append(dict(scale=scale,scenario=scenario,implementation=name,instrumented=True,
                                 traced_peak_bytes=peak,traced_retained_bytes=retained,total_calls=stats.total_calls,
                                 profile=[dict(function=str(k),calls=v[1],cumulative_seconds=v[3])
                                          for k,v in sorted(stats.stats.items(),key=lambda x:x[1][3],reverse=True)[:8]]))
    summary=[]
    for scale in (4,1000,10000,100000):
        for scenario in ('episodes','single-episode'):
            for name in ('before','after'):
                samples=[r for r in rows if r['scale']==scale and r['scenario']==scenario and r['implementation']==name and not r.get('instrumented')]
                walls=sorted(r['wall_seconds'] for r in samples)
                summary.append(dict(scale=scale,scenario=scenario,implementation=name,
                                    median_seconds=statistics.median(walls),p95_seconds=walls[-1],p99_seconds=walls[-1],max_seconds=walls[-1],
                                    cpu_median_seconds=statistics.median(r['cpu_seconds'] for r in samples)))
    output='docs/history-setup-results-2026-10-08.json'
    with open(output,'w') as f: json.dump(dict(environment=dict(python=platform.python_version(),platform=platform.platform()),
                                             rows=rows,summary=summary,note='15 alternating in-process pairs; objects prepared outside timing; profiles separate; empirical tails only.'),f,indent=2)
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
