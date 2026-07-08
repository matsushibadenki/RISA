# RISA MVP-1 技術設計書

## 1. 目的

RISA MVP-1 の目的は、RISA の中核仮説である

> 知能の最小単位はノードではなく、関係更新である

を、**小さな人工世界における実用的な動作系**として検証することです。

この段階では自然言語の流暢な対話や大規模知識は目指しません。まずは以下を安定して実現することをゴールとします。

- 構造化イベント列を受け取れる
- イベントからノードと関係を生成できる
- 反復パターンを蓄積できる
- 類似したイベントから簡単な抽象概念を作れる
- 未知の近縁イベントに対して次イベントを予測できる
- 予測理由を経路として説明できる

MVP-1 の最終目標は、研究用デモではなく、**実際に繰り返し入力すると振る舞いが改善していく最小の RISA コア**を作ることです。

---

## 2. MVP-1 のスコープ

### 2.1 含めるもの

- 手入力または JSON ファイル入力の構造化イベント
- 動的グラフの生成と更新
- 局所的な関係強化とパターン蓄積
- 単純な抽象ノード生成
- 次イベント予測
- 推論経路の説明
- 永続化
- CLI による実行

### 2.2 含めないもの

- 自由入力の自然言語理解
- 画像、音声、センサ入力
- 反実仮想シミュレーション
- 文脈分裂による例外処理の完全対応
- 複雑な行動計画
- 分散実行
- GUI

ただし、画像や音声を永続的にスコープ外へ置くわけではありません。MVP-1 では「生データを直接扱わず、構造化イベントに変換された後の状態遷移だけを扱う」という境界を明確にするために除外しています。将来方針は [RISA 概念形成とマルチモーダル学習メモ](RISA-Concept-Formation-and-Multimodal-Notes.md) に整理します。

### 2.3 成功条件

MVP-1 は次を満たせば成功とみなします。

- 20 から 200 件程度のイベント列で安定動作する
- 未知の主体に対して既知パターンを転用できる
- 抽象ノードを少なくとも 1 種類自動生成できる
- 予測に理由グラフを付けられる
- 同一入力に対して再現可能な結果が得られる

---

## 3. 研究仮説を実装仮説へ落とす

RISA の思想は広いですが、MVP-1 では以下の実装仮説に縮約します。

### 3.1 実装仮説

1. 経験は「イベント」として離散化できる
2. イベント間の反復から、因果に近い遷移パターンを抽出できる
3. 類似イベント群から、上位概念ノードを生成できる
4. 予測は重み付き文生成ではなく、局所グラフ探索で実現できる
5. 説明可能性は、活性化経路を保存することで確保できる

補足:

ここでいう「イベント」は、単なる名詞の並びではなく、実質的には `State -> Event -> State` の状態遷移を縮約したものとみなします。この立場は将来の概念形成やマルチモーダル拡張に重要です。

### 3.2 MVP-1 における知能の定義

MVP-1 では、RISA の知能を次のように定義します。

- 経験を構造に変換する
- 構造を圧縮して再利用可能にする
- 新しい入力に対して、近い過去から次状態を予測する
- 予測の根拠を構造として返す

---

## 4. システム境界

MVP-1 の責務は RISA-Core のうち最小限に限定します。

```text
Input Events
  ->
Event Parser
  ->
Event Graph Builder
  ->
Relation Substrate
  ->
Pattern / Abstraction Updater
  ->
Predictor
  ->
Explanation
```

### 4.1 外部に置くもの

- 入力イベントの作成
- 実験データの選定
- 学習結果の可視化
- 将来の自然言語パーサー

### 4.2 内部に置くもの

- イベント正規化
- ノードとエッジの生成
- 経験蓄積
- パターン蓄積
- 抽象化
- 予測
- 説明
- 保存と読み込み

---

## 5. ドメイン前提

MVP-1 は最初から一般世界を扱わず、**小さな人工世界**を対象にします。最初の推奨ドメインは「生物の行動と状態変化」です。

例:

- 走る -> 疲れる
- 休む -> 疲労が減る
- 飲む -> 喉の渇きが減る
- 食べる -> 空腹が減る
- 雨が降る -> 地面が濡れる

