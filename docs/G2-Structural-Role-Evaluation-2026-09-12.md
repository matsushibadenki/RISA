# G2 Structural Role Evaluation / G2 構造role評価 / G2 结构role评估

## Result / 結果 / 结果

[Done] G2.5は一hop target roleの範囲で通過した。Eventに`target_roles`がない場合、RISAは`out:powered_by`のようなtarget entityの正規化relation位置から安定した内部roleを作る。5 seed・seedごとに独立development 800件・final 200件で、構造roleと外部roleは予測・compositionとも100%、roleなしablationは50%だった。構造経路の差は+50ポイントで、finalの対応bootstrap区間下限は+43ポイント。未知relationと逆向きrelationへの誤型付けは0%だった。構造role候補と外部role候補はすべて、support・development・final IDを分離したまま`adopted`へ到達した。

[Done] G2.5 passed for one-hop target roles. If an Event supplies no `target_roles`, RISA derives a stable internal role from the target entity's normalized relation position, for example `out:powered_by`. Across five seeds with 800 independent development cases and 200 final cases per seed, induced and supplied roles both reached 100% success in prediction and composition. The no-role ablation reached 50%, a 50-point gap whose final paired-bootstrap lower bound was +43 points. Mistyping on unknown and reversed relations was 0%. Every induced and supplied candidate reached `adopted` with disjoint support, development and final IDs.

[Done] G2.5在一hop target role范围内通过。Event未提供`target_roles`时，RISA从target entity的标准化relation位置（例如`out:powered_by`）生成稳定内部role。5个seed中，每个seed使用800个独立development案例和200个final案例；结构归纳role与外部提供role的预测及composition成功率均为100%。禁用所有role时为50%，因此结构路径提升50个百分点，final配对bootstrap区间下限为+43个百分点。未知relation及反向relation的错误类型率均为0%。所有结构role候选及外部role候选均在support、development与final ID互不重叠的条件下进入`adopted`。

## Implemented contract / 実装契約 / 实现契约

- Supplied roles take precedence, preserving the existing public contract.
- If roles are absent and induction is enabled, the engine locates every variable bound to the concrete target identity and records sorted `out:<relation>`, `in:<relation>` or `self:<relation>` descriptors.
- The descriptor tuple is independent of entity identity and variable name. Its SHA-256 prefix becomes an opaque `struct_role:<id>`; the readable signature remains in candidate metadata for explanation and audit.
- Training, candidate discovery, evidence indices, prediction, composition, replay, validation, CLI queries and persistence reconstruction use the same resolver.
- `enable_role_induction=False` provides an explicit ablation path.

外部roleを優先して既存contractを保つ。roleがなく誘導が有効な場合は、具体target identityに束縛された変数を探し、`out:<relation>`、`in:<relation>`、`self:<relation>`を整列した位置署名を作る。entity identityと変数名を含まない署名から不透明な`struct_role:<id>`を生成し、説明用の可読署名は候補metadataに残す。学習、候補発見、証拠index、予測、composition、Replay、validation、CLI、保存再構築は同じresolverを使う。`enable_role_induction=False`で独立ablationできる。

外部提供role优先，从而保持既有contract。未提供role且启用归纳时，系统查找绑定到具体target identity的变量，并生成排序后的`out:<relation>`、`in:<relation>`或`self:<relation>`位置签名。签名不依赖entity identity及变量名，其SHA-256前缀形成不透明的`struct_role:<id>`，可读签名保留在候选metadata中用于解释与审计。训练、候选发现、证据索引、预测、composition、重放、验证、CLI及持久化重建使用同一resolver。`enable_role_induction=False`提供独立消融路径。

## Held-out comparison / 独立比較 / 独立比较

| Final metric, mean over five seeds | Induced role | Supplied role | No role |
| --- | ---: | ---: | ---: |
| Prediction success | 100% | 100% | 50% |
| Composition success | 100% | 100% | 50% |
| Mistyping on unknown/reversed relations | 0% | 0% | — |
| Persisted state bytes | 106,565.8 | 142,812.2 | — |

The induced State was 25.38% smaller than the supplied-role State in this controlled setup because the repeated human-readable role labels were absent. This is a serialization result for the benchmark, not a general memory-complexity result. Leakage audit counts were zero for support-development, support-final and development-final overlap. Manifest SHA-256: `a39f13968160d9b7576298f2873415b92a6254c056b9b94c2dc4c52d4897c261`.

## Scope and next gate / 適用範囲と次gate / 适用范围及下一门槛

This result establishes deterministic one-hop positional typing in a controlled structured world. It does not establish semantic type discovery. Relation names are still observed symbols, the target identity must appear in `entity_bindings`, and two meanings with the same direct relation signature collide into one role. Actor and arbitrary-variable induction, multi-hop neighborhoods, missing/noisy relations and real logs remain untested.

この結果が示すのは、制御された構造世界での決定的な一hop位置型付けであり、意味型の自動発見ではない。relation名は観測済みsymbolで、target identityは`entity_bindings`に必要であり、同じ直接relation署名を持つ異なる意味は一つのroleへ衝突する。actor・任意変数の誘導、multi-hop近傍、欠落・noiseを含むrelation、実ログは未検証である。

该结果证明的是受控结构世界中的确定性一hop位置类型化，并未证明语义类型自动发现。relation名称仍是观测符号，target identity必须出现在`entity_bindings`中；具有相同直接relation签名的不同含义会冲突到同一role。actor及任意变量归纳、多hop邻域、缺失或含噪relation以及真实日志仍未验证。

[Done] 後続G2.6で、一hop署名内の衝突を最大二hop・base roleごとに最大8 refinementへ分化し、actorと任意entity変数へ拡張した。独立結果はG2 role曖昧性解消評価に記録した。

[Done] Follow-up G2.6 refines collisions within one-hop signatures using at most two hops and eight refinements per base, extending the contract to actors and arbitrary entity variables. The independent result is recorded in the G2 role-disambiguation evaluation.

[Done] 后续G2.6已将一hop签名内的冲突限制在最多二hop及每个base最多8个refinement，并扩展到actor及任意entity变量。独立结果记录于G2 role消歧评估。

Reproducible inputs and complete rows are in `experiments/g2_structural_role_manifest.json` and `docs/g2-structural-role-results.json`.
