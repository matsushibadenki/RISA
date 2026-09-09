# G2 Candidate Transfer Evaluation / G2候補転移評価 / G2候选迁移评估

Date: 2026-09-10. Benchmark: `g2-c1-candidate.1.0`. Canonical manifest SHA-256: `c572d2e49d12ceae19728e8511ad63b8bad7115d1dd2d862f12dd23daebc2db9`.

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
回帰queryの出力一致を確認してからrole集計を除去すると対象readoutは平均81 bytesから2 bytesとなり、候補あり100%、
なし25%だった。一方、final 200 queryの広い集合で保存State全体は平均26,399 bytesから26,487 bytesへ88 bytes増加した。
再読込用directiveを保存する一方、除去したreadoutは元からschema v3の保存対象外であるためである。p95は今回
0.061675 msから0.056066 msだったが微小時間の単発診断であり、総memory増加を覆す根拠にはしない。

English: The current candidate restates the same answer as the typed-role counts and adds no predictive capability, so
it fails the structural-value gate. Equivalence-checked compaction reduces the target readout from 81 to 2 bytes and
keeps candidate-backed success at 100% versus 25% when candidates are disabled. Across the broader 200-query final
corpus, however, total persisted state grows by 88 bytes, from 26,399 to 26,487. The reload directive is persisted while
the removed schema-v3 readout was already rebuild-only. Observed p95 changes from 0.061675 ms to 0.056066 ms, but this
small-duration diagnostic does not offset the total-memory failure.

简体中文: 当前候选只是重新表达类型化角色频度表的相同答案，没有增加预测能力，因此未通过结构价值门槛。等价性检查后的
压缩把目标readout由81 bytes降至2 bytes，有候选时成功率保持100%，关闭候选后为25%。但在更广的final 200 query集合上，
持久化State总量由26,399 bytes增至26,487 bytes，增加88 bytes；原因是重载directive需要保存，而被删除的schema v3 readout
原本就只在运行时重建。此次p95由0.061675 ms降至0.056066 ms，但微小时延诊断不足以抵消总memory失败。

## Redesign / 再設計 / 重新设计

- [Done] 単一遷移候補を能力向上として自動採用しない。
- [Done] 既存readoutでは表現できない複数relation、時間列、適用前提、変数束縛を候補schemaへ追加した。
- [Done] candidate-backed compactionは回帰query一致時だけ適用し、不一致ならrollbackする。元Eventを保持し、新規Event学習前にreadoutを復元する。
- [Done] 総保存State、p95時間、200 final queryで診断し、保存量が88 bytes増える現方式を総memory圧縮として棄却した。
- [Next] 保存directiveではなくEvent・候補schema・支持IDの重複を直接圧縮し、同じ回帰契約で再評価する。
- [Later] 二世代候補は祖先と支持・評価IDが重ならず、独立held-outで追加改善する場合だけ有効とみなす。

## Artifacts / 成果物 / 产物

- Manifest: [`experiments/g2_candidate_manifest.json`](../experiments/g2_candidate_manifest.json)
- Runner: [`experiments/candidate_transfer_evaluation.py`](../experiments/candidate_transfer_evaluation.py)
- Results: [`g2-candidate-transfer-results.json`](g2-candidate-transfer-results.json)
