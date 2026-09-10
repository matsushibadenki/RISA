# RISA MVP-1 技術設計書

> 2026-09-05: 現行の実装評価は[設計評価](RISA-Structural-AI-Assessment-2026-09-05.md)、優先順位は[ROADMAP](ROADMAP.md)、規範は[policy §0](policy.md)を参照。この文書の歴史的な仕様・仮説は、現行実装の完全性や性能の実証ではありません。
>
> Current assessment, priorities and rules are in the linked documents. Historical specifications/hypotheses here do not establish current completeness or performance.
>
> 当前评估、优先级与规则以上述链接为准。本文历史规格与假设不证明当前实现完整性或性能。

## 2026-09-08 G0実装追記 / G0 implementation addendum / G0实现补充

- 日本語: Primitiveの出力を原子的なeffect集合として扱い、純粋transition関数をsimulation、planning、Replayで共有する。Replay候補はbranch別に状態・資源・根拠を保持する。
- English: Primitive outputs are atomic effect sets. Simulation, planning, and replay share a pure transition function, while replay candidates retain independent state, resources, and evidence.
- 简体中文: 原语输出采用原子效果集合。模拟、规划与重放共享纯转移函数，重放候选逐分支保存独立状态、资源与证据。
- 日本語: Eventは`episode_id`と`source`を持ち、同一ID・同一内容はno-op、同一ID・異内容とepisode内の遅着は拒否する。
- English: Events carry `episode_id` and `source`; identical retries are no-ops, while conflicting IDs and late arrivals within an episode are rejected.
- 简体中文: Event包含`episode_id`与`source`；相同ID和内容的重试不产生变化，同ID异内容及回合内迟到事件会被拒绝。
- 日本語: 予測はactor/action/targetの観測根拠に接地し、根拠がなければ棄却する。claimは導出・仮説・棄却を区分する。
- English: Predictions are grounded in observed actor/action/target evidence and abstain when unsupported. Claims distinguish derived, hypothetical, and abstained results.
- 简体中文: 预测以已观测的actor/action/target证据为基础，无依据时弃答；claim区分推导、假设与弃答。
- 日本語: state schema v2は旧単一outputを移行し、同一directory内の一時fileと`os.replace`で原子的に保存する。破損時は検証済みbackupへ復旧する。
- English: State schema v2 migrates legacy single outputs, saves atomically through a same-directory temporary file and `os.replace`, and recovers from a validated backup.
- 简体中文: state schema v2迁移旧单一输出，通过同目录临时文件与`os.replace`原子保存，并可从已验证备份恢复。

## 2026-09-08 G2実装追記 / G2 implementation addendum / G2实现补充

