# 音乐图谱数据挖掘分析系统

## 项目概述

这是一个用于分析音乐图谱数据的完整数据挖掘系统，实现了三个核心任务：
1. **评估音乐人的表现**
2. **分析音乐流派发展**
3. **预测Oceanus Folk超级明星**

## 文件结构

```
Topic1/
├── Topic1_graph.json          # 原始数据文件
├── data_preprocessing.py       # 数据预处理模块
├── task_analysis.py           # 三个任务的分析实现
├── run_analysis.py           # 运行分析的入口脚本
├── save_results.py            # 保存分析结果的脚本
├── data_mining_analysis_plan.md  # 详细分析计划文档
└── README.md                  # 本文件
```

## 快速开始

### 1. 运行完整分析

```bash
python run_analysis.py
```

这将执行三个任务的分析，并显示示例结果。

### 2. 使用单个模块

```python
from data_preprocessing import MusicGraphProcessor
from task_analysis import Task1_PersonEvaluation, Task2_GenreAnalysis, Task3_OceanusFolkPrediction

# 初始化
processor = MusicGraphProcessor('Topic1_graph.json')

# 任务1：评估音乐人
task1 = Task1_PersonEvaluation(processor)
evaluation = task1.evaluate_person(person_id)

# 任务2：分析流派
task2 = Task2_GenreAnalysis(processor)
analysis = task2.analyze_genre_development('Oceanus Folk')

# 任务3：预测超级明星
task3 = Task3_OceanusFolkPrediction(processor)
candidates = task3.predict_superstars(top_n=20)
```

## 功能说明

### 数据预处理模块 (`data_preprocessing.py`)

**MusicGraphProcessor类**提供以下功能：

- `get_node(node_id)`: 根据ID获取节点
- `get_nodes_by_type(node_type)`: 获取特定类型的所有节点
- `get_edges_from(source_id)`: 获取从某个节点出发的所有边
- `get_edges_to(target_id)`: 获取指向某个节点的所有边
- `get_edges_by_type(edge_type)`: 获取特定类型的所有边
- `extract_date(node, priority)`: 提取节点日期（按优先级）
- `get_person_works(person_id)`: 获取音乐人的所有作品
- `get_album_songs(album_id, person_id)`: 推断专辑包含的歌曲

### 任务1：评估音乐人表现 (`Task1_PersonEvaluation`)

**功能**：
- `evaluate_person(person_id)`: 评估单个音乐人
- `evaluate_all_persons()`: 评估所有音乐人
- `get_person_works_grouped(person_id)`: 获取音乐人作品（按专辑分组）

**评估指标**：
- 总作品数（歌曲、专辑）
- 成名率（notable作品占比）
- 时间跨度（最早到最晚作品）
- 角色多样性（Performer/Composer/Lyricist/Producer）
- 流派分布
- 影响力分数（被翻唱、采样、引用次数）
- 合作网络规模
- 唱片公司支持
- 综合评分

### 任务2：分析音乐流派发展 (`Task2_GenreAnalysis`)

**功能**：
- `get_genre_timeline(genre)`: 获取流派时间线（按年份统计）
- `get_cover_relationships(genre)`: 获取翻唱关系
- `analyze_genre_development(genre)`: 完整分析流派发展
- `get_all_genres()`: 获取所有流派列表

**分析内容**：
- 年度作品数量统计
- 年度成名率
- 翻唱关系网络
- 翻唱时间模式
- 流派发展趋势

### 任务3：预测Oceanus Folk超级明星 (`Task3_OceanusFolkPrediction`)

**功能**：
- `extract_person_features(person_id)`: 提取音乐人特征
- `predict_superstars(top_n)`: 预测超级明星候选人

**特征维度**：
1. **当前表现**：OF作品数、成名作品数、成名率
2. **上升趋势**：最近5年作品数、增长率、首次OF作品时间
3. **创新性**：原创作品占比、被引用次数
4. **合作网络**：与已成名OF音乐人的合作
5. **支持度**：唱片公司数量
6. **角色多样性**：在OF中的角色数
7. **时间因素**：活跃时长、最近活跃时间

**评分公式**：
```
综合评分 = 
  0.25 × 当前表现分数
+ 0.25 × 上升趋势分数
+ 0.20 × 网络影响力分数
+ 0.15 × 创新性分数
+ 0.10 × 支持度分数
+ 0.05 × 角色多样性分数
```

## 数据结构

### 节点类型
- **Song**: 歌曲
- **Person**: 音乐人
- **Album**: 专辑
- **RecordLabel**: 唱片公司
- **MusicalGroup**: 音乐组合/乐队

### 边类型（关系）
- **PerformerOf**: 表演者关系
- **ComposerOf**: 作曲者关系
- **LyricistOf**: 作词者关系
- **ProducerOf**: 制作人关系
- **RecordedBy**: 录制关系
- **DistributedBy**: 发行关系
- **MemberOf**: 成员关系（Person → MusicalGroup）
- **CoverOf**: 翻唱关系
- **InterpolatesFrom**: 插值来源
- **InStyleOf**: 风格类似
- **LyricalReferenceTo**: 歌词引用
- **DirectlySamples**: 直接采样

## 输出结果

### 任务1输出示例
```python
{
    'name': '音乐人姓名',
    'total_works': 10,
    'notable_rate': 0.8,
    'time_span': 15,
    'score': 85.5,
    'genre_distribution': {'Oceanus Folk': 5, 'Dream Pop': 3},
    ...
}
```

### 任务2输出示例
```python
{
    'genre': 'Oceanus Folk',
    'yearly_counts': {2020: 10, 2021: 15, ...},
    'yearly_notable_rate': {2020: 0.8, ...},
    'cover_stats': {'total_covers': 126, ...},
    ...
}
```

### 任务3输出示例
```python
[
    {
        'name': '候选人姓名',
        'score': 86.33,
        'of_total': 36,
        'of_notable_count': 24,
        'recent_active': 2040,
        ...
    },
    ...
]
```

## 保存分析结果

运行 `save_results.py` 可以将分析结果保存为JSON文件：

```bash
python save_results.py
```

这将生成：
- `person_evaluations.json`: 所有音乐人的评估结果
- `genre_analysis.json`: 流派分析结果
- `oceanus_folk_candidates.json`: Oceanus Folk超级明星候选人

## 扩展功能建议

1. **数据可视化**：使用NetworkX和matplotlib/plotly可视化网络和趋势
2. **机器学习**：使用XGBoost等模型改进预测准确性
3. **聚类分析**：对音乐人进行聚类分析
4. **时间序列预测**：预测未来流派发展趋势
5. **网络分析**：计算PageRank、中心性等指标

## 注意事项

1. **Album-Song关系**：数据中没有直接的包含关系，系统通过共享Person、时间、流派等推断
2. **日期字段**：优先级为 release_date > written_date > notoriety_date
3. **性能**：处理全部数据可能需要一些时间，建议先使用示例数据测试

## 依赖库

```
json
collections
datetime
re
```

## 许可证

本项目用于数据可视化课程作业。



person_gener_matrix这个文件里面记录了每个人对应的流派概率（按照歌曲的分类）


