# 音乐图谱数据挖掘分析计划

## 一、数据结构梳理（已完成基础部分）

### 节点类型
- **Song**: 歌曲（字段：name, release_date, written_date, genre, single, notable, notoriety_date）
- **Person**: 音乐人（字段：name, stage_name）
- **Album**: 专辑（字段：name, release_date, genre, notable, written_date, notoriety_date）
- **RecordLabel**: 唱片公司（字段：name）
- **MusicalGroup**: 音乐组合/乐队（通过MemberOf关系连接Person）

### 边类型（关系）
- **PerformerOf**: 表演者关系（Person → Song/Album）
- **ComposerOf**: 作曲者关系（Person → Song/Album）
- **LyricistOf**: 作词者关系（Person → Song/Album）
- **ProducerOf**: 制作人关系（Person → Song/Album）
- **RecordedBy**: 录制关系（Song/Album → RecordLabel）
- **DistributedBy**: 发行关系（Song/Album → RecordLabel）
- **MemberOf**: 成员关系（Person → 可能是乐队/组织）
- **CoverOf**: 翻唱关系（Song → Song）
- **InterpolatesFrom**: 插值来源（Song → Song）
- **InStyleOf**: 风格类似（Song → Song）
- **LyricalReferenceTo**: 歌词引用（Song → Song）
- **DirectlySamples**: 直接采样（Song → Song）

## 二、你的分析计划评估与补充建议

### 1. 评估音乐人的表现

#### 你的计划（很好）：
- ✅ 统计每个歌手有哪些歌，并按专辑分组
- ✅ 分离是否成名的歌曲
- ✅ 按流派分类歌曲

#### 补充建议：
**a) 多维度表现指标**
- **作品数量**：总作品数、单曲数、专辑数
- **成名率**：notable作品占比
- **时间跨度**：最早作品到最晚作品的时间范围
- **角色多样性**：作为Performer/Composer/Lyricist/Producer的角色数
- **合作网络**：与其他音乐人的合作次数
- **唱片公司关系**：与多少唱片公司合作
- **影响力指标**：
  - 被翻唱次数（CoverOf的target）
  - 被采样次数（DirectlySamples的target）
  - 被引用次数（InterpolatesFrom, LyricalReferenceTo的target）
  - 被风格模仿次数（InStyleOf的target）

**b) 流派表现**
- 每个音乐人在不同流派的作品数
- 在特定流派（如Oceanus Folk）的专业度
- 流派转换模式（是否跨流派创作）

**c) 时间维度分析**
- 活跃期长度
- 成名时间点（首次notable作品时间）
- 创作高峰期（作品密集度）

### 2. 分析音乐流派发展

#### 你的计划（很好）：
- ✅ 按流派分类，时间轴排序
- ✅ 找出翻唱关系
- ✅ 统计每一年份各流派的歌曲数量

#### 补充建议：
**a) 流派生命周期分析**
- 流派出现时间（首次出现年份）
- 流派发展曲线（年度作品数趋势）
- 流派衰落/复苏模式
- 流派间的关系网络（通过InStyleOf等关系）

**b) 流派创新与传承**
- **翻唱网络**：分析CoverOf关系，识别经典作品
- **风格演化**：通过InStyleOf关系追踪风格传承
- **采样与插值**：DirectlySamples和InterpolatesFrom关系分析
- **跨流派融合**：分析同时属于多个流派的特征

**c) 流派影响力指标**
- 每个流派的notable作品占比
- 流派间的翻唱频率（哪个流派更常被翻唱）
- 流派与唱片公司的关系

**d) 特别针对Oceanus Folk**
- 历史发展轨迹
- 关键人物和作品
- 与其他流派的交叉关系
- 发展趋势预测（基于时间序列）

### 3. 预测Oceanus Folk超级明星

#### 补充建议（这是核心任务）：
**a) 特征工程（核心特征）**
- **当前表现**：
  - Oceanus Folk作品总数
  - Oceanus Folk notable作品数
  - Oceanus Folk成名率（notable作品占比）
  
- **上升趋势**（最近5年，2024-2029）：
  - 作品数量增长率
  - notable作品增长率
  - 首次Oceanus Folk作品时间（越晚越好，说明是新星）
  
- **合作网络**：
  - 与已成名Oceanus Folk音乐人的合作次数
  - 在Oceanus Folk网络中的中心性（PageRank, Betweenness）
  - 与关键节点的距离
  
- **创新性**：
  - 原创作品占比（非CoverOf, 非DirectlySamples）
  - 是否有InStyleOf关系（被他人模仿）
  - 是否有InterpolatesFrom（被他人引用）
  
- **唱片公司支持**：
  - 合作的RecordLabel数量
  - 与知名唱片公司的合作（可定义知名度为：合作音乐人数量多的公司）
  
- **时间因素**：
  - 活跃时长（但不要太长，新星更可能）
  - 最近活跃时间（2024-2029）
  - 首次作品时间（相对较晚）
  
- **多角色能力**：
  - 角色多样性（Composer/Lyricist/Performer/Producer）
  - 在Oceanus Folk中担任的角色数

**b) 历史超级明星分析**
- 找出历史上Oceanus Folk的超级明星（notable作品多、影响力大）
- 提取他们的特征模式：
  - 成名路径（作品数增长曲线）
  - 合作模式
  - 时间特征
  - 角色特征

