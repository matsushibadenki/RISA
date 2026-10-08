# Replay optimization and remaining verification — 2026-10-08

日本語: [Done] Replayの正誤判定で使わない説明・出典の生成を省略した。同じ予測選択ルールを持つ既存の軽量経路を使う。Event復元時のコピー削減案は、効果が安定しなかったため撤回した。[Pending] 実運用corpusと、現在の権限で実行できないネイティブ累積allocation計測、および直接電力測定を保留する。

English: [Done] Replay skips explanation/provenance construction that its correctness check never consumes, using the existing effects-only path with identical selection rules. Revert the Event-restoration copy trial because improvements were inconsistent. [Pending] Deployment corpus, native cumulative-allocation measurements unavailable under current permissions, and direct energy measurements.

简体中文: [Done] Replay正误判断不再生成未使用的解释和来源，使用预测选择规则相同的现有效果专用路径。Event恢复复制优化因收益不稳定而撤回。[Pending] 实际运行语料、当前权限下无法执行的原生累计分配测量，以及直接能耗测量暂缓。

## Retained change

| Required field | Result |
| --- | --- |
| Problem | Clean Replay requests a full `PredictionResult` but consumes only `predicted_effects`. |
| Root cause | Public prediction constructs supporting paths, gathers/sorts evidence IDs and formats explanation even when Replay never reads them. |
| Evidence | Separate 10k profile: 0.01788s Replay, 0.0145s prediction, 0.0050s evidence lookup, 0.0042s Event supporting paths. Nested times overlap; instrumentation is not normal latency. |
| Changed files | `risa/engine/replay.py`, paired benchmark harness and frozen reference, regression tests, documentation. |
| Change | Use existing `predict_effects_for_validation` for clean Replay's equality check. Leave deployment forecasting, perturbations, adoption, contextual split proposals and public prediction unchanged. |
| Why | Remove work whose output is unused. No new cache, thread, schema or approximation. |
| Before / After | 10k trained Events, Replay bound 32: median 9.995→2.997ms (70.0% reduction), empirical p95/p99/max 20.541→5.258ms. Nine alternating pairs, fresh processes, no simultaneous benchmark workers. |
| CPU impact | 10k median 9.989→2.680ms. Profile calls 26,111→19,987; provenance assembly is skipped. |
| GPU impact | Not applicable to this synchronous CLI. |
| Memory impact | Separate 10k traced peak 103,906→90,604 bytes. Overall RSS is dominated by input state, approximately 158MB in both cases; no large RSS reduction claimed. |
| I/O impact | No new I/O and no persisted representation change. |
| Energy impact | Reduced CPU work is a proxy; no joules measured. Timed-operation context switches are recorded in raw results. |
| Correctness verification | Every measured Replay summary and complete persistence snapshot match frozen-reference Replay. Regression cases compare bounded/unbounded/zero Replay, both role depths, drift failures, contextual split mode, post-Replay full predictions and adoption/candidate counters. Public prediction still exposes evidence. |
| Regression risk | Internal effects-only selection must remain identical to public selection. Existing shared implementation and explicit equivalence tests enforce this. No clean Replay consumer reads score or provenance. |
| Keep / Revert | Keep. |

Raw measurements: [10k](replay-optimization-results-2026-10-08.json), [1k](replay-medium-results-2026-10-08.json), [four-Event example](replay-small-results-2026-10-08.json). The fixture is produced with real `train_events`, but uses synthetic bounded vocabulary. It does not establish independent held-out scientific quality. Separate instrumented samples do not enter timing summaries. Small sample tail estimates are empirical order statistics, not production guarantees.

The four-Event repository example uses 25 pairs: median 0.295→0.238ms (19.4% reduction), p95 0.315→0.252ms, maximum 0.333→0.256ms. Actual absolute latency is small; do not exaggerate its user impact.

## Reverted Event-copy trial

| Required field | Result |
| --- | --- |
| Problem / root cause | Each compact Event record is shallow-copied and given an explicit empty specs mapping before construction. |
| Evidence | Baseline cold-load profile includes full Event hydration inside state reconstruction. Copying is real work, but graph reconstruction, JSON decoding and derived indexes remain larger costs. |
| Changed files / change | Trial added a six-line fast path to `state.py` for plain dictionaries without explicit IDs/specs. Source code is restored after the comparison. Frozen state parser and compatibility tests remain. |
| Why | Avoid an extra record dictionary clone and empty comprehension. |
| Before / After | Nine paired samples: load wall median 0.650→0.800s, fresh save 1.004→0.905s, overwrite 1.267→1.070s. Broad variation prevents consistent attribution to this small branch. |
| CPU impact | Load 0.500→0.480s, fresh save 0.851→0.863s, overwrite 1.257→1.067s; no consistent gain across operations. |
| GPU / I/O | No GPU work; paired saved-file hashes and state snapshots match. |
| Memory / energy | No established practical memory improvement; no direct energy measurement. |
| Correctness / risk | Compatibility cases cover schema versions 1/4/6, omitted and explicit IDs/specs, pair-list records, default isolation, input aliases and malformed records. The branch adds format-dependent complexity. |
| Keep / Revert | Revert. Revisit only if future profiles justify Event hydration work. |

[Raw Event trial](event-restoration-results-2026-10-08.json). This report marks the trial evaluated, not Event restoration optimized. The experimental baseline mode in the graph harness holds graph reconstruction fixed and compares the frozen pre-trial state parser.

