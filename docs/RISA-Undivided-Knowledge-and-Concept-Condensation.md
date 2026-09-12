# RISA 未分知と概念凝縮 / Undivided Knowledge and Concept Condensation / 未分知识与概念凝聚

Updated: 2026-09-06

## 1. 判断 / Decision / 判断

日本語: 対話で示された観念はRISAへ取り入れられる。特に有用なのは、文章量そのものではなく、異なる表現、対象、文脈に残る再利用可能な構造を発見し、未命名のまま検証してからConcept Cellへ昇格させる考え方である。

English: The idea can be incorporated into RISA. Its useful core is not text volume alone, but discovering reusable structure that survives changes in wording, objects, and context, validating it without a name, and only then promoting it to a Concept Cell.

简体中文: 这一观念可以纳入RISA。其核心不是文本数量本身，而是发现跨表达、对象与上下文仍可复用的结构，先以无名形式验证，再提升为Concept Cell。

この機構はG0の意味論修正とG1の比較評価が完了した後のG2研究とする。現在のaction/effect集約を、そのまま新概念生成と呼ばない。

This mechanism belongs to G2 after G0 semantic repairs and G1 evaluation. Current action/effect aggregation is not sufficient to claim concept discovery.

该机制属于G2，须在G0语义修正和G1比较评估后开展。当前动作/效果聚合不足以称为概念发现。

## 2. RISAでの用語 / Operational terms / 操作性术语

| 対話の語 / Term / 术语 | RISAでの意味 / Operational meaning / 操作含义 |
| --- | --- |
| 未分知 / Undivided Knowledge / 未分知识 | 複数経験に分散しているが、まだ一つの共有schemaとして採用されていない関係・遷移・例外の集合 / Relations, transitions, and exceptions distributed across experiences but not yet adopted as a shared schema / 分散于多个经验中、尚未作为共享schema采纳的关系、转移与例外集合 |
| 概念圧 / Concept Pressure / 概念压力 | 新しい共有schemaを導入したときに期待される圧縮、予測、再利用の改善から、例外・複雑性・探索costを引いた昇格根拠 / Evidence for promotion: expected compression, prediction, and reuse gains minus exception, complexity, and search costs / 引入共享schema后的压缩、预测与复用收益，扣除例外、复杂性与搜索成本后的提升依据 |
| 意味凝縮 / Semantic Condensation / 语义凝聚 | 異なる経験を、束縛可能な少数の関係単位と例外で再記述する操作 / Re-encoding diverse experiences with fewer bindable relation units and exceptions / 用少量可绑定关系单元和例外重新编码多样经验 |
| 概念解像度 / Conceptual Resolution / 概念分辨率 | queryと文脈に応じて統合または分裂できる粒度の範囲 / The range of granularities available for merging or splitting structure under a query and context / 随查询与上下文可合并或拆分结构的粒度范围 |
| 語彙地平線 / Lexical Horizon / 词汇地平线 | 現在の採用済みschemaでは高costまたは低精度だが、候補schemaで検証可能になった問題領域 / Problems costly or inaccurate under adopted schemas but testable with candidate schemas / 当前schema成本高或精度低、借助候选schema才可验证的问题区域 |
| 意味発芽 / Semantic Germination / 语义萌发 | 新概念を使うことで、以前は候補化できなかった予測や関係が生成され、独立データで支持されること / A concept enables previously unavailable predictions or relations that receive independent support / 新概念产生此前无法提出的预测或关系，并获得独立数据支持 |
| 知能複利 / Intelligence Compounding / 智能复利 | 採用概念が次の候補発見を改善する反復効果。改善量を各世代で測定できる場合だけ成立とする / Iterative gain where adopted concepts improve later discovery, accepted only when measured per generation / 已采纳概念改善后续发现的迭代收益，仅在逐代测得改进时成立 |

これらは説明語であり、観測値ではない。コード上では測定可能なfieldと状態遷移へ分解する。

These are explanatory terms, not observations. The implementation must decompose them into measurable fields and state transitions.

这些是解释性术语而非观测值，实现时必须拆分为可测字段与状态转移。

## 3. 追加する中間層 / Candidate layer / 候选层

現在の流れへ、Event MemoryとConcept Cellの間に匿名候補層を追加する。

Add an anonymous candidate layer between Event Memory and Concept Cells.

在Event Memory与Concept Cell之间增加匿名候选层。

