<p align="center">
  <img src="docs/images/logo_RISA.png" width="220" alt="RISA logo">
</p>

# RISA

**RISA** (Relationally Involving Self-organizing Architecture) is a Python research prototype for learning reusable structure from experience. It ingests structured events, builds a relational world model, discovers recurring transitions and candidate concepts, and uses that model for prediction and planning.

The central research hypothesis is that experience can **condense into reusable internal structure**. More experience should improve performance on unfamiliar problems without requiring storage and search work to grow in proportion to the event log. A concept, in this view, is a structure reused across many experiences, not a label supplied in advance.

RISA has a working structured-world core. It has **not** established a general advantage over strong baselines, demonstrated recursive concept formation, or shown end-to-end learning at 100,000 events. The current priority is to test which structural mechanisms actually help under change before adding new perception or execution layers.

## Current evidence

| Stage          | What was measured                                                                      | Result and limit                                                                                                                                                                                                                                                                                                                                                                                              |
| -------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| G1             | Synthetic control, composition, binding, uncertainty and A→B→A drift tasks             | Structural primitives support multi-step planning, but RISA tied the strongest applicable grounded-transition baseline on the main static tasks. The original B drift phase reached 33.3% success. [Report](docs/G1-Comparative-Evaluation-2026-09-08.md)                                                                                                                                                     |
| G2             | Targeted tests of learned applicability, role binding, candidate reuse and persistence | Several targeted ablations improved, including learned-precondition composition at 100% versus 0% and binding at 100% versus 75%. Supplied-precondition composition still tied the grounded table. These are task-specific results, not general superiority. [Structural reuse](docs/G2-Structural-Reuse-Evaluation-2026-09-08.md) · [Derived candidates](docs/G2-Derived-Candidate-Evaluation-2026-09-11.md) |
| G2.5–G2.6      | Roles induced from relation position and refined when outcomes conflict                | One-hop induced roles matched supplied roles on the reported tasks; targeted two-hop refinement improved prediction, composition and planning over restricted role conditions. [Structural roles](docs/G2-Structural-Role-Evaluation-2026-09-12.md) · [Role disambiguation](docs/G2-Role-Disambiguation-Evaluation-2026-09-13.md)                                                                             |
| G2 persistence | Full G2 states across five seeds                                                       | Schema v4 reduced mean serialized state from 134,478 to 102,287 bytes (23.94%) with no reported reload differences over 5,000 predictions and 2,250 plans, plus composition and simulation checks. The storage gap to simpler baselines remains. [Report](docs/G2-Persistence-Evaluation-2026-09-10.md)                                                                                                       |
| G3.1           | Indexed prediction access and bounded Replay selection at 1k, 10k and 100k events      | Indexed and full-scan `PredictionResult` payloads matched in all nine scale rows. Event-access work improved by at least 63.49× and p95 latency by at least 20.37×; Replay selection stayed within 128 events. The fixture did **not** execute full graph construction, online learning, candidate discovery or planning at 100k. [Report](docs/G3-Scale-Evaluation-2026-09-13.md)                            |
| G3.2          | Five-seed A→B→A mechanism, cue, readout, scope and label-budget controls                 | Development closed as a negative result: split/merge/dormancy did not beat strong context-subset tables on recovery or retention. A scope audit preserves unchanged scoped validation after broader-parent updates with zero labels and rejects 15/15 in-scope counterexample/role/lineage mutations. Full revalidation tied no-merge at 552/1,440 while using 8,000 more labels; the strong table scored 1,440/1,440 with zero labels. No independent final was spent because the preregistered development gate failed. [Decision report](docs/G3.2-Scope-Expiry-Audit-2026-10-05.md) |