- 日本語: 現行stateはschema v4である。v3でEventに追加した`actor_roles`、`target_roles`、`observed_states_before`、`before_state_observed`、`transition_succeeded`を保持し、v3以前を読込時に移行する。
- English: The current state uses schema v4. It retains the event role, before-observation and transition-success fields introduced in v3 and migrates states from v3 and earlier on load.
- 简体中文: 当前state采用schema v4，保留v3引入的Event角色、前态观测及转移成功字段，并在读取时迁移v3及更早版本。
- 日本語: target roleは`role:*` nodeと`has_role` edgeへ保存し、action/context/effect/actor/target/roleの派生evidence indexから予測根拠を取得する。indexは永続化せずimmutable Eventから再構築する。
- English: Target roles are stored as `role:*` nodes and `has_role` edges. Prediction reads a derived action/context/effect/actor/target/role evidence index, rebuilt from immutable events rather than persisted.
- 简体中文: target角色保存为`role:*`节点及`has_role`边。预测使用action/context/effect/actor/target/role派生证据索引；索引不持久化，而是从不可变Event重建。
- 日本語: `ChangeHypothesis`は同一action・target・contextの直近3件が旧outcomeと一致しない場合に生成する。予測時のrecency supportは0.5で、A→B→Aの新しい連続観測により再度置き換えられる。
- English: A `ChangeHypothesis` forms when the latest three observations for an action, target and context agree with each other and differ from the prior outcome. Prediction adds 0.5 recency support and later A observations can replace B again.
- 简体中文: 当同一action、target及context最近3次观测彼此一致且不同于旧结果时生成`ChangeHypothesis`。预测增加0.5近期支持，后续A观测可再次替换B。
- 日本語: `ApplicabilityHypothesis`は完全なbefore観測を持つ同一atomic outcomeについて、成功2件以上の全てに存在し、完全観測の失敗例には存在しないstateだけを前提候補にする。成功反例が現れた前提は撤回する。
- English: An `ApplicabilityHypothesis` keeps only states present in every one of at least two complete successful before observations and absent from complete failures for the same atomic outcome. A successful counterexample retracts the condition.
- 简体中文: `ApplicabilityHypothesis`仅保留同一原子结果至少2个完整成功前态中全部出现、且完整失败前态中未出现的状态；成功反例会撤回该条件。
- 日本語: graph保存は配列中心のlossless `compact-v1`形式へ変更し、legacy object形式も読める。Replayは`replay_max_events`で直近Event数を制限できる。
- English: Graph persistence uses a lossless array-oriented `compact-v1` format while retaining legacy object-format reads. `replay_max_events` bounds replay to recent events.
- 简体中文: 图持久化改为以数组为主的无损`compact-v1`格式，同时兼容旧object格式；`replay_max_events`可限制重放的最近Event数量。
- 日本語: `UnnamedConceptCandidate`は異なるtarget、source、episodeにまたがる共有schemaから生成する。derived/replay Eventを一次支持から除外し、developmentとfinalの証拠ID重複を拒否する。候補は`proposed -> provisional -> adopted/rejected`へ進み、支持または反例が変われば評価を無効化する。
- English: `UnnamedConceptCandidate` is generated from schemas shared across targets, sources and episodes. Derived/replay events cannot provide primary support, development/final evidence overlap is rejected, and changed support invalidates evaluation. The implemented lifecycle is `proposed -> provisional -> adopted/rejected`.
- 简体中文: `UnnamedConceptCandidate`由跨target、source及episode共享的schema生成。derived/replay Event不能作为主要支持，development与final证据重叠会被拒绝，支持变化会使评估失效；已实现生命周期为`proposed -> provisional -> adopted/rejected`。
- 日本語: 採用候補は非永続の`candidate_inference_index`へ載せる。予測は候補支持を明示し、計画は`derived:candidate:*`の一時Primitiveへ変換する。Eventと保存graphは変更せず、flagで候補利用を無効化できる。
- English: Adopted candidates enter a non-persisted `candidate_inference_index`. Prediction exposes candidate support and planning materializes `derived:candidate:*` ephemeral primitives. Events and the stored graph remain unchanged, and candidate use can be disabled.
- 简体中文: 已采纳候选进入不持久化的`candidate_inference_index`。预测会显示候选支持，规划将其转换为`derived:candidate:*`临时原语；Event及持久化图保持不变，并可关闭候选使用。
- 日本語: `temporal_sequence`候補は同一episode内で同じtargetとtarget roleを共有し、第1 Eventのeffectが第2 Eventの観測前提を満たす隣接2段階からだけ生成する。各stepは状態前提、消費状態、数値前提、変数差分、effectと`target_variable`を保持する。採用後はstart action・goal effect・target roleの派生indexから引き、同一target束縛を保つ一時macroとして純粋transition関数で適用する。
- English: A `temporal_sequence` candidate is generated only from adjacent two-step observations in one episode that share a target and target role and whose first effect satisfies an observed requirement of the second event. Each step retains state requirements, consumed states, numeric requirements, variable deltas, effects and a `target_variable`. Once adopted, a derived start-action, goal-effect and target-role index retrieves it as an ephemeral same-target macro applied through the pure transition function.
- 简体中文: `temporal_sequence`候选仅从同一回合内相邻的两步观测生成：两步共享target及target角色，且第一步效果满足第二个Event的观测前提。每一步保存状态前提、消耗状态、数值前提、变量差分、效果及`target_variable`。采纳后通过start action、goal effect及target角色的派生索引检索，并以保持同一target绑定的临时宏交给纯转移函数执行。
- 日本語: 同じstart actionとgoal effectを覆う採用済み型付きplanが存在し、queryのtarget roleに一致するplanがない場合、Compositionは無型Primitiveへfallbackせずabstainする。状態・数値条件の不成立はrole不一致と区別し、一致候補が適用不能な場合は通常探索を続ける。
- English: If an adopted typed plan covers a start action and goal effect but none matches the query target role, composition abstains instead of falling back to untyped primitives. Failed state or numeric applicability is distinguished from role mismatch; normal search remains available when a role-matching candidate is merely inapplicable.
- 简体中文: 若已采纳的类型化plan覆盖某start action与goal effect，但没有plan匹配query的target角色，则Composition弃答，不回退到无类型原语。状态或数值适用条件失败与角色不匹配分开处理；角色匹配候选仅因条件不适用时仍可继续普通搜索。
- 日本語: 同一actorが2段階を実行し、両Eventでactor roleも共有される場合、時間候補は`actor`と`target`の二変数を持つ。派生indexはtarget roleとactor roleの複合keyを使い、CompositionとCLIの`actor_roles`が一致する場合だけmacroを適用する。actor roleの欠落も型付きplanに必要な束縛不足としてabstainする。
- English: When the same actor performs both steps and the events share an actor role, the temporal candidate carries both `actor` and `target` variables. Its derived index uses a compound target-role and actor-role key. The macro applies only when composition and CLI `actor_roles` match; a missing actor role is treated as insufficient binding for the typed plan and abstains.
- 简体中文: 若同一actor执行两步且两个Event共享actor角色，则时间候选同时包含`actor`与`target`变量。派生索引使用target角色及actor角色的复合key；仅当Composition及CLI的`actor_roles`匹配时应用宏。actor角色缺失也被视为类型化plan的绑定不足并弃答。
- 日本語: actor role候補では、支持列すべてでactorとtargetが同一なら`equal`、すべて異なるなら`not_equal`を`variable_constraints`へ記録する。CompositionとCLIが具体actor/targetを渡した場合に制約を検査し、違反時は無型経路へfallbackしない。identityが片方でも未指定なら、この制約だけでは棄却しない。
- English: For actor-role candidates, `variable_constraints` records `equal` when actor and target are identical in every supporting sequence and `not_equal` when they always differ. Composition and CLI enforce the constraint when both concrete identities are supplied and do not fall back to an untyped path on violation. The identity constraint alone does not reject a query when either identity is absent.
- 简体中文: 对含actor角色的候选，若所有支持序列中的actor与target都相同，则`variable_constraints`记录`equal`；若始终不同，则记录`not_equal`。Composition及CLI在两个具体identity均提供时检查该约束，违规时不回退到无类型路径。若任一identity未提供，则不会仅因该identity约束而拒绝query。
- 日本語: Eventは後方互換のactor/targetに加えて、任意名の`entity_bindings`、変数ごとの`entity_role_bindings`、変数名を端点とする`entity_relations`と完全観測を示す`entity_relations_observed`を持てる。parserはroleとrelationが未定義変数を参照する入力を拒否し、relation配列が明示された場合は空配列でも完全観測とする。旧Eventの空でないrelation配列も完全観測として扱う。
- English: In addition to backward-compatible actor/target fields, events can carry arbitrary named `entity_bindings`, per-variable `entity_role_bindings`, `entity_relations` whose endpoints are variable names, and an `entity_relations_observed` completeness flag. The parser rejects undefined variable references and treats an explicitly supplied relation array as complete even when empty. Legacy non-empty relation arrays also count as complete.
- 简体中文: 除后向兼容的actor/target字段外，Event还可包含任意命名的`entity_bindings`、每个变量的`entity_role_bindings`、以变量名为端点的`entity_relations`及完整观测标记`entity_relations_observed`。parser拒绝未定义变量引用；显式提供的relation数组即使为空也视为完整观测，旧Event中的非空relation数组同样视为完整。
- 日本語: `relational_sequence`候補は同一episodeの隣接2 Eventでidentityが変数ごとに維持され、第1効果が第2前提を満たし、全変数に共有roleがある場合に生成する。候補は任意数のrole変数、step別relation、変数間equal/not_equalを保持する。Compositionはquery roleの包含、relation集合の包含、具体identity制約を全て満たす場合だけ一時macroを適用する。
- English: A `relational_sequence` candidate forms from adjacent events in one episode when identities remain stable per variable, the first effect satisfies a second-step requirement and every variable has a shared role. It retains any number of role variables, per-step relations and pairwise equality constraints. Composition applies the ephemeral macro only when query roles, relation inclusion and concrete identity constraints all match.
- 简体中文: 当同一回合的相邻两个Event中各变量identity保持稳定、第一步效果满足第二步前提、且每个变量都有共享角色时，生成`relational_sequence`候选。候选保存任意数量的角色变量、每步relation及变量间同一/差异约束。仅当query角色、relation包含及具体identity约束全部匹配时，Composition才应用临时宏。
- 日本語: relation前提は完全観測された全成功列のstep別共通部分であり、成功例の一部にだけあるrelationは観測noiseとして候補を分割しない。対応する完全観測失敗列が必要relationを欠く場合は`relation_negative_event_ids`へ、全て満たす場合は`counterexample_event_ids`へ記録する。新しい成功列が既存前提を欠くと共通部分から除かれ、relationを含まない安定候補IDのまま評価状態を`proposed`へ戻す。
- English: Relation requirements are the per-step intersection across all completely observed successful sequences, so relations appearing in only some successes are treated as observation noise rather than splitting candidates. A matching complete failed sequence goes to `relation_negative_event_ids` when it lacks a requirement and to `counterexample_event_ids` when it satisfies every requirement. A new success lacking an old requirement removes it from the intersection and resets the stable relation-independent candidate ID to `proposed`.
- 简体中文: relation前提取所有完整观测成功序列在每一步的交集，因此只出现在部分成功例中的relation作为观测噪声处理，不拆分候选。匹配的完整失败序列若缺少必要relation则记录到`relation_negative_event_ids`，若满足全部前提则记录到`counterexample_event_ids`。新成功序列若缺少旧前提，会将其从交集中撤回，并在保持与relation无关的稳定候选ID时把评估状态重置为`proposed`。
- 日本語: Eventから決定的に再構築できる頻度表とactivation indexはschema v3の保存payloadから除外し、読込時に再構築する。Eventを持たないlegacy payloadだけは旧indexをfallbackで読む。
- English: Count tables and the activation index are omitted from schema-v3 persistence and deterministically rebuilt from events. Legacy payloads without events retain a fallback to their stored indices.
- 简体中文: schema v3不再持久化可从Event确定性重建的频度表及activation索引，读取时重新生成；没有Event的旧payload仍回退读取旧索引。
- 日本語: schema v4は`UnnamedConceptCandidate`の構造schema、型変数、支持IDと反例IDを保存せず、採否・held-out評価値・構造と証拠のfingerprintだけを`candidate_evaluations`へ保存する。読込時にEventから候補を再発見し、fingerprintが一致する候補だけ評価状態を復元する。旧`unnamed_concept_candidates` payloadは引き続き読める。
- English: Schema v4 omits reconstructable candidate schemas, typed variables, support IDs and counterexample IDs. It stores only lifecycle state, held-out metrics and a structural-evidence fingerprint in `candidate_evaluations`. Loading rediscovers candidates from events and restores evaluation only when the fingerprint matches. Legacy full-candidate payloads remain readable.
- 简体中文: schema v4不再保存可重建的候选schema、类型变量、支持ID及反例ID，只在`candidate_evaluations`中保存生命周期、留出评估值及结构证据fingerprint。读取时从Event重新发现候选，仅在fingerprint一致时恢复评估状态；旧完整候选payload仍可读取。
- 日本語: schema v4のEvent payloadは辞書keyと重複する内部`id`、空list・空dict・`None`・既定の真偽値・既定episode/sourceを省略する。読込時は辞書keyとEvent dataclassの既定値から完全なEventを復元する。非既定値と観測内容は省略しない。
- English: Schema v4 event records omit the internal ID duplicated by the map key, empty collections, `None`, default booleans and default episode/source values. Loading restores complete events from the map key and Event dataclass defaults; observed and non-default values are retained.
- 简体中文: schema v4的Event记录省略与字典key重复的内部ID、空集合、`None`、默认布尔值及默认episode/source。读取时由字典key和Event dataclass默认值恢复完整Event；观测值及非默认值不会省略。
- 日本語: pattern・structural pattern・primitiveは辞書keyと重複するIDおよび既定値だけを省略するlossless recordを使う。PrimitiveのReplay統計・採用状態・適用前提、graphのenergy・dormancy・edge reliabilityは学習履歴なので保持し、Eventから推測再構築しない。
- English: Pattern, structural-pattern and primitive records losslessly omit only IDs duplicated by map keys and default values. Primitive replay metrics, adoption and applicability state plus graph energy, dormancy and edge reliability remain persisted as learning history rather than being guessed from events.
- 简体中文: pattern、structural pattern及primitive记录仅无损省略与字典key重复的ID及默认值。Primitive的Replay指标、采纳与适用状态，以及graph的energy、dormancy和edge reliability均作为学习历史保留，不从Event推测重建。
- 日本語: 派生候補は`derivation_type`、`parent_candidate_ids`、`parent_evidence_digests`、`derivation_generation`を持つ。specializationは親supportの非空部分集合だけを使い、mergeは同じschema kindと型roleを持つ二候補以上を要求する。共通祖先を持つDAGは許可し、循環または存在しない親は拒否する。
- English: Derived candidates carry a derivation type, parent IDs, parent-evidence digests and generation. Specialization uses only a non-empty subset of parent support; merging requires at least two candidates with compatible schema kinds and typed roles. DAGs with shared ancestors are valid, while cycles and missing parents are rejected.
- 简体中文: 派生候选包含`derivation_type`、父候选ID、父证据digest及派生代数。specialization只能使用父支持的非空子集；merge要求至少两个schema kind及类型角色兼容的候选。允许含共同祖先的DAG，拒绝循环及缺失父节点。
- 日本語: 派生候補のdevelopment/final評価は、自身のsupportに加えて全祖先のsupportとevaluation IDとの重複を拒否する。親fingerprintが変化した派生候補は次の発見・読込で復元しない。`dormant`は評価statusと分離し、採用知識を削除せず推論indexからだけ外す。
- English: Development and final evaluation for a derived candidate reject overlap with its own support and every ancestor's support and evaluation IDs. Derived candidates with changed parent fingerprints are not restored during later discovery or loading. Dormancy is separate from evaluation status and removes adopted knowledge only from inference indices.
- 简体中文: 派生候选的development/final评估拒绝与自身支持及所有祖先的支持和评估ID重叠。父fingerprint变化的派生候选不会在后续发现或读取时恢复。`dormant`与评估状态分离，只将已采纳知识移出推理索引而不删除。
- 日本語: candidate-backed compactionは指定回帰queryの`predicted_effects`が圧縮前後で一致する場合だけrole readoutを削除し、不一致なら原子的にrollbackする。directiveを保存して再読込時に再適用し、新規Event学習前には全readoutをEventから復元してdirectiveを破棄する。
- English: Candidate-backed compaction removes a role readout only when regression-query outputs match before and after, rolling back atomically on mismatch. Persisted directives reapply after reload; new learning restores all readouts from events and discards the stale directives.
- 简体中文: 候选支持的压缩仅在指定回归query的`predicted_effects`压缩前后一致时删除角色readout，不一致则原子回滚。directive会持久化并在重载后重新应用；新Event学习前从Event恢复全部readout并丢弃旧directive。
- 日本語: 実測値と未完了条件は[G2構造再利用評価](G2-Structural-Reuse-Evaluation-2026-09-08.md)と[ROADMAP](ROADMAP.md)を正とする。
- English: The [G2 evaluation](G2-Structural-Reuse-Evaluation-2026-09-08.md) and [ROADMAP](ROADMAP.md) are authoritative for measured results and unfinished gates.
- 简体中文: 实测结果及未完成门槛以[G2评估](G2-Structural-Reuse-Evaluation-2026-09-08.md)和[ROADMAP](ROADMAP.md)为准。