### 5.1 理由

- 因果と状態変化が明確
- ノード型を限定しやすい
- 予測の正誤を判定しやすい
- 抽象概念を作りやすい

---

## 6. データモデル

MVP-1 では、思想を守りつつも実装負荷を下げるため、データ構造を絞ります。

### 6.1 Node

```python
Node(
    id: str,
    kind: str,
    label: str,
    attributes: dict[str, str],
    abstraction_level: int,
    created_at: int,
    usage_count: int,
    stability: float,
    recent_activity: float,
    energy: float,
    last_activated_at: int,
    dormant: bool,
)
```

`recent_activity`, `energy`, `dormant` は、将来の Concept Cell 的な局所自律へつなぐための最小メタボリズム要素です。MVP-1 では完全な分裂・融合までは行わず、まずは「使われると活性化し、接続維持コストがあると休眠しやすい」という簡易制約を入れます。

#### kind の候補

- `entity`
- `process`
- `state`
- `concept`
- `pattern`

### 6.2 Edge

```python
Edge(
    source: str,
    target: str,
    relation_type: str,
    context_tags: tuple[str, ...],
    evidence_count: int,
    reliability: float,
    plasticity: float,
    last_updated: int,
)
```

#### relation_type の候補

- `participates_in`
- `affects`
- `precedes`
- `causes`
- `instance_of`
- `similar_to`
- `abstracts_to`
- `predicts`

### 6.3 Event

MVP-1 では自然言語を避け、イベントを最初から構造化します。

```python
Event(
    id: str,
    timestamp: int,
    actor: str,
    action: str,
    target: str | None,
    observed_effects: list[str],
    context_tags: list[str],
)
```

### 6.4 Episode

連続イベントをひとまとまりの経験列として扱います。

```python
Episode(
    id: str,
    events: list[Event],
    source: str,
)
```

### 6.5 Pattern

MVP-1 の抽象化と予測を安定化させるため、グラフ本体とは別に集計オブジェクトを持ちます。

```python
Pattern(
    id: str,
    signature: str,
    event_count: int,
    actors: set[str],
    actions: set[str],
    effects: set[str],
    support: int,
)
```

### 6.6 Graph Store

内部表現は次の辞書ベースで十分です。

```python
GraphStore(
    nodes_by_id: dict[str, Node],
    edges_by_key: dict[tuple[str, str, str], Edge],
    adjacency_out: dict[str, set[tuple[str, str]]],
    adjacency_in: dict[str, set[tuple[str, str]]],
)
```

理由:

- 実装が単純
- シリアライズしやすい
- 局所探索が高速
- 将来 NetworkX や Rust 実装へ置き換えやすい

---

## 7. 入力仕様

MVP-1 の標準入力は JSON Lines または JSON 配列とします。

### 7.1 単一イベント例

```json
{
  "id": "e001",
  "timestamp": 1,
  "actor": "dog",
  "action": "run",
  "target": null,
  "observed_effects": ["fatigue_up"],
  "context_tags": ["animal", "movement"]
}
```

### 7.2 エピソード例

```json
[
  {
    "id": "e001",
    "timestamp": 1,
    "actor": "dog",
    "action": "run",
    "target": null,
    "observed_effects": ["fatigue_up"],
    "context_tags": ["animal", "movement"]
  },
  {
    "id": "e002",
    "timestamp": 2,
    "actor": "dog",
    "action": "rest",
    "target": null,
    "observed_effects": ["fatigue_down"],
    "context_tags": ["animal", "recovery"]
  }
]
```

### 7.3 制約

- `actor` と `action` は必須
- `observed_effects` は 1 個以上を推奨
- `timestamp` は同一エピソード内で単調増加
- `context_tags` は 0 個以上

---

## 8. コアアーキテクチャ

推奨ディレクトリ構成は以下です。

```text
risa/
  core/
    models.py
    graph_store.py
  engine/
    event_parser.py
    graph_builder.py
    learner.py
    abstractor.py
    predictor.py
    explainer.py
    persistence.py
  cli/
    main.py
  data/
    toy_world.json
  tests/
    test_graph_builder.py
    test_predictor.py
    test_abstractor.py
```

