# RISA Roadmap / RISA ロードマップ / RISA 路线图

Updated: 2026-10-10. [Design assessment / 設計評価 / 设计评估](RISA-Structural-AI-Assessment-2026-09-05.md)

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

- 🟢 [Done] implemented in the current codebase / 現行コードに実装済み / 当前代码已实现
- 🟠 [Next] high-priority unfinished work / 最優先の未完了作業 / 高优先级未完成工作
- 🔴 [Later] planned, but not the closest next step / 依存段階通過後の予定 / 前置阶段通过后的计划
- ⭕️ [Pending] cannot be verified in the current development environment / 現在の開発環境で検証できないため保留 / 当前开发环境无法验证，因此暂缓

日本語: 🟢 [Done]は実装の存在を示し、研究仮説の実証とは区別する。G0、G1、G2.1〜G2.6とG3.1は完了。G3.2はdevelopmentで負の結果として終了し、G3.3は100kの全処理scale評価まで完了し、直近はG3.4の成長曲線と独立held-out評価。
G4以降は重要でも🔴 [Later]とする。指標・閾値は評価前に固定し、結果を見て合格条件を緩めない。

English: 🟢 [Done] means implemented, not scientifically validated. G0, G1, G2.1–G2.6 and G3.1 are complete; G3.2 development closed as a negative result. G3.3 end-to-end profiling completes through 100k; G3.4 growth curves and independent held-out evaluation are next. G4 onward is 🔴 [Later].
Freeze metrics and thresholds before evaluation; do not relax gates after seeing results.

简体中文: 🟢 [Done]表示已实现，不等于科学验证。G0、G1、G2.1至G2.6及G3.1已完成；G3.2开发评估以负面结果结束。G3.3已完成至10万的端到端测量；下一步是G3.4增长曲线及独立留出评估。G4以后标为🔴 [Later]。
评估前固定指标与阈值，不根据结果放宽通过条件。

## Current baseline / 現在地 / 当前基础

| Status | 日本語 | English | 简体中文 |
| --- | --- | --- | --- |
| 🟢 [Done] | 構造化Event、頻度学習、グラフ、簡易概念、Primitive、JSON保存 | Structured events, counts, graph, simple concepts, primitives, JSON persistence | 结构化事件、频度学习、图、简单概念、原语及JSON保存 |
| 🟢 [Done] | 学習前予測、誤差履歴、共活性、代謝、Replay、文脈分裂の最小経路 | Minimal pre-update prediction, error history, coactivation, metabolism, replay, context splitting | 最小学前预测、误差历史、共激活、代谢、重放与上下文分裂 |
| 🟢 [Done] | 状態消費・排他更新・数値資源・単位と上下限の部品 | Consumption, exclusive replacement, numeric resources, units and bounds | 状态消耗、互斥替换、数值资源、单位与边界 |
| 🟢 [Done] | 分岐simulation、goal/constraint評価、what-if、AND/OR、偏序実行、threat検出 | Branch simulation, goal/constraint evaluation, what-if, AND/OR, partial-order execution, threats | 分支模拟、目标与约束评估、假设比较、AND/OR、偏序执行及冲突检测 |
| 🟢 [Done] | G0反例、G1/G2評価基盤、G2学習機構を回帰テスト化し、全284テストが通過 | G0 counterexamples, G1/G2 evaluation and G2 learning mechanisms covered; all 284 tests pass | G0反例、G1/G2评估及G2学习机制已纳入回归测试，全部284项测试通过 |

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
| 🟢 [Done] | G0.1 同時effectを原子的な集合として保持し、別outcomeと分離。deltaは一回適用し旧単一outputを移行 | Store joint effects as atomic sets, separate alternatives, apply deltas once, and migrate legacy single outputs | 将同时效果保存为原子集合并与备选结果分离；变化量只应用一次，并迁移旧单一输出 |
| 🟢 [Done] | G0.2 純粋transition関数を共有し、Replayの状態・資源・根拠をbranch別保持 | Share a pure transition kernel and preserve replay state, resources, and evidence per branch | 共享纯转移函数，重放逐分支保存状态、资源与证据 |
| 🟢 [Done] | G0.3 Event IDを冪等化し、衝突を拒否。episode境界と遅着・順序契約を実装 | Make Event IDs idempotent, reject conflicts, and enforce episode and late-arrival ordering | 实现事件ID幂等、冲突拒绝、回合边界及迟到事件顺序契约 |
| 🟢 [Done] | G0.4 根拠なしactionを棄却し、導出/仮説/棄却を区分。actor/targetを具体照合 | Abstain on unsupported actions, distinguish derived/hypothetical/abstained claims, and ground actor/target | 对无依据动作弃答，区分推导/假设/弃答，并具体匹配actor与target |
| 🟢 [Done] | G0.5 schema v2、原子的保存、旧state移行、backup復旧を実装 | Implement schema v2, atomic saves, legacy migration, and backup recovery | 实现schema v2、原子保存、旧状态迁移及备份恢复 |

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
| 🟢 [Done] | G1.1 独立した人工環境、generator、split manifest、5 seed、各split 200 episodeを固定 | Fixed independent environment, generator, split manifest, five seeds and 200 episodes per split | 已固定独立环境、生成器、划分manifest、5个seed及每个split 200回合 |
| 🟢 [Done] | G1.2 頻度、完全事例検索、具体遷移表、oracleを同一plannerで比較 | Compared frequency, exact retrieval, grounded transition and oracle with the same planner | 已用同一planner比较频度、完整案例检索、具体转移表及oracle |
| 🟢 [Done] | G1.3 構造共有、共活性、Replay、代謝、分裂を個別無効化して測定 | Measured individual ablations of sharing, coactivation, replay, metabolism and splitting | 已分别测量结构共享、共激活、Replay、代谢及分裂消融 |
| 🟢 [Done] | G1.4 学習前精度、goal到達、棄却、忘却、時間、保存量、失敗例を記録 | Recorded pre-update accuracy, goal success, abstention, forgetting, time, storage and failures | 已记录学前准确率、目标达成、弃答、遗忘、时间、存储量及失败例 |

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

