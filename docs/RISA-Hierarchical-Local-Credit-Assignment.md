# RISA Hierarchical Local Credit Assignment

## 1. 目的 / Purpose / 目的

日本語:
global gradient Backpropagationを必須にせず、局所信号、時間、階層構造、構造可塑性から、Backpropに匹敵する
credit assignmentへどこまで近づけるかを検証します。

English:
Study how closely local signals, time, hierarchy, and structural plasticity can approach Backprop-level
credit assignment without requiring global end-to-end gradients.

简体中文:
研究在不依赖全局端到端梯度的情况下，局部信号、时间、层级结构与结构可塑性能够在多大程度上实现接近
Backprop的信用分配能力。

## 2. 境界

RISAは逆向き情報を禁止しません。区別する対象は次です。

```text
Backward information
  goal, reward, prediction error, activity trace, replay
  -> 使用する

Backward gradient
  end-to-end differential gradient over the global computation graph
  -> RISAコアの必須条件にしない
```

知覚器や局所adapterをgradientで訓練するhybrid構成は許容します。永続構造記憶、Concept Cell代謝、online更新が
global Backpropなしでは機能しない構成は目標から外します。

## 3. 仮説

```text
Input Event
  -> Local Activity
  -> Interaction
     -> STDP-like timing
     -> bAP-like branch notification
     -> outcome modulation
  -> Local Plasticity
  -> Network State Change
  -> Next Event
```

望ましいoutcomeが起きたとき、global gradientを計算せず、outcome nodeから直前に活動したbranch、sub-branch、
eligible relationへ構造階層を逆向きにたどります。

```text
Soma outcome
  -> active branch A
    -> active sub-branch A1
      -> eligible input x1
```

## 4. Credit Packet

最小実装ではcreditを一つのscalarへ早期圧縮せず、次を保持するpacketとして扱います。

- `outcome_id`: 成功・失敗・予測誤差の根拠
- `source_event_id`: credit計算を開始したEvent
- `target_structure_id`: 更新候補PrimitiveまたはConcept Cell
- `local_activity`: outcome前の活動量
- `temporal_proximity`: 時間差によるeligibility
- `branch_contribution`: 親branch内の相対寄与
- `modulation`: rewardまたはfailure signal
- `novelty`: 既存構造で説明しにくい度合い
- `trace_path`: 逆向きにたどった構造ID列

初期creditは積の形を候補にしますが、ゼロ因子やscale独占を避ける正規化、加法形、log-spaceもablationします。

## 5. 更新を分離する

### Strength plasticity

- 成功かつeligible: reliability、再利用優先度を強化
- 失敗かつeligible: reliabilityを弱化し、plasticityを上げる
- 非活動: rewardだけでは更新しない

### Topology plasticity

- 反復共活動: 接続候補
- 長期低利用: 休眠またはpruning候補
- 新規相関と高prediction error: branch growth候補
- 文脈競合: split候補

strength更新とtopology更新は別の閾値、予算、rollback履歴を持たせます。

## 6. 最初のベンチマーク

同じ入力から複数branchが活動し、一つだけが遅延outcomeへ因果的に寄与する人工世界を作ります。

比較対象:

- 頻度だけのHebbian更新
- 時間窓だけのSTDP-like更新
- reward-modulated eligibility trace
- hierarchical local credit
- 小規模global Backprop baseline

評価:

- 正しいbranchへのcredit precision / recall
- distractorへのcredit leakage
- delayed reward距離ごとの成功率
- 更新した構造数と計算量
- 継続学習後の旧課題保持率
- credit pathの説明可能性

## 7. Fractal Canopyとの接続

Fractal Canopyのrouteは推論経路であると同時にcredit indexになり得ます。forward時にroot-to-leaf activity traceを
保存し、outcome時には同じpathだけを逆向きにたどります。cross-linkを通った活動は別traceとして保持し、tree構造へ
無理に潰しません。

## 8. 採用判断

局所方式がBackpropと完全に同じ更新を再現することは目標にしません。採用価値は、性能だけでなくonline更新、
局所計算、構造編集、忘却耐性、説明可能性を含むPareto比較で判断します。長期creditを解けずHebbian近傍へ退化する
場合は、中核原理として採用せず補助可塑性に限定します。

## 9. 工業的Local Unitとの接続

credit assignmentをnetwork外部の独立optimizerとしてだけ実装せず、各Local Unitがactivity trace、eligibility、
threshold、context、structural budgetを持つ構成を実験します。生物学的樹状突起の忠実な再現ではなく、branch単位の
局所計算とBackward informationを明示interfaceにします。詳細は
[Industrialized Neural Computation Principles](RISA-Industrialized-Neural-Computation-Principles.md)に整理します。

## 10. Multi-Timescale Credit Memory

局所eligibilityを無期限に保持しません。時間範囲に応じて情報量を圧縮し、異なるmemory層へ移します。

```text
Fast Trace
  milliseconds to seconds
  exact local activity and timing
        |
        v
Medium Trace
  seconds to minutes
  branch contribution summary
        |
        v
Event Memory
  minutes to episodes
  active module/branch snapshot and context
        |
        v
Structural Memory
  reusable causal route and replay evidence
```

outcomeが遅れて判明した場合は、全synapseへrewardをbroadcastするのではなく、Event Memoryから関連episode、module、
branch候補を検索し、trace confidence付きcredit packetを再配送します。

```text
Outcome
  -> relevant Event Memory
    -> active modules
      -> active branches
        -> surviving local eligibility
          -> plasticity candidate
```

各層への圧縮で失われた情報は復元したふりをしません。packetにはmemory層、trace age、confidence、候補分岐数を持たせ、
古いcreditほど更新量を弱めるか、Replayで再現できた場合だけcommitします。

## 11. SNN比較ベンチマーク

この方式がSNN学習困難を解決したとはまだ言えません。次を同じevent stream、状態数、接続budget、評価期間で比較します。

- point-neuron + STDP
- reward-modulated STDP / eligibility trace
- surrogate-gradient SNN
- dendritic branch + hierarchical local credit
- dendritic branch + hierarchical local credit + Event Memory replay

精度以外に、credit leakage、最大遅延距離、online更新速度、更新対象数、旧課題保持率、説明可能なcredit path率を測ります。
点ニューロン化がSNN学習困難の一因である可能性は検証仮説であり、原因として確定しません。
