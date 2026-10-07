# Prediction index reconstruction — 2026-10-07

日本語: [Done] 保存前検証とCLI読み込みの再構築コストを調査し、予測索引の大きな効果バケットで発生する線形の重複確認を削減した。異なる効果が多い1万Eventの単独索引再構築中央値は2.848→0.074秒（約38.5倍）。一時メモリは約2.1MB増える。通常の少語彙データに同程度の改善があるとは主張しない。完全な保存前検証、移行、候補復元と破損復旧は維持した。

English: [Done] Profiled reconstruction in pre-save validation and CLI loading, then reduced linear duplicate checks in large prediction-index effect buckets. Isolated reconstruction for 10k high-diversity Events improved from 2.848 to 0.074 seconds median (about 38.5×). Temporary memory increases by approximately 2.1 MB. This does not establish equivalent gains on bounded-vocabulary workloads. Full pre-save validation, migrations, candidate restoration and corruption recovery remain in place.

简体中文: [Done] 分析保存前验证和CLI加载的重建成本，减少预测索引大型效果桶中的线性重复检查。1万高多样性Event的单独索引重建中位数从2.848降至0.074秒（约38.5倍）。临时内存增加约2.1MB。不能推断少词汇数据也有同样收益。完整保存前验证、迁移、候选恢复及损坏恢复均保留。

## Measured change

| Reporting field | Evidence / decision |
| --- | --- |
| Problem | Prediction index reconstruction linearly searched ordered activation lists once per effect. Multiple effects also repeated role resolution and key construction. |
| Root cause | An activation bucket with an increasing number of distinct effects makes repeated `effect not in values` checks quadratic. |
| Evidence | Before: separately profiled diverse-index rebuild took 2.958 seconds, including 2.614 seconds self time in the rebuild loop. This is an instrumented diagnostic, not a normal latency estimate. |
| Changed files | `risa/engine/prediction_indexes.py`, `experiments/reconstruction_optimization.py`, `experiments/persistence_optimization.py`, frozen reference index builder, regression tests and documentation. |
| Change | Buckets shorter than 16 retain list membership. Larger buckets get a local set for duplicate checks. Lists still preserve chronological first-seen order. Compute role scopes and key strings once per Event, then reuse across its effects. |
| Why | Bound list probes on small buckets and use average constant-time membership on large buckets. The threshold limits linear scans; it is not claimed to be a universally optimal tuning value. |
| Before / After | Seven independent processes per case. Diverse index median 2.848384→0.073963 seconds; maximum/p95/p99 5.740192→0.079693 seconds. Cold loading the real trained bounded-vocabulary 10k fixture: median 0.317863→0.299761 seconds, but maximum/p95/p99 worsened 0.355916→0.405259 seconds. No stable overall loading gain is established. |
| CPU | Diverse-index median CPU 2.815071→0.073918 seconds. Cold-load CPU 0.316799→0.299525 seconds. Separately profiled diverse-index call counts 1,780,026→1,689,810; role resolution calls decrease from three per Event to one for this three-effect workload. |
| GPU | Not applicable. |
| Memory | Diverse-index traced peak 3,203,989→5,304,450 bytes (+2.10 MB); max process RSS 49.17→51.35 MB. Cold-load traced peak stays approximately 93.15 MB. The optimization trades temporary memory for lower CPU; it does not reduce memory. |
| I/O | No new persisted fields, file reads, services or writes. Persistence encoder, atomic write and backup logic are unchanged. |
| Energy | CPU time is a proxy only. No direct energy measurement. |
| Correctness | All 208 tests pass. All eight reconstructed indexes compare exactly with the frozen pre-change implementation in every measured process, including instrumented runs. Regression tests cover multi-effect Events, duplicates, empty effects, shuffled timestamps, both role depths, normalized labels, full predictions and rebuilding after replacing the Event corpus. |
| Risk | A set exists only during rebuilding, and only for buckets that reach 16 effects. High-diversity inputs use extra temporary memory. Ordered lists remain the public representation. |
| Keep / Revert | Keep the bounded-probe implementation for the demonstrated diversity-dependent hotspot. The initial prototype looked up temporary membership on small buckets too; replace it with the direct small-list branch. Retain all full reconstruction validation. |

The high-diversity case constructs Event records directly and isolates index reconstruction. It does not train graph construction, discovery, Replay or planning, and does not establish learned quality or end-to-end throughput. The cold-load fixture was produced with real `train_events` and bounded Replay. Seven-sample p95/p99 equal the sample maximum; they are not production tail estimates. Tracing and profiling use separate samples from normal timings.

Raw results: [before](reconstruction-before-results.json), [initial prototype](reconstruction-prototype-results.json), [retained implementation](reconstruction-after-results.json).

## Full-validation contract and remaining cost

