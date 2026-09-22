# RISA Roadmap / RISA ロードマップ / RISA 路线图

Updated: 2026-09-16. [Design assessment / 設計評価 / 设计评估](RISA-Structural-AI-Assessment-2026-09-05.md)

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

日本語: [Done]は実装の存在を示し、研究仮説の実証とは区別する。G0、G1、G2.1〜G2.6とG3.1のEvent access scale検証まで完了し、直近はG3.2のdrift評価。
G4以降は重要でも[Later]とする。指標・閾値は評価前に固定し、結果を見て合格条件を緩めない。

English: [Done] means implemented, not scientifically validated. G0, G1, G2.1–G2.6 and G3.1 Event-access scale validation are complete; G3.2 drift evaluation is next and G4 onward is [Later].
Freeze metrics and thresholds before evaluation; do not relax gates after seeing results.

简体中文: [Done]表示已实现，不等于科学验证。G0、G1、G2.1至G2.6及G3.1 Event访问规模验证已完成，下一步是G3.2漂移评估；G4以后标为[Later]。
评估前固定指标与阈值，不根据结果放宽通过条件。

## Current baseline / 現在地 / 当前基础

| Status | 日本語 | English | 简体中文 |
| --- | --- | --- | --- |
| [Done] | 構造化Event、頻度学習、グラフ、簡易概念、Primitive、JSON保存 | Structured events, counts, graph, simple concepts, primitives, JSON persistence | 结构化事件、频度学习、图、简单概念、原语及JSON保存 |
| [Done] | 学習前予測、誤差履歴、共活性、代謝、Replay、文脈分裂の最小経路 | Minimal pre-update prediction, error history, coactivation, metabolism, replay, context splitting | 最小学前预测、误差历史、共激活、代谢、重放与上下文分裂 |
| [Done] | 状態消費・排他更新・数値資源・単位と上下限の部品 | Consumption, exclusive replacement, numeric resources, units and bounds | 状态消耗、互斥替换、数值资源、单位与边界 |
| [Done] | 分岐simulation、goal/constraint評価、what-if、AND/OR、偏序実行、threat検出 | Branch simulation, goal/constraint evaluation, what-if, AND/OR, partial-order execution, threats | 分支模拟、目标与约束评估、假设比较、AND/OR、偏序执行及冲突检测 |
| [Done] | G0反例、G1/G2評価基盤、G2学習機構を回帰テスト化し、全94テストが通過 | G0 counterexamples, G1/G2 evaluation and G2 learning mechanisms covered; all 94 tests pass | G0反例、G1/G2评估及G2学习机制已纳入回归测试，全部94项测试通过 |

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
- [Done] final 200 queryでcandidate-backed compactionを診断し、readout 81→2 bytes・p95非悪化でも総保存Stateが21,161→21,249 bytesへ増えたため総memory方式として棄却 / Diagnose candidate-backed compaction on 200 final queries; despite an 81-to-2-byte readout and no observed p95 regression, reject it because total persisted state grows from 21,161 to 21,249 bytes / 在200个final query上诊断候选压缩；尽管readout由81降至2 bytes且p95未见恶化，但持久化State总量由21,161增至21,249 bytes，因此作为总内存方案予以否决
- [Done] schema v4で候補schema・型変数・支持/反例IDを保存対象から外し、Event再発見とfingerprint一致時の評価復元へ変更。旧候補payload相当26,399→25,756 bytes / In schema v4 omit candidate schemas, typed variables, support and counterexample IDs; rediscover them from events and restore evaluations on fingerprint match, reducing 26,399 to 25,756 bytes / schema v4不再保存候选schema、类型变量、支持及反例ID，从Event重新发现并在fingerprint一致时恢复评估，使26,399降至25,756 bytes
- [Done] `specialized/merged`派生API、採用候補の`dormant`切替、二世代候補、親証拠fingerprint、DAG検証、祖先support/evaluationを含むheld-out重複禁止を実装 / Implement specialized and merged derivation APIs, dormant adopted candidates, second-generation candidates, parent-evidence fingerprints, DAG validation and held-out overlap rejection across ancestor support and evaluations / 实现specialized/merged派生API、已采纳候选休眠切换、第二代候选、父证据fingerprint、DAG验证及涵盖祖先支持与评估的留出重叠禁止
- [Done] 派生候補だけを保存し、再読込時に親fingerprint一致順で復元。親証拠変化時は派生候補を破棄し、dormant候補を推論indexから除外 / Persist only derived candidates, restore them in parent-fingerprint order, discard them when parent evidence changes and exclude dormant candidates from inference indices / 仅持久化派生候选，按父fingerprint一致顺序恢复；父证据变化时丢弃派生候选，并从推理索引排除休眠候选
- [Done] 再現性とprecision改善を満たすcontext specializationを自動提案し、互換な兄弟をcontext論理和付きでmerge。親との差を必須化し、採用時は同じ遷移の広い祖先をdormant化。5 seed・final 200件でmerge 100%対最良の直接親75%、広い祖先は50%・false generalization 100% / Automatically propose reproducible context specializations with precision gain, merge compatible siblings with context disjunctions, require gains over parents and make replaced broad ancestors dormant; over five seeds and 200 final cases merge reaches 100% versus the strongest direct parent's 75%, while the broad ancestor reaches 50% with 100% false generalization / 自动提出具备可复现性及precision提升的context分化，以context析取合并兼容兄弟，要求优于父候选并使被替代的宽泛祖先休眠；5个seed及200个final案例中merge达到100%，最强直接父候选为75%，宽泛祖先为50%且错误泛化100%
- [Done] 親ごとの自動specializationをprecision改善・support順の上位8件に制限し、候補爆発を局所的に抑制 / Limit automatic specializations per parent to the top eight by precision gain and support, locally bounding candidate growth / 按precision提升及support将每个父候选的自动分化限制为前8项，局部抑制候选爆炸
- [Done] 最大24 tagから単一・2連言の36条件を有限探索し、親ごと上位8候補、development winner 1候補だけをfinalへ進める選択契約を実装。学習時に完全相関する6 proxyを含む7候補から5 seedすべてで安定条件を選び、final 200件で100%対親50%、95% CI下限+43ポイント、false generalization 0%対100% / Search a bounded set of singleton and pairwise conjunctions from at most 24 tags, retain eight candidates per parent and allow one development winner into final; from seven candidates including six perfectly correlated training proxies, all five seeds select the stable condition and reach 100% versus the parent's 50%, a +43-point lower 95% bound and 0% versus 100% false generalization over 200 final cases / 从最多24个tag有限搜索单项及二元合取，每个父候选保留8项且仅允许1个development优胜者进入final；在含6个训练时完全相关proxy的7个候选中，5个seed均选中稳定条件，200个final案例达到100%对父候选50%，95%区间下限+43个百分点，错误泛化0%对100%
- [Done] G2.4のcontext schemaについて、発見・候補予算・相関解消・独立採否・推論置換・保存再構築を完了 / Complete discovery, candidate budgeting, correlation resolution, independent adoption, inference replacement and persistence reconstruction for G2.4 context schemas / 完成G2.4 context schema的发现、候选预算、相关性消解、独立采纳、推理替换及持久化重建
- [Done] 外部roleがないEvent/queryからtargetの一hoprelation位置署名を作り、安定した内部role IDへ変換。学習・候補発見・予測・composition・Replay・validation・CLI・保存再構築を同じresolverへ接続 / Build a one-hop relation-position signature for targets without supplied roles, convert it to a stable internal ID, and use one resolver across learning, discovery, prediction, composition, replay, validation, CLI and persistence reconstruction / 从未提供role的Event及query生成target一hop relation位置签名并转换为稳定内部ID，在学习、发现、预测、composition、重放、验证、CLI及持久化重建中使用同一resolver
- [Done] 5 seed・各800 development・200 finalで構造roleと外部roleは予測・compositionとも100%、roleなし50%、差のfinal 95% CI下限+43ポイント、未知・逆向きrelationの誤型付け0%。構造role Stateは外部role版より25.38%小さい / Across five seeds with 800 development and 200 final cases each, induced and supplied roles reach 100% prediction and composition versus 50% without roles; the final 95% lower bound is +43 points, mistyping is 0%, and induced-role State is 25.38% smaller / 5个seed中每个使用800个development及200个final案例；结构role与外部role的预测及composition均为100%，无role为50%，final 95%区间下限+43个百分点，错误类型率0%，结构role State小25.38%
- [Done] G2.5節目: 外部target roleを必要としない一hop位置型について、発見・独立採否・未知target転移・誤型付け拒否・保存再構築を完了 / Complete discovery, independent adoption, unseen-target transfer, mistyping rejection and persistence reconstruction for one-hop positional target roles without supplied labels / 完成无需外部target role的一hop位置类型发现、独立采纳、未见target迁移、错误类型拒绝及持久化重建
- [Done] G2.6 role衝突解消: 同じaction・一hop roleのoutcome分岐だけを最大二hopへ分化し、二hopでも曖昧なら候補化しない。base roleごとのrefinementはsupport順上位8件に制限 / Refine only outcome collisions within one action and one-hop role to depth two, suppress candidates still ambiguous at depth two, and retain at most eight refinements per base by support / 仅将同一action及一hop role内的outcome冲突细分至二hop；二hop仍有歧义时不生成候选，每个base按support最多保留8个refinement
- [Done] actor・target・任意entity変数を同じ構造role resolverへ接続し、relation欠落時は空型を共有せずunknownとしてabstain / Use one structural-role resolver for actors, targets and arbitrary entity variables; treat missing relations as unknown and abstain rather than sharing an empty type / 将actor、target及任意entity变量接入同一结构role resolver；relation缺失时作为unknown弃答，不共享空类型
- [Done] 5 seed・各800 development・200 finalで二hop予測・compositionは100%対一hop50%、planは構造role・外部roleとも100%対誘導無効50%、誤型付け0%、final 95% CI下限は最低+42.5ポイント / Across five seeds with 800 development and 200 final cases each, two-hop prediction and composition reach 100% versus 50% one-hop; induced and supplied-role plans reach 100% versus 50% with induction disabled, mistyping is 0%, and the final 95% lower bound is at least +42.5 points / 5个seed中每个使用800个development及200个final案例；二hop预测及composition为100%对一hop 50%，结构role及外部role plan均为100%对禁用归纳50%，错误类型率0%，final 95%区间下限最低+42.5个百分点
- [Done] G2構造獲得節目: context schemaと有界構造roleについて、発見・衝突解消・独立採否・未知identity転移・保存再構築を閉ループ化 / Close the structured-world G2 loop for context schemas and bounded roles across discovery, disambiguation, independent adoption, unseen-identity transfer and persistence reconstruction / 完成结构世界G2闭环：context schema及有界结构role的发现、消歧、独立采纳、未见identity迁移与持久化重建
- [Done] schema v4でEventの重複ID・空collection・既定値を省略 / In schema v4 omit duplicated event IDs, empty collections and defaults / schema v4省略Event重复ID、空集合及默认值
- [Done] graphのenergy・reliability等は履歴として保持し、pattern・structural pattern・primitiveの重複IDと既定値をlosslessに省略。候補・Event圧縮と合わせて26,399→21,137 bytes、19.93%削減 / Preserve graph energy and reliability history while losslessly omitting duplicated IDs and defaults from pattern and primitive records; combined reduction is 26,399 to 21,137 bytes, or 19.93% / 保留graph的energy及reliability历史，无损省略pattern及primitive记录中的重复ID与默认值；合计由26,399降至21,137 bytes，减少19.93%
- [Done] 5 seedのG2全Stateでschema v4を評価し、平均134,478→102,287 bytes・23.94%削減、5,000予測・2,250計画・Composition・simulation差分0 / Evaluate schema v4 over five full G2 states: 134,478 to 102,287 mean bytes, 23.94% reduction and zero differences over 5,000 predictions, 2,250 plans, composition and simulation / 在5个完整G2 State上评估schema v4：平均134,478降至102,287 bytes，减少23.94%，5,000次预测、2,250次规划、Composition及simulation差异为0

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

