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
  `train`, `predict`, `inspect`
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
- 採用済み primitive を時間的に合成する `compose` CLI
- 任意の `preconditions` を使う最小の `State_t + Action -> State_{t+1}` 表現
- CurrentState と action から複数の effect 候補を保つ `forecast` CLI
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

## 次の重点課題

次に深める優先度が高い領域は次です。

- `State -> Event -> State` 表現の強化
- 共有構造から未保存関係を導く推論ベンチマーク
- `shared relation unit` に相当する、より細かい再利用単位の導入
- 文脈分岐と例外処理の改善
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
python3 -m unittest discover -s tests
```

## ライセンス

未定