- 🟢 [Done] G2.1 型付きtarget役割をEvent、graph、予測根拠へ通し、未知targetを同じ役割の観測から接地 / Ground unseen targets through typed target roles carried by events, graph and evidence / 通过事件、图及证据中的类型化target角色接地未见对象
- 🟢 [Done] G2.2 同一contextの直近3件から変化仮説を作り、A→B→Aの可逆適応を比較 / Form change hypotheses from three recent same-context observations and evaluate reversible A→B→A adaptation / 根据同一context最近3项观测形成变化假设并评估A→B→A可逆适应
- 🟢 [Done] G2.3 完全な前後観測と失敗例から保守的に前提を学び、反例で撤回 / Conservatively learn applicability from complete before observations and failures, retracting on counterexamples / 从完整前态观测与失败中保守学习适用条件，并在反例出现时撤回
- 🟢 [Done] G2.4a action/context/effect/actor/target/roleのevidence index、compact graph保存、直近件数制限Replayを実装 / Implement evidence indices, compact graph persistence and recent-event-bounded replay / 实现证据索引、紧凑图持久化及按最近事件数限制的重放
- 🟢 [Done] G2.4b 複数target・source・episodeの共有から`UnnamedConceptCandidate`を生成し、反例と記述長を記録 / Generate unnamed candidates from diverse target/source/episode support and record counterexamples and description length / 从多target、source及episode的共享结构生成无名候选，并记录反例与描述长度
- 🟢 [Done] G2.4c development/final非重複証拠で`proposed -> provisional -> adopted/rejected`を判定し、証拠変化時に評価を無効化 / Evaluate proposed, provisional, adopted or rejected states on disjoint development/final evidence and invalidate changed evidence / 用互不重叠的development/final证据评估候选，并在证据变化时使评估失效
- 🟢 [Done] 採用候補を派生indexから予測と一時Primitiveへ接続し、元Event・保存graphを変更しない / Connect adopted candidates from a derived index to prediction and ephemeral primitives without changing events or the stored graph / 从派生索引将已采纳候选接入预测及临时原语，不修改Event或持久化图
- 🟢 [Done] Eventから再構築可能な頻度表・activation indexを保存対象から外し、legacy stateのみfallback読込 / Omit rebuildable count and activation indices from persistence with a legacy fallback / 不再持久化可从Event重建的频度表及activation索引，并保留旧状态回退
- 🟢 [Done] candidate-transferを5 seed・final 200件で比較し、候補あり/なし100%・差0の単一遷移候補を全て棄却 / Compare candidate transfer over five seeds and 200 final cases; reject all redundant single-transition candidates at 100% versus 100% / 用5个seed及200个final案例比较候选迁移；候选有无均为100%，拒绝全部冗余单一转移候选
- 🟢 [Done] 2段階時間列候補をEventから発見し、同一target役割変数、状態前提・消費、数値前提・変数差分を保持して一時macroとして合成 / Discover two-step temporal candidates from events, preserve a same-target role variable plus state and numeric applicability and transitions, and compose them as ephemeral macros / 从Event发现两步时间序列候选，保存同一target角色变量、状态与数值适用条件及转移，并作为临时宏组合
- 🟢 [Done] role不一致時の無型fallbackを止め、時間列候補を5 seed・development 800・final 200件で比較し、100%対75%・差+25ポイント・false generalization 0%対33.3%で採用 / Stop untyped fallback on role mismatch; compare over five seeds, 800 development and 200 final cases, and adopt at 100% versus 75%, +25 points and 0% versus 33.3% false generalization / 禁止角色不匹配时回退到无类型路径；以5个seed、800个development及200个final案例比较，候选100%对75%、提升25个百分点、错误泛化0%对33.3%，因此采纳
- 🟢 [Done] actor/target二つの型付きrole変数を時間schema・派生index・Composition query・CLIへ通し、role不一致と欠落時にabstain / Carry typed actor and target variables through temporal schemas, derived indices, composition queries and CLI, abstaining on mismatched or missing roles / 将actor与target两个类型化角色变量贯穿时间schema、派生索引、Composition query及CLI，并在角色不匹配或缺失时弃答
- 🟢 [Done] 関係候補を5 seed・development 800・final 200件で比較し、100%対40%・差+60ポイント・false generalization 0%対75%で採用 / Compare relational candidates over five seeds, 800 development and 200 final cases; adopt at 100% versus 40%, +60 points and 0% versus 75% false generalization / 以5个seed、800个development及200个final案例比较关系候选；候选100%对40%、提升60个百分点、错误泛化0%对75%，因此采纳
- 🟢 [Done] 具体actor/target identityをComposition query・CLIへ通し、支持Eventから一貫して帰納できる`equal`/`not_equal`制約を実行時検査 / Pass concrete actor and target identities into composition queries and CLI, enforcing consistently induced equality or inequality constraints at runtime / 将具体actor及target identity传入Composition query与CLI，并在运行时检查从支持Event一致归纳的同一或差异约束
- 🟢 [Done] Eventへ任意`entity_bindings`・`entity_role_bindings`・`entity_relations`を追加し、候補発見・role/identity/relation照合・再読込へ通す / Add arbitrary entity, role and relation bindings to events and carry them through discovery, role/identity/relation matching and reload / 为Event添加任意entity、角色及relation绑定，并贯穿候选发现、role/identity/relation匹配及重载
- 🟢 [Done] 任意3-entity関係候補を5 seed・development 800・final 200件で比較し、100%対20%・差+80ポイント・false generalization 0%対100%で採用 / Compare generic three-entity candidates over five seeds, 800 development and 200 final cases; adopt at 100% versus 20%, +80 points and 0% versus 100% false generalization / 以5个seed、800个development及200个final案例比较任意三entity候选；候选100%对20%、提升80个百分点、错误泛化0%对100%，因此采纳
- 🟢 [Done] `entity_relations_observed`で完全観測を区別し、成功列のrelation共通部分だけを前提化して余分なnoiseによるschema分割を防止 / Distinguish complete observations with `entity_relations_observed` and infer only successful relation intersections to prevent noisy schema fragmentation / 用`entity_relations_observed`区分完整观测，仅将成功序列的relation交集作为前提，避免噪声导致schema分裂
- 🟢 [Done] 前提relationを欠く失敗列を負例、全前提を満たす失敗列を反例として分離し、新しい成功例が前提を欠けば同一候補IDで前提を撤回して再評価待ちへ戻す / Separate failures missing required relations from true counterexamples, and retract a premise under the same candidate ID when a new success lacks it, resetting evaluation / 区分缺少必要relation的负例与满足全部前提的真正反例；新成功例缺少前提时在同一候选ID下撤回前提并重置评估
- 🟢 [Done] candidate-backed role readout圧縮を回帰一致時だけ適用し、不一致rollback、保存再構築、新規学習時復元を実装 / Apply candidate-backed role compaction only after regression equivalence, with rollback, reload reconstruction and restoration before learning / 仅在回归一致时应用候选支持的角色readout压缩，并实现不一致回滚、重载重建及学习前恢复
- 🟢 [Done] 5 seed診断で対象role readoutを平均81 bytesから2 bytesへ削減し、候補経由の成功率100%を維持 / Reduce the targeted role readout from 81 to 2 bytes on average over five seeds while preserving 100% candidate-backed success / 5个seed中目标角色readout平均由81 bytes降至2 bytes，并保持候选路径100%成功率
- 🟢 [Done] final 200 queryでcandidate-backed compactionを診断し、readout 81→2 bytes・p95非悪化でも総保存Stateが21,161→21,249 bytesへ増えたため総memory方式として棄却 / Diagnose candidate-backed compaction on 200 final queries; despite an 81-to-2-byte readout and no observed p95 regression, reject it because total persisted state grows from 21,161 to 21,249 bytes / 在200个final query上诊断候选压缩；尽管readout由81降至2 bytes且p95未见恶化，但持久化State总量由21,161增至21,249 bytes，因此作为总内存方案予以否决
- 🟢 [Done] schema v4で候補schema・型変数・支持/反例IDを保存対象から外し、Event再発見とfingerprint一致時の評価復元へ変更。旧候補payload相当26,399→25,756 bytes / In schema v4 omit candidate schemas, typed variables, support and counterexample IDs; rediscover them from events and restore evaluations on fingerprint match, reducing 26,399 to 25,756 bytes / schema v4不再保存候选schema、类型变量、支持及反例ID，从Event重新发现并在fingerprint一致时恢复评估，使26,399降至25,756 bytes
- 🟢 [Done] `specialized/merged`派生API、採用候補の`dormant`切替、二世代候補、親証拠fingerprint、DAG検証、祖先support/evaluationを含むheld-out重複禁止を実装 / Implement specialized and merged derivation APIs, dormant adopted candidates, second-generation candidates, parent-evidence fingerprints, DAG validation and held-out overlap rejection across ancestor support and evaluations / 实现specialized/merged派生API、已采纳候选休眠切换、第二代候选、父证据fingerprint、DAG验证及涵盖祖先支持与评估的留出重叠禁止
- 🟢 [Done] 派生候補だけを保存し、再読込時に親fingerprint一致順で復元。親証拠変化時は派生候補を破棄し、dormant候補を推論indexから除外 / Persist only derived candidates, restore them in parent-fingerprint order, discard them when parent evidence changes and exclude dormant candidates from inference indices / 仅持久化派生候选，按父fingerprint一致顺序恢复；父证据变化时丢弃派生候选，并从推理索引排除休眠候选
- 🟢 [Done] 再現性とprecision改善を満たすcontext specializationを自動提案し、互換な兄弟をcontext論理和付きでmerge。親との差を必須化し、採用時は同じ遷移の広い祖先をdormant化。5 seed・final 200件でmerge 100%対最良の直接親75%、広い祖先は50%・false generalization 100% / Automatically propose reproducible context specializations with precision gain, merge compatible siblings with context disjunctions, require gains over parents and make replaced broad ancestors dormant; over five seeds and 200 final cases merge reaches 100% versus the strongest direct parent's 75%, while the broad ancestor reaches 50% with 100% false generalization / 自动提出具备可复现性及precision提升的context分化，以context析取合并兼容兄弟，要求优于父候选并使被替代的宽泛祖先休眠；5个seed及200个final案例中merge达到100%，最强直接父候选为75%，宽泛祖先为50%且错误泛化100%
- 🟢 [Done] 親ごとの自動specializationをprecision改善・support順の上位8件に制限し、候補爆発を局所的に抑制 / Limit automatic specializations per parent to the top eight by precision gain and support, locally bounding candidate growth / 按precision提升及support将每个父候选的自动分化限制为前8项，局部抑制候选爆炸
- 🟢 [Done] 最大24 tagから単一・2連言の36条件を有限探索し、親ごと上位8候補、development winner 1候補だけをfinalへ進める選択契約を実装。学習時に完全相関する6 proxyを含む7候補から5 seedすべてで安定条件を選び、final 200件で100%対親50%、95% CI下限+43ポイント、false generalization 0%対100% / Search a bounded set of singleton and pairwise conjunctions from at most 24 tags, retain eight candidates per parent and allow one development winner into final; from seven candidates including six perfectly correlated training proxies, all five seeds select the stable condition and reach 100% versus the parent's 50%, a +43-point lower 95% bound and 0% versus 100% false generalization over 200 final cases / 从最多24个tag有限搜索单项及二元合取，每个父候选保留8项且仅允许1个development优胜者进入final；在含6个训练时完全相关proxy的7个候选中，5个seed均选中稳定条件，200个final案例达到100%对父候选50%，95%区间下限+43个百分点，错误泛化0%对100%
- 🟢 [Done] G2.4のcontext schemaについて、発見・候補予算・相関解消・独立採否・推論置換・保存再構築を完了 / Complete discovery, candidate budgeting, correlation resolution, independent adoption, inference replacement and persistence reconstruction for G2.4 context schemas / 完成G2.4 context schema的发现、候选预算、相关性消解、独立采纳、推理替换及持久化重建
- 🟢 [Done] 外部roleがないEvent/queryからtargetの一hoprelation位置署名を作り、安定した内部role IDへ変換。学習・候補発見・予測・composition・Replay・validation・CLI・保存再構築を同じresolverへ接続 / Build a one-hop relation-position signature for targets without supplied roles, convert it to a stable internal ID, and use one resolver across learning, discovery, prediction, composition, replay, validation, CLI and persistence reconstruction / 从未提供role的Event及query生成target一hop relation位置签名并转换为稳定内部ID，在学习、发现、预测、composition、重放、验证、CLI及持久化重建中使用同一resolver
- 🟢 [Done] 5 seed・各800 development・200 finalで構造roleと外部roleは予測・compositionとも100%、roleなし50%、差のfinal 95% CI下限+43ポイント、未知・逆向きrelationの誤型付け0%。構造role Stateは外部role版より25.38%小さい / Across five seeds with 800 development and 200 final cases each, induced and supplied roles reach 100% prediction and composition versus 50% without roles; the final 95% lower bound is +43 points, mistyping is 0%, and induced-role State is 25.38% smaller / 5个seed中每个使用800个development及200个final案例；结构role与外部role的预测及composition均为100%，无role为50%，final 95%区间下限+43个百分点，错误类型率0%，结构role State小25.38%
- 🟢 [Done] G2.5節目: 外部target roleを必要としない一hop位置型について、発見・独立採否・未知target転移・誤型付け拒否・保存再構築を完了 / Complete discovery, independent adoption, unseen-target transfer, mistyping rejection and persistence reconstruction for one-hop positional target roles without supplied labels / 完成无需外部target role的一hop位置类型发现、独立采纳、未见target迁移、错误类型拒绝及持久化重建
- 🟢 [Done] G2.6 role衝突解消: 同じaction・一hop roleのoutcome分岐だけを最大二hopへ分化し、二hopでも曖昧なら候補化しない。base roleごとのrefinementはsupport順上位8件に制限 / Refine only outcome collisions within one action and one-hop role to depth two, suppress candidates still ambiguous at depth two, and retain at most eight refinements per base by support / 仅将同一action及一hop role内的outcome冲突细分至二hop；二hop仍有歧义时不生成候选，每个base按support最多保留8个refinement
- 🟢 [Done] actor・target・任意entity変数を同じ構造role resolverへ接続し、relation欠落時は空型を共有せずunknownとしてabstain / Use one structural-role resolver for actors, targets and arbitrary entity variables; treat missing relations as unknown and abstain rather than sharing an empty type / 将actor、target及任意entity变量接入同一结构role resolver；relation缺失时作为unknown弃答，不共享空类型
- 🟢 [Done] 5 seed・各800 development・200 finalで二hop予測・compositionは100%対一hop50%、planは構造role・外部roleとも100%対誘導無効50%、誤型付け0%、final 95% CI下限は最低+42.5ポイント / Across five seeds with 800 development and 200 final cases each, two-hop prediction and composition reach 100% versus 50% one-hop; induced and supplied-role plans reach 100% versus 50% with induction disabled, mistyping is 0%, and the final 95% lower bound is at least +42.5 points / 5个seed中每个使用800个development及200个final案例；二hop预测及composition为100%对一hop 50%，结构role及外部role plan均为100%对禁用归纳50%，错误类型率0%，final 95%区间下限最低+42.5个百分点
- 🟢 [Done] G2構造獲得節目: context schemaと有界構造roleについて、発見・衝突解消・独立採否・未知identity転移・保存再構築を閉ループ化 / Close the structured-world G2 loop for context schemas and bounded roles across discovery, disambiguation, independent adoption, unseen-identity transfer and persistence reconstruction / 完成结构世界G2闭环：context schema及有界结构role的发现、消歧、独立采纳、未见identity迁移与持久化重建
- 🟢 [Done] schema v4でEventの重複ID・空collection・既定値を省略 / In schema v4 omit duplicated event IDs, empty collections and defaults / schema v4省略Event重复ID、空集合及默认值
- 🟢 [Done] graphのenergy・reliability等は履歴として保持し、pattern・structural pattern・primitiveの重複IDと既定値をlosslessに省略。候補・Event圧縮と合わせて26,399→21,137 bytes、19.93%削減 / Preserve graph energy and reliability history while losslessly omitting duplicated IDs and defaults from pattern and primitive records; combined reduction is 26,399 to 21,137 bytes, or 19.93% / 保留graph的energy及reliability历史，无损省略pattern及primitive记录中的重复ID与默认值；合计由26,399降至21,137 bytes，减少19.93%
- 🟢 [Done] 5 seedのG2全Stateでschema v4を評価し、平均134,478→102,287 bytes・23.94%削減、5,000予測・2,250計画・Composition・simulation差分0 / Evaluate schema v4 over five full G2 states: 134,478 to 102,287 mean bytes, 23.94% reduction and zero differences over 5,000 predictions, 2,250 plans, composition and simulation / 在5个完整G2 State上评估schema v4：平均134,478降至102,287 bytes，减少23.94%，5,000次预测、2,250次规划、Composition及simulation差异为0

詳細設計: [未分知と概念凝縮 / Undivided Knowledge and Concept Condensation / 未分知识与概念凝聚](RISA-Undivided-Knowledge-and-Concept-Condensation.md)

候補の追加価値検証: [G2候補転移評価 / Candidate transfer evaluation / 候选迁移评估](G2-Candidate-Transfer-Evaluation-2026-09-08.md)

時間列候補の追加価値検証: [G2時間列候補評価 / Temporal candidate evaluation / 时间序列候选评估](G2-Temporal-Candidate-Evaluation-2026-09-09.md)

関係候補の追加価値検証: [G2関係候補評価 / Relational candidate evaluation / 关系候选评估](G2-Relational-Candidate-Evaluation-2026-09-09.md)

任意関係候補の追加価値検証: [G2任意関係評価 / Generic relation evaluation / 任意关系评估](G2-Generic-Relation-Evaluation-2026-09-09.md)

派生候補の追加価値検証: [G2派生候補評価 / Derived candidate evaluation / 衍生候选评估](G2-Derived-Candidate-Evaluation-2026-09-11.md)

相関contextの連言選択検証: [G2 context連言評価 / Context conjunction evaluation / Context合取评估](G2-Context-Conjunction-Evaluation-2026-09-12.md)

構造roleの独立比較: [G2構造role評価 / Structural role evaluation / 结构role评估](G2-Structural-Role-Evaluation-2026-09-12.md)

構造role衝突の独立比較: [G2 role曖昧性解消評価 / Role disambiguation evaluation / Role消歧评估](G2-Role-Disambiguation-Evaluation-2026-09-13.md)

日本語: [G2比較結果](G2-Structural-Reuse-Evaluation-2026-09-08.md)では、final 200 episodeでRISAは観測から前提を学ぶ
composition 100%（具体遷移表0%）、binding 100%（同75%、役割束縛なし75%）、B期drift 75%（同33.3%、
変化適応なし33.3%）だった。Control、明示前提composition、A1/A2は100%を維持し、Uncertaintyは94%で同率だった。
この旧評価では役割型を入力で与えていた。G2.5では一hopの位置roleに限って外部labelを除去したが、意味型の自動発見ではない。保存量は静的学習後138,918 bytes対3,458 bytesで、効率の課題は未解決である。

English: The [G2 comparison](G2-Structural-Reuse-Evaluation-2026-09-08.md) reports 100% versus 0% on learned-
applicability composition, 100% versus 75% on binding, and 75% versus 33.3% in phase B drift over the pooled final
episodes. Control, supplied-precondition composition and A1/A2 remain at 100%; uncertainty ties at 94%. Target roles
were supplied in that benchmark. G2.5 removes them for one-hop positional roles, but does not establish semantic type discovery. Static state remains large at 138,918 bytes versus 3,458 bytes.

简体中文: [G2比较结果](G2-Structural-Reuse-Evaluation-2026-09-08.md)显示：从观测学习适用条件的composition为100%对0%，
binding为100%对75%，B阶段drift为75%对33.3%。Control、已提供前提的composition及A1/A2保持100%，Uncertainty同为94%。
该旧评估中的target角色由输入提供。G2.5已在一hop位置role范围内移除外部标签，但尚未证明语义类型自动发现。静态状态仍为138,918 bytes，而基线为3,458 bytes。

