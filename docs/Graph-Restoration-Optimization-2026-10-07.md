# Graph restoration and temporary context sharing — 2026-10-07

日本語: [Done] Graph/Event復元のうち、Graph復元で繰り返されるcontext tupleと文字列の保持を削減した。共有するのは不変な通常の文字列tupleだけで、表は復元ごとに作成し、128件を上限に破棄する。保存schema、出典、復元検証、重複レコード統合、バックアップは維持する。引数配置とevidence countの小変更は計測の結果、撤回した。

English: [Done] Reduced retained duplicate context tuples and strings during graph restoration. Only immutable plain-string tuples are shared; the table is local to restoration, capped at 128 entries and discarded afterward. Schema, provenance, validation, duplicate merges and backups remain unchanged. Positional-constructor and evidence-count micro-optimization trials were reverted after measurement.

简体中文: [Done] 减少Graph恢复时重复保留的context元组和字符串。仅共享不可变的普通字符串元组；共享表在每次恢复时建立，上限128项，结束后释放。schema、来源、验证、重复记录合并及备份保持不变。位置参数和evidence count的微优化在测量后撤回。

## Problem, evidence and implementation

The trained 10k-Event fixture contains 10,020 nodes and 42,554 edges. Of these edges, 42,518 have nonempty context tags, but only five nonempty tag tuples are distinct. The original decoder allocated a tuple for each edge and retained separately decoded equal strings through those tuples. Empty tuples were already shared by Python and do not need this change.

| Required reporting field | Retained context-sharing change |
| --- | --- |
| Problem | Graph hydration retains many equal immutable context tuples and their separately parsed strings. |
| Root cause | Each edge calls `tuple(values)` independently; the JSON decoder does not deduplicate context string values. |
| Evidence | Real trained fixture: 42,518 nonempty edge tuples, five distinct tuples. Separate initial profile attributes 0.253s to graph restoration with 42,554 edge registrations. Normal timings are measured separately. |
| Changed files | `risa/core/graph_store.py`, `experiments/graph_restore_optimization.py`, frozen graph baseline, `tests/test_graph_restore_optimization.py`, README and roadmap. |
| Change | Reuse equal plain-string context tuples during graph hydration. Use a local pool capped at 128 entries; bypass empty tuples and unhashable values. Preserve accepted scalar types and string subclasses. |
| Why it should improve performance | Fewer retained duplicate tuples and strings, fewer live objects for garbage collection. No persistent index, synchronization or service is introduced. |
| Before / After | Alternating old/new order, fresh process per sample, same prepared input, same current encoder and prediction indexes. Normal measurements and cProfile/tracemalloc are separate. Final measurements are below. |
| CPU impact | Normal wall and process CPU are measured for graph-only hydration, cold loading, fresh save and overwrite save. No thread pool, clock setting or concurrency change. |
| GPU impact | Not applicable to this synchronous Python CLI. |
| Memory impact | Measure peak RSS, traced peak and traced retained memory before correctness checks. Live allocation block counts are recorded, not cumulative allocation counts. |
| I/O impact | Identical saved bytes; no new file or network operations. The persistence format and fsync/backup behavior are unchanged. |
| Energy impact | CPU time and context switches are measured; direct joules remain unmeasured. |
| Correctness verification | Frozen-reference equality for all graph fields, both adjacency maps, metabolism worklist, coactivation neighbors, full state snapshots and paired saved hashes. Tests cover both graph formats, duplicate merges, field values, malformed rows, updates after sharing, cap behavior and accepted unusual context values. |
| Regression risk | Workloads with many unique tag tuples may incur lookup overhead without sharing benefit; the 128-entry cap bounds transient table growth. Sharing tuple identity is intentional; tuple values remain immutable and updates replace an edge's tuple independently. |
| Keep / Revert | Keep only the context-sharing implementation. Do not retain the two micro-optimization trials. |

The compact format continues to copy node attribute dictionaries. The legacy format preserves its existing input-sharing behavior when duplicate nodes merge. This optimization does not change either contract.

## Reverted experiments

| Required field | Positional constructors | Evidence-count clamp |
| --- | --- | --- |
| Problem / root cause | Keyword argument processing during compact Node/Edge construction. | Repeated `max(count, 1)` calls during Edge registration. |
| Evidence | Profile and identical 10k fixture; positional arguments preserve the same record mapping. | Profile reports 42,554 `max` calls during graph hydration. |
| Changed files / change | Trial in `GraphStore.from_dict`, replacing keywords with positional arguments. | Trial in `add_or_update_edge`, computing the bounded count with a branch. |
| Why | Reduce argument processing. | Remove a builtin function call for each registered Edge. |
| Before / After | Graph median 0.142676→0.150779s (+5.7%); fresh save 0.527440→0.521747s, too small/inconsistent to attribute to this trial. | Graph wall median 0.311505→0.291718s but CPU 0.262989→0.264409s; cold load wall 0.594929→0.616835s. Whole-save differences are small. |
| CPU | Graph median CPU 0.142395→0.150091s; call count unchanged. | Graph profiled calls 275,416→232,862, but no robust normal CPU gain. |
| GPU | Not applicable. | Not applicable. |
| Memory | Graph traced peaks approximately 31.76MB in both variants. | No retention reduction is expected from the count branch. |
| I/O | Paired saved bytes identical. | Paired saved bytes identical. |
| Energy | Not measured. | Not measured. |
| Correctness / risk | Values and restoration snapshots match; positional field ordering adds maintenance risk. | Snapshot equivalence holds; mutating incoming duplicate Edge counts was avoided. |
| Keep / Revert | Revert. | Revert. |