G3.2 development controls now separate candidate lifecycle, unseen-context transfer and return-cue routing. Candidates support some unseen-context predictions, but strong context-subset tables perform better. In a role-free relational return control, default RISA adapts to B but has 0% immediate A-return accuracy; a shared two-hop role projection restores 100% return accuracy in both RISA and simple tables. This isolates an Event/query evidence-routing limitation, without establishing split/merge/dormancy benefit. Opt-in native two-hop readouts now restore 100% immediate return without supplied role labels, matching the strong tables; 720 complete prediction results agree after reload and full-scan reconstruction. This mode is configured before learning with `RisaState(target_role_readout_hops=2)`; the default remains depth one. An opt-in context-conditioned discovery policy now forms candidates in this fixture; query-backed independent adoption on disposable B copies improves partial nuisance transfer, with 400 labels counted per seed. This is not a measured drift benefit. [Discovery report](docs/G3.2-Context-Conditioned-Discovery-2026-10-03.md). A seven-arm online control with a shared 1,200-label cap now executes merge adoption and parent dormancy. Immediate transfer matches no-merge, then disappears as evidence updates invalidate adoption; strong subset tables retain correct answers without adoption labels. [Online ablation report](docs/G3.2-Role-Online-Ablation-2026-10-03.md). Opt-in reactivation of unchanged validated parents repairs a transient fallback gap after merge expiry (16/120 → 48/120 first-update A nuisance answers), without extra labels; A2 exit still fails and strong tables remain better. [Reactivation report](docs/G3.2-Orphaned-Dormancy-2026-10-03.md). A fixed-budget revalidation control increases pre-update nuisance correctness to 552/1,440, but no-merge matches that result using fewer labels (14,000 versus 22,000 across five seeds); strong subset tables score 1,440 without adoption labels. [Revalidation cost report](docs/G3.2-Revalidation-Budget-2026-10-05.md). No independent G3.2 final evaluation has run. See the [relational cue report](docs/G3.2-Relational-Return-Cue-2026-10-03.md), [G3.2 protocol](docs/G3.2-Drift-Protocol.md) and [current roadmap](docs/ROADMAP.md).

## How RISA works

1. **Events and graph.** A structured `Event` records actors, actions, targets, context, observed effects, relations and optional before-state information. Ingestion adds evidence-bearing nodes and edges to the graph.
2. **Learning and structural reuse.** RISA learns outcome counts, shared patterns, transition Primitives, role signatures, applicability conditions and unnamed concept candidates from repeated evidence. Candidate promotion uses disjoint development and final evidence.
3. **Prediction and adaptation.** Predictions return effects, scores, evidence IDs and structural paths. Pre-update validation, bounded Replay and change hypotheses can update the model. Context splitting, candidate merging and dormancy exist, but their causal value under drift is still unproven.
4. **Planning.** Forecasting, branch simulation, goal evaluation and counterfactual planning use the learned model. The planner supports state and numeric constraints, AND/OR goal decomposition, partial-order execution and threat diagnostics. Planning quality must be evaluated separately from world-model quality.
5. **Persistence.** The state uses schema v6, which persists the optional candidate role-refinement policy and target-role readout depth and migrates older states with the depth-one default. Rebuildable readout indexes are derived from Events on load; compact graph and candidate records preserve the evidence and evaluation state needed for reconstruction.

RISA currently accepts **structured JSON events**. Natural language, image and audio perception are outside this core. Planned neural, SNN, logic-gate and hardware paths are conditional on evidence that structural learning itself works.

## Repository layout

| Path               | Purpose                                                                      |
| ------------------ | ---------------------------------------------------------------------------- |
| `risa/core/`       | Event, graph, candidate and state models                                     |
| `risa/engine/`     | Ingestion, learning, discovery, prediction, Replay, planning and persistence |
| `risa/evaluation/` | Benchmark models and G3.2 measurement helpers                                |
| `risa/cli/`        | Command-line interface                                                       |
| `experiments/`     | Versioned manifests and reproducible experiment runners                      |
| `docs/`            | Roadmap, protocols, reports and machine-readable results                     |
| `data/`            | Small structured-world examples                                              |
| `tests/`           | Regression tests                                                             |

## Quick start

Requires Python 3.10 or newer. Run these commands from the repository root:

```bash
python3 -m risa.cli.main train data/toy_world.json --state-dir /tmp/risa-toy
python3 -m risa.cli.main predict --actor wolf --action run --state-dir /tmp/risa-toy
python3 -m pytest -q
```

