# RISA Roadmap / RISA ロードマップ / RISA 路线图

Updated: 2026-09-10. [Design assessment / 設計評価 / 设计评估](RISA-Structural-AI-Assessment-2026-09-05.md)

## Authority and objective / 位置付けと目的 / 定位与目标

日本語: この文書を現行の実行順序とする。旧Phase別の大量のNext項目を、証拠に基づく段階移行へ置き換える。
既存研究ノートは仮説の保管場所であり、実装指示や完了証明ではない。旧機能の詳細はREADME、技術設計とGit履歴に残る。
目標は「経験から適用条件を学び、未知の対象・組合せへ構造を再利用し、変化へ適応できる世界モデル」。

English: This is the authoritative execution order, replacing the previous broad feature queue with evidence gates.
Research notes retain hypotheses, not implementation mandates or proof of completion. Historical details remain in
README, technical design, and Git history. Build a world model that learns applicability, transfers structure to
unseen objects and compositions, and adapts to change.

简体中文: 本文是当前唯一执行顺序，以证据门槛取代宽泛的功能队列。研究笔记用于保留假设，不代表实现指令或完成证明。
历史细节保留在README、技术设计及Git历史中。目标是能学习适用条件、向未见对象和组合迁移结构、并适应变化的世界模型。

- [Done] implemented in the current codebase / 現行コードに実装済み / 当前代码已实现
- [Next] high-priority unfinished work / 最優先の未完了作業 / 高优先级未完成工作
- [Later] planned, but not the closest next step / 依存段階通過後の予定 / 前置阶段通过后的计划

日本語: [Done]は実装の存在を示し、研究仮説の実証とは区別する。G0、G1、G2.1〜G2.3とG2.4の関係前提再設計まで完了し、直近はG2.4の総効率評価。
G3以降は重要でも[Later]とする。指標・閾値は評価前に固定し、結果を見て合格条件を緩めない。

English: [Done] means implemented, not scientifically validated. G0, G1, G2.1–G2.3 and the G2.4 relation-premise redesign are complete; total-efficiency evaluation in G2.4 is next and G3 onward is [Later].
Freeze metrics and thresholds before evaluation; do not relax gates after seeing results.

简体中文: [Done]表示已实现，不等于科学验证。G0、G1、G2.1至G2.3及G2.4的relation前提重设已完成，下一步是G2.4总效率评估；G3以后标为[Later]。
评估前固定指标与阈值，不根据结果放宽通过条件。

## Current baseline / 現在地 / 当前基础

| Status | 日本語 | English | 简体中文 |
| --- | --- | --- | --- |
| [Done] | 構造化Event、頻度学習、グラフ、簡易概念、Primitive、JSON保存 | Structured events, counts, graph, simple concepts, primitives, JSON persistence | 结构化事件、频度学习、图、简单概念、原语及JSON保存 |
| [Done] | 学習前予測、誤差履歴、共活性、代謝、Replay、文脈分裂の最小経路 | Minimal pre-update prediction, error history, coactivation, metabolism, replay, context splitting | 最小学前预测、误差历史、共激活、代谢、重放与上下文分裂 |
| [Done] | 状態消費・排他更新・数値資源・単位と上下限の部品 | Consumption, exclusive replacement, numeric resources, units and bounds | 状态消耗、互斥替换、数值资源、单位与边界 |
| [Done] | 分岐simulation、goal/constraint評価、what-if、AND/OR、偏序実行、threat検出 | Branch simulation, goal/constraint evaluation, what-if, AND/OR, partial-order execution, threats | 分支模拟、目标与约束评估、假设比较、AND/OR、偏序执行及冲突检测 |
| [Done] | G0反例、G1/G2評価基盤、G2学習機構を回帰テスト化し、全91テストが通過 | G0 counterexamples, G1/G2 evaluation and G2 learning mechanisms covered; all 91 tests pass | G0反例、G1/G2评估及G2学习机制已纳入回归测试，全部91项测试通过 |

日本語: G0で意味論を修正し、G1で比較測定した。G2では型付き役割束縛、前提学習、変化適応を実装し、対象課題で改善した。
明示済み前提のcompositionは具体遷移表と同率で、保存量と時間には大差が残るため、候補概念の実利用と効率をG2.4で改善する。