日本語: G0/G1後、構造共有なし・具体遷移表との比較を固定plannerで実施する。最終採用の初期閾値は、
compositionとbindingの両方で最強の適用可能baselineより成功率が5ポイント以上高く、差の95%区間下限が0超、
同じ上限予算を守り、既知課題の低下が2ポイント以内であること。閾値は実験前の設計値で、測定結果ではない。
満たさない場合はfailureを一つ選んで改訂し、2回の事前登録比較でも改善しなければ役割表現・共有単位を再検討する。
自動schema獲得が勝てなければ、明示schemaを使う説明可能な記憶・計画部品へ用途を絞る。

G2.1〜G2.3は対象別ablationで5ポイントを超える改善を示したが、当初の広いgateは未達である。
明示前提compositionが具体遷移表と同率だからである。G2.4ではcontext schemaの閉ループを完了し、G2.5では
一hop構造roleが外部roleと同率、roleなしより+50ポイントとなった。G2.6では二hop衝突解消も+50ポイントとなり、構造世界でのG2実装順序を閉じた。意味型発見とは扱わず、広いgate未達の主因であるoracle相当の明示前提baselineとの同率は残す。機能追加を重ねずG3でscaleとcostを測る。

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

G2.1–G2.3 exceed five points in their targeted ablations, but the original broad gate is not yet met because supplied-
precondition composition still ties the grounded table. G2.4 completes the context-schema loop. In G2.5, one-hop
structural roles tie supplied roles and gain 50 points over no roles. G2.6 also gains 50 points by resolving two-hop
collisions, closing the G2 implementation sequence in the structured world. This is not semantic type discovery, and
the tie with an oracle-like supplied-precondition baseline remains the reason the broad gate is not met. Move to G3
scale and cost measurement instead of adding another feature layer.

简体中文: G0/G1后固定规划器。初始采纳条件：组合与绑定任务均超过最强适用基线至少5个百分点，
差值95%区间下限大于0，遵守相同预算上限，已知任务下降不超过2个百分点。以上是预设门槛，不是实测结果。
两轮预注册改订后仍无改善，则重新考虑绑定与共享表示；自动schema归纳无收益时，收敛为使用显式schema的可解释记忆与规划组件。

概念凝聚还必须比无候选版本降低实测描述长度，且不增加错误泛化。只有当第二代及后续发现能改善与候选谱系证据不重叠的
独立留出回合时，才可称为智能复利。

G2.1至G2.3在各自消融中提升超过5个百分点，但仍未达到原先的广义门槛，因为已提供前提的composition仍与具体转移表持平。
G2.4已完成context schema闭环；G2.5的一hop结构role与外部role持平，并比无role版本高50个百分点。G2.6的二hop冲突消解同样提升50个百分点，从而完成结构世界中的G2实现顺序。这不等于语义类型发现；与近似oracle的已提供前提baseline仍持平，因此广义门槛尚未通过。停止叠加功能，进入G3规模与成本测量。

## G3 — Adaptation and bounded cost / 継続適応と計算予算 / 持续适应与计算预算

