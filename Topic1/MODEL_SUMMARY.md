# 艺人成功评分模型总结

## 1. 任务目标
- **目的**：构建一个可预测“高分艺人”的回归模型，利用 `Topic1_graph.json` 中的网络结构与属性，学习出与 `notable` 信号相关的成功潜力。
- **Ground Truth**：基于每位艺人关联作品的 `notable` 标记（是否上榜）以及与 notable 作品的互动（被采样/翻唱/致敬）。

## 2. 输入与输出
| 类型 | 文件 | 说明 |
| ---- | ---- | ---- |
| 输入 | `Topic1_graph.json` | 包含所有节点（Song/Album/Person/...）与边（PerformerOf、DirectlySamples 等）的音乐知识图谱。 |
| 输出 | `output/artist_features.parquet` | 特征表：每行对应一个艺人，包含图拓扑、统计、嵌入特征及目标分。 |
| 输出 | `output/artist_success_predictions.csv` | 预测结果：`target_score`（真实分）、`predicted_score`（模型分）、`residual`（残差）。 |
| 输出 | `output/artist_success_metrics.json` | 评估指标（RMSE、MAE、R²）、特征列清单、训练/测试样本数。 |
| 输出 | （可选）`output/artist_success_xgb.pkl` | 如果运行时指定 `--model-output`，会保存 XGBoost 模型权重，便于后续推理。 |

## 3. 模型训练流程
源代码在 `scripts/train_artist_success_model.py`，主要步骤如下：

### 3.1 数据加载与索引
- 使用 `MusicGraphProcessor`（见 `data_preprocessing.py`）加载 `Topic1_graph.json`，构建节点/边索引，便于快速查询：
  - `get_person_works(person_id)`：获取艺人所有作品（Song/Album，按 Performer/Composer 等角色划分）。
  - `get_edges_from` / `get_edges_to`：检索任意节点的入边/出边。

### 3.2 构建目标变量（Target Definition）
- 对每位 Person 聚合其作品：
  - 直接拥有 notable 歌曲/专辑：+10 分。
  - 被 notable 作品采样、翻唱、InStyleOf：+5 分。
  - 主动采样/翻唱 notable 作品：+2 分。
- 最终得分使用 `log1p` 平滑，缓解头部艺人得分过高带来的偏差。

### 3.3 特征工程（Feature Engineering）
1. **图拓扑特征**：
   - 构造合作图（Person 之间若共同参与某作品即连边），计算：
     - Degree / Degree Centrality：活跃度、合作广度。
     - Eigenvector Centrality：是否连接“大咖”。
   - 构造影响力子图（仅保留 DirectlySamples/CoverOf/InStyleOf 边）：
     - PageRank：衡量在采样/翻唱网络中的影响力。
     - HITS Hub & Authority：区分“灵感来源”与“枢纽”角色。

2. **统计特征**：
   - 作品总数、notable 作品数及占比。
   - Genre Entropy：流派多样性。
   - Career Span/最近年份：估计生涯长度及近期活跃程度。
   - Single 比例、合作人数、被不同唱片公司支持的数量。

3. **嵌入特征**：
   - 基于合作图生成谱嵌入（Truncated SVD），默认 32 维，可通过 `--embedding-dim` 调整。

### 3.4 模型选择与训练
- **算法**：XGBoost Regressor（`objective=reg:squarederror`）。
  - **原因**：
    - 擅长处理表格数据，能自动建模非线性关系与特征交互。
    - 对不同尺度的特征鲁棒，不需要复杂的标准化。
    - 内置特征重要性，便于解释哪些结构/属性对高分影响最大。
- **参数**（可配置）：
  - `n_estimators=600`、`learning_rate=0.05`、`max_depth=6`、`subsample=0.8`、`colsample_bytree=0.8` 等。
- 使用 `train_test_split`（默认 80/20）划分训练与测试集，度量指标包括 RMSE、MAE、R²。

### 3.5 预测与结果导出
- 训练完毕后，对全量艺人生成 `predicted_score`。
- 同时导出：
  - `artist_success_predictions.csv`：可直接用来排序寻找“潜力股”与“被高估者”。
  - `artist_features.parquet`：若需在其他工具复用特征。
  - `artist_success_metrics.json`：记录模型评估与特征名，便于复现与对比。
  - （可选）模型 pickle，用于在其他应用加载推理。

## 4. 使用方式
```powershell
python scripts/train_artist_success_model.py ^
  --graph Topic1_graph.json ^
  --embedding-dim 64 ^
  --predictions-csv output/artist_success_predictions.csv ^
  --feature-output output/artist_features.parquet ^
  --model-output output/artist_success_xgb.pkl
```
- 运行结束后，根据控制台输出确认 RMSE/MAE/R²。
- 使用 `predicted_score` 列为艺人打分。
- 若要分析特征贡献，可加载模型对象查看 `feature_importances_`。

## 5. 方法选择的理由
1. **Notable-Driven Target**：
   - `notable` 字段来源于真实榜单，代表可观测的“成功”信号。
   - 通过加入采样/翻唱关系，可以把“被认可”与“影响力扩散”都纳入目标。

2. **多源特征融合**：
   - 图拓扑 + 属性统计 + 嵌入共同描述：
     - 拓扑刻画合作/影响网络；
     - 属性体现作品结构与风格跨度；
     - 嵌入捕捉复杂的“圈层”相似性。
   - 组合这些特征后，模型能识别“虽然尚未爆红但网络位置极佳”的潜力艺人。

3. **XGBoost 回归**：
   - 相比线性模型，能更好地拟合非线性与特征交互；
   - 相比深度模型，对样本量与特征规模更友好，便于解释；
   - 训练速度快，易于调参与部署。

## 6. 后续扩展建议
- 引入 Node2Vec / GraphSAGE 等更强的图嵌入，捕捉更高阶的结构特征。
- 将特征重要性与残差结合，挖掘“被低估”的艺人列表，辅助 A&R 决策。
- 加入时间衰减、地区/厂牌等信息，构建更细粒度的成功预测模型。
- 对 `predicted_score` 做阈值或分层，转化为分类任务（高/中/低潜力）。

---
**文件位置**：`MODEL_SUMMARY.md`
