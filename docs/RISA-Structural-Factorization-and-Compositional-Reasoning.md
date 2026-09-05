# RISA 構造因数分解と合成推論

> 2026-09-05: 現行の実装評価は[設計評価](RISA-Structural-AI-Assessment-2026-09-05.md)、優先順位は[ROADMAP](ROADMAP.md)、規範は[policy §0](policy.md)を参照。この文書の歴史的な仕様・仮説は、現行実装の完全性や性能の実証ではありません。
>
> Current assessment, priorities and rules are in the linked documents. Historical specifications/hypotheses here do not establish current completeness or performance.
>
> 当前评估、优先级与规则以上述链接为准。本文历史规格与假设不证明当前实现完整性或性能。

## 1. 目的 / Purpose / 目的

日本語:
この文書は、RISA が大量の完成済み知識を検索するだけでなく、
経験や問題を再利用可能な構造単位へ分解し、その組合せから未保存の遷移・関係・解答候補を導けるかを研究するための設計メモです。

English:
This note defines a research direction in which RISA factors experiences and problems into reusable structural units,
then composes them to infer unstored transitions, relations, or answer candidates.

简体中文：
本文定义一项研究方向：RISA 将经验和问题分解为可复用的结构单元，
再通过组合这些单元推导未被显式存储的状态迁移、关系或答案候选。

## 2. 中核仮説

RISA が扱うべきなのは、何億もの完成した構造の全探索ではありません。
中核仮説は次です。

```text
問題 / 経験
  -> 構造因数分解
  -> 局所的に活性化した再利用単位
  -> 制約つき合成探索
  -> 候補遷移・解答
  -> 予測誤差と再生安定性による検証
```

例えば「支持が失われた対象が下方へ移動する」という経験は、
対象名に依存せず、`support -> support_loss -> directional_transition` のような関係・変換単位の組合せとして表す。
鳥、コップ、荷物などが異なっても、役割と状態遷移が一致する範囲で同じ単位を再利用できる。

## 3. StructuralPrimitive の作業定義

`StructuralPrimitive` は絶対的に最小な記号ではない。
それ以上分解すると意味を失うかではなく、分解によって実用上の性質が失われるかで評価する。

最小候補の情報は次です。

```text
StructuralPrimitive
  id
  relation / transformation type
  role bindings
  input-state constraints
  output-state constraints
  temporal constraints
  context constraints
  support and validation evidence
```

候補は次の四条件を満たすときだけ長期構造へ昇格させる。

1. 再利用性: 異なる経験で反復して利用される。
2. 再構成性: 他の単位との合成で元の経験構造を十分に復元できる。
3. 予測有用性: 次状態・未知関係・探索候補の精度を改善する。
4. 圧縮性: 経験集合の記述長を短くする。

このため、`因数分解` は固定の正解を出す前処理ではなく、複数仮説を比較する継続学習問題である。

## 4. 探索制約

合成空間は爆発するため、RISA は primitive の全組合せを試さない。
候補は以下で局所化する。

- 現在状態と目標状態
- 活性化済み action / effect / concept / context
- 役割の型整合性
- 時間順序と因果順序
- reliability、plasticity、validation、competition の履歴

探索出力には、合成した primitive と各制約を説明経路として残す。
候補が観測と矛盾すれば、独立した真偽判定器ではなく予測誤差・競合・可塑性を通じて弱める。

## 5. 実装順序

1. `StructuralPattern` から、役割・遷移・文脈を含む primitive 候補を抽出する。
2. 複数の primitive が同じ経験を説明する場合、再利用性と記述長で候補を比較する。
3. `State_t -> State_goal` の局所経路探索で primitive を合成する。
4. 未学習の組合せタスクで、単純なカウント予測より一般化するかを測る。
5. 有効な候補だけを Concept Cell / 長期構造へ昇格させる。

## 6. 評価基準

- 未保存の多段遷移を導けるか
- 新しい役割束縛でも既存 primitive を再利用できるか
- 経験全体の記述長を削減できるか
- 合成経路が局所的で、説明可能なサイズに収まるか
- 既存の `StructuralPattern` と単純な頻度予測より精度が改善するか

成功条件は、単に primitive の数が増えることではない。
**少ない再利用単位でより多くの経験を説明し、未保存の関係をより正確に導けること**である。
