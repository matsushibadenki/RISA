# RISA と SARA Engine の相性と役割分担メモ

## 1. 目的

この文書は、RISA と SARA Engine Project の相性を整理し、

- RISA を独立 AI として扱うべきか
- SARA の中の一部として扱うべきか
- どの層がすでに SARA 側にあり、どこに RISA 独自性を置くべきか

を明確にするための設計メモです。

現時点の結論は次です。

> RISA は SARA Engine と非常に相性が良く、むしろ SARA Engine そのものが RISA を実現するための土台になりうる

さらに一歩進めると、

> RISA は独立した AI 全体ではなく、SARA Engine の中核アルゴリズムである Concept Cell Ecosystem として位置付けた方が自然

と考えられます。

---

## 2. なぜ相性が良いのか

SARA Engine がこれまで目指してきた方向は、RISA の思想とかなり強く一致しています。

共通点:

- CPU 中心
- スパースイベント処理
- 局所学習
- 低消費電力志向
- Backpropagation 依存の低減
- イベント中心の世界モデル
- Semantic Echo Field
- Event Memory
- Concept Crystallization

RISA もまた、

- 状態遷移とイベントを最小単位に置く
- 全探索ではなく局所活性化を重視する
- 明示構造の継続更新を中心にする
- 中央最適化より局所自己組織化を重視する

という方向にあります。

つまり、両者は思想的にかなり整合しています。

---

## 3. 以前の見方と現在の見方

以前の見方:

> SARA Engine の中に RISA を組み込む

現在の見方:

> SARA Engine が土台であり、RISA はその中核的な概念形成・構造進化機構として実装される

この見直しは重要です。

前者では RISA が主で SARA が従ですが、後者では SARA がより大きな統合基盤になります。

---

## 4. SARA の既存構造と RISA の差分

SARA の現構想を単純化すると、次のように捉えられます。

```text
Multi Modal Input
  ->
Event Extraction
  ->
Event Memory
  ->
Temporal Relation Graph
  ->
Semantic Echo Field
  ->
Prediction
  ->
Concept Crystallization
```

この流れを見ると、RISA が新たに持ち込むべき核心は広範囲ではありません。

一番大きい差分は、

```text
Concept Cell Layer
```

です。

つまり、これまで

```text
Event
  ->
Relation Graph
```

として見ていたものを、

```text
Event
  ->
Concept Cell
  ->
Relation Graph
```

として捉え直す。

この変更によって、Graph を管理する主体が単なるデータ構造ではなく、Concept Cell 群になります。

---

## 5. SARA における RISA の最も自然な置き場所

現時点で最も自然な構成は、例えば次のようになります。

```text
                 Meta Controller
                        │
 ┌──────────────┼──────────────┐
 │              │              │
 ▼              ▼              ▼
Transformer     SNN        Symbolic
 │              │              │
 └──────┬───────┴───────┬──────┘
        ▼
 Event Extraction
        │
        ▼
 Event Queue
        │
        ▼
 Concept Cell Layer   ← RISA の中核
        │
        ▼
 Semantic Echo Field
        │
        ▼
 Temporal Relation Graph
        │
        ▼
 Concept Crystallization
        │
        ▼
 World Model
```

この見方では、

- Transformer は世界をイベントに変換する
- SNN はイベントを時間的・局所的にルーティングする
- RISA は Concept Cell の自己組織化で構造を育てる
- Semantic Echo Field は時間的共鳴の場になる
- SARA Engine は全体を統合する

という役割分担になります。

---

## 6. Semantic Echo Field との相性

Semantic Echo Field は、RISA と特に相性が良い要素です。

その理由は、Semantic Echo Field がすでに

```text
イベント
  ->
減衰
  ->
共鳴
  ->
消滅
```

という時間構造を持っているからです。

これはそのまま Concept Cell の局所判断材料として使える可能性があります。

例:

- 最近よく共鳴している -> 分裂候補
- 長く静かである -> 休眠候補
- 近傍と共鳴パターンが近い -> 融合候補

つまり、中央の Structure Editor がなくても、