## 1. 目的

RISA MVP-1 の目的は、RISA の中核仮説である

> 知能の最小単位はノードではなく、関係更新である

を、**小さな人工世界における実用的な動作系**として検証することです。

この段階では自然言語の流暢な対話や大規模知識は目指しません。まずは以下を安定して実現することをゴールとします。

- 構造化イベント列を受け取れる
- イベントからノードと関係を生成できる
- 反復パターンを蓄積できる
- 類似したイベントから簡単な抽象概念を作れる
- 未知の近縁イベントに対して次イベントを予測できる
- 予測理由を経路として説明できる

MVP-1 の最終目標は、研究用デモではなく、**実際に繰り返し入力すると振る舞いが改善していく最小の RISA コア**を作ることです。

---

## 2. MVP-1 のスコープ

### 2.1 含めるもの

- 手入力または JSON ファイル入力の構造化イベント
- 動的グラフの生成と更新
- 局所的な関係強化とパターン蓄積
- 単純な抽象ノード生成
- 次イベント予測
- 推論経路の説明
- 永続化
- CLI による実行

### 2.2 含めないもの

- 自由入力の自然言語理解
- 画像、音声、センサ入力
- 反実仮想シミュレーション
- 文脈分裂による例外処理の完全対応
- 複雑な行動計画
- 分散実行
- GUI

ただし、画像や音声を永続的にスコープ外へ置くわけではありません。MVP-1 では「生データを直接扱わず、構造化イベントに変換された後の状態遷移だけを扱う」という境界を明確にするために除外しています。将来方針は [RISA 概念形成とマルチモーダル学習メモ](RISA-Concept-Formation-and-Multimodal-Notes.md) に整理します。

### 2.3 成功条件

MVP-1 は次を満たせば成功とみなします。

- 20 から 200 件程度のイベント列で安定動作する
- 未知の主体に対して既知パターンを転用できる
- 抽象ノードを少なくとも 1 種類自動生成できる
- 予測に理由グラフを付けられる
- 同一入力に対して再現可能な結果が得られる

---

## 3. 研究仮説を実装仮説へ落とす

RISA の思想は広いですが、MVP-1 では以下の実装仮説に縮約します。

### 3.1 実装仮説

1. 経験は「イベント」として離散化できる
2. イベント間の反復から、因果に近い遷移パターンを抽出できる
3. 類似イベント群から、上位概念ノードを生成できる
4. 予測は重み付き文生成ではなく、局所グラフ探索で実現できる
5. 説明可能性は、活性化経路を保存することで確保できる

補足:

ここでいう「イベント」は、単なる名詞の並びではなく、実質的には `State -> Event -> State` の状態遷移を縮約したものとみなします。この立場は将来の概念形成やマルチモーダル拡張に重要です。

### 3.2 MVP-1 における知能の定義

MVP-1 では、RISA の知能を次のように定義します。

- 経験を構造に変換する
- 構造を圧縮して再利用可能にする
- 新しい入力に対して、近い過去から次状態を予測する
- 予測の根拠を構造として返す

### 3.3 MVP-1 で採用する共有原理

MVP-1 では、
概念形成を
「同型な構造を明示探索してクラスタリングする処理」
としては作り込みません。

代わりに、次を優先します。

- 同じ役割署名を持つ経験が同じ共有パターンへ集まる
- 共有された action / effect / context が再利用回数を増やす
- 共通部分と差分は `StructuralPattern` と `StructureDelta` から得る

これは将来、

> 概念 = 繰り返し再利用される内部構造

へ進めるための最小近似です。

### 3.4 MVP-1 における構造検証の立場

MVP-1 では、
構造の妥当性を
独立した高知能 Verifier が
静的に判定する方式は主軸にしません。

優先するのは次です。

- 予測した effect と観測した effect のずれを見る
- 関連構造を同時活性化したときの共鳴と競合を見る
- 反復する構造を強め、再現しない構造を弱める

つまり、

> 構造を読むより、構造を再生してみて安定するかを見る

という立場です。

---

## 4. システム境界

MVP-1 の責務は RISA-Core のうち最小限に限定します。

```text
Input Events
  ->
Event Parser
  ->
Event Graph Builder
  ->
Relation Substrate
  ->
Pattern / Abstraction Updater
  ->
Predictor
  ->
Explanation
```

### 4.1 外部に置くもの

- 入力イベントの作成
- 実験データの選定
- 学習結果の可視化
- 将来の自然言語パーサー

### 4.2 内部に置くもの

- イベント正規化
- ノードとエッジの生成
- 経験蓄積
- パターン蓄積
- 予測誤差の最小計測
- 抽象化
- 予測
- 説明
- 保存と読み込み

---

## 5. ドメイン前提

MVP-1 は最初から一般世界を扱わず、**小さな人工世界**を対象にします。最初の推奨ドメインは「生物の行動と状態変化」です。

例:

- 走る -> 疲れる
- 休む -> 疲労が減る
- 飲む -> 喉の渇きが減る
- 食べる -> 空腹が減る
- 雨が降る -> 地面が濡れる

### 5.1 理由

- 因果と状態変化が明確
- ノード型を限定しやすい
- 予測の正誤を判定しやすい
- 抽象概念を作りやすい

---

## 6. データモデル

MVP-1 では、思想を守りつつも実装負荷を下げるため、データ構造を絞ります。

### 6.1 Node

```python
Node(
    id: str,
    kind: str,
    label: str,
    attributes: dict[str, str],
    abstraction_level: int,
    created_at: int,
    usage_count: int,
    stability: float,
    recent_activity: float,
    energy: float,
    last_activated_at: int,
    dormant: bool,
)
```

`recent_activity`, `energy`, `dormant` は、将来の Concept Cell 的な局所自律へつなぐための最小メタボリズム要素です。MVP-1 では完全な分裂・融合までは行わず、まずは「使われると活性化し、接続維持コストがあると休眠しやすい」という簡易制約を入れます。

#### kind の候補

- `entity`
- `process`
- `state`
- `concept`
- `pattern`

### 6.2 Edge

```python
Edge(
    source: str,
    target: str,
    relation_type: str,
    context_tags: tuple[str, ...],
    evidence_count: int,
    reliability: float,
    plasticity: float,
    last_updated: int,
)
```

#### relation_type の候補

- `participates_in`
- `affects`
- `precedes`
- `globally_precedes`
- `event_precedes`
- `event_globally_precedes`
- `causes`
- `instance_of`
- `similar_to`
- `abstracts_to`
- `predicts`
- `co_activates_with`
- `consumes_state`
- `updates_state_group`
- `allows_state`
- `requires_state_variable`
- `changes_state_variable`

`co_activates_with` は、同一イベント内で一緒に使われた構造を弱く結び、反復によって局所記憶を強めるための可塑性補助関係です。MVP-1 では最小形として導入し、将来は探索優先度や予測補正にも使えるようにします。

`reliability` と `plasticity` は、
将来的に
「よく再現する構造は安定し、
競合に負ける構造は弱まる」
という力学的検証へ接続するための足場でもあります。

現在の MVP-1 では、観測された `process -> state` の `affects` edge ごとに
`reliability` を少し上げ、`plasticity` を少し下げます。
さらに学習前予測が外れた場合は、その予測に使われた既存 edge の
`reliability` を下げ、`plasticity` を戻します。
これは「真偽を中央で決める」のではなく、再現された遷移だけを局所的に安定化する最小の可塑性則です。

将来の研究候補として、局所的に活性化した関係だけから対称親和行列または graph Laplacian を構成し、
固有値・固有空間を「局所構造の結合性、競合、文脈感度」を要約するスペクトルプローブに使う余地があります。
ただしこれは MVP-1 の更新規則ではありません。まず観測と予測誤差に基づく現在の検証規則を基準にし、
精度、説明可能性、計算コストのいずれかを明確に改善する実験結果が得られた場合のみ採用候補とします。

### 6.3 Event

MVP-1 では自然言語を避け、イベントを最初から構造化します。

```python
Event(
    id: str,
    timestamp: int,
    actor: str,
    action: str,
    target: str | None,
    preconditions: list[str],
    observed_effects: list[str],
    context_tags: list[str],
)
```