### 8.1 モジュール責務

#### `models.py`

- `Node`
- `Edge`
- `Event`
- `Episode`
- `Pattern`

#### `graph_store.py`

- ノード追加
- エッジ追加
- 隣接探索
- ノード検索
- シリアライズ

#### `event_parser.py`

- JSON から `Event` / `Episode` を生成
- バリデーション

#### `graph_builder.py`

- イベントから局所構造を生成
- ノードの再利用判定
- 初期エッジ生成

#### `learner.py`

- 反復イベントの集計
- `precedes` / `predicts` / `causes` 候補更新
- 信頼度更新

#### `abstractor.py`

- 類似パターンの発見
- 上位概念ノード生成
- `instance_of` / `abstracts_to` 更新

#### `predictor.py`

- 入力イベントから局所探索
- 候補予測をスコアリング
- 次イベントを返す

#### `explainer.py`

- 予測に使った経路を復元
- 根拠イベントと抽象ノードを返す

#### `persistence.py`

- JSON 保存
- JSON 読み込み

#### `cli/main.py`

- `train`
- `predict`
- `inspect`

---

## 9. 学習フロー

MVP-1 の学習はイベントごとの局所更新で行います。

### 9.1 全体フロー

```text
イベント入力
  ->
正規化
  ->
イベントノード群の取得または生成
  ->
イベント内部の関係生成
  ->
直前イベントとの遷移関係更新
  ->
パターン集計更新
  ->
抽象化候補の判定
  ->
必要なら抽象ノード生成
  ->
保存
```

### 9.2 イベント内部の基本構造

イベント `dog run -> fatigue_up` に対して最低でも次を作ります。

```text
dog --participates_in--> run
run --affects--> fatigue_up
dog --context--> animal
run --context--> movement
```

MVP-1 では `context` をエッジ属性に持たせてもよく、独立ノードにはしなくてよいです。

### 9.3 連続イベントからの遷移学習

同一 actor に対し、時間的に隣接するイベントの action/effect を結びます。

例:

```text
dog run -> fatigue_up
dog rest -> fatigue_down
```

この場合、以下の候補が増えます。

```text
run --precedes--> rest
run --predicts--> fatigue_up
rest --predicts--> fatigue_down
```

### 9.4 信頼度更新

MVP-1 では複雑な最適化ではなく、単純な集計ベースとします。

例:

```text
reliability = evidence_count / opportunity_count
```

`opportunity_count` は「その action が観測された回数」とします。

### 9.5 可塑性更新

MVP-1 では以下の単純ルールで十分です。

- evidence が増えるほど plasticity は下がる
- 最近更新された関係は少し plasticity を保つ
- 矛盾管理は MVP-2 で本格導入する

---

## 10. 抽象化設計

抽象化は RISA の差別化要素なので、MVP-1 でも最低限入れます。ただし複雑な概念発見ではなく、**共有効果による上位概念化**に限定します。

### 10.1 抽象化の最小条件

次の条件を満たしたとき、抽象概念候補を作ります。

- 異なる actor が 2 種類以上ある
- 同じ action を行っている
- 同じ observed_effects を持つ
- context_tags に共通要素がある

加えて、中長期的には「圧縮できる」だけでなく「その概念を導入すると予測が改善する」ことも概念採用条件に含めるべきです。MVP-1 ではまず support と共有効果を使った簡易版を採用し、将来拡張の詳細は [RISA 概念形成とマルチモーダル学習メモ](RISA-Concept-Formation-and-Multimodal-Notes.md) に委ねます。

例:

```text
dog run -> fatigue_up
human run -> fatigue_up
horse run -> fatigue_up
```

このとき、`animal_runner` のような中間概念を生成できます。

### 10.2 抽象ノードの形

```python
Node(
    id="concept:animal_movement_fatigue",
    kind="concept",
    label="animal_movement_fatigue",
    attributes={
        "shared_action": "run",
        "shared_effect": "fatigue_up"
    },
    abstraction_level=1,
    ...
)
```

### 10.3 抽象化で張る関係