- [Done] G3.1: 3 seed・1k→10k→100k Eventの全9条件でindex版と全走査参照版の全予測field差分0。Event作業量を最小63.49倍、p95を最小20.37倍改善し、Replay windowは全sort参照と一致したまま128件に制限 / Across all nine rows over three seeds and 1k→10k→100k Events, every prediction field matches the full-scan reference; Event work improves by at least 63.49×, p95 by at least 20.37×, and the 128-Event Replay window matches a full sort / 在3个seed及1千→1万→10万Event的全部9个条件中，所有预测字段与全扫描参考一致；Event工作量至少改善63.49倍，p95至少改善20.37倍，128件Replay窗口与全排序一致
- [Done] G3.2計測基盤: 機構別切替・A→B→Aランナーと4指標・A1固定条件からのmerge再提案・独立development検証を必須とする実験用採用継承 / Add mechanism switches, an A→B→A metric runner, merge reproposal from frozen A1 scopes and opt-in validation inheritance gated by independent development probes / 已添加机制开关、A→B→A指标运行器、基于冻结A1条件的合并重提议，以及须通过独立development探针的可选验证继承
- [Done] G3.2開発preflight: 5 seed×7条件を完走したが、採用済みmerge・休眠・実行済みPrimitive分裂が全行0で機構機会gateは不合格 / Complete a 5-seed, 7-arm development preflight; the opportunity gate fails because adopted merges, dormancy and executed Primitive splits are zero in every row / 完成5个seed、7条件的开发预检；全部行中已采纳合并、休眠及已执行原语分裂均为零，机制机会门槛未通过
- [Done] G3.2生命周期pilot: 独立probe評価で特化親2件とmergeを採用し、5 seedで休眠on/offの作動差を確認。drift効果は未測定 / Probe-backed adoption of two specialized parents and their merge yields a dormancy on/off contrast in five seeds; drift effects remain unmeasured / 独立探针评估采纳两个特化父候选及其合并，5个seed确认休眠开关的操作差异；漂移效果未测
- [Done] G3.2分裂opportunity: 16 Eventの独立Replay fixtureで分裂on/offの実行差を確認。予測効果は未測定 / A separate 16-Event Replay fixture exercises the split on/off execution path; prediction effects remain unmeasured / 独立的16 Event重放fixture验证分裂开关的执行差异；预测效果未测
- [Done] G3.2候補採用後preflight: A1ではmerge・休眠が作動するが、Bの1～4観測で採用/休眠が失効し、A2終了時の機構gateは不合格。採用ラベル予算も条件間で不一致 / A candidate-primed A→B→A preflight activates merge/dormancy at A1, but validation/dormancy disappear within 1–4 B observations; the final opportunity gate fails and adoption-label budgets differ across arms / 候选采纳后的A→B→A预检在A1触发合并与休眠，但B的1至4次观测使采纳/休眠失效；最终机制门槛未通过，条件间采纳标签预算也不同
- [Done] G3.2失効診断: FullはB後にmerge提案自体が消え、A2でも戻らない。No splitは提案が残るが検証済み採用は戻らない / Full loses the merge proposal itself during B and does not recover it in A2; No split retains a proposal but never regains validated adoption / Full在B阶段失去合并提案且A2未恢复；No split保留提案但未恢复已验证的采纳
- [Done] G3.2追加診断: No split/Merge onlyはA2後に1,200ラベルでmergeを再採用。Fullは提案の再出現に追加25～53 A2 Eventを要した。復帰直後の保持効果ではない / After A2, No split/Merge only re-adopt a merge with 1,200 labels; Full needs 25–53 extra A2 Events just to rediscover a proposal. This is not immediate-return retention / A2结束后No split/Merge only用1,200个标签重新采纳合并；Full仅重新发现提案就需额外25至53个A2 Event。这不代表刚返回时的知识保留
- [Done] G3.2オンライン検証計測: drift runnerに検証callback、A/B共通ラベル上限、消費ID・判断数の記録、採点probeの学習/採用証拠への混入防止を実装。採用効果は未評価 / The drift runner now supports online validation callbacks, a shared A/B label cap, consumed-ID and decision accounting, and guards against scoring-probe leakage into learning or adoption evidence; no adoption effect is established / 漂移运行器现支持在线验证回调、A/B共用标签上限、消耗ID和决策计数，并防止评分探针混入学习或采纳证据；尚未证明采纳效果
- [Done] G3.2オンライン採用の開発pilot: 5 seed×7条件でA2の1/6/12 Event後に最大3,600ラベルの検証を試した。No split/Merge onlyはmergeを再採用したが、Fullは提案不在で0ラベル、全条件でPrimitive分裂0のため機構機会gateは不合格 / A five-seed, seven-arm online adoption pilot tries validation after A2 Events 1/6/12 with a 3,600-label cap. No split and Merge only re-adopt merges, while Full has no proposal and consumes zero labels; all arms have zero Primitive splits, so the opportunity gate fails / 五个seed、七组条件的在线采纳试验在A2第1/6/12个Event后尝试验证，标签上限为3,600。No split和Merge only重新采纳合并，Full因无提案消耗零标签；全部条件的原语分裂均为零，机制机会门槛未通过
- [Done] G3.2分裂drift小世界: 5 seedのA→B→Aでsplit onのみPrimitive分裂を1～2件実行したが、両条件のB/A2回復Event数とReplay再適用量は一致。発火は確認、効果は未確認 / In a five-seed A→B→A split micro-world, split-on executes one or two Primitive splits per seed, yet B/A2 recovery Events and Replay reapplications match split-off. Execution is confirmed; benefit is not / 在五个seed的A→B→A分裂小环境中，仅开启分裂的条件每seed执行1至2次原语分裂，但B/A2恢复Event数和Replay重新应用量与关闭条件相同；确认了触发，尚未确认收益
- [Done] G3.2文脈別drift開発診断: indoorだけ変えoutdoorを保持するとA2入口の旧A精度は0.5残るが、5 seedすべてで分裂0。phaseを24/48 Eventに伸ばしても発火せず、累積Replay scoreが局所誤差を隠す可能性を特定 / In contextual drift, changing only indoor preserves 0.5 immediate A2 accuracy, but executes zero splits in all five seeds, including exploratory 24/48-Event phases; cumulative Replay score may mask local errors / 按情境漂移仅改变indoor而保留outdoor时，A2入口旧A准确率为0.5，但五个seed均未分裂；开发阶段延长至24/48 Event仍未触发，累计Replay分数可能掩盖局部错误
- [Done] G3.2局所Replay診断: context別に独立証拠Eventを1回ずつread-only再採点。5 seedすべてでwarmのindoor 2/2件が誤り、outdoor 0/8件が誤りだが、累積Replay scoreは0.737～0.846で全体閾値0.6を上回る / Read-only re-scoring of distinct evidence Events finds 2/2 warm-indoor errors and 0/8 warm-outdoor errors in all five seeds, while cumulative Replay score remains 0.737–0.846 above the global 0.6 threshold / 只读重评各context的独立证据Event：五个seed中warm-indoor均为2/2错误、warm-outdoor均为0/8错误，但累计Replay分数仍为0.737至0.846，高于全局0.6阈值
- [Done] G3.2条件付き分裂提案pilot: 実験用switchで5 seedすべて分裂を発火させたが、保持・B回復は同じでA2回復が1 seedで2 Event悪化し、誤りのないoutdoorにもvariantを生成。既定値には採用しない / An opt-in conditional split proposal fires in all five seeds but leaves retention and B recovery unchanged, delays A2 recovery by two Events in one seed, and creates variants for error-free outdoor context. Keep it disabled by default / 可选的情境式分裂提案在五个seed全部触发，但保留与B恢复不变，一个seed的A2恢复慢两个Event，并为零错误的outdoor建立variant；默认保持关闭
- [Done] G3.2境界readout介入: B終了時のA/B probeとA2終了時のA probeでPrimitive除去は全seed・全条件で予測効果0件変化（Bのscore差0.05）。recent outcome無効化も効果0件（score差0.5）。この小世界の境界予測への寄与は限定的 / Boundary readout interventions change zero predicted effects when Primitives are removed across all seeds/arms (B score shift 0.05); disabling recent outcomes also changes zero effects (score shift 0.5). Their contribution to this world's boundary predictions is limited / 边界读取干预中，移除原语在全部seed和条件下均不改变预测效果（B分数差0.05）；关闭近期结果也不改变效果（分数差0.5）；其对该环境边界预测的作用有限
- [Done] G3.2全phase寄与診断: Bの60更新前予測はPrimitive除去で全条件0件変化。条件付き分裂はA2で2/60件変わり、うちseed 23の誤予測はPrimitive除去で正解となる。未見actor/target probeもPrimitive除去で変化0件（target roleは入力済み） / Across 60 B pre-update predictions per arm, removing Primitives changes none. The contextual split arm has two A2 flips; removing Primitives corrects seed 23's error. Unseen-actor/target probes also have zero flips, with target role supplied / 每组B阶段60次更新前预测中，移除原语均不改变效果；情境式分裂组A2有两次变化，其中seed 23的错误因移除原语而纠正；未见actor/target探针也无变化，但target role由输入提供
- [Done] G3.2役割条件付き具体遷移baseline: 同じEvent・probeで直近観測表と比較。5 seed合計でbaselineはB/A2各55/60の事前更新正解、RISA全体分裂は45/60・46/60、条件付き分裂は45/60・45/60。保持と未見actor/target境界精度は同じ / A last-observed role-conditioned table on identical Events and probes scores 55/60 pre-update in both B/A2 across five seeds, versus 45/60 and 46/60 for RISA global split and 45/60 in both for contextual split. Retention and unseen-actor/target boundary accuracy match / 在相同Event和探针上，最近观察的角色条件化表在五个seed的B/A2更新前均为55/60，RISA全局分裂为45/60与46/60，情境式分裂两阶段均为45/60；保留与未见actor/target边界精度相同
- [Done] G3.2観測ノイズ開発試験: cleanと20%誤ラベルを同じ5 seedで比較。ノイズ下でRISAはA復帰時の保持が4 seedで高いがB終了時の潜在ルール精度は4 seedで0.5に留まる。分裂on/offは予測曲線が一致し因果効果なし / A paired clean/20% observation-noise stress test gives RISA higher A-return retention in four seeds but only 0.5 latent B accuracy in four seeds; split on/off trajectories match, so no causal split benefit is established / 配对的无噪声及20%观测噪声试验中，RISA在四个seed的A返回保留率较高，但四个seed的B潜在规则准确率仅0.5；分裂开关曲线相同，未证实因果收益
- [Done] G3.2保持解釈gate: B終了時に基準精度の95%へ達した場合だけ条件付き保持を報告し、未達seedも生の保持率とともに残す。20%ノイズでは両モデルが同時にB適応したseedは0件 / Add an adaptation-qualified retention audit while keeping raw retention and every failed seed. In the 20% noise pilot, no paired seed reaches the B adaptation gate for both models / 增加B适应达标后的条件性保留审计，同时保留原始保留率和全部失败seed；20%噪声试验中没有两种模型同时达到B适应门槛的配对seed
- [Done] G3.2復帰識別性監査: contextual worldではA/Bの4 probe中2件が完全同一queryで正解だけ逆。B完全適応かつ復帰手掛かりなしの場合、A2入口のA精度上限は0.5。旧知識保存の証明には使えない / An exact-query audit finds two contradictory A/B probes out of four; with perfect B prediction and no return cue, immediate A accuracy cannot exceed 0.5. This fixture cannot establish preserved A knowledge / 完全query审计发现四个A/B探针中两个标签相反；完全预测B且没有返回提示时，A2入口的A准确率不可能超过0.5，不能据此证明保存了A知识
- [Done] G3.2復帰手掛かりcontrol: 同一`regime:A/B`を全方式へ渡すと衝突0件。20%誤ラベル下でRISAと回数集計表はB終了・A復帰とも5/5 seedで精度1.0、分裂on/offの予測は同じ。識別性は改善したが構造機構の利得なし / An observable-cue control removes exact-query conflicts; under 20% label noise, RISA and a role/context count table both reach 1.0 B-exit and A-return accuracy in all five seeds, with no split-on/off prediction difference / 可观察提示对照消除了完全query冲突；20%错误标签下，RISA与角色/情境计数表在五个seed的B结束和A返回准确率均为1.0，分裂开关预测无差异
- [Done] G3.2分裂readout監査: 20%誤ラベルの条件付き分裂armは各seedでB側variantを4件作り、潜在Bルールに反する採用済みvariantが2/1/2/1/0件。Primitive除去はscoreを変えるが予測効果は変えず、分裂重みの安易な増加は危険 / Under 20% label noise, contextual splitting creates four B-scope variants per seed and adopts 2/1/2/1/0 off-rule variants; Primitive removal changes scores but not effects, so weight increases alone are unjustified / 20%错误标签下，情境分裂每个seed产生四个B范围变体，采纳的偏离潜在规则变体数为2/1/2/1/0；移除原语改变分数但不改变预测效果，不能仅提高权重
- [Done] G3.2分裂variantのcontext境界: Primitive score・候補効果・選択結果・説明経路でsplit variantだけ完全context一致とし、一般Primitiveの部分一致は保持。7開発manifestの主要値変更0行 / Require exact context for split variants in scoring, candidate effects, chosen outcomes and supporting paths while retaining generic Primitive partial matching; seven development manifests have zero primary-metric changes / 分裂变体在评分、候选效果、选定结果及证据路径均须完整情境匹配，普通原语仍可部分匹配；七个开发manifest的主要指标无变化
- [Next] G3.2情報量を揃えた世界設計: 上記の負例と直接的な復帰cue controlを残し、手掛かりが履歴キーをそのまま選ばない開発worldを定義。直近表と回数集計表を両方維持し、機構が実行だけでなく予測・保持に寄与する条件を固定後、独立finalで比較 / Retain the negative world and direct-cue control; define a development world whose return cue does not simply select a stored key. Keep both latest and count tables, and freeze an informative mechanism contrast before an independent final comparison / 保留负面环境及直接提示对照，设计返回提示不会直接选中存储键的开发环境；同时保留最近表与计数表，在独立最终评估前固定能让机制实际影响预测和保留的条件
- [Next] G3.2: 開発seedで機構機会とラベル予算を固定した後、同一worldの個別ablationと強いbaselineで回復・保持・局所更新・Replay量を独立評価 / Freeze mechanism opportunities and label budgets on development seeds, then compare one-factor ablations and strong baselines on the same independent drift worlds for recovery, retention, local updates and Replay work / 在开发seed固定机制机会与标签预算后，于相同独立漂移环境中比较单因素消融和强基线的恢复、保留、局部更新及重放工作量
- [Later] G3.3: 1k→10k→100k Eventでingestion、graph更新、候補発見、凝縮、予測、計画、Replay、保存をend-to-end測定。1Mは先行する3規模の結果で判断 / Profile end-to-end ingestion through persistence at 1k, 10k and 100k Events; decide on 1M from those results / 在1千、1万及10万Event下端到端测量摄取至持久化；根据前三种规模决定是否测试100万
- [Later] G3.4: Eventあたり保存量・active構造数・候補数・記述長とqueryあたり探索量の成長曲線を測る / Measure growth curves for bytes, active structures, candidates and description length per Event, and search work per query / 测量每Event的存储量、活跃结构数、候选数及描述长度，以及每query探索量的增长曲线
- [Later] score校正、unknownの区別、状態を含む探索重複判定 / Calibration, unknown states, state-aware search deduplication / 校准、未知状态及考虑状态的搜索去重