- 🟢 [Done] G3.1: 3 seed・1k→10k→100k Eventの全9条件でindex版と全走査参照版の全予測field差分0。Event作業量を最小63.49倍、p95を最小20.37倍改善し、Replay windowは全sort参照と一致したまま128件に制限 / Across all nine rows over three seeds and 1k→10k→100k Events, every prediction field matches the full-scan reference; Event work improves by at least 63.49×, p95 by at least 20.37×, and the 128-Event Replay window matches a full sort / 在3个seed及1千→1万→10万Event的全部9个条件中，所有预测字段与全扫描参考一致；Event工作量至少改善63.49倍，p95至少改善20.37倍，128件Replay窗口与全排序一致
- 🟢 [Done] G3.2計測基盤: 機構別切替・A→B→Aランナーと4指標・A1固定条件からのmerge再提案・独立development検証を必須とする実験用採用継承 / Add mechanism switches, an A→B→A metric runner, merge reproposal from frozen A1 scopes and opt-in validation inheritance gated by independent development probes / 已添加机制开关、A→B→A指标运行器、基于冻结A1条件的合并重提议，以及须通过独立development探针的可选验证继承
- 🟢 [Done] G3.2開発preflight: 5 seed×7条件を完走したが、採用済みmerge・休眠・実行済みPrimitive分裂が全行0で機構機会gateは不合格 / Complete a 5-seed, 7-arm development preflight; the opportunity gate fails because adopted merges, dormancy and executed Primitive splits are zero in every row / 完成5个seed、7条件的开发预检；全部行中已采纳合并、休眠及已执行原语分裂均为零，机制机会门槛未通过
- 🟢 [Done] G3.2生命周期pilot: 独立probe評価で特化親2件とmergeを採用し、5 seedで休眠on/offの作動差を確認。drift効果は未測定 / Probe-backed adoption of two specialized parents and their merge yields a dormancy on/off contrast in five seeds; drift effects remain unmeasured / 独立探针评估采纳两个特化父候选及其合并，5个seed确认休眠开关的操作差异；漂移效果未测
- 🟢 [Done] G3.2分裂opportunity: 16 Eventの独立Replay fixtureで分裂on/offの実行差を確認。予測効果は未測定 / A separate 16-Event Replay fixture exercises the split on/off execution path; prediction effects remain unmeasured / 独立的16 Event重放fixture验证分裂开关的执行差异；预测效果未测
- 🟢 [Done] G3.2候補採用後preflight: A1ではmerge・休眠が作動するが、Bの1～4観測で採用/休眠が失効し、A2終了時の機構gateは不合格。採用ラベル予算も条件間で不一致 / A candidate-primed A→B→A preflight activates merge/dormancy at A1, but validation/dormancy disappear within 1–4 B observations; the final opportunity gate fails and adoption-label budgets differ across arms / 候选采纳后的A→B→A预检在A1触发合并与休眠，但B的1至4次观测使采纳/休眠失效；最终机制门槛未通过，条件间采纳标签预算也不同
- 🟢 [Done] G3.2失効診断: FullはB後にmerge提案自体が消え、A2でも戻らない。No splitは提案が残るが検証済み採用は戻らない / Full loses the merge proposal itself during B and does not recover it in A2; No split retains a proposal but never regains validated adoption / Full在B阶段失去合并提案且A2未恢复；No split保留提案但未恢复已验证的采纳
- 🟢 [Done] G3.2追加診断: No split/Merge onlyはA2後に1,200ラベルでmergeを再採用。Fullは提案の再出現に追加25～53 A2 Eventを要した。復帰直後の保持効果ではない / After A2, No split/Merge only re-adopt a merge with 1,200 labels; Full needs 25–53 extra A2 Events just to rediscover a proposal. This is not immediate-return retention / A2结束后No split/Merge only用1,200个标签重新采纳合并；Full仅重新发现提案就需额外25至53个A2 Event。这不代表刚返回时的知识保留
- 🟢 [Done] G3.2オンライン検証計測: drift runnerに検証callback、A/B共通ラベル上限、消費ID・判断数の記録、採点probeの学習/採用証拠への混入防止を実装。採用効果は未評価 / The drift runner now supports online validation callbacks, a shared A/B label cap, consumed-ID and decision accounting, and guards against scoring-probe leakage into learning or adoption evidence; no adoption effect is established / 漂移运行器现支持在线验证回调、A/B共用标签上限、消耗ID和决策计数，并防止评分探针混入学习或采纳证据；尚未证明采纳效果
- 🟢 [Done] G3.2オンライン採用の開発pilot: 5 seed×7条件でA2の1/6/12 Event後に最大3,600ラベルの検証を試した。No split/Merge onlyはmergeを再採用したが、Fullは提案不在で0ラベル、全条件でPrimitive分裂0のため機構機会gateは不合格 / A five-seed, seven-arm online adoption pilot tries validation after A2 Events 1/6/12 with a 3,600-label cap. No split and Merge only re-adopt merges, while Full has no proposal and consumes zero labels; all arms have zero Primitive splits, so the opportunity gate fails / 五个seed、七组条件的在线采纳试验在A2第1/6/12个Event后尝试验证，标签上限为3,600。No split和Merge only重新采纳合并，Full因无提案消耗零标签；全部条件的原语分裂均为零，机制机会门槛未通过
- 🟢 [Done] G3.2分裂drift小世界: 5 seedのA→B→Aでsplit onのみPrimitive分裂を1～2件実行したが、両条件のB/A2回復Event数とReplay再適用量は一致。発火は確認、効果は未確認 / In a five-seed A→B→A split micro-world, split-on executes one or two Primitive splits per seed, yet B/A2 recovery Events and Replay reapplications match split-off. Execution is confirmed; benefit is not / 在五个seed的A→B→A分裂小环境中，仅开启分裂的条件每seed执行1至2次原语分裂，但B/A2恢复Event数和Replay重新应用量与关闭条件相同；确认了触发，尚未确认收益
- 🟢 [Done] G3.2文脈別drift開発診断: indoorだけ変えoutdoorを保持するとA2入口の旧A精度は0.5残るが、5 seedすべてで分裂0。phaseを24/48 Eventに伸ばしても発火せず、累積Replay scoreが局所誤差を隠す可能性を特定 / In contextual drift, changing only indoor preserves 0.5 immediate A2 accuracy, but executes zero splits in all five seeds, including exploratory 24/48-Event phases; cumulative Replay score may mask local errors / 按情境漂移仅改变indoor而保留outdoor时，A2入口旧A准确率为0.5，但五个seed均未分裂；开发阶段延长至24/48 Event仍未触发，累计Replay分数可能掩盖局部错误
- 🟢 [Done] G3.2局所Replay診断: context別に独立証拠Eventを1回ずつread-only再採点。5 seedすべてでwarmのindoor 2/2件が誤り、outdoor 0/8件が誤りだが、累積Replay scoreは0.737～0.846で全体閾値0.6を上回る / Read-only re-scoring of distinct evidence Events finds 2/2 warm-indoor errors and 0/8 warm-outdoor errors in all five seeds, while cumulative Replay score remains 0.737–0.846 above the global 0.6 threshold / 只读重评各context的独立证据Event：五个seed中warm-indoor均为2/2错误、warm-outdoor均为0/8错误，但累计Replay分数仍为0.737至0.846，高于全局0.6阈值
- 🟢 [Done] G3.2条件付き分裂提案pilot: 実験用switchで5 seedすべて分裂を発火させたが、保持・B回復は同じでA2回復が1 seedで2 Event悪化し、誤りのないoutdoorにもvariantを生成。既定値には採用しない / An opt-in conditional split proposal fires in all five seeds but leaves retention and B recovery unchanged, delays A2 recovery by two Events in one seed, and creates variants for error-free outdoor context. Keep it disabled by default / 可选的情境式分裂提案在五个seed全部触发，但保留与B恢复不变，一个seed的A2恢复慢两个Event，并为零错误的outdoor建立variant；默认保持关闭
- 🟢 [Done] G3.2境界readout介入: B終了時のA/B probeとA2終了時のA probeでPrimitive除去は全seed・全条件で予測効果0件変化（Bのscore差0.05）。recent outcome無効化も効果0件（score差0.5）。この小世界の境界予測への寄与は限定的 / Boundary readout interventions change zero predicted effects when Primitives are removed across all seeds/arms (B score shift 0.05); disabling recent outcomes also changes zero effects (score shift 0.5). Their contribution to this world's boundary predictions is limited / 边界读取干预中，移除原语在全部seed和条件下均不改变预测效果（B分数差0.05）；关闭近期结果也不改变效果（分数差0.5）；其对该环境边界预测的作用有限
- 🟢 [Done] G3.2全phase寄与診断: Bの60更新前予測はPrimitive除去で全条件0件変化。条件付き分裂はA2で2/60件変わり、うちseed 23の誤予測はPrimitive除去で正解となる。未見actor/target probeもPrimitive除去で変化0件（target roleは入力済み） / Across 60 B pre-update predictions per arm, removing Primitives changes none. The contextual split arm has two A2 flips; removing Primitives corrects seed 23's error. Unseen-actor/target probes also have zero flips, with target role supplied / 每组B阶段60次更新前预测中，移除原语均不改变效果；情境式分裂组A2有两次变化，其中seed 23的错误因移除原语而纠正；未见actor/target探针也无变化，但target role由输入提供
- 🟢 [Done] G3.2役割条件付き具体遷移baseline: 同じEvent・probeで直近観測表と比較。5 seed合計でbaselineはB/A2各55/60の事前更新正解、RISA全体分裂は45/60・46/60、条件付き分裂は45/60・45/60。保持と未見actor/target境界精度は同じ / A last-observed role-conditioned table on identical Events and probes scores 55/60 pre-update in both B/A2 across five seeds, versus 45/60 and 46/60 for RISA global split and 45/60 in both for contextual split. Retention and unseen-actor/target boundary accuracy match / 在相同Event和探针上，最近观察的角色条件化表在五个seed的B/A2更新前均为55/60，RISA全局分裂为45/60与46/60，情境式分裂两阶段均为45/60；保留与未见actor/target边界精度相同
- 🟢 [Done] G3.2観測ノイズ開発試験: cleanと20%誤ラベルを同じ5 seedで比較。ノイズ下でRISAはA復帰時の保持が4 seedで高いがB終了時の潜在ルール精度は4 seedで0.5に留まる。分裂on/offは予測曲線が一致し因果効果なし / A paired clean/20% observation-noise stress test gives RISA higher A-return retention in four seeds but only 0.5 latent B accuracy in four seeds; split on/off trajectories match, so no causal split benefit is established / 配对的无噪声及20%观测噪声试验中，RISA在四个seed的A返回保留率较高，但四个seed的B潜在规则准确率仅0.5；分裂开关曲线相同，未证实因果收益
- 🟢 [Done] G3.2保持解釈gate: B終了時に基準精度の95%へ達した場合だけ条件付き保持を報告し、未達seedも生の保持率とともに残す。20%ノイズでは両モデルが同時にB適応したseedは0件 / Add an adaptation-qualified retention audit while keeping raw retention and every failed seed. In the 20% noise pilot, no paired seed reaches the B adaptation gate for both models / 增加B适应达标后的条件性保留审计，同时保留原始保留率和全部失败seed；20%噪声试验中没有两种模型同时达到B适应门槛的配对seed
- 🟢 [Done] G3.2復帰識別性監査: contextual worldではA/Bの4 probe中2件が完全同一queryで正解だけ逆。B完全適応かつ復帰手掛かりなしの場合、A2入口のA精度上限は0.5。旧知識保存の証明には使えない / An exact-query audit finds two contradictory A/B probes out of four; with perfect B prediction and no return cue, immediate A accuracy cannot exceed 0.5. This fixture cannot establish preserved A knowledge / 完全query审计发现四个A/B探针中两个标签相反；完全预测B且没有返回提示时，A2入口的A准确率不可能超过0.5，不能据此证明保存了A知识
- 🟢 [Done] G3.2復帰手掛かりcontrol: 同一`regime:A/B`を全方式へ渡すと衝突0件。20%誤ラベル下でRISAと回数集計表はB終了・A復帰とも5/5 seedで精度1.0、分裂on/offの予測は同じ。識別性は改善したが構造機構の利得なし / An observable-cue control removes exact-query conflicts; under 20% label noise, RISA and a role/context count table both reach 1.0 B-exit and A-return accuracy in all five seeds, with no split-on/off prediction difference / 可观察提示对照消除了完全query冲突；20%错误标签下，RISA与角色/情境计数表在五个seed的B结束和A返回准确率均为1.0，分裂开关预测无差异
- 🟢 [Done] G3.2分裂readout監査: 20%誤ラベルの条件付き分裂armは各seedでB側variantを4件作り、潜在Bルールに反する採用済みvariantが2/1/2/1/0件。Primitive除去はscoreを変えるが予測効果は変えず、分裂重みの安易な増加は危険 / Under 20% label noise, contextual splitting creates four B-scope variants per seed and adopts 2/1/2/1/0 off-rule variants; Primitive removal changes scores but not effects, so weight increases alone are unjustified / 20%错误标签下，情境分裂每个seed产生四个B范围变体，采纳的偏离潜在规则变体数为2/1/2/1/0；移除原语改变分数但不改变预测效果，不能仅提高权重
- 🟢 [Done] G3.2分裂variantのcontext境界: Primitive score・候補効果・選択結果・説明経路でsplit variantだけ完全context一致とし、一般Primitiveの部分一致は保持。7開発manifestの主要値変更0行 / Require exact context for split variants in scoring, candidate effects, chosen outcomes and supporting paths while retaining generic Primitive partial matching; seven development manifests have zero primary-metric changes / 分裂变体在评分、候选效果、选定结果及证据路径均须完整情境匹配，普通原语仍可部分匹配；七个开发manifest的主要指标无变化
- 🟢 [Done] G3.2分裂variant独立検証: 学習・採点・候補証拠と分離した16ラベルで、条件付き分裂armの誤ラベル由来採用variantを5 seedで2/1/2/1/0件検出。read-onlyで既定採用は未変更 / A 16-label panel disjoint from learning, scoring and candidate evidence detects 2/1/2/1/0 adopted noise-derived variants across five contextual-split seeds; the audit is read-only and default adoption is unchanged / 使用与学习、评分及候选证据分离的16标签面板，在五个情境分裂seed中检测出2/1/2/1/0个由错误标签形成的已采纳变体；审计为只读，默认采纳不变
- 🟢 [Done] G3.2分裂採用介入: 独立検証で不合格の2/1/2/1/0 variantをコピー上で非採用化しても、A/B計40予測の変更0件・精度差0。16教師ラベル/active seedの採用gateは実装せず、merge/dormancy寄与へ移る / Rejecting 2/1/2/1/0 held-out failures on disposable copies changes zero of 40 A/B predictions and no accuracy; do not add a 16-label-per-active-seed gate, and move to merge/dormancy attribution / 在副本中拒绝2/1/2/1/0个独立验证失败变体后，40次A/B预测及准确率均无变化；不增加每个active seed需16标签的门槛，转向合并/休眠贡献
- 🟢 [Done] G3.2候補生命周期readout介入: A1の5 seed×24 probeで採用済みmerge除外は予測効果0/120件、accuracy差0、score差0.2。休眠祖先の再活性化も予測・score差0。1,200教師ラベル/armに対する判断利得はなく、独立finalへ進めない / At the A1 boundary over five seeds and 24 probes, removing the adopted merge changes 0/120 effects and no accuracy, with a 0.2 score shift; reactivating dormant ancestors changes neither predictions nor scores. There is no decision benefit for 1,200 supervised labels per arm, so do not advance to an independent final / 在A1边界的五个seed×24探针中，移除已采纳合并候选后预测效果改变0/120、accuracy无差、score差0.2；重新激活休眠祖先也不改变预测或score。每组1,200个监督标签未带来决策收益，因此不进入独立final
- 🟢 [Done] G3.2未見context組合せcontrol: 5 seed×24 probeでmerge除外が80/120予測を変える条件を確認。ただし部分集合表は100%、RISAは66.67%。矛盾contextで期待する棄権はRISA 0/120、表120/120。drift優位性は未実証 / An unseen-context control yields 80/120 prediction changes on merge removal, but a subset table scores 100% versus RISA 66.67%; expected conflict abstention is 0/120 for RISA and 120/120 for the table. Drift advantage remains unproven / 未见情境组合对照中，移除合并改变80/120预测，但子集表正确率100%、RISA为66.67%；矛盾情境期待弃权时RISA为0/120、表为120/120，漂移优势仍未证明。 [Report / 結果 / 结果](G3.2-Candidate-Context-Transfer-2026-10-03.md)
- 🟢 [Done] G3.2実験用context衝突ガード: 最も具体的な観測部分集合の結果が衝突する場合のみ棄権するread-only評価を追加。矛盾120/120棄権、未見タグ80/120正解を維持、追加ラベル0。全Event走査のため既定推論へは未採用 / Add an opt-in read-only context-conflict policy: abstain on disagreeing most-specific observed subsets; 120/120 conflict abstentions, unchanged 80/120 nuisance accuracy, zero extra labels. Full Event scans prevent default inference adoption / 添加可选只读情境冲突策略：最具体观察子集结果冲突时弃权；矛盾120/120弃权、未知标签80/120正确保持不变、额外标签0。因扫描全部Event，尚未纳入默认推理
- 🟢 [Done] G3.2 context監査index: ingestion/置換で更新する評価用派生indexを実装。1k/10k/100kと全probeで判断・出典IDが走査版と完全一致。100k・3 queryは再利用文脈で300,000 Event参照→9文脈参照、unique文脈では300,000文脈参照。出典保存/出力はO(N)のままで、このcontext index単独ではG3.3完了を示さない / Implement an explicitly updated evaluation context index; decisions and provenance match the scan at 1k/10k/100k and all probes. At 100k over three queries, reused contexts reduce 300,000 Event reads to nine scope reads, while unique contexts require 300,000 scope reads. Provenance storage/output remains O(N); this context-index result alone does not establish G3.3 / 实现显式更新的评估情境索引；1千/1万/10万及全部探针的判断与来源均与扫描一致。10万及三个query中，复用情境将300,000次Event读取降至9次情境读取，唯一情境仍需300,000次情境读取；来源存储/输出仍为O(N)，此context索引结果本身不证明G3.3完成
- 🟢 [Done] G3.2未見contextのA→B→A負例: 5 seed×7条件でA1精度66.67%がB/A2終了時0%、回復未達。subset直近表はB 5〜7/A2 5〜6 Event、回数表はB 8〜10/A2 8〜11 Eventで100%へ回復。復帰cueなし・採用予算不一致のため保持/因果優位性は主張しない / A five-seed, seven-arm unseen-context drift control falls from 66.67% A1 accuracy to zero at B/A2 exit without recovery; subset latest recovers to 100% in B 5–7/A2 5–6 Events and subset count in B 8–10/A2 8–11. No return cue and unequal adoption budgets preclude retention/causal advantage claims / 五个seed、七组条件的未见情境漂移控制从A1的66.67%降至B/A2结束的0%，未恢复；子集最近表以B 5至7/A2 5至6个Event、计数表以B 8至10/A2 8至11个Event恢复至100%。无返回线索且采纳预算不一致，不主张保留或因果优势。 [Report / 結果 / 结果](G3.2-Nuisance-Transfer-Drift-2026-10-03.md)
- 🟢 [Done] G3.2関係構造の復帰cue: 2-hop辺方向だけでA/Bを識別する5 seed×7条件、採用ラベル全方式0件。既定RISAはB 100%・A復帰0%、同じ2-hop役割投影のRISA/表はB/復帰100%・A2回復0 Event。Event/query証拠routingの差を分離、機構gateは不合格 / A relation-direction return cue across five seeds and seven arms with zero labels gives default RISA 100% B but 0% immediate A return; RISA/tables with the same two-hop role projection reach 100% B/return and zero A2 recovery Events. Isolate Event/query evidence routing; mechanism gate still fails / 五个seed、七组条件及零标签的关系方向返回线索中，默认RISA的B为100%、即时A返回0%；相同两跳role投影的RISA/表达到B/返回100%、A2恢复0 Event。分离Event/query证据routing差异，机制门槛仍失败。 [Report / 結果 / 结果](G3.2-Relational-Return-Cue-2026-10-03.md)
- 🟢 [Done] G3.2 role readout対応: `target_role_readout_hops=2`をopt-in実装し、Event/query証拠・直近結果・既知entityのscopeを一致。5 seedでB/即時保持100%、A2回復0、720完全PredictionResultが保存再構築/全走査と一致。schema v5に設定保存、旧stateは既定1。同role driftと欠損関係も検証し、強い2-hop表と同等 / Implement opt-in depth-two target-role readouts with aligned Event/query evidence, recent outcomes and known-entity scopes; five seeds reach 100% B/immediate retention and zero A2 recovery, with 720 complete PredictionResults equal after reload/full scan. Schema v5 persists the mode, legacy defaults to one; same-role drift/missing relations verified. Matches strong two-hop tables / 实现可选两跳target-role读取，对齐Event/query证据、近期结果及已知entity scope；五个seed的B/即时保留100%、A2恢复0，720个完整PredictionResult重载/全扫描一致。schema v5保存模式，旧state默认一跳；验证同role漂移及缺失关系，与强两跳表同等
- 🟢 [Done] G3.2文脈条件付きrole候補生成: opt-inで文脈内の衝突だけを2-hopで解決し、反例を保持。5 seedでA1 6/B・A2 12候補、全候補未採用でdrift精度差0。query付き適用/継承probeを追加し、Bコピーで独立400ラベルによりA warm mergeを採用、nuisance 80/240件が正解へ変化。schema v6へ方針保存、30 checkpoint保存同値。元軌跡の回復/保持利得ではない / Opt-in context-conditioned role discovery preserves counterexamples and yields six A1/twelve B–A2 candidates over five seeds, with zero measured drift gain while unadopted. Query-backed adoption/extension probes validate an A warm merge on B copies with 400 independent labels, changing 80/240 nuisance probes to correct. Schema v6 persists policy; 30 checkpoints reload equally. No recovery/retention gain in the original trajectory / 可选情境条件role发现保留反例，五个seed中A1六个、B–A2十二个候选，未采纳时漂移收益为零。query支持的采纳/继承探针在B副本用400独立标签采纳A warm merge，80/240 nuisance探针变为正确。schema v6保存策略，30 checkpoint重载一致；原轨迹恢复/保留无收益。 [Report / 結果 / 结果](G3.2-Context-Conditioned-Discovery-2026-10-03.md)
- 🟢 [Done] G3.2 query付きオンライン採用ablation: 5 seed・7条件に同じ1,200ラベル上限、実消費0/800/1,200を記録。全機構ありでmerge採用・親2候補休眠を実行したが、B直後のA未見文脈80/120正解はmergeなしと同じ。A2初回更新で16/120（休眠なし48/120）、終了時全条件0。強い2-hop部分集合表は追加ラベル0でA/B各120/120。175保存checkpoint同値、独立final未実行 / Online query-backed adoption over five seeds and seven arms records equal 1,200-label availability and unequal 0/800/1,200 consumption. Merge adoption and two-parent dormancy execute, but full matches no-merge at 80/120 A nuisance answers; first A2 update drops full to 16/120 versus 48/120 without dormancy, all end at zero. Strong subset tables retain 120/120 per regime without labels. 175 reload checkpoints agree; no independent final / 五个seed七条件共享1,200标签上限，记录0/800/1,200实际消耗。合并及父候选休眠执行，但完整条件与无合并均为80/120；A2首次更新完整16/120，无休眠48/120，最终均0。强子集表无标签保持每种环境120/120；175重载checkpoint一致，未进行独立最终评估。 [Report / 結果 / 结果](G3.2-Role-Online-Ablation-2026-10-03.md)
- 🟢 [Done] G3.2検証不変の親再活性化: opt-in training optionで失効descendantの代替がなく、親の証拠・検証・lineageが不変のときだけ再活性化。5 seed・7条件の35組で追加ラベル0・採用判断同一、全機構ありのA2初回未見文脈正解16/120→48/120、終了時は両方0。350保存checkpoint同値、強い部分集合表には未達 / Opt-in unchanged-parent reactivation after replacement expiry improves full first-A2 nuisance correctness 16/120→48/120 over 35 paired rows, with identical labels and adoption decisions; both end at zero. 350 reload checkpoints agree; strong subset tables remain better / 可选验证不变祖先重新激活在35配对中，将完整条件A2首次未见情境正确数16/120提高到48/120，标签及采纳决定相同，最终均0。350重载checkpoint一致，仍弱于强子集表。 [Report / 結果 / 结果](G3.2-Orphaned-Dormancy-2026-10-03.md)
- 🟢 [Done] G3.2再検証寿命・予算control: 5 seed・7条件・3方針・2上限の210実行。4,800上限の独立再採用で更新前正解168/1,440→552/1,440、full実消費22,000ラベル、no-mergeも552で14,000。強い部分集合表は0ラベルで1,440正解。1,200上限はfull再検証15回を停止。1,260保存checkpoint同値、独立final未実行 / 210 fixed-schedule runs measure re-adoption lifetime and cost: full improves 168→552/1,440 pre-update answers with 22,000 labels; no-merge matches with 14,000, while strong subset tables score 1,440 without labels. Low-cap full blocks all 15 refreshes; 1,260 reload checkpoints agree; no independent final / 210固定日程运行测量重新采纳寿命及成本：完整条件168→552/1,440，消耗22,000标签；无合并同分仅14,000，强子集表0标签全对。低预算完整条件停止十五次刷新，1,260重载checkpoint一致，未独立最终评估。 [Report / 結果 / 结果](G3.2-Revalidation-Budget-2026-10-05.md)
- 🟢 [Done] G3.2検証scope監査: 5 seedで範囲外の親更新後も不変候補の検証を0ラベルで維持し、範囲内counterexample・役割・lineage mutationは15/15拒否。既存固定予算controlではfullとno-mergeが552/1,440で同点、fullは8,000ラベル多く、強い部分集合表は0ラベルで1,440/1,440 / Across five seeds, unchanged scoped validation survives broader-parent updates with zero labels, while all 15 in-scope counterexample/role/lineage mutations are rejected. Full ties no-merge at 552/1,440 while spending 8,000 more labels; the strong subset table reaches 1,440/1,440 with zero labels / 五个seed中，不变作用域验证在宽父更新后以零标签保留，作用域内反例、角色及谱系的15项变更全部被拒绝；full与no-merge同为552/1,440但多耗8,000标签，强子集表零标签达到1,440/1,440。 [Report / 結果 / 结果](G3.2-Scope-Expiry-Audit-2026-10-05.md)
- 🟢 [Done] G3.2開発判断: 機構作動・識別可能性・readout・scope・再検証費用を分離したが、merge/split/dormancyは強いbaselineへの回復・保持優位を示さず、独立finalを消費せず負の結果として完了 / Close G3.2 development without spending an independent final: mechanism execution, identifiability, readout, scope and revalidation cost are isolated, but merge/split/dormancy do not beat strong baselines on recovery or retention / G3.2已分离机制触发、可识别性、读取、作用域及重新验证成本，但合并、分裂及休眠在恢复或保留上未超过强基线，因此不消耗独立最终集并以负面结果完成
- 🟢 [Done] G3.3a 実学習経路のstage計測、process時間上限、予測・計画・凝縮・保存復元の再現runnerを実装 / Implement real-training stage profiling, bounded processes, prediction/planning/compaction/persistence checks / 已实现真实学习阶段计时、有界进程及预测/规划/压缩/持久化检查。[Protocol / 評価契約 / 协议](G3.3-End-to-End-Protocol.md)
- 🟢 [Done] G3.3b 変化検出で履歴全体のsortを除去し、時系列indexから直近runと直前Eventだけ参照。走査fallbackと全状態が一致 / Remove full-history sorting from change detection; read the recent run and predecessor through event order with exact scan-fallback state equality / 变化检测不再排序全部历史，利用时序索引读取最近序列及前一Event，与扫描回退的完整状态一致
- 🟢 [Done] G3.3c 固定45秒の実測で1k全経路・12/12予測・復元不一致0を確認。10k/100kは4k完了checkpointで時間上限、1Mは見送り / Measure 1k end-to-end with 12/12 correct predictions and zero reload mismatches; 10k/100k time out at a 4k completed checkpoint; defer 1M / 实测1千完整路径，12/12预测正确且恢复不一致为0；1万/10万在4千完成checkpoint达到预算，暂不测试100万。[Report / 評価報告 / 报告](G3.3-End-to-End-Evaluation-2026-10-07.md)
- 🟢 [Done] G3.3d 共活性隣接index、固定点代謝worklist、検証用の根拠出力省略、前提観測index、証拠membership setで全処理を改善。凍結Git関数と18保存checkpoint・108全予測・108復元予測が一致 / Optimize coactivation, metabolism, validation provenance output, observed applicability and evidence membership; match frozen Git functions at 18 persisted checkpoints, 108 full predictions and 108 reload predictions / 优化共活性、代谢、验证来源输出、前提观测及证据membership，与冻结Git函数的18保存checkpoint、108完整预测及108恢复预测一致
- 🟢 [Done] G3.3 全経路評価: 同じ45秒上限で1k/10k/100kを0.274/2.781/40.314秒で完了。各12/12正解、凝縮・復元不一致0。100k最大RSSは2.045GiB、候補0の容量fixtureであり凝縮の実証とは区別 / Complete 1k/10k/100k in 0.274/2.781/40.314s under the same 45s cap, with 12/12 correct and zero compaction/reload mismatches per scale; peak 100k RSS is 2.045GiB and the zero-candidate capacity fixture establishes no condensation benefit / 在相同45秒预算下以0.274/2.781/40.314秒完成1千/1万/10万，各12/12正确且压缩/恢复不一致为0；10万峰值RSS为2.045GiB，零候选容量环境不证明凝聚收益。[Report / 評価報告 / 报告](G3.3-Incremental-Scale-Evaluation-2026-10-07.md)
- 🔴 [Later] G3.3 1M: 保存復元のmemory増幅と費用を見直し、専用の容量検討後に判断 / Review persistence memory amplification and cost before a dedicated 1M capacity decision / 复核持久化内存放大及成本，再决定100万容量测试
- 🔴 [Later] G3.2情報量を揃えた新world: 負例と直接cue controlを残し、履歴キーを直接選ばない復帰手掛かり、強い表baseline、固定ラベル予算を持つ新しい事前登録研究として再開 / Revisit an information-matched drift world only as a new preregistered study with a non-key-like return cue, strong table baselines and a fixed label budget / 仅作为新的预注册研究重新开展信息匹配漂移环境，使用不直接选择历史键的返回提示、强表基线及固定标签预算
- 🟢 [Done] 計測に基づく保存最適化: compact JSONの標準encoderを採用し、100k新規保存中央値12.901→6.874秒、保存量161.38→85.82MB。整形指定・schema・根拠・復元・原子的backupを保持。分割保存の試行はメモリ改善がなく棄却 / Adopt the standard compact encoder: 100k fresh-save median 12.901→6.874s and bytes 161.38→85.82MB, preserving optional pretty output, schema, evidence, restoration and atomic backup; reject the buffered-save trials without memory benefit / 采用标准compact encoder，10万新建保存中位数12.901→6.874秒，161.38→85.82MB，保持可选整形、schema、证据、恢复及原子backup；无内存收益的分块保存试验已撤回。[Report / 報告 / 报告](Software-Optimization-2026-10-07.md)
- 🟢 [Done] 保存最適化後のG3.3再確認: 100k全経路39.575秒、12/12正解、復元不一致0、最大RSS1.842GiB。全体速度は以前とほぼ同じで、保存量減は学習凝縮ではなくJSON表現による / Recheck G3.3 after persistence optimization: 100k completes in 39.575s with 12/12 correct, zero reload mismatches and 1.842GiB peak RSS; overall speed is approximately unchanged and lower bytes reflect JSON representation, not learned condensation / 持久化优化后复核G3.3，10万39.575秒、12/12正确、恢复不一致0、峰值RSS1.842GiB；整体速度大致不变，存储减少来自JSON表示而非学习凝聚
- 🟠 [Next] G3.4: Eventあたり保存量・active構造数・候補数・記述長とqueryあたり探索量の成長曲線を測る / Measure growth curves for bytes, active structures, candidates and description length per Event, and search work per query / 测量每Event的存储量、活跃结构数、候选数及描述长度，以及每query探索量的增长曲线
- 🔴 [Later] G3.5 RetNet由来の同値実行研究: 構造summaryに限り、offline並列・online逐次・chunk逐次の3経路を同一意味論から導出し、全`PredictionResult`・採用判断・永続化checkpointの完全一致を先に検証。逐次状態bytesと1 Eventあたり更新量が履歴長に依存しないか測る / RetNet-inspired equivalent execution: derive offline-parallel, online-recurrent and chunk-recurrent paths for structural summaries from one semantic contract; first require exact equality of every `PredictionResult`, adoption decision and persistence checkpoint, then test whether recurrent state bytes and per-Event update work are history-length invariant / RetNet启发的等价执行研究：仅针对结构摘要，从同一语义契约推导离线并行、在线递归及分块递归三条路径；先验证全部`PredictionResult`、采纳决定及持久化checkpoint完全一致，再测量递归状态字节数和每Event更新量是否不随历史长度增长
- 🔴 [Later] G3.6 多時間尺度保持ablation: 短期・中期・長期の固定減衰summaryを、減衰なし・単一減衰・現行Replay/休眠と同一予算で比較。G3.2の回復・保持・誤一般化・Replay費用に加え、各尺度の状態bytesと更新時間を報告し、学習済み構造や出典Eventを減衰summaryで置換しない / Multi-timescale retention ablation: compare fixed short-, medium- and long-decay summaries against no decay, one decay and current Replay/dormancy under matched budgets; report G3.2 recovery, retention, false generalization and Replay cost plus state bytes/update time per scale, without replacing learned structures or provenance Events / 多时间尺度保留消融：在相同预算下比较固定短、中、长期衰减摘要、无衰减、单一衰减及现有Replay/休眠；报告G3.2恢复、保留、错误泛化、重放成本及各尺度的状态字节数和更新时间，不用衰减摘要替代已学习结构或来源Event
- 🔴 [Later] score校正、unknownの区別、状態を含む探索重複判定 / Calibration, unknown states, state-aware search deduplication / 校准、未知状态及考虑状态的搜索去重