English: G0 repairs semantic contracts and G1 measures them comparatively. G2 adds typed role binding, learned
applicability and change adaptation with gains on their targeted tasks. Supplied-precondition composition still ties
the grounded table, while storage and latency gaps remain; G2.4 now targets useful candidate concepts and efficiency.

简体中文: G0已修复语义契约，G1已完成比较测量。G2实现了类型化角色绑定、适用条件学习及变化适应，并在对应任务取得提升。
已提供前提的composition仍与具体转移表持平，存储量及时延差距仍大；G2.4将改进候选概念的实际使用及效率。

## G0 — Semantic and evidence integrity / 意味論と証拠の修正 / 语义与证据修正

| Status | 日本語 | English | 简体中文 |
| --- | --- | --- | --- |
| [Done] | G0.1 同時effectを原子的な集合として保持し、別outcomeと分離。deltaは一回適用し旧単一outputを移行 | Store joint effects as atomic sets, separate alternatives, apply deltas once, and migrate legacy single outputs | 将同时效果保存为原子集合并与备选结果分离；变化量只应用一次，并迁移旧单一输出 |
| [Done] | G0.2 純粋transition関数を共有し、Replayの状態・資源・根拠をbranch別保持 | Share a pure transition kernel and preserve replay state, resources, and evidence per branch | 共享纯转移函数，重放逐分支保存状态、资源与证据 |
| [Done] | G0.3 Event IDを冪等化し、衝突を拒否。episode境界と遅着・順序契約を実装 | Make Event IDs idempotent, reject conflicts, and enforce episode and late-arrival ordering | 实现事件ID幂等、冲突拒绝、回合边界及迟到事件顺序契约 |
| [Done] | G0.4 根拠なしactionを棄却し、導出/仮説/棄却を区分。actor/targetを具体照合 | Abstain on unsupported actions, distinguish derived/hypothetical/abstained claims, and ground actor/target | 对无依据动作弃答，区分推导/假设/弃答，并具体匹配actor与target |
| [Done] | G0.5 schema v2、原子的保存、旧state移行、backup復旧を実装 | Implement schema v2, atomic saves, legacy migration, and backup recovery | 实现schema v2、原子保存、旧状态迁移及备份恢复 |

日本語: G0.1→G0.5を実装し、反例を含む全69テストで同時effectと一回のcost、排他outcomeの非混合、
重複入力no-op、target区別、根拠参照、保存復元の一致を確認した。完全観測は集合一致で判定する。
部分観測maskはG1の評価データ契約として実装する。旧単一outputは安全に移行し、復元不能な同時性は推測しない。

English: G0.1–G0.5 are implemented. All 69 tests verify joint effects and cost-once behavior, isolated outcomes,
duplicate no-op, target distinction, traceable evidence, and persistence round trips. Complete observations use set
equality. Partial-observation masks belong to the G1 evaluation-data contract. Legacy single outputs migrate safely;
ambiguous joint effects are never guessed.

简体中文: G0.1至G0.5已实现。全部69项测试验证同时效果与单次成本、结果隔离、重复输入无变化、target区分、
可追溯证据及保存恢复一致性。完整观测使用集合一致；部分观测mask将在G1评估数据契约中实现。
旧单一输出可安全迁移，无法恢复的同时性不会被猜测。

## G1 — Comparative evaluation / 比較評価基盤 / 比较评估基础

| Status | 日本語 | English | 简体中文 |
| --- | --- | --- | --- |
| [Done] | G1.1 独立した人工環境、generator、split manifest、5 seed、各split 200 episodeを固定 | Fixed independent environment, generator, split manifest, five seeds and 200 episodes per split | 已固定独立环境、生成器、划分manifest、5个seed及每个split 200回合 |
| [Done] | G1.2 頻度、完全事例検索、具体遷移表、oracleを同一plannerで比較 | Compared frequency, exact retrieval, grounded transition and oracle with the same planner | 已用同一planner比较频度、完整案例检索、具体转移表及oracle |
| [Done] | G1.3 構造共有、共活性、Replay、代謝、分裂を個別無効化して測定 | Measured individual ablations of sharing, coactivation, replay, metabolism and splitting | 已分别测量结构共享、共激活、Replay、代谢及分裂消融 |
| [Done] | G1.4 学習前精度、goal到達、棄却、忘却、時間、保存量、失敗例を記録 | Recorded pre-update accuracy, goal success, abstention, forgetting, time, storage and failures | 已记录学前准确率、目标达成、弃答、遗忘、时间、存储量及失败例 |

