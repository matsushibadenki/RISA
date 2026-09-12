# G2 Derived Candidate Evaluation / G2派生候補評価 / G2衍生候选评估

## Result / 結果 / 结果

[Done] Automatic context specialization and sibling merge passed the independent comparison. Across five seeds, each merged candidate became `provisional` after 800 development cases and `adopted` after 200 final cases. Final accuracy was 100% versus 75% for its strongest direct parent, a +25 point paired gain with a 95% bootstrap interval of +19 to +31 points. The broad ancestor reached 50% with 100% false generalization; the merge and direct parent both had 0% false generalization.

[Done] context specializationと兄弟mergeの自動提案は独立比較を通過した。5 seedすべてで、800件のdevelopment後に`provisional`、200件のfinal後に`adopted`となった。final正解率は100%、最良の直接親は75%で、対応差+25ポイント、bootstrap 95%信頼区間は+19〜+31ポイントだった。広い祖先は50%・false generalization 100%で、mergeと直接親のfalse generalizationはいずれも0%だった。

[Done] 自动context分化及兄弟合并通过独立比较。5个seed中，每个合并候选在800个development案例后成为`provisional`，在200个final案例后成为`adopted`。final准确率为100%，最强直接父候选为75%，配对提升25个百分点，bootstrap 95%置信区间为+19至+31个百分点。宽泛祖先为50%且错误泛化100%；merge及直接父候选的错误泛化均为0%。

## Mechanism / 仕組み / 机制

- A tag-specific subset needs at least two distinct targets, sources and episodes.
- Its observed precision must exceed the parent's precision by at least 0.2.
- Each parent keeps at most eight proposals, ranked by precision gain and support.
- Compatible siblings preserve their scopes as `required_context_alternatives`; merge never erases these conditions.
- Promotion requires positive held-out gains over the baseline and strongest parent. Support, ancestor support, ancestor evaluation, development and final IDs cannot overlap.
- After development, an explicit selection step grants final-evidence access to the bounded winner set.
- Adoption makes broader adopted ancestors for the same action, role and effects dormant so their overgeneralization cannot remain active.

## Scope / 適用範囲 / 适用范围

This controlled benchmark uses externally supplied, balanced context tags. It establishes that the lifecycle and replacement mechanism can recover useful structural scope; it does not establish robustness to noisy tags, correlated tags, class imbalance or multiple-candidate selection. Those are the next evaluation target.

この統制benchmarkは、外部から与えた均衡context tagを使う。候補生命周期と置換機構が有用な構造的適用範囲を回復できることは示したが、noisy tag、相関tag、class imbalance、多重候補選択への耐性は未証明であり、次の評価対象とする。

该受控benchmark使用外部提供且均衡的context tag。结果证明候选生命周期及替换机制能够恢复有用的结构适用范围，但尚未证明对含噪tag、相关tag、类别不均衡及多候选选择的稳健性；这些是下一项评估目标。

Reproducible inputs and full rows are in `experiments/g2_derived_candidate_manifest.json` and `docs/g2-derived-candidate-results.json`. Manifest SHA-256: `37d161e1eafd868635548e6e436ae0694e4d43d69ae36d607d0e15b56ce95ba5`.
