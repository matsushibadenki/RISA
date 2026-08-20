# RISA Roadmap / RISA ロードマップ / RISA 路线图

## Purpose / 目的 / 目的

このロードマップは、
RISA を
「実用的に動く最小コア」
から
「構造記憶と動的推論を備えた知能基盤」
へ育てるための段階整理です。

This roadmap organizes the path from
a practical minimal RISA core
to
a broader intelligence substrate with structural memory and dynamic inference.

这个路线图用于整理
RISA 从“可实际运行的最小核心”
发展到“具备结构记忆与动态推理能力的智能基础”
的步骤。

---

## Current Status / 現在地 / 当前状态

- [Done] 構造化イベントの学習、局所探索、概念生成、説明付き予測の最小ループ
- [Done] `recent_activity` / `energy` / `dormant` を使った最小の構造代謝
- [Done] `co_activates_with` による共活性の最小強化
- [Done] `co_activates_with` を予測説明経路へ反映
- [Done] `co_activates_with` を候補探索へ反映
- [Done] 共活性強度に応じた局所探索半径の最小制御
- [Done] 共有 action / effect による簡易概念統合
- [Done] 「構造保存だけでは知識創発は不十分」という課題を研究テーマとして明文化
- [Done] 文脈つき `StructuralPattern` を共有構造メモリとして導入
- [Done] `StructureDelta` を最小実装として保存開始
- [Done] 「概念 = 繰り返し再利用される内部構造」という設計原則を明文化
- [Done] 「独立 Verifier より、共鳴・競合・予測誤差で構造を選別する」という原則を明文化
- [Done] 学習前予測と観測結果の比較による局所予測検証履歴を最小実装として導入
- [Done] effect 単位の検証履歴を `Pattern` / `StructuralPattern` の安定性へ反映
- [Done] 競合履歴を `co_activates_with` の reliability / plasticity へ反映

---

## Phase 1 / Phase 1 / 第一阶段

### [Next] Structural Memory as Long-Term Knowledge

日本語:
長期知識の保存基盤を
重みそのものではなく
外部化された構造記憶として設計する。

English:
Treat long-term knowledge as an externalized structural memory
rather than as opaque distributed weights.

简体中文:
将长期知识设计为外部化的结构记忆，
而不是不透明的分布式权重。

研究テーマ:

- [Next] 知識保存形式を学習器から切り離す
- [Next] `Knowledge = inference(Structure, Context)` の形で扱う
- [Later] 異なる学習器間で同じ構造基盤を共有する

### [Next] Structural Sharing and Knowledge Emergence

日本語:
構造を保存するだけではなく、
構造間で共有される
再利用可能パターンから
未知の関係を生成できるようにする。

English:
Go beyond storing structures
and enable reusable shared structural patterns
to generate previously unstored relations.

简体中文:
不仅要保存结构，
还要让结构之间共享可复用模式，
从而生成此前未显式存储的关系。

研究テーマ:

- [Next] 「保存した関係」ではなく「再利用可能な構造パターン」を知識単位として扱う
- [Done] 文脈つき再利用可能パターンを最小実装として学習・予測へ接続する
- [Done] 共有構造パターン同士の差分を `StructureDelta` として蓄積する
- [Next] 明示的な同型探索より先に、共有される局所関係単位の再利用を優先する
- [Next] 経験同士の共通部分と差分を、共有内部単位の重なりとして自然に得る設計へ寄せる
- [Next] 類似構造・上位構造・役割構造への波及更新を設計する
- [Next] 保存されていない関係を導けた時点を「知識創発」と定義する
- [Later] 構造的不変量
  例:
  `X -supports-> Y`
  のような役割パターン
  を抽出する

### [Next] Co-Activation-Guided Inference

日本語:
共活性した構造を
単なる記録ではなく、
局所探索と予測優先度に使う。

English:
Use co-activation traces
not only as memory records
but also as inference guidance.

简体中文:
将共活性痕迹
不仅作为记忆记录，
也作为推理引导。