日本語: G3.1の予測read modelとReplay選択は採用条件を通過した。合成fixtureは完全な学習・graph構築・候補発見・planner探索を含まないため、それらの100k性能は未評価として残す。G3.2で更新範囲、Replay件数、回復速度と忘却をdrift下で測る。

English: G3.1 prediction read models and Replay selection passed the adoption gate. Full learning, graph construction, candidate discovery and planner search were excluded from the synthetic fixture, so their 100k performance remains unmeasured. G3.2 measures update scope, Replay work, recovery and forgetting under drift.

简体中文: G3.1的预测read model及Replay选择已通过采纳门槛。合成fixture不含完整学习、graph构建、候选发现及planner搜索，因此这些路径的10万规模性能仍未测量。G3.2将在漂移下测量更新范围、Replay工作量、恢复及遗忘。

詳細: [G3.1 Event access scale評価 / Event-access scale evaluation / Event访问规模评估](G3-Scale-Evaluation-2026-09-13.md)

G3.2評価契約: [Drift ablation protocol / 漂移消融評価契約 / 漂移消融评估协议](G3.2-Drift-Protocol.md)。主要指標は`recovery_events`、`retention_after_return`、`adaptation_touch_ratio`、`replay_cost_per_recovery`。G3.3ではtime/bytes/active structures/candidate generation per Eventとplanner expanded nodes per queryを記録する。G3.4ではEvent増加に伴い再利用構造が増え、保存量と探索量の増分が下がり、独立held-out成功率が上がるかを同時に検証する。曲線が比例増加する場合は凝縮仮説を見直す。