`preconditions` は Event が成立する前に観測された状態です。省略可能であり、
省略時は既存の action/effect 遷移として扱います。指定された場合だけ、
RISA は `State_t + Action -> State_{t+1}` の状態条件として primitive に保持します。

### 6.4 Episode

連続イベントをひとまとまりの経験列として扱います。

```python
Episode(
    id: str,
    events: list[Event],
    source: str,
)
```

### 6.5 Pattern

MVP-1 の抽象化と予測を安定化させるため、グラフ本体とは別に集計オブジェクトを持ちます。

```python
Pattern(
    id: str,
    signature: str,
    event_count: int,
    actors: set[str],
    actions: set[str],
    effects: set[str],
    support: int,
)
```

### 6.6 Graph Store

内部表現は次の辞書ベースで十分です。

```python
GraphStore(
    nodes_by_id: dict[str, Node],
    edges_by_key: dict[tuple[str, str, str], Edge],
    adjacency_out: dict[str, set[tuple[str, str]]],
    adjacency_in: dict[str, set[tuple[str, str]]],
)
```

### 6.7 Shared Structure Memory

MVP-1 では、
経験ごとに完結したグラフだけを保存するのではなく、
繰り返し再利用される共有構造を別記憶として持ちます。

```python
StructuralPattern(
    id: str,
    signature: str,
    role_signature: str,
    support: int,
    actions: set[str],
    effects: set[str],
    actors: set[str],
    context_tags: set[str],
    member_pattern_ids: set[str],
)
```

これは将来の
`shared relation unit`
ほど細かくはありませんが、
MVP-1 では
「複数経験が同じ内部表現を再利用する」
最初の足場として扱います。

### 6.8 StructuralPrimitive

MVP-1 では、共有構造をさらに細かい再利用候補として観察するため、
繰り返された `entity -> process -> state` 遷移から `StructuralPrimitive` を抽出します。

```python
StructuralPrimitive(
    id: str,
    relation_type: str,
    role_signature: str,
    input_conditions: set[str],
    input_state_conditions: set[str],
    consumed_states: set[str],
    state_group_updates: dict[str, str],
    numeric_preconditions: dict[str, float],
    state_variable_deltas: dict[str, float],
    output_state: str,
    temporal_constraint: str,
    context_tags: set[str],
    member_pattern_ids: set[str],
    evidence_event_ids: set[str],
    support: int,
    validation_score: float,
    reuse_score: float,
    compression_proxy: float,
    replay_count: int,
    replay_success_count: int,
    replay_score: float,
    deployment_replay_count: int,
    deployment_replay_success_count: int,
    deployment_replay_score: float,
    perturbation_replay_count: int,
    perturbation_replay_success_count: int,
    perturbation_replay_score: float,
    adoption_score: float,
    adopted: bool,
)
```

各 Event は `event_primitive_ids` により、どの primitive 候補の組合せで説明されたかを保持します。
MVP-1 の primitive は action/effect 遷移に限定され、任意の問題を因数分解・合成する完成機構ではありません。
今後、再利用性、再構成性、予測改善、記述長削減を比較して初めて、長期的な構造因子として採用します。

現実装では、候補を即座に推論へ使いません。複数 Event で再利用され、局所検証スコアと
圧縮代理値と replay 安定度から得る `adoption_score` が閾値を超えたものだけを `adopted` とします。
`compression_proxy` は小規模データでの暫定指標であり、厳密な Minimum Description Length や
複数 primitive による再構成性をまだ代替しません。

### 6.9 StructureDelta

MVP-1 では、
共有構造同士の差分も最小形で保存します。

```python
StructureDelta(
    id: str,
    source_pattern_id: str,
    target_pattern_id: str,
    role_signature: str,
    operations: list[str],
    support: int,
    context_tags: set[str],
)
```

目的は、

- 共通構造と差分を分けて観察すること
- 例外や変換パターンの芽を残すこと
- 将来の「変化パターン学習」へ接続すること

です。

### 6.10 Primitive Composition

MVP-1 では、採用済み primitive を action の時間的前後関係で局所探索し、
目標 effect へ到達する最小の合成経路を返せます。

```text
process:run
  -> primitive:run->fatigue_up
  -> precedes
  -> process:rest
  -> primitive:rest->fatigue_down
```

CLI では `compose --start-action ... --start-state ... --goal-effect ...` として利用します。
`--start-state` を渡すと、各 primitive の `input_state_conditions` を満たす経路だけを通ります。
これは状態を追加的に積み上げる最小探索であり、状態の消費、否定、資源量、因果制約、
複数未来候補のシミュレーションを備えた完成済み計画器ではありません。

同じ状態条件と action に複数の採用済み primitive が適用できる場合は、
`forecast --action ... --current-state ...` が effect 候補を一つに潰さず返します。
各候補には primitive ID、状態条件、採用スコアを含む根拠経路を付けます。
これは次状態候補の列挙です。複数ステップの候補保持は後述のbranch simulationが担当し、
行動選択はまだ扱いません。

### 6.11 Event Memory and Candidate Validation

MVP-1 の最小設計では、
新しい経験をすぐに確定知識とみなすのではなく、
少なくとも概念上は次の順を取ります。

```text
Event Memory
  ->
Structure Candidate
  ->
Replay / Reactivation
  ->
Resonance / Conflict
  ->
Long-term Structure
```

MVP-1 では、学習バッチ後に過去 Event を現在の予測器へ再投入し、観測 effect を再現できるかを
`replay_score` として Primitive に戻します。これは、モデル自身が形成した現在の世界モデル上で
記憶を再評価する最小の drift monitor です。

さらに deployment replay では、actor ごとの active state を観測値で毎回リセットせず、前段で
採用済み Primitive が予測した effect を次段の入力状態へ渡します。これにより、clean replay では
見えない自己生成軌跡上の drift を `deployment_replay_score` として分離して記録します。現段階では
状態を集合へ追加するだけで、状態の消費、置換、確率的サンプリングは扱いません。
したがって、現実装は決定的な短距離 deployment replay であり、確率的な長期 on-policy rollout や、
候補を一時記憶から長期記憶へ物理的に移す二層ストアではありません。

controlled perturbation replay では、active state が存在する各ステップで、event IDから決定的に
一状態を選んでdropoutし、同じ観測effectを再現できるか測ります。結果は
`perturbation_replay_score`へ保存しますが、必要なpreconditionへの依存まで誤りとして罰しないため、
現段階ではadoption scoreへ加えません。これは冗長性と単一点依存を見つける診断指標です。

### 6.12 Structural Adaptation Candidate

Replay結果は即時の構造破壊ではなく、局所的な編集候補へ変換します。

```python
StructuralAdaptationCandidate(
    primitive_id: str,
    reason: str,
    proposed_operation: str,
    pressure: float,
    evidence: dict[str, float | int],
)
```

現実装の局所ルールは次です。

- clean replayが不安定: `SPLIT_CONTEXT`
- clean replayは安定しdeployment trajectoryだけ不安定: `REPAIR_TRANSITION`
- 通常trajectoryは安定しstate dropoutだけに弱い: `ADD_REDUNDANT_PATH`

候補は`structural_adaptation_candidates`へ永続化し、操作ごとに安全条件を設けます。

MVP-1では`SPLIT_CONTEXT`だけを自動実行します。次の条件をすべて満たす必要があります。

- 元Primitiveに紐づく証拠Eventが存在する
- 証拠Eventを二つ以上の実在context群へ分配できる
- 各variantが元Primitiveのrelation、role、state条件、outputを継承する
- 元Primitiveを削除せず、`superseded_by`で履歴を保持する
- 分裂後の新規Eventを一致するcontext variantへルーティングする

候補の`status`は`proposed`、`executed`、`blocked`のいずれかとし、生成したvariant IDを
`result_primitive_ids`へ保存します。

`REPAIR_TRANSITION`は、対象Primitiveの証拠Eventごとに同一actorの直前Eventを探し、その観測effectが
Primitiveのpreconditionと一致する場合だけ`precedes`を追加・強化します。結果のedge IDは
`result_structure_ids`へ保存します。一致する観測がなければ候補を`blocked`とし、既存edgeも強化しません。
これは新しい因果関係の生成ではなく、複数actorのイベント混在で欠落した局所時間関係の復元です。

通常学習でも時間関係を二種類に分離します。

- `precedes`: 同一actor内で直前に起きたaction間の局所順序。Primitive compositionに使用する。
- `globally_precedes`: actorを問わない入力Eventの到着順。観測履歴として保持し、因果合成には直接使わない。

`train_events`を複数回呼ぶ場合は、保存済みEventから全体末尾とactor別末尾を復元して新しいバッチを
接続します。これにより継続学習の呼び出し境界で時間系列が切れません。現段階ではaction/process単位に
集約したedgeに加え、個々のEvent間にも次を保存します。

- `event_precedes`: 同一actorの具体的なEvent間順序
- `event_globally_precedes`: actorを問わない具体的なEvent到着順

`event_precedes`は予測の`supporting_paths`にも含め、集約されたaction規則だけでなく、どの具体的経験列が
根拠になったかを説明します。`event_globally_precedes`は観測順序の保持に限定し、予測因果の根拠へは
直接利用しません。

### 6.13 State Consumption

Eventは任意の`consumed_states`を持てます。

```python
Event(
    preconditions=["charged"],
    consumed_states=["charged"],
    action="use",
    observed_effects=["depleted"],
)
```

Primitiveは`consumed_states={"state:charged"}`を継承し、Graphには
`event -> consumes_state -> state`を保存します。forecastはeffectとともに`removed_states`を返し、
Compositionとdeployment replayは次状態を次の順で更新します。

