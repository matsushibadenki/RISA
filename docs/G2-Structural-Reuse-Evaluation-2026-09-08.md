# G2 Structural Reuse Evaluation / G2構造再利用評価 / G2结构复用评估

Date: 2026-09-08. Benchmark: `g2.0.0`. Canonical manifest SHA-256: `f65f52b5e4c8af6bfd94eee941b94f690480a3e7b7c4c988716aea4d4a716647`.

## Contract / 評価契約 / 评估契约

日本語: G1と同じ5固定seedを使い、各split・各seed 200 held-out episodeを80% development、20% finalへ
決定的に分割した。G2では観測から前提を学ぶ`composition_learned`を追加し、役割束縛と変化適応を個別に無効化する
ablationを加えた。全方式は同じplannerと独立環境oracleを使う。driftだけは予測、採点、観測学習の順で更新し、
Replayを20更新ごとに直近16 Eventへ制限した。全seedで学習Event IDとheld-out IDの重複は0、compositionへ
供給された答えを示す時間edgeは0だった。

English: The benchmark uses the same five fixed seeds as G1. Each split and seed has 200 held-out episodes,
deterministically partitioned 80% development and 20% final. G2 adds `composition_learned`, where applicability must
be inferred from observations, plus separate role-binding and change-adaptation ablations. Every method uses the same
planner and independent environment oracle. Only drift updates online in predict-score-observe order. Replay is capped
at the latest 16 events every 20 updates. Every seed has zero training/held-out ID overlap and zero answer-revealing
temporal edges in composition.

简体中文: 本基准沿用G1的5个固定seed。每个split、每个seed含200个留出回合，并确定性划分为80% development与
20% final。G2新增必须从观测推断适用条件的`composition_learned`，并分别消融角色绑定及变化适应。所有方法使用同一
规划器及独立环境oracle。仅drift按预测、评分、观测学习顺序在线更新；Replay固定为每20次更新最多重放最近16个Event。
所有seed的训练与留出Event ID重叠均为0，composition中泄露答案的时间边为0。

## Implemented mechanisms / 実装機構 / 已实现机制

- [Done] `actor_roles`と`target_roles`をEvent、graph、evidence path、queryへ通し、同じ役割の既知targetから未知targetを束縛する。
- [Done] 同一action・target・contextで直近3件が旧outcomeと異なる場合に`ChangeHypothesis`を作り、直近根拠を予測へ反映する。
- [Done] 完全なbefore観測を持つ成功2件以上と失敗1件以上から`ApplicabilityHypothesis`を作り、成功反例で撤回する。
- [Done] action/context/effect/actor/target/role index、`compact-v1` graph保存、件数制限Replayを実装する。
- [Done] 多様なtarget、source、episodeで共有されるschemaを`UnnamedConceptCandidate`とし、非重複のdevelopment/final証拠で段階評価する。
- [Done] 採用済み候補だけを派生indexへ載せ、予測と保存されない一時Primitiveへ接続する。機能flagで候補なし経路を保持する。

English: Events now carry typed roles; prediction can bind unseen targets through observed role evidence. Three recent
same-context outcomes can form a reversible change hypothesis. Complete successful and failed before-state observations
can form conservative applicability hypotheses that retract on counterexamples. Evidence lookup is indexed, graphs use
the lossless `compact-v1` format, and replay is bounded. Diverse repeated schemas can become unnamed candidates and move
from proposed to provisional and adopted or rejected using disjoint evidence.
Only adopted candidates enter a derived inference index. Prediction and planning consume them through ephemeral
primitives without modifying source events or the persisted graph; a feature flag preserves the no-candidate path.

简体中文: Event现可携带类型化角色，预测能借助已观测角色证据绑定未见target；同一context最近3次结果可形成可逆变化
假设；完整成功及失败前态观测可形成保守的适用条件假设，并在反例出现时撤回。证据查询已索引化，图采用无损
`compact-v1`格式，重放有数量上限。跨多个target、source及episode复现的schema可形成无名候选，并使用不重叠证据从
proposed推进至provisional，再进入adopted或rejected。
只有已采纳候选会进入派生推理索引；预测与规划通过不持久化的临时原语使用候选，不修改源Event或持久化图，并保留无候选开关。

## Final results / 最終結果 / 最终结果

Final rows pool 200 episodes across five seeds for each static split. Parentheses show coverage.

