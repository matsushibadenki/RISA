# RISA Roadmap / RISA ロードマップ / RISA 路线图

Updated: 2026-09-05. [Design assessment / 設計評価 / 设计评估](RISA-Structural-AI-Assessment-2026-09-05.md)

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

日本語: [Done]は実装の存在を示し、研究仮説の実証とは区別する。直近はG0、次いでG1。
G2以降は重要でも[Later]とする。指標・閾値は評価前に固定し、結果を見て合格条件を緩めない。

English: [Done] means implemented, not scientifically validated. Execute G0 then G1; G2 onward is [Later].
Freeze metrics and thresholds before evaluation; do not relax gates after seeing results.

简体中文: [Done]表示已实现，不等于科学验证。先执行G0，再执行G1；G2以后标为[Later]。
评估前固定指标与阈值，不根据结果放宽通过条件。

## Current baseline / 現在地 / 当前基础

| Status | 日本語 | English | 简体中文 |
| --- | --- | --- | --- |
| [Done] | 構造化Event、頻度学習、グラフ、簡易概念、Primitive、JSON保存 | Structured events, counts, graph, simple concepts, primitives, JSON persistence | 结构化事件、频度学习、图、简单概念、原语及JSON保存 |
| [Done] | 学習前予測、誤差履歴、共活性、代謝、Replay、文脈分裂の最小経路 | Minimal pre-update prediction, error history, coactivation, metabolism, replay, context splitting | 最小学前预测、误差历史、共激活、代谢、重放与上下文分裂 |
| [Done] | 状態消費・排他更新・数値資源・単位と上下限の部品 | Consumption, exclusive replacement, numeric resources, units and bounds | 状态消耗、互斥替换、数值资源、单位与边界 |
| [Done] | 分岐simulation、goal/constraint評価、what-if、AND/OR、偏序実行、threat検出 | Branch simulation, goal/constraint evaluation, what-if, AND/OR, partial-order execution, threats | 分支模拟、目标与约束评估、假设比较、AND/OR、偏序执行及冲突检测 |
| [Done] | 既存55テストと今回の6診断。複数effectとReplay整合性に欠陥を確認 | 55 existing tests and six assessment probes; joint-effect and replay defects identified | 现有55项测试与六项诊断；发现多效果与重放一致性缺陷 |

日本語: 「全経路で統一状態遷移が完成」という旧記述は撤回する。単一effectを中心とした部品は動くが、
同時effectとReplay分岐を含む契約はG0未完了。役割誘導・構造汎化・局所計算量・因果同定の優位性は未測定。

English: Retract the earlier claim of complete shared transition semantics. Single-effect components work, but
joint effects and replay branches remain unfinished G0 work. Role induction, structural transfer, computational
locality, and causal identification advantages have not been measured.

简体中文: 撤回此前“所有路径已完成统一转移语义”的表述。单效果部件可运行，但同时效果与重放分支仍属于G0未完成工作。
角色归纳、结构迁移、计算局部性及因果同定优势尚未测量。

## G0 — Semantic and evidence integrity / 意味論と証拠の修正 / 语义与证据修正

| Status | 日本語 | English | 简体中文 |
| --- | --- | --- | --- |
| [Next] | G0.1 同時effectの束と別outcomeを分離。deltaは一回適用。単一output形式を移行 | Separate joint effects from alternative outcomes; apply deltas once; migrate legacy output | 区分同时效果与备选结果，变化量只应用一次，迁移旧输出格式 |
| [Next] | G0.2 純粋transition関数を共有し、Replayも状態・資源・根拠をbranch別保持 | Share a pure transition kernel; preserve per-branch replay states, resources, evidence | 共享纯转移函数，重放逐分支保存状态、资源与证据 |
| [Next] | G0.3 Event ID冪等性、訂正、episode境界、遅着・順序契約を実装 | Implement event idempotency, corrections, episode boundaries, late-arrival ordering | 实现事件幂等、更正、回合边界及迟到事件顺序契约 |
| [Next] | G0.4 根拠なしactionの棄却、観測/導出/仮説の説明区分、actor/targetの具体照合 | Abstain on unsupported actions; distinguish observed/derived/hypothetical evidence; match actor/target | 对无依据动作弃答，区分观测/推导/假设，匹配actor与target |
| [Next] | G0.5 schema version、原子的保存、旧state移行と復旧検証 | Version schemas, save atomically, verify migration and recovery | schema版本化、原子保存、迁移与恢复验证 |

日本語: 順序はG0.1→G0.2→G0.3→G0.4→G0.5。各変更で既存テストと反例を回帰テスト化して実行する。
完了条件は、同時effectと一回のcost、排他outcomeの非混合、重複入力no-op、target区別、
存在する根拠への説明参照、保存復元後の同一結果をすべて確認すること。完全観測では集合一致を測り、
部分観測にはmaskを要求する。既存データから同時性を復元できない場合は推測移行せず、要再学習と明示する。

English: Implement G0.1–G0.5 in order, turning the counterexamples into regression tests alongside existing tests.
Pass only when joint effects/cost-once, isolated outcomes, duplicate no-op, target distinction, traceable explanations,
and persistence round trips hold. Use set equality for complete observations and masks for partial ones.
Mark ambiguous legacy data for retraining instead of guessing joint effects.