G3.2開発preflight: [機構機会監査 / Mechanism opportunity audit / 机制机会审计](G3.2-Drift-Preflight-2026-09-16.md)。35行すべてで採用済みmergeと休眠が0のため、独立finalへ進めず生命周期の作動機会を先に修正する。

追加の開発診断: [オンライン採用 / Online adoption / 在线采纳](G3.2-Online-Validation-Development-2026-09-18.md)、[Primitive分裂 / Primitive split / 原语分裂](G3.2-Split-Drift-Opportunity-2026-09-18.md)、[文脈別drift / Contextual drift / 按情境漂移](G3.2-Contextual-Drift-2026-09-18.md)、[条件付き分裂提案 / Conditional split proposal / 条件式分裂提案](G3.2-Contextual-Split-Proposal-2026-09-18.md)、[全phase予測寄与 / Phase-wide readout attribution / 全阶段预测贡献](G3.2-Readout-Attribution-2026-09-18.md)、[役割条件付きbaseline / Grounded role baseline / 角色条件化基线](G3.2-Grounded-Role-Baseline-2026-09-22.md)、[観測ノイズ / Observation noise / 观测噪声](G3.2-Observation-Noise-Development-2026-09-22.md)、[復帰手掛かり / Observable return cue / 可观察返回提示](G3.2-Observable-Return-Cue-2026-09-22.md)、[分裂readout / Split readout / 分裂读取](G3.2-Split-Readout-Audit-2026-09-22.md)。機構が作動しても回復効果がない場合と、提案消失・局所誤差の希釈により機会がない場合を別々に記録する。