研究テーマ:

- [Done] `co_activates_with` を説明経路に反映する
- [Done] `co_activates_with` を予測スコアに最小利用する
- [Done] `co_activates_with` を候補探索に使う
- [Done] 共活性を局所探索半径の最小制御に使う
- [Next] 共活性半径を文脈や信頼度に応じて適応化する

### [Next] Dynamic Structural Validation

日本語:
構造を静的に正誤判定するのではなく、
予測誤差、共鳴、競合、恒常性の中で
再生安定性を評価する検証方式へ進める。

English:
Validate structures through
prediction error, resonance, competition, and homeostasis
rather than through a separate static verifier.

简体中文:
不要只用独立的静态验证器判断结构对错，
而要通过预测误差、共鸣、竞争与稳态机制
来评估结构的再生稳定性。

研究テーマ:

- [Next] `predicted` と `observed` の局所誤差を構造更新へ接続する
- [Done] `predicted` と `observed` の最小比較を学習ループへ接続する
- [Done] 局所誤差履歴を共有構造の安定性スコアへ接続する
- [Done] 競合する経路の最小抑制ルールを設計し、予測スコアと edge 可塑性へ接続する
- [Next] 再現性が高い構造ほど安定する可塑性則を定義する
- [Later] `synaptic scaling` に相当する構造恒常性を導入する
- [Later] 独立 Verifier を標準経路にせず、必要時だけ補助的に使う

### [Next] Replay and Gradual Consolidation

日本語:
新しい経験をいきなり長期構造へ固定せず、
一時記憶、再生、既存構造との相互作用を経て
徐々に統合する。

English:
Do not immediately commit new experience
into long-term structure.
Use temporary memory, replay, and gradual consolidation.

简体中文:
不要把新经验立刻写入长期结构，
而应通过临时记忆、重放、与既有结构相互作用后
再逐步整合。

研究テーマ:

- [Next] `Event Memory -> Structure Candidate -> Replay -> Consolidation` の最小ループを設計する
- [Later] 高速一時記憶と低速長期構造の二層化を実装する

### [Next] Neural Representation + Structural Memory + Dynamic Inference

日本語:
ニューラル系は
生データからイベント候補を抽出する高速推論器、
RISA は
永続構造記憶と世界モデル、
推論器は
必要時に関連構造を探索して知識を生成する
という役割分担を明確にする。

English:
Separate roles across
neural representation,
structural memory,
and dynamic inference.

简体中文:
明确区分
神经表征、
结构记忆、
动态推理
三者的职责。

研究テーマ:

- [Next] Neural layer の入出力境界を `Event / Concept candidates` で定義する
- [Next] RISA 側の永続構造を `Events + Relations + Roles + Temporal structure` で持つ
- [Later] 質問時に関連部分構造を取り出して動的推論する経路を確立する

---

## Phase 2 / Phase 2 / 第二阶段

### [Next] Transition-Centric World Model

日本語:
静的な
`A -> relation -> B`
の記録だけでなく、
`Structure_t --Event--> Structure_{t+1}`
を蓄積する
遷移中心の世界モデルへ進める。

English:
Move from static triples
to
transition-centric world modeling.

简体中文:
从静态三元组
转向
以状态迁移为中心的世界模型。

研究テーマ:

- [Next] `State_t + Action -> State_{t+1}` を一次表現として強化する
- [Next] CurrentState から複数の未来候補を探索する仕組みを設計する
- [Later] 構造探索結果をシミュレーション的に評価する

### [Next] Stored Structure != Available Knowledge

日本語:
保存された構造と
その場で導かれる知識を分離し、
「覚えていないが導ける」
性質を研究主題として明示する。

English:
Make a clear distinction between
stored structure
and
available knowledge generated at inference time.

简体中文:
明确区分
“已存储的结构”
与
“推理时生成的可用知识”。

研究テーマ:

- [Next] 多段経路探索から未学習の関係を導く推論ベンチマークを作る
- [Next] `A -> B -> C -> D` から `A => D` を導く説明可能推論を評価する
- [Next] 人間がまだ命名していない潜在構造を内部単位として保持し、有用性で評価する
- [Later] 条件付き推論
  例:
  温度・圧力・履歴つき相変化推論
  を扱う

### [Next] Reusable Relation Units

日本語:
経験を最初から完成済みグラフとして比較・分類するのではなく、
小さな関係単位の再利用が積み重なった結果として
概念や差分が見えてくる設計へ進める。

English:
Move toward a design where
concepts and differences emerge
from the reuse of small relation units
rather than from explicit whole-structure matching.

简体中文:
推进一种设计：
概念与差分
并不是通过显式的整结构匹配得到，
而是由小型关系单元的反复复用自然涌现。

研究テーマ:

- [Next] `shared relation unit` の最小データ型を定義する
- [Next] 経験を「単一構造」ではなく「共有単位の組合せ」として保存する
- [Next] 共通性を `same structure` 判定ではなく `same unit reuse` で近似する
- [Later] 差分を別オブジェクトとして計算するのではなく、共有単位の非重複部分として導出する

---

## Phase 3 / Phase 3 / 第三阶段

### [Next] Learner-Agnostic Knowledge Substrate

日本語:
Transformer、
SNN、
将来の未知の学習器が変わっても、
知識継承が壊れにくい保存基盤を作る。

English:
Build a learner-agnostic knowledge substrate
that can outlive individual learning architectures.

简体中文:
构建一种与学习器解耦的知识基底，
使知识可以跨架构继承。

研究テーマ:

- [Next] `Learner -> Structure` の標準入出力境界を定義する
- [Later] `Transformer -> G`, `SNN -> G`, `Future Learner -> G` の相互運用性を検証する
- [Later] 学習器を差し替えても世界モデルの整合性が保てるか評価する

### [Later] SNN = Dynamics, RISA = Structure

日本語:
SNN を時間・位相・イベントダイナミクス担当、
RISA を構造保存と概念進化担当として分業する。

English:
Let SNN specialize in dynamics,
while RISA specializes in persistent structure and concept evolution.

简体中文:
让 SNN 负责动态与时序，
让 RISA 负责持久结构与概念演化。

研究テーマ:

- [Later] 発火タイミングを `Phase / Temporal relation` として構造へ写像する
- [Later] SNN のイベント流を RISA の構造更新へ接続する
- [Later] SNN 活性を局所探索制御に利用する

---

## Phase 4 / Phase 4 / 第四阶段

### [Later] Ambiguous, Continuous, and Affective Signals

日本語:
皮肉、
雰囲気、
危険っぽさ、
顔の印象、
音の不穏さ
のような
連続値・曖昧性・時間変化を含む情報を
ニューラル表現と構造記憶の協調で扱う。

English:
Handle ambiguity,
continuous signals,
and affective cues
through cooperation between neural representations and structural memory.

简体中文:
通过神经表征与结构记忆的协作，
处理模糊、连续以及情感性信号。

研究テーマ:

- [Later] 画像・音・文章から曖昧なイベント候補を抽出する
- [Later] 曖昧候補を構造仮説として保留・比較する
- [Later] 文脈で意味が確定した時だけ構造へ定着させる

---

## Research Notes / 研究ノート / 研究说明

- [Next] RISA を単なる Knowledge Graph に戻さない
- [Next] 静的存在記述より
  「世界がどう変化するか」
  を優先する
- [Next] 推論結果として知識がその場で生成される設計を重視する
- [Later] 世界モデルの正確さと未来探索能力を
  知能評価の中心指標にする

---

## Related Docs / 関連文書 / 相关文档

- `docs/RISA-and-SARA-Engine-Compatibility.md`
- `docs/RISA-Structural-Interpolation-and-Smoothing.md`
- `docs/RISA-Concept-Formation-and-Multimodal-Notes.md`
- `docs/RISA-Transformer-SNN-Relationship-Notes.md`
- `docs/policy.md`
