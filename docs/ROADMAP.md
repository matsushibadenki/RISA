# RISA Roadmap / RISA ロードマップ / RISA 路线图

## Purpose / 目的 / 目的

このロードマップは、
RISA を
「実用的に動く最小コア」
から
「構造記憶と動的推論を備えた知能基盤」
へ育てるための段階整理です。

This roadmap organizes the path from
a practical minimal RISA core
to
a broader intelligence substrate with structural memory and dynamic inference.

这个路线图用于整理
RISA 从“可实际运行的最小核心”
发展到“具备结构记忆与动态推理能力的智能基础”
的步骤。

---

## Current Status / 現在地 / 当前状态

- [Done] 構造化イベントの学習、局所探索、概念生成、説明付き予測の最小ループ
- [Done] `recent_activity` / `energy` / `dormant` を使った最小の構造代謝
- [Done] `co_activates_with` による共活性の最小強化
- [Done] `co_activates_with` を予測説明経路へ反映
- [Done] `co_activates_with` を候補探索へ反映
- [Done] 共活性強度に応じた局所探索半径の最小制御
- [Done] 共有 action / effect による簡易概念統合
- [Done] 「構造保存だけでは知識創発は不十分」という課題を研究テーマとして明文化
- [Done] 文脈つき `StructuralPattern` を共有構造メモリとして導入
- [Done] `StructureDelta` を最小実装として保存開始
- [Done] 「概念 = 繰り返し再利用される内部構造」という設計原則を明文化
- [Done] 「独立 Verifier より、共鳴・競合・予測誤差で構造を選別する」という原則を明文化
- [Done] 学習前予測と観測結果の比較による局所予測検証履歴を最小実装として導入
- [Done] effect 単位の検証履歴を `Pattern` / `StructuralPattern` の安定性へ反映
- [Done] 競合履歴を `co_activates_with` の reliability / plasticity へ反映
- [Done] 現行世界モデルによる Event Replay と Primitive 再評価の最小ループ
- [Done] actor 別の自己生成状態を連鎖させる deployment Replay
- [Done] MVP-1 state transition semantics: 離散状態、消費、排他置換、量的資源、単位、上下限、原子的更新

### [Done] MVP-1 State Transition Semantics Milestone

日本語:
構造化Eventから、離散状態と量的状態を安全に更新し、Replay・forecast・Compositionで同じ意味論を共有する
最小実行基盤が完成した。

English:
The MVP-1 core now shares one state-transition semantics across replay, forecasting, and composition,
including discrete state, consumption, exclusive replacement, bounded numeric resources, and atomic updates.

简体中文:
MVP-1核心现已在重放、预测与组合中共享统一的状态转移语义，支持离散状态、状态消耗、排他替换、
有界数值资源与原子更新。

---

## Phase 1 / Phase 1 / 第一阶段

### [Next] Structural Memory as Long-Term Knowledge

日本語:
長期知識の保存基盤を
重みそのものではなく
外部化された構造記憶として設計する。

English:
Treat long-term knowledge as an externalized structural memory
rather than as opaque distributed weights.

简体中文:
将长期知识设计为外部化的结构记忆，
而不是不透明的分布式权重。

研究テーマ:

- [Next] 知識保存形式を学習器から切り離す
- [Next] `Knowledge = inference(Structure, Context)` の形で扱う
- [Later] 異なる学習器間で同じ構造基盤を共有する

### [Next] Structural Sharing and Knowledge Emergence

日本語:
構造を保存するだけではなく、
構造間で共有される
再利用可能パターンから
未知の関係を生成できるようにする。

English:
Go beyond storing structures
and enable reusable shared structural patterns
to generate previously unstored relations.

简体中文:
不仅要保存结构，
还要让结构之间共享可复用模式，
从而生成此前未显式存储的关系。

研究テーマ:

- [Next] 「保存した関係」ではなく「再利用可能な構造パターン」を知識単位として扱う
- [Done] 文脈つき再利用可能パターンを最小実装として学習・予測へ接続する
- [Done] 共有構造パターン同士の差分を `StructureDelta` として蓄積する
- [Next] 明示的な同型探索より先に、共有される局所関係単位の再利用を優先する
- [Next] 経験同士の共通部分と差分を、共有内部単位の重なりとして自然に得る設計へ寄せる
- [Next] 類似構造・上位構造・役割構造への波及更新を設計する
- [Next] 保存されていない関係を導けた時点を「知識創発」と定義する
- [Later] 構造的不変量
  例:
  `X -supports-> Y`
  のような役割パターン
  を抽出する

