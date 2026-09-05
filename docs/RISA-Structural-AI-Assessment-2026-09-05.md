# RISA structural AI assessment / 構造AI設計評価 / 结构AI设计评估

Date: 2026-09-05. Reviewed runtime revision: `70d2db064fbe8b34964ba86b53b2bd8a85547220`.

## 判断 / Decision / 判断

日本語: **継続する価値はある。ただし、現在の機能追加中心の進め方は変更する。**
状態遷移、根拠付き記憶、制約付き計画の基盤は実在する。構造ベースのAIとして最も見込みがあるのは、
経験から適用条件を学び、既知の遷移を未知の対象・組合せへ再利用し、環境変化に局所的に適応する世界モデルである。
現在は「構造化された入力仕様を集計・再利用する研究用エンジン」であり、一般的な役割構造の獲得、
構造自己組織化の優位性、汎用知能、ANN/SNNに対する性能優位は実証していない。

English: Continue, but switch from feature accumulation to falsifiable experiments. The transition memory and
constrained planning core exists. The promising direction is a world model that learns applicability, transfers
transitions across objects and compositions, and adapts locally. General role induction, superior self-organization,
general intelligence, and advantages over ANN/SNN remain unproven.

简体中文: 值得继续，但应从功能堆积转向可证伪实验。状态转移记忆与约束规划核心已经存在。
有希望的方向是学习适用条件、跨对象与组合复用转移、并进行局部适应的世界模型。
通用角色归纳、自组织优势、通用智能以及相对ANN/SNN的性能优势尚未得到验证。

## 確認範囲と限界 / Scope and limits / 范围与限制

README、roadmap、policy、技術設計と関連研究方針、およびcore/engine/CLI、人工データ、既存テストを横断確認した。
学習→予測→Replay→適応と、forecast→simulation→evaluation→planningを重点的に追った。
これは設計評価と小さな反例の確認であり、網羅的なバグ検出、実世界性能評価、大規模性能測定ではない。

- `python3 -m unittest discover -s tests`: **55 tests, OK**。
- `python3 -m experiments.structural_assessment`: 合成データによる6項目の診断。
- [診断コード](../experiments/structural_assessment.py) / [実測出力](structural-assessment-2026-09-05.json)。永続stateは変更しない。
- Replay反例は採用済みPrimitiveを直接置いた制御fixture。学習成功率を測ったものではない。
- 既存テストの合格は、そのテスト範囲の実装整合性を示す。汎化や因果同定の証明ではない。

English: This is a cross-module design review with six synthetic probes, not an exhaustive bug audit or a real-world
benchmark. All 55 existing tests pass. The replay probe uses a controlled adopted-primitive fixture; it does not
measure learning quality. No persisted state was changed.

简体中文: 本次为跨模块设计评估及六项合成诊断，不是穷尽式缺陷审查或真实场景基准。
现有55项测试全部通过。重放反例使用预设已采纳原语，只验证执行语义，不衡量学习质量。未修改持久状态。

## 維持する資産 / Assets to preserve / 保留的基础

| 実装 / Implementation / 实现 | 評価 / Assessment / 评价 |
| --- | --- |
| Event、Primitive、根拠ID、保存復元 | 経験から説明まで追跡する土台 / Traceable memory foundation / 可追溯记忆基础 |
| 消費・排他状態・数値資源・単位・範囲検査 | 遷移の実行契約を作る有用な部品 / Useful transition contracts / 有用的转移执行契约 |
| 独立branch、AND/OR plan、Primitive ID指定実行、threat検出 | 合成仮説を検査する装置として再利用 / Reuse as a composition test engine / 作为组合验证引擎复用 |
| 学習前予測、誤差履歴、文脈分裂、Replay | 継続適応の出発点。ただし外部評価が必要 / Adaptation scaffold requiring external evaluation / 需外部评估的适应框架 |

全面的な書き直しは不要。学習の価値を測るために既存plannerを固定し、遷移表現と証拠の意味を先に修正する。

English: Preserve the engine; stabilize planning while repairing transition and evidence semantics.

简体中文: 保留现有引擎；暂时稳定规划功能，优先修正转移与证据语义。

## 問題と根拠 / Findings and evidence / 问题与依据

### F1 — 同時effectと排他的outcomeの混同 / Joint effects vs alternatives / 同时效果与备选结果混淆

`learner.learn_from_event`はobserved_effectsごとに単一outputのPrimitiveを生成し、各々へ同じ資源deltaを複写する。
`simulator`は候補ごとにbranchを作る。`activate -> {lit, warm}, energy -= 1`を3回観測しても、
一段予測は`{lit}`と`{warm}`の別branchになった。AND goalの欠落や、後の組合せで同一actionを重複実行するリスクがある。
数値deltaの原子性だけでは、離散effectを含む遷移全体の原子性を保証できない。