## Pending conditions

- [Pending] Actual deployment-corpus testing: repository `data/` contains example worlds/interventions, not a provided deployment dataset. Resume when such a corpus is available.
- [Pending] Native cumulative allocation/copy telemetry: `xctrace help` works, but `xctrace list templates` aborts before recording because Instruments cannot create its cache under `~/Library/Caches/com.apple.dt.InstrumentsCLI/path_manager` within the current filesystem permissions. No recording was performed. Memray is not installed. Resume in an authorized profiling environment; current tracemalloc peaks/live blocks must not be called cumulative allocations.
- [Pending] Direct process-energy measurement: no calibrated per-process joule measurement is configured. `powermetrics` advertises an energy-impact proxy, which is not a direct joule count. Resume with suitable instrumentation and attribution.
- [Later] Million-Event capacity review and additional synthetic tail sampling. A 100k checkpoint does not prove 1M capacity.
- [Next] Remaining learning/discovery/planning costs and G3.4 independent held-out quality versus structural/storage/search growth. These can be evaluated in development and are not Pending.

日本語: 保留は「未実装だから」ではなく、必要なデータ・計測条件を現在の開発環境で満たせない項目に限る。開発環境で検証可能な残作業は[Next]/[Later]を維持する。

English: Pending denotes missing data or measurement conditions in the current development environment, not ordinary unfinished implementation. Keep testable unfinished work Next/Later.

简体中文: Pending仅表示当前开发环境缺少数据或测量条件，不表示普通未完成实现。可以在开发环境验证的剩余工作仍使用Next/Later。

## Reproduction

```sh
python3 -m experiments.persistence_optimization --prepare --scales 0 1000 10000
python3 -m experiments.replay_optimization --output /tmp/replay-10k.json
python3 -m experiments.replay_optimization --fixture /tmp/risa-optimization-fixtures/1000 --output /tmp/replay-1k.json
python3 -m experiments.replay_optimization --fixture /tmp/risa-optimization-fixtures/examples --samples 25 --output /tmp/replay-small.json
python3 -m pytest -q
```

## Regression checks and scale measurements

All 238 tests pass (25.25 seconds). The current interpreter reports `Py_DEBUG=False`; timings use normal execution without profiling, and instrumented allocations/calls use separate workers.

| Stored Events | Replay bound | Before median | After median | Reduction | Before/after p95 | Before/after maximum |
| --- | --- | --- | --- | --- | --- | --- |
| 4 | min(32, Events) | 0.295ms | 0.238ms | 19.4% | 0.315/0.252ms | 0.333/0.256ms |
| 1,000 | min(32, Events) | 2.400ms | 1.619ms | 32.5% | 3.099/1.690ms | 3.099/1.690ms |
| 10,000 | min(32, Events) | 9.995ms | 2.997ms | 70.0% | 20.541/5.258ms | 20.541/5.258ms |

Nine medium/large pairs and 25 small pairs preserve exact Replay summaries and snapshot hashes; all separate instrumented runs also match the reference. Deployment and perturbation Replay remain enabled and their counters are included in equality checks.

## Full-pipeline verification and unresolved tail stability

[First run](g3-end-to-end-replay-results-2026-10-08.json): 1k and 10k complete correctly; 100k finishes training but exceeds the unchanged 45-second process budget during save. The last completed checkpoint reports 100,000 ingested Events. Unfinished save/load work is excluded from checkpoint stage totals. This is a failed budget check, not a completed run.

[Same-condition retry](g3-end-to-end-replay-retry-results-2026-10-08.json) is `profile_complete`:

| Events | Worker wall | Replay stage | Correct predictions | Reload/compaction differences |
| --- | --- | --- | --- | --- |
| 1,000 | 0.268s | 0.001537s | 12/12 | 0/0 |
| 10,000 | 2.889s | 0.015239s | 12/12 | 0/0 |
| 100,000 | 43.438s | 0.229562s | 12/12 | 0/0 |

Keep the first failure and retry; do not pick the successful result as proof of stable tails. Unchanged training stages also varied substantially from earlier runs, so the precise cause of full-path variation is unresolved. A paired microbenchmark isolates the Replay change, but the full-path observations do not establish an end-to-end speedup. [Next] Investigate and stabilize the 100k budget/tail margin in development. It is testable and therefore is not Pending. No threshold was relaxed and no additional retries were performed.

These are bounded-vocabulary synthetic runs with zero candidate concepts; compaction is a no-op. They do not establish semantic condensation, transfer or G3.4 held-out quality. Million-Event work remains deferred for capacity review.

日本語: 初回の10万Eventは保存中に45秒を超過。同条件の再測定は43.438秒で完了し、各規模12/12正解・復元差0。失敗も残し、tailの安定性や全工程の高速化を実証したとは扱わない。[Next] 10万Eventの予算・tail安定化。

English: The first 100k run times out during save; the same-condition retry completes in 43.438s, with all scales 12/12 correct and zero restore differences. Retain both outcomes; stable tails or whole-pipeline speedup are not established. [Next] 100k budget/tail stability.

简体中文: 首次10万Event在保存时超过45秒；同条件重测43.438秒完成，每组12/12正确且恢复差异为零。保留两次结果，不能证明尾延迟稳定或完整流程加速。[Next] 10万Event预算与尾延迟稳定性。
