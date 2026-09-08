# G2 Candidate Transfer Evaluation / G2候補転移評価 / G2候选迁移评估

Date: 2026-09-08. Benchmark: `g2-c1-candidate.0.0`. Canonical manifest SHA-256: `a1bd3b99e70340b66ff4a7b58529c0bde8f3664ac30e540cba4bebab07806ab4`.

## Question / 問い / 问题

日本語: 単一action・target role・atomic outcomeを表す`UnnamedConceptCandidate`が、既存の型付きrole集計を超えて
未知target予測を改善するかを測る。候補の支持Eventとdevelopment/final IDを完全に分離し、候補あり/なしを同じqueryで
paired比較する。開発差が5ポイント未満または95%区間下限が0以下なら候補を棄却する。

English: This test asks whether a single-action, target-role, atomic-outcome candidate improves unseen-target prediction
beyond the existing typed-role readout. Supporting, development and final IDs are disjoint. Candidate and no-candidate
predictions are paired on identical queries. Development gain below five points or a non-positive lower 95% bound rejects
the candidate.

简体中文: 本评估检验由单一action、target角色及原子结果组成的候选，能否超过现有类型化角色readout并改善未见target预测。
支持、development及final ID完全分离；在相同query上配对比较有无候选。development提升低于5个百分点或95%区间下限
不大于0时拒绝候选。

## Result / 結果 / 结果

Five seeds produced 800 development and 200 final episodes.

| Partition | Candidate | No candidate | Paired delta | False-generalization delta |
| --- | ---: | ---: | ---: | ---: |
| Development | 100% | 100% | 0 points | 0 points |
| Final counterfactual | 100% | 100% | 0 points | 0 points |

All five candidates were rejected at the development gate. Leakage audit: support/development overlap `0`, support/final
overlap `0`, development/final overlap `0`.

日本語: 現候補は既存role集計と同じ答えを再表現しており、予測能力を追加しない。構造AIの追加価値として採用できない。
ただし回帰queryの出力一致を確認してからrole集計を除去する圧縮では、対象readoutが平均81 bytesから2 bytesになり、
候補あり100%、なし25%だった。これは候補が新しい汎化器ではなく、既存readoutを損失なく置き換える圧縮単位になり得る
ことを示す診断であり、通常比較の成功率とは分けて扱う。

English: The current candidate restates the same answer as the typed-role counts and adds no predictive capability, so
it fails the structural-value gate. After regression-query equivalence checks, candidate-backed compaction reduces the
target role readout from 81 to 2 bytes on average; candidate success is 100% versus 25% when candidate use is disabled.
This supports candidate-backed compression, not a new generalization claim.

简体中文: 当前候选只是重新表达类型化角色频度表的相同答案，没有增加预测能力，因此未通过结构价值门槛。在另一个移除
角色频度readout前先检查回归query输出一致，目标readout平均由81 bytes降至2 bytes；有候选为100%，关闭候选后为25%。
这支持候选用于压缩，不能作为新泛化能力的证据。

## Redesign / 再設計 / 重新设计

- [Done] 単一遷移候補を能力向上として自動採用しない。
- [Next] 既存readoutでは表現できない複数relation、時間列、適用前提、変数束縛を候補schemaへ追加する。
- [Done] candidate-backed compactionは回帰query一致時だけ適用し、不一致ならrollbackする。元Eventを保持し、新規Event学習前にreadoutを復元する。
- [Next] 対象readout以外を含む総memory、p95時間、広いquery corpusで圧縮gateを評価する。
- [Later] 二世代候補は祖先と支持・評価IDが重ならず、独立held-outで追加改善する場合だけ有効とみなす。

## Artifacts / 成果物 / 产物

- Manifest: [`experiments/g2_candidate_manifest.json`](../experiments/g2_candidate_manifest.json)
- Runner: [`experiments/candidate_transfer_evaluation.py`](../experiments/candidate_transfer_evaluation.py)
- Results: [`g2-candidate-transfer-results.json`](g2-candidate-transfer-results.json)
