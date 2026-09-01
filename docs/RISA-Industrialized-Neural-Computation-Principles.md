# RISA Industrialized Neural Computation Principles

## 1. 位置付け / Position / 定位

日本語:
脳を物質としてコピーするのではなく、局所計算、時間通信、feedback、可塑性、再帰という計算原理を、
測定・交換・量産可能なsoftware/hardware unitへ置換する研究方針です。

English:
Translate local computation, temporal communication, feedback, plasticity, and recurrence into measurable,
replaceable engineering units instead of materially copying the brain.

简体中文:
不从物质层面复制大脑，而是把局部计算、时间通信、反馈、可塑性与递归转化为可测量、可替换的工程单元。

## 2. 最小計算unit

通常の点ニューロンだけでなく、複数の局所branchを持つintegration unitを候補にします。

```text
x1, x2, x3 -> Local Branch A --+
                                  -> Integration Unit -> Event
x4, x5, x6 -> Local Branch B --+
```

概念モデル:

```text
event = Integrate(
  BranchA(x1, x2, x3, local_state, time),
  BranchB(x4, x5, x6, local_state, time),
  integration_state,
  modulation
)
```

初期unit state:

- activationまたはmembrane-like state
- recent activity
- eligibility trace
- connection strength
- local threshold
- context trace
- energy / structural budget

生物学的電位や化学物質を忠実に再現する必要はありません。各状態が予測、online learning、credit assignment、
省計算性のどれへ寄与するかをablation可能にします。

## 3. 学習器をunitから切り離しすぎない

各unitは計算だけでなく、次の更新候補を局所的に作ります。

- 入力と出力の時間関係によるstrength更新
- integration結果を受けたeligibility更新
- reward/context/novelty modulationによるcredit確定
- 反復共活動によるconnection候補
- 長期低利用によるdormancy/pruning候補
- 高い未説明相関によるbranch growth候補

候補生成は分散させますが、無制約な自己改変にはしません。接続予算、energy、証拠Event、Replay、rollback可能性を
commit条件にします。

## 4. アルゴリズムとしてのフラクタル

事前に美しいcanopy形状を設計するのではなく、同じprotocolを異なるscaleで再利用します。

```text
local process
  -> integrate
  -> emit event
  -> receive feedback
  -> update or restructure
```

このprotocolをbranch、integration unit、local circuit、moduleへ適用します。各scaleのstate型と時間定数は同一である
必要はありません。自己相似なのはAPIと更新循環であり、node数や形状ではありません。

## 5. 成長実験

最小seedから開始し、局所則だけで構造を成長させます。

比較群:

- flat固定構造
- 人手設計の固定canopy
- strengthだけを学ぶ可変weight構造
- strengthとtopologyを学ぶ成長canopy

共通制約:

- 同じevent stream
- 同じ総計算budget
- 同じ最大接続数
- 同じoutcome signal
- 同じ評価期間

測定:

- holdout prediction / goal達成
- activityあたりの計算量
- online adaptation速度
- 過去課題の保持率
- branch再利用率
- 構造深度、分岐係数、cross-link率
- pruning後の性能回復

canopy状へならなくても性能が高ければ、その形を失敗とは扱いません。目的は自然物に似せることではなく、局所則から
実用的な構造が創発するかを検証することです。

## 6. SNNとの関係

`Neuron + Spike + STDP`だけでは研究範囲が不足します。RISA/SARAとの接続では次を一組として比較します。

```text
Dendritic-like local computation
+ event/spike timing
+ hierarchical local credit
+ structural plasticity
+ modulation
+ recurrence
```

SNNは時間表現とevent routingの候補であり、RISAの構造記憶やConcept Cellを必ず置き換えるものではありません。

## 7. 最重要未解決問題

長距離credit assignmentを解けなければ、局所可塑性は短い相関学習へ退化する可能性があります。評価は数stepだけでなく、
長い階層、遅延outcome、複数episode、Replay後の再配分へ拡張します。

調べる失敗形:

- temporal proximityだけで直近branchへcreditが偏る
- rewardが広すぎて無関係unitまで強化する
- 深い階層でcreditが消失する
- recurrent loopで同じcreditを重複計上する
- branch growthがcredit経路を不安定化する

この研究の問いは「Backpropを捨てられるか」だけではありません。

> **局所的に自己更新する工業的unitから、大域的な知性と長期因果学習を創発させられるか。**
