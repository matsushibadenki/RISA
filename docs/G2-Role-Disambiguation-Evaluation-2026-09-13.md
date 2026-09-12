# G2 Role Disambiguation Evaluation / G2 role曖昧性解消評価 / G2 role消歧评估

## Result / 結果 / 结果

[Done] G2.6 passed in the controlled structured benchmark. RISA keeps the existing one-hop role when its outcome is unambiguous. When one action and one-hop role produce multiple outcomes, it tests a two-hop relation-position signature and retains it only when the refined role maps to one outcome. Across five seeds with 800 independent development and 200 final cases per seed, two-hop roles reached 100% prediction and composition success versus 50% for the one-hop-only path. The final paired-bootstrap lower bound was at least +42.5 points and mistyping on missing or unknown second-hop relations was 0%.

[Done] G2.6は制御された構造benchmarkで通過した。一hop roleのoutcomeが一意なら既存roleを維持する。同じaction・一hop roleから複数outcomeが生じた場合だけ二hopのrelation位置署名を検査し、細分化後のroleが一つのoutcomeへ対応するときだけ候補化する。5 seed・seedごとに独立development 800件・final 200件で、二hop roleは予測・compositionとも100%、一hop限定経路は50%だった。finalの対応bootstrap区間下限は最低+42.5ポイントで、欠落・未知の二hop relationへの誤型付けは0%だった。

[Done] G2.6在受控结构benchmark中通过。一hop role的outcome无歧义时保留既有role；同一action及一hop role产生多个outcome时才检查二hop relation位置签名，并仅在细分role对应单一outcome时生成候选。5个seed中，每个seed使用800个独立development案例和200个final案例；二hop role的预测及composition成功率均为100%，仅一hop路径为50%。final配对bootstrap区间下限最低为+42.5个百分点，对缺失或未知二hop relation的错误类型率为0%。

## Bounded structural contract / 有界構造契約 / 有界结构契约

- Role paths are limited to two hops by `MAX_ROLE_SIGNATURE_HOPS = 2`.
- One ambiguous base role can retain at most eight refinements, ranked deterministically by support and role ID.
- A two-hop signature that still contains multiple outcomes creates no candidate. Differences visible only at hop three therefore remain unresolved and produce abstention.
- Query resolution returns a shallow-to-deep role hierarchy. Existing one-hop candidates remain compatible; refined candidates activate only when the query supplies the distinguishing neighborhood.
- Missing distinguishing relations produce no refined role rather than a shared empty type.

role pathは最大二hop、一つの曖昧なbase roleからのrefinementは最大8件に固定した。候補はsupportとrole IDで決定的に選ぶ。二hopでもoutcomeが混ざる署名は候補化せず、三hop目だけに差がある例は未解決のままabstainする。queryは浅いroleから深いroleの順に解決するため、一hop候補との互換性を保ちつつ、識別近傍がある場合だけ細分化候補を起動する。relation欠落を共通の空型として学習しない。

role path最多为二hop，每个模糊base role最多保留8个refinement，并按support及role ID确定性排序。二hop签名若仍对应多个outcome则不生成候选，因此只有第三hop存在差异的案例保持未解决并弃答。query按从浅到深的顺序解析role，既保持一hop候选兼容性，也仅在存在区分邻域时激活细分候选。缺失relation不会被学习为共享空类型。

## Actor and arbitrary variables / actorと任意変数 / actor及任意变量

The same relation-position resolver now supplies roles for actors and every bound entity variable that lacks an external role. Temporal and relational plan candidates use those roles, and composition derives the corresponding query roles from new identities. In the held-out plan task, induced and supplied roles both reached 100% versus 50% with induction disabled. Each seed retained two collision candidates and two plan candidates; all reached `adopted` on disjoint evidence.

同じrelation位置resolverを、外部roleがないactorと全entity変数へ接続した。時間列・関係plan候補はそのroleを使い、composition queryも未知identityから対応roleを作る。held-out planは構造role版・外部role版とも100%、誘導無効版50%だった。各seedの候補は衝突2件・plan 2件で、すべて非重複証拠により`adopted`へ到達した。

同一relation位置resolver现用于未提供外部role的actor及全部entity变量。时间序列与关系plan候选使用这些role，composition query也可从新identity生成对应role。held-out plan中结构role版与外部role版均为100%，禁用归纳时为50%。每个seed保留2个冲突候选和2个plan候选，全部使用互不重叠的证据进入`adopted`。

| Final metric, mean over five seeds | Induced/refined | Supplied role | Restricted baseline |
| --- | ---: | ---: | ---: |
| Collision prediction success | 100% | 100% | 50% one-hop |
| Collision composition success | 100% | 100% | 50% one-hop |
| Missing/unknown-relation mistyping | 0% | — | — |
| Actor/arbitrary-variable plan success | 100% | 100% | 50% induction disabled |
| Combined persisted State bytes | 330,401.2 | 404,835.6 | — |

The induced States were 18.39% smaller in this benchmark because repeated external role strings were absent. This is a serialization measurement for these synthetic States, not a general complexity bound. Support-development, support-final and development-final overlap counts were all zero.

## Scope / 適用範囲 / 适用范围

The result establishes bounded structural disambiguation over observed symbolic relations. It does not infer relation semantics, discover latent relations from raw perception or prove performance on noisy real logs. Relational plan schemas still require stable variable names across demonstrations and queries even though the induced role IDs themselves do not depend on those names. The fixed two-hop ceiling intentionally leaves deeper ambiguity unresolved.

この結果は、観測済みsymbolic relation上の有界な構造曖昧性解消を示す。relationの意味推定、生の知覚からの潜在relation発見、noiseを含む実ログ性能は未証明である。誘導role ID自体は変数名に依存しないが、関係plan schemaはdemonstrationとqueryで安定した変数名をまだ必要とする。固定二hop上限は、深い曖昧性を意図的に未解決のまま残す。

该结果证明的是观测symbolic relation上的有界结构消歧，尚未证明relation语义推断、从原始感知发现潜在relation或含噪真实日志性能。虽然归纳role ID本身不依赖变量名，关系plan schema仍要求demonstration与query使用稳定变量名。固定二hop上限有意保留更深层歧义。

[Done] 後続のG3.1で1k・10k・100k Eventのindex版と全走査版を比較し、詳細を[G3.1 scale評価](G3-Scale-Evaluation-2026-09-13.md)へ記録した。

[Done] The subsequent G3.1 compared indexed and full-scan execution at 1k, 10k and 100k Events; see the [G3.1 scale evaluation](G3-Scale-Evaluation-2026-09-13.md).

[Done] 后续G3.1已在1千、1万及10万Event规模比较索引版与全扫描版，详见[G3.1规模评估](G3-Scale-Evaluation-2026-09-13.md)。

Reproducible inputs and complete rows are in `experiments/g2_role_disambiguation_manifest.json` and `docs/g2-role-disambiguation-results.json`. Manifest SHA-256: `fea4d5e3ea7567059e0c280b452f821c04e4ef1e6883a6cb6b4dafec325807d8`.
