# Input validation optimization — 2026-10-09

日本語: 🟢 [Done] 学習前検証で履歴辞書全体をコピーせず、既存履歴と今回の追加分を分けて検索する。順序判定は今回入力するepisodeだけ集計する。重複、ID競合、遅着Eventの扱いを維持する。🟠 [Next] 10万Event全経路の安定性は引き続き検証する。

English: 🟢 [Done] Validate against existing history plus a small incoming overlay instead of copying the full history dictionary. Collect ordering maxima only for incoming episodes, preserving duplicate, ID-conflict and late-arrival semantics. 🟠 [Next] Full-path 100k stability remains unfinished.

简体中文: 🟢 [Done] 验证时查询既有历史与本批新增项，不复制整个历史字典。仅汇总本批episode的顺序上限，保留重复、ID冲突及迟到Event语义。🟠 [Next] 10万Event完整流程稳定性仍未完成。

| Required field | Result |
| --- | --- |
| Problem | Each training chunk copies every stored Event reference and computes latest ordering keys for all historical episodes. |
| Root cause | The `seen` dictionary mixes existing records with a small incoming batch; ordering maps retain unrelated episodes. |
| Evidence | Separate 100k multiple-episode profile: 204,004→5,013 calls. Profiling is outside normal timing; the history scan itself remains. |
| Changed files | `risa/engine/runtime.py`, paired input benchmark, validation regression tests, raw results and documentation. |
| Change | Keep an incoming-only `seen` overlay, fall back to original `events_by_id` for global ID conflicts, filter historical episode aggregation to incoming episodes. |
| Why | Remove the full dictionary copy and unused maxima without a persistent cache or stale-history assumption. |
| Before / After | 15 alternating in-process pairs, setup/equality outside timing. 100k multiple-episode median 22.025→13.319ms (39.5% shorter), empirical p95/p99/max 23.341→14.278ms. 10k median 2.121→0.783ms. |
| CPU impact | 100k multiple-episode median 22.002→13.282ms; single-episode 20.703→19.223ms. Small single-episode 1k median rises 0.388→0.447ms; 10k 1.831→1.914ms. Four-Event overhead is approximately 0.2 microseconds. |
| GPU impact | No GPU path. |
| Memory impact | Separate traced 100k peak: multiple-episode 5,967,511→82,055 bytes; single-episode 5,261,871→71,655 bytes. This is isolated temporary memory, not process RSS or cumulative allocation telemetry. |
| I/O impact | No new production I/O or persisted schema changes. |
| Energy impact | CPU work is a proxy; no direct joules measured. |
| Correctness | Compare exact accepted Event lists or exact ValueError text against frozen original validation. Cover empty inputs, historical/in-batch duplicates, global conflicts including episode changes, ordering ties, late arrivals, unrelated episodes and externally mutated history. Preserve input/history dictionaries. Complete training snapshots agree after every mixed duplicate/new chunk. |
| Regression risk | Additional set membership and fallback dictionary lookups can cost tens of microseconds on small single-episode batches; those regressions are recorded. Validation still scans all stored Events and still compares complete duplicate payloads. |
| Keep / Revert | Keep for measured large-history CPU and transient-memory gains while retaining exact validation contracts. |

Raw [isolated results](input-validation-results-2026-10-09.json). Reproduce: `python -m experiments.input_validation_optimization`. The frozen function is imported from `experiments/references/runtime_before_history_20261008.py`; input validation was unchanged between that snapshot and this edit. No benchmark worker runs concurrently with another benchmark or the test suite. Fifteen observations provide empirical order statistics, not production tail guarantees. Synthetic histories are not deployment-corpus evidence.

⭕️ [Pending] Real deployment corpus, authorized native allocation/copy telemetry, and calibrated process joules remain on hold. 🟠 [Next] The measured 100k wall-time instability remains testable and unfinished; the 45s limit is unchanged.

Full-path [unchanged-budget result](g3-input-validation-results-2026-10-09.json): 1k and 10k complete with 12/12 correct and zero reload/compaction differences. The 100k attempt completes ingestion then times out during save. Last completed checkpoint is wall 42.708s / CPU 34.840s; completed input-validation stages total 1.338s. These aggregate stages do not include unfinished save work. Changing conditions and other varying stages prevent a full-path speedup claim. 100k final correctness remains unverified in this attempt.

Validation: `python -m pytest -q` — **258 passed in 37.81s**, including eleven added compatibility cases. `git diff --check` passes.