```text
Event Memory
  -> grounded relation units
  -> residual groups not explained well by adopted structures
  -> UnnamedConceptCandidate
  -> train-only replay and reconstruction
  -> held-out prediction and composition test
  -> provisional Concept Cell
  -> optional human-readable aliases
  -> derived re-indexing of memory
```

候補は例えば次を保持する。

```text
UnnamedConceptCandidate {
  id
  structural_schema
  typed_role_variables
  supporting_event_ids
  counterexample_event_ids
  source_and_episode_diversity
  expression_and_context_diversity
  reconstruction_gain
  description_length_delta
  heldout_prediction_delta
  heldout_composition_delta
  exception_cost
  inference_cost
  parent_candidate_ids
  derivation_generation
  lifecycle_status
}
```

`id`は意味名ではなく安定した内部識別子にする。名称はaliasであり、構造本体、証拠、適用範囲を変更しない。英語、日本語、简体中文の名称は同じ内部IDへ結び付ける。

The ID is a stable internal identity, not a semantic name. Names are aliases and cannot alter structure, evidence, or applicability. English, Japanese, and Simplified Chinese labels point to the same ID.

ID是稳定的内部标识，不是语义名称。名称只是别名，不得改变结构、证据或适用范围；英语、日语和简体中文名称指向同一内部ID。

## 4. 概念圧の計測 / Measuring concept pressure / 概念压力测量

単一の不透明scoreを概念の真理値にしない。少なくとも次を個別に記録する。

Do not turn one opaque score into a truth value. Record at least these components separately.

不要把单一不透明分数当成真值，至少分别记录以下部分。

- 独立したsource、episode、actor、target、contextにまたがる証拠多様性
- schemaと束縛を導入した実測記述長の減少
- 既存構造では説明できなかったexperienceの再構成改善
- 未学習episodeでの次状態予測とgoal到達率の改善
- 新しい対象・役割束縛・組合せへの転用成功
- counterexample、例外schema、誤予測、探索量、保存量のcost

同一文、同一Event ID、同一sourceの言い換え、Replayで生成した記録を独立証拠として数えない。大量の反復は支持度を上げ得るが、source diversityの代わりにはならない。

Duplicate text, the same Event ID, paraphrases from one source, and replayed records are not independent evidence. Repetition can increase support but cannot replace source diversity.

重复文本、相同Event ID、同一来源的改写及重放记录均不算独立证据。重复可增加支持度，但不能替代来源多样性。

候補の比較には次のような分解を使えるが、係数はG1後に事前登録する。

```text
benefit = description_length_gain
        + heldout_prediction_gain
        + heldout_composition_gain
        + cross_binding_reuse_gain

cost = exception_cost
     + false_generalization_cost
     + inference_cost
     + storage_cost

concept_pressure = benefit - cost
```

`concept_pressure > 0`だけでは昇格させない。全component、適用範囲、比較baseline、信頼区間を保存する。

A positive total alone is insufficient for promotion. Preserve all components, scope, baselines, and uncertainty intervals.

总分大于零也不足以提升，必须保留各分量、适用范围、比较基线与不确定区间。

## 5. 候補のライフサイクル / Candidate lifecycle / 候选生命周期

```text
latent
  -> proposed
  -> provisional
  -> adopted
  -> specialized | merged | dormant | rejected
```

- `latent`: residualや共有unitの重なりとして存在し、まだ独立objectにしない。
- `proposed`: bounded searchで候補化し、生成根拠と予算を記録する。
- `provisional`: train/development範囲で圧縮と予測の両方を改善した。
- `adopted`: 固定held-outでbaselineを超え、反例と適用範囲を保持する。
- `specialized`: 文脈別の分裂が汎化を改善する。
- `merged`: 二候補の統合が個別保持より短く正確になる。
- `dormant`: 現在は有用性が低いが、証拠を失わず再活性化できる。
- `rejected`: 改善が再現せず、理由と失敗例を保持する。

名称の付与は`provisional`以降とする。命名しやすさや人間の納得感を採用scoreへ混ぜない。

Naming starts only at `provisional`. Ease of naming and human appeal are not adoption signals.

仅在`provisional`之后命名，名称是否好听或易懂不得进入采纳分数。

### 5.1 構造roleの誘導 / Structural role induction / 结构role归纳