G3.2 contract: the same four primary metrics separate recovery, retention, local rewrite scope and Replay work. G3.3 measures time, bytes, active structures and candidate generation per Event plus planner expanded nodes per query. G3.4 tests whether reusable structure grows while marginal storage/search work falls and independent held-out success rises; proportional growth triggers a reconsideration of condensation.

G3.2协议：四项主要指标分别衡量恢复、保留、局部改写范围及重放工作量。G3.3测量每Event的时间、字节、活跃结构和候选生成，以及每query的规划器扩展节点。G3.4同时检验可复用结构是否增加、边际存储与搜索成本是否下降、独立留出成功率是否提高；若结构按Event数量成比例增长，应重新审视凝聚假设。

## G4 — Recursive concept formation / 再帰的概念形成 / 递归概念形成

- [Later] G4.1 二世代候補を既存構造から発見し、祖先証拠と重ならない独立held-outで追加利得を示す / Discover second-generation candidates from learned structures and demonstrate gain on independent held-out episodes disjoint from ancestral evidence / 从已学习结构发现第二代候选，并在与祖先证据不重叠的独立留出回合中证明增益
- [Later] G4.2 Event→Primitive→Schema→Macro→抽象relationの3～4段階が人手ラベルなしで形成されるか検証 / Test whether three to four levels of Event-to-Primitive-to-Schema-to-Macro-to-abstract-relation hierarchy arise without supplied labels / 检验Event到原语、Schema、宏及抽象关系的三至四层层级能否在无人为标签下形成
- [Later] G4.3 系譜証拠と分離した新しい小世界へ構造を転移し、モデル品質とplanner品質を四条件で分離 / Transfer structure to a new small world with disjoint lineage evidence and separate model from planner quality in four cells / 将结构迁移到谱系证据互不重叠的新小世界，并以四条件区分模型与规划器质量