```text
next_states = (current_states - consumed_states) + predicted_effects
```

これにより、資源、権限、一時フラグなど、一度使うと失われる状態を表現できます。既存Eventは
`consumed_states`省略時に空集合となり互換性を維持します。現段階では量的資源や、
複数effect間の原子的更新までは扱いません。

### 6.14 Exclusive State Groups

排他的状態の置換には`state_group_updates`を使います。

```python
Event(
    action="charge",
    state_group_updates={"battery": "charged"},
    observed_effects=["charged"],
)

Event(
    action="use",
    preconditions=["charged"],
    state_group_updates={"battery": "depleted"},
    observed_effects=["depleted"],
)
```

RISAはgroupごとに観測された状態候補を`exclusive_state_groups`へ蓄積します。Primitive実行時は、
更新先以外の同一group状態を削除してから新状態を追加します。

Graphには`event -> updates_state_group -> state_group`と
`state_group -> allows_state -> state`を保存します。group更新値は同じEventの`observed_effects`にも
含まれなければならず、観測されていない状態置換は入力時に拒否します。排他性は明示宣言されたgroupに
限定し、名前の類似性だけから自動推定しません。

### 6.15 Numeric State Variables

量的資源には最低必要量と増減量を使います。

```python
Event(
    action="refill",
    state_variable_deltas={"energy": 10.0},
    state_variable_specs={
        "energy": StateVariableSpec(unit="joule", minimum=0.0, maximum=10.0)
    },
    observed_effects=["fueled"],
)

Event(
    action="spend",
    numeric_preconditions={"energy": 5.0},
    state_variable_deltas={"energy": -5.0},
    observed_effects=["spent"],
)
```

forecastとCompositionは現在値がminimum以上のPrimitiveだけを候補にし、更新後の全変数が宣言された
上下限内に収まる場合だけ遷移を許可します。複数deltaは仮状態へまとめて適用され、一つでも範囲外なら
全更新を棄却します。deployment replayはactorごとの
作業変数へ最上位候補のdeltaを加算します。Graphには`requires_state_variable`と
`changes_state_variable`を保存します。数値は有限実数だけを受け付けます。forecast結果は
`variable_deltas`に加えて、原子的適用後の`resulting_variables`も返します。

同じ変数へ矛盾するunit、minimum、maximumが宣言された場合は、EventやGraphを更新する前のpreflightで
学習バッチを拒否します。未指定の仕様は後続Eventで補完できますが、確定済み仕様を暗黙変換しません。

CLIでは次のように指定できます。

```bash
python3 -m risa.cli.main forecast --action spend --variable energy=5 --state-dir state
python3 -m risa.cli.main compose --start-action refill --goal-effect spent \
  --start-variable energy=10 --state-dir state
```

現段階では単位名を保持して同一変数の整合性検査に使いますが、単位変換は行いません。deployment replayでは
不確実な複数候補のうち最上位候補だけのdeltaを
作業変数へ原子的に適用します。

`data/stateful_world.json`は、排他的battery状態と`joule`単位のenergyを組み合わせたMVP-1状態遷移
ベンチマークです。`energy=5`では`use`が成立し、`energy=4`では候補が生成されないことを検証します。

### 6.16 Branch Simulation

`simulate_branches`は、各未来候補を独立した`TrajectoryBranch`として展開します。branchは
`current_states`、`current_variables`、累積score、採用したPrimitiveを共有可変状態なしで保持します。
各stepには更新前後の状態と量的変数、削除状態を記録するため、結果だけでなく遷移過程も説明できます。

探索は`max_steps`、`max_branches`、`max_candidates_per_step`で制限するbounded beam searchです。
通常のforecastは採用済みPrimitiveだけを返しますが、branch simulationは、支持数2以上かつclean Replayを
2回以上行い成功率0.8以上の少数候補も探索対象へ残します。これにより単一予測の多数派選択と、未来探索での
不確実性保持を分離します。未反復候補やReplay不安定な候補は採用しません。

```bash
python3 -m risa.cli.main simulate --start-action route \
  --start-variable energy=5 --max-steps 2 --max-branches 4 --state-dir state
```

`data/branching_world.json`では、安全経路と高速経路が別branchとなり、二段目のpreconditionとenergy更新が
互いに混ざらないことを検証します。これは未来候補を保持するMVPであり、goal最適化、反実仮想介入、
確率校正、リスク評価、環境への実行は次段階です。

### 6.17 Branch Evaluation

`evaluate_branches`はbranch simulationの結果を次の独立成分で評価します。

- `goal_score`: 指定した代替goal状態のいずれかが終端状態に存在するか
- `confidence_score`: branch累積scoreをstep数で幾何平均した値
- `cost_penalty`: 開始時から終端までに正味消費した量的状態へ利用者指定weightを掛けた値
- `risk_penalty`: trajectory中に一度でも通過したavoid状態の割合

utilityはMVP固定係数で、`0.55 goal + 0.20 confidence - 0.15 cost - 0.10 risk`です。costは
`1 - exp(-weighted_cost)`で0から1へ正規化します。ただし選択はutilityだけで行わず、goal達成を
辞書順で最優先にします。どのbranchもgoalへ到達しない場合は、診断用評価を残したまま
`selected_branch_id = null`を返します。

```bash
python3 -m risa.cli.main evaluate --start-action route \
  --goal-state arrived_safe --goal-state arrived_fast \
  --avoid-state fast_path --start-variable energy=5 \
  --cost-variable energy=0.1 --max-steps 2 --state-dir state
```

出力は選択IDだけでなく、全branch、各評価成分、matched goal、encountered risk、変数別costを含みます。
このため選択理由を単一scoreへ隠しません。複合goalとhard constraintは後述のGoal Specificationが担当します。
期限、行動cost、探索中pruning、確率校正、Pareto frontierは未実装です。avoid状態やgoal条件は外部から
与える必要があり、RISAが危険性や価値を自律的に理解したことを意味しません。

### 6.18 Goal Specification

複合目標は`GoalSpecification`で表します。

```python
GoalSpecification(
    required_states=["safe_path"],
    any_state_groups=[["arrived_safe", "arrived_fast"]],
    minimum_variables={"energy": 1.0},
    maximum_variables={},
    forbidden_states=["fast_path"],
)
```

`required_states`はすべて必要なAND節です。`any_state_groups`は各group内がOR、group間はANDです。
数値条件は終端変数へ適用します。`forbidden_states`は終端だけでなく`states_before`と`states_after`を含む
trajectory全体で検査するhard constraintです。

評価結果は`goal_satisfied`、`hard_constraints_satisfied`に加え、missing required state、未達OR group、
未達数値条件、違反hard constraintを別々に返します。`goal_score`は満たしたgoal節の割合であり、完全達成の
代用にはしません。選択には完全達成とhard constraint適合の両方が必要です。

CLIでは`--require-state`、`--goal-state`、`--min-variable`、`--max-variable`、`--forbid-state`を使います。
旧来の`goal_states` APIは一つのOR groupへ変換して互換性を維持します。

離散的な禁止状態はsimulation中に早期pruningします。終端数値goalなど、後続遷移で回復し得る条件は
simulation後に評価します。時間期限、作用禁止、数値制約のtrajectory-wide検査、nestedな論理式は次段階です。

### 6.19 Constraint-Aware Search

`simulate_branches_with_diagnostics`は`forbidden_states`を受け取り、初期状態と各候補遷移後の状態集合を
検査します。禁止状態を含むbranchは`next_actions`へ渡さず、その場で破棄します。従来の
`simulate_branches`は同じ実装を呼ぶwrapperで、戻り値をbranch配列のまま維持します。

診断結果は次を含みます。

- `expanded_candidate_count`: Primitiveから生成して制約検査した候補数
- `constraint_pruned_count`: 禁止状態により展開を止めた候補数。初期状態違反も含む
- `beam_pruned_count`: `max_branches`制限で除外した候補数

`evaluate` CLIはGoal Specificationの`forbidden_states`をsimulationへ渡し、診断値を
`search_diagnostics`として評価結果へ含めます。hard constraint違反branchは評価候補に残りません。
一方、`avoid_states`はsoft riskなので早期除外せず、risk/costとのtrade-off比較に残します。

このMVPで早期検査するのは離散的な禁止状態だけです。終端goalの数値上下限を途中で適用すると、後続actionで
回復可能なbranchまで誤って除外するためpruneしません。時間期限、禁止action、trajectory全体の数値bound、
将来回復可能性を考慮したadmissible heuristicは未実装です。またpruned branchの全内容は保存せず、件数のみを
監査情報として残します。

### 6.20 Counterfactual Planning

`InterventionSpecification`はbaseline作業状態への一時的な介入を表します。

```python
InterventionSpecification(
    id="boost_energy",
    start_action=None,
    add_states=[],
    remove_states=[],
    variable_overrides={"energy": 5.0},
    cost=0.25,
)
```

`plan_counterfactuals`はbaselineと各介入について、状態・変数をコピーし、constraint-aware simulationと
branch evaluationを独立実行します。介入は開始actionの置換、初期状態の追加・削除、初期数値変数の上書きを
行えます。同じ状態の追加と削除、負・非有限cost、非有限variable override、重複IDは拒否します。

各`CounterfactualOutcome`は介入仕様、branch評価、実現可能性、介入cost penalty、plan scoreを保持します。
plan scoreは選択branchのutilityから`0.15 * (1 - exp(-intervention_cost))`を引いたMVP指標です。
完全goal達成かつhard constraint適合のbranchを持つ介入だけを選択可能とします。baselineも予約ID
`baseline`として同じ比較表へ含めます。

