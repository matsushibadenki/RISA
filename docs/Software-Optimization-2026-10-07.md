# Software optimization / ソフトウェア最適化 / 软件优化

2026-10-07. Applied the supplied software optimization guide: architecture review → baseline → profile → one change → repeat → regression check → Keep/Revert.

日本語: 保存処理を計測して改善した。10万Eventの新規保存中央値は12.901→6.874秒（46.7%短縮）、上書きは12.843→10.795秒（15.9%短縮）。保存量は161,380,115→85,816,075 bytes（46.8%削減）。schemaと全JSON値を維持し、従来の整形出力は`save_state(state, path, pretty=True)`で利用できる。メモリ改善は小さく、全pipelineは40.314→39.575秒とほぼ同程度だった。局所保存の短縮を全体高速化と混同しない。

English: Measured and improved persistence. At 100k Events, median fresh save falls from 12.901 to 6.874s (46.7%), overwrite from 12.843 to 10.795s (15.9%), and storage from 161,380,115 to 85,816,075 bytes (46.8%). The schema and every JSON value are preserved; `save_state(state, path, pretty=True)` retains legacy formatting. Memory gains are small, and the whole pipeline changes only from 40.314 to 39.575s. The local save gain is not a demonstrated equivalent gain in total training latency.

简体中文: 测量并优化持久化。10万Event的新建保存中位数12.901→6.874秒（减少46.7%），覆盖保存12.843→10.795秒（减少15.9%），存储161,380,115→85,816,075 bytes（减少46.8%）。schema及所有JSON值保持一致，`save_state(state, path, pretty=True)`保留原格式。内存改善较小，完整pipeline仅40.314→39.575秒，不能将局部保存收益等同于整体训练提速。

## Architecture and measurements / 構成と計測 / 架构及测量

- Production is a synchronous Python CLI. Train/predict/planning commands load a state, execute in one process/thread and return. There is no production render loop, UI thread, GPU workload, network client, database, IPC boundary, background timer or polling loop. Idle CLI processes exit; no idle-power or frame-time claim applies.
- Data flow: JSON/JSONL Events → parser → pre-update prediction → graph/learning/metabolism → concept discovery/Replay/adaptation → schema-v6 JSON persistence. Commands reconstruct evidence/readout/chronology/candidate indices on load. `predict` therefore includes cold state reconstruction per invocation.
- Surveyed CLI, core state/graph/models, runtime, parser, predictor, learner, Replay, discovery, planner and persistence. G3.3's previous 100k profile already identified save (9.126s), load (3.216s), history setup (3.485s) and Replay (4.174s) as remaining costs. New isolated profiles confirm Python JSON formatting and snapshot export are substantial save costs.
- Normal CPython 3.10.18 on macOS ARM64, no debug interpreter build. Normal latency samples have neither cProfile nor tracemalloc. Allocation/call profiles run separately at 10k. Each sample is a fresh process, with the same prepared state and verified fsync/backup behavior.
- Small domain case: repository `data/stateful_world.json`, four real example Events, 25 samples per operation. Scale/stress fixtures: real `train_events` with default mechanisms and bounded Replay at 1k/10k/100k, three samples per operation. These synthetic loads are not production telemetry; no production corpus was supplied. Do not extrapolate to 1M.
- Overwrite samples begin with the **legacy pretty fixture** and preserve its bytes in the backup. They measure migration-compatible overwrite rather than only steady-state compact overwrite.
- Measured: wall/CPU seconds, median/p95/p99/max, call counts, traced peak/live allocations, process peak RSS, output bytes, full persisted-state equality and evidence-cache behavior. Traced live allocation blocks are not cumulative allocation counts. Memcpy volume, hardware energy, lock waits and context-switch counts were not measured; there is no production thread-lock or GPU subsystem to profile.

## Before / After

Seconds; p95 and p99 equal the maximum at only three samples. These are empirical observations, not reliable production tail estimates.