Raw results: [positional trial](graph-restore-positional-results.json), [count trial](graph-restore-clamp-results.json), [initial sharing prototype](graph-restore-context-pool-prototype-results.json), [retained implementation](graph-restore-context-pool-results.json). Different trials ran at different times and must not be compared as a single common baseline. The count trial shows broad wall/CPU variation, reinforcing the need for paired normal measurements.

## Cache audit and measured limits

[Separate audit](graph-restore-context-cache-audit.json): 42,513 hits, five misses, 36 empty bypasses, hit ratio 99.9882%, one pool construction, no invalidations or evictions, peak five entries. Shallow pool memory is 496 bytes including canonical tuples shared with Edges, excluding their strings. The dictionary disappears when restoration returns; canonical tuples remain owned by graph edges. No stale pool survives a later load. New unique contexts beyond the cap are returned directly; existing cached contexts remain usable.

This audit measures this new temporary pool. It does not close audits of all other long-lived RISA indexes. Allocation metrics do not measure total allocated bytes over time, memcpy volume or process energy. Resource context-switch counters cover only the timed operation and exclude fixture setup and correctness checks.

## Reproduction and next work

```sh
python3 -m experiments.persistence_optimization --prepare --scales 0 1000 10000 100000
python3 -m experiments.graph_restore_optimization --samples 7 --output /tmp/graph-restore.json
python3 -m experiments.graph_restore_optimization --audit-cache --output /tmp/context-audit.json
python3 -m experiments.graph_restore_optimization --fixture /tmp/risa-optimization-fixtures/examples --samples 25 --output /tmp/small-restore.json
python3 -m experiments.end_to_end_scale_evaluation --output /tmp/g3-context-pool.json
python3 -m pytest -q
```

日本語: [Next] Event復元での一時辞書コピーと、学習・Replay・候補探索の残る負荷を個別評価する。[Next] G3.4の独立留出品質と構造成長評価。[Later] 実運用corpusのtail、100万Event、他の長寿命cache監査、累積allocation・コピー量・直接電力測定。

English: [Next] Isolate temporary Event dictionary copying and remaining learning/Replay/discovery costs. [Next] G3.4 independent held-out quality and growth. [Later] Production-corpus tails, 1M Events, other long-lived cache audits, cumulative allocations, copy volume and direct energy.

简体中文: [Next] 分别评估Event恢复的临时字典复制及学习、重放、候选发现的剩余成本。[Next] G3.4独立留出质量与增长。[Later] 实际语料尾延迟、百万Event、其他长生命周期缓存审计、累计分配、复制量及直接能耗测量。

## Final paired measurements

Final type-preserving implementation, seven pairs per operation, trained 10k Event fixture. p95 and p99 equal the maximum at this sample count.

| Operation | Before median | After median | Change | Before p95/p99/max | After p95/p99/max | Before/after median CPU |
| --- | --- | --- | --- | --- | --- | --- |
| graph | 0.125752s | 0.101308s | -19.4% | 0.154445s | 0.116643s | 0.125729/0.101264s |
| load | 0.268589s | 0.245787s | -8.5% | 0.501790s | 0.299417s | 0.268545/0.245696s |
| fresh | 0.533729s | 0.476687s | -10.7% | 0.576900s | 0.602813s | 0.531505/0.474905s |
| overwrite | 0.887889s | 0.783115s | -11.8% | 0.911761s | 0.804947s | 0.882834/0.778997s |

Separate instrumented memory measurements:

| Operation | Before/after traced peak | Before/after traced retained | Before/after live allocation blocks |
| --- | --- | --- | --- |
| graph | 31,755,875/29,717,978 bytes | 31,755,625/29,717,728 bytes | 368,066/325,575 |
| load | 93,178,528/91,139,576 bytes | 75,233,240/70,726,880 bytes | 1,099,164/1,014,126 |
| fresh | 101,661,712/99,621,305 bytes | 430,601/335,091 bytes | 7,050/5,060 |
| overwrite | 117,747,297/115,707,458 bytes | 431,302/336,444 bytes | 7,066/5,082 |

Cold-load retained traced memory drops 4,506,360 bytes (about 4.5 MB). Fresh-save max RSS falls approximately 246.0→239.4 MB, overwrite 262.0→254.3 MB; these are process peaks, including fixture setup, not cumulative allocation counts. All 28 normal medium pairs preserve snapshot hashes, and all 14 saved-file pairs preserve SHA-256 hashes. Eight separate instrumented samples also pass restoration equivalence.

