# G1 Comparative Evaluation / G1比較評価 / G1比较评估

Date: 2026-09-08. Benchmark: `g1.0.0`. Manifest SHA-256: `2e75d76f0d26ad483ae1bb4258ec81f84e7afd560d148e45a051100890947e2c`.

## Contract / 評価契約 / 评估契约

日本語: 5固定seed、各split・各seed 200 held-out episodeを生成し、80%をdevelopment、20%をfinalへ決定的に割り当てた。全held-out IDは学習IDと分離され、compositionには答えを示す時間edgeを与えていない。driftだけは予測、採点、観測学習の順で更新した。Replayは20更新ごとに直近16 Eventへ固定した。

English: Five fixed seeds generate 200 held-out episodes per split and seed, deterministically divided into 80% development and 20% final. Held-out IDs never enter training, and composition receives no answer-revealing temporal edges. Only drift updates online in predict-score-observe order. Replay is fixed to the latest 16 events every 20 updates.

简体中文: 使用5个固定seed，每个split、每个seed生成200个留出回合，并确定性地分为80% development与20% final。留出ID不进入训练，composition不提供泄露答案的时间边。仅drift按预测、评分、观测学习顺序更新；Replay固定为每20次更新重放最近16个Event。

Methods are RISA, frequency, exact retrieval, grounded transition table, oracle, and five one-feature RISA ablations. All planning methods use the same breadth-first planner; an independent oracle executes the selected action sequence. Complete observations use set equality, partial observations use an explicit subset mask, and correct abstentions remain part of all-query success while coverage is reported separately.

## Final results / 最終結果 / 最终结果

Final rows pool 200 episodes across five seeds for each static split. Values are all-query success; parentheses show coverage.

| Method | Control | Composition | Binding | Uncertainty |
| --- | ---: | ---: | ---: | ---: |
| RISA | 100% (100%) | 100% (100%) | 75% (75%) | 94% (75%) |
| Grounded transition | 100% (100%) | 100% (100%) | 75% (75%) | 94% (75%) |
| Frequency | 100% (100%) | 0% (100%) | 50% (100%) | 94% (75%) |
| Exact retrieval | 0% (0%) | 0% (0%) | 0% (0%) | 25% (0%) |
| Oracle | 100% (100%) | 100% (100%) | 100% (100%) | 100% (75%) |
| RISA without structural sharing | 100% (100%) | 0% (0%) | 75% (75%) | 69% (50%) |

RISA final 95% intervals are Control `[0.9812, 1.0000]`, Composition `[0.9812, 1.0000]`, Binding `[0.6857, 0.8049]`, and Uncertainty `[0.8981, 0.9653]`. The complete machine-readable table contains all five ablations, per-seed values, coverage, covered accuracy, failure examples, latency, stored bytes, recovery, and forgetting.

| Drift phase | RISA | Grounded transition | Oracle |
| --- | ---: | ---: | ---: |
| A1 | 100% | 100% | 100% |
| B | 33.3% | 33.3% | 100% |
| A2 | 100% | 100% | 100% |

RISA never reached the 80% recovery threshold during B. It solved the one-third of B cases carrying an explicit exception context, but failed on the changed outcome under the original context. It returned to the threshold within the first 10 A2 episodes. Delayed observations were included in B. The result shows contextual exception handling and retention of the old mode, but no useful same-context adaptation.

## Decision / 判断 / 判断

日本語: 構造primitiveはこのbenchmarkの複数step計画と禁止状態回避に必要だった。しかしRISAは最強の適用可能baselineを上回らず、構造AIとしての優位性は実証されていない。未知target `radiator`を型や役割で`heater`へ束縛できず棄却し、同一contextのB期へ適応できなかった。共活性、Replay、代謝、分裂は個別に外しても今回の成功率を改善・悪化させず、寄与を示す課題設計または機構の再設計が必要である。

English: Structural primitives are necessary for this benchmark's multi-step planning and forbidden-state avoidance, but RISA does not beat the strongest applicable baseline. It cannot bind the unseen `radiator` target to the heater role and does not adapt to same-context phase B. Removing coactivation, replay, metabolism, or splitting does not change success here, so their contribution remains unsupported by this benchmark.

简体中文: 结构原语是本基准多步规划与禁止状态回避所必需的，但RISA没有超过最强适用基线。它无法把未见`radiator`对象绑定到heater角色，也无法适应同一context的B阶段。移除共激活、Replay、代谢或分裂没有改变本次成功率，因此这些机制的贡献仍缺乏证据。

RISA used about 161,635 stored bytes after static training versus 2,286 for the grounded transition baseline. On the final run's Control split, mean prediction time was about 0.049 ms versus 0.0009 ms. These Python-level measurements are environment-sensitive, but the size and latency gap is large enough to make compact evidence indexing and bounded replay immediate design requirements.

## Artifacts / 成果物 / 产物

- Manifest: [`experiments/g1_manifest.json`](../experiments/g1_manifest.json)
- Runner: [`experiments/comparative_evaluation.py`](../experiments/comparative_evaluation.py)
- Complete results: [`g1-comparative-results.json`](g1-comparative-results.json)
- Evaluation implementation: [`risa/evaluation/benchmark.py`](../risa/evaluation/benchmark.py)

The result is an initial synthetic benchmark, not a broad intelligence claim. It uses supplied preconditions for composition; learning applicability from before/after observations remains G2 work.
