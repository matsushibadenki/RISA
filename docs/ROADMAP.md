# RISA Roadmap / RISA ロードマップ / RISA 路线图

Updated: 2026-11-24. [Design assessment / 設計評価 / 设计评估](RISA-Structural-AI-Assessment-2026-09-05.md)

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

## Latest implementation priority / 最新の実装優先順 / 最新实施优先级

- 🟢 [Done] [接地訂正の依存pilot / Grounding correction pilot / 接地修改依赖试验](G3.4-Grounding-Correction-2026-11-24.md): 明示 `GroundingCorrectionTracker` を実装。局所Event参照96→16・256→64、局所CPU比0.253–0.336。独立state・6 process/3 hash seed・36軌跡で32,256完全結果照合、各段階の保存/復元一致。役割対/identityを保持し、影響先の校正を失効。通常ingestionは変更しない。 / Explicit scoped cache repair preserves joint bindings and clears affected calibration; 32,256 complete comparisons and stepwise persistence match. Normal ingestion is unchanged. / 显式局部缓存修复保持联合绑定并清除受影响校准，32,256完整比较及逐步保存恢复一致，常规摄入不变。
- 🟢 [Done] 生成器source digest・Python/RNG版・seed・snapshot digest・項目の旧値/新値を記録するmanifestと、別stateへの逐次再生照合を実装。総費用に編集/manifest準備を含む。 / Record source/runtime/RNG versions, seeds, snapshot digest and explicit old/new edits, with separate-state replay; charge preparation costs. / 记录源码/运行时/RNG版本、seed、snapshot摘要及旧新值，独立state重放并计入准备成本。
- 🟢 [Done] 負の結果も採用判断へ反映: 総CPU比0.973–1.042、fallback CPU比1.142–1.353。依存保持量41,063–96,605 bytesはlookup予算外。全体高速化は未確認なので明示APIに限定。 / Total CPU ratios0.973–1.042 and fallback ratios1.142–1.353 do not establish an overall win; dependency metadata adds41,063–96,605 bytes outside the lookup cap. Keep opt-in. / 总CPU比0.973–1.042、fallback比1.142–1.353，依赖额外占41,063–96,605 bytes，尚无整体收益，仅显式启用。
- 🟠 [Next] **訂正密度とquery回数に応じた費用回収条件**。全走査・全再構築・依存先再構築の総費用を比較し、全支持集合の検査・fallback時の依存再取得を削減する条件を検証する。明示mutation世代管理、逆参照の追加/削除、候補変化、peakメモリ測定は未完了。未報告の直接変更を検出したことにはしない。 / Prioritize density/query-count payback and reducing support validation/fallback metadata costs. Mutation generations, reverse-edge maintenance, candidate changes and peak memory remain open; unreported mutations are not detected. / 优先验证修改密度/查询次数回本及降低支持检查/fallback元数据成本；变更版本、反向边维护、候选变化和峰值内存尚未完成，不宣称检测未报告修改。
- 🔴 [Later] 学習状態全体の訂正やcandidate/Replay局所化へは未拡張。G3.2の負の結果・G3.4の独立評価gateを維持。 / Learned-world correction and candidate/Replay localization remain later; preserve G3.2 negatives and G3.4 independent gates. / 学习状态整体修正和候选/Replay局部化留待后续，保留G3.2负结果及G3.4独立门槛。

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
- 🟢 [Done] append差分更新と3 arm比較を下記で実装・評価。役割多様化の費用評価は下記で完了、自動選択は未完了 / Append maintenance and diverse-role costs are evaluated below; automatic selection remains open / 下述已完成差分维护及多角色成本评估；自动选择仍未完成。

### Incremental grounding maintenance — 2026-10-11

- 🟢 [Done] [差分接地index](G3.4-Incremental-Grounding-2026-10-11.md): 明示incremental modeで追加支持証拠のみ反映。訂正/欠落証拠到着は無効化、Primitive置換/splitは再構築fallback。既定と保存schemaは維持 / Add explicit incremental support maintenance with invalidation/rebuild fallback; preserve defaults and schema / 显式差分维护新增支持证据，修改/缺失证据到达失效，Primitive替换/split重建fallback，保持默认与schema。
- 🟢 [Done] 3 seed×2世界×3反復、1/3/24 Event更新×1/40 queryで全走査/全再構築/差分を比較。97,416完全結果比較、各更新の保存内容、108軌跡の実保存/復元が一致 / Three-arm cyclic-order comparison preserves97,416 complete results, every serialized update and108 actual save/reload trajectories / 三arm循环顺序比较中97,416完整结果、每更新序列化及108轨迹实保存/恢复一致。
- 🟢 [Done] 96 Event到達までの維持読み出し4,578/1,554/240→96。1 Event＋1 queryの合計時間は全再構築比4.6%短縮、全走査比1.0%悪化。1 Event＋40 queryは全走査比28.7%短縮、24 Event＋40 queryは全再構築比2.3%悪化も保持 / Reduce maintenance reads to96; retain both timing gains and regressions, including4.6%gain against rebuild but1.0%loss against scan at one Event/one query / 维护读取降至96；保留改善与恶化，包括单Event单query较重建快4.6%但较扫描慢1.0%。
- 🟢 [Done] 24種類の役割対、identity訂正、重複投入、実context split、置換、欠落証拠到着、復元を回帰検証。全テスト293件成功 / Regress24 joint role types, equality changes, duplicate ingestion, real split, replacement, missing evidence and reload;293 tests pass / 回归24种联合角色、identity修改、重复输入、真实split、替换、缺失证据及恢复；293测试通过。
- 🟢 [Done] 固有witness増加時のコピー/並べ直しを下記で測定・改善。3 query密度で方式選択条件を比較 / Measure and remove append copying/sorting below; compare selection conditions at three query densities / 下述测量并消除追加复制/排序，以三种query密度比较选择条件。
- 🔴 [Later] 差分modeの既定有効化は上記検証後。現在はopt-in、候補利得・凝縮の未達も維持 / Consider default incremental mode only after broader validation; keep opt-in and unproven candidate/condensation claims / 广泛验证后再考虑默认差分模式，当前保持opt-in及候选优势/凝聚未证明。

### Grounding diversity and selection — 2026-10-11

- 🟢 [Done] [役割・witness多様化](G3.4-Grounding-Diversity-2026-10-11.md): 8/64/256種類×1/4/16 query×2役割分布×4反復、全走査/全再構築/旧差分/改善差分を比較。116,352完全結果、1,152更新内容、288実保存/復元が一致 / Compare four arms over72 trajectories;116,352 complete results,1,152 serialized updates and288 actual save/reload checks match / 四方式72轨迹，116,352完整结果、1,152更新内容及288实保存/恢复一致。
- 🟢 [Done] appendの集合コピー・全並べ直しを除去。256種類の16回維持を約3.4–5.1ms→0.18–0.27msへ削減。役割対/identity、訂正fallback、保存schemaを維持 / Remove append copying/sorting, reducing maintenance at256 types from3.4–5.1ms to0.18–0.27ms; preserve joint witnesses and persistence / 移除追加复制/排序，256种的维护由3.4–5.1ms降至0.18–0.27ms，保持联合witness及保存约定。
- 🟢 [Done] 少数queryでは全走査、安定appendでは差分、無効化後は走査または費用回収可能な全再構築という費用条件を整理。8種類1 queryは走査優位。合計時間の旧差分比悪化も記録し、自動閾値は導入しない / Document cost-based selection including scan wins and incremental regressions; no automatic threshold / 整理基于成本的选择条件，保留扫描优势与差分总时间退化，不设自动阈值。
- 🟢 [Done] 同一actorへのwitness集中を役割対/identity lookupで改善し、複数役割・wildcard・構築/更新/メモリを下記で比較。訂正後query密度のpolicy検証は引き続き未完了 / Implement joint lookup and evaluate multi-role/wildcard/build/update/memory costs below; post-correction density policy remains open / 下述已实现联合lookup并评估多角色、通配、构建/更新/内存；修改后query密度policy仍未完成。
- 🔴 [Later] 独立world・複数process/hash順序で選択policyを交差検証し、十分な根拠が得られてから自動切替・既定変更を検討 / Cross-validate policy on independent worlds and process/hash orders before automatic switching or default changes / 以独立world与多process/hash顺序交叉验证后再考虑自动切换或默认变更。
- 🟢 [Done] 全テスト296件成功、差分形式検査成功 / All296 tests and diff whitespace checks pass / 全部296项测试与diff格式检查通过。

### Joint role/identity grounding lookup — 2026-10-11

- 🟢 [Done] [接地検索索引](G3.4-Grounding-Lookup-2026-10-11.md): 同じwitness内のactor/target役割対とidentity許可を索引化。複数役割、型なし混在、target/identity wildcardを保持し、新規witnessのみ差分追加 / Index within-witness role pairs and identity masks, preserving multi-role and wildcard semantics with append maintenance / 索引同一witness内角色对和identity许可，保持多角色及通配语义，差分追加。
- 🟢 [Done] 8/64/256種類×各側1/4役割×3反復で全走査/旧線形/新lookupを比較。完全結果9,504ケース、144更新内容、54実保存/復元で不一致0 / Compare18 trajectories;9,504 complete-result cases,144 serialized updates and54 actual save/reload checks match / 比较18轨迹，9,504完整结果、144更新内容及54实保存/恢复均一致。
- 🟢 [Done] 256種類のquery時間を旧線形比59.2–68.3%短縮。cacheオブジェクト推定量は11.1–68.5%増、4役割で構築2.564→3.248ms・8回更新0.153→0.186ms。小規模での総時間悪化も記録。保存増分0 bytes、既定の全走査を維持 / Reduce query time59.2–68.3% at256 types, recording11.1–68.5% memory growth, build/update overhead and small-case regressions; zero persisted overhead and scan remains default / 256种query减少59.2–68.3%，记录内存增加11.1–68.5%、构建/更新成本和小规模退化；保存增加0 bytes，默认仍扫描。
- 🟢 [Done] Primitive単位のlookup辞書予算と線形fallbackを下記で実装。広い役割・訂正後query密度の比較を追加 / Implement per-primitive lookup-container budget and exact linear fallback below; add wide-role/post-correction comparisons / 下述实现每Primitive的lookup字典预算及精确线性fallback，添加多角色与修改后query比较。
- 🔴 [Later] 自動切替・既定変更は、複数process/hash順序と上記予算policyの交差検証後 / Consider automatic switching/default changes after cross-validation over processes/hash orders and memory policies / 多process/hash顺序与内存policy交叉验证后再考虑自动切换及默认变更。
- 🟢 [Done] 全テスト299件成功。3,840照合組合せ、同一actorを含む480完全結果ケース、既存の訂正/split/欠落証拠回帰を検証 / All299 tests pass, including3,840 matcher combinations,480 complete-result cases with a shared actor, and correction/split/missing-evidence regressions / 全299测试通过，覆盖3,840匹配组合、含同一actor的480完整结果及修改/split/缺失证据回归。

### Explicit lookup budget — 2026-10-12

- 🟢 [Done] [予算付き接地索引](G3.4-Grounding-Budget-2026-10-12.md): `lookup_budget_bytes`でPrimitiveごとの追加辞書コンテナを制限。超過時は役割対/identityを保つ線形witness検索へ戻し、明示再構築まで維持 / Bound extra dictionary containers per primitive with exact linear fallback until rebuilding / 限制每Primitive额外字典容器，超限精确线性fallback并保持至重建。
- 🟢 [Done] 予算0・上限ちょうど・1 byte不足・append超過・identity訂正後の引継ぎを検証。保存schemaと既定全走査を維持。load後の予算は再指定 / Validate zero/exact/one-byte-short budgets, append overflow and correction inheritance; preserve schema/default scan and explicitly reselect budget after load / 验证零/恰好/差1 byte预算、追加超限及修改后继承，保持schema和默认扫描，加载后重新指定。
- 🟢 [Done] 全Primitive合計lookup予算と複数process/hash順序の混在比較を下記で実装・検証。独立した実worldの費用回収は未完了 / Implement aggregate lookup budgets and multi-process/hash mixed evaluation below; independent real-world amortization remains open / 下述已实现总lookup预算及多process/hash混合评估，独立真实world成本回收仍未完成。
- 🔴 [Later] 速度による自動policy選択・既定変更は上記交差検証後 / Defer speed-based automatic policy/default changes until cross-validation / 交叉验证后再考虑基于速度的自动policy及默认变更。
- 🟢 [Done] 48条件、20,736完全結果・240保存用checkpoint・192実保存/復元で不一致0。64役割のcache推定量を無制限lookup比91.4–92.9%削減。訂正直後1 queryは走査有利、16 queryは予算付き/線形が構築費を回収。今回は全8KiB条件がfallback / Verify48 trajectories and exact results/persistence; reduce64-role cache91.4–92.9%, retain scan advantage for one cold query and amortization at16; all8KiB entries fall back / 48轨迹结果及保存一致，64角色cache减少91.4–92.9%；冷单query扫描有利，16次可回收构建费，本次8KiB全部fallback。
- 🟢 [Done] 全302テスト成功。独立/結合worldの160完全結果比較、予算境界・訂正・wildcard fallbackを検証 / All302 tests pass, including160 compositional comparisons plus budget/correction/wildcard regressions / 全302测试通过，含160组合结果比较及预算/修改/通配回归。