日本語: G3.1の予測read modelとReplay選択は採用条件を通過した。G3.1合成fixtureは完全な学習・graph構築・候補発見・planner探索を含まないため、それらは別のG3.3実学習fixtureで100kまで測定した。G3.2では更新範囲、Replay件数、回復速度と忘却をdrift下で測定した。

English: G3.1 prediction read models and Replay selection passed the adoption gate. Full learning, graph construction, candidate discovery and planner search were excluded from the G3.1 synthetic fixture; a separate G3.3 real-training fixture now measures those paths through 100k. G3.2 measured update scope, Replay work, recovery and forgetting under drift.

简体中文: G3.1的预测read model及Replay选择已通过采纳门槛。G3.1合成fixture不含完整学习、graph构建、候选发现及planner搜索；独立G3.3真实学习fixture现已测量这些路径至10万规模。G3.2已在漂移下测量更新范围、Replay工作量、恢复及遗忘。

詳細: [G3.1 Event access scale評価 / Event-access scale evaluation / Event访问规模评估](G3-Scale-Evaluation-2026-09-13.md)

G3.2評価契約: [Drift ablation protocol / 漂移消融評価契約 / 漂移消融评估协议](G3.2-Drift-Protocol.md)。主要指標は`recovery_events`、`retention_after_return`、`adaptation_touch_ratio`、`replay_cost_per_recovery`。G3.3ではtime/bytes/active structures/candidate generation per Eventとplanner expanded nodes per queryを記録する。G3.4ではEvent増加に伴い再利用構造が増え、保存量と探索量の増分が下がり、独立held-out成功率が上がるかを同時に検証する。曲線が比例増加する場合は凝縮仮説を見直す。

G3.2開発preflight: [機構機会監査 / Mechanism opportunity audit / 机制机会审计](G3.2-Drift-Preflight-2026-09-16.md)。35行すべてで採用済みmergeと休眠が0のため、独立finalへ進めず生命周期の作動機会を先に修正する。

