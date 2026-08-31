# RISA

RISA は **Relationally Involving Self-organizing Architecture** の略で、
重み付き関数近似を知識の本体に置くのではなく、
**経験から関係構造を自己更新し続ける知能**
を目指す研究プロジェクトです。

現在の RISA は、
単なる知識グラフや単なる構造保存ではなく、

- 経験を状態遷移として蓄積する
- 反復する構造を共有パターンとして圧縮する
- 共活性と局所探索で必要な周辺だけを起動する
- 保存済み構造から未保存の関係を導ける方向へ進む

という設計思想を中心にしています。

特に重要なのは、

> 概念は最初から与えられる分類名ではなく、
> 多数の経験で繰り返し再利用された内部構造である

という立場です。

## 現在の状態

RISA はすでに
**MVP-1 の雛形実装が動作している段階**
です。

現時点では、

- 構造化イベントの学習
- 最小グラフ更新
- 共有構造パターンの学習
- 構造差分の保存
- 共活性ベースの局所探索
- 説明付き予測
- 簡易な構造代謝
- 学習前予測と観測比較による局所検証履歴
- effect 単位の検証履歴を共有構造の安定性へ反映
- 競合履歴を `co_activates_with` の可塑性へ反映
- 反復観測された `affects` 関係を安定化し、予測誤差で再可塑化
- 現在の世界モデルで過去経験を再生し、構造ドリフトを採用判断へ反映
- 自己生成したeffectを次のactive stateへ渡すdeployment replay
- active state dropoutによる構造頑健性の診断
- Replay失敗の種類に応じた局所適応候補の生成
- 観測contextだけを使う安全なPrimitive分裂と継続ルーティング
- actor-localな観測effectに基づく遷移修復
- actor-localな`precedes`と全体到着順`globally_precedes`の分離
- 個別経験を保持するevent-level temporal edgeと時系列説明
- `consumed_states`による状態消費を含むtrajectory
- `state_group_updates`による排他的状態置換
- `numeric_preconditions`と`state_variable_deltas`による部分消費
- unit・minimum・maximum付き量的状態と原子的更新
- 複数候補の状態・量的資源を混ぜずに追跡する分岐シミュレーション
- goal・資源cost・trajectory riskを分解表示する分岐評価
- AND/OR状態、数値条件、禁止状態を表すGoal Specification
- hard constraint違反branchの早期pruningと探索診断
- 初期action・状態・数値変数の介入案を比較するCounterfactual Planning
- Goal状態を出力するPrimitiveからの根拠付き介入候補生成
- 観測済み時間関係を逆向きにたどる複数step Goal Decomposition
- 提案action列をstep単位で検証するSequence-Constrained Simulation
- 複数のAND前提subplanを依存graphへ統合するConjunctive Planning
- 同じ前提を満たす複数producerを保持・実行比較するDisjunctive Planning
- 入れ子のAND/OR前提を深さ制限付きで展開するNested AND-OR Planning

まで実装されています。

つまり今は
「構想だけのリポジトリ」ではなく、
**小さく動く研究用コアを持ちながら設計思想を深めている段階**
です。

## 目標

最終目標は、
**動作する実用性のある知能**
を作ることです。

そのために、当面は次を重視します。

1. 経験を壊れにくい構造記憶として保持できる
2. 構造を圧縮し、再利用可能な内部単位を育てられる
3. 局所探索だけで予測と説明ができる
4. 新しい経験で継続的に改善できる
5. 学習器が変わっても知識基盤を継承しやすい

## 設計思想

RISA の現状の中核思想は次です。

- 知識は「保存された文章」ではなく「再利用可能な構造」である
- 構造を大量に保存するだけでは知識創発は起きない
- 重要なのは構造間で何を共有するかである
- 概念は明示分類の結果ではなく、内部構造の再利用から立ち上がる
- 推論は全探索ではなく局所活性化と局所探索で行う
- 例外は削除するのではなく、文脈分化や差分学習の材料として扱う
- 長期的には Transformer・SNN・Symbolic と共生する知能基盤を目指す

