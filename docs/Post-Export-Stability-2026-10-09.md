# Post-export repeated scale gate — 2026-10-09

日本語: 🟢 [Done] 変更後の同一コードで全経路を直列3回測定し、全規模が45秒制限内で完了した。10万Eventのworker時間は29.519〜30.103秒、最小予算余裕は14.897秒。🟠 [Next] 長期・異なる負荷条件でのtail確認とG3.4の成長曲線・独立held-out評価を進める。今回の短期再現確認を本番p99保証としない。

English: 🟢 [Done] Three serial full-path repetitions on identical post-change code complete every scale within 45s. 100k worker times are 29.519–30.103s, leaving at least 14.897s budget margin. 🟠 [Next] Longer and varied-load tail checks plus G3.4 growth/independent held-out evaluation. This short reproducibility check is not a production p99 guarantee.

简体中文: 🟢 [Done] 修改后相同代码的三次串行完整流程均在45秒内完成。10万Event的worker时间29.519至30.103秒，最小预算余量14.897秒。🟠 [Next] 长期及不同负载尾延迟、G3.4增长曲线与独立留出评估。本次短期可重复性检查不代表生产p99保证。

| Scale | Completed | Worker wall median | Worker wall maximum | Prediction checks | Reload / compaction differences |
| --- | --- | --- | --- | --- | --- |
| 1k | 3/3 | 0.254s | 0.256s | 36/36 | 0 / 0 |
| 10k | 3/3 | 2.473s | 2.577s | 36/36 | 0 / 0 |
| 100k | 3/3 | 29.522s | 30.103s | 36/36 | 0 / 0 |

| 100k repetition | Worker wall | Measured operation wall | Process CPU | Save stage | Peak RSS |
| --- | --- | --- | --- | --- | --- |
| 1 | 29.522s | 29.218s | 29.043s | 4.830s | 1,933,459,456 bytes |
| 2 | 29.519s | 29.212s | 29.025s | 4.953s | 1,893,695,488 bytes |
| 3 | 30.103s | 29.735s | 29.527s | 4.958s | 1,953,398,784 bytes |

Worker wall includes subprocess startup/shutdown; process CPU begins at the operation timer. Accounted operation wall minus CPU is approximately 0.175–0.208s. This is smaller than the previous diagnostic's 5.60s gap, but workload timing and scheduling vary: no causal attribution to another process or the export edit follows from this difference.

| Required field | Result |
| --- | --- |
| Problem / root cause | Previous 100k runs varied from successful single runs to repeated timeouts. The cause of all historical variation is unresolved. |
| Evidence / before / after | Preserve earlier three timeouts and the later single success; now three fresh repeated gates complete. Same manifest hash `d4e7a68973a7a54a578d46735e5be16e19a5fa2dce843e459173fbad07486e3f`, same 45s budget, seed17, 1000-Event chunks, Replay32. |
| Changed files / change / why | Raw repeated-run artifact and documentation only. Verify reproducibility of the retained export change before pursuing further runtime edits. |
| CPU / GPU | 100k CPU 29.025–29.527s; no GPU work. |
| Memory / I/O | Peak RSS about 1.76–1.82 GiB; saved bytes remain 85,816,075 for 100k. No new production I/O or representation changes. |
| Energy | CPU and recorded context switches are proxies only. No joules measured. |
| Correctness | All nine scale runs complete, each 12/12 correct, zero reload/compaction differences. This bounded workload has zero candidate readout compaction opportunities. |
| Risk | Three observations cannot establish production tails, held-out generalization or stability under unrelated external loads. Empirical p95/p99 in the raw summary both equal the observed maximum. |
| Keep / Revert | Keep the measured export optimization; mark this short repeated gate complete, keep broader stability and research-quality evaluation unfinished. |

Raw [three repeated runs](g3-flat-export-stability-results-2026-10-09.json). Reproduce: `python -m experiments.end_to_end_stability --repetitions 3 --output docs/g3-flat-export-stability-results-2026-10-09.json`. Repetitions run serially, with no concurrent tests or benchmark workers. Profiling instrumentation is excluded. All nine run rows remain in the file; no successful retry replaces an unsuccessful result.

Verification: all repeated correctness gates pass; `git diff --check` passes. No source code changed in this stage, so the previous **260 passing regression tests** remain the relevant code validation; they were not rerun for documentation-only changes.

⭕️ [Pending] Deployment corpus, native cumulative allocation/copy measurements unavailable under existing permissions, and calibrated process joules retain their hold conditions. 🔴 [Later] Million-Event evaluation still requires a dedicated capacity review; completing this gate does not start it automatically.
