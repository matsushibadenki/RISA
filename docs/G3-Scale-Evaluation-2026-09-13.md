# G3.1 Indexed Event Access and Bounded Replay Evaluation — 2026-09-13

## Result / 結果 / 结果

[Done] 日本語: 3固定seedで1k・10k・100k Eventを比較し、全9条件をscaleごとの60秒予算内で完走した。index版とEvent全走査参照版は各12 query、計108 queryで精度100%、`PredictionResult`全fieldの差分0だった。Event参照作業量は最小63.49倍、p95 latencyは最小20.37倍改善し、事前に固定した「品質低下1ポイント以内、作業量またはp95を2倍以上改善」のgateを通過した。

[Done] English: Across three fixed seeds at 1k, 10k and 100k Events, all nine scale conditions completed within the 60-second per-scale budget. The indexed and full Event-scan reference paths both achieved 100% accuracy with zero differences across every `PredictionResult` field over 108 queries. Event-access work improved by at least 63.49× and p95 latency by at least 20.37×, passing the frozen gate of no more than one point of quality loss and at least 2× lower work or p95 latency.

[Done] 简体中文: 在3个固定seed、1千、1万及10万Event下，全部9个规模条件均在每个规模60秒预算内完成。索引路径与Event全扫描参考路径在108个query中精度均为100%，所有`PredictionResult`字段差异为0。Event访问工作量至少改善63.49倍，p95时延至少改善20.37倍，通过预先固定的门槛：质量下降不超过1个百分点，工作量或p95至少改善2倍。

## Protocol / 評価方法 / 评估方法

- Manifest: `experiments/g3_scale_manifest.json`
- Result artifact: `docs/g3-scale-results.json`
- Manifest SHA-256: `b36767068c47c5192f71b516a30968d8088739c5e93b96affea84feb2417ce40`
- Seeds: `17, 37, 73`; scales: `1,000, 10,000, 100,000`; measured queries: `12` per row.
- The full-scan reference reconstructs prediction count tables, activation postings and evidence postings from every immutable Event for every query, then calls the same predictor as the indexed path.
- The indexed path reads in-memory derived indexes. Exact `PredictionResult` equality checks predicted effects, scores, evidence IDs, paths, status and applicability basis.
- Replay uses a derived chronological Event index. Its selected window is compared with a full sort, and selection work must remain within the fixed 128-Event budget.

## Measurements / 実測 / 实测

Values below are the median across three seeds. The adoption gate uses the worst row, not these medians.

| Events | Indexed p95 | Full scan p95 | Median latency ratio | Median Event-work ratio | Replay selection | Stored State |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1,000 | 0.190 ms | 4.318 ms | 22.7× | 64.5× | 128 | 280,277 bytes |
| 10,000 | 0.444 ms | 57.321 ms | 123.2× | 64.1× | 128 | 2,360,236 bytes |
| 100,000 | 4.327 ms | 2,277.311 ms | 519.9× | 64.0× | 128 | 23,249,427 bytes |

日本語: 時系列indexへの通常の末尾追加は一つのIDだけを更新し、100k条件のupdate p95中央値は0.0036 ms、128件のReplay window選択p95中央値は0.0357 msだった。Replay windowは全9条件で全sort参照と一致し、選択時に調べたEventは128件だった。時系列indexは永続化せず、読込時にEventから再構築するため、schema v4 payloadを増やさない。

English: Normal chronological-index appends update one ID; at 100k, median update p95 was 0.0036 ms and median p95 for selecting the 128-Event Replay window was 0.0357 ms. Replay windows matched the full-sort reference in all nine rows and examined 128 Events during selection. The chronological index is derived on load rather than persisted, so it does not enlarge the schema-v4 payload.

简体中文: 时序索引的正常末尾追加只更新一个ID；10万Event条件下update p95中位数为0.0036 ms，选择128个Event的Replay窗口p95中位数为0.0357 ms。全部9个条件的Replay窗口与全排序参考一致，选择阶段检查128个Event。时序索引在读取时派生而不持久化，因此不会增加schema v4 payload。

## Scope / 適用範囲 / 适用范围

日本語: これは合成Event上の予測read modelとReplay選択のscale評価である。fixtureは完全なgraph構築、オンライン学習、候補発見、planner探索を実行せず、それらの100k性能を示さない。full-scan時間はこの実行環境の参考値であり、機種間で一般化しない。採用対象はindex付きEvent参照と有界Replay選択であり、RISA全体のscale完了宣言ではない。

English: This evaluates prediction read models and Replay selection over synthetic Events. The fixture does not run full graph construction, online learning, candidate discovery or planner search, so it does not establish their 100k performance. Full-scan timings are local-machine measurements and are not portable. The adopted result covers indexed Event access and bounded Replay selection, not end-to-end RISA scalability.

简体中文: 该评估针对合成Event上的预测read model及Replay选择。fixture未运行完整graph构建、在线学习、候选发现或planner搜索，因此不能证明这些路径在10万规模下的性能。全扫描时间是本机测量，不可直接推广到其他机器。采纳范围是索引化Event访问及有界Replay选择，而非宣告RISA整体规模问题已完成。

## Roadmap decision / 方針 / 路线决定

[Done] G3.1 adopts the indexed Event-access path and derived chronological Replay index.

[Next] G3.2 measures drift recovery and forgetting while isolating context splitting, merging and dormancy. It must record recovery delay, retained pre-drift accuracy, adaptation count and bounded Replay work.

[Later] End-to-end 100k ingestion, graph construction, candidate discovery and planning need separate workload-specific profiles before deployment architecture is selected.