現在の実装では、この思想をいきなり完全実装するのではなく、

- `StructuralPattern`
- `StructureDelta`
- `co_activates_with`
- `recent_activity` / `energy` / `dormant`

のような最小要素から段階的に具体化しています。

## MVP-1 の範囲

MVP-1 では、
自由自然言語や生の画像・音声はまだ直接扱いません。

入力は JSON 形式の構造化イベントに限定し、
まずは次を安定して成立させます。

- イベントからノードとエッジを生成する
- 時系列反復から予測関係を学習する
- 類似経験から共有構造を圧縮する
- 共有構造間の差分を保存する
- 次に起きやすい effect を予測する
- 予測の根拠を構造として説明する

この段階での RISA は、
知覚器そのものではなく、
**状態遷移イベントの統合器・構造記憶・局所推論器**
として設計しています。

## 現在の実装内容

最小の研究用コアとして、以下を含みます。

- `risa/core`
  基本データ構造
- `risa/engine`
  学習、抽象化、予測、代謝、保存
- `risa/cli`
  `train`, `predict`, `inspect`, `forecast`, `compose`, `simulate`, `evaluate`, `plan`
- `data/toy_world.json`
  最初の学習データ
- `tests/`
  `unittest` ベースの最小テスト

現在動作している要素は次です。

- 構造化イベントの読み込み
- event node を含む最小グラフ更新
- action / effect パターン学習
- 文脈つき `StructuralPattern` の共有構造学習
- 反復する action / effect 遷移からの `StructuralPrimitive` 抽出
- Event を構成する primitive ID の保存
- 再利用・検証・圧縮代理値による primitive の provisional 採用
- Replay 成功率による primitive の再評価と段階的 Consolidation
- actor別の自己生成状態軌跡によるdeployment drift評価
- 通常Replayと分離したcontrolled perturbation replay
- `SPLIT_CONTEXT` / `REPAIR_TRANSITION` / `ADD_REDUNDANT_PATH`適応候補
- 証拠で分配可能な`SPLIT_CONTEXT`の自動実行
- precondition生成が観測済みの場合だけ行う`REPAIR_TRANSITION`
- 継続学習バッチを保存済み時系列へ接続する時間インデックス
- `event_precedes`を含む具体的な予測根拠パス
- forecast/composition/replayにおける`remove -> add`状態更新
- 観測済みgroup候補から旧状態を除去する排他更新
- CLIから指定できる量的state variable
- 適用後の`resulting_variables`を返すstateful forecast
- 採用済み primitive を時間的に合成する `compose` CLI
- 任意の `preconditions` を使う最小の `State_t + Action -> State_{t+1}` 表現
- CurrentState と action から複数の effect 候補を保つ `forecast` CLI
- 支持された少数候補も保持し、独立trajectoryとして展開する `simulate` CLI
- 目標達成を最優先に、confidence・cost・riskを比較する `evaluate` CLI
- 共有構造間の最小差分 `StructureDelta` の蓄積
- 共有 action / effect による簡易概念生成
- `actor`, `action`, `context` を入口にした簡易局所活性化
- 根拠イベントと根拠経路を含む予測説明
- `recent_activity`, `energy`, `dormant` を使った最小の構造代謝
- 同一イベントで共活性した構造に対する `co_activates_with` の強化
- `co_activates_with` を使った候補探索と説明補強
- 学習前予測と観測結果の差を蓄積する最小の prediction-validation history
- `Pattern` / `StructuralPattern` の `validation_score` を使った安定性補正
- 競合履歴による `competition_inhibits` 経路の説明と `co_activates_with` 可塑性補正
- `affects` edge の再現性に応じた reliability / plasticity 更新と説明経路への反映

## 最初の評価タスク

最初の実験は、
小さな toy world で行います。

```text
dog run -> fatigue_up
dog rest -> fatigue_down
human run -> fatigue_up
horse run -> fatigue_up
drink water -> thirst_down
```

この学習後に、

```text
wolf run -> ?
```

に対して

```text
fatigue_up
```

を予測し、
その理由を構造として返せれば、
RISA の最小原理が機能していると判断できます。