| Events | Operation | Before median | After median | Change | Before p95/p99/max | After p95/p99/max |
| --- | --- | --- | --- | --- | --- | --- |
| 1,000 | fresh | 0.058 | 0.038 | -33.7% | 0.076 | 0.040 |
| 1,000 | overwrite | 0.083 | 0.058 | -29.6% | 0.085 | 0.059 |
| 10,000 | fresh | 0.832 | 0.667 | -19.8% | 0.849 | 0.727 |
| 10,000 | overwrite | 1.469 | 1.029 | -30.0% | 2.189 | 1.041 |
| 100,000 | fresh | 12.901 | 6.874 | -46.7% | 12.984 | 12.588 |
| 100,000 | overwrite | 12.843 | 10.795 | -15.9% | 14.048 | 11.962 |

Repository four-Event example, 25 samples, milliseconds. Initial three-sample overwrite measurements appeared slower; the larger repeat separates that filesystem noise from a stable regression. Full p99 values are retained in the linked raw summaries.

| Operation | Before median | After median | Before p95 | After p95 | Before max | After max |
| --- | --- | --- | --- | --- | --- | --- |
| fresh | 1.062 | 0.889 | 1.109 | 0.931 | 1.111 | 0.941 |
| overwrite | 1.498 | 1.335 | 1.576 | 1.397 | 2.212 | 1.942 |

## Trial 1: buffered pretty JSON — Revert

- **Problem:** Large pretty-JSON save work and transient allocations.
- **Root cause:** Generic Python fragment walking plus full snapshot/reconstruction.
- **Evidence:** Before 10k profile: 13,904,774 calls, 109,237,318 traced peak bytes; `json.dumps` consumes 1.360 of 3.122 instrumented seconds.
- **Changed files:** Experimental edits to `risa/engine/persistence.py`; removed from production.
- **Change:** Retain at most 4,096 encoder fragments, stage to a file, release the snapshot, and reconstruct from staged bytes before atomic publication.
- **Why it should improve performance:** Hypothesis: reduce encoder fragment retention and the full encoded string. Measurement did not confirm lower overall RSS.
- **Before:** 100k fresh median 12.901s; overwrite 12.843s; fresh maximum RSS 2.177GiB.
- **After:** Fresh 9.236s; overwrite 13.417s; fresh maximum RSS 2.231GiB.
- **CPU impact:** Fresh median 10.393→9.230 CPU seconds; still roughly 13.9M profiled calls.
- **GPU impact:** Not applicable.
- **Memory impact:** No improvement in peak RSS; slightly worse.
- **I/O impact:** Same output bytes plus a new staged-file read for verification.
- **Energy impact:** No direct measurement; CPU time is a limited proxy.
- **Correctness verification:** Legacy byte equality and invalid snapshot/fsync/replace/recovery checks passed.
- **Regression risk:** Overwrite latency regressed and memory hypothesis failed.
- **Keep / Revert:** Revert the extra staging/buffering machinery; do not retain complexity for an unconfirmed memory benefit. [Measurements](persistence-streaming-results.json), [overwrite profile](persistence-streaming-overwrite-profile.json).

## Trial 2: buffered compact JSON — Superseded

