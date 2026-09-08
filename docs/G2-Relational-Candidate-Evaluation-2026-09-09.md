# G2 Relational Candidate Evaluation / G2関係候補評価 / G2关系候选评估

Date: 2026-09-09. Benchmark: `g2-c3-relational-candidate.0.0`. Canonical manifest SHA-256: `e0f301b44b5b5f04e68855935f76964b4ca6d6f81bef4b9f08a8a01c377bae03`.

## Question / 問い / 问题

日本語: 2段階時間列候補をactorとtargetの二つの型付きrole変数へ拡張し、既存の無型Primitive・時間edge経路では
扱えない役割組合せとidentity制約を識別できるか測る。正常な`controller -> powered_device`、誤actor role、
誤target role、`actor == target`違反、状態前提欠落をpaired比較する。

English: This benchmark extends a two-step temporal candidate with typed actor and target variables. It tests whether the
candidate distinguishes role combinations unavailable to the existing untyped primitive and temporal-edge path. Paired
cases cover a valid `controller -> powered_device` relation, a wrong actor role, a wrong target role, an `actor == target`
constraint violation, and a missing state requirement.

简体中文: 本基准将两步时间候选扩展为actor与target两个类型化角色变量，检验其能否区分现有无类型原语及时间边路径无法处理的
角色组合及identity约束。配对案例包括正确的`controller -> powered_device`关系、错误actor角色、错误target角色、
`actor == target`约束违规及状态前提缺失。

## Result / 結果 / 结果

Five seeds produced 800 development and 200 final cases.

| Partition | Relational candidate | Existing path | Paired delta | Candidate false generalization | Existing-path false generalization |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | 100% | 40% | +60 points | 0% | 75% |
| Final | 100% | 40% | +60 points | 0% | 75% |

All five candidates passed `proposed -> provisional -> adopted`. Support/development, support/final and development/final
ID overlaps are all `0`.

日本語: 候補は各episodeで同一actorと同一targetを保ち、`actor:controller`と`target:powered_device`の両方が一致した
queryだけを合成した。さらに支持Eventから得た`actor != target`を具体identityへ適用した。既存経路はこれらを表現しないため、
誤actor、誤target、identity違反の3種類を誤って合成した。
この限定課題では、複数role変数が単一target role候補を超える追加価値を示した。

English: The candidate preserves the same actor and target across each episode and composes only when both
`actor:controller` and `target:powered_device` match, and it applies the learned `actor != target` constraint to concrete
identities. The existing path represents neither constraint and incorrectly composes wrong-actor, wrong-target and
identity-violation cases. On this scoped task, multiple role variables add value beyond a target-only candidate.

简体中文: 候选在每个回合中保持同一actor与同一target，并仅在`actor:controller`及`target:powered_device`同时匹配时组合。
候选还把从支持Event归纳的`actor != target`约束应用于具体identity。现有路径不表示这些约束，因而错误组合了错误actor、
错误target及identity违规三类案例。在该限定任务中，多角色变量显示出
超过单一target角色候选的附加价值。

## Redesign / 再設計 / 重新设计

- [Done] 同一actor・同一targetの2段階列からactor/target role変数を発見し、複合派生indexとComposition queryへ通す。
- [Done] actor roleをCLIへ追加し、role不一致または必要role欠落時は無型経路へfallbackせずabstainする。
- [Done] 5 seedの非重複development/final比較で、+60ポイントとfalse generalization −75ポイントを確認する。
- [Done] queryとCLIへ具体actor/target identityを通し、支持Eventから帰納した`equal`/`not_equal`を実行時に検査する。
- [Next] actor/target以外の可変entity集合とrelation edgeをEvent schemaへ一般化する。
- [Later] relation候補の圧縮効果を総保存量、探索量、p95時間、広い回帰集合で判定する。

## Artifacts / 成果物 / 产物

- Manifest: [`experiments/g2_relational_candidate_manifest.json`](../experiments/g2_relational_candidate_manifest.json)
- Runner: [`experiments/temporal_candidate_evaluation.py`](../experiments/temporal_candidate_evaluation.py)
- Results: [`g2-relational-candidate-results.json`](g2-relational-candidate-results.json)