The `wolf run` example is a smoke check: action frequency can produce the same answer. It does not establish structural generalization.

To inspect stateful branches and constraints:

```bash
python3 -m risa.cli.main train data/branching_world.json --state-dir /tmp/risa-branch
python3 -m risa.cli.main simulate --start-action route \
  --start-variable energy=5 --max-steps 2 --max-branches 4 \
  --state-dir /tmp/risa-branch
python3 -m risa.cli.main evaluate --start-action route \
  --require-state safe_path --forbid-state fast_path \
  --start-variable energy=5 --max-steps 2 \
  --state-dir /tmp/risa-branch
```

The CLI also provides `inspect`, `forecast`, `compose` and `plan`. Run `python3 -m risa.cli.main --help` or a subcommand's `--help` for options. Examples for conjunction, disjunction and nested AND/OR plans are in `data/`.

## Reproduce the research checks

```bash
python3 -m experiments.comparative_evaluation \
  --manifest experiments/g1_manifest.json --output /tmp/g1-results.json
python3 -m experiments.scale_evaluation \
  --manifest experiments/g3_scale_manifest.json --output /tmp/g3-scale-results.json
python3 -m experiments.g3_drift_preflight \
  --manifest experiments/g3_drift_preflight_manifest.json \
  --output /tmp/g3-drift-preflight-results.json
python3 -m experiments.g3_lifecycle_readiness \
  --manifest experiments/g3_lifecycle_readiness_manifest.json \
  --output /tmp/g3-lifecycle-readiness-results.json
python3 -m experiments.g3_drift_candidate_primed \
  --manifest experiments/g3_drift_candidate_primed_manifest.json \
  --output /tmp/g3-drift-candidate-primed-results.json
```

The G3.2 preflights are **development diagnostics**. Their expected opportunity-gate result is `fail`; neither substitutes for an independent final experiment. The lifecycle pilot shows that validated specialized parents can become dormant after a validated merge. The candidate-primed drift preflight shows that this validation disappears during B observations. Postphase re-adoption needs new labels, and dynamic rediscovery needs more A2 Events. None of these diagnostics demonstrates a drift benefit. G3.1's 100k full-scan reference can take substantially longer than the other checks. The committed result artifacts and their manifests are linked from the corresponding reports.

To profile the actual training-to-persistence path with fixed per-scale budgets:

```bash
python3 -m experiments.end_to_end_scale_evaluation \
  --manifest experiments/g3_end_to_end_manifest.json \
  --output /tmp/g3-end-to-end-results.json
```

A time-limited scale reports `scale_gate_incomplete`, with the last completed chunk and process wall time. It does not count as a completed large-scale run.

State files use compact JSON by default. The schema and values are unchanged; Python callers can use `save_state(state, path, pretty=True)` for the previous readable formatting. Measured save work and output size are lower; see the [optimization report](docs/Software-Optimization-2026-10-07.md) for before/after results and limitations.

## Roadmap

- [Done] G0–G2.6: structured-event semantics, targeted comparisons, candidate lifecycle, induced roles and persistence checks.
- [Done] G3.1: indexed prediction access and bounded Replay selection measured through 100k synthetic events.
- [Done] G3.2 groundwork: mechanism switches, drift metrics, online runner, probe-backed candidate adoption, and separate pilots that exercise split and merge/dormancy switches. The combined drift fixture still lacks these opportunities.
- [Done] G3.2: closed the drift-development cycle as a documented negative result; the independent final set remains unused.
- [Done] G3.3 profiling runner: real training stages, bounded subprocesses, planning, compaction and save/load checks; chronological change detection now avoids full-history sorting. [Protocol](docs/G3.3-End-to-End-Protocol.md).
- [Done] G3.3 initial capacity diagnostic: 1k completes with 12/12 correct predictions and exact reload results; 10k/100k exceed the fixed budget at a 4k completed checkpoint. [Report](docs/G3.3-End-to-End-Evaluation-2026-10-07.md).
- [Done] G3.3: optimized prediction, metabolism and learning complete 1k/10k/100k under the unchanged 45-second cap, in 0.274/2.781/40.314 seconds. All scales have 12/12 correct predictions and exact compaction/reload results; 18 persisted checkpoints match frozen Git functions. [Report](docs/G3.3-Incremental-Scale-Evaluation-2026-10-07.md).
- [Later] 1M capacity: review the 2.045GiB peak RSS at 100k and persistence costs first.
- [Next] G3.4: measure structure growth, description length, storage per event, candidate generation and planner work per query.
- [Later] G4: test second-generation concepts, self-formed hierarchy and transfer to a new small world using lineage-disjoint held-out evidence.

