# G2 Persistence Evaluation / G2永続化評価 / G2持久化评估

Date: 2026-09-10. Benchmark: `g2-persistence.0.0`. Manifest SHA-256: `e0336e7dd2d5172f1b0edf92ee769176b25cefb8e7c0bad15d90821eeda0ebf0`.

## Contract / 評価契約 / 评估契约

日本語: G2の全training Stateを5固定seedで生成し、schema v4と、Event・候補・pattern・primitiveを旧verbose形式へ戻した同値payloadを比較する。再読込前後で全static予測、全goal計画、Composition、branch simulationが完全一致し、schema v4が小さい場合だけ採用する。読込p95は各seed 15回のJSON decodeと`RisaState.from_dict`を測る。

English: Build complete G2 training states for five fixed seeds and compare schema v4 with an equivalent payload using verbose event, candidate, pattern and primitive records. Accept only when schema v4 is smaller and all static predictions, goal plans, composition probes and branch simulations match before and after reload. Load p95 covers 15 JSON-decode plus `RisaState.from_dict` runs per seed.

简体中文: 使用5个固定seed生成完整G2训练State，并比较schema v4与恢复为旧verbose Event、候选、pattern及primitive记录的等价payload。仅当schema v4更小，且重载前后所有static预测、goal规划、Composition及分支simulation完全一致时才采纳。读取p95按每个seed 15次JSON解析与`RisaState.from_dict`测量。

## Result / 結果 / 结果

| Metric | Result |
| --- | ---: |
| Seeds / seed数 | 5 |
| Training events | 275 |
| Prediction queries | 5,000 |
| Planning queries | 2,250 |
| Mean verbose-equivalent state | 134,478 bytes |
| Mean schema-v4 state | 102,287 bytes |
| Reduction | 23.94% |
| Mean load p95 | 2.030841 ms |
| Prediction mismatches | 0 |
| Planning mismatches | 0 |
| Composition matches | 5 / 5 |
| Simulation matches | 5 / 5 |

日本語: schema v4永続化を採用する。候補はEventから再発見し、評価fingerprint一致時だけ採否を復元する。Event、pattern、structural pattern、primitiveは重複IDと既定値を省略する。graphのenergy・dormancy・reliability、PrimitiveのReplay統計・採用状態・適用前提は履歴として保持する。保存量は23.94%減ったが、以前のG2比較における具体遷移baselineとの差を解消する規模ではない。

English: Accept schema-v4 persistence. Candidates are rediscovered from events and lifecycle evaluations return only on fingerprint match. Event, pattern, structural-pattern and primitive records omit duplicated IDs and defaults. Graph energy, dormancy and reliability plus primitive replay, adoption and applicability history remain persisted. The 23.94% reduction is useful but does not close the earlier storage gap to the grounded-transition baseline.

简体中文: 采纳schema v4持久化。候选从Event重新发现，仅在评估fingerprint一致时恢复生命周期状态。Event、pattern、structural pattern及primitive记录省略重复ID与默认值；graph的energy、dormancy、reliability，以及Primitive的Replay、采纳与适用历史仍保留。23.94%的削减有效，但尚不足以消除此前与具体转移baseline的存储差距。

## Roadmap / ロードマップ / 路线图

- [Done] schema v4の候補再構築、compact Event、lossless導出recordをG2全Stateで検証 / Validate candidate reconstruction, compact events and lossless derived records across full G2 states / 在完整G2 State上验证候选重建、紧凑Event及无损派生记录
- [Done] 5,000予測、2,250計画、Composition・simulationで再読込一致 / Verify reload equivalence over 5,000 predictions, 2,250 plans, composition and simulation / 在5,000次预测、2,250次规划、Composition及simulation上验证重载等价性
- [Next] 候補のspecialization・merge・dormancyと二世代候補を、循環支持禁止と独立held-out gate付きで実装 / Implement candidate specialization, merge, dormancy and second-generation candidates with circular-support prevention and an independent held-out gate / 实现候选分化、合并、休眠及第二代候选，并加入循环支持防止与独立留出门槛

## Artifacts / 成果物 / 产物

- Manifest: [`experiments/g2_persistence_manifest.json`](../experiments/g2_persistence_manifest.json)
- Runner: [`experiments/g2_persistence_evaluation.py`](../experiments/g2_persistence_evaluation.py)
- Results: [`g2-persistence-results.json`](g2-persistence-results.json)