> Semantic Echo の局所状態を見ながら Concept Cell が自律的に振る舞う

という形にできるかもしれません。

---

## 7. Event Memory は SARA の大きな武器

RISA 単体で考えると、構造更新に意識が寄りすぎて、経験の厚みが足りなくなりやすいです。

一方で SARA には Event Memory があります。

これは非常に大きい。

意味:

- Concept Cell が経験から育つ
- 単発イベントではなく反復イベントから概念が安定する
- 過去エピソードを使って予測と検証ができる
- Concept Crystallization の材料が Event Memory に蓄積される

RISA が「概念の自己組織化」であるなら、SARA はそのための経験基盤をすでに持っていると考えられます。

---

## 8. SNN は主役ではなく部品になりうる

以前は

```text
SARA = SNN ベースエンジン
```

として見る発想が強かったかもしれません。

しかし現在の整理では、

```text
SARA = 世界モデル OS
```

と捉える方が自然です。

この立場に立つと、

- Transformer は知覚ドライバ
- SNN はイベントルータ / 時間処理部品
- Symbolic は論理計算ライブラリ
- RISA は概念形成・構造進化カーネル

になります。

つまり、SNN も重要ではあるが、システム全体の本体ではなく一つの専門モジュールになります。

---

## 9. SARA を世界モデル OS と見る

この会話から得られる最も大きな見直しは、SARA の位置付けです。

SARA は単なる SNN エンジンではなく、

> 複数アーキテクチャを統合し、イベントから世界モデルを成長させる知能 OS

として再定義できるかもしれません。

このとき、

- Transformer
- SNN
- Symbolic
- Memory
- RISA

は SARA OS 上の機能モジュール、あるいはプラグインになります。

この見方は、以前整理した `Mixture of Architectures` ともよく整合します。

---

## 10. RISA の再定義

この前提に立つと、RISA の名前の位置付けも少し変わります。

以前:

> RISA = 独立した新方式 AI

現在:

> RISA = SARA Engine の中核アルゴリズムである Concept Cell Ecosystem

この再定義には実務上の利点があります。

- RISA の責務が明確になる
- SARA の既存資産を無理なく継承できる
- SNN や Transformer との上下関係で迷いにくくなる
- 実装境界が切りやすくなる

---

## 11. 設計への具体的含意

### 11.1 MVP-1 では SARA 全体を作ろうとしない

MVP-1 では SARA OS 全体の完成を目指す必要はありません。  
まずは RISA の最小コアとして、

- Event Queue
- Concept Cell Layer
- 簡易 Semantic Echo
- 小さな Relation Graph
- Predict / Explain

のループを成立させればよい。

### 11.2 ただし API 境界は SARA 前提で切る

早い段階から、

- Event Extraction
- Event Memory
- Concept Cell Layer
- Prediction
- Verification

を疎結合なモジュールとして切っておくと、将来 SARA へ統合しやすい。

### 11.3 Semantic Echo を Concept Cell 更新則へ使う

Concept Cell の

- 分裂
- 休眠
- 融合
- 活性化

を、Semantic Echo の局所統計から決められないかを重点研究テーマにする価値が高い。

### 11.4 World Model までを一貫した一本の流れとして扱う

RISA の評価を、単に「概念ができたか」で終わらせず、

```text
Event
  ->
Concept Cell
  ->
World Model
  ->
Prediction
  ->
Verification
  ->
Concept Evolution
```

の閉ループとして評価する必要がある。

---

## 12. 現時点の実務的結論

現時点では、次の整理が最も実用的です。

1. SARA を統合基盤として考える
2. RISA をその中の Concept Cell Ecosystem として定義する
3. SNN は時間処理とルーティングの専門部品として使う
4. Semantic Echo Field を構造代謝の局所判断材料として再利用する
5. MVP-1 では RISA コアを小さく実証し、あとで SARA 全体へ接続する

この見方を採ると、RISA と SARA は競合せず、

> SARA が土台で、RISA がその中核進化カーネル

という、かなり筋の良い関係に整理できます。