The long-term test is whether more experience produces more reusable structure, lower marginal storage and search cost, and higher success on unseen problems **at the same time**. If structure counts and costs grow roughly with the event log while only accuracy improves, the condensation hypothesis needs revision. The [roadmap](docs/ROADMAP.md) defines the evidence gates and later research options.

## Documentation

- [Roadmap](docs/ROADMAP.md)
- [G3.2 drift protocol](docs/G3.2-Drift-Protocol.md) and [preflight report](docs/G3.2-Drift-Preflight-2026-09-16.md)
- [G3.1 scale report](docs/G3-Scale-Evaluation-2026-09-13.md)
- [G2 structural reuse](docs/G2-Structural-Reuse-Evaluation-2026-09-08.md), [derived candidates](docs/G2-Derived-Candidate-Evaluation-2026-09-11.md), [context conjunctions](docs/G2-Context-Conjunction-Evaluation-2026-09-12.md), [persistence](docs/G2-Persistence-Evaluation-2026-09-10.md)
- [G1 comparative evaluation](docs/G1-Comparative-Evaluation-2026-09-08.md)
- [MVP technical design](docs/RISA-MVP-1-Technical-Design.md) and [concept condensation notes](docs/RISA-Undivided-Knowledge-and-Concept-Condensation.md)

## License

MIT License.

Event persistence now filters omitted defaults before recursive copying while preserving saved bytes. 日本語: Event保存時の不要な既定値コピーを削減し、保存バイト列を維持します。简体中文: Event保存前排除无需保存的默认字段，保持保存字节不变。[Measured results / 計測結果 / 测量结果](docs/Event-Export-Optimization-2026-10-07.md).

Prediction index rebuilding now bounds duplicate-list scans for large effect buckets and reuses per-Event role/key work. 日本語: 大きな効果バケットの重複確認とEventごとの役割・キー再計算を削減します。简体中文: 减少大型效果桶的重复检查及每Event角色与键的重复计算。[Results and measured tradeoffs / 結果と交換条件 / 结果与实测成本](docs/Index-Reconstruction-Optimization-2026-10-07.md).

Graph restoration shares repeated immutable context tuples with a bounded temporary pool. 日本語: Graph復元で不変context tupleを共有し、保持メモリと読み込み・保存時間を削減します。简体中文: Graph恢复使用有上限的临时池共享不可变context元组，减少保留内存及加载、保存时间。[Measurements, cache audit and limitations / 計測・cache監査・制限 / 测量、缓存审计及限制](docs/Graph-Restoration-Optimization-2026-10-07.md).

Clean Replay now shares the effects-only prediction path and avoids unused provenance construction. 日本語: Replayの正誤判定では不要な出典生成を省き、公開予測の出典は維持します。简体中文: Replay正误判断省略未使用的来源生成，公开预测仍保留来源。[Measurements and Pending conditions / 計測と保留条件 / 测量及暂缓条件](docs/Replay-Optimization-2026-10-08.md).

学習履歴の選択処理を最適化しました。測定結果と単一episodeでの負荷増は[評価報告](docs/History-Setup-Optimization-2026-10-08.md)に記載しています。

English: Training history selection now avoids unused sorting/grouping; the report includes measured gains and the single-episode cost.

简体中文: 学习历史选择减少无用排序与分组；报告记录收益及单episode开销。
