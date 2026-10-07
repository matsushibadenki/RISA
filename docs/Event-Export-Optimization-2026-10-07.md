# Event persistence export optimization — 2026-10-07

日本語: [Done] 保存しない既定値をコピーする前に除外する。1万Eventの新規保存中央値は0.624→0.522秒（16.3%短縮）、上書き保存は0.972→0.859秒（11.6%短縮）。保存ファイルの内容・バイト列・出典を維持し、全205テストが通過した。メモリ削減は確認できていない。

English: [Done] Omit default Event fields before recursive copying. Median fresh saves at 10k Events improved from 0.624 to 0.522 seconds (16.3%); overwrites improved from 0.972 to 0.859 seconds (11.6%). Saved bytes and provenance remain identical, and all 205 tests pass. No memory reduction is established.

简体中文: [Done] 在递归复制前排除无需保存的Event默认字段。1万Event的新建保存中位数从0.624降至0.522秒（缩短16.3%），覆盖保存从0.972降至0.859秒（缩短11.6%）。保存字节及来源信息完全一致，205项测试全部通过。未确认内存减少。

## Evidence and decision

| Reporting field | Result |
| --- | --- |
| Problem | Event persistence copied all 26 fields, then discarded defaults and id. |
| Root cause | `Event.to_dict()` invokes recursive `dataclasses.asdict` before persistence filtering. |
| Evidence | Separate 10k cProfile run attributes 0.760 seconds to Event export before the change. Afterward it takes 0.670 seconds; traced/profiled timings are not normal latency estimates. |
| Changed files | `risa/core/state.py`, `experiments/persistence_optimization.py`, `tests/test_event_persistence_export.py`, documentation. |
| Change | Select retained fields, then use standard `asdict` on a private dataclass containing the selected dictionary. Subclasses and instance export overrides keep the original export path. |
| Why | Avoid recursive conversion of omitted fields while keeping nested dataclass conversion and independent mutable output containers. No custom recursive serializer is introduced. |
| Before / After | Same compact encoder, same legacy pretty input fixtures, fresh subprocess per sample. 1k fresh: 35.69→31.68 ms; overwrite: 54.87→51.65 ms. 10k fresh: 624.29→522.42 ms; overwrite: 971.57→859.14 ms. Five samples per case. |
| CPU | 10k median fresh CPU: 0.622→0.520 seconds; overwrite: 0.963→0.855 seconds. Separately profiled calls: 4,563,586→3,603,585. |
| GPU | Not applicable to this synchronous Python persistence path. |
| Memory | 10k traced peak stays approximately 101.66 MB; process peak RSS stays approximately 245–246 MB fresh and 261 MB overwrite. No meaningful gain claimed. Live allocations are not cumulative allocation counts. |
| I/O | All 21 paired synthetic outputs, including separately profiled samples, have identical SHA-256 hashes. File sizes and atomic write/backup/fsync behavior remain unchanged. |
| Energy | CPU time decreases; direct energy consumption has not been measured. |
| Correctness | 205 tests pass. New checks compare every Event field with the former exporter, verify nested copies cannot mutate source Events, default omission and custom subclass exports. Benchmark reload snapshots all match. |
| Risk | Default comparison occurs before recursive conversion for normal typed Event fields. Public `Event.to_dict()` is unchanged. Custom Event export implementations use the original path. |
| Keep / Revert | Keep: normal latency and CPU improve without byte changes or extra persistent caches. |

Five-sample p95/p99 equal the sample maximum. Fresh 10k maximum falls from 0.636 to 0.578 seconds; overwrite maximum falls from 1.004 to 0.873 seconds. These are empirical observations, not production tail guarantees. Synthetic fixtures use bounded vocabulary. Do not extrapolate this save-path change to end-to-end training or independent held-out quality.

Raw measurements: [before](event-export-before-results.json), [after](event-export-after-results.json). Baseline measurements were recorded before modifying `state.py`; their `implementation: after` label denotes the already optimized compact persistence encoder. The new `event-before` mode reproduces the former Event exporter while retaining that encoder.

Reproduce from the repository root:

```sh
python3 -m experiments.persistence_optimization --prepare --scales 0 1000 10000
python3 -m experiments.persistence_optimization --scales 1000 10000 --samples 5 --implementation event-before --output /tmp/event-before.json
python3 -m experiments.persistence_optimization --scales 1000 10000 --samples 5 --implementation after --output /tmp/event-after.json
python3 -m pytest -q
```

## Remaining work

日本語: [Next] 保存時の完全な状態再構築とCLI起動時のindex再構築を個別計測し、検証・移行・破損復旧の契約を保った削減方法を評価する。[Next] G3.4の独立留出品質と構造成長の評価。[Later] その他のindexのcache監査、実運用corpusでの大規模tail測定、100万Event容量評価、累積allocation・context switch・直接電力測定。今回これらの実装完了は主張しない。

English: [Next] Isolate full pre-save reconstruction and per-CLI index reconstruction costs, then evaluate reductions that preserve validation, migrations and recovery. [Next] G3.4 independent held-out quality and structural growth. [Later] Other index cache audits, production-corpus tail measurements, 1M-Event capacity, cumulative allocations, context switches and direct energy measurement. These remain unfinished.

简体中文: [Next] 分别测量保存前完整状态重建和CLI索引重建成本，在保留验证、迁移及恢复契约的条件下评估优化。[Next] G3.4独立留出质量与结构增长评估。[Later] 其他索引缓存审计、实际语料的大规模尾延迟、百万Event容量、累计分配、上下文切换及直接能耗测量。这些尚未完成。

## Small example check

The four-Event repository example was measured in 25 fresh subprocesses per operation and implementation. fresh: median 0.758→0.764 ms; p95 0.831→0.834 ms; maximum 0.936→0.851 ms. overwrite: median 1.212→1.204 ms; p95 1.421→1.303 ms; maximum 1.439→1.327 ms. All 51 paired files, including separate instrumentation, have identical hashes and reload snapshots. Absolute differences are under 0.1 ms and do not establish a useful small-case speedup. This is a repository example, not a production corpus. [Before](event-export-examples-before-results.json) · [After](event-export-examples-after-results.json).