### Aggregate lookup budget and mixed execution — 2026-10-12

- 🟢 [Done] [全Primitive合計予算](G3.4-Grounding-Total-Budget-2026-10-12.md): `total_lookup_budget_bytes`で全lookup辞書コンテナ合計を制限。Primitive別上限も併用し、差分残高管理、超過解放、新規Primitiveへの再利用、無効化後の引継ぎを実装。元証拠・RSS・一時ピークは対象外 / Add aggregate and per-primitive container caps with incremental accounting, release/reuse and invalidation inheritance; exclude source evidence/RSS/transient peaks / 实现总量及单Primitive容器上限，差分计量、释放复用及失效继承，不限制源证据/RSS/临时峰值。
- 🟢 [Done] 12個の別process、hash seed0/1/42各4反復、2種類のquery集中先で比較。2 lookup＋2線形の混在を維持し、6,880/8,192 bytes。16,128完全結果ケース・72保存用checkpoint・96実保存/復元、process間の結果digest/保存SHA256/割当が一致 / Validate12 fresh processes and24 trajectories; mixed2+2 allocation uses6,880/8,192 bytes;16,128 complete cases,72 serialized checkpoints and96 save/reload checks match, including cross-process digests/allocations / 12个独立process、24轨迹保持2+2混合，使用6,880/8,192 bytes，16,128完整结果、72序列化及96保存/恢复一致，跨process digest与分配一致。
- 🟢 [Done] lookup集中時は線形index比query10.1%短縮、cache推定量は無制限比48.0%減（線形比7.4%増）。線形集中時の検索量削減はなく、無制限lookupの方が速い点も記録 / Record10.1% query gain when lookup-hot and48.0% less cache than unlimited (7.4% above linear); no structural gain on linear-hot and unlimited remains faster there / lookup集中query改善10.1%，cache较无限减少48.0%但较线性增加7.4%；线性集中无结构收益且无限更快。
- 🟢 [Done] 全305テスト成功。合計残高の実辞書サイズ一致、予算境界、二重上限、順序変更、append解放/再利用、重複、訂正/置換、保存/復元を検証 / All305 tests pass including exact container accounting, boundaries, combined caps, ordering, release/reuse, duplicates, corrections/replacements and persistence / 全305测试通过，覆盖实际字典计量、边界、双上限、顺序、释放复用、重复、修改替换及保存。
- 🟢 [Done] query頻度/辞書費用による割当・再昇格を下記で実装し、同予算ID順と固定/移動/急変の人工fixtureで比較。実worldの費用回収は未検証 / Implement frequency/cost allocation and promotion below with equal-budget stationary/shifting/rapid synthetic comparisons; real-world payback remains unverified / 下述实现频率/成本分配及升级，以同预算固定/迁移/急变合成实验比较，真实world成本回收未验证。
- 🔴 [Later] 自動policy・既定変更は独立worldでの検証後。今回の合計上限はcurrent indexの保持コンテナに限定 / Defer automatic policy/default changes until independent-world validation; cap currently applies only to retained containers of the current index / 独立world验证后再考虑自动policy及默认变更，当前仅限制现有index保留容器。

### Query-frequency allocation and promotion — 2026-10-12

- 🟢 [Done] [query頻度による割当](G3.4-Grounding-Frequency-2026-10-12.md): `allocation_policy='frequency'`と明示的な`rebalance_primitive_grounding`を追加。直近actor接地参照数/辞書bytesで予算内に再配置し、降格・再昇格・区間カウントリセットを実装 / Add explicit recent-access/byte rebalancing, demotion/promotion and window reset / 添加显式最近访问/bytes重分配、降级升级及区间计数重置。
- 🟢 [Done] 辞書費用を上限付き一時構築で測定・キャッシュ。appendで費用見積りを失効し、訂正/置換による再構築で履歴をリセット。費用調査・再配置・毎query計数も比較費用に含める / Cache bounded cost probes, invalidate estimates on append and reset history on rebuilding; include profiling/probing/reallocation costs / 缓存预算内成本探测，追加失效估算，重建重置历史，计入计数/探测/重分配成本。
- 🟢 [Done] 最小保持区間と連続確認を下記で実装し、3 query密度で比較。時間に基づく費用回収判定と独立した実worldは未完了 / Implement residency and consecutive confirmation below and compare three densities; time-based payback and independent real workloads remain open / 下述实现最短保持及连续确认，比较三种密度；基于时间的回收判断与独立真实负载仍未完成。
- 🔴 [Later] 自動の区間長選択・既定policy変更は上記検証後。現在は明示opt-in、既定ID順 / Defer automatic window/default-policy choices until validation; keep frequency opt-in and ID order default / 验证后再考虑自动区间和默认policy，当前显式启用，默认ID顺序。
- 🟢 [Done] 各方式12,000 bytes、6 process・3 hash seed、固定/移動/急変の18軌跡を比較。各runの5,184完全結果・108保存用checkpoint・36実保存/復元が一致し、process間の結果digest・保存SHA256・割当履歴も一致 / Compare18 equal-budget trajectories across6 processes/3 seeds;5,184 complete cases,108 serialized checkpoints and36 save/reload checks per run match, including cross-process digests/traces / 同预算18轨迹、6 process/3 seed，每run5,184完整结果、108序列化及36保存/恢复一致，跨process digest与分配历史一致。
- 🟢 [Done] 再配置込み総CPU中央値は固定22.0%減、移動5.8%減、急変27.8%増。初回wall-onlyのばらつき・逆転結果も保持。普遍的優位は主張しない / Total CPU medians including reallocation improve22.0%/5.8% for stationary/shifting and regress27.8% for rapid; retain noisy first wall-only results without universal superiority claims / 含重分配CPU中位数固定/迁移减少22.0%/5.8%，急变增加27.8%，保留首轮wall-only波动/反转，不声称普遍优势。
- 🟢 [Done] 全308テスト成功。頻度/費用優先、降格・再昇格、費用キャッシュ失効、訂正・無効化・復元、予算0と不正policyを回帰検証 / All308 tests pass across frequency/cost ranking, demotion/re-promotion, cost invalidation, corrections/reload and invalid/zero-budget settings / 全308测试通过，覆盖频率/成本排序、降级再升级、成本失效、修改恢复及非法/零预算。


### Stable lookup allocation — 2026-10-15

- 🟢 [Done] [再配置の安定化](G3.4-Grounding-Stability-2026-10-15.md): 明示`confirmation_windows`と`minimum_residency_windows`を追加。空区間・追加・訂正の履歴処理を検証。既定1/0は即時頻度方式 / Add explicit confirmation/residency controls with empty-window, append and correction history handling; defaults1/0 retain immediate frequency / 添加显式确认/保持控制，验证空区间、追加及修改历史处理，默认1/0保持即时频率。
- 🟢 [Done] 下記で未参照・費用未知の冷候補調査を保留し、独立/結合の開発worldで実composer参照分布と費用回収を測定。運用ログでの検証は未完了 / Defer unknown-cost unaccessed probes below and measure real composer accesses/payback on development worlds; production-trace validation remains open / 下述延后未访问且成本未知的探测，在开发world测量实际composer访问/回收；生产日志验证仍未完成。
- 🔴 [Later] 自動窓幅・policy選択と既定変更は上記検証後 / Defer automatic windows/policy/default changes until validation / 验证后再考虑自动区间/policy及默认变更。
- 🟢 [Done] 全311テスト成功 / All311 tests pass / 全部311测试通过。
- 🟢 [Done] 同予算4方式×3 query密度、12 process/3 hash seed、108軌跡を比較。38,880完全結果・648保存用checkpoint・432実保存/復元、process間の割当/結果digest/保存SHA256が一致 / Compare108 trajectories across four modes/three densities/12 processes;38,880 complete cases,648 serialized checkpoints and432 save/reloads match, including cross-process traces/digests / 四方式三密度12 process共108轨迹，38,880完整结果、648序列化及432保存/恢复一致，跨process轨迹/digest一致。
- 🟢 [Done] 急変時の連続確認で再昇格9→0、総CPUは即時頻度比12.9–15.6%減。ただしID比5.1–10.8%増、256 query固定集中は即時頻度比23.9%増。改善と遅延の双方を記録し明示opt-inを維持 / Confirmation reduces rapid promotions9→0 and CPU12.9–15.6% versus frequency, yet costs5.1–10.8% more than ID and23.9% more than frequency on stationary256; preserve explicit opt-in / 确认使急变升级9→0，CPU较频率减少12.9–15.6%，但较ID增加5.1–10.8%、固定256较频率增加23.9%；保持显式启用。


### Cold candidate probes and observed payback — 2026-10-15

- 🟢 [Done] [冷候補調査と費用回収](G3.4-Grounding-Payback-2026-10-15.md): 未参照・費用未知の線形候補を保留し、後続参照で調査・昇格可能。`probe_cold_candidates=True`で旧方式を再現 / Defer unknown-cost unaccessed linear candidates while permitting later probes/promotions; retain explicit eager baseline / 延后未访问且成本未知的线性候选，后续可探测升级，显式保留旧方式。
- 🟢 [Done] 実composerの接地参照数を採取。query短縮Sと維持増分Cを対応processごとに分離し、S>Cの回収判定と事後損益分岐を記録。将来予測・自動閾値ではない / Record actual composer accesses and paired query savings S/extra maintenance C, observed S>C recovery and retrospective break-even; no prediction/automatic threshold / 记录实际composer访问，逐配对process分离节省S/额外维护C，记录S>C回收及事后盈亏平衡，不做预测/自动阈值。
- 🟢 [Done] 下記で過去照合例から線形/lookup単価を計測し、計測・構築費を含む候補利益による明示配分を実装・比較。運用評価と自動化は継続課題 / Measure past-sample unit costs and compare explicit candidate-benefit allocation including calibration/build costs below; operational evaluation/automation remain open / 下述计测历史照合单价，实现并比较含计测/构建费的显式收益分配；运行评估和自动化仍待完成。
- ⭕️ [Pending] 実運用queryログは未提供。運用分布での回収と窓幅の検証はログ入手後。開発worldを運用分布とは扱わない / Production query logs are unavailable; defer operational payback/window validation until supplied, without treating development worlds as production / 未提供生产query日志，获取后验证运行回收/区间，不把开发world当生产分布。
- 🔴 [Later] 自動policy・既定のID順変更は独立した運用評価後 / Defer automatic policy/default ID changes until independent operational evaluation / 独立运行评估后再考虑自动policy或默认ID变更。
- 🟢 [Done] 全313テスト成功（350.08秒）。性能測定はテスト終了後 / All313 tests pass in350.08s; performance runs follow tests / 全313测试通过（350.08秒），性能测量在测试结束后。
- 🟢 [Done] 9 process/3 hash seed、2 world×2密度の36軌跡。33,696完全結果・216保存用checkpoint・108実保存/復元一致。同process内は保存バイト一致、process間はgraph edge順のみ正規化した内容と完全結果digestが一致 / Across36 trajectories,33,696 complete cases,216 serialized checkpoints and108 save/reloads match; bytes match within process, edge-order-normalized contents and full-result digests match across processes / 36轨迹中33,696完整结果、216序列化及108保存/恢复一致；同process字节一致，跨process仅规范edge顺序的内容及完整结果digest一致。
- 🟢 [Done] 調査8→6回（25%減）、最初の確認待ちは3→0回。再配置CPU中央値3.8–16.2%減。ただし総CPUのID比は−1.5〜+4.2%、回収3–6/9 process。密度のみの閾値・普遍的優位は採用しない / Reduce probes8→6, first wait3→0 and rebalance CPU3.8–16.2%; total versus ID ranges−1.5 to+4.2% with recovery3–6/9, insufficient for density-only thresholds / 探测8→6、首次等待3→0、重分配CPU减少3.8–16.2%；总CPU较ID为−1.5至+4.2%、回收3–6/9，不采用仅密度阈值。
- 🟢 [Done] 追加の保存監査を含む専用9テスト成功。process間のraw保存順・内部参照数・割当にはhash依存差があることも記録し、同一とは主張しない / Nine targeted tests pass after the added save audit; retain hash-dependent raw ordering/access/allocation differences without claiming equality / 添加保存审计后专用9测试通过；保留依赖hash的raw顺序/访问/分配差异，不声称一致。
- 🔴 [Later] 接地index以前からあるgraph edge順と探索参照順の再現性を別途監査。保存内容やquery意味を変えずに決定化できるか検証 / Separately audit pre-existing graph edge/search order reproducibility before deterministic ordering changes / 单独审计既有graph edge/搜索顺序可复现性，再验证不改变语义的确定顺序。