### Evaluation contract / 評価契約 / 评估契约

| Split / 分割 / 划分 | 日本語 | English | 简体中文 |
| --- | --- | --- | --- |
| Control | 既知action・未知actor。頻度で解ける対照群 | Known action/unseen actor; solvable by frequency | 已知动作/未见actor，频度可解的对照 |
| Composition | 個別遷移は既知、組合せと順序は未見。観測隣接edgeを答えとして供給しない | Known transitions, unseen combinations/order; no answer-revealing precedence | 已知单步转移、未见组合与顺序，不提供泄露答案的前后关系 |
| Binding | 新しい対象束縛、対象数、actor/target交換、無関係物体 | New bindings/object counts, actor-target swaps, distractors | 新绑定与对象数量、角色交换、干扰对象 |
| Drift | A→B→A、例外文脈、遅延観測。回復速度と旧問題保持 | A→B→A, exceptions, delayed observations; recovery and retention | A→B→A、例外与延迟观测，测恢复与保持 |
| Uncertainty | 未知action、欠落観測、確率outcome、禁止状態 | Unknown actions, missing observations, stochastic outcomes, forbidden states | 未知动作、缺失观测、随机结果与禁止状态 |

日本語: まず決定的な小世界で各方式が同じ情報を受けることを検証する。5固定seed、各課題200以上のheld-out episodeを
初期予算とし、95%区間はepisode単位で報告する。これは研究運用上の初期設定であり、検出力の保証ではない。
開発用と最終評価用を分け、IDを変えた重複trajectory、同型問題の漏洩を検査する。評価Eventを学習・Replayに入れない。
オンラインdrift評価だけは予測→採点→観測学習の順で行い、全方式で同じ更新機会とReplay予算を与える。
plannerと環境oracleは別実装とし、生成計画を環境で実行して達成判定する。前提・deltaを入力で与える条件と、
before/after観測から学ぶ条件の結果を別表にする。oracle遷移＋同一plannerも上限対照として学習誤差と探索誤差を分解する。
棄却を除外して精度を水増しせず、coverageと全queryの成功率を併記する。確率校正前はscoreを確率と呼ばない。

English: Start with deterministic worlds and equal information. Use five fixed seeds and at least 200 held-out
episodes per task initially, reporting episode-level 95% intervals; this is a starting budget, not a power guarantee.
Separate development/final splits and check duplicate/isomorphic leakage. Held-out events never enter training/replay.
For online drift only, predict, score, then learn, with equal update opportunities and replay budgets.
Use an independent environment oracle to execute plans. Report supplied preconditions/deltas separately from learned
before/after models. An oracle model with the same planner separates model errors from search errors.
Report coverage and all-query success; do not call uncalibrated scores probabilities.

简体中文: 先用确定性小环境保证输入信息公平。初始采用5个固定种子、每项任务至少200个留出回合，报告回合级95%区间；
这只是初始预算，不保证统计检验功效。分开开发集与最终评估集，检查重复和同构泄漏；留出事件不进入训练或重放。
仅在线漂移评估按预测、评分、学习顺序进行，并给各方法相同更新机会与重放预算。
由独立环境执行计划；人工提供前提/delta与从前后观测学习的结果分开报告。真实模型加同一规划器用于分离学习和搜索误差。
同时报告覆盖率与全部查询成功率；未经校准的分数不称为概率。

日本語: G1は[比較評価結果](G1-Comparative-Evaluation-2026-09-08.md)として完了した。RISAはcompositionで100%、
bindingで75%だが具体遷移表と同率であり、優位性は確認できなかった。B期driftは例外context分の33.3%に留まり、未知targetは棄却した。
この失敗をG2の役割束縛、変化点適応、証拠圧縮の設計入力とする。

