# 音乐流派可视化应用

这是一个基于 Vue 3 和 D3.js 的音乐流派可视化应用，用于展示26个音乐流派及其下的音乐人。

## 功能特性

1. **主视图（流派视图）**
   - 显示26个音乐流派的圆圈
   - 每个圆圈的大小代表属于该流派的音乐人数量（判断标准：genre_share > 50%）
   - 每个流派使用不同颜色显示
   - 支持点击流派进入第二层视图

2. **第二层视图（音乐人视图）**
   - 显示选中流派下的所有音乐人（最多显示前50名）
   - 每个音乐人用圆圈表示，圆圈大小代表其分数（score）
   - 使用力导向图布局，确保圆圈不重叠
   - 悬停显示音乐人名称和分数
   - 支持返回流派视图

## 技术栈

- Vue 3 (Composition API)
- D3.js 7.x
- Vite (构建工具)

## 安装和运行

1. 安装依赖：
```bash
npm install
```

2. 确保数据文件位置正确：
   - 将 `data/visualization_data.json` 复制到 `public/data/` 目录
   - 或者修改 `src/App.vue` 中的数据加载路径

3. 启动开发服务器：
```bash
npm run dev
```

4. 构建生产版本：
```bash
npm run build
```

## 项目结构

```
genre-visualization/
├── src/
│   ├── components/
│   │   ├── GenreView.vue      # 流派视图组件
│   │   └── ArtistView.vue     # 音乐人视图组件
│   ├── App.vue                # 主应用组件
│   ├── main.js                # 应用入口
│   └── style.css              # 全局样式
├── public/
│   └── data/
│       └── visualization_data.json  # 可视化数据
├── index.html                 # HTML 模板
├── package.json               # 项目配置
├── vite.config.js            # Vite 配置
└── README.md                  # 说明文档
```

## 代码说明

### 主要组件

#### App.vue
- 主应用组件，负责视图切换和数据加载
- 管理两个视图状态：`genres`（流派视图）和 `artists`（音乐人视图）

#### GenreView.vue
- 流派视图组件
- 使用 D3 力导向图布局算法计算26个流派圆圈的位置
- 圆圈大小基于该流派的音乐人数量
- 每个流派使用不同颜色

#### ArtistView.vue
- 音乐人视图组件
- 使用 D3 力导向图布局算法计算音乐人圆圈的位置
- 圆圈大小基于音乐人的分数
- 支持悬停显示详细信息

### 关键功能实现

1. **流派判断逻辑**：在数据预处理阶段，已经筛选出 genre_share > 50% 的音乐人
2. **布局算法**：使用 D3 的 `forceSimulation` 实现力导向图布局，确保圆圈不重叠
3. **颜色方案**：使用 D3 的 `schemeCategory20` 和 `schemeSet3` 色板为26个流派分配颜色
4. **响应式设计**：支持窗口大小变化，自动调整画布尺寸

## 调试提示

- 打开浏览器开发者工具查看控制台日志
- 所有关键操作都有日志输出，格式为 `[组件名] 操作描述`
- 如果数据加载失败，检查 `public/data/visualization_data.json` 文件是否存在
- 如果布局异常，检查数据格式是否正确

## 数据格式

`visualization_data.json` 应包含以下结构：

```json
{
  "genres": ["流派1", "流派2", ...],
  "genres_data": {
    "流派1": {
      "count": 100,
      "display_count": 50,
      "artists": [
        {
          "person_id": 123,
          "name": "音乐人名称",
          "score": 85.5,
          "genre_share": 0.8
        }
      ]
    }
  }
}
```

