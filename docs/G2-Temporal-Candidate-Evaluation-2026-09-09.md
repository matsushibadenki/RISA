# G2 Temporal Candidate Evaluation / G2時間列候補評価 / G2时间序列候选评估

Date: 2026-09-09. Benchmark: `g2-c2-temporal-candidate.0.0`. Canonical manifest SHA-256: `55de198b15df818ffbf6c9bc7211c14e1a57cf46e1e3d86d7e068e3d71a181f3`.

## Question / 問い / 问题

日本語: 同一target roleを束縛する2段階候補が、既存のPrimitiveと`precedes` edgeによる合成を超えるかを測る。
正常条件、初期状態欠落、数値資源不足、誤target roleを同一queryで候補あり/なしpaired比較する。支持Event、development、
finalのIDは分離し、developmentで5ポイント以上かつ95%区間下限が正にならなければ候補を棄却する。

English: This benchmark tests whether a two-step same-target-role candidate improves on composition through existing
primitives and `precedes` edges. Paired queries cover valid inputs, missing initial state, insufficient numeric resources
and a wrong target role. Support, development and final IDs are disjoint. The candidate is rejected unless development
gain reaches five points with a positive lower 95% bound.

简体中文: 本基准检验绑定同一target角色的两步候选，能否超过现有原语与`precedes`边的组合路径。配对query覆盖正常输入、
初始状态缺失、数值资源不足及错误target角色。支持、development及final ID互不重叠；若development提升不足5个百分点或
95%区间下限不为正，则拒绝候选。

## Result / 結果 / 结果

Five seeds produced 800 development and 200 final cases.

| Partition | Temporal candidate | Existing path | Paired delta | Candidate false generalization | Existing-path false generalization |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | 100% | 75% | +25 points | 0% | 33.3% |
| Final | 100% | 75% | +25 points | 0% | 33.3% |

All five candidates passed `proposed -> provisional -> adopted`. Leakage audit: support/development overlap `0`,
support/final overlap `0`, development/final overlap `0`.

日本語: 時間列schemaは前提、状態消費、数値差分、同一target束縛を一つのmacroに保持する。初回比較で見つかった
「誤role時に無型Primitiveへfallbackする」問題を修正し、同じstart/goalを覆う採用済み型付きplanがある場合は、role不一致を
棄却するようにした。正常条件、状態欠落、数値不足を維持しながら誤roleだけをabstainできたため、能力ゲートを通過した。

English: The temporal schema packages applicability, consumption, numeric deltas and same-target binding into one macro.
The first comparison exposed an untyped fallback on role mismatch. The fix rejects that fallback when an adopted typed
plan already covers the same start/goal pair. It preserves valid, missing-state and low-resource behavior while abstaining
only on the wrong role, so the candidate passes the capability gate.

简体中文: 时间序列schema在一个宏中保存适用条件、状态消耗、数值差分及同一target绑定。首次比较发现角色不匹配时会回退到
无类型原语；现已修复为：若已采纳的类型化plan覆盖同一start/goal，则拒绝该回退。正常、缺少状态及资源不足行为保持不变，
同时仅对错误角色弃答，因此候选通过能力门槛。

## Redesign / 再設計 / 重新设计

- [Done] 2段階時間列候補の発見、段階評価、派生index、純粋transition適用、無効化flag、再読込復元を実装する。
- [Done] role不一致時の無型fallbackを禁止し、5 seedの非重複development/final比較で+25ポイント、false generalization −33.3ポイントを確認する。
- [Next] Event/queryを複数entityの型付きrole変数とrelationで表現し、各stepで変数の同一性・相違を検査する。
- [Done] 同じstart/goalを覆う採用済み型付きplanがある場合のrole不一致をabstainする。
- [Later] 時間macroによる保存量・探索量削減は、広い回帰集合で同値性を確認してから別の圧縮gateで評価する。

## Artifacts / 成果物 / 产物

- Manifest: [`experiments/g2_temporal_candidate_manifest.json`](../experiments/g2_temporal_candidate_manifest.json)
- Runner: [`experiments/temporal_candidate_evaluation.py`](../experiments/temporal_candidate_evaluation.py)
- Results: [`g2-temporal-candidate-results.json`](g2-temporal-candidate-results.json)