English: G1 is complete in the [comparative report](G1-Comparative-Evaluation-2026-09-08.md). RISA reaches 100% on
composition and 75% on binding, tying the grounded transition baseline. It reaches only the explicit-context third of
phase B drift and abstains on unseen targets. G2 uses these failures to redesign bindings, change adaptation, and evidence efficiency.

简体中文: G1已完成，详见[比较评估报告](G1-Comparative-Evaluation-2026-09-08.md)。RISA在composition为100%、
binding为75%，与具体转移表持平；B阶段drift仅解决带显式context的33.3%，并对未见target弃答。
G2将据此重设角色绑定、变化适应及证据效率。

## G2 — Learned structural reuse / 学習された構造再利用 / 学习型结构复用

- [Done] G2.1 型付きtarget役割をEvent、graph、予測根拠へ通し、未知targetを同じ役割の観測から接地 / Ground unseen targets through typed target roles carried by events, graph and evidence / 通过事件、图及证据中的类型化target角色接地未见对象
- [Done] G2.2 同一contextの直近3件から変化仮説を作り、A→B→Aの可逆適応を比較 / Form change hypotheses from three recent same-context observations and evaluate reversible A→B→A adaptation / 根据同一context最近3项观测形成变化假设并评估A→B→A可逆适应
- [Done] G2.3 完全な前後観測と失敗例から保守的に前提を学び、反例で撤回 / Conservatively learn applicability from complete before observations and failures, retracting on counterexamples / 从完整前态观测与失败中保守学习适用条件，并在反例出现时撤回
- [Done] G2.4a action/context/effect/actor/target/roleのevidence index、compact graph保存、直近件数制限Replayを実装 / Implement evidence indices, compact graph persistence and recent-event-bounded replay / 实现证据索引、紧凑图持久化及按最近事件数限制的重放
- [Done] G2.4b 複数target・source・episodeの共有から`UnnamedConceptCandidate`を生成し、反例と記述長を記録 / Generate unnamed candidates from diverse target/source/episode support and record counterexamples and description length / 从多target、source及episode的共享结构生成无名候选，并记录反例与描述长度
- [Done] G2.4c development/final非重複証拠で`proposed -> provisional -> adopted/rejected`を判定し、証拠変化時に評価を無効化 / Evaluate proposed, provisional, adopted or rejected states on disjoint development/final evidence and invalidate changed evidence / 用互不重叠的development/final证据评估候选，并在证据变化时使评估失效
- [Done] 採用候補を派生indexから予測と一時Primitiveへ接続し、元Event・保存graphを変更しない / Connect adopted candidates from a derived index to prediction and ephemeral primitives without changing events or the stored graph / 从派生索引将已采纳候选接入预测及临时原语，不修改Event或持久化图
- [Done] Eventから再構築可能な頻度表・activation indexを保存対象から外し、legacy stateのみfallback読込 / Omit rebuildable count and activation indices from persistence with a legacy fallback / 不再持久化可从Event重建的频度表及activation索引，并保留旧状态回退
- [Done] candidate-transferを5 seed・final 200件で比較し、候補あり/なし100%・差0の単一遷移候補を全て棄却 / Compare candidate transfer over five seeds and 200 final cases; reject all redundant single-transition candidates at 100% versus 100% / 用5个seed及200个final案例比较候选迁移；候选有无均为100%，拒绝全部冗余单一转移候选
- [Done] 2段階時間列候補をEventから発見し、同一target役割変数、状態前提・消費、数値前提・変数差分を保持して一時macroとして合成 / Discover two-step temporal candidates from events, preserve a same-target role variable plus state and numeric applicability and transitions, and compose them as ephemeral macros / 从Event发现两步时间序列候选，保存同一target角色变量、状态与数值适用条件及转移，并作为临时宏组合
- [Done] role不一致時の無型fallbackを止め、時間列候補を5 seed・development 800・final 200件で比較し、100%対75%・差+25ポイント・false generalization 0%対33.3%で採用 / Stop untyped fallback on role mismatch; compare over five seeds, 800 development and 200 final cases, and adopt at 100% versus 75%, +25 points and 0% versus 33.3% false generalization / 禁止角色不匹配时回退到无类型路径；以5个seed、800个development及200个final案例比较，候选100%对75%、提升25个百分点、错误泛化0%对33.3%，因此采纳
- [Done] actor/target二つの型付きrole変数を時間schema・派生index・Composition query・CLIへ通し、role不一致と欠落時にabstain / Carry typed actor and target variables through temporal schemas, derived indices, composition queries and CLI, abstaining on mismatched or missing roles / 将actor与target两个类型化角色变量贯穿时间schema、派生索引、Composition query及CLI，并在角色不匹配或缺失时弃答
- [Done] 関係候補を5 seed・development 800・final 200件で比較し、100%対40%・差+60ポイント・false generalization 0%対75%で採用 / Compare relational candidates over five seeds, 800 development and 200 final cases; adopt at 100% versus 40%, +60 points and 0% versus 75% false generalization / 以5个seed、800个development及200个final案例比较关系候选；候选100%对40%、提升60个百分点、错误泛化0%对75%，因此采纳
- [Done] 具体actor/target identityをComposition query・CLIへ通し、支持Eventから一貫して帰納できる`equal`/`not_equal`制約を実行時検査 / Pass concrete actor and target identities into composition queries and CLI, enforcing consistently induced equality or inequality constraints at runtime / 将具体actor及target identity传入Composition query与CLI，并在运行时检查从支持Event一致归纳的同一或差异约束
- [Done] Eventへ任意`entity_bindings`・`entity_role_bindings`・`entity_relations`を追加し、候補発見・role/identity/relation照合・再読込へ通す / Add arbitrary entity, role and relation bindings to events and carry them through discovery, role/identity/relation matching and reload / 为Event添加任意entity、角色及relation绑定，并贯穿候选发现、role/identity/relation匹配及重载
- [Done] 任意3-entity関係候補を5 seed・development 800・final 200件で比較し、100%対20%・差+80ポイント・false generalization 0%対100%で採用 / Compare generic three-entity candidates over five seeds, 800 development and 200 final cases; adopt at 100% versus 20%, +80 points and 0% versus 100% false generalization / 以5个seed、800个development及200个final案例比较任意三entity候选；候选100%对20%、提升80个百分点、错误泛化0%对100%，因此采纳
- [Done] `entity_relations_observed`で完全観測を区別し、成功列のrelation共通部分だけを前提化して余分なnoiseによるschema分割を防止 / Distinguish complete observations with `entity_relations_observed` and infer only successful relation intersections to prevent noisy schema fragmentation / 用`entity_relations_observed`区分完整观测，仅将成功序列的relation交集作为前提，避免噪声导致schema分裂
- [Done] 前提relationを欠く失敗列を負例、全前提を満たす失敗列を反例として分離し、新しい成功例が前提を欠けば同一候補IDで前提を撤回して再評価待ちへ戻す / Separate failures missing required relations from true counterexamples, and retract a premise under the same candidate ID when a new success lacks it, resetting evaluation / 区分缺少必要relation的负例与满足全部前提的真正反例；新成功例缺少前提时在同一候选ID下撤回前提并重置评估
- [Done] candidate-backed role readout圧縮を回帰一致時だけ適用し、不一致rollback、保存再構築、新規学習時復元を実装 / Apply candidate-backed role compaction only after regression equivalence, with rollback, reload reconstruction and restoration before learning / 仅在回归一致时应用候选支持的角色readout压缩，并实现不一致回滚、重载重建及学习前恢复
- [Done] 5 seed診断で対象role readoutを平均81 bytesから2 bytesへ削減し、候補経由の成功率100%を維持 / Reduce the targeted role readout from 81 to 2 bytes on average over five seeds while preserving 100% candidate-backed success / 5个seed中目标角色readout平均由81 bytes降至2 bytes，并保持候选路径100%成功率
- [Done] final 200 queryでcandidate-backed compactionを診断し、readout 81→2 bytes・p95非悪化でも総保存Stateが26,399→26,487 bytesへ増えたため総memory方式として棄却 / Diagnose candidate-backed compaction on 200 final queries; despite an 81-to-2-byte readout and no observed p95 regression, reject it because total persisted state grows from 26,399 to 26,487 bytes / 在200个final query上诊断候选压缩；尽管readout由81降至2 bytes且p95未见恶化，但持久化State总量由26,399增至26,487 bytes，因此作为总内存方案予以否决
- [Next] `specialized/merged/dormant`、二世代候補、祖先を含む循環支持禁止を完成 / Complete specialization, merging, dormancy, second-generation candidates and ancestor-aware circular-support prevention / 完成分化、合并、休眠、第二代候选及祖先感知的循环自证防止
- [Next] Event・候補schema・支持IDに残る重複を圧縮し、同じ広い回帰queryで総保存量とp95を再測定 / Compress duplication in events, candidate schemas and support IDs, then remeasure total persistence and p95 on the same broad query corpus / 压缩Event、候选schema及支持ID中的重复，并在同一广泛回归query上重新测量持久化总量及p95