CLIの`plan --interventions FILE`はJSON配列から介入案を読み込みます。`data/branching_interventions.json`は、
energy不足のbaseline、energy上書き、禁止状態注入、未知actionを比較し、実現可能なenergy介入を選択する
ベンチマークです。

Counterfactualは観測済みPrimitiveに基づく仮想展開であり、介入の因果効果を実験的に同定したものではありません。
介入案は外部から明示的に与え、現段階では自動生成しません。simulation結果をEvent Memoryや永続Graphへ
書き戻さず、実環境でactionを実行する機能も持ちません。

### 6.21 Intervention Candidate Generation

`generate_intervention_candidates`はGoal Specificationのrequired stateと各OR groupの候補状態を集め、それらを
出力する`StructuralPrimitive`だけを逆向きに調べます。候補生成へ使えるPrimitiveは、採用済み、または支持数2以上・
clean Replay 2回以上・Replay成功率0.8以上のものに限定します。query contextとPrimitive contextが明示的に
競合する場合も除外します。

各Primitiveから次を生成します。

- Primitiveのprocess入力を介入後の`start_action`とする
- 未充足の`input_state_conditions`を`add_states`候補とする
- `numeric_preconditions`を満たす最低開始値を`variable_overrides`候補とする
- 終端minimum goalとPrimitive deltaから`minimum - delta`を逆算する
- action変更、状態追加、数値変更量から説明用heuristic costを付ける
- `generation_reason`と`evidence_primitive_ids`を保持する

禁止状態を直接出力するPrimitiveや、禁止状態の追加を必要とする候補は生成しません。CLIでは
`plan --generate-interventions`を使い、`--max-generated-interventions`で候補数を制限します。手動の
`--interventions`と併用することもできます。

この生成は単一Primitiveの局所的な逆写像です。複数Primitiveのbackward chaining、maximum goalからの逆算、
必要状態を作る前段actionの再帰生成、状態削除案、学習済み介入cost、因果介入の同定は扱いません。heuristic costは
候補順序を安定させるためのMVP値で、現実の費用を意味しません。生成案は必ずcounterfactual simulationと
Goal Evaluationを通し、生成しただけでは採用・実行しません。

### 6.22 Backward Goal Decomposition

`generate_backward_intervention_candidates`は終端goal状態を出力するPrimitiveから開始し、その
`input_state_conditions`を出力する前段Primitiveを再帰的に探します。前段actionから後段actionへの
actor-local `precedes` edgeが観測されている場合だけchainへ接続します。`globally_precedes`は使用しません。

生成したchainは次を保持します。

- `suggested_action_sequence`: 前段から終端までのaction列
- `evidence_primitive_ids`: 同じ順序のPrimitive根拠列
- 外部から必要なまま残る`add_states`
- chain全体を終端から逆走して求めた`variable_overrides`

数値逆算は各変数について後段から前段へ進み、各stepの`numeric_preconditions`と
`required_before >= required_after - delta`を満たす最小開始値を求めます。例えば終端`energy >= 2`、
前段delta `energy=-2`なら開始値4を提案します。

探索は`--backward-depth`と`--max-generated-interventions`で制限し、訪問済みPrimitive IDによって循環を
止めます。禁止状態を出力・要求するchainは候補から除外します。単段候補とchain候補は同じplannerで
cost、goal、constraintを比較します。

現段階は線形chainです。複数の未充足preconditionを別々のsubplanで作るAND/OR plan graph、状態消費により
後段条件が壊れる場合の静的検査、代替action列の組合せ最適化は扱いません。またplannerのsimulationは
開始action以降をlearned `precedes`で展開するため、`suggested_action_sequence`を強制実行してはいません。
次段階ではsequenceそのものをstepごとに照合して実現性を検証します。

### 6.23 Sequence-Constrained Simulation

`simulate_action_sequence_with_diagnostics`は、`suggested_action_sequence`を固定順序で実行します。最初に全隣接
action pairをactor-local `precedes`で検査し、一つでも未観測ならPrimitive展開前に失敗します。その後、各stepで
現在の離散状態・数値変数に適用可能な支持済みPrimitiveだけを展開し、状態削除、排他更新、数値delta、禁止状態を
通常のbranch simulationと同じ意味論で適用します。

完全なaction列を通過したbranchだけを返し、`terminated_reason="sequence_complete"`とします。途中で候補が
なくなったbranchは成功結果へ残しません。診断値は次です。

- `sequence_failed_count`: 空sequence、初期constraint違反、途中で適用候補が消えたbranchの数
- `invalid_sequence_edge_count`: 観測済み`precedes`がない隣接action pairの数
- 通常と共通のexpanded candidate、constraint prune、beam prune

Counterfactual plannerは`suggested_action_sequence`を持つ介入に限ってこのsimulationを使用します。手動介入や
単段候補は従来の自由branch simulationを使います。介入の`start_action`とsequence先頭が異なる場合は拒否します。

このMVPはaction順序を固定しますが、各actionに複数のeffect Primitiveが適用できる場合はbranchを保持します。
複数前提を満たすsubplanの合流、並行action、部分順序、同じactionの異なるPrimitiveをIDで固定する機能は
未実装です。したがって実環境向けexecutorではなく、提案sequenceの構造的実現可能性検証器です。

### 6.24 Conjunctive Plan Graph

`ConjunctivePlanGraph`はPrimitive IDをnode、前提stateの供給関係を`PlanGraphDependency` edgeとして保持します。
`generate_conjunctive_plan_candidates`は終端Primitiveの全`input_state_conditions`を調べ、各前提を出力する
支持済みPrimitiveを再帰的に追加します。同じ前提が後続の複数nodeで必要な場合、producer nodeを共有します。

```text
prepare_frame -> frame_ready -> prepare_power
       |                            |
       +------ frame_ready ---------+-> launch
                    power_ready --------> launch
```

外部から供給するしかない前提は`unresolved_states`に残し、介入の`add_states`として明示します。依存graphは
topological constraintを満たし、かつ隣接action間に観測済み`precedes`がある順序へ線形化します。最大7 node、
`--backward-depth`以内に制限し、線形化できないgraphは候補にしません。生成sequenceは既存の
Sequence-Constrained Simulationで再検証します。

`data/conjunctive_world.json`は`launch`が`frame_ready AND power_ready`を要求する評価世界です。plan graphは
3 Primitiveと3 state dependencyを形成し、`prepare_frame -> prepare_power -> launch`を完走します。線形chainと
plan graphが同じscoreとcostの場合は、依存関係を説明できるplan graphを優先します。

現段階では各required stateについてID順の最初の適用可能producerを一つ選びます。複数producerのOR分岐、
複数actionが同名の場合の厳密Primitive割当、並行実行、部分順序のままのsimulation、7 nodeを超える効率的な
線形化は未実装です。

日本語: 複数のAND前提を、説明可能なPrimitive依存graphとして統合します。

English: Multiple conjunctive prerequisites are integrated into an explainable primitive dependency graph.

简体中文: 将多个合取前提整合为可解释的原语依赖图。

### 6.25 Disjunctive Subplan Search

`generate_disjunctive_plan_candidates`は、終端Primitiveの直接前提を生成できる支持済みPrimitiveを一つに
決め打ちせず、前提ごとのproducer集合として保持します。集合の直積を上限付きで列挙し、各組合せを独立した
`ConjunctivePlanGraph`へ変換します。同じ終端Primitiveに属する候補は`alternative_group_id`を共有し、
`selected_producers`にrequired stateから採用Primitiveへの対応を記録します。

各variantは、再帰的な前提解決、action列への線形化、数値資源の逆算を経た後、通常の
Sequence-Constrained Simulationで厳密に再生されます。plannerは可否、goal score、介入costを同じ基準で比較し、
OR候補を生成時のID順だけで選びません。`data/disjunctive_world.json`では、安全経路と高速経路の両方を保持し、
終端の最低資源制約まで含めると追加資源を必要としない安全経路を選択します。

探索爆発を避けるため候補数を`max_candidates`で制限します。この段階では複数producerを終端Primitiveの直接前提
だけで列挙していました。次節のNested AND-OR Plan Graphで入れ子前提まで拡張します。確率的producer、
Pareto front、部分順序の直接simulationは引き続き未実装です。

日本語: 代替producerを消さずに保持し、同一条件の実行結果から選択します。

English: Alternative producers remain explicit and are selected by comparable execution evidence.

简体中文: 保留显式的替代生产者，并依据可比较的执行证据进行选择。

### 6.26 Nested AND-OR Plan Graph

Disjunctive Subplan Searchを再帰化し、終端Primitiveだけでなく、選択したproducer自身の全前提にも同じ
AND/OR展開を適用します。各Primitiveの前提集合はAND、各required stateを生成可能なPrimitive集合はORです。
探索branchはPrimitive IDのvisited集合を持ち、循環を除外します。producerとconsumerの間には、指定contextで
観測済みの`precedes`到達経路が必要です。

```text
                    launch
                      AND
                  power_ready
                       |
                  charge_core
                       AND
                  supply_ready
                   /       \
          collect_solar   draw_grid
```

各完成variantは`selected_producers`に直接・入れ子双方の選択を保持します。`alternative_choice_count`は複数producerが
存在した選択点数、`dependency_depth`は終端から最深producerまでのdependency edge数です。候補上限を超えた場合は
`alternative_search_truncated=true`とし、探索が完全だったかを隠しません。