追加の開発診断: [オンライン採用 / Online adoption / 在线采纳](G3.2-Online-Validation-Development-2026-09-18.md)、[Primitive分裂 / Primitive split / 原语分裂](G3.2-Split-Drift-Opportunity-2026-09-18.md)、[文脈別drift / Contextual drift / 按情境漂移](G3.2-Contextual-Drift-2026-09-18.md)、[条件付き分裂提案 / Conditional split proposal / 条件式分裂提案](G3.2-Contextual-Split-Proposal-2026-09-18.md)、[全phase予測寄与 / Phase-wide readout attribution / 全阶段预测贡献](G3.2-Readout-Attribution-2026-09-18.md)、[役割条件付きbaseline / Grounded role baseline / 角色条件化基线](G3.2-Grounded-Role-Baseline-2026-09-22.md)、[観測ノイズ / Observation noise / 观测噪声](G3.2-Observation-Noise-Development-2026-09-22.md)、[復帰手掛かり / Observable return cue / 可观察返回提示](G3.2-Observable-Return-Cue-2026-09-22.md)、[分裂readout / Split readout / 分裂读取](G3.2-Split-Readout-Audit-2026-09-22.md)、[分裂variant独立検証 / Split-variant held-out validation / 分裂变体独立验证](G3.2-Split-Variant-Heldout-Validation-2026-09-25.md)、[候補生命周期readout / Candidate lifecycle readout / 候选生命周期读取](G3.2-Candidate-Lifecycle-Readout-2026-09-28.md)。機構が作動しても回復効果がない場合と、提案消失・局所誤差の希釈により機会がない場合を別々に記録する。

G3.2 contract: the same four primary metrics separate recovery, retention, local rewrite scope and Replay work. G3.3 measures time, bytes, active structures and candidate generation per Event plus planner expanded nodes per query. G3.4 tests whether reusable structure grows while marginal storage/search work falls and independent held-out success rises; proportional growth triggers a reconsideration of condensation.

G3.2协议：四项主要指标分别衡量恢复、保留、局部改写范围及重放工作量。G3.3测量每Event的时间、字节、活跃结构和候选生成，以及每query的规划器扩展节点。G3.4同时检验可复用结构是否增加、边际存储与搜索成本是否下降、独立留出成功率是否提高；若结构按Event数量成比例增长，应重新审视凝聚假设。

### RetNet research note / RetNet研究ノート / RetNet研究说明