### Measured candidate search benefit — 2026-10-22

- 🟢 [Done] [検索利益の実測](G3.4-Grounding-Benefit-2026-10-22.md): 明示calibrationと`allocation_metric='benefit'`を追加。過去照合の線形/lookup CPU単価差と、計測・昇格構築費で候補を評価。通常queryに収集処理を追加せず、既定の頻度/ID/全走査を維持 / Add explicit calibration and benefit ranking from past unit CPU costs and setup costs; no default sampling/policy changes / 添加显式计测及收益排序，使用历史CPU单价和设置费用；不改变默认采样/policy。
- 🟢 [Done] appendは対象entryの見積りを失効、訂正/再構築/復元は全失効。query計数・保存schema・役割対/identity判定を維持。全317テスト成功（129.81秒） / Invalidate estimates on append/rebuild/load while preserving counters, persistence and joint semantics;317 tests pass / 追加/重建/加载使估算失效，保持计数、保存及联合语义；317测试通过。
- 🟢 [Done] 下記で同じ照合例・joint行の計測値を回数制限付きで再利用する方式を実装し、毎回計測と比較。標本数と偏りの検証は継続 / Implement bounded reuse for unchanged samples/joint rows below and compare fresh calibration; sample-size/bias validation continues / 下述实现相同样本/joint行的限次复用并与每次计测比较；样本数/偏斜验证继续。
- ⭕️ [Pending] 実運用ログによる分布変化・費用回収検証はログ提供後 / Production distribution/payback validation awaits logs / 生产分布/回收验证等待日志。
- 🔴 [Later] 自動policy・既定変更、退避利益と複数区間償却の最適化 / Defer automatic/default policy and displacement/multi-window optimization / 暂缓自动/默认policy及驱逐/多区间优化。
- 🟢 [Done] 9 process・3 hash seed、3 world×2密度の54軌跡。74,880完全結果・216保存checkpoint・162実保存/復元が一致。process間は完全結果とedge順のみ正規化した保存内容を照合 / Verify54 trajectories,74,880 complete cases,216 serialized checkpoints and162 save/reloads; cross-process full results and edge-order-normalized contents match / 验证54轨迹、74,880完整结果、216序列化及162保存/恢复，跨process完整结果及仅规范edge顺序的内容一致。
- 🟢 [Done] 単価利益方式は頻度方式比で総CPU3.7–50.7%悪化。小worldの昇格2→0でも計測約4.1–4.3msを回収できず。集中512 queryはID比8.0%減だが頻度方式より遅い。実験用opt-inに限定し既定不採用 / Benefit policy regresses total CPU3.7–50.7% versus frequency; fewer small-world promotions do not repay calibration. Concentrated512 beats ID8.0% but loses to frequency; keep experimental opt-in / 收益方式总CPU较频率恶化3.7–50.7%，小world减少升级未回收计测费；集中512较ID快8.0%仍慢于频率，仅实验性启用。


### Bounded calibration reuse — 2026-10-22

- 🟢 [Done] [計測値の再利用](G3.4-Grounding-Reuse-2026-10-22.md): 明示`reuse=True, max_reuses=2`。照合例の内容/順序、計測設定、予算が一致する成功計測だけを再利用。上限後は再計測 / Add explicit bounded reuse for successful identical ordered samples/settings/budget; refresh after the limit / 显式限次复用相同有序样本/设置/预算的成功计测，上限后重测。
- 🟢 [Done] 同じPrimitive・rowsでjoint行数不変の支持追加は辞書費用/計測を保持。新行・置換・不整合・訂正・再構築・復元は失効。集合全コピー/hashを増やさず、標本入力も最大64件で停止 / Preserve estimates on unchanged support without whole-set copies/hashes; invalidate changed rows/rebuilds and cap sample consumption at64 / 同行支持追加保留估算，不增加全集合复制/hash，变化/重建失效，最多消耗64样本。
- 🟢 [Done] 全320テスト成功（128.33秒）。再利用上限、照合例変化、無効化、連続確認、入力消費上限、3 worldの結果/保存を回帰検証 / All320 tests pass, covering reuse limits, changed samples, invalidation, confirmation, bounded input and three-world parity / 全320测试通过，覆盖复用上限、样本变化、失效、确认、输入上限及三world一致性。
- 🟢 [Done] 下記で同じ先頭queryから後半が変わる条件を追加し、prefix8/reservoir8/reservoir32の偏りと収集・計測込み費用を比較。収集/計測間隔の適応化は継続 / Compare prefix8/reservoir8/reservoir32 under changed tails below, including collection/calibration costs; adaptive cadence remains open / 下述比较尾部变化时三种采样的偏差及采集/计测成本，自适应间隔仍未完成。
- ⭕️ [Pending] 実運用queryログによる自動切替・再利用間隔の検証はログ提供後 / Operational automatic switching/reuse cadence awaits production logs / 生产自动切换/复用间隔验证等待日志。
- 🔴 [Later] 時間TTLや適応的失効、複数区間の償却・退避損失の最適化 / Defer time TTL/adaptive expiry and multi-window/displacement optimization / 暂缓时间TTL/自适应失效及多区间/驱逐优化。
- 🟢 [Done] 12 process・3 hash seed、72軌跡で102,912完全結果・288保存checkpoint・288実保存/復元が一致。区間ごとの保持cache推定量も記録 / Verify102,912 complete cases,288 serialized checkpoints and288 save/reloads over72 trajectories/12 processes; record retained-cache snapshots / 72轨迹12 process验证102,912完整结果、288序列化及288保存/恢复，记录保留cache快照。
- 🟢 [Done] 小worldの計測15→5回、集中world3→2回。計測CPU29.9–66.4%削減。対応processの総CPU変化率中央値は0.6–18.3%改善だが、独立/集中512 queryの方式別中央値比は約7.0%/6.8%悪化。両集計を保持し、頻度方式より遅いため既定不採用 / Cut calibration CPU29.9–66.4%; paired total changes improve0.6–18.3% but separate medians regress7.0%/6.8% at independent/concentrated512. Retain both summaries; frequency remains faster so no default change / 计测CPU减少29.9–66.4%，配对总变化改善0.6–18.3%，独立/集中512分别汇总中位比却恶化7.0%/6.8%；保留两种汇总，频率仍更快，不改默认。


### Whole-window binding samples — 2026-10-22

- 🟢 [Done] [区間全体からの標本化](G3.4-Grounding-Sampling-2026-10-22.md): 明示`GroundingSampleWindow`を追加。Primitiveごと1〜64件のjoint照合をreservoir/prefix方式で保持。同じseed/入力列では再現可能、通常queryは変更しない / Add explicit bounded per-Primitive reservoir/prefix windows preserving joint bindings and deterministic seeds; normal queries unchanged / 添加显式每Primitive限量reservoir/prefix，保持联合照合及seed可复现性，不改普通query。
- 🟢 [Done] 先頭が同じでも後半が変わる集中worldでprefixの計測再利用とreservoirの再計測を確認。512 sampling seedで位置別選択頻度、Primitive間の独立性、役割/identity一体保持、入力変更からの保護を検証。全323テスト成功（102.14秒） / Validate changed-tail recalibration,512-seed inclusion frequencies, stream independence and joint immutable samples;323 tests pass / 验证尾变重测、512 seed选择频率、流独立及联合不可变样本；323测试通过。
- 🟢 [Done] 下記で明示的な収集周期を実装し、省略区間の標本TVと費用を比較。適応化は継続 / Implement explicit cadence below and compare skipped-window TV/costs; adaptation remains open / 下述实现显式周期，比较跳过区间TV/成本，自适应仍未完成。
- ⭕️ [Pending] 実運用ログ上の分布変化・sampling seed感度・自動間隔はログ提供後 / Operational drift/seed sensitivity/automatic cadence awaits logs / 生产漂移/seed敏感性/自动间隔等待日志。
- 🔴 [Later] 省略を利用するreservoir方式と全Primitive合計のcollector予算 / Defer skip-based reservoir algorithms and aggregate collector memory budgets / 暂缓跳过式reservoir及全Primitive采集器总预算。
- 🟢 [Done] 15 process・3 hash seed、90軌跡で132,480完全結果・360保存checkpoint・450実保存/復元が一致。同process内は保存バイト一致、process間は完全結果とedge順のみ正規化した保存内容が一致 / Verify132,480 complete cases,360 serialized checkpoints and450 save/reloads across90 trajectories/15 processes/3 hash seeds; bytes match within each process, full results and edge-order-normalized contents match across processes / 15 process、3 hash seed、90轨迹验证132,480完整结果、360序列化及450保存/恢复一致；同process字节一致，跨process完整结果及仅规范edge顺序的保存内容一致。
- 🟢 [Done] 集中512 queryの後半変化で分布差TVはprefix8の0.9844からreservoir8の0.0156へ改善（sampling seed 0）。ただし収集・計測込み総CPU中央値はprefix8比で全条件0.3–28.9%増。32例も単一seedで必ず精度改善するとは限らず費用増。品質改善と費用を分けて記録し、明示opt-in・既定維持 / At sampling seed0, concentrated512 changed-tail TV improves0.9844→0.0156, but total CPU medians including collection/calibration regress0.3–28.9% versus prefix8 across all conditions.32 samples cost more without guaranteed single-seed accuracy gains; keep explicit opt-in/defaults / sampling seed0时集中512尾变TV从0.9844改善至0.0156，但含采样/计测总CPU中位数在各条件较prefix8增加0.3–28.9%；32例成本更高且单seed精度不保证改善，保持显式启用及默认配置。

### Explicit collection cadence — 2026-10-26

- 🟢 [Done] [収集間隔](G3.4-Grounding-Cadence-2026-10-26.md): `GroundingSampleSchedule`で毎区間/2区間/4区間を比較。省略区間にobserver不要、既知変更は`force=True`で収集・周期リセット。既定interval1、通常query変更なし / Add explicit cadence and forced refresh without skipped-window observers; retain interval1 and normal queries / 添加显式周期及强制刷新，跳过区间无观察器，保持间隔1及普通query。
- 🟢 [Done] 全325テスト成功（42.54秒）。15 process・3 hash seed・90軌跡、132,480完全結果・360保存checkpoint・450実保存/復元一致。同process保存バイトとprocess間edge順のみ正規化した内容・完全結果digestを検証 / 325 tests pass; verify132,480 complete cases,360 checkpoints and450 save/reloads across90 trajectories/15 processes, with within-process bytes and cross-process normalized contents/results / 325测试通过；15 process、90轨迹验证132,480完整结果、360序列化及450保存/恢复，同process字节及跨process规范内容/结果一致。
- 🟢 [Done] 4区間周期は毎区間比総CPU中央値が−23.9〜+0.2%、2区間周期は−13.1〜+10.0%。集中512の変化直後TVは毎区間0.0156に対し省略0.9844。全条件で頻度方式より遅く、既定不採用。計測境界と対応process集計も報告 / Every4 total medians range−23.9 to+0.2%, every2−13.1 to+10.0%; skipped drift TV0.9844 versus0.0156 at concentrated512. Frequency remains faster; report timing boundaries/paired summaries, no default change / 每4区间总中位变化−23.9至+0.2%，每2区间−13.1至+10.0%；集中512跳过TV0.9844而每区间0.0156，仍慢于频率，记录计时边界及配对汇总，不改默认。
- 🟢 [Done] 下記で完了区間の件数ヒントと短期変化・位相差の比較を追加。同件数の役割/identity変化は検知できないことを明示 / Add completed-count hints and transient/phase comparisons below, retaining equal-count role/identity blind spots / 下述添加完成计数提示及短期/相位比较，明确同计数角色/identity盲点。
- ⭕️ [Pending] 実運用ログによる周期・閾値選定 / Production cadence/threshold validation awaits logs / 生产周期/阈值验证等待日志。
- 🔴 [Later] 適応周期・skip-based reservoir・全Primitive collector合計予算 / Adaptive cadence, skip-based reservoirs and aggregate collector budgets / 自适应周期、跳过式reservoir及采集器总预算。

### Completed-count hints for transient drift — 2026-10-28

