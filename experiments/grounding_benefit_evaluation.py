"""Measured unit-cost allocation versus frequency/bytes and ID order."""
from collections import Counter
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter, process_time
from experiments.compositional_holdout import training_episode, heldout_cases
from experiments.compositional_grounding_costs import _query
from experiments.grounding_frequency_evaluation import event, query, OPTIONS
from experiments.grounding_payback_evaluation import timed, content_digest
from experiments.grounding_lookup_evaluation import cache_heap
from risa.core.state import RisaState
from risa.engine.runtime import train_events
from risa.engine.persistence import save_state, load_state
from risa.engine import primitive_grounding as g
from risa.engine.grounding_calibration import calibrate_grounding_benefits
from risa.engine.grounding_sampling import GroundingSampleWindow, GroundingSampleSchedule, GroundingCountTrigger, collector_bytes

ARMS=('id','frequency','benefit')


def run_worker(repeat=0, densities=(32,512), variants=None, calibration_blocks=(0,2),
               sample_configs=None, tail_shift=False, cadence_configs=None,
               transient_block=None, count_burst=False, count_trigger_arms=(), time_observer_setup=False,
               sample_factories=None):
    variants = {'benefit': {}} if variants is None else variants
    arms = ('id','frequency',*variants)
    rows=[]
    for world in ('independent','coupled','concentrated'):
        base=RisaState()
        wide=world=='concentrated'
        train_events(base,[event(p,k) for p in range(4) for k in range(64)] if wide else
            [e for i in range(32) for e in training_episode(17,world,i)],OPTIONS)
        panel=[(p,k,v) for p in range(4) for k in (0,23,63,64) for v in range(3)] if wide else [
            (c,b) for c in heldout_cases(29,world) for b in (False,True)]
        hot=[(3,k,v) for k in (0,23,63,64) for v in range(3)] if wide else panel
        def ask(state,case,indexed=True):
            return query(state,*case,indexed) if wide else _query(state,*case,indexed)
        budget=12000 if wide else 2320
        for density in densities:
            states={n:RisaState.from_dict(base.to_dict()) for n in arms}
            stats={n:dict(build={},train=[],query=[],rebalance=[],calibration=[],promotions=0,retained_heap_samples=[],sampler_heap=[]) for n in arms}
            traces=[]; checks=0
            schedules={n:GroundingSampleSchedule(**c) for n,c in (cadence_configs or {}).items()}
            retained={}
            triggers={n:GroundingCountTrigger() for n in count_trigger_arms}
            pending={n:False for n in count_trigger_arms}
            window_count=8 if transient_block is not None else 4
            for n in arms[repeat%len(arms):]+arms[:repeat%len(arms)]:
                _,stats[n]['build']=timed(lambda:g.build_primitive_grounding(states[n],incremental=True,
                    total_lookup_budget_bytes=budget,allocation_policy='id' if n=='id' else 'frequency'))
            for block in range(window_count):
                changed=(block==transient_block) if transient_block is not None else block!=0
                count=density*(2 if count_burst and changed else 1)
                if tail_shift:
                    prefix=[(3,0,0)]*8 if wide else hot[:8]
                    tail=([(3,0,0)] if not changed else [(3,63,2)]) if wide else [
                        c for c in hot if c[0]['category'] in
                        (('seen_path','unseen_path') if not changed else ('wrong_identity','crossed_roles'))]
                    cases=(prefix+[tail[i%len(tail)] for i in range(max(0,count-len(prefix)))])[:count]
                else:
                    cases=[hot[i%len(hot)] for i in range(density)]
                collected={}
                answers={}; trace={}
                for n in arms[(repeat+block)%len(arms):]+arms[:(repeat+block)%len(arms)]:
                    state=states[n]
                    if block==2:
                        _,cost=timed(lambda:train_events(state,[event(p,64) for p in range(4)] if wide else
                            training_episode(17,world,32),OPTIONS))
                        stats[n]['train'].append(cost)
                    if block==window_count-1:
                        first='0-0' if wide else f'train:{world}:17:0:0'
                        state.events_by_id[first].target=state.events_by_id[first].actor
                        g.invalidate_primitive_grounding(state)
                    if transient_block is not None or time_observer_setup:
                        setup_wall,setup_cpu=perf_counter(),process_time()
                    samples={}
                    original=g.actor_matches
                    collect=n in variants and block in calibration_blocks
                    sampler=None
                    schedule_cost={'cpu':0.,'wall':0.}
                    if n in schedules:
                        forced=pending.get(n,False)
                        sampler,schedule_cost=timed(lambda:schedules[n].next_window(force=forced))
                        collect=sampler is not None and block != window_count-1
                        trace[n]={'collected':collect}
                        if transient_block is not None:
                            trace[n].update(forced=forced,query_count=len(cases))
                    if collect and sample_configs is not None and n not in schedules:
                        sampler=(sample_factories or {}).get(n, GroundingSampleWindow)(**sample_configs[n])
                    if collect:
                        by_id={id(e):k for k,e in state._primitive_grounding_index['entries'].items()}
                        def recording(entry,ars,actor,target,trs,diagnostics=None):
                            key=by_id[id(entry)]
                            if sampler is not None:
                                sampler.observe(key,ars,actor,target,trs)
                            else:
                                bucket=samples.setdefault(key,[])
                                if len(bucket)<8:bucket.append((tuple(ars),actor,target,tuple(trs)))
                            return original(entry,ars,actor,target,trs,diagnostics)
                        g.actor_matches=recording
                    if transient_block is not None or time_observer_setup:
                        schedule_cost={'wall':perf_counter()-setup_wall,'cpu':process_time()-setup_cpu}
                    cleanup_cost={'wall':0.,'cpu':0.}
                    try:
                        answers[n],cost=timed(lambda:[ask(state,c) for c in cases])
                    finally:
                        if transient_block is not None or time_observer_setup:
                            cleanup_wall,cleanup_cpu=perf_counter(),process_time()
                        g.actor_matches=original
                        if transient_block is not None or time_observer_setup:
                            cleanup_cost={'wall':perf_counter()-cleanup_wall,'cpu':process_time()-cleanup_cpu}
                    for clock in ('cpu','wall'):cost[clock]+=schedule_cost[clock]+cleanup_cost[clock]
                    stats[n]['query'].append(cost)
                    if n in triggers:
                        pending[n],trigger_cost=timed(lambda:triggers[n].observe(len(cases),sampled=collect))
                        for clock in ('cpu','wall'):stats[n]['query'][-1][clock]+=trigger_cost[clock]
                        trace[n]['force_next']=pending[n]
                    if collect:
                        if sampler is not None:
                            samples,export_cost=timed(sampler.samples)
                            # Include snapshot construction in the charged collection cost.
                            for clock in ('cpu','wall'):stats[n]['query'][-1][clock]+=export_cost[clock]
                            stats[n]['sampler_heap'].append(collector_bytes(sampler._streams))
                            trace[n] = dict(**trace.get(n, {}), collector_exhausted=sampler.exhausted)
                            collected[n]=samples
                            retained[n]=samples
                        report=calibrate_grounding_benefits(state,samples,**variants[n])
                        stats[n]['calibration'].append(report)
                    moved,cost=timed(lambda:g.rebalance_primitive_grounding(state,
                        allocation_metric='benefit' if n in variants else 'frequency'))
                    stats[n]['rebalance'].append(cost)
                    stats[n]['promotions']+=moved['promotions']
                    ix=state._primitive_grounding_index
                    assert ix['lookup_bytes_used']<=budget
                    stats[n]['retained_heap_samples'].append(cache_heap(ix))
                    trace[n]=dict(**trace.get(n,{}),selected=sorted(k for k,e in ix['entries'].items() if e['lookup'] is not None),
                        used=ix['lookup_bytes_used'])
                if cadence_configs:
                    collected={n:retained.get(n,{}) for n in variants}
                if collected:
                    # Independent full stream outside timing: only the ID arm, which has no hit counters.
                    full={}; original=g.actor_matches
                    by_id={id(e):k for k,e in states['id']._primitive_grounding_index['entries'].items()}
                    def recording_full(entry,ars,actor,target,trs,diagnostics=None):
                        full.setdefault(by_id[id(entry)],[]).append((tuple(ars),actor,target,tuple(trs)))
                        return original(entry,ars,actor,target,trs,diagnostics)
                    g.actor_matches=recording_full
                    try:
                        audited=[ask(states['id'],c) for c in cases]
                    finally:g.actor_matches=original
                    assert audited==answers['id']
                    for name,sample in collected.items():
                        weighted=0.; accesses=sum(map(len,full.values()))
                        for key,stream in full.items():
                            truth=Counter(stream); estimate=Counter(sample.get(key,[]))
                            n=len(stream); m=sum(estimate.values())
                            tv=.5*sum(abs(truth[v]/n-estimate[v]/m) for v in truth.keys()|estimate.keys()) if m else 1.
                            weighted+=n*tv
                        trace[name]['sample_tv']=weighted/accesses if accesses else 0.
                        trace[name]['sample_digest']=hashlib.sha256(repr(sorted(sample.items())).encode()).hexdigest()
                expected=[ask(states['id'],c,False) for c in cases]
                assert all(a==expected for a in answers.values()); checks+=len(cases)
                # No future case or verification access is included in allocation counts.
                for c in panel:
                    expected_case=ask(states['id'],c,False)
                    for state in states.values():
                        ix=state._primitive_grounding_index
                        snapshot={k:e.get('query_hits',0) for k,e in ix['entries'].items()}
                        assert ask(state,c)==expected_case
                        for k,e in ix['entries'].items():
                            if 'query_hits' in e:e['query_hits']=snapshot[k]
                    checks+=1
                assert all(s.to_dict()==states['id'].to_dict() for s in states.values())
                trace['result_sha256']=hashlib.sha256(repr(expected).encode()).hexdigest()
                traces.append(trace)
            with TemporaryDirectory() as directory:
                saved=[]
                for n,state in states.items():
                    stats[n]['heap']=cache_heap(state._primitive_grounding_index)
                    path=Path(directory)/n
                    _,stats[n]['save']=timed(lambda:save_state(state,path))
                    saved.append((path/'state.json').read_bytes())
                    restored,stats[n]['load']=timed(lambda:load_state(path))
                    g.build_primitive_grounding(restored,total_lookup_budget_bytes=budget,
                        allocation_policy='id' if n=='id' else 'frequency')
                    for c in panel:
                        assert ask(restored,c)==ask(state,c,False);checks+=1
                assert len(set(saved))==1
            rows.append(dict(world=world,density=density,stats=stats,trace=traces,comparisons=checks,
                saved_sha256=hashlib.sha256(saved[0]).hexdigest(),saved_content_sha256=content_digest(saved[0])))
    return dict(hash_seed=os.environ.get('PYTHONHASHSEED'),repeat=repeat,rows=rows)