**c) 预测模型**
- **监督学习**：
  - 标签：历史Oceanus Folk明星（1）vs 普通音乐人（0）
  - 特征：以上所有特征
  - 模型：XGBoost, Random Forest, 神经网络
  
- **无监督学习**：
  - 聚类分析：找出与历史明星相似的群体
  - 异常检测：找出表现异常突出（可能成为明星）的音乐人
  
- **时间序列预测**：
  - 基于个人作品增长趋势预测未来5年
  - 基于流派发展趋势调整预测

**d) 网络分析**
- **中心性指标**：
  - Degree Centrality（连接数）
  - Betweenness Centrality（中介度）
  - Closeness Centrality（接近度）
  - PageRank（影响力排名）
  
- **社区检测**：
  - 识别Oceanus Folk社区
  - 检测社区内的核心人物

**e) 综合评分公式（建议）**
```
超级明星潜力分数 = 
  0.25 × 当前表现分数（作品数、notable率）
+ 0.25 × 上升趋势分数（增长率、最近活跃度）
+ 0.20 × 网络影响力分数（中心性、合作）
+ 0.15 × 创新性分数（原创性、被引用）
+ 0.10 × 支持度分数（唱片公司、合作网络）
+ 0.05 × 角色多样性分数
```

**f) 验证方法**
- 交叉验证：使用历史数据验证模型
- 时间分割：用2020年前的数据训练，预测2020-2024的表现
- 特征重要性分析：找出最关键的特征

## 三、额外推荐的分析方向

### 1. 社交网络分析
- **合作网络**：音乐人之间的合作关系图
- **影响力传播**：通过翻唱、采样等关系追踪影响力
- **社区发现**：识别音乐人群体/流派社区

### 2. 唱片公司分析
- 各唱片公司的流派偏好
- 唱片公司对音乐人成名的促进作用
- 唱片公司的时间发展轨迹

### 3. 专辑与单曲分析
- 专辑vs单曲的成名率对比
- 专辑内歌曲的流派多样性
- 专辑制作团队分析

### 4. 时间模式分析
- 创作周期（written_date到release_date的时长）
- 成名时间点（notable_date vs release_date）
- 季节性模式（是否有特定月份/年份的创作高峰）

### 5. 网络特征分析
- 节点中心性（degree, betweenness, closeness）
- PageRank算法计算影响力
- 小世界网络特征

## 四、具体实施建议

### 数据预处理步骤：
1. **构建节点索引**：按ID快速查找节点
2. **构建边索引**：按source和target分别索引
3. **提取时间信息**：统一处理所有日期字段
4. **构建流派-作品映射**：快速查找流派相关作品
5. **构建音乐人-作品映射**：按角色类型分类

### 分析工具推荐：
- **网络分析**：NetworkX（Python）
- **聚类分析**：scikit-learn（KMeans, DBSCAN, 层次聚类）
- **时间序列**：pandas, statsmodels
- **可视化**：D3.js, Plotly, Gephi（网络可视化）
- **预测模型**：scikit-learn, XGBoost, 时间序列模型

### 评估指标建议：
- **音乐人评分**：加权综合指标（作品数×0.3 + 成名率×0.3 + 影响力×0.2 + 时间跨度×0.1 + 角色多样性×0.1）
- **流派发展指数**：年度作品数、notable占比、创新度
- **超级明星预测**：基于历史数据的特征匹配度

## 五、数据结构关键发现

### 已确认的结构：
1. **Album与Song的关系**：
   - ❌ 没有直接的"包含"关系边
   - ✅ 通过共享的Person节点间接关联（同一Person既参与Album又参与Song）
   - ✅ 有CoverOf, InStyleOf等关系连接Album和Song（2350条）

2. **MemberOf关系**：
   - ✅ target是MusicalGroup节点类型
   - ✅ 表示Person属于某个音乐组合/乐队
   - ✅ 共有568条MemberOf关系，涉及约20个MusicalGroup

3. **边类型统计**（共12种）：
   - PerformerOf: 13,587条（最多）
   - RecordedBy: 3,798条
   - ComposerOf: 3,290条
   - ProducerOf: 3,209条
   - DistributedBy: 3,013条
   - LyricistOf: 2,985条
   - InStyleOf: 2,289条
   - InterpolatesFrom: 1,574条
   - LyricalReferenceTo: 1,496条
   - CoverOf: 1,429条
   - DirectlySamples: 619条
   - MemberOf: 568条

### 需要处理的问题：
1. **Album分组**：由于没有直接的包含关系，需要通过以下方式推断：
   - 相同Person在同一时间段的Album和Song
   - 相同RecordLabel和相同时间段的作品
   - 相同genre和时间相近的作品

2. **时间字段优先级**：建议优先级：
   - 对于作品分析：release_date > written_date > notoriety_date
   - 对于创作分析：written_date > release_date

3. **成名标准**：notable=true是主要标准，但可以结合：
   - notoriety_date存在
   - 被翻唱/采样次数
   - 影响力传播

4. **数据完整性**：需要检查和处理：
   - 缺失的日期字段
   - 缺失的genre字段
   - 缺失的关系数据

---

**下一步行动建议**：
1. 先完成数据预处理，构建所有必要的索引和映射
2. 实现基础统计功能（你的计划1-5）
3. 在此基础上进行深度分析（聚类、预测等）
4. 可视化和结果展示