- 🟢 [Done] [短期変化と件数ヒント](G3.4-Grounding-Transient-2026-10-28.md): `GroundingCountTrigger`を追加。完了区間の件数差/比から次区間の強制収集を促す。初回・収集済み区間の追加収集を抑止、保持状態は直前件数のみ。通常query・保存形式・既定は維持 / Add explicit completed-count hints for the next window, suppressing initial/already-sampled changes; constant state and unchanged defaults/persistence / 添加下一窗口完成计数提示，抑制初次/已采样变化，常量状态，保持默认及保存。
- 🟢 [Done] 全327テスト成功（296.02秒）。閾値・0件・不正入力・未来情報不使用・同件数の見落とし・変化後の古い標本更新と全結果/保存一致を検証 / 327 tests pass, covering thresholds, zeros, validation, causal timing, equal-count blindness, stale-sample recovery and parity / 327测试通过，覆盖阈值、零计数、校验、因果顺序、同计数盲点、旧样本恢复及一致性。
- 🟢 [Done] [2026-11-02の比較結果](G3.4-Grounding-Skip-2026-11-02.md): 通常のreservoir収集における毎照合の乱数生成を減らす方式を比較。位置別選択確率・joint条件・小/大区間の総費用を検証し、収集自体の費用を削減 / Compare fewer-random-draw reservoir collection with inclusion probabilities, joint semantics and small/large-window total costs / 比较减少随机调用的reservoir，验证选择概率、联合条件及大小窗口总成本，降低采样本身成本。
- ⭕️ [Pending] 実運用ログでの区間・件数閾値・変化と件数の関係の検証 / Operational windows/count thresholds/drift correlation await logs / 运行窗口、计数阈值及漂移关联验证等待日志。
- 🔴 [Later] 自動周期と件数以外の低費用な変化検出、全Primitive collector予算 / Automatic cadence, other cheap drift signals and aggregate collector budgets / 自动周期、其他低成本漂移信号及采集器总预算。
- 🟢 [Done] 15 process・3 hash seed・180軌跡で295,680完全結果・1,440保存checkpoint・900実保存/復元一致。収集判断もprocess間一致。全体ストリーム監査は配分に渡さない / Verify295,680 complete cases,1,440 checkpoints and900 save/reloads over180 trajectories; collection decisions reproduce across processes and audit streams never inform allocation / 180轨迹验证295,680完整结果、1,440状态及900保存恢复；采样决策跨process一致，审计流不参与分配。
- 🟢 [Done] 集中・位相4・件数増加後の復帰で区間6のTV1→0。同件数変化・周期外の1区間変化は検出できず。周期方式比CPU中央値−15.0〜+7.9%、品質改善条件でも対応process中央値+0.9%・高速7/15で安定優位なし。明示opt-inを維持 / Restore TV1→0 after concentrated phase4/burst return, but miss equal-count/off-cycle transients. CPU medians range−15.0 to+7.9%; quality-improving case paired+0.9%, faster7/15; retain opt-in / 集中相位4突增后TV1→0，仍遗漏同计数/周期外短变；CPU中位比−15.0至+7.9%，质量改善条件配对+0.9%、仅7/15更快，保持显式启用。

### Skip reservoir — 2026-11-02

- 🟢 [Done] [収集コストの比較](G3.4-Grounding-Skip-2026-11-02.md): 1 Primitive・8,192照合で乱数呼び出し8,184→平均169.30、収集CPU44.1%減。32照合では16.4%増、全体CPUは−1.0〜+2.3%のため明示選択。 / Opt-in skip sampling cuts long-stream collector CPU by 44.1% but costs 16.4% more for short streams; no consistent end-to-end gain. / 显式跳过采样在长流降低采样CPU 44.1%，短流增加16.4%，整体未稳定提速。
- 🟢 [Done] 全329テスト成功（50.08秒）。1,024 sampling seedで位置別採取・joint条件・独立再現性を検証。12 process・72軌跡の102,912完全結果、288 checkpoint、288保存/復元が一致。 / Verified inclusion and joint bindings across 1,024 seeds, full results and persistence across 72 trajectories. / 1,024个seed验证位置采样和联合条件，72条轨迹验证完整结果及持久化一致。
- 🟢 [Done] [2026-11-19のcollector予算比較](G3.4-Grounding-Collector-Budget-2026-11-19.md)で多数短列の保持量・peak・標本欠落を測定。差分計量と同一byte予算の比較は末尾のNextへ継続。 / Measure retained memory, peak and coverage loss; continue incremental accounting and matched-byte comparisons in the latest Next item. / 已测量保留量、峰值及样本缺失；增量计量和同字节预算比较继续列入末尾Next。
- ⭕️ [Pending] 実運用の照合列長・費用回収はログ入手後。 / Production stream lengths and payback await logs. / 生产流长度及收益等待日志。

### LittleBit-inspired accounting and compression controls — 2026-11-11