```text
dog   --instance_of--> concept:animal_movement_fatigue
human --instance_of--> concept:animal_movement_fatigue
horse --instance_of--> concept:animal_movement_fatigue
concept:animal_movement_fatigue --predicts--> fatigue_up
concept:animal_movement_fatigue --participates_in--> run
```

### 10.4 命名方針

MVP-1 では人間らしいラベル生成は不要です。内部ラベルは機械生成でよいです。

例:

- `concept:shared_run_fatigue_up:001`
- `pattern:run_to_fatigue_up`

---

## 11. 予測設計

MVP-1 の予測は「次に起こりやすい effect または event を返す」ことに絞ります。

### 11.1 入力

予測入力は少なくとも以下を受け取ります。

```python
PredictionQuery(
    actor: str,
    action: str,
    target: str | None = None,
    context_tags: list[str] = [],
)
```

### 11.2 探索優先順位

1. actor に直接結び付く過去パターン
2. 同じ action のパターン
3. actor が属する抽象概念のパターン
4. 同じ context を持つ近傍パターン

MVP-1 の実装では、ここを「簡易局所活性化」として扱います。つまり全パターンを走査するのではなく、`actor`, `action`, `context` から引ける候補集合を先に集め、その局所集合だけを比較します。

### 11.3 スコアリング

MVP-1 の簡易スコアは以下で十分です。

```text
PredictionScore =
  0.45 * direct_match_score
  + 0.30 * action_pattern_score
  + 0.20 * concept_support_score
  + 0.05 * recency_score
```

#### direct_match_score

- 同一 actor + action の履歴一致度

#### action_pattern_score

- action に対する effect の一般頻度

#### concept_support_score

- actor が属する抽象概念に支えられている度合い

#### recency_score

- 最近観測されたパターンを少し優先する補助値

### 11.4 出力

```python
PredictionResult(
    predicted_effects: list[str],
    score: float,
    supporting_paths: list[list[str]],
    evidence_event_ids: list[str],
)
```

### 11.5 期待される動作

学習済み:

```text
dog run -> fatigue_up
human run -> fatigue_up
horse run -> fatigue_up
```

問い合わせ:

```text
wolf run -> ?
```

期待:

```text
fatigue_up
```

理由:

- `run` の一般パターン
- `animal` 文脈の共有
- 抽象概念への近接

---

## 12. 説明設計

RISA の重要価値である説明可能性は MVP-1 から実装します。

### 12.1 出力形式

予測時に、少なくとも以下を返します。

- 予測結果
- 使用した主要ノード
- 使用した主要エッジ
- 根拠イベント
- 抽象ノードの有無

### 12.2 説明例

```text
Prediction: fatigue_up

Reasoning path:
wolf
  -> run
  -> concept:shared_run_fatigue_up:001
  -> fatigue_up

Evidence:
- dog run -> fatigue_up
- human run -> fatigue_up
- horse run -> fatigue_up
```

### 12.3 実装方針

- `predictor` がスコアリング時の候補経路を保持する
- 最終選択時にトップ経路のみ `explainer` へ渡す
- 初期段階では全文生成せず、構造説明を返す

---

## 13. 永続化設計

MVP-1 では可搬性を優先し、JSON ベースで保存します。

### 13.1 保存対象

- ノード一覧
- エッジ一覧
- パターン一覧
- メタ情報

### 13.2 推奨ファイル

```text
state/
  graph_nodes.json
  graph_edges.json
  patterns.json
  metadata.json
```

### 13.3 メタ情報例

```json
{
  "version": "0.1.0",
  "event_count": 128,
  "node_count": 53,
  "edge_count": 121,
  "concept_count": 4,
  "last_updated": 1720425600
}
```

---

## 14. CLI 設計

最初の利用形態は CLI が最も効率的です。

### 14.1 コマンド

```bash
python -m risa.cli.main train data/toy_world.json
python -m risa.cli.main predict --actor wolf --action run --context animal
python -m risa.cli.main inspect --node concept:shared_run_fatigue_up:001
```

### 14.2 `train`

- 入力ファイルを読む
- イベント列を学習する
- 結果を保存する
- 学習統計を表示する

### 14.3 `predict`

- 現在の状態を読む
- クエリを評価する
- 予測と理由を表示する