詳細設計: [未分知と概念凝縮 / Undivided Knowledge and Concept Condensation / 未分知识与概念凝聚](RISA-Undivided-Knowledge-and-Concept-Condensation.md)

候補の追加価値検証: [G2候補転移評価 / Candidate transfer evaluation / 候选迁移评估](G2-Candidate-Transfer-Evaluation-2026-09-08.md)

時間列候補の追加価値検証: [G2時間列候補評価 / Temporal candidate evaluation / 时间序列候选评估](G2-Temporal-Candidate-Evaluation-2026-09-09.md)

関係候補の追加価値検証: [G2関係候補評価 / Relational candidate evaluation / 关系候选评估](G2-Relational-Candidate-Evaluation-2026-09-09.md)

任意関係候補の追加価値検証: [G2任意関係評価 / Generic relation evaluation / 任意关系评估](G2-Generic-Relation-Evaluation-2026-09-09.md)

日本語: [G2比較結果](G2-Structural-Reuse-Evaluation-2026-09-08.md)では、final 200 episodeでRISAは観測から前提を学ぶ
composition 100%（具体遷移表0%）、binding 100%（同75%、役割束縛なし75%）、B期drift 75%（同33.3%、
変化適応なし33.3%）だった。Control、明示前提composition、A1/A2は100%を維持し、Uncertaintyは94%で同率だった。
役割型は入力で与えており自動型発見ではない。保存量は静的学習後138,918 bytes対3,458 bytesで、効率の課題は未解決である。

