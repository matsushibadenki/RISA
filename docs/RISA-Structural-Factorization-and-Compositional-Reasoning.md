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

## 7. Predictive factorization with dependency guards — 2026-10-10

### 日本語

[Memory Mosaics](https://arxiv.org/html/2405.06394v3)のPredictive Disentanglementを、
「少ない観測で予測できる部分問題への分解」という設計上の参考にする。
論文のニューラル連想記憶・勾配学習をRISAへ実装したことや、RISAの凝縮仮説が証明されたことを意味しない。
学習時に分解方法を決める仕組みと、推論時に記憶を追加する仕組みは区別する。

RISAでは次を設計契約とする。

1. 分解候補は、未知の**全体の組合せ**で予測に役立つかを評価する。entity名だけを変えた転移と区別し、
   全経路は未観測でも局所遷移が観測済みかを監査する。
2. 独立性は無条件に仮定しない。同一Eventで支持されたactor/target役割対とidentity等値、
   状態の生成・消費、共有資源、文脈条件、原子的な複数effectを保持する。
   独立した役割の周辺集合が一致するだけでは、jointな適用条件を満たしたことにしない。
3. 採用判断には未知組合せの正解率・誤受理・必要Event数と、schema/束縛/例外/出典を含む保存量、
   構築・更新・検索の費用を使う。予測誤差の改善だけで独立因子や因果機構の発見とは呼ばない。
4. 完全経路の記憶表だけでなく、**制約を保つ因子分解した遷移表**と比較する。
   world modelの比較には同じplannerを使い、native plannerの結果は別に記録する。
   依存条件を落とす対照は反例の感度検査であり、競争力のあるbaselineとして扱わない。
5. 学習された長期構造と逐次追加される一次証拠を区別し、summary/indexは再構築可能な派生物とする。
   Memory Mosaicsのpersistent memoryをRISAのオンライン候補採用と同一視しない。

最初の[G3.4実験](G3.4-Compositional-Holdout-2026-10-10.md)は、独立/依存の2世界で既知の局所遷移を
未知経路へ合成する開発対照である。RISAと強い表は同点、候補採用は0であり、潜在因子の自動発見や
候補固有の利得を実証していない。[実験契約](G3.4-Compositional-Holdout-Protocol.md)を参照。
既存の接地read model最適化を先行し、意味規則の異なる世界・十分な候補採用機会へ段階的に広げる。

### English

Memory Mosaics' predictive disentanglement motivates evaluating decompositions by how quickly they predict
unseen combinations. This is a structural research adaptation, not a neural implementation, reproduction,
causal-identification result or proof of condensation. Distinguish learned feature/decomposition rules from
inference-time evidence accumulation and distinguish persistent neural memory from online candidate adoption.

Audit unseen complete paths separately from unseen identities and verify that local transitions are observed.
Preserve same-Event joint role/equality witnesses, state production/consumption, shared resources, context and
atomic outcomes. Marginal role compatibility is insufficient. Evaluate quality, false acceptance, sample
requirements and actual storage/construction/update/query costs including schemas, bindings, exceptions and
provenance. Compare against a dependency-preserving factorized table with a shared planner as well as a whole-path
control; dependency-dropping arms are sensitivity tests, not strong competitors. Keep summaries reconstructible.

The linked two-world G3.4 development experiment ties the strong table and adopts no candidates. It demonstrates
supplied-contract composition, not discovered latent factors or a candidate advantage. Prioritize the grounding
read model, then varied semantic rules and legitimate candidate opportunities under unchanged adoption gates.

### 简体中文

Memory Mosaics的预测解耦启发我们用更少观察下对未知组合的预测能力评估分解。
这是结构研究借鉴，不是神经架构实现、论文复现、因果识别或凝聚证明。
区分学得的分解规则与推理时积累的证据，也不将持久神经记忆等同于在线候选采纳。

分别审计未知完整路径与未知entity，并确认局部转移已观察。保留同一Event的联合角色和identity见证、
状态生成与消耗、共享资源、文脉及原子结果，不能仅凭边际角色兼容推断联合适用性。
同时评估准确率、误受理、所需Event数及包含schema、绑定、例外、来源的存储与构建/更新/查询成本。
除完整路径表外，必须加入保留依赖的因子化转移表并固定planner；删除依赖的对照只用于敏感度检查。
summary/index必须可重建。

本次两世界G3.4开发实验与强表同分、采纳候选零，只验证已给定约束下的组合，未证明潜在因子发现或候选优势。
先完成接地read model，再扩展变化语义规则与真实候选机会，保留既定采纳门槛。
