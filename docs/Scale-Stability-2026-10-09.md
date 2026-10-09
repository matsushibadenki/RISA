# Full-path stability verification — 2026-10-09

日本語: 🟢 [Done] 同じmanifest・45秒制限で全経路を3回測定した。10万Eventは3回ともtimeoutしたため、前回の30.4秒だけでは安定性を判断できない。🟠 [Next] CPU時間とwall時間の差を計測し、残る処理量と遅延変動を切り分ける。閾値は緩めない。

English: 🟢 [Done] Repeat the full path three times with the same manifest and 45s budget. All three 100k attempts time out; the earlier 30.4s completion does not establish stability. 🟠 [Next] Measure process CPU alongside wall time to distinguish remaining work from latency variation, keeping the budget unchanged.

简体中文: 🟢 [Done] 使用相同manifest及45秒预算重复完整流程三次。10万Event三次均超时，之前30.4秒完成不能证明稳定性。🟠 [Next] 同时测量进程CPU及wall时间，区分剩余工作量与延迟波动，不放宽预算。

| Required field | Result |
| --- | --- |
| Problem / root cause | A single successful capacity run hides substantial latency variation. The cause of that variation remains unresolved. |
| Evidence | Three serial repetitions, fresh subprocesses, original scales/seed/chunk/Replay/query counts/budget. 100k: 0/3 complete, 3/3 timeout; 1k and 10k: 3/3 complete. |
| Changed files | Repetition harness, full-path telemetry, summary/censoring regression tests, raw measurements, README and roadmap. |
| Change / why | Preserve every outcome and write results after each repetition. Add checkpoint process CPU time and voluntary/involuntary context-switch counts for diagnosis, including partial progress. |
| Before / After | Prior single run: 100k full path 30.390s. Current repetitions: all censored at approximately 45s; no completed 100k median or p95/p99 can be reported. This is a verification result, not a new runtime speedup. |
| CPU / memory | Original repeated runs only contain wall stages and peak RSS. A separate diagnostic records CPU and switches; do not retroactively infer CPU from wall time. No production memory change. |
| GPU / I/O / energy | No GPU change or new production I/O. Benchmark checkpoints gain scalar telemetry only. Direct joules remain unavailable; CPU and switch counts are proxies, not energy measurements. |
| Correctness | All completed 1k/10k attempts have 12/12 correct predictions and zero reload/compaction differences. Incomplete 100k runs do not establish final correctness; aggregate correctness is null when no run completes. |
| Risk | Completed-only quantiles exclude censored timeouts and cannot represent overall tails. Three samples cannot establish production p99. No attribution of the slowdown to hardware, unrelated processes or a specific algorithm is proven. |
| Keep / Revert | Keep measurement and telemetry; do not mark 100k stability complete or relax the 45s threshold. |

| Scale | Completed | Worker wall median | Worker wall maximum | Predictions / restoration |
| --- | --- | --- | --- | --- |
| 1k | 3/3 | 0.584s | 0.784s | 36/36 correct; zero differences |
| 10k | 3/3 | 6.903s | 6.947s | 36/36 correct; zero differences |
| 100k | 0/3 | Unavailable | Three ~45s censored outcomes | Final verification unavailable |

First two 100k attempts retain last completed training chunks at 57k and 71k Events. The third completes training and saving, then times out before load completes. Checkpoint timings omit unfinished work. The previous successful run and these failures remain separately recorded; no successful retry replaces the failures.

Raw [repeated measurements](g3-stability-results-2026-10-09.json). Reproduce with `python -m experiments.end_to_end_stability --repetitions 3`. Profiling instrumentation is not mixed into these timings. Synthetic bounded vocabulary does not establish held-out structural generalization.

⭕️ [Pending] Deployment corpus, native cumulative allocation/copy measurement under authorized permissions, and calibrated process energy retain their documented hold conditions. 🟠 [Next] 100k stability is testable in this environment and remains active unfinished work.

Separate [CPU diagnostic](g3-stability-diagnostic-2026-10-09.json), under the same 45s budget: 100k also times out. Last checkpoint after 100k ingestion records wall 39.348s and process CPU 33.750s, with 11 voluntary and 205,562 involuntary context switches. The approximately 5.60s difference demonstrates elapsed time beyond accounted process CPU, but does not isolate its cause. Completed 1k/10k checks remain exact. CPU numbers exclude initialization before the timer and unfinished work after the checkpoint; context-switch counts do not establish power consumption or prove interference from another application.

Validation: `python -m pytest -q` — **247 passed in 35.90s**. Censored timeout/error summaries, incomplete correctness, and persisted CPU/switch telemetry are covered. `git diff --check` passes. Runtime learning and prediction code are unchanged in this measurement stage.