分岐状態遷移は次のコマンドで確認できます。

```bash
python3 -m risa.cli.main train data/branching_world.json --state-dir /tmp/risa-branch
python3 -m risa.cli.main simulate --start-action route \
  --start-variable energy=5 --max-steps 2 --max-branches 4 \
  --state-dir /tmp/risa-branch
```

`safe_path -> arrived_safe`と`fast_path -> arrived_fast`は別trajectoryとして保持され、
各候補のenergyも独立して更新されます。

分岐を評価して選択する場合は次を実行します。

```bash
python3 -m risa.cli.main evaluate --start-action route \
  --goal-state arrived_safe --goal-state arrived_fast \
  --require-state safe_path --min-variable energy=1 \
  --forbid-state fast_path \
  --avoid-state fast_path --start-variable energy=5 \
  --cost-variable energy=0.1 --max-steps 2 --state-dir /tmp/risa-branch
```

複数の`--goal-state`は代替目標（OR）、複数の`--require-state`はすべて必要な目標（AND）です。
`--min-variable`と`--max-variable`は終端数値条件、`--forbid-state`はtrajectory全体のhard constraintです。
到達可能な目標がない場合、
順位は診断用に返しますが`selected_branch_id`は`null`となります。

`evaluate`は`--forbid-state`へ入った候補を次stepへ展開しません。出力の`search_diagnostics`には、
展開候補数、constraint prune数、beam prune数が含まれます。比較用の`--avoid-state`はsoft riskなので、
候補を残したままpenaltyだけを付けます。

介入案を比較する場合はJSON配列で指定します。

```bash
python3 -m risa.cli.main plan --start-action route \
  --interventions data/branching_interventions.json \
  --require-state safe_path --goal-state arrived_safe --goal-state arrived_fast \
  --min-variable energy=2 --forbid-state fast_path \
  --start-variable energy=3 --max-steps 2 --state-dir /tmp/risa-branch
```

`plan`はbaselineも同じ表へ含め、各介入の開始action、状態追加・削除、変数上書き、明示costを比較します。
goalを達成できる介入だけが選択対象です。simulationは一時的で、学習済み構造を変更しません。

既存Primitiveから介入案を生成する場合、介入ファイルは不要です。

```bash
python3 -m risa.cli.main plan --start-action route --generate-interventions \
  --backward-depth 3 \
  --require-state safe_path --goal-state arrived_safe --goal-state arrived_fast \
  --min-variable energy=2 --forbid-state fast_path \
  --start-variable energy=3 --max-steps 2 --state-dir /tmp/risa-branch
```

生成案には`generated`、`generation_reason`、`evidence_primitive_ids`が付きます。現段階ではgoal状態を
直接出力するPrimitiveに加え、観測済み`precedes`で接続された前段Primitiveを`--backward-depth`まで
逆向きにたどります。chain候補には`suggested_action_sequence`が付きます。生成結果は実行命令ではなく
simulation対象の仮説です。

chain候補はplanner内で自由な次action探索へ戻さず、`suggested_action_sequence`を指定順に実行します。
各隣接actionの`precedes`、Primitiveのstate・数値条件、禁止状態を再検証し、途中失敗や不正edgeは
`sequence_failed_count`と`invalid_sequence_edge_count`へ記録します。

`data/conjunctive_world.json`では、`launch`に必要な`frame_ready`と`power_ready`を別々のsubplanとして解決し、
`prepare_frame -> prepare_power -> launch`へ線形化します。出力の`plan_graph.dependencies`から、どのPrimitiveが
どの前提状態を供給したか確認できます。

`data/disjunctive_world.json`では、`power_ready`を生成する安全・高速の2経路を同じ
`alternative_group_id`に保持します。各候補の`selected_producers`、必要資源、実行結果を比較し、目標制約を
満たす低cost経路を選びます。代替案を早期に一つへ潰さず、Sequence-Constrained Simulationで同じ条件下に
置いて選ぶことが、このMVPの中心です。

English: Producer alternatives are preserved as an OR group and compared by exact sequence simulation.

