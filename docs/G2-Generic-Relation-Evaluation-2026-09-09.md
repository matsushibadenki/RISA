# G2 Generic Relation Evaluation / G2任意関係評価 / G2任意关系评估

Date: 2026-09-09. Benchmark: `g2-c4-generic-relation.0.0`. Canonical manifest SHA-256: `9be45c1bdc1a44299da1285810fc16da58bca828b27434bed45fafdf2877aa8f`.

## Question / 問い / 问题

日本語: actor/target固定表現を、任意名のentity変数、型付きrole、変数間relationへ一般化した候補が未知identityへ転移するかを
測る。`operator holds credential`と`credential opens resource`を必要とする2段階列について、正例、誤role、relation欠落、
identity相違制約違反、誤relationを候補あり/なしでpaired比較する。

English: This benchmark asks whether a candidate generalized from fixed actor/target fields to arbitrary named entity
variables, typed roles and relations transfers to unseen identities. A two-step sequence requires `operator holds
credential` and `credential opens resource`; paired cases cover a valid relation, wrong role, missing relation, identity
inequality violation and wrong relation.

简体中文: 本基准检验从固定actor/target推广至任意命名entity变量、类型化角色及变量间relation的候选，能否迁移至未见identity。
两步序列要求`operator holds credential`及`credential opens resource`；配对案例包括正确关系、错误角色、relation缺失、
identity差异约束违规及错误relation。

## Result / 結果 / 结果

Five seeds produced 800 development and 200 final cases.

| Partition | Generic relation candidate | Existing path | Paired delta | Candidate false generalization | Existing-path false generalization |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | 100% | 20% | +80 points | 0% | 100% |
| Final | 100% | 20% | +80 points | 0% | 100% |

All five candidates passed `proposed -> provisional -> adopted`. Support/development, support/final and development/final
ID overlaps are all `0`.

日本語: 候補は3変数のrole、2本のrelation、変数間`not_equal`、各stepの状態遷移を保持し、新しいrobot・key・doorへ
再束縛した。既存Primitive＋時間edgeはentity relationを表現しないため、4種類の負例をすべて誤って合成した。この限定課題では
任意entity relationが固定actor/target表現を超える構造的追加価値を示した。

English: The candidate preserves three variable roles, two relations, pairwise inequality and step transitions, then
rebinds them to a new robot, key and door. Existing primitives plus temporal edges cannot represent entity relations and
compose every negative variant incorrectly. On this scoped task, arbitrary entity relations add structural value beyond
the fixed actor/target representation.

简体中文: 候选保存三个变量角色、两条relation、变量间`not_equal`及各步骤状态转移，并重新绑定到新的robot、key及door。
现有原语与时间边无法表示entity relation，因而错误组合了全部四类负例。在该限定任务中，任意entity relation显示出超过固定
actor/target表示的结构附加价值。

## Limits and next gate / 限界と次のgate / 局限与下一门槛

- [Done] Eventへ`entity_bindings`、`entity_role_bindings`、`entity_relations`を追加し、未知変数参照を入力時に拒否する。
- [Done] 任意変数数のrole照合、identity制約、relation包含を候補発見・派生index・Composition・再読込へ通す。
- [Done] 5 seedの非重複development/final比較で+80ポイント、false generalization −100ポイントを確認する。
- [Next] relationの追加・撤回を失敗Eventから学び、現在の完全一致schemaがnoise下で過分割しないか評価する。
- [Next] 総memory、p95時間、候補数、schema重複を広い回帰query corpusで測る。

## Artifacts / 成果物 / 产物

- Manifest: [`experiments/g2_generic_relation_manifest.json`](../experiments/g2_generic_relation_manifest.json)
- Runner: [`experiments/generic_relation_candidate_evaluation.py`](../experiments/generic_relation_candidate_evaluation.py)
- Results: [`g2-generic-relation-results.json`](g2-generic-relation-results.json)