| Method | Control | Supplied composition | Learned composition | Binding | Uncertainty |
| --- | ---: | ---: | ---: | ---: | ---: |
| RISA | 100% (100%) | 100% (100%) | 100% (100%) | 100% (100%) | 94% (75%) |
| Grounded transition | 100% (100%) | 100% (100%) | 0% (100%) | 75% (75%) | 94% (75%) |
| RISA without role binding | 100% (100%) | 100% (100%) | 100% (100%) | 75% (75%) | 94% (75%) |
| RISA without structural sharing | 100% (100%) | 0% (0%) | 0% (0%) | 100% (100%) | 69% (50%) |

The final 95% intervals are `[0.9812, 1.0000]` for RISA on learned composition and binding, `[0.0000, 0.0188]`
for the grounded table on learned composition, and `[0.6857, 0.8049]` for the grounded table and no-role ablation on
binding.

| Drift phase | RISA | Grounded transition | RISA without change adaptation |
| --- | ---: | ---: | ---: |
| A1 | 100% | 100% | 100% |
| B | 75% | 33.3% | 33.3% |
| A2 | 100% | 100% | 100% |

RISA's final phase-B interval is `[0.6277, 0.8422]`; both comparison methods have `[0.2273, 0.4594]`. Development
A2 was 98.2% for RISA because a short recency window initially retained B, while final A2 was 100%. This is useful
adaptation with a measurable transient recovery cost.

## Decision and limits / 判断と限界 / 判断与限制

日本語: G2.1〜G2.3の各機構は対応ablationに対して効果があり、G1で観測した3つの失敗を改善した。特に前提を
入力せずbefore/afterと失敗例から学ぶcompositionでは、同じplannerを使う具体遷移表の0%に対して100%だった。
ただし、これは構造AI全般の優位性を実証しない。target roleは入力で明示され、自動型発見ではない。前提学習は完全観測を
必要とし、状態消費の意味までは帰納しない。候補の昇格には明示的なheld-out指標が必要である。採用候補は予測・計画で
利用可能だが、後続の候補転移評価では既存role readoutを超える改善がなかった。

English: Each G2.1–G2.3 mechanism changes its matching ablation and fixes the three G1 failures. Learned-applicability
composition reaches 100% while the grounded table with the same planner reaches 0%. This does not establish a general
structural-AI advantage. Target roles are supplied, applicability induction requires complete observations and does not
induce consumption semantics. Candidate promotion still requires explicitly supplied held-out metrics. Adopted candidates
are usable by prediction and planning; the follow-up transfer evaluation found no gain over the existing role readout.

简体中文: G2.1至G2.3各机制都优于对应消融，并改善了G1发现的三类失败。从观测学习适用条件的composition达到100%，
而使用同一规划器的具体转移表为0%。这仍不能证明结构AI具有普遍优势。target角色由输入提供，适用条件归纳要求完整观测，
且尚未学习状态消耗语义；候选提升仍需要显式提供留出指标。已采纳候选现可用于预测及规划，但后续迁移评估显示其
没有超过现有角色readout。

Static RISA state averages 138,918 bytes after training versus 3,458 bytes for the grounded transition table, about
40 times larger. Compact graph storage and rebuilding count/activation indices from immutable events reduced the earlier
G2 snapshot from roughly 221,701 bytes by about 37%, but total state compression remains [Next]. Python-level Control
prediction averages about 0.0572 ms versus 0.0009 ms; these
timings are environment-sensitive and show direction rather than a portable performance guarantee.

The original broad G2 gate remains open because supplied-precondition composition still ties the strongest baseline and
the type schema is external. The subsequent [candidate-transfer evaluation](G2-Candidate-Transfer-Evaluation-2026-09-08.md)
found 100% versus 100% and rejected every single-transition candidate as redundant. Candidate schemas must now represent
multi-relation, temporal or applicability structure unavailable to current readouts; compression remains a separate gate.

## Artifacts / 成果物 / 产物

- Manifest: [`experiments/g2_manifest.json`](../experiments/g2_manifest.json)
- Runner: [`experiments/comparative_evaluation.py`](../experiments/comparative_evaluation.py)
- Complete results: [`g2-comparative-results.json`](g2-comparative-results.json)
- Benchmark: [`risa/evaluation/benchmark.py`](../risa/evaluation/benchmark.py)
- Candidate discovery: [`risa/engine/candidate_discovery.py`](../risa/engine/candidate_discovery.py)
- Evidence index: [`risa/engine/evidence.py`](../risa/engine/evidence.py)
- Candidate transfer evaluation: [`G2-Candidate-Transfer-Evaluation-2026-09-08.md`](G2-Candidate-Transfer-Evaluation-2026-09-08.md)