`data/nested_and_or_world.json`では、直下producerが一つしかないため旧direct-OR方式では候補を作れませんでした。
再帰探索は二段目の`collect_solar OR draw_grid`を発見し、数値資源を逆算して両方を厳密simulationします。

現在もgraphを実行する前に最大7 Primitiveの全順列から有効な線形列を探します。このため、独立したAND subplanが
増えるとfactorialに増加します。部分順序のままready nodeを実行するexecutor、同名actionのPrimitive ID固定、
確率的OR、探索全体のPareto pruningは未実装です。

日本語: AND/OR依存を末端まで展開し、探索の深さと打切りを説明可能にします。

English: AND/OR dependencies expand to leaves with explicit depth and truncation evidence.

简体中文: 将AND/OR依赖展开到叶节点，并明确记录深度与截断证据。

### 6.27 Partial-Order Plan Execution

`simulate_plan_graph_with_diagnostics`は、plan graphを事前に一つのaction列へ固定せず、各branchで未実行Primitiveの
incoming dependencyを検査します。全producerが完了したnodeをreadyとし、現在のstate・数値変数・contextへ
実際に適用できるnodeだけを展開します。複数ready nodeは異なる実行順branchになります。

実行候補はaction名だけで選ばず、`plan_graph.primitive_ids`が指定したPrimitive IDと一致するforecastだけを採用します。
これにより同じactionに複数effectや条件違いのPrimitiveがある場合も、計画外の構造へすり替わりません。全node完了時は
`terminated_reason="plan_graph_complete"`です。

診断値は次です。

- `ready_node_expansion_count`: dependency上readyになり、適用を試みたnode数
- `deadlock_count`: 未実行nodeがあるのにreadyまたは適用可能nodeがないbranch数
- `primitive_mismatch_count`: graph参照先不在、graph外dependency、action条件欠落の数
- 共通のexpanded candidate、constraint prune、beam prune

候補生成時の説明用`action_sequence`はKahn型topological sortで線形時間に作り、旧来の最大7 node全順列探索は
廃止します。実行器はそのsequenceには依存しません。9 nodeのwide graphを使うテストで、独立した8 producerを
複数順序で実行し、終端Primitiveまで完走することを検証します。

現段階では実並列実行ではなく、partial orderの逐次interleavingです。また、独立node間で一方が他方の必要stateを
consumeするthreat、排他state更新、共有numeric resourceの競合を事前解析してdependencyを追加する機能はありません。
これらは実行時branch失敗としては観測できますが、次段階ではplan graph生成時に明示します。

日本語: 全順列を作らず、依存を満たしたPrimitiveをID固定で直接実行します。

English: Dependency-ready primitives execute by exact ID without enumerating all total orders.

简体中文: 无需枚举所有全序，按精确ID执行依赖已满足的原语。

### 6.28 Plan Graph Threat Detection

`detect_plan_graph_threats`は、plan graph内のPrimitive間干渉を実行前に静的検査し、`PlanGraphThreat`として保存します。

検出対象:

- `state_clobber`: sourceが、affected Primitiveの必要stateをconsumeする
- `exclusive_state_clobber`: sourceの排他group更新が、affected Primitiveの必要stateを置換する
- `numeric_resource_contention`: dependencyで順序づけられていない2 Primitiveが同じ数値資源を減少させる

各threatはsource/affected Primitive ID、stateまたはvariable、severity、現在のordering、resolution hint、説明を持ちます。
dependencyの推移閉包で、破壊側が先なら`high`、利用側が先なら`low`、未順序なら`medium`とします。

```text
prepare_shared
   /       \
use_shared  consume_shared
   \       /
      finish
```

この例では`consume_shared`が`use_shared`の必要stateを消費します。両者は同時readyなので、consume先行branchは
deadlockしますが、use先行branchは完走できます。そのため検出時点でplan全体を拒否せず、threatを保持したまま
partial-order executorで順序を比較します。planner診断の`declared_threat_count`からplanに含まれる静的threat数を
確認できます。

numeric resource contentionは不足の証明ではなく潜在競合です。十分な初期資源があれば両方実行できます。また、
producerによる途中補給、排他groupの再生成、複雑なcausal link保護までは解析しません。現段階ではordering edgeを
自動追加せず、次段階で安全性と循環を検査したrepair候補として提案します。

日本語: 独立subplan間の干渉を説明可能なthreatとして保持し、実行順で検証します。

English: Cross-subplan interference is retained as an explainable threat and tested through execution order.

简体中文: 将子计划间干扰保留为可解释冲突，并通过执行顺序进行验证。

`ADD_REDUNDANT_PATH`は存在しない因果経路を生成してしまう危険があるため、現段階では提案に留めます。

理由:

- 実装が単純
- シリアライズしやすい
- 局所探索が高速
- 将来 NetworkX や Rust 実装へ置き換えやすい

---

## 7. 入力仕様

MVP-1 の標準入力は JSON Lines または JSON 配列とします。

### 7.1 単一イベント例

```json
{
  "id": "e001",
  "timestamp": 1,
  "actor": "dog",
  "action": "run",
  "target": null,
  "observed_effects": ["fatigue_up"],
  "context_tags": ["animal", "movement"]
}
```

### 7.2 エピソード例

```json
[
  {
    "id": "e001",
    "timestamp": 1,
    "actor": "dog",
    "action": "run",
    "target": null,
    "observed_effects": ["fatigue_up"],
    "context_tags": ["animal", "movement"]
  },
  {
    "id": "e002",
    "timestamp": 2,
    "actor": "dog",
    "action": "rest",
    "target": null,
    "observed_effects": ["fatigue_down"],
    "context_tags": ["animal", "recovery"]
  }
]
```

### 7.3 制約

- `actor` と `action` は必須
- `observed_effects` は 1 個以上を推奨
- `timestamp` は同一エピソード内で単調増加
- `context_tags` は 0 個以上

---

## 8. コアアーキテクチャ

推奨ディレクトリ構成は以下です。

```text
risa/
  core/
    models.py
    graph_store.py
  engine/
    event_parser.py
    graph_builder.py
    learner.py
    abstractor.py
    predictor.py
    explainer.py
    persistence.py
  cli/
    main.py
  data/
    toy_world.json
  tests/
    test_graph_builder.py
    test_predictor.py
    test_abstractor.py
```

### 8.1 モジュール責務

#### `models.py`

- `Node`
- `Edge`
- `Event`
- `Episode`
- `Pattern`

#### `graph_store.py`

- ノード追加
- エッジ追加
- 隣接探索
- ノード検索
- シリアライズ

#### `event_parser.py`

- JSON から `Event` / `Episode` を生成
- バリデーション

#### `graph_builder.py`

- イベントから局所構造を生成
- ノードの再利用判定
- 初期エッジ生成

#### `learner.py`

- 反復イベントの集計
- `precedes` / `predicts` / `causes` 候補更新
- 信頼度更新

#### `abstractor.py`

- 類似パターンの発見
- 上位概念ノード生成
- `instance_of` / `abstracts_to` 更新

#### `predictor.py`

- 入力イベントから局所探索
- 候補予測をスコアリング
- 次イベントを返す

#### `explainer.py`

- 予測に使った経路を復元
- 根拠イベントと抽象ノードを返す

#### `persistence.py`

- JSON 保存
- JSON 読み込み

#### `cli/main.py`

- `train`
- `predict`
- `inspect`

---

## 9. 学習フロー

MVP-1 の学習はイベントごとの局所更新で行います。

### 9.1 全体フロー

```text
イベント入力
  ->
正規化
  ->
イベントノード群の取得または生成
  ->
イベント内部の関係生成
  ->
直前イベントとの遷移関係更新
  ->
パターン集計更新
  ->
抽象化候補の判定
  ->
必要なら抽象ノード生成
  ->
保存
```

### 9.2 イベント内部の基本構造

イベント `dog run -> fatigue_up` に対して最低でも次を作ります。

```text
dog --participates_in--> run
run --affects--> fatigue_up
dog --context--> animal
run --context--> movement
```

MVP-1 では `context` をエッジ属性に持たせてもよく、独立ノードにはしなくてよいです。

### 9.3 連続イベントからの遷移学習

同一 actor に対し、時間的に隣接するイベントの action/effect を結びます。

例:

```text
dog run -> fatigue_up
dog rest -> fatigue_down
```

この場合、以下の候補が増えます。

```text
run --precedes--> rest
run --predicts--> fatigue_up
rest --predicts--> fatigue_down
```

### 9.4 信頼度更新

MVP-1 では複雑な最適化ではなく、単純な集計ベースとします。

例:

```text
reliability = evidence_count / opportunity_count
```

`opportunity_count` は「その action が観測された回数」とします。

この `reliability` 更新は、将来の RISA における **構造補間** の最小形と見なせます。  
つまり MVP-1 ではまだ重いサブグラフ統合や構造平滑化は行わないが、

- 関係ごとに確からしさを持つ
- 新しい経験でその確からしさを滑らかに更新する

という仕組みだけ先に入れておく。より広い設計意図は [RISA 構造補間と構造平滑化のメモ](RISA-Structural-Interpolation-and-Smoothing.md) に整理します。

### 9.5 可塑性更新

MVP-1 では以下の単純ルールで十分です。

- evidence が増えるほど plasticity は下がる
- 最近更新された関係は少し plasticity を保つ
- 矛盾管理は MVP-2 で本格導入する

---

## 10. 抽象化設計