- **Problem:** Whitespace and Python formatting work remained in Trial 1.
- **Root cause:** Its `iterencode` path still performs recursive Python fragment walking even without indentation.
- **Evidence:** 10k profile still contains 1,223,196 `_iterencode` calls and 2,958,343 recursive dictionary-encoder calls.
- **Changed files:** Experimental `risa/engine/persistence.py` buffer implementation; removed.
- **Change:** Remove whitespace while retaining the 4,096-fragment staging loop and byte reconstruction validation.
- **Why it should improve performance:** Fewer output bytes and formatting operations, without changing JSON data.
- **Before:** Trial 1 fresh median 9.236s, overwrite 13.417s at 100k; 161,380,115 bytes.
- **After:** Fresh 9.159s, overwrite 13.077s; 85,816,075 bytes.
- **CPU impact:** Python fragment walking remains dominant; fresh median 9.148 CPU seconds.
- **GPU impact:** Not applicable.
- **Memory impact:** No substantial peak-RSS improvement; fresh maximum 2.229GiB.
- **I/O impact:** Output reduced 46.8%, but staged verification adds a read.
- **Energy impact:** Not measured.
- **Correctness verification:** All recorded sample persistence snapshots match their input states.
- **Regression risk:** Maximum overwrite sample reached 17.106s; tails are undersampled.
- **Keep / Revert:** Revert buffering. Carry forward compact output into the simpler final implementation. [Measurements](persistence-compact-results.json).

## Final: standard compact encoder — Keep

- **Problem:** Unnecessary pretty formatting consumes CPU, transient allocations and disk space on every save.
- **Root cause:** `indent=2` forces Python recursive formatting rather than the normal CPython encoder's optimized path.
- **Evidence:** Baseline cProfile plus Trial 2 identify continued fragment walking; final profile falls to 4,563,586 calls (67.2% fewer). Instrumented save time is 3.122→1.924s; do not substitute that traced timing for normal latency.
- **Changed files:** `risa/engine/persistence.py`; `tests/test_persistence_optimization.py`; `experiments/persistence_optimization.py`; frozen baseline in `experiments/references/persistence_before_20261007.py`; report and roadmap/README.
- **Change:** Default to `separators=(",", ":")` without indentation, retain sorted keys/ASCII escaping/default numeric behavior, and offer `pretty=True`. The original in-memory reconstruction check, backup validation, atomic tempfile replacement, fsync and cleanup remain unchanged. No new data cache, lock, worker or format schema is introduced.
- **Why it should improve performance:** Eliminate formatting work and use the standard optimized encoder, producing fewer bytes with a smaller production patch.
- **Before:** Tables above; 100k fresh CPU median 10.393s, fresh peak RSS 2.177GiB, overwrite peak RSS 2.327GiB.
- **After:** 100k fresh CPU median 6.788s (34.7% lower), overwrite CPU median 10.753s (15.7% lower); fresh peak RSS 2.115GiB (2.9% lower), overwrite 2.268GiB (2.5% lower). Traced 10k peak is 109,237,318→101,662,607 bytes (6.9% lower). Do not claim a large memory reduction.
- **CPU impact:** Fewer interpreter calls and lower median CPU time, without adding parallelism or changing CPU clocks.
- **GPU impact:** Not applicable.
- **Memory impact:** Modest; reconstruction of the entire model still dominates peak memory.
- **I/O impact:** New primary output decreases 46.8%. Legacy overwrite still reads and writes the full old pretty backup; no fsync is removed. The discarded staged-verification read is absent.
- **Energy impact:** CPU work decreases; joules and work/J are unmeasured. No background activity is added.
- **Correctness verification:** All measured snapshots round-trip identically; every JSON value equals pretty output; `pretty=True` matches the old bytes; legacy backup bytes/recovery remain valid; invalid snapshots, encoding failure, fsync failure and replace failure preserve the old primary and clean tempfiles. The compact-path regression test checks that CPython does not fall back to Python fragment walking, and skips when that optional backend is unavailable. All 202 tests pass. CLI train/predict succeeds.
- **Regression risk:** Default whitespace and raw file hashes change. Consumers should parse JSON; callers requiring the former bytes can pass `pretty=True`. Numeric precision, field ordering, schema-v6 compatibility and old-file loading are preserved. CPython-specific speed is measured only on this host; alternative interpreters retain a functional fallback.
- **Keep / Revert:** Keep the small formatter change; remove both staging trials. [Before](persistence-before-results.json), [final](persistence-final-results.json), [example before](persistence-examples-before-25-results.json), [example final](persistence-examples-final-25-results.json).

