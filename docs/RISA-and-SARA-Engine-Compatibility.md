# RISA と SARA Engine の相性と役割分担メモ

> 2026-09-18 時点の扱い: 以下は初期の設計仮説であり、SARA との統合を決定した文書ではない。RISA は現在、構造化 Event を入力する独立した研究コアである。G3.2 の機構機会 gate は未通過で、G4 の再帰的概念形成も未実証。第 13 節の検証条件を満たすまでは、時間スケール分担、SARA を基盤とする構成、双方向接続の利益を実証済みとして扱わない。

## 1. 目的

この文書は、RISA と SARA Engine Project の相性を整理し、

- RISA を独立 AI として扱うべきか
- SARA の中の一部として扱うべきか
- どの層がすでに SARA 側にあり、どこに RISA 独自性を置くべきか

を明確にするための設計メモです。

この文書を作成した時点の設計仮説は次です。

> RISA は SARA Engine と非常に相性が良く、むしろ SARA Engine そのものが RISA を実現するための土台になりうる

さらに一歩進めた未検証の構想として、

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

当初の拡張案:

> SARA Engine が土台であり、RISA はその中核的な概念形成・構造進化機構として実装される

この拡張案は比較対象として残します。

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

当初の拡張案:

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

初期構想としては、次の役割分担が考えられます。ただし、現在の実装や実験結果から統合方式を確定できません。

1. SARA を統合基盤として考える
2. RISA をその中の Concept Cell Ecosystem として定義する
3. SNN は時間処理とルーティングの専門部品として使う
4. Semantic Echo Field を構造代謝の局所判断材料として再利用する
5. MVP-1 では RISA コアを小さく実証し、あとで SARA 全体へ接続する

この見方を採ると、RISA と SARA は競合せず、

> SARA の高速な信号処理と RISA の構造学習を接続できるかは、将来の独立した実験課題

G3.2〜G4 では RISA 単体の機構効果と構造凝縮を先に測ります。

## 13. 双方向接続の検証契約（[Later]）

この意見から採用するのは、反復された下位パターンを構造候補へ昇格させ、検証済み構造を下位の選択へ返す、という**反証可能なインターフェース仮説**です。SARA の具体的な内部表現や実時間特性は、この RISA リポジトリでは確認されていません。

1. **上り方向:** 外部のパターン検出器は、候補 Event または episode signature として、出典、観測時刻、episode ID、観測 mask、信頼度を渡す。RISA の採用条件と lineage 分離を緩めず、同じ入力情報量の構造化 Event 対照と比べて、未知 episode の予測・転移、保存量、候補数を測る。反復頻度だけで concept と認定しない。
2. **下り方向:** RISA は、採用済み構造の ID、適用条件、信頼度、失効条件を提案 signal として返す。受信側はその signal を無視できる。固定 routing、無作為 routing、同等費用の単純な統計的 prior と比べ、独立 episode で成功率、誤 routing、遅延、計算量を測る。下り信号を RISA の教師ラベルへ戻して評価を循環させない。
3. **比較条件:** RISA 単体、SARA 側単体、上りのみ、下りのみ、双方向の5条件を同じ episode と入出力予算で比較する。SARA 側の実装が利用可能になるまでこの比較を実行済みと記さない。SNN や perception adapter を G3.2 の失敗した対照を救うために追加しない。
4. **採否:** G3.2 の機構効果と G4 の独立 held-out 階層形成が評価された後、事前固定した seed と閾値で、双方向接続が未知 episode の成功率または費用を改善し、誤一般化を悪化させない場合だけ統合候補にする。ミリ秒・秒・日という境界は測定対象であり、設計定数にしない。