抽象化は RISA の差別化要素なので、MVP-1 でも最低限入れます。ただし複雑な概念発見ではなく、**共有効果による上位概念化**に限定します。

### 10.1 抽象化の最小条件

次の条件を満たしたとき、抽象概念候補を作ります。

- 異なる actor が 2 種類以上ある
- 同じ action を行っている
- 同じ observed_effects を持つ
- context_tags に共通要素がある

加えて、中長期的には「圧縮できる」だけでなく「その概念を導入すると予測が改善する」ことも概念採用条件に含めるべきです。MVP-1 ではまず support と共有効果を使った簡易版を採用し、将来拡張の詳細は [RISA 概念形成とマルチモーダル学習メモ](RISA-Concept-Formation-and-Multimodal-Notes.md) に委ねます。

例:

```text
dog run -> fatigue_up
human run -> fatigue_up
horse run -> fatigue_up
```

このとき、`animal_runner` のような中間概念を生成できます。

### 10.2 抽象ノードの形

```python
Node(
    id="concept:animal_movement_fatigue",
    kind="concept",
    label="animal_movement_fatigue",
    attributes={
        "shared_action": "run",
        "shared_effect": "fatigue_up"
    },
    abstraction_level=1,
    ...
)
```

### 10.3 抽象化で張る関係

```text
dog   --instance_of--> concept:animal_movement_fatigue
human --instance_of--> concept:animal_movement_fatigue
horse --instance_of--> concept:animal_movement_fatigue
concept:animal_movement_fatigue --predicts--> fatigue_up
concept:animal_movement_fatigue --participates_in--> run
```

### 10.4 命名方針

MVP-1 では人間らしいラベル生成は不要です。内部ラベルは機械生成でよいです。

例:

- `concept:shared_run_fatigue_up:001`
- `pattern:run_to_fatigue_up`

---

## 11. 予測設計

MVP-1 の予測は「次に起こりやすい effect または event を返す」ことに絞ります。

### 11.1 入力

予測入力は少なくとも以下を受け取ります。

```python
PredictionQuery(
    actor: str,
    action: str,
    target: str | None = None,
    context_tags: list[str] = [],
)
```

### 11.2 探索優先順位

1. actor に直接結び付く過去パターン
2. 同じ action のパターン
3. actor が属する抽象概念のパターン
4. 同じ context を持つ近傍パターン

MVP-1 の実装では、ここを「簡易局所活性化」として扱います。つまり全パターンを走査するのではなく、`actor`, `action`, `context` から引ける候補集合を先に集め、その局所集合だけを比較します。

### 11.3 スコアリング

MVP-1 の簡易スコアは以下で十分です。

```text
PredictionScore =
  0.45 * direct_match_score
  + 0.30 * action_pattern_score
  + 0.20 * concept_support_score
  + 0.05 * recency_score
```

#### direct_match_score

- 同一 actor + action の履歴一致度

#### action_pattern_score

- action に対する effect の一般頻度

#### concept_support_score

- actor が属する抽象概念に支えられている度合い

#### recency_score

- 最近観測されたパターンを少し優先する補助値

### 11.4 出力

```python
PredictionResult(
    predicted_effects: list[str],
    score: float,
    supporting_paths: list[list[str]],
    evidence_event_ids: list[str],
)
```

### 11.5 期待される動作

学習済み:

```text
dog run -> fatigue_up
human run -> fatigue_up
horse run -> fatigue_up
```

問い合わせ:

```text
wolf run -> ?
```

期待:

```text
fatigue_up
```

理由:

- `run` の一般パターン
- `animal` 文脈の共有
- 抽象概念への近接

---

## 12. 説明設計

RISA の重要価値である説明可能性は MVP-1 から実装します。

### 12.1 出力形式

予測時に、少なくとも以下を返します。

- 予測結果
- 使用した主要ノード
- 使用した主要エッジ
- 根拠イベント
- 抽象ノードの有無

### 12.2 説明例

```text
Prediction: fatigue_up

Reasoning path:
wolf
  -> run
  -> concept:shared_run_fatigue_up:001
  -> fatigue_up

Evidence:
- dog run -> fatigue_up
- human run -> fatigue_up
- horse run -> fatigue_up
```

### 12.3 実装方針

- `predictor` がスコアリング時の候補経路を保持する
- 最終選択時にトップ経路のみ `explainer` へ渡す
- 初期段階では全文生成せず、構造説明を返す

---

## 13. 永続化設計

MVP-1 では可搬性を優先し、JSON ベースで保存します。

### 13.1 保存対象

- ノード一覧
- エッジ一覧
- パターン一覧
- メタ情報

### 13.2 推奨ファイル

```text
state/
  graph_nodes.json
  graph_edges.json
  patterns.json
  metadata.json
```

### 13.3 メタ情報例

```json
{
  "version": "0.1.0",
  "event_count": 128,
  "node_count": 53,
  "edge_count": 121,
  "concept_count": 4,
  "last_updated": 1720425600
}
```

---

## 14. CLI 設計

最初の利用形態は CLI が最も効率的です。

### 14.1 コマンド

```bash
python -m risa.cli.main train data/toy_world.json
python -m risa.cli.main predict --actor wolf --action run --context animal
python -m risa.cli.main inspect --node concept:shared_run_fatigue_up:001
```

### 14.2 `train`

- 入力ファイルを読む
- イベント列を学習する
- 結果を保存する
- 学習統計を表示する

### 14.3 `predict`

- 現在の状態を読む
- クエリを評価する
- 予測と理由を表示する

### 14.4 `inspect`

- ノードやエッジ、概念の内部構造を表示する

---

## 15. テスト設計

MVP-1 は理論よりも振る舞い検証が重要です。最低限、以下の自動テストが必要です。

### 15.1 単体テスト

- イベントが正しく読み込まれる
- ノード重複が発生しない
- エッジの evidence_count が正しく増える
- 予測スコアが決定的に計算される
- 抽象ノードが条件成立時のみ作られる

### 15.2 結合テスト

入力:

```text
dog run -> fatigue_up
human run -> fatigue_up
horse run -> fatigue_up
```

期待:

- `run` に対する `fatigue_up` 予測が得られる
- 抽象概念が 1 つ以上作られる
- `wolf run` で `fatigue_up` を返す

### 15.3 回帰テスト

- 同じデータで再学習しても結果が不安定に変わらない
- 保存後に再読込しても予測が一致する

---

## 16. 実装優先順位

### Phase 1: 動く最小骨格

- `Event`, `Node`, `Edge`, `GraphStore`
- JSON 入力
- ノードとエッジ生成
- 保存

### Phase 2: 学習

- 連続イベント遷移の蓄積
- `predicts` 更新
- 信頼度更新

### Phase 3: 予測

- クエリ入力
- 局所探索
- スコアリング
- 結果表示

### Phase 4: 抽象化

- 共有 action/effect の検出
- 概念ノード生成
- `instance_of` 接続

### Phase 5: 説明

- 根拠イベント提示
- 経路表示

---

## 17. 想定リスク

### 17.1 ノード爆発

原因:

- actor/action/effect をそのまま増やし続ける

対策:

- MVP-1 ではラベル正規化を必須にする
- 同義語統合は手動辞書で対応する
- context をノード化しすぎない

### 17.2 抽象化の暴走

原因:

- 表面的な一致だけで概念を作る

対策:

- 2 件ではなく 3 件以上の support を要求する設定を用意する
- 共有 effect と共有 context の両方を条件にする

### 17.3 予測の過学習

原因:

- 直近のイベントだけを強く見すぎる

対策:

- actor 直結パターンと action 一般パターンの両方を使う
- recency の比重を小さく保つ

### 17.4 実用性の不足

原因:

- 理論的には面白いが動作が弱い

対策:

- 「何件学習すると何を予測できるか」をベンチマーク化する
- まずは toy world で確実に勝ち筋を作る

---

## 18. 実用化に向けた判断基準

MVP-1 は最終形ではありませんが、実用的に動作することを当面の最終目標とするなら、次の判断基準を持つべきです。

### 18.1 続行ライン

- 予測がルールベースを超えて一般化する
- 抽象ノードが再利用される
- 説明が人間に理解可能
- 新規データ追加で性能が改善する

### 18.2 見直しライン

- 予測が単純集計以上に伸びない
- 抽象化がノイズしか生まない
- ノード管理コストが急増する
- 実装の大半が例外処理に費やされる

---

## 19. MVP-1 完了定義

以下を満たした時点で MVP-1 完了とします。

- CLI で学習、予測、状態確認ができる
- toy world データセットが同梱されている
- `wolf run -> fatigue_up` のような近縁一般化が成功する
- 抽象ノードが自動生成される
- 予測理由をイベント経路として表示できる
- 保存と再読込後も同じ予測を返せる
- 単体テストと結合テストがある

---

## 20. 次段階への接続

MVP-1 の次は MVP-2 として、以下を追加するのが自然です。

- 例外処理のための文脈分裂
- 矛盾管理
- より明確な因果方向推定
- 睡眠処理による圧縮
- Structural Smoothing
- サブグラフ差分統合
- 自然言語から構造化イベントへの変換

さらにその先では、映像・音・行動を統一的な状態遷移表現へ落とすマルチモーダル化が重要になります。この方針と論点は [RISA 概念形成とマルチモーダル学習メモ](RISA-Concept-Formation-and-Multimodal-Notes.md) に記録します。

MVP-1 の価値は、RISA の全構想を一気に作ることではありません。**動的グラフだけで予測と抽象化が実用的に回り始めるかを、最小の機械で確かめること**にあります。
