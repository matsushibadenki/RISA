# G2 Context Conjunction Evaluation / G2 context連言評価 / G2 context合取评估

## Result / 結果 / 结果

[Done] The bounded conjunction and selection milestone passed. Training makes six proxy tags perfectly correlated with the stable `indoor + powered` condition. The engine explores 36 singleton or pairwise conditions and proposes seven indistinguishable specializations. On 800 independent development cases per seed, proxy accuracy ranges from 83.125% to 87.125%, while the stable condition reaches 100%. Only that development winner receives access to 200 final cases. Across five seeds, final accuracy is 100% versus the broad parent's 50%; paired bootstrap intervals range from +43–57 to +43.5–56.5 points. False generalization is 0% versus 100%.

[Done] 有界な連言探索と選択の節目を通過した。学習では6個のproxy tagを安定条件`indoor + powered`と完全相関させ、36個の単一・2連言条件から区別不能な7個のspecializationを生成した。seedごとに独立development 800件でproxyは83.125〜87.125%、安定条件は100%となり、このdevelopment winnerだけをfinal 200件へ進めた。5 seedのfinalは100%対広い親50%、対応bootstrap区間は+43〜+57から+43.5〜+56.5ポイント、false generalizationは0%対100%だった。

[Done] 有界合取搜索及选择达到阶段目标。训练中让6个proxy tag与稳定条件`indoor + powered`完全相关，从36个单项或二元合取条件生成7个训练时不可区分的分化候选。每个seed使用800个独立development案例后，proxy准确率为83.125%至87.125%，稳定条件为100%；只有该development优胜者可以进入200个final案例。5个seed的final均为100%，宽泛父候选为50%；配对bootstrap区间从+43至+57个百分点到+43.5至+56.5个百分点，错误泛化为0%对100%。

## Selection contract / 選択契約 / 选择契约

- Search uses at most 24 tags and condition size two, so one parent evaluates at most 300 raw conditions.
- At most eight proposals survive per parent, ranked by observed precision gain and support.
- Overlapping conjunctions remain separate. A merge is allowed only for siblings with disjoint support, preserving an explicit context disjunction.
- Multiple candidates may share development evidence. `select_derived_candidates_for_final` selects one winner and rejects the remaining provisional candidates.
- A derived candidate cannot consume final evidence unless selected. Support, ancestor support, ancestor evaluation, development and final IDs remain disjoint.
- Final adoption requires a positive confidence lower bound and at least five points over both baseline and strongest parent.

## Scope / 適用範囲 / 适用范围

The benchmark breaks proxy correlation in development and final using synthetic context tags. It validates bounded pairwise schema selection and evidence separation. It does not prove causal discovery, higher-order conjunctions or robustness to missing context observations. Its then-next milestone, structural role induction without supplied role labels, is now complete for one-hop target positions; multi-hop disambiguation remains G2.6.

このbenchmarkは合成context tagを用い、developmentとfinalでproxy相関を崩している。有限な2連言schema選択と証拠分離は検証したが、因果発見、3項以上の連言、context観測欠落への耐性は未証明である。当時の次の節目だった外部role labelなしの構造role誘導は一hop target位置について完了し、multi-hop曖昧性解消をG2.6に残す。

该benchmark使用合成context tag，并在development及final中打破proxy相关性。结果验证了有界二元合取schema选择及证据隔离，但未证明因果发现、三项以上合取或context观测缺失稳健性。当时的下一阶段目标——不依赖外部role标签的结构role归纳——现已完成一hop target位置部分，multi-hop歧义消解留到G2.6。

Reproducible inputs and full rows are in `experiments/g2_context_conjunction_manifest.json` and `docs/g2-context-conjunction-results.json`. Manifest SHA-256: `354578dea0189708c1b87300423f06a6afc7d22f333950a0ed3ba124dd4146fa`.