English: The [G2 comparison](G2-Structural-Reuse-Evaluation-2026-09-08.md) reports 100% versus 0% on learned-
applicability composition, 100% versus 75% on binding, and 75% versus 33.3% in phase B drift over the pooled final
episodes. Control, supplied-precondition composition and A1/A2 remain at 100%; uncertainty ties at 94%. Target roles
are supplied rather than induced. Static state remains large at 138,918 bytes versus 3,458 bytes.

简体中文: [G2比较结果](G2-Structural-Reuse-Evaluation-2026-09-08.md)显示：从观测学习适用条件的composition为100%对0%，
binding为100%对75%，B阶段drift为75%对33.3%。Control、已提供前提的composition及A1/A2保持100%，Uncertainty同为94%。
target角色由输入提供，尚未自动归纳。静态状态仍为138,918 bytes，而基线为3,458 bytes。

日本語: G0/G1後、構造共有なし・具体遷移表との比較を固定plannerで実施する。最終採用の初期閾値は、
compositionとbindingの両方で最強の適用可能baselineより成功率が5ポイント以上高く、差の95%区間下限が0超、
同じ上限予算を守り、既知課題の低下が2ポイント以内であること。閾値は実験前の設計値で、測定結果ではない。
満たさない場合はfailureを一つ選んで改訂し、2回の事前登録比較でも改善しなければ役割表現・共有単位を再検討する。
自動schema獲得が勝てなければ、明示schemaを使う説明可能な記憶・計画部品へ用途を絞る。

G2.1〜G2.3は対象別ablationで5ポイントを超える改善を示したが、当初の広いgateは未達である。
明示前提compositionは具体遷移表と同率で、役割型も外部入力だからである。G2.4では候補概念を実際の推論へ接続し、
型・schemaの自動獲得と効率を独立held-outで検証する。gateの定義は維持する。