参考 / Source / 来源: [LittleBit: Ultra Low-Bit Quantization via Latent Factorization, arXiv:2506.13771v5](https://arxiv.org/html/2506.13771v5)（v5: 2026-02-05、確認: 2026-11-11）。§3・§4.1はLLM重みの低rank・二値化・残差補償とQAT、§5・Appendix Dは補助パラメータを含む容量と速度の評価。 / Sections 3–4.1 address approximate LLM weight compression and QAT; §5 and Appendix D distinguish auxiliary storage and practical latency. / 第3至4.1节讨论LLM权重近似压缩及QAT，第5节和附录D区分辅助存储与实际延迟。

適用範囲 / Scope / 范围: 以下はRISAへの応用提案であり、論文がRISAの改善を実証したものではない。現行の離散Event・joint witness・役割対・identityを低rank近似や二値化で置き換えない。標本の欠落は配分品質の問題として測り、正解・根拠の欠落と混同しない。 / These are proposed RISA adaptations, not paper-validated RISA results. Keep exact Events, joint witnesses and identity semantics; distinguish allocation-sample coverage from answer/evidence correctness. / 以下为RISA应用提案，并非论文已验证的结果；保持Event、联合证据及identity精确语义，区分分配样本覆盖率与答案/证据正确性。

- 🟠 [Next] **既存collector合計予算実験の評価を強化**。標本payloadだけでなく、Primitive別の辞書・RNG状態・counter・skip状態・共有role/identity表を内訳にする。共有オブジェクトの二重計上を避け、保持量・一時展開peak・実保存bytesを別々に報告し、Python推定量をRSSと呼ばない。無制限方式、単純な件数上限、総予算方式を同一入力・同一実メモリ予算で比較し、適用した上限の対象を明示する。 / Extend the existing collector-budget experiment with payload, dictionaries, RNG, counters, skip state and shared role/identity tables; avoid double counting. Separate retained estimates, temporary peaks and saved bytes. Compare uncapped, count-capped and aggregate-budget approaches with explicit accounting boundaries. / 强化现有采样总预算实验，统计payload、字典、RNG、计数、skip及共享角色/identity表，避免重复计量；区分保留估计、临时峰值和保存字节，比较无限额、件数上限与总预算，明确预算边界。
- 🟠 [Next] **同じ実験の採用条件**。少数長列と多数短列、役割/identityの低・高多様性、集中先の変化を分ける。収集・出力・校正・再配置・再構築の総CPU/wallと、標本coverage・TVを同時に記録。独立world・複数seed/hash順序で全走査との完全結果・根拠参照・保存内容の一致を必須とし、総費用が悪化した方式は既定にしない。容量や乱数回数の減少だけを高速化の証拠としない。 / In the same experiment, stratify stream count/length, binding diversity and shifting hotspots; report all maintenance costs and sample coverage/TV. Require exact results, evidence references and persistence against full scans across independent worlds and seeds. Do not infer speed from compactness alone. / 同一实验区分流数量/长度、绑定多样性及热点迁移，记录全部维护成本和样本coverage/TV；跨独立world与seed验证完整结果、证据引用及保存一致，不以体积下降推断提速。
- 🔴 [Later] **共有表現＋正確な例外の可逆符号化を比較**。予算内訳で重複payloadが支配的と分かった場合に限り、role/identityのintern化・joint行の共有辞書と、共通部分＋例外表を比較する。これは残差補償からの発想であり、数値近似の導入ではない。参照表・例外・復号作業も予算へ含め、稀な依存反例、append/訂正/復元を含む完全一致で採否を決める。 / If duplicate payload dominates, compare interning/shared joint dictionaries with lossless common-plus-exception encoding. This is an analogy, not numerical residual approximation; charge tables, exceptions and decoding, and preserve rare dependencies through updates and reloads. / 仅在重复payload占主导时比较intern化、联合共享字典与无损公共部分加例外编码；这是启发而非数值近似，计入表、例外和解码成本，保持稀有依赖及更新恢复精确一致。
- 🔴 [Later] **G4後の知覚adapter候補**。LLM adapterを必要とする段階で、LittleBit型圧縮を通常精度・一般的な低bit方式と比較する。QAT/蒸留の準備費用、モデル全体・作業領域の容量、実機end-to-end遅延、英語/日本語/简体中文からの構造抽出と誤bindingを評価する。論文の最大11.6×はA100上のMLP kernel比較（§5, Fig.6）であり、RISAや他ハードウェアの全体速度の保証ではない。実装未着手はLaterとし、環境で実施不能な項目だけPendingへ移す。 / After G4, evaluate compressed perception adapters against full precision and low-bit baselines, including training cost, total memory, hardware latency and trilingual extraction/binding quality. The paper's 11.6× figure is an A100 MLP-kernel result, not a RISA end-to-end guarantee. / G4之后比较压缩感知adapter与全精度、低bit基线，包含训练成本、总内存、实机延迟及三语结构提取/绑定质量。论文11.6×仅为A100 MLP kernel结果，不保证RISA整体提速。

この追記は研究計画のみ。実装・性能実験の新たな完了を意味せず、既存G3.4の完全一致・独立評価gateを維持する。 / Planning only; no new implementation or performance result is claimed, and existing G3.4 gates remain intact. / 本次仅更新计划，不宣称新增实现或性能结果，保持G3.4原有门槛。

### Change-driven computation and reusable results — 2026-11-12

参照 / Reference / 参考: [計算量削減アイデア提案](chatgpt-conversation://6af5043e-b69c-83ec-8aaa-a19733416756)（2026-11-12確認）。「変化の影響先だけを更新」「推論結果と文章化を分離」「誤差に応じて更新範囲を広げる」をRISA向けに具体化する。参照チャットのCDNは仮説名であり、本プロジェクトでの実装・新規性・高速化を意味しない。80%削減の例やチャット内の他研究の数値・未解決引用を採用根拠には使わない。 / Adapt the conversation's change-driven updates, reusable reasoning and separated rendering as testable RISA hypotheses. CDN is a proposed name, not an implemented or validated architecture; illustrative savings and unresolved research citations are not adoption evidence. / 将对话中的变化驱动更新、推理复用及独立表达转为可检验的RISA假设；CDN只是提议名称，示例收益及未解析研究引用不作为采纳证据。

**既存機構との対応 / Existing mechanisms / 现有机制**

- 🟢 [Done] 接地indexのappend差分更新と、joint支持が変わらない場合の計測値保持は既存の `update_primitive_grounding` にある。訂正時の `invalidate_primitive_grounding` は現在全体を破棄する。この既存実装を出発点とし、CDN全体の実装済み扱いにはしない。 / Existing append updates and unchanged-support calibration reuse in `primitive_grounding.py` provide a starting point; correction invalidation currently clears the entire index. This does not implement CDN as a whole. / 现有接地index已支持追加增量更新及不变支持的计测复用，但修改会清空整个index；不代表CDN整体已实现。
- 🟢 [Done] `PredictionResult` と `explainer.format_prediction` は既に構造化予測と表示処理を分離する。小型生成モデルや文章の意味検証は未実装。 / Structured prediction and display formatting are already separate; neural rendering and semantic validation are not implemented. / 结构化预测与显示已分离，神经表达器和语义校验尚未实现。

**取り入れる設計 / Design commitments / 设计约束**

再利用の可否は入力の似かよりや誤差閾値だけで決めず、依存対象の変更で判定する。最初の対象は再構築可能な接地indexに限定する。Event IDから依存Primitiveへの逆参照と世代情報を持つ案を、都度全走査と比較する。保持するjoint行が同じでも、支持Event・支持数・confidence・出典が変化すれば、それらを読む結果は別途更新する。検索の「不一致」「棄却」も、新しい証拠や候補の追加で変わり得る。未知の依存、直接変更、role誘導規則の変更、復元後の未検証状態は全再構築へ戻す。少量の変更が広い依存先に伝わるケースも省略しない。

Use dependency changes, not input similarity or low error alone, to authorize reuse. Start with rebuildable grounding indexes. Compare Event-to-Primitive reverse references and generations with scanning. Unchanged joint rows do not imply unchanged support counts, confidence or provenance. Negative results can become positive after new evidence. Unknown dependencies, direct mutations, changed role-induction rules and unverified reload state require full reconstruction; a small input delta may have broad effects.

依据依赖变化而非输入相似度或低误差决定复用，首先限定于可重建接地index。比较Event到Primitive反向引用、版本与全扫描。joint行不变不意味着支持数、置信度或来源不变；新增证据可改变否定结果。依赖未知、直接修改、角色规则变化及未验证恢复状态需完整重建，小变化也可能广泛传播。

- 🟠 [Next] **訂正依存pilotの残りの比較**（2026-11-24の明示cache APIと局所/広域比較は完了。最新優先順を参照）。逆参照の構築/更新/保持費用を含め、全走査・現行全再構築・依存先再構築を比較する。無関係Event、同じjoint行への支持追加、役割/identity訂正、複数Primitiveで共有する証拠、未登録参照の追加、候補の追加/削除、影響先がほぼ全体になるケースを固定する。通常queryの予測器や推定routerは先に追加しない。 / After the collector-budget evaluation, compare scans, full rebuilds and dependency-scoped correction rebuilds including reverse-index costs, with irrelevant changes, shared witnesses, corrections, new/missing references and broad fan-out controls. / 采样总预算评估后比较全扫描、全重建及依赖范围重建，计入反向index成本，覆盖无关变化、共享证据、修改、新增/缺失引用及广泛传播；不先加入预测router。
- 🟠 [Next] **同pilotの採用条件**。同一Event列を独立stateへ与え、全結果payload（候補・score・根拠を含む）、役割/identity反例、保存/復元が現行方式と一致すること。触ったEvent/Primitive数、検査数、全再構築へのfallback率、保持bytes・一時peak、総CPU/wallを記録する。`影響判定 + 局所更新 + 検証 + fallback` の費用を全再構築と比較し、複数process/hash順序・複数変更密度で回収を確認する。未参照部分の正しさを実行時の全走査で確かめる設計なら、その検証費用も必ず含める。 / Require complete result/evidence/persistence parity on independent states and dependency counterexamples. Charge routing, updates, verification and fallback; report work, memory and end-to-end costs across change densities, processes and hash seeds. Runtime full-scan verification is never free. / 独立state验证完整结果、证据及保存一致，统计访问范围、检查数、fallback率、内存与总成本；跨变化密度、process和hash顺序验证收益，运行时全扫描校验必须计费。
- 🔴 [Later] **学習の局所化**。依存pilotが成立した後、candidate生成・Replay・再検証の影響範囲へ広げる。誤差ゼロでも支持数・頻度・減衰・出典・将来の候補機会は更新対象とし、Eventの取り込み自体を省略しない。G3.2の負の結果を保持し、既存能力保持と独立held-out利得のgateを緩めない。ニューラル逆伝播の省略は現行RISAの対象外。 / Extend proven dependencies to discovery, Replay and revalidation without skipping evidence ingestion, counts, decay or future candidate opportunities. Retain G3.2 negative findings and retention/held-out gates; neural backward skipping is outside the current core. / 依赖验证后再扩展至候选发现、Replay和再验证，不省略证据摄入、计数、衰减及未来候选机会；保留G3.2负结果及能力保持/留出门槛，当前核心不涉及神经反传省略。
- 🔴 [Later] **推論結果の再利用と文章化**。G4後のadapter段階で、構造化結果を唯一の意味入力として英語/日本語/简体中文へ出力する。まず決定的テンプレートを基準とし、学習型生成器は任意の比較対象にする。主体/対象・否定・確信度・根拠ID・棄却を保持し、表示だけの変更で再推論しない。意味変更時は依存を再検証し、不正な文章化はテンプレートへ戻す。結果cacheはquery引数、状態/資源、制約、候補集合と依存世代を含む契約が確定してから導入する。 / After G4, render structured results in three languages using deterministic templates as the baseline. Preserve binding, negation, confidence, evidence and abstention; revalidate semantic changes and fall back on invalid rendering. Define complete query/state/resource/constraint/candidate dependencies before result caching. / G4之后以确定模板为基线将结构结果输出为三语，保持绑定、否定、置信度、证据和弃答；语义变化需再验证，表达失败回退模板；明确query、状态、资源、约束和候选依赖后才缓存结果。

この更新で採用したのは設計・実験計画。新しいrouter、訂正差分更新、結果cacheの実装や速度向上はまだ主張しない。現在のcollectorメモリ評価を先に完結し、その後に上記pilotへ進む。 / This update adopts design and evaluation plans, not a new router, correction algorithm, result cache or speedup claim. Finish collector-memory evaluation first. / 本次采纳设计和实验计划，不宣称新增router、修改增量算法、结果缓存或提速；先完成采样内存评估。

### Cost-aware execution paths and contribution controls — 2026-11-12

入力資料 / Input / 输入: ユーザー提示の「既存エンジン改善→必要計算の削減→構造変更」の提案。以下はRISA向けの設計・実験計画として採用する。提示されたvLLM・DFlash・モデル振り分け等の倍率は条件・出典をここでは検証していないため、実績・目標値・掛け合わせた期待値として記録しない。既存collector予算→訂正依存pilot→G4の順序は変えない。 / Adopt the supplied staged optimization ideas as RISA evaluation plans. Quoted external speedups are not verified here and are not targets or multiplicative forecasts. Preserve the current collector-budget, correction-dependency and G4 sequence. / 将用户的分阶段优化建议采纳为RISA评估计划；外部倍率未在此核实，不作为实绩、目标或相乘预测；保持采样预算、修改依赖pilot、G4的顺序。

- 🟠 [Next] **既存pilotに寄与の対照実験を追加**。collector予算・訂正依存評価では、固定入力と独立stateで各最適化のon/offを比較し、単独効果と組合せ効果を分ける。計数対象は層やAttention Headではなく、Event参照・joint照合・index構築/更新・標本収集・校正・再配置・検証・fallbackとする。多用される処理が低寄与とは限らないため、実行回数だけを根拠に削除しない。役割/identityの稀な反例、未知組合せ、分布変化を含め、測定用probeを学習や選択判断へ混入させない。 / Add matched on/off and combined ablations to existing pilots for evidence reads, joint matching, index maintenance, sampling, calibration, verification and fallback. Frequency is not causal contribution; include rare binding counterexamples and keep scoring probes out of training/routing. / 在既有pilot加入匹配的开关及组合消融，测量证据访问、联合匹配、index维护、采样、校准、验证和fallback；频率不等于因果贡献，覆盖稀有绑定反例并隔离评分probe。
- 🟠 [Next] **同一比較の費用指標を固定**。単一queryのCPU/wall、全処理の時間、連続queryのthroughput、p50/p95、構築・更新・保持量を別々に報告する。計時は監査と分離し、選択器・cache照合・再試行・検証を含む。cold/warm、固定/移動集中、小/大区間を区別する。現在はCPU研究prototypeの比較であり、throughput改善をそのままGPU費用・金銭・消費電力の削減としない。tailを主張できる反復数と測定条件を事前固定する。 / Separate per-query latency, total time, throughput, percentiles and memory; include selection, cache checks, retries and verification. Distinguish cold/warm and changing workloads; CPU measurements do not establish monetary or energy savings. / 分别报告单query延迟、总时间、吞吐、分位数及内存，计入选择、cache检查、重试与验证；区分冷暖和变化负载，CPU测量不代表金钱或能耗收益。
- 🔴 [Later] **正確な処理経路の選択**。collector予算と訂正依存の費用回収を確認した後、同じ結果を返す全走査・線形index・lookup・検証済み再利用の範囲で選択を比較する。まず固定方式と単純な規則を基準とし、過去のquery数・更新密度・実測費用だけを使う。全経路の実行後に最速を選ぶoracleはオフラインの参考下限に限定し、本番routerの成果としない。未校正・未知分布・依存不明なら既定の正確な経路へ戻す。選択でqueryの意味・候補集合・根拠を変えず、完全結果・保存/復元一致と総費用改善で採否を決める。 / After cost validation, compare fixed and simple causal selection among exact scans, linear indexes, lookups and validated reuse. An all-path hindsight oracle is only an offline lower-bound reference. Unknown costs/dependencies use the exact default; require full-result and persistence parity plus lower total cost. / 成本验证后，在精确扫描、线性index、lookup及已验证复用之间比较固定与简单因果选择；事后全路径oracle仅作离线下限参考；未知成本/依赖回退精确默认，要求完整结果及保存一致且总成本降低。
- 🔴 [Later] **推論予算と投機的な候補生成は別の品質実験**。探索深さ・展開数・Replay予算の削減は単なる実行経路変更ではないため、完全一致の最適化と分離する。上限到達を「解なし」と扱わず、未完了と正当な棄却を区別する。安価な候補生成→既存の意味/根拠検証→必要なら探索拡張を比較し、有効な候補を見つけても、同一の最良性・候補列挙が必要な契約では即打切りしない。品質目標、誤受理、成功率、fallback率、破棄した計算と再探索の費用を独立held-outで評価する。 / Treat reduced search/Replay budgets and speculative proposals as separate quality-changing experiments. Budget exhaustion is not proof of no solution. Validate proposals and extend search when necessary; a valid proposal does not prove optimality or complete enumeration. Charge rejected work and retries and assess held-out quality. / 减少搜索/Replay预算及投机候选属于独立的质量变化实验，预算耗尽不证明无解；验证候选并按需扩展，有效候选不保证最优或完整枚举，计入废弃工作及重试并评估留出质量。
- 🔴 [Later] **LLMサービング技術はadapter導入後**。G4後に生成モデルを実際に接続する場合だけ、batching、KV管理、量子化、投機生成、大小モデルの切替を比較対象にする。まず既存の構造化結果＋決定的三言語表示を基準とし、英語/日本語/简体中文で内容・否定・identity・根拠・棄却を保持する。単独/併用、同じハードウェア・負荷・品質条件でend-to-end費用を計測する。これらを現在のPython接地indexへ直接移植しない。 / Evaluate batching, KV management, quantization, speculative generation and model cascades only when a post-G4 language adapter exists, against deterministic trilingual rendering and matched hardware/load/quality baselines. / 仅在G4后实际引入语言adapter时比较batching、KV管理、量化、投机生成和模型级联，以确定三语表达及同硬件/负载/质量为基线，不直接移植至当前Python接地index。

今回の変更は計画の統合のみ。新しいrouterや省略実行は未実装であり、1/2・1/5・1/10の費用削減を約束しない。 / Planning integration only: no new router or execution skipping is implemented, and no reduction factor is promised. / 本次仅整合计划，未实现新router或省略执行，不承诺特定降本倍率。


### Lottery-ticket-inspired reversible selection — 2026-11-14

参照 / References / 参考: [宝くじ仮説の解説](chatgpt-conversation://6af81e8c-4140-83e8-b099-ea0ae1934e50)、[Frankle & Carbin, The Lottery Ticket Hypothesis, ICLR 2019](https://arxiv.org/abs/1803.03635)。原論文はニューラルネットの部分構造と初期重みの組合せを扱う。RISAでは「学習後に縮められること」と「縮めた状態で将来も学べること」を分ける実験設計を採用する。これは記号構造への類推であり、RISAで当たりくじや初期重みの効果を実証したことにはならない。 / The paper concerns neural subnetworks and their initial weights. Adopt the distinction between compression after learning and continued learnability under restriction as a symbolic experiment, not evidence of neural winning tickets in RISA. / 原论文研究神经子网络及其初始权重；RISA采纳“学习后可压缩”与“受限后仍可学习”的实验区分，属于符号结构类比，不证明RISA存在神经中奖子网。

- 🟠 [Next] **既存pilotの判定を段階化**。collector予算・訂正依存pilotの同一入力比較に、変更直後、同じ追加Event列の処理後、保存/復元後の監査点を置く。全走査との完全結果（score・根拠・identity条件を含む）と保存内容の一致を各点で確認し、不一致を後の回復で相殺しない。選択用developmentと独立held-outを分離し、初期構築から費用回収までの累積CPU/wall・保持量・peakを記録する。 / Add immediate, matched-future-stream and reload checkpoints to existing exact-optimization pilots; require full results and persistence parity at every checkpoint, rather than accepting later recovery. Separate development selection from held-out audits and measure cumulative cost from initialization to payback. / 在既有精确优化pilot加入修改后、相同后续Event流后及恢复后检查点，每点要求完整结果及保存一致，不允许以后续恢复抵消不一致；隔离选择与留出审计，测量初始化至回本的累计成本。
- 🔴 [Later] **可逆な実行対象制限のpilot**。collector予算・訂正依存評価を先に完結し、G3.4で有効な候補の採用と制限対象の冗長性を確認してから着手する。既存の候補lifecycleとreadout復元機構を調べ、重複した休眠機構を作らない。Event・Primitive・候補の根拠と履歴は保持し、まず実験用のactive集合だけを制限する。未知条件や依存不明時は全対象へ戻す。全結果一致を保証できない制限は品質変化実験として分離し、正確なindex最適化として扱わない。 / After the current pilots and demonstrated candidate opportunity/redundancy in G3.4, test reversible active-set restriction using existing lifecycle/restoration mechanisms where possible. Preserve authoritative Events, Primitives, evidence and history; fall back to the full set for unknown conditions. Treat restrictions without exact guarantees as quality-changing experiments. / 先完成当前pilot，并在G3.4确认有效候选和冗余机会，再复用现有生命周期及恢复机制测试可逆active集合限制；保留Event、Primitive、证据及历史，未知条件回退全集；无法保证精确一致的限制属于质量变化实验。
- 🔴 [Later] **四つの対照と未来情報の遮断**。全対象を維持、初めから小さい容量、同じ学習checkpointで同容量を無作為選択、その時点までの証拠で選択、の4条件を比較する。同じcheckpointからの分岐は独立stateを使い、その後のEvent順序・query・回復予算を揃える。「初めから小さい」条件だけは同じ入力を最初から学習し、大きい系の学習済み状態を受け取らない。選択は使用頻度だけで決めず、役割対・joint witness・identityを一体として扱う。未来の成績で選んだ集合は参考oracleに限定する。 / Compare full capacity, small capacity from the start, random same-size restriction at a checkpoint and evidence-informed restriction at that checkpoint. Use independent states and matched future streams/budgets; the small-from-start arm must not inherit learned state. Preserve coupled bindings; hindsight masks are offline oracles only. / 比较全容量、从头小容量、同checkpoint随机等容量限制及基于当时证据的限制；分支独立且后续流和预算一致，从头小容量不得继承大系统的学习状态；保留联合绑定，未来信息选择仅作离线oracle。
- 🔴 [Later] **直後品質・回復能力・最終品質を分離**。未知組合せ、独立化できない反例、低頻度の役割/identity、A→B→Aを含む独立worldで評価する。短い回復学習が成功しても最終held-outを再利用して選択しない。候補採用・休眠が発火しない場合は機会不足として報告し、G3.2の負の結果や採用gateを変更しない。品質変化条件では全対象との結果差を報告し、各条件自身の保存前後の完全結果・履歴の復元一致を別途必須にする。 / Separate immediate degradation, recovery and final held-out quality across unknown compositions, inseparable dependencies, rare bindings and A→B→A worlds. Do not tune on final tests or relax existing gates when opportunities are absent. Report differences from the full-set arm separately from mandatory within-arm save/reload fidelity. / 区分即时退化、恢复及最终留出质量，覆盖未知组合、不可拆依赖、稀有绑定和A→B→A；不使用最终测试调参，不因机会缺失放宽门槛；相对全集的差异与各条件保存恢复一致性分别报告。
- 🔴 [Later] **同品質までの総費用で採否を決定**。候補探索、試験分岐、失敗した制限、回復、fallback、再昇格、再構築を含め、事前固定した品質条件までの総CPU/wall・Event数を比較する。未到達は未到達として記録する。active件数減少をメモリ削減とみなさず、休眠構造・復元情報を含む保持量、peak、実保存bytesを測る。既存readout圧縮では総保存量が増えた結果を維持し、純利益が確認されるまで既定動作を変えない。 / Decide by total time and Events to predefined quality, including selection, failed trials, recovery and fallback; report non-attainment. Count dormant structures and recovery metadata in retained/peak/saved storage. Fewer active entries alone establish neither memory savings nor speedup; retain the existing negative compaction result and defaults until net benefit is shown. / 以达到预定质量的总时间及Event数判定，计入选择、失败试验、恢复和fallback，明确未达标；内存包含休眠结构及恢复元数据，active数量减少不代表省内存或提速，保留既有压缩负面结果，确认净收益前不改默认。

今回導入したのは評価条件と後続実験の設計。実行対象制限は未実装。FFNの縮小やAdam状態の移行は現行の記号系に対応しないため直接導入せず、将来LLM adapterを学習する必要が生じた段階で再検討する。 / This update adopts evaluation requirements and a future experiment, not an implemented restriction. FFN resizing and Adam-state migration do not apply to the current symbolic system; reconsider only if training a future LLM adapter becomes necessary. / 本次采纳评估要求及后续实验设计，尚未实现执行集合限制；FFN缩减及Adam状态迁移不适用于当前符号系统，仅在未来确需训练LLM adapter时重评。


### Explicit constraints and verified search — 2026-11-16

参考 / Source / 来源: [Classical Energies Learn to Reason 1,000× Faster than Looped Models, CRAM](https://arxiv.org/html/2611.17309)（v1、2026-11-12）。論文は明示的energyによる制約パズルの学習・探索を扱う。§3とAppendix B/Cを参考に、以下をRISA独自の設計・評価案とする。 / The paper studies explicit-energy learning and search for constraint puzzles. Sections 3 and Appendices B/C motivate the following RISA-specific proposals. / 论文研究显式energy的约束谜题学习与搜索；参考第3节及附录B/C，提出以下RISA设计及评估方案。

適用境界 / Boundary / 边界: 論文のfit timeはCRAMがwarm、比較モデルがcoldであり、FLOPsにはデータ移動・乱数生成等を含めない。表題の倍率をRISAの目標値に転用しない。 / Fit timing compares warm CRAM with cold baselines; FLOPs exclude data movement and RNG, among other operations. Do not transfer the headline multiplier to RISA. / fit计时比较warm CRAM与cold基线，FLOPs不含数据移动及随机数生成等，不将标题倍率转为RISA目标。

- 🟠 [Next] **既存の訂正依存pilotへ局所再計算の対照を統合**。Event→Primitiveの逆参照から影響するjoint行・役割/identity条件・支持数・根拠を列挙し、全再構築と依存先再構築を比較する。新規Eventで成立する未登録の組合せや削除/置換も対象とし、逆参照にないことを無影響の証明にしない。依存不明は全再構築へ戻す。反映直後・追加学習後・保存復元後の完全結果を独立worldで照合し、逆参照の構築/更新/保持費用を含める。collector合計予算の評価を先に完結する順序は維持する。 / Extend the existing correction-dependency pilot with affected joint rows, bindings, support and provenance. Cover new combinations and deletion/replacement; missing reverse references do not prove independence. Fall back on unknown dependencies, audit full results through subsequent learning/reload, and charge reverse-index costs. Keep collector-budget evaluation first. / 在现有修改依赖pilot比较受影响的联合行、绑定、支持数及来源，覆盖新组合和删除替换；缺少反向引用不证明无影响，未知依赖回退全重建；验证后续学习及恢复的完整结果并计入反向索引成本，仍先完成采样总预算评估。
- 🔴 [Later] **明示的制約による探索順序のpilot**。現在のplannerの前提・資源・禁止状態・依存競合を再利用し、未充足条件の内訳を持つ評価値で展開順序を変える。graphの既存energy履歴をそのまま正解判定や新しい目的関数と見なさない。まず固定遷移モデルで既存探索、手設計の評価値、学習した評価値を比較して探索効果を分離し、次にモデルも学習する条件を独立に測る。oracleの規則を使う条件は明示し、観測のみの学習と混同しない。 / Reuse planner preconditions, resources, forbidden states and threats to rank expansions with inspectable violation components. Existing graph energy history is not a correctness certificate. Compare current search, hand-designed and learned rankings under a fixed transition model before separately testing learned models; label oracle information explicitly. / 复用planner前提、资源、禁止状态及依赖冲突，以可检查的违约分项排序；现有graph energy不是正确性证书。先固定转移模型比较原搜索、手设和学习排序，再单独评估模型学习，并标明oracle信息。
- 🔴 [Later] **停止条件を正解検証から切り離さない**。低い評価値・局所停滞・訓練上の閾値到達だけでは成功としない。独立環境で計画を実行し、前提、資源、禁止状態、最終goal、joint witnessとidentityを確認する。到達可能性・最短計画・全候補列挙の契約を分け、実行可能解を得ても最適性や列挙完了を主張しない。予算切れ・局所停滞は未解決とし、再試行または既存探索へ戻す。正確な最適化として採用する場合はscore・順序・根拠を含む従来の完全結果と保存内容の一致を必須とする。 / Validate plans in an independent environment; low scores, stagnation and learned thresholds are not success proofs. Distinguish feasibility, optimality and enumeration contracts. Budget exhaustion remains unresolved; retry or fall back. Exact optimizations require full-result ordering, scores, provenance and persistence parity. / 在独立环境验证计划，低分、停滞及学习阈值不证明成功；区分可行性、最优性和枚举契约，预算耗尽仍是未解决并重试或回退；精确优化要求完整结果顺序、分数、来源及保存一致。
- 🔴 [Later] **高次の依存を消さない学習対照**。学習する評価値は探索順序の補助に限定して開始する。役割対を個別に満たすが同時には成立しない例、3者以上の依存、未知組合せ、解なし/複数解、少数のidentity反例を分けて評価する。pairwise表現で表せない条件はjoint制約として保持する。未観測の組合せを自動的に負例にせず、負例生成には既存の妥当性検証を使い、その費用も記録する。候補選択と閾値はdevelopmentに限定し、独立held-outを消費して調整しない。 / Start with learned ranking only. Test inseparable, higher-order and rare identity constraints, novel combinations and zero/multiple solutions. Retain joint constraints when pairwise factors are insufficient. Unobserved combinations are not automatically negative; validate generated negatives, charge that work and isolate development from held-out selection. / 学习评分先仅辅助排序，分别测试不可拆、高阶、稀有identity约束、未知组合及无解多解；pairwise不足时保留联合约束。未观测组合不自动作为负例，验证生成负例并计费，隔离development和留出选择。
- 🔴 [Later] **独立seed・同品質・総費用で判定**。既存探索と強い適用可能baselineを維持し、同じEvent、query、品質条件、予算で比較する。構築・学習・評価値更新・全探索鎖/再開始・検証・fallback・保存復元を含む総CPU/wall、p50/p95、保持/peakを記録する。cold/warmを別表にし、複数process/hash順序で未知worldと分布変化を測る。探索だけの高速化と学習済み構造の転用利益を分離し、単純な世界での成功をG4達成と扱わない。 / Compare independent seeds at matched data, quality and budgets against existing search and strong baselines. Charge training, score updates, all chains/restarts, verification, fallback and persistence; report CPU/wall, latency and memory with separate cold/warm results. Separate search efficiency from structural transfer and retain G4 gates. / 在同数据、质量及预算下以独立seed比较原搜索和强基线；计入训练、评分更新、全部搜索链及重启、验证、回退和持久化，分别报告冷暖耗时与内存；区分搜索效率和结构迁移，保留G4门槛。

今回の採用は既存pilotの評価要件と後続探索の設計。CRAM、energy学習、新しい停止器は未実装であり、速度改善も未測定。 / This update adopts evaluation requirements and future search design; CRAM, learned energies and new stopping rules are not implemented or benchmarked. / 本次采纳评估要求和后续搜索设计，尚未实现或测量CRAM、energy学习及新停止规则。


### Diagnosis-driven proposals and withdrawal — 2026-11-19

参考 / Source / 来源: [Language Models Can Rewrite Their Own Weights, arXiv:2611.21885v1](https://arxiv.org/html/2611.21885v1)（2026-11-16）。§2・Fig.1の設定では編集者はセッション中固定され、反復セッションは元の重みから始まる。損傷修復でも編集者は非損傷モデルである。これを累積的な自己改良やRISAの有効性の証明とは扱わない。 / In §2 and Fig.1, the editor stays fixed within a session and repeated sessions start from base weights; repair uses an undamaged editor. This does not establish cumulative self-improvement or RISA's effectiveness. / 第2节及图1中，编辑者在会话内固定，重复会话从基础权重开始，修复由未损坏模型编辑；这不证明累积自我改进或RISA的有效性。

以下はRISAへの独自の応用案。ニューラル重みの書換えを導入せず、既存の候補lifecycle・独立評価・撤回の計画を強化する。collector合計予算→訂正依存pilotの実行順序は変えない。 / The following are RISA-specific adaptations to candidate lifecycle, independent evaluation and withdrawal, not neural weight editing. Preserve collector-budget then correction-dependency priorities. / 以下为RISA候选生命周期、独立评估及撤回机制的应用方案，不引入神经权重编辑；保持采样总预算后修改依赖pilot的顺序。

- 🟠 [Next] **既存pilotのpaired監査を具体化**。同一snapshotから分離したstate、同一Event/query列・seed・予算を用い、変更前後の完全結果、根拠、保存復元を比較する。不一致は平均精度に集約せず、誤→正、正→誤、予算切れ、正当な棄却、未完了を区別する。独立world/episodeを統計単位とし、同じ問題のseed違いを独立問題として数えない。全試行・撤回・無変更・失敗も記録する。これは既存の完全一致要件の具体化であり、新規の優先課題を追加するものではない。 / Specify matched independent states, streams, seeds and budgets in existing pilots. Audit full results, provenance and persistence; distinguish improvements, regressions, exhausted budgets, valid abstention and unfinished work. Use independent worlds/episodes as statistical units, not repeated seeds of one problem. Record every trial, withdrawal, no-op and failure. / 在现有pilot固定独立state、相同流、seed及预算，审计完整结果、来源和保存；区分改善、退化、预算耗尽、有效弃答和未完成，以独立world/episode为统计单位而非同题重复seed；记录全部试验、撤回、无修改及失败，不新增优先任务。
- 🔴 [Later] **診断→限定した変更案→採用または撤回**。G3.4で候補の有効な採用機会を確認した後、既存specialize/merge/dormant機構で扱える変更だけを独立コピーに提案する。診断は失敗した役割対・identity・context・支持Eventへ遡り、頻度や相関だけで証拠を削除しない。比較対象は無変更、既存の決定的規則、同予算の診断を使わない提案とする。候補ID・親/祖先・証拠・変更差分・消費した評価ID・費用・採否理由を記録する。採用gate、評価器、原Eventは提案側から変更させず、効果不明は無変更とし、G3.2の負の結果を維持する。 / After demonstrated G3.4 opportunity, propose bounded changes on copies through existing specialization, merge and dormancy mechanisms. Trace failures to bindings, context and evidence. Compare no-op, deterministic rules and equal-budget proposals without diagnosis. Record lineage, evidence, diffs, evaluation IDs, cost and decisions; keep evaluators, adoption gates and source Events outside the proposal's mutable scope. Unknown benefit means no change. / G3.4确认机会后，利用现有特化、合并和休眠机制在副本提出有限修改，追溯失败绑定、上下文及证据；比较无修改、确定规则和同预算无诊断提案；记录谱系、证据、差异、评估ID、成本及决策，提案不得修改评估器、采纳门槛或原Event，不明收益保持原状。
- 🔴 [Later] **提案・採用検証・finalを分離**。候補生成用development、採用判断用の独立episode、最終報告用held-outを分ける。採用判定結果も適応的な情報になるため、検証の再利用回数・総試行数を制限して記録し、同じ検証setへ繰り返し合わせ込まない。上限と判定基準は事前固定する。finalは候補選択へ戻さない。未知組合せ・稀なidentity反例・保持すべき既存能力・A→B→Aを別々に報告し、平均改善で局所退化を隠さない。 / Separate proposal development, adoption episodes and final held-out reporting. Gate feedback is adaptive information: predeclare trial/reuse budgets and decision criteria, log all use and never tune on final tests. Report novel combinations, rare identity counterexamples, retention and A→B→A separately. / 隔离提案development、采纳episode及最终留出；门槛反馈也属于适应性信息，预先限定并记录试验及复用预算和判定标准，不用final调参，分别报告未知组合、稀有identity反例、保持和A→B→A。
- 🔴 [Later] **元状態からの再選択と累積変更を別実験にする**。毎回同じsnapshotから候補を作る条件と、直前の採用状態から次の候補を作る条件を分離する。累積条件では元状態と直前状態の双方に対して保持・改善・祖先を確認し、複数世代の未見episodeで追加利益がなければ再帰的改善とは呼ばない。各状態自身の保存復元一致と撤回時の復元を検証する。品質を変える候補の前後は差分を測り、正確なindex最適化の完全一致契約と混同しない。探索・棄却・検証・rollback・再構築を含む総費用と、採用後queryの費用を分けて費用回収を測る。 / Separate repeated selection from a fixed snapshot and cumulative edits from the last adopted state. Audit retention against both initial and previous states and require new independent episodes across generations before claiming recursive improvement. Verify persistence/rollback fidelity; distinguish quality-changing proposals from exact index optimizations. Include all rejected work and maintenance in payback. / 分开固定snapshot重复选择与基于上次采纳状态的累积修改；相对初始和前一状态检查保持，跨世代独立episode有额外收益才称递归改善；验证持久化及撤回，区分质量变化提案和精确index优化，回本计入全部拒绝工作及维护。
- 🔴 [Later] **損傷修復は再構築baselineと比較**。派生indexやcacheへ実験用の故障を注入する場合は原Eventを保持し、正規の全再構築・checkpoint復元を必ず対照にする。壊れた状態からの回復と、健全な状態を超える改善を別々に測る。修復の成功を構造発見の成功に数えず、再構築より診断修復が有利になる条件がなければ追加機構を採用しない。 / For derived-index/cache fault experiments, preserve source Events and compare canonical rebuild and checkpoint restoration. Recovery from damage is distinct from improvement beyond a healthy baseline and is not evidence of structural discovery. / 派生index/cache故障实验保留原Event，以全重建和checkpoint恢复为对照；损伤恢复不同于超过健全基线的改善，不作为结构发现证据，无净收益则不采纳额外修复机制。

今回は設計・評価計画の統合のみ。自動診断による新しい変更器や自己書換えは未実装であり、性能改善を主張しない。 / Planning integration only; no new diagnostic editor or self-rewriting mechanism is implemented, and no performance gain is claimed. / 本次仅整合设计和评估计划，未实现新诊断编辑器或自我改写机制，不宣称性能提升。


### Aggregate collector budget and lazy RNG — 2026-11-19

- 🟢 [Done] [全Primitive収集予算の実装・比較](G3.4-Grounding-Collector-Budget-2026-11-19.md)。`budget_bytes`・先着`max_streams`をwindow/scheduleへ追加。保持対象・一時peakを分離し、超過時は直前状態へ戻して収集を停止。通常queryと保存形式は維持。 / Implement explicit aggregate retained-byte and key caps with rollback/freeze and separate peak accounting; preserve normal queries and persistence. / 实现显式保留字节总上限和key上限，超限回滚冻结并区分峰值，保持常规query及保存格式。
- 🟢 [Done] RNGを最初の置換まで遅延生成。多数短列で保持量60.3%減、CPU中央値比79.5%減、標本一致。6 process・3 hash seed・36軌跡の52,992監査ケース、144 checkpoint、180保存/復元一致。 / Lazy RNG preserves samples and cuts many-short-stream memory 60.3% and median CPU ratio 79.5%; six-process full-result/persistence audit passes. / 延迟RNG保持样本，大量短流内存减少60.3%、CPU中位数比减少79.5%，六process完整结果及保存审计通过。
- 🟢 [Done] 総予算方式の制約を測定。4,096-byte capは全108windowで停止しTV最大0.989。32,768-byte capは少数長列で全量計量・試行コピーにより悪化。総予算方式の既定化は見送り、乱数遅延化だけを既存collectorへ適用。 / Measure capped coverage loss and expensive ongoing accounting; keep caps opt-in and apply only lazy RNG to existing collectors. / 测量限额覆盖损失及持续计量高成本，上限保持显式启用，仅延迟RNG应用于现有采集器。
- 🟢 [Done] [同予算の後半query収集比較](G3.4-Grounding-Recent-2026-11-19.md)を実施。品質改善と費用増を分けて確認し、残る費用削減を末尾のNextへ移す。 / Complete matched-budget late-query comparison; move remaining cost reduction to the latest Next item. / 已完成同预算后段query比较，区分质量改善和成本增加，后续降本移至末尾Next。

- 🟢 [Done] 全337テスト成功（49.97秒）、`git diff --check`通過。 / All 337 tests pass (49.97 s); diff whitespace checks pass. / 全337测试通过（49.97秒），差异空白检查通过。


### Conservative collector headroom — 2026-11-19

- 🟢 [Done] [差分計量と同予算比較](G3.4-Grounding-Collector-Accounting-2026-11-19.md): 共有payloadの解放分を差し引かない保守的な上界を使い、余裕がある既存streamの全量走査・試行コピーを省略。新規stream・RNG初期化・skip更新・予算付近は従来の厳密処理へ戻す。 / Conservative headroom avoids full scans/copies without subtracting shared removals; uncertain growth uses exact trial accounting. / 保守余量不减去共享释放量，省略全扫描及复制；增长不确定时回退精确试验计量。
- 🟢 [Done] 341テスト成功（130.24秒）、最終対照実装で関連12テストも成功。同予算で標本・件数・停止位置と保持量上限を検証。 / All 341 tests pass; 12 targeted tests also pass with the final reference implementation, verifying samples, counts, stopping and memory bounds. / 341测试通过，最终对照实现的12个相关测试也通过，验证样本、计数、停止及内存上限。
- 🟢 [Done] [同予算の後半query収集比較](G3.4-Grounding-Recent-2026-11-19.md)を実施。品質改善と費用増を分けて確認し、残る費用削減を末尾のNextへ移す。 / Complete matched-budget late-query comparison; move remaining cost reduction to the latest Next item. / 已完成同预算后段query比较，区分质量改善和成本增加，后续降本移至末尾Next。

- 🟢 [Done] 同一32,768-byte予算で少数長列の収集CPU中央値比88.2%減、全体の対応CPU比中央値0.428（36/36改善）。4,096-byte条件は0.993で安定優位なし。6 process・3 hash seed、54,528監査ケース・144 checkpoint・216保存/復元一致、標本/TV/停止状態も一致。保持量は同じ。 / Matched-byte long-stream collector CPU ratio falls 88.2%; charged-world paired median is 0.428, with unchanged samples and retained bytes. Tight-budget performance is inconclusive; full-result and persistence audits pass. / 同字节预算长流采样CPU中位数比减少88.2%，整体配对中位比0.428，样本及保留量不变；紧预算无稳定收益，完整结果及保存审计通过。


### Budgeted late-query collection — 2026-11-19

- 🟢 [Done] [最近のjoint witness収集](G3.4-Grounding-Recent-2026-11-19.md): `policy='recent'`をwindow/scheduleへ追加。同じbyte上限内で古いPrimitiveを退避して収集を続ける。過大な単一標本は元状態を壊さず見送り、役割・identityを一体で保持。通常query・保存形式は維持。 / Add opt-in recent collection with joint bindings, LRU key eviction and atomic oversized rejection under the same byte cap. / 添加显式近期采集，联合绑定、LRU key退避及过大观察原子拒绝，保持同字节上限。
- 🟢 [Done] 6 process・3 hash seedで同予算比較。後半TVはbinding変化4KiBで1→0、key変化32KiBで1→0.0625。全区間の代表性は悪化する条件もあり、一様reservoirと区別。 / Tail quality improves in shift cases but full-window representation can worsen; recent is not uniform sampling. / 变化条件下后段质量改善，但全窗口代表性可能恶化，近期采集并非均匀采样。
- 🟢 [Done] 保存/loadを含む総CPU比中央値は4KiBで1.866、32KiBで1.151。速度優位は未確認のため明示opt-in。全347テスト、54,528監査ケース、144 checkpoint、216保存/復元一致。 / Total CPU including save/load rises; retain opt-in. All 347 tests and full-result/persistence audits pass. / 含保存加载的总CPU增加，保持显式启用；347测试及完整结果/保存审计通过。
- 🟢 [Done] [recent費用比較](G3.4-Grounding-Recent-Cost-2026-11-19.md)で同品質・同byte予算の重複計量削減を検証。新規key退避の追加最適化はLaterへ分離し、訂正依存pilotへ進む。 / Validate duplicate-accounting reduction at matched quality/bytes; defer further churn optimization and proceed to correction dependencies. / 已验证同质量同预算下减少重复计量，额外新key优化列Later，进入修改依赖pilot。


### Guarded recent accounting — 2026-11-19

- 🟢 [Done] [recent計量の重複削減](G3.4-Grounding-Recent-Cost-2026-11-19.md)。余裕のある既存keyでは全体の計量1回で受理し、overflow時も候補が変わるまでは計量結果を再利用。小予算の悪化を測定したため、保持量が予算の半分以下の条件に限定するガードを追加。 / Deduplicate existing-key accounting, reuse valid overflow counts, and guard by half-budget headroom after measuring tight-budget regressions. / 减少现有key重复计量并复用有效overflow结果，测量紧预算退化后增加半预算余量保护。
- 🟢 [Done] 同品質・同予算で32KiB総CPU比中央値0.801（30/36改善）、4KiBは1.007で安定優位なし。6 process・3 hash seed、54,528監査ケース・144 checkpoint・216保存/復元一致。標本/TV/保持量も一致し、通常queryの既定は維持。 / Matched-quality 32KiB paired CPU median 0.801, tight-budget 1.007; full-result, sample and persistence audits pass. / 同质量32KiB配对CPU中位比0.801，紧预算1.007；完整结果、样本及保存审计通过。
- 🟠 [Next] 訂正依存pilot: Event→Primitive逆参照の費用を含め、訂正時の全再構築と影響先再構築を比較する。新規の組合せ・欠落参照・役割/identity変更・広い波及では安全な全再構築へ戻し、独立worldで完全結果/保存一致と総費用を検証する。 / Next compare full and dependency-scoped correction rebuilds, charging reverse references and falling back for uncertain dependencies. / 下一步比较全重建与修改依赖局部重建，计入反向引用费用，未知依赖回退全重建。
- 🔴 [Later] recentの新規key大量流入時の退避/コピー最適化と、別分布でのガード閾値検証。半予算の閾値は今回のdevelopment規則であり最適性や実運用の費用回収は未証明。 / Defer churn optimization and independent guard-threshold validation; the half-budget rule is a development heuristic. / 后续处理新key流入优化及独立阈值验证，半预算规则仅为development启发式。

- 🟢 [Done] 最終ガード付き実装で全351テスト成功（1397.95秒）。性能比較とは別実行。`git diff --check`通過。 / Final guarded implementation passes all 351 tests in a separate run; diff check passes. / 最终含保护实现独立运行通过351测试，差异检查通过。


### Interpretable specifications and reconstruction audits — 2026-11-22

参考 / Source / 来源: [Interpretable weight-space programming builds transparent transformers and brain encoding models, arXiv:2611.18114v1](https://arxiv.org/html/2611.18114v1)（2026-11-13）。§2の固定評価器と説明からの再構築、§4.2の交絡診断を研究入力に採用する。論文の再構築は主に予測性能の再現であり、厳密な意味同値や因果機構の証明ではない。神経encodingでは評価器がreadoutをfitしているため、全工程を学習不要とは扱わない。 / Adopt fixed evaluation, description-based reconstruction and confound diagnosis as research inputs, not proofs of exact semantic or causal equivalence. Neural encoding includes fitted readouts. / 采纳固定评估、描述重建及混杂诊断作为研究输入，不视为精确语义或因果等价证明；神经encoding包含readout拟合。

以下はRISA独自の研究・実装対象。既定の訂正依存pilotを最優先とし、ニューラル重みの直接生成を現行記号系へ移植しない。 / The following are RISA-specific research and implementation targets. Keep the correction-dependency pilot first; do not transplant neural weight generation into the current symbolic system. / 以下为RISA研究及实现目标，仍优先修改依赖pilot，不将神经权重生成直接移植至当前符号系统。

- 🟠 [Next] **訂正依存pilotの検証可能な仕様と反例監査**。再構築対象を決める根拠をEvent参照、役割対、identity、joint witness、候補lineageまで辿れる診断出力として定義する。既存schemaを再利用し、自由記述だけを依存判定に使わない。意味を保つIDの一対一改名（全参照も更新）、無関係な格納順序変更、無関係なmetadata変更と、実際に意味を変える役割/identity訂正を分けてテストする。時間順序や意味のあるsource条件は無差別にshuffleしない。全再構築との完全結果・根拠・保存内容の一致と、診断出力の構築/保持費用を測る。 / Define auditable dependency diagnostics through Event references, role pairs, identity, joint witnesses and lineage using existing schemas. Distinguish semantics-preserving renaming/storage changes from real binding corrections; never blindly shuffle causal time or meaningful source conditions. Compare full results, provenance and persistence against full rebuilds and charge diagnostic costs. / 复用schema定义可追溯至Event、角色对、identity、联合证据及谱系的依赖诊断；区分保语义改名/存储变换与真实绑定修改，不随意打乱因果时间或有意义source；对照全重建验证结果、来源及保存，并计入诊断成本。
- 🔴 [Later] **候補の実行可能な仕様と独立再構築器**。訂正依存評価後、候補schemaから前提・効果・資源・役割/identity制約・適用範囲を出力し、別の小さな参照interpreterで再構築して評価する。serializerの往復だけでなく、推論実装を共有しない参照器との比較にする。自然言語説明だけからの再構築は別の解釈可能性実験とし、説明なし・条件を欠落させた説明を対照にする。英語/日本語/简体中文で表現差を調べ、文字数/bytes/使用tokenを報告する。説明が短い、または正解率が同じだけでは合格とせず、未知組合せ、稀なjoint反例、棄却、score・根拠の差も評価する。LLM判定は補助診断に限定する。 / After correction evaluation, export candidate preconditions, effects, resources, bindings and scope for a separate reference interpreter, not just a serialization round trip. Test natural-language reconstruction separately against no-description and missing-condition controls, with trilingual size accounting. Short text or equal aggregate accuracy is insufficient; audit unseen combinations, rare joint counterexamples, abstention, scores and evidence. LLM judgment is supplementary. / 修改依赖评估后导出候选前提、效果、资源、绑定及范围，使用独立参照解释器而非仅序列化往返。自然语言重建另设无描述及缺条件对照，统计三语长度；短文本或平均准确率相同不足以通过，还需审计未知组合、稀有联合反例、弃答、分数及证据，LLM评判仅辅助。
- 🔴 [Later] **説明可能な候補提案を既存lifecycleへ接続**。11月19日の診断→提案→撤回計画へ統合し、固定した型付きschema/許可演算の範囲で候補を生成する。提案器は評価器、原Event、採用gateを変更できない契約とする。人手の規則、決定的探索、LLM提案を同じ入力・評価予算で比較し、外部から与えたアルゴリズム/知識とEventから獲得した構造を記録上分離する。既知手法の再実装をG4の再帰的概念獲得と数えない。生成・選別・独立検証・棄却・説明監査・保存の全費用と、失敗/無変更の全試行を記録する。API/GPUを要する実験は必要になってから環境可否を判定し、未着手だけでPendingにしない。 / Integrate typed, bounded proposals into the existing diagnosis/proposal/withdrawal plan. Keep evaluators, source Events and gates immutable to the proposer. Compare human rules, deterministic search and LLM proposals at matched budgets; distinguish supplied knowledge from Event-derived structure and do not label known-algorithm reimplementation as G4 discovery. Charge all trials, audits and persistence. / 将有类型、受限的提案纳入既有诊断/提案/撤回计划，提案器不能修改评估器、原Event及门槛；同预算比较人工规则、确定搜索和LLM，区分外部知识与Event获得结构，已知算法重写不计为G4发现；计入全部试验、审计及保存费用。
- 🔴 [Later] **交絡を崩す転用と、品質通過後の簡素化**。既存G3.4 source交絡の負の結果を保持し、episode境界・入力長・nuisance tag・IDなどだけのbaselineを設ける。候補選択はdevelopmentに限定し、本来の役割/identity構造を維持したままproxy相関だけを崩した独立worldで最終評価する。probeや正解ラベルを学習入力へ混入させない。候補を簡素化する場合は先に意味・品質条件を満たし、その後にschemaサイズだけでなく例外表・根拠・実保存bytes・実行時間を比較する。予測改善、記述の簡潔さ、因果的な説明を別指標とし、説明の再構築成功だけで因果性を主張しない。 / Preserve G3.4's negative source-confounding result. Add nuisance-only controls and break proxy correlations in independent worlds while retaining true binding structure; keep final probes outside selection/training. Simplify only after semantic/quality gates, counting exceptions, evidence, stored bytes and execution cost. Distinguish prediction, concise description and causal explanation. / 保留G3.4 source混杂负面结果，设置仅干扰变量的对照，在独立world保留真实绑定结构并打破proxy相关，final probe不进入选择或学习；语义及质量通过后再简化，计入例外、证据、保存字节和运行成本，区分预测、简洁描述及因果解释。

今回の変更は研究・実装対象と検証条件の追加。新しい提案器、参照interpreter、説明再構築実験は未実装であり、性能改善やG4達成を主張しない。 / This update adds targets and evaluation requirements, not implemented proposers, reference interpreters or reconstruction experiments; no performance or G4 success is claimed. / 本次新增目标及验证要求，尚未实现新提案器、参照解释器或描述重建实验，不宣称性能改善或G4完成。


### Reproducible population search and outcome costs — 2026-11-23

参考 / Source / 来源: [Evolution Strategies at Scale: LLM Fine-Tuning Beyond Reinforcement Learning, arXiv:2509.24372v3](https://arxiv.org/html/2509.24372v3)（v3: 2026-07-14）。§3のseedによる候補再現と集団評価を参考にする。ただしAppendix A.7は評価集合に基づくcheckpoint選択を含み、A.8のFLOPs比較は1 sample評価の見積もりである。RISAの独立finalや同品質までの総費用と同一視しない。 / Use seeded candidate reconstruction and population evaluation as inspiration; A.7 includes evaluation-set checkpoint selection and A.8 estimates per-sample FLOPs, neither equivalent to RISA's independent final or total cost to quality. / 参考seed重建和群体评估；A.7包含基于评估集的checkpoint选择，A.8估计单sample FLOPs，不等同于RISA独立final或同质量总成本。

適用範囲 / Scope / 范围: 現行RISAは記号的なEvent/Primitive系。以下は独自の応用案であり、LLM全重みへのESの成果を移植したものではない。訂正依存pilotを最優先のまま維持する。 / These are adaptations to symbolic RISA, not transferred full-weight LLM results. Keep the correction-dependency pilot first. / 以下为符号RISA的应用方案，并非直接移植LLM全权重ES成果，仍优先修改依赖pilot。

- 🟠 [Next] **訂正manifestの拡張検証**（2026-11-24に旧値/新値と別state再生を実装。変更→復元→同変更再実行、追加/削除を含む拡張は残る）。生成worldのseedだけでなく、生成器/RNGの版、入力snapshotのdigest、変更Event ID・項目・旧値/新値、実行順序を記録し、全再構築と部分再構築に同じ訂正列を与える。正規のEvent・根拠をseedに置き換えて削除しない。変化を再生成できても旧状態の完全復元は別問題なので、不変snapshotまたは旧値の明示差分から復元し、加算後の減算だけを完全一致の根拠としない。未変更条件、変更→復元→再実行を含めて完全結果・保存内容・校正の無効化範囲と、manifest/復元の費用を測る。 / Extend correction pilots with generator/RNG version, input digest, explicit Event field edits and order, not seeds alone. Preserve authoritative evidence; restore immutable snapshots or recorded old values rather than assuming arithmetic inversion is exact. Audit no-op and correction/restore/replay cases, calibration invalidation and total manifest/restore cost. / 修改pilot记录生成器/RNG版本、输入摘要、Event字段旧新值及顺序，而非仅seed；保留权威证据，以不变snapshot或旧值恢复，不假定算术逆运算精确；审计无修改、修改恢复重放、校准失效范围及总费用。
- 🔴 [Later] **小規模な非微分設定探索を固定規則と比較**。訂正依存評価後、必要性が確認されたcollector配分・収集周期・再配置条件の少数パラメータだけを対象に、固定規則、同予算random/grid search、ES型の候補集団を比較する。整数・範囲・列挙型を検証し、離散schemaやjoint bindingを数値平均しない。Event、証拠、意味判定、採用gateは探索対象から除外する。候補は同じ過去区間と独立stateで評価し、未知の次区間・別worldで費用回収を確認する。更新機会がない設定や定数rewardも含め、標準偏差0での正規化は更新しない等の処理を事前固定する。 / After correction evaluation, compare fixed rules, matched-budget random/grid search and ES-like populations over a few justified execution-policy parameters. Validate discrete domains; never average schemas/bindings or optimize evidence/semantic gates. Use matched historical windows and independent states, then new windows/worlds for payback. Predefine constant-reward and no-op behavior. / 修改评估后，针对少量必要的执行策略参数比较固定规则、同预算random/grid及ES式群体；校验离散域，不平均schema/绑定，不优化证据或语义门槛；使用相同历史窗口及独立state，再在新窗口/world验证回本，并预定恒定reward和无操作处理。
- 🔴 [Later] **集団評価でも意味・品質を先に固定**。完全結果/保存一致に失敗した実行設定を速度rewardで救済しない。候補生成・探索深さ・Replay量を変える研究は別の品質変化実験とし、棄却/未完了/無解の区別、稀な役割/identity反例、保持、未知組合せのgateを先に定義する。候補周辺の小変更への安定性も測るが、集団平均が良いことをreward hackingや局所退化の不存在としない。候補選択・試行回数・閾値調整はdevelopment内、finalは選択へ戻さない。 / Exact-result/persistence failures cannot be compensated by speed reward. Treat search/Replay changes as separate quality experiments with preregistered abstention, binding, retention and composition gates. Measure neighborhood stability without assuming population averages prevent reward hacking. Keep all selection/tuning in development. / 结果或保存不一致不能由速度reward抵消；搜索/Replay变更属于独立质量实验，预定弃答、绑定、保持及组合门槛；测量邻域稳定性但不认为群体平均能排除reward hacking，选择调参限于development。
- 🔴 [Later] **再現性と総費用を集団全体で計測**。seedの派生を候補ID・パラメータ群ごとに固定し、同じseedの不用意な再初期化による相関を区別する。候補生成seedと評価world seedを分離し、worker完了順・process/hash順序を変えて再現性を監査する。候補生成、全個体のquery、失敗候補、snapshot複製/復元、集約・通信、最終検証を含む総CPU/wallとpeakを測り、並列での経過時間短縮と総計算量削減を分ける。集団サイズや世代数は論文の値を固定採用せず、等評価回数および等総費用の対照で決める。 / Derive independent candidate/parameter-group seeds and separate them from evaluation seeds; audit worker/hash-order effects. Charge every candidate, failed trial, copy/restore, aggregation, communication and validation. Distinguish parallel latency from total compute and compare both evaluation-count and total-cost budgets rather than importing population sizes. / 固定候选及参数组seed派生并与评估seed分离，审计worker/hash顺序；计入全部候选、失败、复制恢复、聚合通信及验证，区分并行耗时和总计算量，以同评估次数及同总成本比较，不直接沿用论文群体规模。

全パラメータLLM調整はG4後にadapter学習が本当に必要な場合のLater候補へ限定する。今回の変更は研究・実装計画の統合のみで、新しいES最適化器や自動設定変更は未実装。 / Full-weight LLM tuning remains a post-G4 adapter option only if needed. This is planning integration; no ES optimizer or automatic configuration changes are implemented. / 全参数LLM调整仅作为G4后确需adapter学习时的Later候选；本次仅整合计划，未实现ES优化器或自动配置变更。
