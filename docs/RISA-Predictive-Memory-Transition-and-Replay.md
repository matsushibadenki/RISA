# Predictive Memory Transition and Structural Replay

## 位置付け

Kumar and Isola の `Pretraining Recurrent Networks without Recurrence` は、
記憶学習を次の二問題へ分離します。

1. Transformer teacher が、未来予測に必要な情報を持つ memory target を作る。
2. recurrent updater が、現在 memory と次入力から次 memory を一段だけ予測する。

Sequential Memory Transfer (SMT) は「何を記憶すべきか」と「どう一段更新するか」を分離し、
Backpropagation Through Time を使わずに updater を事前学習します。Deployment Memory Transfer
(DMT) は updater 自身が生成した memory を入力にして追加学習し、逐次実行時の drift を抑えます。

## RISA への採用

RISA は dense memory vector をそのまま採用しません。対応関係を次のように置きます。

```text
SMT memory target       -> 再現すべき Event / state transition
one-step updater        -> 局所的な構造更新則
deployment drift        -> 現在の世界モデルが過去経験を再現できない状態
DMT correction          -> Replay failure に基づく Primitive 再評価
```

MVP-1 では学習後に Event Memory を現在の予測器へ再投入し、観測 effect と一致した割合を
`StructuralPrimitive.replay_score` に保存します。Primitive の provisional adoption は、
validation、reuse、compression proxy、clean replay stability、deployment replay stability の
組合せで決めます。

deployment replay は actor ごとにactive stateを保持し、前段でモデルが予測したeffectだけを
次段へ渡します。観測stateを毎回復元しないため、局所的な誤差が後続遷移へ与える影響を測れます。

deployment replayはdrift診断のため最上位候補を一つだけ進めます。複数の支持された未来を比較する用途では、
`simulate_branches`が候補ごとに離散状態と量的状態を複製し、bounded beamとして独立展開します。この二つを
混同せず、Replayは記憶の安定性、branch simulationは未来の不確実性を扱います。

controlled perturbation replay は、そのactive stateから決定的に一状態をdropoutして再予測します。
通常軌跡で成功し摂動時だけ失敗する構造は、必要条件への単一点依存を持つと診断できます。この値は
正誤ではなく頑健性を表すため、現段階ではadoption scoreから分離します。

Replay後には、各Primitiveが局所統計だけから適応候補を生成します。clean replay failureは
`SPLIT_CONTEXT`、deployment-only driftは`REPAIR_TRANSITION`、perturbation-only failureは
`ADD_REDUNDANT_PATH`へ対応させます。これは中央Verifierによる正誤判定ではなく、異なる不安定性へ
異なる局所応答を割り当てる最小の恒常性ルールです。

自動編集は、既存Eventを複数の実在context群へ分配できる`SPLIT_CONTEXT`に限定します。元Primitiveは
削除せずsupersededとして保持し、その後の観測は一致するvariantへ送ります。

`REPAIR_TRANSITION`は追加証拠なしには実行せず、同一actorの直前Eventが必要preconditionを観測effectとして
生成している場合だけ、欠落した`precedes`を復元します。代替経路を発明する`ADD_REDUNDANT_PATH`は
引き続き提案だけに留めます。

時間関係は同一actor内の`precedes`と、actorをまたぐ単なる到着順`globally_precedes`へ分離します。
構造合成は前者だけを利用し、入力ストリームの隣接を局所因果と誤認しないようにします。
さらに具体的なEvent間にも`event_precedes`と`event_globally_precedes`を保存し、前者は予測説明へ
接続します。これによりReplayで使う経験列と、予測が提示する証拠列を同じ時間構造上で追跡できます。

deployment replayのactive stateは追加だけでなく、Primitiveの`consumed_states`を先に除去してから
予測effectを追加します。これにより、一度だけ使える状態を誤って後続Eventへ持ち越すdriftを検出できます。

`state_group_updates`がある場合は、同一排他groupで観測済みの旧状態も除去します。これにより
`charged`と`depleted`のような同時成立しない状態をtrajectory内へ残さず、明示的な状態置換をReplayできます。

量的資源はactorごとの作業変数としてReplayし、`numeric_preconditions`で最低量を確認した後、
`state_variable_deltas`を加算します。これは永続的な外部世界の現在値ではなく、経験列を再構成するための
trajectory-local stateです。

state variableにはunit、minimum、maximumを宣言でき、Replayは全deltaを仮状態へ適用してから境界を検査します。
一変数でも違反する場合は更新全体を棄却し、部分適用による壊れたtrajectoryを作りません。

この実装は DMT そのものではありません。ニューラル memory trajectory を自己回帰生成せず、
構造世界モデルが過去の観測を維持できるかを測る、DMT-inspired structural drift monitor です。

## 研究仮説

以下は論文結果ではなく、RISA 向けの拡張仮説です。

- 記憶は working / episodic / semantic / procedural に分け、更新速度を変える。
- 未来予測だけでなく、再構成、因果整合性、新規性、再利用価値を構造採用目的へ加える。
- 全 Event を同じ強度で更新せず、surprise、prediction error、novelty で更新量を制御する。
- adaptation candidateを実行した場合の予測改善と副作用を比較する。
- Transformer は知覚・初期教師として利用し、最終的には蓄積構造から target を作る self-teaching を検証する。
- 固定長 active structural state と外部 episodic store を分け、内部状態から連想的に過去経験を再活性化する。

## 採用しない短絡

- 未来予測に十分な状態が、長期的に重要な稀少知識も必ず保持するとは仮定しない。
- dense memory を graph に置き換えるだけで構造知能が成立するとは仮定しない。
- Replay 成功だけを真理判定に使わない。誤った多数派、文脈差、例外を保持する。
- Transformer teacher を恒久的な正解生成器にはしない。

## 次の実験

1. clean replay と deployment replay の drift 検出率を比較する。
2. clean replay failure と perturbation failure に異なる局所更新則を適用する。
3. replay なし、validation のみ、validation + replay で継続学習時の旧知識保持率を測る。
4. future prediction 単独と multi-objective adoption で、稀少だが重要な Event の保持率を測る。

## 参照

- Akarsh Kumar and Phillip Isola, [Pretraining Recurrent Networks without Recurrence](https://arxiv.org/html/2606.06479v2), arXiv:2606.06479v2, 2026.
