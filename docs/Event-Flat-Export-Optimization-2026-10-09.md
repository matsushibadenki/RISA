# Flat Event export optimization — 2026-10-09

日本語: 🟢 [Done] 保存する通常Eventの不変値と文字列リストを軽量にコピーする。複雑な値は従来の再帰変換へ戻し、保存前の完全検証・backup・atomic writeを維持する。🟠 [Next] 10万Event全経路の安定性は別途検証する。

English: 🟢 [Done] Copy flat Event immutable values and string lists through a lightweight path. Complex values retain the original recursive conversion; full save validation, backups and atomic writes remain. 🟠 [Next] Verify 100k full-path stability separately.

简体中文: 🟢 [Done] 使用轻量路径复制普通Event的不可变值及字符串列表。复杂值继续使用原递归转换，保留完整保存验证、备份及原子写入。🟠 [Next] 单独验证10万Event完整流程稳定性。

| Required field | Result |
| --- | --- |
| Problem | Event export uses recursive dataclass conversion even for plain immutable values and flat string lists. |
| Root cause | `asdict` recursively dispatches deepcopy on strings/scalars and reconstructs containers. |
| Evidence | Separate fresh-save profile call count 3,781,261→1,901,265; overwrite 5,352,214→3,472,222. Instrumented timings are excluded from normal latency summaries. |
| Changed files | `risa/core/state.py`, Event export compatibility tests, paired measurements and documentation. Existing comparison harness reused. |
| Change | Reuse exact built-in immutable scalars and copy exact built-in lists of exact strings. Any other retained value falls back to the original complete recursive conversion. |
| Why | Avoid unnecessary recursive copy dispatch while preserving independent mutable outputs, nested dataclasses, custom deepcopy hooks and custom Event exports. No cache or approximation. |
| Before / After | Five alternating pairs, fresh subprocess per measurement, real-trained 10k fixture: fresh median 0.477514→0.408876s (14.4% shorter); overwrite 0.796069→0.704978s (11.4% shorter). |
| Tail impact | Empirical fresh p95/p99/max 0.554330→0.421214s; overwrite 0.843362→0.717257s. Five samples are not production tail guarantees. |
| CPU impact | Fresh median 0.476084→0.406961s; overwrite 0.786302→0.701592s. |
| GPU impact | No GPU path. |
| Memory impact | No material peak-memory gain: traced fresh approximately 99.62MB and overwrite 115.70MB for both versions. Normal peak RSS remains approximately 239MB / 254MB. Traced live blocks are not cumulative allocations. |
| I/O impact | Saved bytes and hashes exactly match (10k: 8,509,735 bytes); full pre-save state hydration, existing-file validation, backup and atomic replacement are unchanged. |
| Energy impact | CPU and context switches are proxies, no calibrated joules measured. |
| Correctness | Every pair verifies complete state snapshots and saved-file SHA256 outside timing. Tests cover all Event fields, recursive nested values, output independence, omitted defaults, custom Event export and scalar-subclass deepcopy hooks; public Event.to_dict remains unchanged. |
| Regression risk | Complex Events incur preliminary inspection before falling back, and receive no promised speedup. Fast path accepts exact built-in types only, so subclass behavior stays on the original path. |
| Keep / Revert | Keep for measured normal-case saving gains with exact bytes and state. |

Raw [paired results](event-flat-export-results-2026-10-09.json). Reproduce fixture with `python -m experiments.persistence_optimization --prepare --scales 10000`, then `python -m experiments.graph_restore_optimization --event-baseline --operations fresh overwrite --samples 5 --output docs/event-flat-export-results-2026-10-09.json`.

The existing `event-baseline` option compares against `state_before_event_restore_20261008.py`, holding graph hydration fixed. Its historical baseline label refers to that snapshot, not the new optimization target. Event hydration code is identical between the compared versions; the measured change is Event export. Synthetic bounded vocabulary does not establish deployment-corpus quality. The initial attempt lacked its temporary fixture and performed no timed operation; the fixture was prepared before all recorded measurements.

⭕️ [Pending] Deployment corpus, native cumulative allocation/copy telemetry and calibrated direct energy remain on hold. 🟠 [Next] Full-path wall-time stability remains testable and unfinished.

Full-path [unchanged-budget check](g3-flat-export-results-2026-10-09.json): 100k completes in 30.884s (worker wall 31.193s, process CPU 30.339s), with save stage 4.870s. Every scale has 12/12 correct predictions and zero reload/compaction differences. This single run does not establish stable tails; other varying stages prevent attributing the whole elapsed-time change to Event export. Earlier timeout results are retained.

Validation: `python -m pytest -q` — **260 passed in 24.12s**; `git diff --check` passes.
