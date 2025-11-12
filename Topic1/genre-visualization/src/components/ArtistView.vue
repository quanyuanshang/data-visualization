<template>
  <div class="artist-view">
    <!-- 标题栏 -->
    <header class="header">
      <button class="back-button" @click="handleGoBack">
        ← 返回流派视图
      </button>
      <div class="title-info">
        <h1>{{ genre }}</h1>
        <p class="subtitle">共 {{ artists.length }} 位音乐人（显示前50名）</p>
      </div>
    </header>
    
    <!-- SVG 画布容器 -->
    <div class="canvas-container" ref="containerRef">
      <svg :width="width" :height="height" ref="svgRef">
        <!-- 定义渐变 -->
        <defs>
          <radialGradient id="artist-gradient" cx="30%" cy="30%">
            <stop offset="0%" :stop-color="genreColor" stop-opacity="1" />
            <stop offset="100%" :stop-color="genreColor" stop-opacity="0.6" />
          </radialGradient>
        </defs>
        
        <!-- 音乐人圆圈组 -->
        <g class="artists-group">
          <circle
            v-for="(node, index) in artistNodes"
            :key="node.artist.person_id"
            :cx="node.x"
            :cy="node.y"
            :r="node.radius"
            fill="url(#artist-gradient)"
            :stroke="genreColor"
            :stroke-width="1.5"
            class="artist-circle"
            :class="{ 'hovered': hoveredArtist === node.artist.person_id }"
            @click="handleArtistClick(node.artist)"
            @mouseenter="hoveredArtist = node.artist.person_id"
            @mouseleave="hoveredArtist = null"
          />
          
          <!-- 音乐人名称标签（只在悬停时显示） -->
          <g
            v-for="node in artistNodes"
            :key="`label-${node.artist.person_id}`"
            v-show="hoveredArtist === node.artist.person_id"
            class="artist-label-group"
          >
            <rect
              :x="node.x - node.labelWidth / 2 - 4"
              :y="node.y - node.radius - 25"
              :width="node.labelWidth + 8"
              :height="20"
              fill="rgba(0, 0, 0, 0.8)"
              rx="4"
            />
            <text
              :x="node.x"
              :y="node.y - node.radius - 12"
              fill="white"
              text-anchor="middle"
              dominant-baseline="middle"
              class="artist-label"
              font-size="12"
            >
              {{ node.artist.name }}
            </text>
            <text
              :x="node.x"
              :y="node.y - node.radius - 2"
              fill="white"
              text-anchor="middle"
              dominant-baseline="middle"
              class="artist-score"
              font-size="10"
            >
              分数: {{ node.artist.score.toFixed(1) }}
            </text>
          </g>
        </g>
      </svg>
      
      <!-- 图例 -->
      <div class="legend">
        <div class="legend-item">
          <div class="legend-circle" :style="{ background: genreColor }"></div>
          <span>圆圈大小 = 音乐人分数</span>
        </div>
        <div class="legend-item">
          <span>悬停查看详细信息</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import * as d3 from 'd3'

// ==================== Props ====================
const props = defineProps({
  genre: {
    type: String,
    required: true
  },
  artists: {
    type: Array,
    required: true
  }
})

// ==================== Emits ====================
const emit = defineEmits(['go-back'])

// ==================== 响应式数据 ====================
const containerRef = ref(null)
const svgRef = ref(null)
const width = ref(1200)
const height = ref(800)
const hoveredArtist = ref(null)

// ==================== 计算属性 ====================
/**
 * 获取流派的颜色（与 GenreView 中的颜色保持一致）
 */
const genreColor = computed(() => {
  // 使用与 GenreView 相同的颜色生成逻辑
  const genres = [
    "Acoustic Folk", "Alternative Rock", "Americana", "Avant-Garde Folk",
    "Blues Rock", "Celtic Folk", "Darkwave", "Desert Rock", "Doom Metal",
    "Dream Pop", "Emo/Pop Punk", "Indie Folk", "Indie Pop", "Indie Rock",
    "Jazz Surf Rock", "Lo-Fi Electronica", "Oceanus Folk", "Post-Apocalyptic Folk",
    "Psychedelic Rock", "Sea Shanties", "Southern Gothic Rock", "Space Rock",
    "Speed Metal", "Symphonic Metal", "Synthpop", "Synthwave"
  ]
  const index = genres.indexOf(props.genre)
  // 使用与 GenreView 相同的颜色数组
  const colors = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
    '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5',
    '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7',
    '#dda15e'
  ]
  return colors[index % colors.length]
})

