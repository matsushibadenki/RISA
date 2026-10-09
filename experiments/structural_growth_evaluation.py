"""G3.4b induced-role/temporal growth pilot; no held-out-driven adoption."""
from collections import Counter
from dataclasses import replace
import argparse
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
from risa.core.models import Event, PredictionQuery
from risa.core.state import RisaState
from risa.engine.composer import compose_to_effect
from risa.engine.persistence import save_state, load_state
from risa.engine.predictor import predict_next_effect
from risa.engine.runtime import train_events, TrainingOptions


def validate_manifest(manifest):
    checkpoints=manifest['episode_checkpoints']
    if len(checkpoints)<3 or any(type(n) is not int or n<1 for n in checkpoints) or checkpoints!=sorted(set(checkpoints)):
        raise ValueError('three or more increasing positive episode checkpoints required')
    for key in ('episodes_per_chunk','cases_per_partition','replay_budget','worker_budget_seconds'):
        if type(manifest[key]) is not int or manifest[key]<1:
            raise ValueError(f'{key} must be a positive integer')
    if manifest['cases_per_partition']%6 or not manifest['seeds']:
        raise ValueError('balanced six-variant cases and nonempty seeds required')
    return manifest


def training_episode(seed,index):
    target=f'train-device-{seed}-{index}';episode=f'train-{seed}-{index}'
    effect,relation=('warm','powered_by') if index%2==0 else ('cold','cooled_by')
    common=dict(actor=f'train-actor-{index}',target=target,episode_id=episode,source=f'train-source-{index}',
                entity_bindings={'object':target,'provider':f'train-provider-{seed}-{index}'},
                entity_relations=[{'source':'object','relation':relation,'target':'provider'}],entity_relations_observed=True)
    return [Event(id=f'{episode}-inspect',timestamp=index*3+1,action='inspect',observed_effects=[effect],**common),
            Event(id=f'{episode}-charge',timestamp=index*3+2,action='charge',preconditions=['connected'],numeric_preconditions={'energy':2.0},state_variable_deltas={'energy':-1.0},observed_effects=['charged'],**common),
            Event(id=f'{episode}-activate',timestamp=index*3+3,action='activate',preconditions=['charged'],consumed_states=['charged'],numeric_preconditions={'energy':1.0},state_variable_deltas={'energy':-1.0},observed_effects=['online'],observed_states_before=['charged'],before_state_observed=True,**common)]


def heldout_cases(seed,partition,count):
    # Independent truth-table construction, not a call to training templates.
    variants=[('powered_by',False,['connected'],2.0,['warm'],True),
              ('cooled_by',False,['connected'],2.0,['cold'],True),
              ('powered_by',False,[],2.0,['warm'],False),
              ('powered_by',False,['connected'],1.0,['warm'],False),
              ('stored_in',False,['connected'],2.0,[],False),
              ('powered_by',True,['connected'],2.0,[],False)]
    cases=[]
    for i in range(count):
        relation,reverse,states,energy,effects,online=variants[i%6]
        target=f'{partition}-device-{seed}-{i}';actor=f'{partition}-actor-{seed}-{i}'
        query=PredictionQuery(actor=actor,action='inspect',target=target,
                              entity_bindings={'item':target,'counterpart':f'{partition}-provider-{seed}-{i}'},
                              entity_relations=[{'source':'counterpart' if reverse else 'item','relation':relation,'target':'item' if reverse else 'counterpart'}])
        kind=('powered','cooled','missing_state','low_energy','unsupported_relation','reverse_relation')[i%6]
        cases.append(dict(id=f'{partition}-{seed}-{i}',kind=kind,query=query,states=states,energy=energy,effects=effects,online=online))
    random.Random(f'{partition}:{seed}').shuffle(cases)
    return cases