简体中文: 多个生产者方案作为OR组保留，并通过严格的序列模拟进行比较。

`data/nested_and_or_world.json`では、`launch`直下の`power_ready` producerは一つですが、そのproducerが要求する
`supply_ready`に太陽・電力網の2経路があります。探索は末端までAND前提をたどり、内側のORを2つのplan variantへ
展開します。`alternative_choice_count`、`dependency_depth`、`alternative_search_truncated`から探索範囲を確認できます。

English: Nested producer alternatives are expanded recursively with explicit depth and truncation metadata.

简体中文: 递归展开嵌套生产者替代方案，并显式记录深度与截断信息。

## 次の重点課題

次に深める優先度が高い領域は次です。

- `State -> Event -> State` 表現の強化
- 共有構造から未保存関係を導く推論ベンチマーク
- `shared relation unit` に相当する、より細かい再利用単位の導入
- 文脈分岐と例外処理の改善
- 目的・制約・不確実性を扱うbranch評価の拡張
- 独立subplanを全順列なしで実行するPartial-Order Plan Execution
- 共活性と信頼度に応じた探索半径の適応化
- Concept Cell の分裂 / 融合 / 休眠ルールの本格化

ロードマップ上では、
特に
**構造保存から構造共有へ、構造共有から知識創発へ**
進めることが最重要テーマです。

## ドキュメント

- [RISA Roadmap](docs/ROADMAP.md)
- [RISA MVP-1 Technical Design](docs/RISA-MVP-1-Technical-Design.md)
- [RISA Design Policy](docs/policy.md)
- [RISA Concept Formation and Multimodal Notes](docs/RISA-Concept-Formation-and-Multimodal-Notes.md)
- [RISA Structural Sharing and Knowledge Emergence](docs/RISA-Structural-Sharing-and-Knowledge-Emergence.md)
- [RISA Structural Interpolation and Smoothing](docs/RISA-Structural-Interpolation-and-Smoothing.md)
- [RISA Plasticity and Memory Reinforcement](docs/RISA-Plasticity-and-Memory-Reinforcement.md)
- [RISA Predictive Memory Transition and Structural Replay](docs/RISA-Predictive-Memory-Transition-and-Replay.md)
- [RISA Concept Cells and Structure Metabolism](docs/RISA-Concept-Cells-and-Structure-Metabolism.md)
- [RISA Constraints and Self-Organization Notes](docs/RISA-Constraints-and-Self-Organization-Notes.md)
- [RISA Search and Activation Strategy Notes](docs/RISA-Search-and-Activation-Strategy-Notes.md)
- [RISA Relation Field and Event Packets](docs/RISA-Relation-Field-and-Event-Packets.md)
- [RISA Transformer and SNN Relationship Notes](docs/RISA-Transformer-SNN-Relationship-Notes.md)
- [RISA Transformer Coevolution and Hypothesis Loop](docs/RISA-Transformer-Coevolution-and-Hypothesis-Loop.md)
- [RISA Mixture of Architectures and Dynamic Routing](docs/RISA-Mixture-of-Architectures-and-Dynamic-Routing.md)
- [RISA and SARA Engine Compatibility](docs/RISA-and-SARA-Engine-Compatibility.md)
- [RISA Open Source Landscape and Differentiation](docs/RISA-Open-Source-Landscape-and-Differentiation.md)
- [RISA vs ANN and SNN Assessment](docs/RISA-vs-ANN-and-SNN-Assessment.md)
- [RISA RAG and SNN Cache Analogy Notes](docs/RISA-RAG-and-SNN-Cache-Analogy-Notes.md)

## 実行例

```bash
python3 -m risa.cli.main train data/toy_world.json --state-dir state
python3 -m risa.cli.main predict --actor wolf --action run --state-dir state
python3 -m risa.cli.main train data/stateful_world.json --state-dir stateful-state
python3 -m risa.cli.main forecast --action use --current-state charged \
  --variable energy=5 --context robot --context power --state-dir stateful-state
python3 -m unittest discover -s tests
```

## ライセンス

未定
