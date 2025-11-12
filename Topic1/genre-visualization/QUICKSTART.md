# 快速启动指南

## 前置要求

- Node.js 16+ 和 npm

## 安装步骤

1. **进入项目目录**
   ```bash
   cd genre-visualization
   ```

2. **安装依赖**
   ```bash
   npm install
   ```

3. **确保数据文件存在**
   - 数据文件应该位于：`public/data/visualization_data.json`
   - 如果文件不存在，请从项目根目录的 `data/` 目录复制：
     ```bash
     # Windows PowerShell
     Copy-Item "..\data\visualization_data.json" -Destination "public\data\visualization_data.json"
     
     # Linux/Mac
     cp ../data/visualization_data.json public/data/visualization_data.json
     ```

4. **启动开发服务器**
   ```bash
   npm run dev
   ```

5. **打开浏览器**
   - 应用会自动在浏览器中打开（通常是 http://localhost:3000）
   - 如果没有自动打开，请手动访问该地址

## 使用说明

### 主视图（流派视图）
- 显示26个音乐流派的圆圈
- **圆圈大小**：代表属于该流派的音乐人数量（genre_share > 50%）
- **颜色**：每个流派使用不同颜色
- **交互**：点击任意流派圆圈进入第二层视图

### 第二层视图（音乐人视图）
- 显示选中流派下的音乐人（最多50名）
- **圆圈大小**：代表音乐人的分数（score）
- **布局**：使用力导向图算法，确保圆圈不重叠
- **交互**：
  - 悬停圆圈查看音乐人名称和分数
  - 点击"返回流派视图"按钮返回主视图

## 常见问题

### 1. 数据加载失败
- **问题**：页面显示"数据加载失败"
- **解决**：检查 `public/data/visualization_data.json` 文件是否存在
- **解决**：检查浏览器控制台的错误信息

### 2. 圆圈重叠
- **问题**：流派或音乐人圆圈重叠
- **解决**：这是正常的，力导向图算法会自动调整位置。如果重叠严重，可以刷新页面重新计算布局

### 3. 样式显示异常
- **问题**：页面样式不正确
- **解决**：清除浏览器缓存，重新加载页面
- **解决**：检查浏览器控制台是否有CSS加载错误

### 4. 端口被占用
- **问题**：`npm run dev` 报错端口被占用
- **解决**：修改 `vite.config.js` 中的端口号，或关闭占用端口的程序

## 调试技巧

1. **打开浏览器开发者工具**（F12）
2. **查看控制台日志**：
   - `[App]` - 应用主组件日志
   - `[GenreView]` - 流派视图组件日志
   - `[ArtistView]` - 音乐人视图组件日志
3. **检查网络请求**：确保 `visualization_data.json` 文件成功加载
4. **检查数据格式**：确保JSON文件格式正确

## 构建生产版本

```bash
npm run build
```

构建后的文件会在 `dist/` 目录中，可以部署到任何静态文件服务器。