🔴 [Later] Research reference: Sun et al., [*Retentive Network: A Successor to Transformer for Large Language Models*](https://arxiv.org/abs/2307.08621), [HTML](https://arxiv.org/html/2307.08621v4). RetNet derives parallel, recurrent and chunkwise-recurrent forms of one retention computation: parallel execution supports training, recurrent execution maintains a fixed-size state for constant-cost autoregressive inference, and chunkwise recurrence combines parallel work inside chunks with recurrent summaries across chunks. Its multi-scale heads use different fixed decay rates; the paper's ablations report worse language-modeling results when decay or multi-scale decay is removed. The reported evidence concerns neural sequence modeling and language-model cost, not symbolic graph learning, concept condensation, provenance-preserving memory or drift adaptation.

日本語: 採用候補は「意味論を1つにしてbatch/online/chunk実行を同値化すること」「複数時間尺度を単一減衰・減衰なしと個別比較すること」「性能とmemory/throughput/latencyを同時に測ること」。RISAではEvent出典と検証済み構造を固定サイズ状態へ不可逆に畳み込まず、summaryは再構築可能な派生indexとして扱う。G3.1の完全一致原則を維持し、G3.2～G3.4の構造効果が成立する前にRetNetを本体へ組み込まない。

English: Carry forward three ideas: one semantic operation with batch/online/chunk execution, explicit no-decay/single-decay/multi-scale ablations, and joint quality plus memory/throughput/latency measurement. In RISA, never irreversibly fold provenance Events or validated structures into fixed-size state; summaries remain rebuildable derived indexes. Preserve G3.1 exact equivalence, and do not integrate RetNet into the core before G3.2–G3.4 establish structural benefit.

简体中文: 保留三项思路：同一语义操作具有batch、online及chunk三种执行形式；明确比较无衰减、单一衰减及多尺度衰减；同时测量质量、内存、吞吐量与延迟。RISA不得把来源Event或已验证结构不可逆地压入固定状态，摘要只能作为可重建派生索引。继续遵守G3.1完全一致原则，在G3.2至G3.4证明结构收益前不把RetNet并入核心。

## G4 — Recursive concept formation / 再帰的概念形成 / 递归概念形成

- 🔴 [Later] G4.1 二世代候補を既存構造から発見し、祖先証拠と重ならない独立held-outで追加利得を示す / Discover second-generation candidates from learned structures and demonstrate gain on independent held-out episodes disjoint from ancestral evidence / 从已学习结构发现第二代候选，并在与祖先证据不重叠的独立留出回合中证明增益
- 🔴 [Later] G4.2 Event→Primitive→Schema→Macro→抽象relationの3～4段階が人手ラベルなしで形成されるか検証 / Test whether three to four levels of Event-to-Primitive-to-Schema-to-Macro-to-abstract-relation hierarchy arise without supplied labels / 检验Event到原语、Schema、宏及抽象关系的三至四层层级能否在无人为标签下形成
- 🔴 [Later] G4.3 系譜証拠と分離した新しい小世界へ構造を転移し、モデル品質とplanner品質を四条件で分離 / Transfer structure to a new small world with disjoint lineage evidence and separate model from planner quality in four cells / 将结构迁移到谱系证据互不重叠的新小世界，并以四条件区分模型与规划器质量

日本語: 「経験から再利用可能構造が自己凝縮する」を中心仮説とし、保存量・探索量・未知問題成功率を同時に問う。独立held-outの改善がなければ二世代発見を知能増幅と呼ばない。自然言語・画像等の知覚adapterはG4の証拠を確認してから接続する。

English: The central hypothesis is self-condensation of reusable structure from experience, judged jointly by storage, search and unseen-problem success. Do not call second-generation discovery intelligence compounding without independent held-out gains. Connect language and image perception adapters only after the G4 evidence is established.

简体中文: 核心假设是经验自行凝聚为可复用结构，需同时考察存储量、搜索量与未知问题成功率。若没有独立留出增益，不把第二代发现称为智能增益；语言与图像感知适配器应在G4证据成立后接入。

## G5 — Adaptive discovery policy from search history / 探索履歴からの発見方針学習 / 基于探索历史的发现策略学习

🔴 [Later] Research reference: Zheng et al., [*Dream-RSI: Recursive Self-Improvement through Evolving Worlds* (PDF)](https://github.com/zhengkid/Dream-RSI/blob/main/papers/Dream-RSI.pdf), [arXiv HTML](https://arxiv.org/html/2609.14858). Dream-RSI replays **recorded discovery trees** to compare exploration policies over already observed branches, then deploys a selected policy to collect new trees. This is a meta-exploration idea; it does not demonstrate RISA's concept condensation or A→B→A adaptation.

| Status | 日本語 | English | 简体中文 |
| --- | --- | --- | --- |
| 🔴 [Later] G5.1 | 候補発見の分岐、親候補、選択順、予算、評価結果、停止理由を探索木として記録。RISAのEvent Replayとは別に扱う | Log discovery branches, parent candidates, selection order, budgets, evaluation outcomes and stopping reasons as search trees; keep this distinct from Event Replay | 将候选发现的分支、父候选、选择顺序、预算、评估结果与停止原因记录为搜索树，并与Event重放区分 |
| 🔴 [Later] G5.2 | 記録済み枝だけを厳密に再生し、未観測枝では結果を推測せずcoverage不足を報告。枝順・並列数・停止規則を同じ予算で比較 | Replay only recorded branches; report coverage gaps instead of inventing outcomes for unseen branches. Compare branch order, parallelism and stopping rules under matched budgets | 只重放已记录分支；对未观察分支报告覆盖缺口，不推测结果。在相同预算下比较分支顺序、并行度与停止规则 |
| 🔴 [Later] G5.3 | 固定探索方針、ランダム/単純heuristic、履歴要約による誘導を対照に、学習した方針を独立の新世界へオンライン展開 | Compare with fixed, random/simple heuristic and history-summary policies, then deploy the selected policy online in independent new worlds | 与固定、随机/简单启发式及历史摘要引导策略比较，再于独立新世界中在线部署选中策略 |

日本語: G3.2～G4で候補形成と効果・費用を確認してから着手する。評価器と候補生成器を固定し、方針だけを変える。主指標は独立世界でのheld-out成功率、必要な候補評価回数、wall time、保存量、探索coverageとする。オフライン履歴上で現行方針以上という結果は、その履歴への適合を示すだけで、未知枝や新世界での改善保証とはみなさない。候補系譜、方針開発用の木、最終評価用の木を分離し、同一計算予算で複数seedの区間を報告する。G5の採用は、独立オンライン評価で成功率を維持または改善しつつ実探索費用を下げ、G4の構造凝縮・誤一般化の基準を悪化させない場合に限る。

English: Start after G3.2–G4 establish candidate formation, benefit and cost. Hold the candidate generator and evaluator fixed while changing only the exploration policy. Primary measures are held-out success in new worlds, candidate evaluations, wall time, storage and search coverage. A policy that wins on its replay pool is only better on that pool; replay cannot validate unseen branches or guarantee online improvement. Separate candidate lineage, policy-development trees and final-evaluation trees, and report intervals across matched seeds and budgets. Adopt the policy only if independent online evaluation maintains or improves success while reducing real exploration cost without worsening G4 condensation or false generalization.

简体中文: 在G3.2至G4验证候选形成、收益与成本后再开展。固定候选生成器和评估器，仅改变探索策略。主要指标为独立新世界的留出成功率、候选评估次数、运行时间、存储量和搜索覆盖率。历史重放池上的优势只适用于该池，不能验证未观察分支或保证在线提升。分离候选谱系、策略开发树及最终评估树，在匹配的seed与预算下报告区间。只有独立在线评估在维持或提高成功率的同时降低实际探索成本，且不恶化G4的结构凝聚与错误泛化，才采纳该策略。

## Optional applications and execution research / 用途と実行層の追加研究 / 应用与执行层研究

- 🔴 [Later] 狭い業務手順・資源管理の外部ログでshadow評価 / Shadow evaluation on bounded workflow/resource logs / 在有限流程与资源日志上影子评估
- 🔴 [Later] Threat-Aware Ordering Repair。G1で探索失敗が主要因の場合に前倒し再判断 / Ordering repair, reconsider earlier only if G1 isolates search as the bottleneck / 若G1确认搜索为瓶颈再考虑提前顺序修复
- 🔴 [Later] Canopy、階層credit、SNN、スペクトル診断 / Canopy, hierarchical credit, SNN, spectral probes / Canopy、层级信用、SNN与谱诊断
- 🔴 [Later] Neural adapter、多言語知覚、multimodal、SARA接続 / Neural adapters, multilingual perception, multimodal and SARA integration / 神经适配器、多语言感知、多模态与SARA集成
- 🔴 [Later] SARA双方向接続の独立評価: 反復パターン→出典付きEvent候補→RISA構造と、検証済み構造→任意のrouting priorを別々にablationし、単体・上りのみ・下りのみ・双方向を同じ予算で比較する。時間スケール分担は測定する / Independently test a SARA bridge: repeated patterns to provenance-bearing Event candidates to RISA structure, and validated structure back as an optional routing prior. Ablate each direction and compare standalone, one-way and two-way systems under matched budgets; measure rather than assume timescale boundaries / 独立评估SARA双向接口：重复模式经带来源的Event候选进入RISA结构，已验证结构作为可选路由先验返回；分别消融两个方向，在相同预算下比较单体、单向与双向系统，并测量而非预设时间尺度边界
- 🔴 [Later] 微分可能論理ゲート: soft候補発見、hard gate離散化、時間・関係macroのBoolean/LUT compile / Differentiable logic gates for soft candidate discovery, hard-gate discretization and Boolean/LUT compilation of temporal and relational macros / 可微逻辑门：soft候选发现、hard gate离散化，以及时间与关系宏的Boolean/LUT编译
- 🔴 [Later] RDDLGN型の時間候補generatorと、連続知覚adapter・離散構造実行のhybrid比較 / Compare an RDDLGN-style temporal candidate generator and a hybrid continuous-perception/discrete-structure executor / 比较RDDLGN式时间候选生成器及连续感知adapter与离散结构执行的hybrid
- 🔴 [Later] BitNetを論理gateと同一視せず、`{-1,0,+1}`を促進・非接続・抑制relationへ写す三値符号付きEvent回路を比較 / Without equating BitNet with logic gates, compare a ternary signed-event circuit mapping `{-1,0,+1}` to excitatory, absent and inhibitory relations / 不将BitNet等同于逻辑门，比较把`{-1,0,+1}`映射为促进、无连接及抑制relation的三值有符号Event电路
- 🔴 [Later] dense三値行列、sparse signed graph、変化部分だけを伝播するevent-driven graph、Boolean/LUT、現行graphを同条件比較 / Compare dense ternary matrices, sparse signed graphs, change-only event-driven graphs, Boolean/LUT and the current graph under matched conditions / 同条件比较dense三值矩阵、sparse signed graph、仅传播变化部分的event-driven graph、Boolean/LUT及当前graph
- 🔴 [Later] `0`の非接続化では`absent/dormant/pruned`を区別し、可塑性、再配線cost、忘却を評価 / Distinguish absent, dormant and pruned zero-connections and evaluate plasticity, rewiring cost and forgetting / 将零连接区分为absent、dormant及pruned，并评估可塑性、重新连接成本及遗忘
- 🔴 [Later] CPU bitset/LUTで完全な意味一致と2倍以上のp95または走査量改善を確認した場合だけFPGA評価 / Evaluate FPGA only after a CPU bitset/LUT prototype achieves exact semantics and at least 2× p95 or scanned-work improvement / 仅当CPU bitset/LUT原型实现完全语义一致且p95或扫描量至少改善2倍后评估FPGA

日本語: 外部入力境界は出典・confidence・episode・観測maskを持つEvent候補にする。英語・日本語・简体中文の
ラベルは表示と知覚adapterで扱い、内部IDと役割意味を翻訳依存にしない。新moduleはG1と同じ評価に接続し、
個別ablationの改善がある場合だけ採用する。現規模ではクラウド・VPS・DBの追加構築は必要ない。

English: External event candidates carry provenance, confidence, episode and observation masks. Support English,
Japanese and Simplified Chinese at display/perception boundaries; internal identities and roles must not depend on
translation. Adopt modules only after controlled gains. Current scale does not justify new cloud/VPS/DB infrastructure.

简体中文: 外部事件候选携带来源、置信度、回合与观测mask。显示与感知边界支持英语、日语与简体中文，内部ID与角色语义不依赖翻译。
新模块只有在受控比较取得收益后采纳。当前规模不需要新增云、VPS或数据库基础设施。

詳細: [RISA微分可能論理ゲート研究 / Differentiable logic-gate research / RISA可微逻辑门研究](RISA-Differentiable-Logic-Gate-Research-Notes.md)

- 🟢 [Done] Event保存時の既定値コピーを削減し、1万Eventの新規保存中央値を16.3%、上書きを11.6%短縮。保存バイト列は一致 / Filter default Event fields before copying; 10k median fresh saves improve 16.3%, overwrites 11.6%, with identical bytes / 复制前筛选Event默认字段；1万Event新建保存中位数缩短16.3%，覆盖缩短11.6%，字节完全一致。[Report / 報告 / 报告](Event-Export-Optimization-2026-10-07.md)
- 🟢 [Done] 保存前の完全状態検証とCLI index再構築の個別計測・契約監査 / Isolate pre-save validation and CLI index reconstruction costs and audit their contracts / 分别测量保存前完整验证及CLI索引重建成本，并审计其契约。

- 🟢 [Done] 高多様性の予測索引再構築を2.848→0.074秒に短縮し、全208テスト・保存バイト列同値を確認。一時メモリ約2.1MB増、通常新規保存中央値2.6%遅延 / High-diversity index rebuilding improves 2.848→0.074s; all 208 tests and byte equivalence pass, with +2.1MB temporary memory and 2.6% bounded-case fresh-save overhead / 高多样性索引重建2.848→0.074秒；208项测试与字节一致性通过，临时内存增加2.1MB，常见场景新建保存中位数慢2.6%。[Report / 報告 / 报告](Index-Reconstruction-Optimization-2026-10-07.md)
- 🟢 [Done] Graph復元を個別評価し、重複レコード処理・schema移行・破損復旧を維持してcontextを共有 / Evaluate graph restoration and share contexts while preserving duplicate-record handling, migrations and recovery / 单独评估Graph恢复，共享context并保留重复记录处理、迁移及损坏恢复。

- 🟢 [Done] 復元時のcontext共有により1万Eventの読み込み中央値8.5%、新規保存10.7%、上書き11.8%短縮、保持メモリ約4.5MB削減。共有表のhit率99.9882%、128件に制限し復元後破棄。小規模・共有なしの負荷増加も記録 / Context sharing improves 10k median loading 8.5%, fresh save 10.7%, overwrite 11.8%, and retained memory about 4.5MB; audited hit ratio 99.9882%, local pool capped at 128, with measured small/no-reuse overhead / context共享使1万Event加载中位数缩短8.5%、新建保存10.7%、覆盖11.8%，保留内存减少约4.5MB；审计命中率99.9882%，临时池上限128项，并记录小规模及无复用成本。[Report / 報告 / 报告](Graph-Restoration-Optimization-2026-10-07.md)
- 🟢 [Done] 現行コードでG3.3全経路を再確認し、10万Eventを37.693秒、各規模12/12正解・復元差0で完了 / Recheck current G3.3 full paths: 100k completes in 37.693s, all scales 12/12 correct with zero restoration differences / 重新验证当前G3.3完整流程：10万Event为37.693秒，全部规模12/12正确且恢复差异为零。単発容量確認 / Single-run capacity check / 单次容量检查。
- 🟠 [Next] 学習・候補探索・Planningの残る負荷を個別評価 / Evaluate remaining learning/discovery/planning costs separately / 分别评估学习、候选发现及规划的剩余成本。

- 🟢 [Done] Event復元コピー削減の比較を完了し、安定した効果がない案を撤回 / Evaluate Event restoration copy reduction and revert the inconsistent trial / 完成Event恢复复制优化比较，撤回收益不稳定的方案。
- 🟢 [Done] Replayの未使用出典生成を省略し、1万Event中央値9.995→2.997ms、全238テストで状態・summary・公開予測互換性を確認 / Skip unused Replay provenance: 10k median 9.995→2.997ms, all 238 tests verify state, summary and public prediction compatibility / 省略Replay未使用的来源生成：1万Event中位数9.995→2.997ms，238项测试验证状态、summary及公开预测兼容性。[Report / 報告 / 报告](Replay-Optimization-2026-10-08.md)
- 🔴 [Later] Event復元のさらなる変更は、今後のprofileで費用対効果が確認された場合に再検討 / Revisit Event hydration only if later profiles justify it / 后续分析证明收益时再考虑Event恢复优化。
- ⭕️ [Pending] 実運用corpusでのtail評価：対象データ未提供 / Deployment-corpus tails: no deployment dataset supplied / 实际语料尾延迟：尚未提供运行数据。
- ⭕️ [Pending] ネイティブ累積allocation・コピー量の計測：xctraceが権限外のcache作成で起動失敗。許可された計測環境で再開 / Native cumulative allocations/copy telemetry: xctrace fails creating its out-of-workspace cache; resume in an authorized measurement environment / 原生累计分配及复制量：xctrace创建权限外缓存失败，待具备授权测量环境后恢复。
- ⭕️ [Pending] 直接消費電力：プロセス単位のjoule計測条件未整備 / Direct energy: calibrated process-level joule measurement is not configured / 直接能耗：尚未配置进程级焦耳测量条件。

- 🟢 [Done] Replay変更後のG3.3を同じ45秒条件で再確認。同条件retryは10万Eventを43.438秒・各規模12/12正解・復元差0で完了し、初回timeoutも保存 / Recheck G3.3 under unchanged 45s budgets: retry completes 100k in 43.438s, all scales 12/12 correct with zero restore differences; first timeout retained / 在原45秒预算下复查G3.3：重测10万Event为43.438秒，各组12/12正确且恢复差异为零，保留首次超时结果。
- 🟠 [Next] 10万Event全経路の予算余裕とtailを安定化。開発環境で測定済みの不安定性であり⭕️ [Pending]にはしない / Stabilize full-path 100k budget margin and tails; observed instability is testable, not Pending / 稳定10万Event完整流程的预算余量与尾延迟；这是已测量的可验证不稳定性，不归为Pending。

- 🟢 [Done] 学習履歴の全体sortと不要なepisode集計を削減。10万Event履歴選択中央値43.527→13.798ms、全経路30.390秒・12/12正解・復元差0。単一episodeの1万Eventは1.350ms遅延 / Remove history sorting and unrelated episode grouping: 100k selection median 43.527→13.798ms, full path 30.390s with 12/12 correct and zero restore differences; 10k single-episode selection adds 1.350ms / 减少历史排序及无关episode分组：10万Event选择中位数43.527→13.798ms，完整流程30.390秒、12/12正确且恢复差异为零；单episode的1万Event增加1.350ms。[Report / 報告 / 报告](History-Setup-Optimization-2026-10-08.md)

- 🟢 [Done] 全経路の直列3回測定とCPU診断を追加。1千・1万Eventは全回正解・復元差0、10万Eventは3回とも45秒timeout、別診断もtimeout。前回の単発成功を安定性の証拠としない / Add three serial full-path repetitions and CPU telemetry: all 1k/10k checks exact, all three 100k runs and the separate diagnostic time out at 45s; prior single success does not establish stability / 新增三次串行完整流程及CPU诊断：1千及1万Event全部正确且恢复差异为零，10万Event三次及另一次诊断均在45秒超时；之前单次成功不证明稳定性。[Report / 報告 / 报告](Scale-Stability-2026-10-09.md)
- 🟢 [Done] 変更後の短期再現確認：同一コードの直列3回で10万Eventがすべて45秒以内に完了。CPU・wall差も記録 / Short repeated post-change gate: all three serial 100k runs complete within 45s; CPU/wall gaps recorded / 修改后短期可重复性检查：三次串行10万Event均在45秒内完成，并记录CPU与wall差。

- 🟢 [Done] 入力検証の全履歴辞書コピーと無関係episodeの集計を削減。10万Event単体中央値22.025→13.319ms、重複・ID競合・順序判定を維持 / Remove full-history dictionary copying and unrelated episode maxima: 100k isolated median 22.025→13.319ms, preserving duplicate/conflict/order semantics / 减少输入验证的全历史字典复制及无关episode汇总：10万Event单独中位数22.025→13.319ms，保留重复、冲突及顺序语义。[Report / 報告 / 报告](Input-Validation-Optimization-2026-10-09.md)
- 🟢 [Done] 入力検証変更時のtimeoutを保存し、その後のEvent保存改善と分けて記録 / Retain the input-validation-stage timeout separately from subsequent export improvements / 保留输入验证修改后的超时结果，与后续Event保存优化分别记录。

- 🟢 [Done] 通常Event保存の再帰コピーを削減。1万Event新規保存中央値14.4%、上書き11.4%短縮、保存bytes・復元状態同値。完全検証・backup・atomic writeを維持 / Reduce recursive copying for flat Events: 10k median fresh saves improve 14.4%, overwrites 11.4%, with identical bytes/state and full validation/backups/atomic writes / 减少普通Event递归复制：1万Event新建保存中位数缩短14.4%，覆盖缩短11.4%，字节及恢复状态一致，保留完整验证、备份及原子写入。[Report / 報告 / 报告](Event-Flat-Export-Optimization-2026-10-09.md)
- 🟢 [Done] 変更後の45秒全経路確認は10万Event30.884秒、各規模12/12正解、復元差0。単発成功であり安定性は🟠 [Next]のまま / Post-change full path completes 100k in 30.884s with exact checks; this single run leaves stability Next / 修改后完整流程10万Event为30.884秒，各组12/12正确且恢复差异为零；单次成功，稳定性仍为Next。

- 🟢 [Done] Event保存変更後の全経路は全3回・全規模完了。10万Event worker中央値29.522秒、最大30.103秒、最小余裕14.897秒、各規模36/36正解・復元差0 / All three post-export gates complete at every scale: 100k worker median29.522s, max30.103s, minimum margin14.897s; 36/36 correct per scale, zero restoration differences / Event保存修改后三次完整流程全部规模通过：10万Event worker中位数29.522秒、最大30.103秒、最小余量14.897秒，各规模36/36正确且恢复差异为零。[Report / 報告 / 报告](Post-Export-Stability-2026-10-09.md)
- 🟠 [Next] 長期・負荷条件を変えたtail評価とG3.4の成長曲線・独立held-out品質評価。短期3回成功は本番p99保証にしない / Longer varied-load tails and G3.4 growth/independent held-out quality; three short successes do not guarantee production p99 / 长期及变化负载尾延迟、G3.4增长曲线及独立留出质量；短期三次成功不保证生产p99。

- 🟢 [Done] G3.4a 成長・未知entity転移pilotを事前固定3 seed・48/96/192/384 Eventで実行。roleあり100%、なし33.3%、復元効果差0。ただし構造2・候補0・保存増分ほぼ線形でjoint成長条件は不成立 / Run preregistered G3.4a growth/novel-entity pilot: role-aware100%, no-role33.3%, exact reload effects; structures2/candidates0 and near-linear marginal storage fail joint growth signal / 执行预先固定的G3.4a增长及未知entity迁移pilot：role100%、无role33.3%、恢复效果无差异；结构2、候选0及近线性边际存储未满足联合增长条件。[Report / 報告 / 报告](G3.4-Growth-Pilot-2026-10-09.md)
- 🟢 [Done] G3.4b 系列・誘導role・候補成長pilotの条件を事前固定し実行。G3.4全体は未完了 / Predeclare and run the sequence/induced-role/candidate-growth pilot; G3.4 remains unfinished / 预先固定并执行序列、诱导role及候选增长pilot；G3.4整体未完成。

- 🟢 [Done] G3.4bは3 seedすべて候補10（時間2・関係2）を発見、全予測・合成の復元一致。構造は4、採用候補0で成長・凝縮条件は不成立 / G3.4b discovers10 candidates per seed, including2 temporal/2 relational, with exact full prediction/composition reloads; primitives4/adopted candidates0 fail growth/condensation signals / G3.4b每seed发现10个候选（时间2、关系2），完整预测及合成恢复一致；结构4、采纳候选0，未满足增长及凝聚条件。[Report / 報告 / 报告](G3.4-Structural-Growth-2026-10-09.md)
- 🟢 [Done] G3.4合成の対象役割接地: 通常Primitiveを支持Eventの役割と照合し、未対応・逆向き対象の誤受理を8/24→0に修正。3 seed全checkpoint、候補on/offとも24/24、完全復元差0。修正回帰であり新規独立finalではない / Ground ordinary Primitives by supporting Event roles; false accepts fall 8/24→0 over all three-seed checkpoints, both candidate modes score24/24 with exact reloads. Repair regression, not new independent final / 普通Primitive按支持Event角色接地，误受理8/24→0，三个seed所有checkpoint两候选模式24/24及精确重载；修复回归而非新独立最终评估。 [Report / 結果 / 结果](G3.4-Composition-Grounding-2026-10-09.md)
- 🟢 [Done] 強化した合成baselineで旧候補回帰を再確認: role時間系列（seed23）は既存100%で候補利得0・冗長として拒否。actor/target関係（seed29）は候補100%・既存60%で40pt利得、既存の誤一般化率0.5は残存 / Stronger composition baseline makes the role-temporal regression redundant (seed23,100% ordinary success); actor/target relational regression retains100% versus60% candidate gain, with ordinary false-generalization0.5 unresolved / 强合成基线使role时间回归冗余（seed23普通100%）；actor/target关系回归候选100%对普通60%，普通误泛化0.5未解决
- 🟢 [Done] G3.4通常合成のactor/target接地: 同じ支持Eventでactor/target役割と具体identity等値を照合。5 seed・development100/final200件で候補/通常とも100%、誤一般化0、候補利得0で既存gateは冗長として拒否。joint witness・等値学習・抽象合成を回帰確認 / Ordinary joint actor/target grounding scores100% in both paths over100 development/200 final cases across five seeds, with zero false generalization and zero candidate gain; the unchanged gate rejects redundancy. Joint-witness/equality/abstract regression tests cover contracts / 普通joint actor/target接地在五seed开发100/最终200case中两路径100%、误泛化0、候选增益0，原gate拒绝冗余；joint witness、等值及抽象合成回归验证。 [Report / 結果 / 结果](G3.4-Actor-Binding-2026-10-09.md)
- 🟢 [Done] G3.4 joint品質v2: 新seed/entity・source均等化、役割/identity/状態/資源反例でRISA候補on/offと学習joint表＋simple BFSが全40/40、誤受理0。提案6・採用0、構造2固定・保存ほぼ線形で候補優位/凝縮gateは未達。v1 source交絡の失敗を保持 / New entity/source-balanced joint fixture ties learned-table/simple-BFS at40/40 across all checkpoints, zero false accepts; six proposed/zero adopted candidates and constant two primitives fail advantage/condensation gates. V1 source-confounding failure retained / 新entity及source平衡joint fixture所有checkpoint与学得表/simple BFS同为40/40，误受理0；提案六/采纳零、Primitive二固定，优越性/凝聚gate未通过，保留v1 source交络失败。 [Report / 結果 / 结果](G3.4-Independent-Joint-Quality-2026-10-10.md)
- 🟢 [Done] G3.4合成仕事量を直接計測: 診断あり/なしの完全結果同値。固定fixtureでnode48・Primitive検査96は一定だが、8/16/32 Eventの接地参照288/576/1,152は線形増加。macroのstep/kernelも別計測し、node0を仕事量0としない / Direct composition counters preserve complete results; node48/Primitive scans96 stay constant while grounding reads288/576/1,152 grow with8/16/32 Events. Macro step/kernel work is counted separately / 直接合成计量完整结果同值，node48/Primitive检查96固定，而8/16/32 Event接地访问288/576/1,152线性增长，macro step/kernel另计。 [Report / 結果 / 结果](G3.4-Composition-Search-Work-2026-10-10.md)
- 🟢 [Done] G3.4接地read model: opt-in joint役割/identity indexを実装。3 seed×5 checkpointで全走査/復元の完全結果一致、1,200/1,200正解。512 Eventでは構築512参照、80 queryの参照36,864→0 / Opt-in lossless grounding index preserves complete results across append/reload; 1,200/1,200 correct. At512 Events, build512 reads and warm query reads36,864→0 / 实现opt-in无损接地index，增量/重载完整结果同值，1,200/1,200正确；512 Event构建512访问，预热query访问36,864→0。 [Report / 結果 / 结果](G3.4-Primitive-Grounding-Index-2026-10-10.md)

### Memory Mosaics-inspired G3.4 controls — 2026-10-10

- 🟢 [Done] 予測に役立つ分解と依存条件保持を[設計契約](RISA-Structural-Factorization-and-Compositional-Reasoning.md#7-predictive-factorization-with-dependency-guards--2026-10-10)へ追加。論文再現・潜在因子発見・凝縮実証とは区別 / Document predictive factorization with dependency guards, distinct from paper reproduction, latent-factor discovery or condensation evidence / 将预测分解与依赖保持写入设计，区分论文复现、潜在因子发现及凝聚实证。
- 🟢 [Done] [未知組合せ・依存反例の比較実験](G3.4-Compositional-Holdout-2026-10-10.md)を3 seed・2世界・24/48/96 Eventで実行。局所遷移は既知、全交差経路は未知と監査。RISA候補on/off、制約保持表、同一BFSのRISA通常Primitiveは各360/360、誤受理0 / Run audited unseen-whole-path controls: native RISA on/off, guarded table and shared-BFS RISA primitives each score360/360 with zero false accepts / 三seed、两世界及三个checkpoint完成未知完整路径审计，RISA候选开关、约束表与共享BFS普通Primitive各360/360、误受理零。
- 🟢 [Done] 完全経路表は独立世界の未知4件を棄却。役割周辺化・資源リセット・ticket除去の対照は対応反例を誤受理し、依存条件の必要性を確認。弱い対照への勝利を固有の利得としない / Whole-path control misses four independent combinations; marginal-role, reset-resource and dropped-ticket controls expose targeted false accepts, not a strong-baseline advantage / 完整路径表漏掉四个独立组合，角色边际化、资源重置及删除ticket暴露对应误受理，不作为超越强基线的证据。
- 🟢 [Done] 完全結果720件の復元/計測一致、評価不変性を確認。候補18・採用0、候補利得0で既定gate不合格。接地Event参照は経験数に比例し、G3.4の凝縮条件は未達 / Verify720 complete reload/instrumentation matches and immutable evaluation;18 proposed/zero adopted candidates fail advantage gate, and linear evidence reads leave condensation unproven / 验证720个完整结果恢复/计量一致及评估不变；候选十八/采纳零、优势门槛未通过，证据读取线性增长，凝聚未证明。
- 🟠 [Next] G3.4接地indexの役割多様化・signature成長と学習/query交互実行の再構築費用を測定。独立world・同一planner品質/成長評価も継続 / Measure varied-role signature growth and interleaved learning/query rebuild cost; continue independent-world/same-planner quality and growth / 测量角色多样化、signature增长及学习/query交替重建费用，继续独立world/同planner质量与增长评估。
- 🟠 [Next] 初期checkpointで品質が飽和しない意味規則群と正当な候補採用機会を事前固定。未知組合せの必要Event数、独立化による誤受理、構造数・限界費用を強い因子化表と同一plannerで比較。採用gateは緩和しない / Freeze varied semantic worlds and legitimate candidate opportunities; compare learning curves, dependency errors and marginal costs against a strong factorized table with the same planner, without relaxing adoption gates / 预先固定变化语义world及真实候选机会，以同planner对比强因子化表的学习曲线、依赖误受理及边际成本，不放宽采纳门槛。
- 🔴 [Later] 構造効果の実証後に学習可能なkey/value記憶を別armとして検討。現実験はニューラルMemory Mosaicsを実装しない / Consider learned key/value memories as a separate arm only after structural benefit is established; current controls do not implement neural Memory Mosaics / 结构收益确立后再考虑可学习key/value记忆独立比较，目前未实现神经Memory Mosaics。

日本語: 未達項目は開発環境で検証可能なため🟠 [Next]として扱う。環境都合で試験不能な作業が発生した場合のみ⭕️ [Pending]へ移す。

English: Unfinished experiments remain testable development work, marked Next. Use Pending only for checks the development environment cannot execute.

简体中文: 未完成实验可在开发环境验证，保持Next；仅环境无法执行的验证才标记Pending。

### Compositional grounding index cost audit — 2026-10-10

- 🟢 [Done] [未知組合せfixtureでのindex費用監査](G3.4-Compositional-Grounding-Costs-2026-10-10.md): 候補on/off720 queryの完全結果一致、正解720/720・誤受理0。追加学習・cold構築・復元・診断有無も一致 / Verify720 exact compositional results with candidate on/off, append, cold build, reload and instrumentation;720/720 correct, zero false accepts / 候选开关720个组合query完整结果一致，追加学习、冷构建、恢复及计量模式均一致，全正确且误受理零。
- 🟢 [Done] warm接地Event参照を独立848/1,696/3,392・依存880/1,760/3,520から0へ削減（各40 query）。構築参照24/48/96とwitness検査224/234を別計数 / Reduce warm grounding Event reads to zero, separately counting24/48/96 build reads and224/234 witness checks per40-query panel / warm接地Event访问降为零，另计24/48/96构建读取及每40-query面板224/234 witness检查。
- 🟢 [Done] 3 seed×3回で構築・追加学習＋全再構築・query・実保存・loadを計測。保存バイト列同一、追加0 byte。論理summary1,325/1,343 byte、tracemalloc保持9,358 byte。全再構築方式・opt-inを維持 / Measure build, append plus full rebuild, query, actual save and load; identical persisted bytes, zero extra, logical summary1,325/1,343 bytes and traced retained9,358 bytes; keep opt-in full rebuild / 三seed×三次测量构建、追加学习加全重建、query、实际保存及load；持久化字节相同、额外零、逻辑summary1,325/1,343 byte、追踪保持9,358 byte；维持opt-in全重建。
- 🟢 [Done] 96 Event保存悪化と交互実行を下記の追加監査で切り分けた。旧測定は保持し、役割多様化・差分更新・既定有効化の判断は未完了 / Attribute the96-Event save regression and measure interleaving below; preserve old results, with role diversity, incremental updates and default enablement still open / 已完成下述96 Event保存及交替执行审计，保留旧测量；角色多样化、增量更新与默认启用仍待评估。

### Save GC attribution and interleaved updates — 2026-10-10

- 🟢 [Done] [保存GC・交互実行監査](G3.4-Save-GC-and-Interleaving-2026-10-10.md): 旧手順で35.5%悪化を再現し、世代2 GCがreference0/index12回へ偏ることを記録。GC停止を除く中央値差は2.6%、均等先行順の新規保存差は0.1%。元artifactにGC traceはなく再現実験での帰属 / Reproduce35.5% save regression with generation-2 GC skew0/12; GC-subtracted median gap2.6%, balanced-order fresh-save gap0.1%; attribution is from reproduction, not a trace of the original run / 复现35.5%保存恶化及世代2 GC偏斜0/12；扣GC中位差2.6%、均衡顺序新保存差0.1%，归因来自复现而非旧trace。
- 🟢 [Done] 既存費用benchmarkの既定3回を4回へ変更し先行順を均等化、結果へpaired_order_balancedを記録。保存検証・backup・fsync・本番GC動作は維持 / Balance the previous benchmark with four repetitions and record paired_order_balanced; preserve production validation, backup, fsync and GC / 旧benchmark默认改四次均衡先行顺序并记录paired_order_balanced，保留生产验证、backup、fsync及GC。
- 🟢 [Done] 1/3/24 Event更新×1/40 queryを比較。1,584更新のシリアライズ、32,472 queryの完全結果、144 checkpointの実保存/backup/復元が一致。1 queryでは再構築込みindexが遅く、40 queryでは本fixtureで短縮 / Compare1/3/24-Event updates with1/40 queries:1,584 serialized states,32,472 complete results and144 file/backup/reload checkpoints match; cold index loses at one query and improves at40 in this fixture / 比较1/3/24 Event与1/40 query：1,584序列化、32,472完整结果及144实文件/backup/恢复checkpoint一致；单query全重建更慢，40 query改善。
- 🟠 [Next] 低query密度での差分更新または全走査選択を、役割多様化・証拠変更・split・復元とともに評価。閾値を今回の2密度だけで決めずopt-in維持 / Evaluate incremental maintenance or full-scan selection for sparse queries with diverse roles, evidence changes, split and reload; retain opt-in without inferring a threshold from only two densities / 在多样角色、证据变化、split及恢复下评估低query密度的增量维护或全扫描选择，不凭两种密度定阈值，保持opt-in。
