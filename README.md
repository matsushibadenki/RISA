# RISA

RISA は **Relationally Involving Self-organizing Architecture** の略で、重みを学習するのではなく、**関係構造そのものを更新し続ける AI** を目指す研究プロジェクトです。

このリポジトリでは、まず小さな人工世界を対象に、動的グラフだけで

- 経験の蓄積
- 反復パターンの学習
- 抽象概念の生成
- 次イベント予測
- 推論経路の説明

ができるかを検証します。

## 現在の状態

現在は構想整理フェーズで、コア実装はこれからです。公開時点では、設計思想と MVP-1 の技術設計を主な成果物として含んでいます。

## 目標

当面の最終目標は、**実用的に動作する最小の RISA コア**を作ることです。

そのために、最初のマイルストーンとして以下を目指します。

1. 構造化イベント列を学習できる
2. 動的グラフを更新できる
3. 小さな抽象概念を自動生成できる
4. 未知の近縁イベントを予測できる
5. 予測の理由を構造として説明できる

## ドキュメント

- [RISA MVP-1 Technical Design](docs/RISA-MVP-1-Technical-Design.md)
- [RISA Concept Formation and Multimodal Notes](docs/RISA-Concept-Formation-and-Multimodal-Notes.md)
- [RISA Design Policy](docs/policy.md)
- [RISA vs ANN and SNN Assessment](docs/RISA-vs-ANN-and-SNN-Assessment.md)
- [RISA Search and Activation Strategy Notes](docs/RISA-Search-and-Activation-Strategy-Notes.md)
- [RISA Relation Field and Event Packets](docs/RISA-Relation-Field-and-Event-Packets.md)
- [RISA Transformer and SNN Relationship Notes](docs/RISA-Transformer-SNN-Relationship-Notes.md)
- [RISA RAG and SNN Cache Analogy Notes](docs/RISA-RAG-and-SNN-Cache-Analogy-Notes.md)
- [RISA Concept Cells and Structure Metabolism](docs/RISA-Concept-Cells-and-Structure-Metabolism.md)
- [RISA Constraints and Self-Organization Notes](docs/RISA-Constraints-and-Self-Organization-Notes.md)
- [RISA Transformer Coevolution and Hypothesis Loop](docs/RISA-Transformer-Coevolution-and-Hypothesis-Loop.md)
- [RISA Mixture of Architectures and Dynamic Routing](docs/RISA-Mixture-of-Architectures-and-Dynamic-Routing.md)
- [RISA Open Source Landscape and Differentiation](docs/RISA-Open-Source-Landscape-and-Differentiation.md)
- [RISA and SARA Engine Compatibility](docs/RISA-and-SARA-Engine-Compatibility.md)

## MVP-1 の範囲

MVP-1 では自由な自然言語や画像入力は扱いません。まずは JSON 形式の構造化イベントを入力とし、次の能力だけを確実に作ります。

- イベントからノードとエッジを生成する
- 時系列の反復から予測関係を作る
- 類似イベント群から上位概念ノードを作る
- 次に起きやすい effect を予測する
- その理由を経路として返す

## 実装方針

初期実装では、複雑な最適化や大規模分散は行いません。まずは Python でシンプルに作り、以下を優先します。

- データ構造が明確であること
- 学習更新が追跡できること
- 予測理由が説明できること
- 再学習時に結果が再現できること

## 最初の評価タスク

最初の実験は、以下のような toy world で行う想定です。

```text
dog run -> fatigue_up
dog rest -> fatigue_down
human run -> fatigue_up
horse run -> fatigue_up
drink water -> thirst_down
```

この学習後に、たとえば

```text
wolf run -> ?
```

に対して

```text
fatigue_up
```

を予測できれば、RISA の最小原理が動いていると判断できます。

## リポジトリ方針

- まずは研究として筋の良い最小系を作る
- 思想よりも動作検証を優先する
- 不要に複雑な実装へ飛ばない
- 各段階を小さく完結させながら拡張する

## 次の実装候補

- `risa/core` の基本モデル定義
- グラフストア
- JSON イベントローダ
- 学習 CLI
- 予測 CLI
- toy world データセット

次に深める候補は以下です。

- `State -> Event -> State` の表現強化
- `圧縮 + 予測改善` に基づく概念採用
- 文脈分岐と例外処理
- Relation Attention に相当する探索制御
- 高速イベント層と低速概念層の分離
- Concept Cell の分裂 / 融合 / 休眠ルールの本格化

## 現在の雛形

最小の雛形として、以下を追加済みです。

- `risa/core`: 基本データ構造
- `risa/engine`: 入力、学習、抽象化、予測、保存
- `risa/cli`: `train`, `predict`, `inspect`
- `data/toy_world.json`: 最初の学習データ
- `tests/`: 標準ライブラリ `unittest` による最小テスト

現時点では、次の要素まで動作します。

- 構造化イベントの読み込み
- event node を含む最小グラフ更新
- action/effect パターン学習
- 共有 action/effect による簡易概念生成
- `actor`, `action`, `context` を入口にした簡易局所活性化
- 根拠イベントを含む予測説明
- node ごとの `recent_activity`, `energy`, `dormant` を使った最小の構造代謝

## 実行例

```bash
python3 -m risa.cli.main train data/toy_world.json --state-dir state
python3 -m risa.cli.main predict --actor wolf --action run --state-dir state
python3 -m unittest discover -s tests
```

## ライセンス

未定
