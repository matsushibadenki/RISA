"""Fixed G3.4 exploratory growth/novel-entity transfer pilot."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
from time import perf_counter
from risa.core.models import Event, GoalSpecification, PredictionQuery
from risa.core.state import RisaState
from risa.engine.persistence import save_state, load_state
from risa.engine.planner import plan_counterfactuals
from risa.engine.predictor import predict_next_effect
from risa.engine.runtime import train_events, TrainingOptions


def validate_manifest(manifest):
    checkpoints=manifest['event_checkpoints']
    if len(checkpoints)<3 or any(type(n) is not int or n<1 for n in checkpoints) or checkpoints!=sorted(set(checkpoints)):
        raise ValueError('at least three increasing positive checkpoints required')
    for key in ('chunk_size','replay_budget','worker_budget_seconds','cases_per_partition'):
        if type(manifest[key]) is not int or manifest[key]<1:
            raise ValueError(f'{key} must be a positive integer')
    if manifest['cases_per_partition']%3 or not manifest['seeds']:
        raise ValueError('balanced three-role cases and nonempty seeds required')
    return manifest


def joint_signal(rows, manifest):
    first,last=rows[0],rows[-1]
    metrics=last['metrics']['final']
    return dict(prediction_gain_pass=metrics['accuracy']-metrics['no_role_accuracy']>=manifest['minimum_prediction_gain'],
                false_generalization_pass=metrics['false_generalization_rate']-metrics['no_role_false_generalization_rate']<=manifest['maximum_false_generalization_delta'],
                active_growth_pass=last['active_structures']>first['active_structures'],
                marginal_bytes_pass=last['marginal_bytes_per_event']<=rows[1]['marginal_bytes_per_event']*(1-manifest['minimum_marginal_bytes_reduction']))


def cases(seed, partition, count):
    rng=random.Random(seed+(100000 if partition=='development' else 200000))
    result=[]
    for i in range(count):
        role=i%3
        query=PredictionQuery(actor=f'{partition}-actor-{seed}-{i}',action='operate',
                              target=f'{partition}-target-{seed}-{i}',target_roles=[f'role-{role}'],
                              context_tags=[f'context-{rng.randrange(2)}'])
        result.append((f'{partition}-{seed}-{i}',query,[f'effect-{role}'] if role<2 else []))
    return result


def score(state, queries):
    successes=baseline=negative=baseline_negative=0
    predictions=[]
    for _,query,expected in queries:
        effects=predict_next_effect(state,query).predicted_effects
        no_roles=predict_next_effect(state,replace(query,target_roles=[])).predicted_effects
        successes+=effects==expected;baseline+=no_roles==expected
        if not expected:
            negative+=bool(effects);baseline_negative+=bool(no_roles)
        predictions.append(effects)
    negatives=sum(not expected for _,_,expected in queries)
    return dict(accuracy=successes/len(queries),no_role_accuracy=baseline/len(queries),
                false_generalization_rate=negative/negatives,no_role_false_generalization_rate=baseline_negative/negatives),predictions


def worker(manifest,seed,path):
    rng=random.Random(seed);state=RisaState(target_role_readout_hops=2)
    partitions={name:cases(seed,name,manifest['cases_per_partition']) for name in ('development','final')}
    rows=[];previous_bytes=previous_events=0;started=perf_counter()
    for checkpoint in manifest['event_checkpoints']:
        for offset in range(len(state.events_by_id),checkpoint,manifest['chunk_size']):
            events=[]
            for i in range(offset,min(checkpoint,offset+manifest['chunk_size'])):
                role=rng.randrange(2)
                events.append(Event(id=f'train-{seed}-{i}',timestamp=i+1,actor=f'train-actor-{i%3}',action='operate',
                                    target=f'train-target-{i}',target_roles=[f'role-{role}'],observed_effects=[f'effect-{role}'],
                                    context_tags=[f'context-{rng.randrange(2)}'],episode_id=f'train-episode-{seed}-{i//4}'))
            train_events(state,events,TrainingOptions(replay_max_events=manifest['replay_budget']))
        initial=state.to_dict();metrics={};predictions={}
        for name,queries in partitions.items():metrics[name],predictions[name]=score(state,queries)
        planner=plan_counterfactuals(state,'operate',GoalSpecification(required_states=['effect-0']),[],max_steps=2)
        if state.to_dict()!=initial:raise AssertionError('evaluation mutated learned state')
        with tempfile.TemporaryDirectory(prefix='risa-growth-') as directory:
            save_state(state,directory);size=(Path(directory)/'state.json').stat().st_size
            restored=load_state(directory)
            mismatches=sum(score(restored,partitions[name])[1]!=predictions[name] for name in partitions)
            if mismatches:raise AssertionError('reload effects differ')
        row=dict(seed=seed,events=checkpoint,stored_bytes=size,bytes_per_event=size/checkpoint,
                 marginal_bytes_per_event=(size-previous_bytes)/(checkpoint-previous_events),
                 active_structures=sum(p.adopted for p in state.structural_primitives.values()),
                 candidates=len(state.unnamed_concept_candidates),
                 active_candidates=sum(not c.dormant for c in state.unnamed_concept_candidates.values()),
                 candidate_description_length_delta=sum(c.description_length_delta for c in state.unnamed_concept_candidates.values()),
                 planner_expanded_candidates=sum(o.evaluation.search_diagnostics.get('expanded_candidate_count',0) for o in planner.outcomes),
                 metrics=metrics,reload_mismatches=mismatches,elapsed_seconds=perf_counter()-started)
        rows.append(row);previous_bytes=size;previous_events=checkpoint
        Path(path).write_text(json.dumps(dict(seed=seed,rows=rows,case_ids={name:[c[0] for c in queries] for name,queries in partitions.items()})))
    return dict(seed=seed,rows=rows,case_ids={name:[c[0] for c in queries] for name,queries in partitions.items()})


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',default='experiments/g3_growth_manifest.json')
    p.add_argument('--output',default='docs/g3-growth-pilot-results-2026-10-09.json');p.add_argument('--worker',action='store_true');p.add_argument('--seed',type=int)
    args=p.parse_args();manifest=validate_manifest(json.loads(Path(args.manifest).read_text()))
    if args.worker:worker(manifest,args.seed,args.output);return
    runs=[]
    with tempfile.TemporaryDirectory(prefix='risa-growth-workers-') as directory:
        for seed in manifest['seeds']:
            progress=Path(directory)/f'{seed}.json'
            try:
                completed=subprocess.run([sys.executable,'-m','experiments.growth_evaluation','--worker','--seed',str(seed),'--manifest',args.manifest,'--output',str(progress)],capture_output=True,text=True,timeout=manifest['worker_budget_seconds'])
                status='complete' if completed.returncode==0 else 'error'
                error=completed.stderr[-4000:] if completed.returncode else None
            except subprocess.TimeoutExpired:status='timeout';error=None
            run=json.loads(progress.read_text()) if progress.exists() else dict(seed=seed,rows=[])
            run.update(status=status,error=error);runs.append(run)
            if status=='complete':
                run['joint_signal']=joint_signal(run['rows'],manifest)
            print(json.dumps(dict(seed=seed,status=status)),flush=True)
    result=dict(manifest=manifest,manifest_sha256=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),runs=runs,
                note='Exploratory supplied-role synthetic pilot; no parameter tuning. No scientific quality or condensation acceptance from this pilot alone.')
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':main()