简体中文: 按G0.1至G0.5实施，将反例转为回归测试并运行现有测试。
通过条件包括同时效果与单次成本、结果隔离、重复输入无变化、target区分、可追溯解释及保存恢复一致性。
完整观测使用集合一致，部分观测使用mask；无法恢复同时性的旧数据应标记需重新训练。

## G1 — Comparative evaluation / 比較評価基盤 / 比较评估基础

| Status | 日本語 | English | 简体中文 |
| --- | --- | --- | --- |
| [Next] | G1.1 独立した人工環境、generator、split manifest、seedと予算を固定 | Freeze independent environment, generator, splits, seeds, budgets | 固定独立环境、生成器、划分、种子与预算 |
| [Next] | G1.2 頻度、完全事例検索、具体遷移表＋同一plannerのbaseline | Frequency, exact retrieval, grounded transition table with the same planner | 频度、完整案例检索、具体转移表加同一规划器基线 |
| [Next] | G1.3 構造共有、共活性、Replay、代謝、分裂を個別無効化 | Individually ablate sharing, coactivation, replay, metabolism, splitting | 分别消融结构共享、共激活、重放、代谢与分裂 |
| [Next] | G1.4 学習前次状態精度、完全goal到達、棄却、忘却、時間とmemoryを記録 | Record pre-update state accuracy, complete goal success, abstention, forgetting, time and memory | 记录学前状态精度、完整目标成功、弃答、遗忘、时间与内存 |

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

日本語: G1完了は、全方式・全splitの再現可能な結果表と失敗例が揃うこと。RISAの勝利は完了条件ではない。
優位性がなければ、その事実を次の設計入力にする。

English: G1 passes when reproducible comparative tables and failure cases exist. RISA need not win; null results guide design.

简体中文: G1完成条件是可复现的完整比较结果与失败案例，不要求RISA获胜；无优势也是设计依据。

## G2 — Learned structural reuse / 学習された構造再利用 / 学习型结构复用

- [Later] 型付き関係と役割束縛 / Typed relations and role bindings / 类型化关系与角色绑定
- [Later] 前後観測・失敗例から前提候補を比較 / Compare preconditions from before/after and failures / 从前后观测与失败比较前提候选
- [Later] 観測順序と適用条件を分離し、未観測合成を独立環境で検証 / Separate observed order from applicability and validate novel compositions / 分离观测顺序与适用性，验证新组合
- [Later] 共有schema＋束縛＋例外の記述長とheld-out予測改善で採用 / Adopt using schema/binding/exception length and held-out gain / 按schema、绑定、例外描述长度与留出收益采纳

日本語: G0/G1後、構造共有なし・具体遷移表との比較を固定plannerで実施する。最終採用の初期閾値は、
compositionとbindingの両方で最強の適用可能baselineより成功率が5ポイント以上高く、差の95%区間下限が0超、
同じ上限予算を守り、既知課題の低下が2ポイント以内であること。閾値は実験前の設計値で、測定結果ではない。
満たさない場合はfailureを一つ選んで改訂し、2回の事前登録比較でも改善しなければ役割表現・共有単位を再検討する。
自動schema獲得が勝てなければ、明示schemaを使う説明可能な記憶・計画部品へ用途を絞る。

English: After G0/G1, hold the planner fixed. Initial adoption gate: at least +5 percentage points over the strongest
applicable baseline on both composition and binding, a positive lower 95% bound for the difference, equal budget caps,
and no more than 2 points of loss on familiar tasks. These are prospective thresholds, not results.
After two preregistered revisions without improvement, reconsider bindings/sharing; if schema induction adds no value,
narrow the product to explainable memory/planning with supplied schemas.

简体中文: G0/G1后固定规划器。初始采纳条件：组合与绑定任务均超过最强适用基线至少5个百分点，
差值95%区间下限大于0，遵守相同预算上限，已知任务下降不超过2个百分点。以上是预设门槛，不是实测结果。
两轮预注册改订后仍无改善，则重新考虑绑定与共享表示；自动schema归纳无收益时，收敛为使用显式schema的可解释记忆与规划组件。

## G3 — Adaptation and bounded cost / 継続適応と計算予算 / 持续适应与计算预算

- [Later] 文脈分裂・統合・休眠の個別効果をdrift評価 / Measure splitting/merging/dormancy under drift / 在漂移中分别评估分裂、合并与休眠
- [Later] action/effect/role/evidence索引と予算付きReplay / Action/effect/role/evidence indices and bounded replay / 动作、效果、角色、证据索引与有界重放
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

日本語: 外部入力境界は出典・confidence・episode・観測maskを持つEvent候補にする。英語・日本語・简体中文の
ラベルは表示と知覚adapterで扱い、内部IDと役割意味を翻訳依存にしない。新moduleはG1と同じ評価に接続し、
個別ablationの改善がある場合だけ採用する。現規模ではクラウド・VPS・DBの追加構築は必要ない。

English: External event candidates carry provenance, confidence, episode and observation masks. Support English,
Japanese and Simplified Chinese at display/perception boundaries; internal identities and roles must not depend on
translation. Adopt modules only after controlled gains. Current scale does not justify new cloud/VPS/DB infrastructure.

简体中文: 外部事件候选携带来源、置信度、回合与观测mask。显示与感知边界支持英语、日语与简体中文，内部ID与角色语义不依赖翻译。
新模块只有在受控比较取得收益后采纳。当前规模不需要新增云、VPS或数据库基础设施。
