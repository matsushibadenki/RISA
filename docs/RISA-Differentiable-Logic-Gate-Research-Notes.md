# RISA Differentiable Logic-Gate Research / RISA微分可能論理ゲート研究 / RISA可微逻辑门研究

Status / 状態 / 状态: [Later] research theme / 将来研究テーマ / 未来研究主题。現行runtimeには未実装で、実測上の優位性はまだ主張しない。Not implemented in the current runtime; no measured advantage is claimed. 尚未在当前runtime实现，也不主张已取得实测优势。

## Motivation / 動機 / 动机

日本語: [論理ゲート式ニューラルネットワークの記事](https://zenn.dev/teba_eleven/articles/68955053ed75be)を、
RISAの将来研究テーマを追加する起点とする。記事が重視するのは、論理ゲートを学習可能にする連続緩和、局所性・共有・
階層による帰納バイアス、意味を保つ二値表現、LUTやFPGAでの実行である。RISAでは、構造候補の発見・評価と、採用済み
候補の低コスト実行を分離できるため、この系統と接続できる可能性がある。

English: The [logic-gate neural-network article](https://zenn.dev/teba_eleven/articles/68955053ed75be) is the trigger
for this future RISA research theme. It emphasizes continuous relaxation for learning, architectural inductive bias from
locality, sharing and hierarchy, meaning-preserving binary representations, and LUT or FPGA execution. RISA may connect
to this line of work because candidate discovery and evaluation are already separated from execution of adopted structure.

简体中文: 以[逻辑门神经网络文章](https://zenn.dev/teba_eleven/articles/68955053ed75be)作为RISA未来研究主题的起点。
文章强调用于学习的连续松弛、由局部性、共享及层级结构带来的归纳偏置、保持语义的二值表示，以及LUT或FPGA执行。
RISA已将候选发现与评估同已采纳结构的执行分开，因此可能与该研究方向衔接。

Primary references include [Deep Differentiable Logic Gate Networks](https://arxiv.org/abs/2210.08277),
[Convolutional Differentiable Logic Gate Networks](https://arxiv.org/abs/2411.04732), and
[Recurrent Deep Differentiable Logic Gate Networks](https://arxiv.org/abs/2508.06097).
The ternary bridge below is grounded in [BitNet b1.58](https://arxiv.org/abs/2402.17764). BitNet keeps the Transformer
matrix-computation model while restricting weights to `{-1, 0, +1}`; this is distinct from composing Boolean gates.

## RISA hypothesis / RISA仮説 / RISA假设

- [Later] 日本語: 採用済み`UnnamedConceptCandidate`、前提、role束縛、時間macroをBoolean/LUT回路へcompileし、通常graph実行と意味的に一致させる。 / English: Compile adopted candidates, applicability, role bindings and temporal macros into Boolean/LUT circuits with semantic equivalence to graph execution. / 简体中文: 将已采纳候选、适用条件、角色绑定及时间宏编译为Boolean/LUT电路，并与图执行保持语义一致。
- [Later] 日本語: 候補発見中だけsoft gateまたは連続緩和を使い、採用後はhard gateへ離散化する。元Event、反例、回帰queryを保持し、離散化前後の差を検査する。 / English: Use soft gates or continuous relaxation only during candidate discovery, then discretize adopted candidates into hard gates while checking pre/post-discretization behavior against events, counterexamples and regression queries. / 简体中文: 仅在候选发现期间使用soft gate或连续松弛，采纳后离散化为hard gate，并依据Event、反例及回归query检查离散化前后差异。
- [Later] 日本語: RDDLGN型の再帰回路をEvent時間列、change hypothesis、bounded replayの候補generatorとして比較する。RISAの永続記憶を置き換えず、提案moduleとして隔離する。 / English: Compare an RDDLGN-style recurrent circuit as a candidate generator for event sequences, change hypotheses and bounded replay, isolated as a proposal module rather than replacing persistent RISA memory. / 简体中文: 将RDDLGN式循环电路作为Event序列、变化假设及有界重放的候选生成器进行比较，并作为提案模块隔离，不替换RISA持久记忆。
- [Later] 日本語: 連続知覚adapterで意味的近傍を保持し、型付きEvent・relationへ接地してから離散gateで実行するhybridを比較する。 / English: Compare a hybrid that preserves semantic neighborhoods in a continuous perception adapter, grounds them into typed events and relations, and executes adopted decisions with discrete gates. / 简体中文: 比较一种hybrid方案：连续感知adapter保持语义邻域，接地为类型化Event与relation后，再由离散gate执行已采纳决策。

## Ternary signed event circuit / 三値符号付きイベント回路 / 三值有符号事件电路

日本語: BitNetの三値重みを論理gateと同一視せず、連続値TransformerとBoolean回路の間にある低bit行列表現として扱う。
RISAでは`+1`を促進relation、`0`を構造的非接続、`-1`を抑制relationとする**候補符号体系**を研究する。これは
BitNetの重みに生物学的意味があるという主張ではなく、RISAの型付きedgeへ明示的な意味を与える別設計である。

English: Treat BitNet's ternary weights as a low-bit matrix representation between continuous Transformers and Boolean
circuits, rather than as logic gates. RISA will study a candidate signed vocabulary where `+1` is an excitatory relation,
`0` is structural absence and `-1` is an inhibitory relation. This does not assign biological meaning to BitNet weights;
it is a separate semantic design for typed RISA edges.

简体中文: 不把BitNet三值权重等同于逻辑门，而将其视为连续Transformer与Boolean电路之间的低bit矩阵表示。RISA将研究一种
候选有符号语义：`+1`表示促进relation，`0`表示结构性无连接，`-1`表示抑制relation。这并非声称BitNet权重具有生物学意义，
而是为RISA类型化edge赋予显式语义的独立设计。

- [Later] 日本語: `SignedRelation`を`sign ∈ {-1,0,+1}`、role条件、遅延、confidence、支持Eventで表し、`0`を保存edgeではなく非接続として扱う。 / English: Represent a `SignedRelation` with a ternary sign, role conditions, delay, confidence and supporting events; encode zero as absence rather than a stored edge. / 简体中文: 使用三值sign、角色条件、延迟、置信度及支持Event表示`SignedRelation`，并将零编码为无连接而非持久edge。
- [Later] 日本語: 入力または状態が変わったnodeからだけ`+1/-1` edgeを伝播し、巨大な三値行列全体の毎step再計算を避けるevent-driven executorを比較する。 / English: Compare an event-driven executor that propagates only along signed edges from changed inputs or states instead of recomputing a full ternary matrix every step. / 简体中文: 比较事件驱动执行器，仅沿发生变化的输入或状态所连接的有符号edge传播，避免每一步重算完整三值矩阵。
- [Later] 日本語: 伝播後にhard logicで前提、禁止状態、role/identity束縛を検証し、三値信号だけで安全条件を上書きしない。 / English: Validate applicability, forbidden states and role/identity bindings with hard logic after propagation; ternary signals cannot override safety constraints. / 简体中文: 传播后使用hard logic验证适用条件、禁止状态及角色/identity绑定，三值信号不得覆盖安全约束。
- [Later] 日本語: 非BP学習は局所Event差分、Replay、候補のheld-out gainから符号追加・反転・削除を提案する方式と、soft/STE系学習をablation比較する。 / English: Compare non-backprop proposals for adding, flipping or deleting signs from local event deltas, replay and held-out candidate gain against soft or straight-through-estimator learning. / 简体中文: 将基于局部Event差分、Replay及候选留出增益提出sign新增、翻转或删除的非反向传播方法，与soft或直通估计器学习进行消融比较。

日本語: この研究の中心仮説は「低bit化」単独ではなく、`0`を実際の非接続へ変換し、変化部分だけを時間的に疎に伝播することで
計算量を減らせるか、である。`0` edgeを削除すると再学習可能性も失われ得るため、`absent`、`dormant`、`pruned`を区別し、
再配線costと忘却も測る。

English: The central hypothesis concerns converting zero into actual disconnection and propagating only changed regions
with temporal sparsity, rather than low-bit arithmetic alone. Because deleting zero edges may also remove plasticity,
the design distinguishes `absent`, `dormant` and `pruned` states and measures rewiring cost and forgetting.

简体中文: 核心假设不只是低bit计算，而是把零转换为真实无连接，并仅让变化区域按时间稀疏传播。删除零edge也可能损失可塑性，
因此设计区分`absent`、`dormant`及`pruned`，并测量重新连接成本与遗忘。

## Evaluation order / 評価順 / 评估顺序

1. [Later] 日本語: 小規模な採用済み時間・関係候補をtruth tableへ変換し、Python上のbitset/LUT executorを作る。 / English: Convert small adopted temporal and relational candidates to truth tables and build a Python bitset/LUT executor. / 简体中文: 将小规模已采纳时间及关系候选转换为真值表，并构建Python bitset/LUT执行器。
2. [Later] 日本語: 全回帰queryでgraph executorと完全一致する場合だけ、速度・保存量比較へ進む。 / English: Proceed to speed and storage comparisons only after exact agreement with the graph executor on the full regression corpus. / 简体中文: 仅在全部回归query上与图执行器完全一致后，才进入速度及存储量比较。
3. [Later] 日本語: soft-to-hard学習は固定manifest、独立development/final、候補なしablationで、発見精度・false generalization・記述長を測る。 / English: Evaluate soft-to-hard learning with fixed manifests, disjoint development/final partitions and a no-gate ablation, measuring discovery quality, false generalization and description length. / 简体中文: 使用固定manifest、互不重叠的development/final及无gate消融评估soft-to-hard学习，测量发现质量、错误泛化及描述长度。
4. [Later] 日本語: CPU prototypeが品質低下1ポイント以内でp95または走査量を2倍以上改善した場合だけ、FPGA/LUT hardware評価へ進む。 / English: Consider FPGA/LUT hardware only if the CPU prototype improves p95 latency or scanned work by at least 2× with no more than one point of quality loss. / 简体中文: 仅当CPU原型在质量下降不超过1个百分点时将p95时延或扫描量改善至少2倍，才进入FPGA/LUT硬件评估。
5. [Later] 日本語: 三値系はdense ternary matrix、sparse signed graph、event-driven signed graph、Boolean/LUT、現行RISA graphを同じEvent列で比較する。 / English: Compare dense ternary matrices, sparse signed graphs, event-driven signed graphs, Boolean/LUT execution and the current RISA graph on identical event streams. / 简体中文: 在相同Event流上比较dense ternary matrix、sparse signed graph、event-driven signed graph、Boolean/LUT执行及当前RISA graph。

日本語: hardware評価ではthroughput、p50/p95、推論当たりenergy、回路深度、gate/LUT数、memory、compile時間、分布変化時の
挙動を記録し、同一task・同一hardware予算で比較する。event-driven系では更新node数、走査edge数、発火数、無変化stepの
計算量、再配線回数も記録する。

English: Hardware evaluation records throughput, p50/p95 latency, energy per inference, circuit depth, gate/LUT count,
memory, compile time and behavior under distribution shift, compared on the same task and hardware budget. Event-driven
variants also record changed nodes, scanned edges, firings, work on unchanged steps and rewiring count.

简体中文: 硬件评估记录吞吐量、p50/p95时延、单次推理能耗、电路深度、gate/LUT数量、内存、编译时间及分布变化下的行为，
并在相同任务与硬件预算下比较。事件驱动方案还记录变化node数、扫描edge数、发火数、无变化step计算量及重新连接次数。

## Stop conditions / 中止条件 / 停止条件

日本語: 離散化でrole束縛・abstention・数値境界が変化する、回路サイズが候補数に対して制御不能に増える、既存bitset実装を
超えない、三値graphがdense ternary baselineより疎性を活用できない、またはsoft gateが独立held-outで候補品質を改善しない場合は中止する。記事中の将来予測やGPUとの速度比較は、
RISA自身が同一条件で再現するまで設計根拠として扱い、実証結果として扱わない。

English: Stop if discretization changes role binding, abstention or numeric boundaries; circuit size grows uncontrollably;
the approach does not beat a compact bitset baseline; the signed graph cannot exploit sparsity over a dense ternary
baseline; or soft gates fail to improve candidate quality on independent
held-out data. Treat forecasts and GPU comparisons in the source article as research motivation until RISA reproduces
them under matched conditions.

简体中文: 若离散化改变角色绑定、弃答或数值边界，电路规模失控增长，无法超过紧凑bitset基线，三值graph不能比dense ternary
基线利用稀疏性，或soft gate不能在独立留出数据上
改善候选质量，则停止该方向。来源文章中的未来预测及GPU速度比较在RISA同条件复现前仅作为研究动机，不作为实证结果。