Timed-operation context-switch medians (voluntary/involuntary):

- graph: before 0/30; after 0/6.
- load: before 0/24; after 0/28.
- fresh: before 3/122; after 3/38.
- overwrite: before 13/346; after 15/187.

### Small repository example

[Four-Event example, 25 pairs per operation](graph-restore-small-results.json). No useful small-case speedup is established; median overhead is below 0.020 ms per operation. All 100 normal snapshot pairs and 50 saved-file pairs match.

| Operation | Before/after median | Before/after p95 | Before/after maximum |
| --- | --- | --- | --- |
| graph | 0.075/0.088ms | 0.092/0.095ms | 0.093/0.095ms |
| load | 0.542/0.562ms | 0.575/0.587ms | 0.589/0.588ms |
| fresh | 0.800/0.810ms | 0.984/0.840ms | 1.091/0.989ms |
| overwrite | 1.276/1.292ms | 1.651/1.591ms | 1.671/1.707ms |

### No-reuse stress case

[2,000 graph edges with distinct context tags, 25 pairs](graph-restore-unique-results.json): graph median 2.335→2.559 ms (+9.6%, +0.224 ms), p95 2.532→2.655 ms, maximum 2.550→2.666 ms. This isolated synthetic case has zero Events and does not measure learned quality or a full training pipeline. All 25 snapshot pairs match. [Audit](graph-restore-unique-cache-audit.json): zero hits, 2,000 misses, 128 peak entries, 10,840 shallow bytes, one pool construction, no invalidations/evictions. Thus sharing has a small CPU cost when nothing repeats; the cap bounds table growth. Retain for the measured high-reuse trained-fixture path, with this limitation stated explicitly. The measured trained fixture is synthetic; it does not replace evaluation on an actual deployment corpus.

Recreate that stress fixture before using the generic runner:

```sh
python3 - <<'PYTHON'
import json
from pathlib import Path
from risa.core.models import Edge
from risa.core.state import RisaState
path = Path('/tmp/risa-context-unique-reproduction')
path.mkdir(exist_ok=True)
state = RisaState()
for i in range(2000):
    state.graph.add_or_update_edge(Edge(str(i), str(i+1), 'before', (f'context-{i}',)))
(path / 'state.json').write_text(json.dumps(state.to_dict()))
PYTHON
python3 -m experiments.graph_restore_optimization --fixture /tmp/risa-context-unique-reproduction --operations graph --samples 25 --output /tmp/unique-restore.json
```

日本語: 最終比較はGraph復元19.4%、読み込み8.5%、新規保存10.7%、上書き11.8%短縮。読み込み後の保持メモリは約4.5MB減。小規模データでは0.02ms未満の増加、共有がない2,000 Edgeでは0.224ms増加があり、万能な改善とは扱わない。

English: Final medians improve 19.4% for graph hydration, 8.5% loading, 10.7% fresh save and 11.8% overwrite. Retained load memory falls about 4.5 MB. Small-case overhead stays below 0.02ms; the 2,000-edge no-reuse case adds 0.224ms. Gains are workload-dependent.

简体中文: 最终中位数Graph恢复缩短19.4%、加载8.5%、新建保存10.7%、覆盖11.8%。加载后保留内存减少约4.5MB。小规模额外成本小于0.02ms；2,000条边无复用场景增加0.224ms。收益取决于数据特征。

## Regression and full-pipeline gate

All 218 tests pass (23.49 seconds). [Final fixed-manifest end-to-end check](g3-end-to-end-context-pool-final-results.json) is `profile_complete`; every scale completes within its original 45-second per-worker budget.

| Events | Worker wall | Peak RSS | Correct predictions | Reload/compaction mismatches | Stored bytes |
| --- | --- | --- | --- | --- | --- |
| 1,000 | 0.248s | 0.043 GiB | 12/12 | 0/0 | 862,045 |
| 10,000 | 2.491s | 0.198 GiB | 12/12 | 0/0 | 8,509,735 |
| 100,000 | 37.693s | 1.822 GiB | 12/12 | 0/0 | 85,816,075 |

This is a single-run capacity/regression check, not a causal end-to-end speedup estimate. Candidates remain zero; compaction is a no-op. Context sharing is an in-memory representation optimization and does not establish semantic condensation, generalization or independent held-out quality. The earlier check before the final subtype-preservation guard is retained as [initial gate](g3-end-to-end-context-pool-results.json). The million-Event decision remains deferred for capacity review.

日本語: 全218テスト通過。1千・1万・10万Eventの全工程が45秒制限内で完了し、各12/12予測、復元・compaction不一致0。単発の容量確認であり、凝聚や汎化の改善を示すものではない。

English: All 218 tests pass. The 1k/10k/100k full pipelines meet the unchanged 45-second budgets, with 12/12 correct predictions each and zero restoration/compaction mismatches. This capacity check does not establish condensation or generalization.

简体中文: 218项测试全部通过。1千、1万、10万Event的完整流程均在原45秒预算内完成，每组12/12预测正确，恢复及compaction差异为零。此容量检查不能证明凝聚或泛化收益。