日本語: 「経験から再利用可能構造が自己凝縮する」を中心仮説とし、保存量・探索量・未知問題成功率を同時に問う。独立held-outの改善がなければ二世代発見を知能増幅と呼ばない。自然言語・画像等の知覚adapterはG4の証拠を確認してから接続する。

English: The central hypothesis is self-condensation of reusable structure from experience, judged jointly by storage, search and unseen-problem success. Do not call second-generation discovery intelligence compounding without independent held-out gains. Connect language and image perception adapters only after the G4 evidence is established.

简体中文: 核心假设是经验自行凝聚为可复用结构，需同时考察存储量、搜索量与未知问题成功率。若没有独立留出增益，不把第二代发现称为智能增益；语言与图像感知适配器应在G4证据成立后接入。

## G5 — Adaptive discovery policy from search history / 探索履歴からの発見方針学習 / 基于探索历史的发现策略学习

[Later] Research reference: Zheng et al., [*Dream-RSI: Recursive Self-Improvement through Evolving Worlds* (PDF)](https://github.com/zhengkid/Dream-RSI/blob/main/papers/Dream-RSI.pdf), [arXiv HTML](https://arxiv.org/html/2609.14858). Dream-RSI replays **recorded discovery trees** to compare exploration policies over already observed branches, then deploys a selected policy to collect new trees. This is a meta-exploration idea; it does not demonstrate RISA's concept condensation or A→B→A adaptation.

| Status | 日本語 | English | 简体中文 |
| --- | --- | --- | --- |
| [Later] G5.1 | 候補発見の分岐、親候補、選択順、予算、評価結果、停止理由を探索木として記録。RISAのEvent Replayとは別に扱う | Log discovery branches, parent candidates, selection order, budgets, evaluation outcomes and stopping reasons as search trees; keep this distinct from Event Replay | 将候选发现的分支、父候选、选择顺序、预算、评估结果与停止原因记录为搜索树，并与Event重放区分 |
| [Later] G5.2 | 記録済み枝だけを厳密に再生し、未観測枝では結果を推測せずcoverage不足を報告。枝順・並列数・停止規則を同じ予算で比較 | Replay only recorded branches; report coverage gaps instead of inventing outcomes for unseen branches. Compare branch order, parallelism and stopping rules under matched budgets | 只重放已记录分支；对未观察分支报告覆盖缺口，不推测结果。在相同预算下比较分支顺序、并行度与停止规则 |
| [Later] G5.3 | 固定探索方針、ランダム/単純heuristic、履歴要約による誘導を対照に、学習した方針を独立の新世界へオンライン展開 | Compare with fixed, random/simple heuristic and history-summary policies, then deploy the selected policy online in independent new worlds | 与固定、随机/简单启发式及历史摘要引导策略比较，再于独立新世界中在线部署选中策略 |

日本語: G3.2～G4で候補形成と効果・費用を確認してから着手する。評価器と候補生成器を固定し、方針だけを変える。主指標は独立世界でのheld-out成功率、必要な候補評価回数、wall time、保存量、探索coverageとする。オフライン履歴上で現行方針以上という結果は、その履歴への適合を示すだけで、未知枝や新世界での改善保証とはみなさない。候補系譜、方針開発用の木、最終評価用の木を分離し、同一計算予算で複数seedの区間を報告する。G5の採用は、独立オンライン評価で成功率を維持または改善しつつ実探索費用を下げ、G4の構造凝縮・誤一般化の基準を悪化させない場合に限る。

English: Start after G3.2–G4 establish candidate formation, benefit and cost. Hold the candidate generator and evaluator fixed while changing only the exploration policy. Primary measures are held-out success in new worlds, candidate evaluations, wall time, storage and search coverage. A policy that wins on its replay pool is only better on that pool; replay cannot validate unseen branches or guarantee online improvement. Separate candidate lineage, policy-development trees and final-evaluation trees, and report intervals across matched seeds and budgets. Adopt the policy only if independent online evaluation maintains or improves success while reducing real exploration cost without worsening G4 condensation or false generalization.

简体中文: 在G3.2至G4验证候选形成、收益与成本后再开展。固定候选生成器和评估器，仅改变探索策略。主要指标为独立新世界的留出成功率、候选评估次数、运行时间、存储量和搜索覆盖率。历史重放池上的优势只适用于该池，不能验证未观察分支或保证在线提升。分离候选谱系、策略开发树及最终评估树，在匹配的seed与预算下报告区间。只有独立在线评估在维持或提高成功率的同时降低实际探索成本，且不恶化G4的结构凝聚与错误泛化，才采纳该策略。

## Optional applications and execution research / 用途と実行層の追加研究 / 应用与执行层研究

- [Later] 狭い業務手順・資源管理の外部ログでshadow評価 / Shadow evaluation on bounded workflow/resource logs / 在有限流程与资源日志上影子评估
- [Later] Threat-Aware Ordering Repair。G1で探索失敗が主要因の場合に前倒し再判断 / Ordering repair, reconsider earlier only if G1 isolates search as the bottleneck / 若G1确认搜索为瓶颈再考虑提前顺序修复
- [Later] Canopy、階層credit、SNN、スペクトル診断 / Canopy, hierarchical credit, SNN, spectral probes / Canopy、层级信用、SNN与谱诊断
- [Later] Neural adapter、多言語知覚、multimodal、SARA接続 / Neural adapters, multilingual perception, multimodal and SARA integration / 神经适配器、多语言感知、多模态与SARA集成
- [Later] SARA双方向接続の独立評価: 反復パターン→出典付きEvent候補→RISA構造と、検証済み構造→任意のrouting priorを別々にablationし、単体・上りのみ・下りのみ・双方向を同じ予算で比較する。時間スケール分担は測定する / Independently test a SARA bridge: repeated patterns to provenance-bearing Event candidates to RISA structure, and validated structure back as an optional routing prior. Ablate each direction and compare standalone, one-way and two-way systems under matched budgets; measure rather than assume timescale boundaries / 独立评估SARA双向接口：重复模式经带来源的Event候选进入RISA结构，已验证结构作为可选路由先验返回；分别消融两个方向，在相同预算下比较单体、单向与双向系统，并测量而非预设时间尺度边界
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