### [Next] Co-Activation-Guided Inference

日本語:
共活性した構造を
単なる記録ではなく、
局所探索と予測優先度に使う。

English:
Use co-activation traces
not only as memory records
but also as inference guidance.

简体中文:
将共活性痕迹
不仅作为记忆记录，
也作为推理引导。

研究テーマ:

- [Done] `co_activates_with` を説明経路に反映する
- [Done] `co_activates_with` を予測スコアに最小利用する
- [Done] `co_activates_with` を候補探索に使う
- [Done] 共活性を局所探索半径の最小制御に使う
- [Next] 共活性半径を文脈や信頼度に応じて適応化する

### [Later] Fractal Canopy Routing Experiment

日本語:
固定の木構造を知識分類として与えるのではなく、
`routing -> local processing -> integration`
という同じ局所計算則を複数スケールで再利用し、
問題ごとに探索深度と活性branchを変える。

English:
Reuse one local
`routing -> processing -> integration`
rule across scales, with adaptive depth and active branches,
rather than imposing a fixed knowledge taxonomy.

简体中文:
不预设固定知识分类树，
而是在多个尺度复用
`路由 -> 局部处理 -> 整合`
规则，并按问题动态调整深度与活跃分支。

研究テーマ:

- [Later] 同一query集合をflat local activation、固定階層routing、自己相似canopy routingで比較する
- [Later] easy queryは浅く、難問・新規問題は深くまたは複数branchへ進むadaptive stoppingを実装する
- [Later] `co_activates_with`、context、replay stabilityをrouter特徴として使い、全探索を避ける
- [Later] treeに閉じず、複数領域へ属する構造をsparse cross-linkで再利用する
- [Later] 頻繁に再利用されるrouteの成長、低利用branchの休眠、誤分岐branchのpruningをConcept Cell代謝と接続する
- [Later] 新branch追加時に既存queryの到達率・予測を壊さない継続学習テストを行う
- [Later] shallow/deep route間で同じ答えに至るconsistencyと、追加計算による改善量を測る
- [Later] Transformer側の実験は小規模encoderまたは既存model adapterで行い、RISAコアの前提条件にしない

最初の評価指標:

- holdout goal到達率または予測精度
- queryあたりの活性node数、探索edge数、推論時間
- easy/hard query別の平均探索深度
- 新規branch学習後の旧query回帰率
- routeと根拠構造の説明可能性

採用条件:

- flat local activationと同等以上の品質で探索量を削減する
- または同程度の計算量で未知構造へのgeneralizationを改善する
- 木構造の固定分類に退化せず、cross-linkと文脈別routeを保持できる

この実験はFractalNetの自己相似subpathとanytime性、Mixture-of-Depthsの動的計算配分から着想を得ます。ただし、
学習後のbranch自律成長やConcept Cell代謝への接続はRISA独自の未検証仮説として扱います。

参考一次資料:

- [FractalNet: Ultra-Deep Neural Networks without Residuals](https://arxiv.org/abs/1605.07648)
- [Mixture-of-Depths: Dynamically allocating compute in transformer-based language models](https://arxiv.org/abs/2404.02258)

### [Next] Hierarchical Local Credit Assignment

日本語:
global gradient Backpropagationを必須にせず、
局所活動、時間、階層構造、outcome modulationから、
どの構造が結果へ寄与したかを逆向きに割り当てる。

English:
Assign outcome credit backward through local activity traces,
time, and hierarchy without requiring global end-to-end gradients.

简体中文:
无需依赖全局端到端梯度，
通过局部活动轨迹、时间与层级结构反向分配结果信用。

研究テーマ:

- [Next] Event/Primitive/Concept Cellごとに有限長のactivity traceと親子branch traceを保持する
- [Next] outcome発生時に、直近のactive subgraphだけへcredit packetを逆向き伝播する
- [Next] `activity * temporal proximity * contribution * modulation * novelty`を分解記録する
- [Next] 成功強化、失敗弱化、未関与branch無更新の三状態を最小局所則として実装する
- [Next] delayed reward課題でeligibility trace長とcredit減衰を比較する
- [Later] STDP型時間窓、bAP型branch通知、neuromodulation型global scalarを個別ablationする
- [Later] 局所strength更新と、接続・pruning・branch growthのtopology更新を分離する
- [Later] Fractal Canopyのroot-to-leaf活動履歴をcredit routing indexとして利用する
- [Later] replay時に過去traceへcreditを再配分し、online時との整合性を検証する
- [Later] credit競合時の総量制約とhomeostatic normalizationを導入する
- [Next] `LocalUnit`のactivity、eligibility、threshold、context、structural budgetを明示型として定義する
- [Later] 同じ`process -> integrate -> feedback -> plasticity` protocolをbranch、unit、moduleの三尺度で再利用する
- [Later] flat、固定canopy、局所則で成長するcanopyを同じevent課題で比較する
- [Later] 形を誘導せずに、再利用・局所credit・接続costだけから樹状構造が創発するか観測する
- [Later] fast activity、eligibility、strength、topologyの更新時間スケールを分離する
- [Next] `Fast Trace -> Medium Trace -> Event Memory -> Structural Memory`のcredit memory階層を型として設計する
- [Next] Event Memoryへmodule/branch activityの圧縮snapshotと不確実性を保持する
- [Next] delayed outcomeからEvent Memoryを検索し、関連branchだけへcredit packetを再配送する
- [Later] 数step、数十step、複数episodeへ遅延を伸ばすcredit horizon benchmarkを作る
- [Later] recurrent loopで同一outcome creditを重複適用しないpacket IDと適用履歴を導入する
- [Later] point-neuron SNN、STDP SNN、surrogate-gradient SNN、dendritic local-credit modelを同一budgetで比較する
- [Later] Transformer比較は精度だけでなくonline adaptation、更新範囲、energy proxy、忘却も測る

最小実験順序:

1. 二段・三段の人工因果chainで、真の寄与branchだけが強化されるか確認する
2. distractor branchを増やし、Hebbian-onlyより誤強化が少ないか比較する
3. rewardを遅延させ、trace減衰と長期credit assignmentの限界を測る
4. branchの追加・pruningを有効化し、strength-only学習との差を比較する
5. 小規模Backprop baselineと到達精度、sample数、更新範囲、忘却を比較する
6. surrogate-gradient SNNと同じ時系列課題・計算budgetで比較する
7. Event Memory replayあり・なしで長期creditの到達距離を比較する

成功指標:

- causally relevant branchへのcredit precision / recall
- delayed outcomeまでの最大有効深度と時間
- 1 eventあたりの更新node数と計算量
- 新規課題学習後の旧構造保持率
- credit経路をEvent IDとPrimitive IDで説明できる割合

失敗条件:

- rewardに近いnodeだけを強化し、長期依存を識別できない
- 頻度の高いdistractorへcreditが漏れる
- hierarchyの深さとともに信号が消失または一枝へ独占される
- topology growthが探索爆発を起こし、pruningで必要経路まで失う

この研究では、Backward informationとBackward gradientを明確に区別します。Backpropは比較baselineや限定moduleで
利用可能ですが、RISAコアの更新に必須とはしません。

最大リスクは長距離credit assignmentです。数stepの成功だけで原理成立とせず、時間・階層深度・replay回数を
段階的に増やし、どこでcreditが消失、拡散、誤帰属するかを失敗結果として保存します。

### [Next] Dynamic Structural Validation

日本語:
構造を静的に正誤判定するのではなく、
予測誤差、共鳴、競合、恒常性の中で
再生安定性を評価する検証方式へ進める。

English:
Validate structures through
prediction error, resonance, competition, and homeostasis
rather than through a separate static verifier.

简体中文:
不要只用独立的静态验证器判断结构对错，
而要通过预测误差、共鸣、竞争与稳态机制
来评估结构的再生稳定性。

研究テーマ:

- [Next] `predicted` と `observed` の局所誤差を構造更新へ接続する
- [Done] `predicted` と `observed` の最小比較を学習ループへ接続する
- [Done] 局所誤差履歴を共有構造の安定性スコアへ接続する
- [Done] 競合する経路の最小抑制ルールを設計し、予測スコアと edge 可塑性へ接続する
- [Done] 再現観測で `affects` edge の reliability を上げ、plasticity を下げる局所則を実装する
- [Done] 学習前予測が外れた既存 `affects` edge を弱め、再適応可能にする局所則を実装する
- [Later] `synaptic scaling` に相当する構造恒常性を導入する
- [Later] 局所活性化サブグラフの対称親和行列または graph Laplacian を作り、スペクトル安定性プローブを評価する
  - 固有値・固有空間を、結合性、競合による分断、文脈感度の補助指標として使う
  - 予測精度、説明可能性、計算コストで既存の局所検証を上回る場合だけ更新則に昇格する
- [Later] 独立 Verifier を標準経路にせず、必要時だけ補助的に使う

### [Next] Replay and Gradual Consolidation

日本語:
新しい経験をいきなり長期構造へ固定せず、
一時記憶、再生、既存構造との相互作用を経て
徐々に統合する。

English:
Do not immediately commit new experience
into long-term structure.
Use temporary memory, replay, and gradual consolidation.

简体中文:
不要把新经验立刻写入长期结构，
而应通过临时记忆、重放、与既有结构相互作用后
再逐步整合。

研究テーマ:

- [Done] `Event Memory -> Structure Candidate -> Replay -> Consolidation` の最小ループを実装する
- [Done] clean evidence に加え、自己生成状態を次段へ渡す deployment Replay を実装する
- [Done] active state dropout による controlled perturbation Replay を実装する
- [Done] Replay種別ごとに`SPLIT_CONTEXT` / `REPAIR_TRANSITION` / `ADD_REDUNDANT_PATH`候補を生成する
- [Done] 観測contextで根拠を分配できる`SPLIT_CONTEXT`を安全な局所編集として実行する
- [Done] superseded Primitiveへの新規観測をcontext variantへ継続ルーティングする
- [Done] 同一actorの直前effectがpreconditionを満たす場合だけ`REPAIR_TRANSITION`を実行する
- [Done] 全体到着順を`globally_precedes`、actor-local順を`precedes`として分離する
- [Done] 継続学習バッチを保存済みの全体・actor-local系列へ接続する
- [Done] process集約edgeに加えて`event_precedes` / `event_globally_precedes`を保持する
- [Done] actor-localなevent-level順序を予測説明の根拠パスへ接続する
- [Done] `consumed_states`により状態消費をPrimitive・Graph・Replay・Compositionへ接続する
- [Done] deployment trajectoryを`remove -> add`順で更新する
- [Done] `state_group_updates`と排他的状態群による状態置換を実装する
- [Done] group候補を継続蓄積し、forecast/replay/compositionの削除集合へ反映する
- [Done] `numeric_preconditions`と`state_variable_deltas`による部分消費を実装する
- [Done] actor別deployment trajectoryとCLIへ数値状態を接続する
- [Done] state variableの単位・上下限・原子的複数更新を実装する
- [Done] `resulting_variables`をforecast/composition結果へ追加する
- [Done] 状態分岐を独立trajectoryとして保持するbounded branch simulationを実装する
- [Done] 採用済み候補に加え、反復支持・Replay成功した少数候補を分岐探索だけに残す
- [Done] 離散状態、量的状態、Primitive根拠をbranchごとに独立して追跡する
- [Done] goal、confidence、resource cost、trajectory riskを分解するbranch evaluatorを実装する
- [Done] goal未達branchを選択せず、到達不能時に選択なしを返す
- [Done] `evaluate` CLIでsimulationからbranch選択までを接続する
- [Done] goalのAND/OR、数値条件、hard constraintを表すGoal Specificationを実装する
- [Done] 部分達成scoreと完全達成、hard constraint適合を分離して説明する
- [Done] 到達不能・制約違反だけの場合に選択なしを返す
- [Done] simulation中に禁止状態へ入ったbranchを早期除外するconstraint-aware searchを実装する
- [Done] 初期状態違反を展開前に停止する
- [Done] expanded candidate、constraint prune、beam pruneを探索診断として返す
- [Done] soft riskとhard constraintを探索意味論上で分離する
- [Done] 初期状態・action・状態変数を介入して比較するCounterfactual Planning MVPを実装する
- [Done] baselineと介入案を同じGoal Specificationで独立評価する
- [Done] 介入costをbranch utilityから分離してplan scoreへ反映する
- [Done] 不可能な介入を選択せず、永続構造を変更しないことを検証する
- [Done] Goal Specificationと既存Primitiveから介入候補を生成するIntervention Candidate Generationを実装する
- [Done] Primitiveのstate条件、numeric precondition、deltaから不足入力を逆算する
- [Done] 生成理由とevidence Primitive IDを介入案へ保持する
- [Done] 手動案と生成案を同じcounterfactual plannerで比較可能にする
- [Done] 複数Primitiveを逆向きに接続するBackward Goal Decomposition MVPを実装する
- [Done] actor-localな`precedes`が観測されたPrimitiveだけをchainへ接続する
- [Done] chain全体のnumeric preconditionとdeltaから必要初期値を逆算する
- [Done] 循環を避け、深度と候補数を制限してaction sequenceと順序付き根拠を返す
- [Done] suggested action sequenceを厳密に実行するSequence-Constrained Simulation MVPを実装する
- [Done] sequence隣接actionのactor-local `precedes`を展開前に再検証する
- [Done] 指定stepごとにstate、numeric condition、hard constraintを検査する
- [Done] sequence完走、途中失敗、不正edgeを別診断として返す
- [Done] 複数の未充足前提をsubplanとして統合するConjunctive Plan Graph MVPを実装する
- [Done] Primitive nodeとrequired-state dependency edgeを明示型として保持する
- [Done] 全AND前提を再帰解決し、未解決状態を隠さず保持する
- [Done] 依存順序と観測済み`precedes`を満たすaction sequenceへ線形化する
- [Done] 同score時は依存説明を持つplan graphを線形chainより優先する
- [Done] 各前提の複数producerを保持・比較するDisjunctive Subplan Search MVPを実装する
- [Done] producerの直積を上限付きで列挙し、同じ`alternative_group_id`へまとめる
- [Done] variantごとの`selected_producers`、必要資源、action sequence、根拠Primitiveを保持する
- [Done] OR候補をSequence-Constrained Simulationで独立評価し、安全・高速経路から制約適合案を選ぶ
- [Done] 入れ子のproducer代替を再帰展開するNested AND-OR Plan Graph MVPを実装する
- [Done] 各PrimitiveのAND前提と各stateのOR producerを任意深度まで同じ規則で展開する
- [Done] visited Primitiveと観測済み`precedes`到達性により循環・根拠なし接続を除外する
- [Done] `alternative_choice_count`と`dependency_depth`をplan graphへ記録する
- [Done] 候補上限による不完全探索を`alternative_search_truncated`として明示する
- [Done] 全順列線形化を廃止するPartial-Order Plan Execution MVPを実装する
- [Done] incoming dependencyを満たしたready Primitiveをbranchごとに直接実行する
- [Done] plan graph指定Primitive IDへ実行候補を固定し、同名actionの混入を防ぐ
- [Done] 9 node graphを全順列なしで完走し、独立subplanの順序をbranchとして保持する
- [Done] ready node展開、deadlock、Primitive不一致を探索診断へ追加する
- [Next] 状態消費・排他更新・共有資源の競合を検出するPlan Graph Threat Detection MVPへ進む
- [Later] `ADD_REDUNDANT_PATH`は代替経路の観測証拠が得られるまで自動実行しない
- [Later] 高速一時記憶と低速長期構造の二層化を実装する
- [Later] working / episodic / semantic / procedural memory の更新速度を分離する
- [Later] Transformer teacher なしで replay target を形成する self-teaching を検証する

日本語: 部分順序graphの直接実行は完了し、次は独立subplan間の干渉を検出します。

English: Partial-order execution is implemented; cross-subplan threat detection is next.

简体中文: 已实现偏序执行；下一步检测子计划之间的冲突。

### [Next] Neural Representation + Structural Memory + Dynamic Inference

日本語:
ニューラル系は
生データからイベント候補を抽出する高速推論器、
RISA は
永続構造記憶と世界モデル、
推論器は
必要時に関連構造を探索して知識を生成する
という役割分担を明確にする。

English:
Separate roles across
neural representation,
structural memory,
and dynamic inference.

简体中文:
明确区分
神经表征、
结构记忆、
动态推理
三者的职责。

研究テーマ:

- [Next] Neural layer の入出力境界を `Event / Concept candidates` で定義する
- [Next] RISA 側の永続構造を `Events + Relations + Roles + Temporal structure` で持つ
- [Later] 質問時に関連部分構造を取り出して動的推論する経路を確立する

---

## Phase 2 / Phase 2 / 第二阶段

### [Next] Transition-Centric World Model

日本語:
静的な
`A -> relation -> B`
の記録だけでなく、
`Structure_t --Event--> Structure_{t+1}`
を蓄積する
遷移中心の世界モデルへ進める。

English:
Move from static triples
to
transition-centric world modeling.

简体中文:
从静态三元组
转向
以状态迁移为中心的世界模型。

研究テーマ:

- [Done] 任意の `preconditions` を Event と primitive に保持し、`State_t + Action -> State_{t+1}` の最小表現を導入する
- [Done] CurrentState と action を満たす採用済み primitive から、複数の次状態候補をスコア付きで返す `forecast` 経路を実装する
- [Done] CurrentState から複数の未来候補をbounded beamで探索する
- [Done] 構造探索結果をgoal達成度、confidence、cost、riskで評価する
- [Done] 終端goalとtrajectory-level hard constraintを型として評価する
- [Done] forbidden stateのconstraint-aware pruningをgoal-directed評価へ接続する
- [Done] 複数介入案を同じGoal Specificationで比較するgoal-directed planningを実装する
- [Done] 手動介入案の比較から、単一Primitiveに基づく根拠付き候補生成へ進む
- [Done] 単段候補生成から、複数step action sequenceの逆向き構成へ進む
- [Done] learned precedenceの自由分岐ではなく、提案sequenceそのものの実現性を検証する
- [Done] 線形sequenceからAND前提を持つplan graphへ進む
- [Next] 単一producer選択からOR代替subplanを保持するplan graphへ進む

日本語: AND前提をすべて満たす依存graphを実装済み。次は代替subplanを保持する。

English: Conjunctive dependency graphs are implemented. Next, preserve alternative subplans.

简体中文: 已实现合取依赖图。下一步是保留可替代的子计划。

### [Next] Structural Factorization and Compositional Reasoning

日本語:
具体的な問題や経験を、再利用可能な関係・役割・時間制約を含む構造単位へ分解し、
局所活性化した候補だけを再結合して、未保存の遷移や解答候補を導く。

English:
Factor concrete problems and experiences into reusable structural units with relations, roles,
and temporal constraints, then compose only locally activated candidates to infer unstored transitions or answers.

简体中文:
将具体问题与经验分解为包含关系、角色和时间约束的可复用结构单元，
只组合局部激活的候选单元，以推导未存储的状态迁移或答案。

研究テーマ:

- [Done] `StructuralPrimitive` の最小データ型を、関係、役割、入力条件、出力状態、時間制約、支持度で定義する
- [Done] 反復する `entity -> process -> state` 遷移から primitive 候補を抽出し、経験を primitive ID の組合せとして保存する
- [Done] 再利用数・局所予測検証・圧縮代理値から、primitive 候補を provisional に採用・保留する局所則を実装する
- [Next] 候補の採用を、再利用性、再構成性、予測改善、Minimum Description Length の四条件で評価する
- [Done] action の時間的前後関係を使い、採用済み primitive の局所合成経路を CLI から返す最小実装を作る
- [Next] 問題状態から目標状態への局所的な primitive 合成探索を、説明可能な経路として返す
- [Later] 未学習の組合せ問題を使い、構造因数分解が単純な保存・検索を上回るか検証する
- [Later] 人間が未命名の primitive を識別子のまま保持し、予測有用性で評価する

### [Next] Stored Structure != Available Knowledge

日本語:
保存された構造と
その場で導かれる知識を分離し、
「覚えていないが導ける」
性質を研究主題として明示する。

English:
Make a clear distinction between
stored structure
and
available knowledge generated at inference time.

简体中文:
明确区分
“已存储的结构”
与
“推理时生成的可用知识”。

研究テーマ:

- [Next] 多段経路探索から未学習の関係を導く推論ベンチマークを作る
- [Next] `A -> B -> C -> D` から `A => D` を導く説明可能推論を評価する
- [Next] 人間がまだ命名していない潜在構造を内部単位として保持し、有用性で評価する
- [Later] 条件付き推論
  例:
  温度・圧力・履歴つき相変化推論
  を扱う

### [Next] Reusable Relation Units

日本語:
経験を最初から完成済みグラフとして比較・分類するのではなく、
小さな関係単位の再利用が積み重なった結果として
概念や差分が見えてくる設計へ進める。

English:
Move toward a design where
concepts and differences emerge
from the reuse of small relation units
rather than from explicit whole-structure matching.

简体中文:
推进一种设计：
概念与差分
并不是通过显式的整结构匹配得到，
而是由小型关系单元的反复复用自然涌现。

研究テーマ:

- [Next] `shared relation unit` の最小データ型を定義する
- [Next] 経験を「単一構造」ではなく「共有単位の組合せ」として保存する
- [Next] 共通性を `same structure` 判定ではなく `same unit reuse` で近似する
- [Later] 差分を別オブジェクトとして計算するのではなく、共有単位の非重複部分として導出する

---

## Phase 3 / Phase 3 / 第三阶段

### [Next] Learner-Agnostic Knowledge Substrate

日本語:
Transformer、
SNN、
将来の未知の学習器が変わっても、
知識継承が壊れにくい保存基盤を作る。

English:
Build a learner-agnostic knowledge substrate
that can outlive individual learning architectures.

简体中文:
构建一种与学习器解耦的知识基底，
使知识可以跨架构继承。

研究テーマ:

- [Next] `Learner -> Structure` の標準入出力境界を定義する
- [Later] `Transformer -> G`, `SNN -> G`, `Future Learner -> G` の相互運用性を検証する
- [Later] 学習器を差し替えても世界モデルの整合性が保てるか評価する

### [Later] SNN = Dynamics, RISA = Structure

日本語:
SNN を時間・位相・イベントダイナミクス担当、
RISA を構造保存と概念進化担当として分業する。

English:
Let SNN specialize in dynamics,
while RISA specializes in persistent structure and concept evolution.

简体中文:
让 SNN 负责动态与时序，
让 RISA 负责持久结构与概念演化。

研究テーマ:

- [Later] 発火タイミングを `Phase / Temporal relation` として構造へ写像する
- [Later] SNN のイベント流を RISA の構造更新へ接続する
- [Later] SNN 活性を局所探索制御に利用する

---

## Phase 4 / Phase 4 / 第四阶段

### [Later] Ambiguous, Continuous, and Affective Signals

日本語:
皮肉、
雰囲気、
危険っぽさ、
顔の印象、
音の不穏さ
のような
連続値・曖昧性・時間変化を含む情報を
ニューラル表現と構造記憶の協調で扱う。

English:
Handle ambiguity,
continuous signals,
and affective cues
through cooperation between neural representations and structural memory.

简体中文:
通过神经表征与结构记忆的协作，
处理模糊、连续以及情感性信号。

研究テーマ:

- [Later] 画像・音・文章から曖昧なイベント候補を抽出する
- [Later] 曖昧候補を構造仮説として保留・比較する
- [Later] 文脈で意味が確定した時だけ構造へ定着させる

### [Later] Cross-Modal Structural Abstraction

日本語:
文章、映像、音、触覚の固有値を統合するのではなく、
各 Encoder が抽出したイベントから状態、差分、関係、順序、反復、強度、予測誤差を構造候補として取り出す。
別モダリティでも予測・再構成に役立つ構造だけを、段階的に共有側へ昇格させる。

English:
Do not merge modality-specific values directly. Extract state, difference, relation, order, repetition,
intensity, and prediction error from encoder events, and promote only cross-modally useful structures.

简体中文:
不要直接合并模态特有的数值。应从编码器事件中提取状态、差异、关系、顺序、重复、强度和预测误差，
并只提升那些跨模态仍有用的结构。

研究テーマ:

- [Later] `Event` にモダリティ由来、固有座標の参照、観測信頼度を追加する境界を定義する
- [Later] `StructuralPattern` / `StructuralPrimitive` にモダリティごとの適用支持度を持たせる
- [Later] `Universal -> Semi-universal -> Modality-specific` を固定分類ではなく、予測・再構成実績から連続的に推定する
- [Later] 一つのモダリティで学んだ遷移構造が別モダリティの予測を改善するか、holdout 実験で検証する
- [Later] 共通構造から各モダリティへ戻す Decoder / 生成経路を、知覚器との双方向仮説ループとして評価する

---

## Research Notes / 研究ノート / 研究说明

- [Next] RISA を単なる Knowledge Graph に戻さない
- [Next] 静的存在記述より
  「世界がどう変化するか」
  を優先する
- [Next] 推論結果として知識がその場で生成される設計を重視する
- [Later] 世界モデルの正確さと未来探索能力を
  知能評価の中心指標にする

---

## Related Docs / 関連文書 / 相关文档

- `docs/RISA-and-SARA-Engine-Compatibility.md`
- `docs/RISA-Structural-Interpolation-and-Smoothing.md`
- `docs/RISA-Concept-Formation-and-Multimodal-Notes.md`
- `docs/RISA-Transformer-SNN-Relationship-Notes.md`
- `docs/policy.md`