`save_state` still serializes JSON, parses those bytes, and calls `RisaState.from_dict` before replacing files. It also validates an existing primary before promoting its exact bytes to the backup. Reconstruction includes graph models, Event models, evidence indexing, prediction indexing, candidate discovery/evaluation restoration and persisted readout compaction. Removing these wholesale would change the failure and restoration contracts. This request therefore optimizes an existing reconstruction component, rather than adding an unchecked save path or persisting redundant indexes.

In the baseline instrumented cold-load sample, total load time was 0.855 seconds; graph reconstruction 0.265, prediction indexing 0.160, evidence indexing 0.137 and JSON parsing 0.151 seconds. Nested timings overlap. Graph and Event construction remain significant work; this report does not mark them optimized.

## Temporary membership audit

Ownership is local to one `rebuild_prediction_indexes` call. Initial contents come from the ordered list exactly once at the threshold; every later append updates both structures. No set survives the function, no invalidation protocol is required between calls, and replacing the Event corpus cannot reuse stale membership. Small buckets allocate no membership sets. There is no TTL, polling, eviction loop or persistent cache. The stress case has four shared activation buckets and 10,002 distinct normalized effects per bucket. This is a lifecycle/correctness audit, not measured cache hit/miss telemetry; audits of other long-lived indexes remain unfinished.

## Reproduction

```sh
python3 -m experiments.persistence_optimization --prepare --scales 10000
python3 -m experiments.reconstruction_optimization --implementation before --output /tmp/reconstruction-before.json
python3 -m experiments.reconstruction_optimization --implementation after --output /tmp/reconstruction-after.json
python3 -m experiments.persistence_optimization --scales 10000 --samples 9 --paired-index --output /tmp/reconstruction-save-paired.json
python3 -m pytest -q
```

日本語: [Next] Graph/Event復元のコストを個別測定し、重複レコードとschema移行の契約を維持する改善を評価する。[Next] G3.4の独立留出品質・構造成長評価。[Later] 実運用corpus、大規模tail、100万Event、その他の長寿命cache、累積allocation・context switch・直接電力測定。

English: [Next] Isolate graph/Event restoration costs and evaluate changes preserving duplicate-record and migration semantics. [Next] G3.4 held-out quality and structural growth. [Later] Production corpus, large-scale tails, 1M Events, other long-lived caches, cumulative allocations, context switches and direct energy.

简体中文: [Next] 分别测量Graph/Event恢复成本，评估保留重复记录及迁移语义的优化。[Next] G3.4留出质量与结构增长。[Later] 实际语料、大规模尾延迟、百万Event、其他长生命周期缓存、累计分配、上下文切换及直接能耗测量。

## Whole-save regression and retained tradeoff

Sequential five-sample save runs differed broadly in graph construction and encoding timings even though those paths were unchanged; they cannot attribute the whole difference to this patch. Raw data is preserved: [before](reconstruction-save-before-results.json), [after](reconstruction-save-after-results.json). Repeat with alternating old/new order per pair, nine pairs per operation, fresh subprocesses and no competing benchmark workers: [paired results](reconstruction-save-paired-results.json).

| Bounded 10k save | Old median | New median | Old p95/p99/max | New p95/p99/max |
| --- | --- | --- | --- | --- |
| Fresh | 0.521569 s | 0.535179 s | 0.810982 s | 0.583214 s |
| Overwrite | 0.889822 s | 0.891650 s | 1.017861 s | 0.945612 s |

Fresh median increases by 2.6%, overwrite by 0.2%. Median CPU is 0.519793→0.533439 seconds fresh and 0.881221→0.885405 seconds overwrite. This is a small bounded-case overhead, not a whole-save improvement. Keep the patch for its demonstrated 38.5× reduction in diversity-dependent index rebuild latency; explicitly accept the measured temporary-memory and small bounded-case CPU tradeoff. Nine-sample tails remain empirical maxima, not robust tail guarantees. All 18 paired files have identical SHA-256 hashes, and all 36 restored persistence snapshots match their input state.

日本語: 通常データでは新規保存中央値が2.6%遅く、上書きは0.2%遅い。高多様性の索引再構築に対する約38.5倍の改善と、一時メモリ増加・小さな通常ケース負荷増加を併記する。18組の保存バイト列が一致し、36回の復元状態も一致した。全208テスト通過。

English: Bounded-case fresh save median regresses 2.6%, overwrite 0.2%. Retain the diversity-dependent 38.5× index improvement with explicit temporary-memory and small bounded-case overhead costs. All 18 paired files and 36 reload snapshots match. All 208 tests pass.

简体中文: 少词汇场景的新建保存中位数慢2.6%，覆盖慢0.2%。保留高多样性索引约38.5倍的改善，同时明确记录临时内存增加及常见场景的小幅成本。18组文件和36次恢复状态完全一致，208项测试通过。