G2.5では、外部`target_roles`がないEventについて、具体target identityがentity relationのどの位置にあるかを内部型として使う。targetに束縛された変数から見た直接relationを`out:<relation>`、`in:<relation>`、`self:<relation>`へ正規化し、整列した署名のhashを`struct_role:<id>`にする。entity identityや変数名が異なっても位置とrelation型が同じなら同じroleとなる。可読署名は候補schemaに残し、hashだけを意味説明として扱わない。

For Events without supplied `target_roles`, G2.5 uses the concrete target's position in entity relations as an internal type. Direct relations seen from variables bound to the target become normalized `out:<relation>`, `in:<relation>` or `self:<relation>` descriptors. A hash of the sorted signature forms `struct_role:<id>`. Different entity identities and variable names map to the same role when relation type and position match. The readable signature remains in the candidate schema; the hash itself is not treated as an explanation.

G2.5对未提供`target_roles`的Event，将具体target identity在entity relation中的位置用作内部类型。从绑定到target的变量观察直接relation，并规范为`out:<relation>`、`in:<relation>`或`self:<relation>`；排序签名的hash形成`struct_role:<id>`。只要relation类型与位置相同，不同entity identity及变量名会映射到同一role。可读签名保留在候选schema中，hash本身不作为意义解释。

外部roleがある場合はそれを優先し、既存contractと比較対照を保つ。role誘導の有効・無効はqueryごとに切り替えられる。Event学習、候補発見、証拠index、予測、composition、Replay、validation、CLI、保存再構築が同じresolverを使わなければ、同じ構造が学習時と利用時で別roleになるため、この一貫性を永続化contractに含める。

Supplied roles take precedence to preserve the existing contract and comparison arm. Induction can be enabled or disabled per query. Event learning, candidate discovery, evidence indexing, prediction, composition, replay, validation, CLI and persistence reconstruction must use the same resolver; otherwise the same structure could receive different roles during learning and use. This consistency is part of the persistence contract.

外部role存在时优先使用，以保持既有contract及比较路径。每个query可单独启用或禁用role归纳。Event学习、候选发现、证据索引、预测、composition、重放、验证、CLI及持久化重建必须使用同一resolver，否则相同结构在学习与使用时可能得到不同role；这一一致性属于持久化contract。

この段階は意味型発見ではない。relation label自体は観測入力で、target identityをbindingから特定できる必要がある。同じ一hop署名の中に複数の結果機構がある場合は衝突する。G2.6ではこの衝突が観測された場合だけ最大二hopへspecializeし、base roleごとの候補をsupport順上位8件に制限した。二hopでもoutcomeが混ざる場合は候補化しない。同じresolverをactorと任意entity変数へ広げ、relation欠落は誤った空roleとして共有せずunknownとしてabstainする。

This stage is not semantic type discovery. Relation labels remain observed inputs, target identity must be recoverable from bindings, and different mechanisms collide when they share one one-hop signature. G2.6 specializes only observed collisions to at most two hops and retains at most eight refinements per base role by support. It creates no candidate when outcomes remain mixed at depth two. The same resolver now covers actors and arbitrary entity variables; missing relations remain unknown and cause abstention rather than forming a shared empty role.

该阶段不等于语义类型发现。relation标签仍来自观测输入，target identity必须能从binding中确定；不同机制若共享同一一hop签名就会冲突。G2.6仅对已观测冲突细分至最多二hop，并按support为每个base role最多保留8个refinement；二hop仍混合多个outcome时不生成候选。同一resolver现已覆盖actor及任意entity变量，relation缺失保持unknown并弃答，不形成共享空role。

## 6. 再解釈ループの安全条件 / Safe reinterpretation / 安全再解释

新概念で既存記憶を読み直すことは有望だが、候補自身が作った派生記録を自分の支持証拠として再利用すると、根拠のない自己増幅が起こる。

Re-reading memory through a new concept is promising, but using candidate-derived records as fresh support creates unsupported self-amplification.

用新概念重新读取记忆很有潜力，但若把候选概念生成的派生记录当作新证据，会形成无依据的自我放大。

必須条件:

- 元Eventを不変の一次証拠として保持する。
- 再解釈結果はderived edge/indexとして分離する。
- `parent_candidate_ids`と`derivation_generation`で循環を検出する。
- 候補から導いた候補は、同じ祖先証拠だけでは昇格できない。
- 各generationの追加価値を、新しいheld-out episodeで測る。
- 新概念を無効化すると派生結果も無効化できるようにする。
- 一世代あたりの候補数、探索edge、Replay件数を制限する。