概念凝縮の追加条件として、候補なし方式より実測記述長を減らし、false generalizationを増やさないことを要求する。
新概念を使う二世代目以降の候補探索は、祖先と重ならない独立held-out episodeで追加改善が確認できた場合だけ「知能複利」と報告する。

English: After G0/G1, hold the planner fixed. Initial adoption gate: at least +5 percentage points over the strongest
applicable baseline on both composition and binding, a positive lower 95% bound for the difference, equal budget caps,
and no more than 2 points of loss on familiar tasks. These are prospective thresholds, not results.
After two preregistered revisions without improvement, reconsider bindings/sharing; if schema induction adds no value,
narrow the product to explainable memory/planning with supplied schemas.

Concept condensation must also reduce measured description length over the no-candidate variant without increasing
false generalization. Report second-generation discovery as intelligence compounding only when it improves independent
held-out episodes whose evidence does not overlap the candidate lineage.

G2.1–G2.3 exceed five points in their targeted ablations, but the original broad gate is not yet met: supplied-
precondition composition still ties the grounded table, and target roles are external inputs. G2.4 must connect
candidates to inference and test automatic type/schema acquisition and efficiency on independent held-out evidence.
The gate remains unchanged.

简体中文: G0/G1后固定规划器。初始采纳条件：组合与绑定任务均超过最强适用基线至少5个百分点，
差值95%区间下限大于0，遵守相同预算上限，已知任务下降不超过2个百分点。以上是预设门槛，不是实测结果。
两轮预注册改订后仍无改善，则重新考虑绑定与共享表示；自动schema归纳无收益时，收敛为使用显式schema的可解释记忆与规划组件。

概念凝聚还必须比无候选版本降低实测描述长度，且不增加错误泛化。只有当第二代及后续发现能改善与候选谱系证据不重叠的
独立留出回合时，才可称为智能复利。

G2.1至G2.3在各自消融中提升超过5个百分点，但仍未达到原先的广义门槛：已提供前提的composition仍与具体转移表持平，
target角色也来自外部输入。G2.4必须把候选接入推理，并在独立留出证据上验证类型/schema自动获取及效率；门槛保持不变。

## G3 — Adaptation and bounded cost / 継続適応と計算予算 / 持续适应与计算预算

- [Later] 文脈分裂・統合・休眠の個別効果をdrift評価 / Measure splitting/merging/dormancy under drift / 在漂移中分别评估分裂、合并与休眠
- [Later] 実装済みindexと予算付きReplayを1k〜100k Eventで比較検証 / Validate the implemented indices and bounded replay at 1k–100k events / 在1千至10万Event规模验证已实现的索引及有界重放
- [Later] 1k→10k→100k Eventの段階測定 / Measure 1k→10k→100k events / 分级测量1k至100k事件
- [Later] score校正、unknownの区別、状態を含む探索重複判定 / Calibration, unknown states, state-aware search deduplication / 校准、未知状态及考虑状态的搜索去重

日本語: G2後に実行。更新範囲、Replay件数、走査edge、p50/p95時間、保存bytes、回復速度と忘却を計測する。
局所索引版は全走査版との候補・結果比較を行い、品質低下1ポイント以内でp95時間または走査量を2倍以上改善することを
初期採用条件とする。最大規模が予算を超えたらそこで止め、上限を結果として報告する。

English: After G2, measure update scope, replay count, scanned edges, p50/p95 latency, stored bytes, recovery and forgetting.
Compare indexed and full-scan candidates/results. Initial gate: at least 2× better p95 latency or scan count with at
most 1 point quality loss. Stop and report the limit if a scale exceeds budget.

简体中文: G2后测更新范围、重放量、扫描边、p50/p95时延、存储量、恢复与遗忘。比较索引版与全扫描版候选和结果。
初始门槛为质量下降不超过1个百分点，p95时延或扫描量改善至少2倍；超预算即停止并报告上限。

## G4 — Application and optional research / 用途と追加研究 / 应用与可选研究

