RISAで追加するものは、ANNの「重み」やSNNの「スパイク」に相当する単一要素ではなく、**構造編集履歴**です。

かなり短く言うと、

```text
ANN = 重みを更新する
SNN = 重み + 発火タイミングを更新する
RISA = 関係構造 + 構造編集履歴を更新する
```

です。

RISAで中心になる追加要素はこの5つです。

```text
1. Relation
関係そのもの

2. Context
その関係が成立する文脈

3. Evidence
その関係を生んだ経験履歴

4. Plasticity Rule
関係をどう変えるかの更新則

5. Structural Operation
ノード生成・分裂・統合・削除・近道生成
```

つまりRISAでは、単に

```text
犬 ─ 哺乳類
```

を保存するのではなく、

```text
犬 ─ 哺乳類
  成立文脈: 生物分類
  根拠経験: 犬、猫、馬、牛に共通構造があった
  信頼度: 高い
  可塑性: 低い
  反例: なし
  更新履歴: 抽象化によって生成
```

のように保存します。

ANNでいう「重み」に一番近いものは、RISAでは **エッジの強さ** ではありません。むしろ、

```text
この関係は残すべきか
分裂すべきか
統合すべきか
上位概念を作るべきか
削除すべきか
```

を決める **構造可塑性メタデータ** です。

RISAの最小データ構造はこうなります。

```text
Node
  id
  label
  type
  context_tags
  birth_reason
  usage_count
  stability
  abstraction_level

Edge
  from
  to
  relation_type
  context
  evidence_count
  reliability
  plasticity
  contradiction_count
  last_used

StructuralMemory
  created_nodes
  merged_nodes
  split_nodes
  pruned_edges
  shortcut_edges
```

なので、RISAでANN/SNNに対して追加される核心は、

```text
構造そのものを変える操作
```

です。

具体的には、

```text
add_node        新しい概念を作る
add_edge        新しい関係を作る
split_node      概念を文脈ごとに分ける
merge_nodes     似た概念を統合する
abstract_node   上位概念を作る
prune_edge      不要な関係を削る
shortcut_edge   頻出経路に近道を作る
```

です。

たとえばANNなら、

```text
犬 → 動物
```

の対応を重みの中に分散保存します。

SNNなら、それに時間的発火パターンが加わります。

RISAなら、

```text
犬
猫
馬
牛
```

の共通構造を見つけて、

```text
哺乳類
```

という**新しいノードを実際に生成**します。

ここが本質的に違います。

一言でまとめると、

```text
ANNに追加されるもの = 重み
SNNに追加されるもの = スパイク時間
RISAに追加されるもの = 構造編集操作
```

です。

もっと正確には、

```text
RISA = 動的グラフ + 文脈 + 根拠履歴 + 構造可塑性 + 自己圧縮
```

です。