**修正契約:** 一つの観測outcomeを`add_effects + delete_effects + group_updates + numeric_deltas`の束で保持する。
同時effectは一度に実行し、確率的な別outcomeとは別の型にする。旧単一outputデータの移行も設計する。

English: A joint `{lit, warm}` observation becomes two exclusive branches. Represent an entire outcome atomically,
apply its resource cost once, and distinguish joint effects from alternative outcomes, with legacy migration.

简体中文: 同时观测到的`{lit, warm}`被拆成两个分支。应以完整结果为原子转移，资源只扣除一次，
区分同时效果与备选结果，并迁移旧数据。

### F2 — Replayが不可能な世界を生成 / Replay merges incompatible worlds / 重放合并不相容世界

`replay._replay_deployment_trajectory`は全候補のeffectをunionし、数値deltaは先頭候補だけを使う。
制御fixtureで排他的な`left`と`right`が同時にactiveとなり、両方を要求する`join -> impossible`が発火した。
通常simulationのbranch分離がReplayへ共有されていない。
さらにclean/deploymentの成功は`bool(predicted & observed)`で判定され、無関係な追加effectや欠落を十分に罰しない。

**修正契約:** 学習・Replay・forecast・計画で同じ純粋なtransition適用関数を共有し、
状態・資源・根拠をbranchごとに保持する。観測が完全ならeffect集合一致、部分観測なら観測mask付き評価を行う。
学習済み経験の再生スコアは内部整合性指標であり、汎化精度として報告しない。

English: Replay unions mutually exclusive effects and uses only the first candidate's numeric delta. Share a pure
transition kernel and retain complete per-branch state. Evaluate full outcomes or explicit partial-observation masks;
training replay is an internal consistency check, not generalization evidence.

简体中文: 重放合并互斥效果，却只使用首个候选的数值变化。应共享纯转移函数，逐分支保留完整状态。
评估完整结果或明确的部分观测掩码；训练数据重放仅衡量内部一致性，不能证明泛化。

### F3 — 役割一般化が未実装 / Missing role binding / 缺少角色绑定

`StructuralPattern`は固定`entity->process->state`とcontextキーの集約で、action/effect/actorの集合を持つ。
`abstractor.rebuild_concepts`は共有action/effectのグループ化。任意の関係分解や変数束縛の学習ではない。
`Event.target`は保存されるが、learnerの集計キーとpredictorの照合に使われない。
同じrobotの`touch(heater)`と`touch(ice)`は、診断で両方`cold`になった。
`wolf run -> tired`もaction頻度baselineと同じ答えであり、構造抽象化の追加価値を識別できない。

**修正契約:** まずactor/targetを含むgrounded条件で誤混合を止め、その後、型付き変数束縛を導入する。
`holds(agent, object)`等の関係、対象別state/resource、異なる対象の非混同を表現する。
役割名やschemaを手で与えた実験と、経験からschemaを誘導した実験は分離する。

English: Current concepts group action/effect labels; they do not learn general role bindings. Targets are ignored
by learning/prediction matching. Fix grounded identity first, then add typed relational bindings and test transfer.
Separate supplied schemas from learned schemas.

简体中文: 当前概念主要聚合动作与效果标签，尚未学习通用角色绑定。学习与预测匹配忽略target。
先修正具体对象的区分，再引入类型化关系绑定，并分开评估人工提供与自主学习的schema。

### F4 — 証拠と説明の整合性 / Evidence integrity / 证据一致性

同じ3 Event IDを再投入すると保存Event数は3のまま、action頻度は3から6へ増えた。
`runtime.train_events`は既存IDの再学習を抑止しない。Replay回数も独立した新規観測数とは異なる。
未知action`never_seen`に対し、根拠Event IDが空なのに`dog -> never_seen -> tired`を説明経路として返した。
この経路は推論時に組み立てられたもので、実在edgeの連鎖とは限らない。

**修正契約:** 同じID・同じ内容はno-op、同じID・異なる内容は明示的訂正か拒否。
出典、episode、時間順序、schema versionを記録し、遅着イベントの扱いを定義する。
観測、導出、未検証仮説を区別し、導出には入力根拠と適用規則を必須にする。
未学習actionから候補を想起しても、適用根拠がなければ確定予測を棄却する。

English: Re-ingestion doubles counts without adding unique events, and an unknown action receives a synthetic
support path without matching evidence IDs. Require idempotency, explicit corrections, episode/time contracts,
and separate observed, derived, and hypothetical claims with abstention when applicability is unsupported.

简体中文: 重复导入会增加计数但不增加独立事件；未知动作获得了无对应证据ID的解释路径。
应保证幂等导入、显式更正与事件时间契约，并区分观测、推导与假设；缺少适用依据时弃答。

### F5 — 順序・適用条件・因果の混同 / Order, applicability, causality / 顺序、适用性与因果