def evaluate(state,cases):
    counts=Counter();outputs=[]
    for case in cases:
        q=case['query'];p=predict_next_effect(state,q);baseline=predict_next_effect(state,replace(q,enable_role_induction=False))
        results=[]
        for enabled in (True,False):
            result=compose_to_effect(state,'charge','online',start_states=case['states'],start_variables={'energy':case['energy']},max_steps=2,
                                     actor=q.actor,target=q.target,entity_bindings=q.entity_bindings,entity_relations=q.entity_relations,enable_candidate_concepts=enabled)
            results.append(result)
        counts['prediction_correct']+=p.predicted_effects==case['effects'];counts['no_induction_correct']+=baseline.predicted_effects==case['effects']
        for name,result in zip(('candidate_on','candidate_off'),results):
            success=bool(result.primitive_ids)
            counts[f'{name}_correct']+=success==case['online']
            counts[f'{name}_false_accepts']+=success and not case['online']
            if success and not case['online']:
                counts[f'{name}_false_accepts:{case["kind"]}']+=1
        outputs.append((p.to_dict(),baseline.to_dict(),results[0].to_dict(),results[1].to_dict()))
    return dict(cases=len(cases),invalid_cases=sum(not c['online'] for c in cases),**counts),outputs


def worker(manifest,seed,path):
    state=RisaState();rows=[];partitions={p:heldout_cases(seed,p,manifest['cases_per_partition']) for p in ('development','final')}
    old_bytes=old_events=episodes=0
    for checkpoint in manifest['episode_checkpoints']:
        for offset in range(episodes,checkpoint,manifest['episodes_per_chunk']):
            events=[event for i in range(offset,min(checkpoint,offset+manifest['episodes_per_chunk'])) for event in training_episode(seed,i)]
            train_events(state,events,TrainingOptions(replay_max_events=manifest['replay_budget']))
        episodes=checkpoint;snapshot=state.to_dict();metrics={};outputs={}
        for p,cases in partitions.items():metrics[p],outputs[p]=evaluate(state,cases)
        if state.to_dict()!=snapshot:raise AssertionError('held-out evaluation mutated state')
        with tempfile.TemporaryDirectory(prefix='risa-structural-growth-') as directory:
            save_state(state,directory);size=(Path(directory)/'state.json').stat().st_size;restored=load_state(directory)
            if any(evaluate(restored,cases)[1]!=outputs[p] for p,cases in partitions.items()):raise AssertionError('full prediction/composition reload mismatch')
        candidates=list(state.unnamed_concept_candidates.values());count=len(state.events_by_id)
        rows.append(dict(events=count,stored_bytes=size,bytes_per_event=size/count,marginal_bytes_per_event=(size-old_bytes)/(count-old_events),
                         active_primitives=sum(p.adopted for p in state.structural_primitives.values()),candidates=len(candidates),
                         adopted_candidates=sum(c.lifecycle_status=='adopted' for c in candidates),candidate_kinds=dict(Counter(c.structural_schema.get('kind','single_transition') for c in candidates)),
                         candidate_description_length_delta=sum(c.description_length_delta for c in candidates),metrics=metrics,reload_mismatches=0))
        old_bytes=size;old_events=count
        Path(path).write_text(json.dumps(dict(seed=seed,rows=rows,case_ids={p:[c['id'] for c in cases] for p,cases in partitions.items()})))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',default='experiments/g3_structural_growth_manifest.json');parser.add_argument('--output',default='docs/g3-structural-growth-results-2026-10-09.json');parser.add_argument('--worker',action='store_true');parser.add_argument('--seed',type=int)
    args=parser.parse_args();manifest=validate_manifest(json.loads(Path(args.manifest).read_text()))
    if args.worker:worker(manifest,args.seed,args.output);return
    runs=[]
    with tempfile.TemporaryDirectory(prefix='risa-structural-workers-') as directory:
        for seed in manifest['seeds']:
            path=Path(directory)/f'{seed}.json'
            try:
                done=subprocess.run([sys.executable,'-m','experiments.structural_growth_evaluation','--worker','--seed',str(seed),'--manifest',args.manifest,'--output',str(path)],capture_output=True,text=True,timeout=manifest['worker_budget_seconds'])
                status='complete' if done.returncode==0 else 'error';error=done.stderr[-4000:] if done.returncode else None
            except subprocess.TimeoutExpired:status='timeout';error=None
            run=json.loads(path.read_text()) if path.exists() else dict(seed=seed,rows=[]);run.update(status=status,error=error);runs.append(run)
            print(json.dumps(dict(seed=seed,status=status,error=error)),flush=True)
    Path(args.output).write_text(json.dumps(dict(manifest=manifest,manifest_sha256=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),runs=runs),indent=2,sort_keys=True)+'\n')

if __name__=='__main__':main()