- [Later] 狭い業務手順・資源管理の外部ログでshadow評価 / Shadow evaluation on bounded workflow/resource logs / 在有限流程与资源日志上影子评估
- [Later] Threat-Aware Ordering Repair。G1で探索失敗が主要因の場合に前倒し再判断 / Ordering repair, reconsider earlier only if G1 isolates search as the bottleneck / 若G1确认搜索为瓶颈再考虑提前顺序修复
- [Later] Canopy、階層credit、SNN、スペクトル診断 / Canopy, hierarchical credit, SNN, spectral probes / Canopy、层级信用、SNN与谱诊断
- [Later] Neural adapter、多言語知覚、multimodal、SARA接続 / Neural adapters, multilingual perception, multimodal and SARA integration / 神经适配器、多语言感知、多模态与SARA集成
- [Later] 微分可能論理ゲート: soft候補発見、hard gate離散化、時間・関係macroのBoolean/LUT compile / Differentiable logic gates for soft candidate discovery, hard-gate discretization and Boolean/LUT compilation of temporal and relational macros / 可微逻辑门：soft候选发现、hard gate离散化，以及时间与关系宏的Boolean/LUT编译
- [Later] RDDLGN型の時間候補generatorと、連続知覚adapter・離散構造実行のhybrid比較 / Compare an RDDLGN-style temporal candidate generator and a hybrid continuous-perception/discrete-structure executor / 比较RDDLGN式时间候选生成器及连续感知adapter与离散结构执行的hybrid
- [Later] BitNetを論理gateと同一視せず、`{-1,0,+1}`を促進・非接続・抑制relationへ写す三値符号付きEvent回路を比較 / Without equating BitNet with logic gates, compare a ternary signed-event circuit mapping `{-1,0,+1}` to excitatory, absent and inhibitory relations / 不将BitNet等同于逻辑门，比较把`{-1,0,+1}`映射为促进、无连接及抑制relation的三值有符号Event电路
- [Later] dense三値行列、sparse signed graph、変化部分だけを伝播するevent-driven graph、Boolean/LUT、現行graphを同条件比較 / Compare dense ternary matrices, sparse signed graphs, change-only event-driven graphs, Boolean/LUT and the current graph under matched conditions / 同条件比较dense三值矩阵、sparse signed graph、仅传播变化部分的event-driven graph、Boolean/LUT及当前graph
- [Later] `0`の非接続化では`absent/dormant/pruned`を区別し、可塑性、再配線cost、忘却を評価 / Distinguish absent, dormant and pruned zero-connections and evaluate plasticity, rewiring cost and forgetting / 将零连接区分为absent、dormant及pruned，并评估可塑性、重新连接成本及遗忘
- [Later] CPU bitset/LUTで完全な意味一致と2倍以上のp95または走査量改善を確認した場合だけFPGA評価 / Evaluate FPGA only after a CPU bitset/LUT prototype achieves exact semantics and at least 2× p95 or scanned-work improvement / 仅当CPU bitset/LUT原型实现完全语义一致且p95或扫描量至少改善2倍后评估FPGA

日本語: 外部入力境界は出典・confidence・episode・観測maskを持つEvent候補にする。英語・日本語・简体中文の
ラベルは表示と知覚adapterで扱い、内部IDと役割意味を翻訳依存にしない。新moduleはG1と同じ評価に接続し、
個別ablationの改善がある場合だけ採用する。現規模ではクラウド・VPS・DBの追加構築は必要ない。

English: External event candidates carry provenance, confidence, episode and observation masks. Support English,
Japanese and Simplified Chinese at display/perception boundaries; internal identities and roles must not depend on
translation. Adopt modules only after controlled gains. Current scale does not justify new cloud/VPS/DB infrastructure.

简体中文: 外部事件候选携带来源、置信度、回合与观测mask。显示与感知边界支持英语、日语与简体中文，内部ID与角色语义不依赖翻译。
新模块只有在受控比较取得收益后采纳。当前规模不需要新增云、VPS或数据库基础设施。

詳細: [RISA微分可能論理ゲート研究 / Differentiable logic-gate research / RISA可微逻辑门研究](RISA-Differentiable-Logic-Gate-Research-Notes.md)