planner生成とsequence/compose探索は観測`precedes`を接続条件に使う。
これは現在の保守的な制限として理解できるが、「前提とeffectが接続できる未観測の順序」を排除する。
一方で到着順の前後関係だけでは因果関係を示さない。Eventの前提・消費・deltaは入力で供給され、
観測から必要条件を発見する学習能力はまだ示されていない。
`plan_counterfactuals`は入力状態を書き換えたモデル内what-ifであり、観測データから因果効果を同定する実装ではない。

**修正契約:** observed order、learned applicability、hard temporal constraintを分離する。
学習遷移の前提・effect・資源整合性から未観測合成を候補化し、独立環境で検証して初めて支持を増やす。
操作可能な介入のallowlist・cost・上限を環境が与え、任意状態追加を実行可能な計画とみなさない。

English: Observed order is currently an execution/generation gate, limiting unseen compositions. Separate order,
applicability, and hard temporal constraints. Validate novel compositions in an independent environment.
Current counterfactual planning is model-based what-if, not identified causal inference; restrict executable interventions.

简体中文: 观测顺序限制了未见组合。应区分顺序、适用条件与硬时间约束，并由独立环境验证新组合。
当前反事实规划是模型内假设比较，不是因果效应同定；可执行干预必须受环境权限与成本约束。

### F6 — 評価・規模・確率の未検証 / Evaluation, scale, calibration / 评估、规模与校准

- predictorは頻度・概念・構造・共活性等の手動重み和。scoreは校正された確率ではない。
- `compression_proxy`は根拠Event数の関数で、実際の符号長や例外costを測るMDLではない。
- primitive照合、共活性候補、根拠説明には全Primitive/edge/Event走査が残る。
  runtimeは学習バッチ後に全経験Replayを行う。小さい探索半径だけで計算量の局所性は保証されない。
- composeの訪問済み判定はaction中心で、異なるstate/resource経路を落とす可能性がある。
- 保存は単一JSONの直接writeで、schema migration、原子的置換、復旧検証は未整備。
- 動作例と回帰テストはあるが、分割固定・baseline・ablation・複数seedを備える研究評価はない。

English: Heuristic scores are uncalibrated; the compression proxy is not MDL. Global scans and full-history replay
remain. Action-only composition deduplication can lose distinct states. Versioned atomic persistence and controlled
comparative benchmarks are unfinished. These are static findings; no scaling advantage was measured.

简体中文: 启发式分数未经概率校准，压缩代理并非MDL。仍有全局扫描与全历史重放；仅按动作去重可能丢失不同状态。
版本化原子保存与受控比较基准尚未完成。以上为静态发现，本次未测得规模优势。

## 再設計 / Redesign / 重新设计

実行順と完了条件は[ROADMAP](ROADMAP.md)を唯一の現行計画とする。
核心は`Evidence -> Transition hypotheses -> Shared execution -> External evaluation -> Local revision`。
構造自己組織化の価値を、同じ入力・planner・予算を用いる固定構造baselineとの差分として測る。
同じ経験のcount、concept、coactivation、Replayを複数の独立証拠と数えない。

English: The roadmap is the authoritative execution plan. Measure self-organization against fixed structures under
identical inputs, planners, and budgets. Multiple representations or replays of one event are not independent evidence.

简体中文: 以路线图作为唯一当前执行计划。在相同输入、规划器与预算下比较自组织与固定结构。
同一事件的多种表征或多次重放不能当作独立证据。

## 一次資料と位置付け / Primary context / 一手资料

構造学習と記号的計画を組み合わせる研究領域は既に存在する。RISAが構造を使うこと自体を新規性とせず、
局所改訂・忘却耐性・証拠追跡・予算内汎化の改善を独自性の候補として検証する。
これは以下の研究と実装を踏まえた設計判断であり、これらの論文がRISAの有効性を示すわけではない。

- [Safe Learning of Lifted Action Models, KR 2021](https://proceedings.kr.org/2021/36/): 観測から適用条件と効果を学ぶ研究。学習したモデルの誤りが計画失敗につながる点も比較軸となる。
- [Lake & Baroni, ICML 2018](https://arxiv.org/abs/1711.00350): SCANの体系的な組合せ汎化評価。RISAへは分割設計の原則を参考にする。現代の全ニューラル方式への否定として引用しない。
- [Li & Silver, CoLLAs 2023](https://proceedings.mlr.press/v232/li23a.html): 関係述語の接地、学習、計画、能動的な情報取得を接続する例。知覚器との接続は有用だが、現在のRISAコア検証の代替にならない。

English: Structural model learning and planning already have precedents. RISA's potential differentiation is measured
local revision, retention, provenance, and transfer under budgets; the cited papers do not establish RISA's effectiveness.

简体中文: 结构模型学习与规划已有先行研究。RISA的潜在差异化应由局部修订、知识保持、证据追踪与预算内迁移的实测收益证明；
上述论文并不证明RISA本身有效。
