"""Explicit cache correction pilot: reverse dependencies versus full rebuilding."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import platform
from time import process_time, perf_counter
from tempfile import TemporaryDirectory

from experiments.compositional_holdout import training_episode, heldout_cases
from experiments.compositional_grounding_costs import _query
from experiments.grounding_frequency_evaluation import event, query, OPTIONS
from experiments.grounding_lookup_evaluation import cache_heap
from experiments.grounding_payback_evaluation import timed, content_digest
from risa.core.state import RisaState
from risa.engine.runtime import train_events
from risa.engine.persistence import save_state, load_state
from risa.engine import primitive_grounding as g
from risa.engine.grounding_corrections import GroundingCorrectionTracker


def worker(order):
    results=[]
    for world in ('independent','coupled','concentrated'):
        base=RisaState()
        wide=world=='concentrated'
        source=[event(p,k) for p in range(4) for k in range(64)] if wide else [e for i in range(32) for e in training_episode(17,world,i)]
        train_events(base,source,OPTIONS)
        panel=[(p,k,v) for p in range(4) for k in (0,1,23,63) for v in range(3)] if wide else [(c,b) for c in heldout_cases(29,world) for b in (False,True)]
        def ask(state, case, indexed):
            return query(state,*case,indexed) if wide else _query(state,*case,indexed)
        snapshot=base.to_dict()
        for budget in (None,4096):
            states={n:RisaState.from_dict(deepcopy(snapshot)) for n in ('full','partial')}
            stats={n:dict(refresh=[],query=[],scan=[],save=[],load=[]) for n in states}
            replay=RisaState.from_dict(deepcopy(snapshot))
            tracker=None
            for n in ('full','partial')[::1 if order%2==0 else -1]:
                # Configure both arms identically before measured setup.
                states[n]._primitive_grounding_total_lookup_budget=budget
                states[n]._primitive_grounding_allocation_policy='frequency' if budget is not None else 'id'
                if n=='partial':
                    tracker,stats[n]['setup']=timed(lambda:GroundingCorrectionTracker(states[n]))
                else:
                    _,stats[n]['setup']=timed(lambda:g.build_primitive_grounding(states[n],total_lookup_budget_bytes=budget,allocation_policy='frequency' if budget is not None else 'id'))
            eid=sorted(base.events_by_id)[0]
            original=deepcopy(base.events_by_id[eid])
            manifest=[];checks=0;reports=[];digests=[];saved_digests=[];preparation=[]
            for step in ('noop','identity','roles','restore','wide','restore_all','unknown'):
                cpu, wall = process_time(), perf_counter()
                fields = ('actor_roles', 'target_roles', 'target')
                before = {key: {f: deepcopy(getattr(e, f)) for f in fields} for key,e in states['full'].events_by_id.items()}
                changed=[eid]
                for state in states.values():
                    if step=='noop': pass
                    elif step=='identity':state.events_by_id[eid].target=state.events_by_id[eid].actor
                    elif step=='roles':
                        state.events_by_id[eid].actor_roles=['new-role','joint-actor']
                        state.events_by_id[eid].target_roles=['new-target','joint-target']
                    elif step=='restore':state.events_by_id[eid]=deepcopy(original)
                    elif step=='wide':
                        changed=sorted(state.events_by_id)
                        for event_id in changed:state.events_by_id[event_id].target=state.events_by_id[event_id].actor
                    elif step=='restore_all':
                        changed=sorted(state.events_by_id)
                        state.events_by_id=deepcopy(base.events_by_id)
                edits = []
                for key,e in sorted(states['full'].events_by_id.items()):
                    for field in fields:
                        new = getattr(e, field)
                        if before[key][field] != new:
                            edits.append(dict(event_id=key, field=field, old=before[key][field], new=deepcopy(new)))
                manifest.append(dict(step=step,event_ids=changed,edits=edits))
                preparation.append(dict(cpu=process_time()-cpu,wall=perf_counter()-wall))
                for edit in edits:
                    target = replay.events_by_id[edit['event_id']]
                    assert getattr(target,edit['field']) == edit['old']
                    setattr(target,edit['field'],deepcopy(edit['new']))
                assert replay.to_dict() == states['full'].to_dict()
                for n in ('full','partial')[::1 if (order+len(manifest))%2==0 else -1]:
                    if n=='partial':
                        report,cost=timed(lambda:tracker.refresh(changed,dependencies_known=step!='unknown'))
                        reports.append(report)
                    else:
                        ix,cost=timed(lambda:g.build_primitive_grounding(states[n],total_lookup_budget_bytes=budget,allocation_policy='frequency' if budget is not None else 'id'))
                        cost['event_reads']=ix['build_event_reads']
                    stats[n]['refresh'].append(cost)
                    _,cost=timed(lambda:[ask(states[n],case,True) for case in panel])
                    stats[n]['query'].append(cost)
                    _,cost=timed(lambda:[ask(states[n],case,False) for case in panel])
                    stats[n]['scan'].append(cost)
                answers=[]
                for case in panel:
                    expected=ask(states['full'],case,False)
                    assert all(ask(state,case,True)==expected for state in states.values())
                    answers.append(repr(expected));checks+=1
                assert states['full'].to_dict()==states['partial'].to_dict()
                digests.append(hashlib.sha256(repr(answers).encode()).hexdigest())
                for state in states.values():
                    ix=state._primitive_grounding_index
                    assert budget is None or ix['lookup_bytes_used']<=budget
                with TemporaryDirectory() as directory:
                    saved=[]
                    for n,state in states.items():
                        path=Path(directory)/n
                        _,cost=timed(lambda:save_state(state,path));stats[n]['save'].append(cost)
                        saved.append((path/'state.json').read_bytes())
                        restored,cost=timed(lambda:load_state(path));stats[n]['load'].append(cost)
                        for case in panel:
                            assert ask(restored,case,True)==ask(state,case,False);checks+=1
                    assert saved[0]==saved[1]
                saved_digests.append(content_digest(saved[0]))
            auxiliary=sys.getsizeof(tracker.references)+cache_heap(dict(supports=tracker.supports,reverse=tracker.reverse))
            results.append(dict(world=world,budget=budget,stats=stats,reports=reports,comparisons=checks,
                auxiliary_bytes=auxiliary,manifest=manifest,preparation=preparation,manifest_bytes=len(json.dumps(manifest).encode()),result_digests=digests,
                input_digest=content_digest(json.dumps(snapshot).encode()),saved_digests=saved_digests))
    return dict(generator_version=1,python=platform.python_version(),rng='Python random.Random MT19937',training_seed=17,query_seed=29,source_digests={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in ('experiments/compositional_holdout.py','experiments/grounding_frequency_evaluation.py','experiments/grounding_correction_evaluation.py')},hash_seed=os.environ.get('PYTHONHASHSEED'),order=order,rows=results)


if __name__=='__main__':
    if len(sys.argv)>1:
        print(json.dumps(worker(int(sys.argv[1]))))
    else:
        runs=[]
        for seed in (0,1,42):
            for order in range(2):
                runs.append(json.loads(subprocess.check_output([sys.executable,'-m','experiments.grounding_correction_evaluation',str(order)],env={**os.environ,'PYTHONHASHSEED':str(seed)})))
                print(f'completed hash={seed} order={order}',flush=True)
        for world in ('independent','coupled','concentrated'):
            for budget in (None,4096):
                rows=[r for p in runs for r in p['rows'] if (r['world'],r['budget'])==(world,budget)]
                assert len({tuple(r['saved_digests']) for r in rows})==1
                assert len({tuple(r['result_digests']) for r in rows})==1
        Path('docs/g3-grounding-correction-results-2026-11-24.json').write_text(json.dumps(dict(processes=runs),indent=2)+'\n')