/**
 * 计算音乐人节点的位置和大小
 * 使用力导向图布局，确保圆圈不重叠
 * 圆圈半径基于音乐人的分数
 */
const artistNodes = computed(() => {
  if (!props.artists || props.artists.length === 0) return []
  
  // 准备节点数据
  const nodes = props.artists.map(artist => ({
    artist,
    score: artist.score || 0
  }))
  
  // 计算半径（基于分数）
  const scores = nodes.map(n => n.score)
  const minScore = Math.min(...scores)
  const maxScore = Math.max(...scores)
  
  // 半径范围：最小8px，最大40px
  const minRadius = 8
  const maxRadius = 40
  const radiusScale = d3.scaleLinear()
    .domain([minScore, maxScore])
    .range([minRadius, maxRadius])
  
  // 为每个节点设置半径
  nodes.forEach(node => {
    node.radius = radiusScale(node.score)
    // 计算标签宽度（用于悬停提示框）
    node.labelWidth = Math.max(
      node.artist.name.length * 7,
      (`分数: ${node.artist.score.toFixed(1)}`).length * 6
    )
  })
  
  // 使用力导向图布局算法计算位置
  // 创建力模拟器
  const simulation = d3.forceSimulation(nodes)
    .force('charge', d3.forceManyBody().strength(-50)) // 排斥力
    .force('center', d3.forceCenter(width.value / 2, height.value / 2)) // 中心力
    .force('collision', d3.forceCollide().radius(d => d.radius + 5)) // 碰撞检测，确保不重叠
    .stop()
  
  // 运行模拟直到稳定
  for (let i = 0; i < 300; i++) {
    simulation.tick()
  }
  
  // 确保所有节点都在画布范围内
  nodes.forEach(node => {
    node.x = Math.max(node.radius, Math.min(width.value - node.radius, node.x))
    node.y = Math.max(node.radius, Math.min(height.value - node.radius, node.y))
  })
  
  return nodes
})

// ==================== 方法 ====================
/**
 * 处理音乐人圆圈点击事件
 */
function handleArtistClick(artist) {
  console.log(`[ArtistView] 点击音乐人: ${artist.name}, 分数: ${artist.score}`)
  // 可以在这里添加更多交互，比如显示详细信息面板
}

/**
 * 处理返回按钮点击事件
 */
function handleGoBack() {
  emit('go-back')
}

/**
 * 初始化画布尺寸
 */
function initCanvasSize() {
  if (containerRef.value) {
    width.value = containerRef.value.clientWidth || 1200
    height.value = containerRef.value.clientHeight || 800
  }
}

// ==================== 生命周期 ====================
onMounted(() => {
  initCanvasSize()
  
  // 监听窗口大小变化
  window.addEventListener('resize', () => {
    initCanvasSize()
  })
})

// 当数据变化时，重新计算布局
watch(() => [props.artists, props.genre], () => {
  if (props.artists && props.artists.length > 0) {
    nextTick(() => {
      console.log(`[ArtistView] 数据更新，重新计算布局，音乐人数量: ${props.artists.length}`)
    })
  }
}, { deep: true })
</script>

<style scoped>
.artist-view {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.header {
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 20px;
  background: rgba(0, 0, 0, 0.2);
  color: white;
}

.back-button {
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 6px;
  color: white;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-button:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateX(-3px);
}

.title-info {
  flex: 1;
}

.title-info h1 {
  font-size: 28px;
  margin-bottom: 8px;
}

.subtitle {
  font-size: 14px;
  opacity: 0.9;
}

.canvas-container {
  flex: 1;
  width: 100%;
  overflow: hidden;
  position: relative;
}

svg {
  display: block;
  width: 100%;
  height: 100%;
}

.artist-circle {
  cursor: pointer;
  transition: all 0.3s ease;
}

.artist-circle:hover {
  stroke-width: 3;
  filter: brightness(1.3);
}

.artist-circle.hovered {
  stroke-width: 3;
  filter: brightness(1.3);
}

.artist-label-group {
  pointer-events: none;
}

.artist-label {
  font-weight: 600;
}

.artist-score {
  opacity: 0.9;
}

.legend {
  position: absolute;
  bottom: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.9);
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  font-size: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.legend-item:last-child {
  margin-bottom: 0;
}

.legend-circle {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.2);
}
</style>

