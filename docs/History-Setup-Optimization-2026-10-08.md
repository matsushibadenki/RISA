# History selection optimization — 2026-10-08

日本語: [Done] 学習開始時の履歴全体の並べ替えを廃止し、今回必要なepisodeとactorの最新Eventだけを選択する。キャッシュは追加せず、履歴変更後も現在の値を読む。単一episodeの中規模では負荷増があるため、その結果も残す。[Next] 10万Event全経路の予算余裕とtailの検証を続ける。

English: [Done] Replace sorting all training history with latest-predecessor selection for incoming episodes and actors. Read current Events without a new cache. Retain the measured medium single-episode regression. [Next] Continue checking full-path 100k budget margin and tails.

简体中文: [Done] 学习开始时不再排序全部历史，而是选择本批episode及actor所需的最新Event。不新增缓存，读取当前Event值。记录中等规模单episode的开销增加。[Next] 继续验证10万Event完整流程的预算余量与尾延迟。

| Required field | Result |
| --- | --- |
| Problem | Every chunk sorts all prior Events and populates predecessor maps for unrelated episodes/actors. |
| Root cause | History setup retains every group even though temporal linking only reads groups present in the incoming chunk. |
| Evidence | Separate 100k multiple-episode profile records 500,003 calls before and 4,028 after. Baseline sorting and normalization process every Event; optimized selection filters episodes before normalization. |
| Changed files | `risa/engine/runtime.py`, frozen runtime reference, isolated benchmark, compatibility tests, README and roadmap. |
| Change | One scan selects maxima of `(timestamp, id)` for relevant groups. `>=` preserves stable-sort last-entry behavior for equal keys. Incoming Events still use the original sort. |
| Why | Remove unused grouping, sorting and temporary collections. No approximation or persisted cache. |
| Before / After | 15 alternating in-process pairs with objects prepared outside timing. 100k multiple-episode median 43.527→13.798ms (68.3% reduction); empirical p95/p99/max 47.416→16.005ms. 10k multiple-episode median 2.446→0.485ms. |
| CPU impact | 100k multiple-episode median 43.527→13.797ms. Single-episode 10k median 2.281→3.631ms, a 1.350ms regression; 100k single-episode 38.605→37.957ms CPU, near parity. |
| GPU impact | No GPU path. |
| Memory impact | Separate traced 100k multiple-episode peak 11,073,125→118,825 bytes; single-episode 7,089,065→4,361 bytes. These are isolated selection peaks, not process RSS or cumulative allocation counts. |
| I/O impact | No new I/O; persisted schema and public predictions unchanged. |
| Energy impact | Reduced CPU work is a proxy; no calibrated joules measured. |
| Correctness verification | Seven tests compare frozen runtime complete snapshots and public predictions after every chunk, both role depths, multiple/default episodes, reversed input, timestamp ties, normalized actors, mutated history and stale event order. Timed predecessor selections also compare reference object identities outside timing. |
| Regression risk | Single-episode medium workloads pay extra per-Event comparisons. All-history scans still occur; this does not remove other history setup or validation costs. |
| Keep / Revert | Keep for measured multiple-episode gains and lower transient memory, with the single-episode cost explicit. |

Raw isolated measurements: [results](history-setup-results-2026-10-08.json). The baseline timed path returns its original complete maps; filtering to relevant groups occurs outside timing. Instrumented samples are separate. Fifteen samples do not establish production p99 guarantees. The synthetic scenario follows the G3.3 episode length and actor vocabulary, with an additional single-episode control; it is not an independent held-out scientific quality evaluation.

Reproduce: `python -m experiments.history_setup_optimization`. Full-path validation uses the unchanged `experiments/g3_end_to_end_manifest.json`, including the 45-second worker budget, Replay bound 32 and 1k/10k/100k scales.

[Pending] Deployment corpus, authorized native cumulative-allocation/copy telemetry and calibrated process energy remain unavailable under the previously documented conditions. This change does not resolve them.

Full-path result: [unchanged-budget run](g3-end-to-end-history-results-2026-10-08.json) completes 100k in **30.390 seconds** (worker wall 30.718s), with 12/12 predictions correct at every scale and zero reload/compaction differences. Peak RSS is 1,955,430,400 bytes (about 1.821 GiB). Total history-setup stage is 1.536s. This is a single run; variation in other stages prevents attributing the entire full-path improvement to predecessor selection, and stable production tails remain [Next]. Compaction in this bounded workload has no adopted candidate readouts and does not establish compaction savings.

Validation: `python -m pytest -q` — **245 passed in 25.10s**; `git diff --check` passes.