## Whole-path check, caches and remaining work / 全経路と残課題 / 完整路径及剩余工作

日本語: [Done] 固定45秒のG3.3で1k/10k/100kが0.304/2.604/39.575秒で完了し、各規模12/12正解、凝縮・復元不一致0。100k最大RSSは1.842GiBだった。凝縮候補は0のfixtureであり、保存量削減はJSONの余白削減によるもの。学習による構造凝縮や汎化の改善ではない。全体速度は単発測定で以前とほぼ同程度。

English: [Done] The unchanged 45-second G3.3 gate completes 1k/10k/100k in 0.304/2.604/39.575s, each with 12/12 correct and zero compaction/reload mismatches. Peak RSS at 100k is 1.842GiB. With zero candidates, reduced storage comes from JSON whitespace rather than learned condensation/generalization. Overall latency is approximately unchanged in this single-run comparison. [Whole-path results](g3-end-to-end-persistence-results.json).

简体中文: [Done] 不变的45秒G3.3门槛下，1千/1万/10万以0.304/2.604/39.575秒完成，每规模12/12正确且压缩/恢复不一致为0。10万峰值RSS为1.842GiB。候选为0，存储减少来自JSON空白，而不是学习型凝聚或泛化改善；单次完整路径时间与以前大致相同。

Existing evidence-membership cache audit during one cold 10k reload: 29,952 hits, 48 misses/rebuilds, zero invalidations/evictions, 99.84% hit ratio and 1,588,192 shallow bytes. This measures bucket-set reuse while reconstructing an index, not cache reuse between independent CLI commands. Shared Event-ID strings/list storage are excluded from the shallow memory estimate. [Audit](persistence-cache-audit.json).

日本語: [Next] roadmapのG3.4で同じserialization設定の成長曲線と独立held-out成功率を評価する。[Later] 新たなprofileではEventの`asdict` exportと保存前の完全復元が主な負荷として残る。省略前に全default fieldをコピーする経路と、CLIの毎回復元を次の候補とするが、専用serializerや永続sessionをこの修正へ追加しない。型変換・旧schema・根拠再構築の契約を先に定めてから計測する。100万件は引き続き容量確認後に判断する。

English: [Next] G3.4 uses the same serialization policy for growth curves and independent held-out success. [Later] Event `asdict` export and full pre-save reconstruction remain prominent. Candidate follow-ups are avoiding copies of default fields before omitting them and retaining state across CLI-like interactive requests. Do not add custom serializers or persistent sessions here: establish type/migration/provenance contracts and measure first. 1M remains deferred pending capacity review.

简体中文: [Next] G3.4以相同serialization设置评估增长曲线及独立留出成功率。[Later] Event的`asdict`导出与保存前完整重建仍是主要成本。后续候选为省略默认字段之前避免复制，以及交互请求间保留状态。本次不增加专用serializer或持久session，先明确类型、迁移及来源重建契约再测量；100万仍待容量确认。

## Reproduce

```bash
python3 -m experiments.persistence_optimization --prepare --scales 0 1000 10000 100000
python3 -m experiments.persistence_optimization --implementation before --output /tmp/persistence-before.json
python3 -m experiments.persistence_optimization --implementation after --output /tmp/persistence-after.json
python3 -m experiments.persistence_optimization --scales 0 --samples 25 --implementation before --output /tmp/examples-before.json
python3 -m experiments.persistence_optimization --scales 0 --samples 25 --implementation after --output /tmp/examples-after.json
python3 -m experiments.persistence_optimization --audit-cache --fixture /tmp/risa-optimization-fixtures/10000 --output /tmp/cache-audit.json
python3 -m pytest -q
```

`0` selects the repository stateful example; positive scales are synthetic real-training loads. `--directory` changes the fixture location. Before and after reuse the same fixtures. Warm filesystem caches and an uncontrolled desktop workload limit absolute latency conclusions; no frequency pinning or energy guarantee is claimed.