def audit(results):
    for world in ('independent','coupled','concentrated'):
        for density in (32,512):
            rows=[r for p in results for r in p['rows'] if r['world']==world and r['density']==density]
            assert len({r['saved_content_sha256'] for r in rows})==1
            assert len({json.dumps([t['result_sha256'] for t in r['trace']]) for r in rows})==1
    return dict(processes=results,results_and_saved_contents_equal=True,
                allocation_determinism_expected=False)


def run_processes(output):
    results=[]
    with TemporaryDirectory() as directory:
        for seed in (0,1,42):
            for repeat in range(3):
                path=Path(directory)/f'{seed}-{repeat}.json'
                subprocess.run([sys.executable,'-m','experiments.grounding_benefit_evaluation',
                    '--worker','--repeat',str(repeat),'--output',str(path)],check=True,
                    env={**os.environ,'PYTHONHASHSEED':str(seed)})
                results.append(json.loads(path.read_text()))
                Path(output).write_text(json.dumps(dict(processes=results),indent=2)+'\n')
                print(f'finished seed={seed} repeat={repeat}',flush=True)
    return audit(results)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true')
    p.add_argument('--repeat',type=int,default=0)
    p.add_argument('--output',default='docs/g3-grounding-benefit-results-2026-10-22.json')
    args=p.parse_args()
    result=run_worker(args.repeat) if args.worker else run_processes(args.output)
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