実装済みの第一段階では、単一遷移の成功例を最大24個のcontext tagから単一条件と2連言へ分け、各部分集合が二つ以上のtarget・source・episodeで再現し、親よりprecisionが0.2以上高い場合だけspecializationを提案する。親ごとにprecision改善とsupportが高い上位8件だけを残す。supportが互いに重ならない互換な兄弟だけをcontext論理和としてmergeし、重なる連言候補は個別に評価する。複数候補をdevelopmentで比較した後、上位1候補だけにfinal評価を許可する。派生候補の採否にはbaselineとの差に加えて最良の親との差と信頼区間下限を要求し、採用後は同じ遷移を表す広い祖先をdormantにする。

The implemented first stage searches singleton and pairwise conjunctions from at most 24 context tags. It proposes a specialization only when the subset repeats across at least two targets, sources and episodes and improves precision over its parent by at least 0.2. Each parent retains at most the top eight proposals by precision gain and support. Compatible siblings merge as a context disjunction only when their support is disjoint; overlapping conjunctions remain separate. After development comparison, only the top candidate may use final evidence. Adoption requires gains and positive confidence lower bounds against both the baseline and strongest parent and makes broader ancestors for the same transition dormant.

已实现的第一阶段从最多24个context tag搜索单项及二元合取。仅当子集至少跨两个target、source及episode复现，并比父候选的precision高0.2以上时提出分化。每个父候选只保留按precision提升及support排序的前8项。仅在support互不重叠时把兼容兄弟合并为context析取；重叠合取保持独立。development比较后，仅排名第一的候选可以使用final证据。采纳同时要求优于baseline与最强父候选且置信区间下限为正，并将表示同一转移的宽泛祖先设为休眠。

`知能複利`は、新しい独立episodeでprediction、composition、compressionのいずれかが世代ごとに改善し、false generalizationとcostが許容範囲内の場合だけ報告する。

Report intelligence compounding only when each generation improves prediction, composition, or compression on new independent episodes while false generalization and cost remain bounded.

仅当每一代在新的独立回合上改善预测、组合或压缩，且错误泛化与成本受控时，才报告智能复利。

## 7. 最初の検証 / First experiment / 首个实验

文章入力の前に、言い換えの影響を切り離せる構造化世界で検証する。

Test in a structured world before text so paraphrase quality is not a confound.

先在结构化世界中测试，避免文本改写质量成为混杂因素。

1. 同じ潜在関係を、異なるactor、target、context、表面labelで観測する。
2. 一部の束縛と組合せを学習から除外する。
3. grounded transition table、固定schema、候補凝縮ありRISAを同じplannerで比較する。
4. 圧縮だけ改善する候補、予測だけ改善する候補、両方改善する候補を分ける。
5. 反例を追加し、分裂、休眠、棄却が適切に起きるか測る。
6. 採用概念による二世代目候補探索を行い、新しいheld-out episodeで追加価値を測る。

最初の成功条件は[ROADMAP](ROADMAP.md)のG2 gateに従う。加えて、候補凝縮あり方式が候補なし方式より、同じ情報と予算で実測記述長を減らし、false generalizationを増やさないことを要求する。

Follow the G2 gate in the roadmap. Additionally, candidate condensation must reduce measured description length over the no-candidate variant under equal information and budgets without increasing false generalization.

遵循路线图G2门槛；此外，在信息与预算相同的条件下，候选凝聚版本必须比无候选版本降低实测描述长度，且不得增加错误泛化。

## 8. 採用しない解釈 / Non-goals / 不采纳的解释

- 文章量が増えれば自動的に知能が上がるとは仮定しない。
- 共通部分が大きいだけのclusterを概念と認定しない。
- 新しい単語を作ったこと自体を新知識と数えない。
- 組合せ数の理論上の増加を、利用可能な知識量と同一視しない。
- 内部Replayの成功を外部世界での正しさと同一視しない。
- LLMが提案した名称や説明を、RISAの構造証拠として直接採用しない。

LLMは将来、候補の言語化、既存用語との重複検索、反例案の生成に使える。ただし構造候補の採用は、RISA側の証拠と独立評価で決める。

An LLM may later verbalize candidates, search for existing terms, and propose counterexamples. Adoption remains governed by RISA evidence and independent evaluation.

未来可用LLM表述候选、检索既有术语并提出反例，但候选采纳仍由RISA证据与独立评估决定。