### 14.4 `inspect`

- ノードやエッジ、概念の内部構造を表示する

---

## 15. テスト設計

MVP-1 は理論よりも振る舞い検証が重要です。最低限、以下の自動テストが必要です。

### 15.1 単体テスト

- イベントが正しく読み込まれる
- ノード重複が発生しない
- エッジの evidence_count が正しく増える
- 予測スコアが決定的に計算される
- 抽象ノードが条件成立時のみ作られる

### 15.2 結合テスト

入力:

```text
dog run -> fatigue_up
human run -> fatigue_up
horse run -> fatigue_up
```

期待:

- `run` に対する `fatigue_up` 予測が得られる
- 抽象概念が 1 つ以上作られる
- `wolf run` で `fatigue_up` を返す

### 15.3 回帰テスト

- 同じデータで再学習しても結果が不安定に変わらない
- 保存後に再読込しても予測が一致する

---

## 16. 実装優先順位

### Phase 1: 動く最小骨格

- `Event`, `Node`, `Edge`, `GraphStore`
- JSON 入力
- ノードとエッジ生成
- 保存

### Phase 2: 学習

- 連続イベント遷移の蓄積
- `predicts` 更新
- 信頼度更新

### Phase 3: 予測

- クエリ入力
- 局所探索
- スコアリング
- 結果表示

### Phase 4: 抽象化

- 共有 action/effect の検出
- 概念ノード生成
- `instance_of` 接続

### Phase 5: 説明

- 根拠イベント提示
- 経路表示

---

## 17. 想定リスク

### 17.1 ノード爆発

原因:

- actor/action/effect をそのまま増やし続ける

対策:

- MVP-1 ではラベル正規化を必須にする
- 同義語統合は手動辞書で対応する
- context をノード化しすぎない

### 17.2 抽象化の暴走

原因:

- 表面的な一致だけで概念を作る

対策:

- 2 件ではなく 3 件以上の support を要求する設定を用意する
- 共有 effect と共有 context の両方を条件にする

### 17.3 予測の過学習

原因:

- 直近のイベントだけを強く見すぎる

対策:

- actor 直結パターンと action 一般パターンの両方を使う
- recency の比重を小さく保つ

### 17.4 実用性の不足

原因:

- 理論的には面白いが動作が弱い

対策:

- 「何件学習すると何を予測できるか」をベンチマーク化する
- まずは toy world で確実に勝ち筋を作る

---

## 18. 実用化に向けた判断基準

MVP-1 は最終形ではありませんが、実用的に動作することを当面の最終目標とするなら、次の判断基準を持つべきです。

### 18.1 続行ライン

- 予測がルールベースを超えて一般化する
- 抽象ノードが再利用される
- 説明が人間に理解可能
- 新規データ追加で性能が改善する

### 18.2 見直しライン

- 予測が単純集計以上に伸びない
- 抽象化がノイズしか生まない
- ノード管理コストが急増する
- 実装の大半が例外処理に費やされる

---

## 19. MVP-1 完了定義

以下を満たした時点で MVP-1 完了とします。

- CLI で学習、予測、状態確認ができる
- toy world データセットが同梱されている
- `wolf run -> fatigue_up` のような近縁一般化が成功する
- 抽象ノードが自動生成される
- 予測理由をイベント経路として表示できる
- 保存と再読込後も同じ予測を返せる
- 単体テストと結合テストがある

---

## 20. 次段階への接続

MVP-1 の次は MVP-2 として、以下を追加するのが自然です。

- 例外処理のための文脈分裂
- 矛盾管理
- より明確な因果方向推定
- 睡眠処理による圧縮
- 自然言語から構造化イベントへの変換

さらにその先では、映像・音・行動を統一的な状態遷移表現へ落とすマルチモーダル化が重要になります。この方針と論点は [RISA 概念形成とマルチモーダル学習メモ](RISA-Concept-Formation-and-Multimodal-Notes.md) に記録します。

MVP-1 の価値は、RISA の全構想を一気に作ることではありません。**動的グラフだけで予測と抽象化が実用的に回り始めるかを、最小の機械で確かめること**にあります。
