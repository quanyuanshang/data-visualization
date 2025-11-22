<template>
  <div class="artist-view">
    <!-- 标题栏 -->
    <header class="header">
      <button class="back-button" @click="handleGoBack">
        ← 返回流派视图
      </button>
      <div class="title-info">
        <h1>{{ genre }}</h1>
        <p class="subtitle">
          共 {{ props.totalArtists }} 位音乐人
          <span v-if="totalPages > 1">｜每页 {{ props.pageSize }} 位｜第 {{ props.currentPage }} / {{ totalPages }} 页</span>
        </p>
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
          <g
            v-for="node in artistNodes"
            :key="node.artist.person_id"
            class="artist-node"
            :transform="`translate(${node.x},${node.y})`"
          >
            <circle
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
              v-show="hoveredArtist === node.artist.person_id"
              class="artist-label-group"
            >
              <rect
                :x="-node.labelWidth / 2 - 4"
                :y="-node.radius - 25"
                :width="node.labelWidth + 8"
                :height="20"
                fill="rgba(0, 0, 0, 0.8)"
                rx="4"
              />
              <text
                :y="-node.radius - 12"
                fill="white"
                text-anchor="middle"
                dominant-baseline="middle"
                class="artist-label"
                font-size="12"
              >
                {{ node.artist.name }}
              </text>
              <text
                :y="-node.radius - 2"
                fill="white"
                text-anchor="middle"
                dominant-baseline="middle"
                class="artist-score"
                font-size="10"
              >
                {{ getMetricLabel(props.sortMetric) }}: {{ formatMetricValue(node.artist[props.sortMetric], props.sortMetric) }}
              </text>
            </g>
          </g>
        </g>
      </svg>
      
      <!-- 图例 -->
      <div class="legend">
        <div class="legend-item">
          <div class="legend-circle" :style="{ background: genreColor }"></div>
          <span>圆圈大小 = {{ getMetricLabel(props.sortMetric) }}</span>
        </div>
        <div class="legend-item">
          <span>悬停查看详细信息</span>
        </div>
      </div>
      
      <!-- 分页控件 -->
      <div class="pagination" v-if="totalPages > 1">
        <button class="page-btn" :disabled="props.currentPage <= 1" @click="changePage(props.currentPage - 1)">上一页</button>
        <span class="page-info">第 {{ props.currentPage }} / {{ totalPages }} 页</span>
        <button class="page-btn" :disabled="props.currentPage >= totalPages" @click="changePage(props.currentPage + 1)">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
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
  },
  totalArtists: {
    type: Number,
    required: true
  },
  currentPage: {
    type: Number,
    required: true
  },
  pageSize: {
    type: Number,
    required: true
  },
  allGenres: {
    type: Array,
    default: () => []
  },
  sortMetric: {
    type: String,
    default: 'score'
  }
})

// ==================== Emits ====================
const emit = defineEmits(['go-back', 'page-change', 'view-tracks'])

// ==================== 响应式数据 ====================
const containerRef = ref(null)
const svgRef = ref(null)
const width = ref(1200)
const height = ref(800)
const hoveredArtist = ref(null)
// 力导向图模拟器
let simulation = null
// 节点数据（响应式，用于动画）
const artistNodes = ref([])

// ==================== 计算属性 ====================
/**
 * 获取流派的颜色（与 GenreView 中的颜色保持一致）
 */
// 与流派视图共用的配色，按 genre 在数组中的索引映射
const palette = [
  '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
  '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
  '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5',
  '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7',
  '#dda15e'
]

function hashToColorIndex(name) {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = (hash << 5) - hash + name.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash) % palette.length
}

const genreColor = computed(() => {
  // 优先用父组件传入的 genre 列表找颜色，fallback 到 hash 颜色
  const available = Array.isArray(props.allGenres) && props.allGenres.length
    ? props.allGenres
    : []
  const index = available.indexOf(props.genre)
  if (index >= 0) {
    return palette[index % palette.length]
  }
  return palette[hashToColorIndex(props.genre)]
})

/**
 * 总页数
 */
const totalPages = computed(() => {
  if (!props.pageSize) return 1
  return Math.max(1, Math.ceil((props.totalArtists || 0) / props.pageSize))
})

/**
 * 初始化力导向图
 * 创建动态的力导向图模拟，让音乐人圆圈有引力和斥力效果，均匀分布
 */
function initForceSimulation() {
  if (!props.artists || props.artists.length === 0) {
    artistNodes.value = []
    return
  }
  
  // 停止之前的模拟（如果存在）
  if (simulation) {
    simulation.stop()
  }
  
  // 准备节点数据
  // 根据 sortMetric 选择用于半径计算的指标值
  const metricKey = props.sortMetric || 'score'
  const nodes = props.artists.map(artist => {
    // 获取当前指标的值
    const metricValue = artist[metricKey] ?? 0
    return {
      artist,
      score: artist.score || 0,
      metricValue: metricValue // 用于半径计算的指标值
    }
  })
  
  // 计算半径（基于选定的指标）
  const metricValues = nodes.map(n => n.metricValue)
  const minValue = Math.min(...metricValues)
  const maxValue = Math.max(...metricValues)
  
  // 半径范围：最小8px，最大40px
  const minRadius = 8
  const maxRadius = 40
  
  // 如果所有值相同，使用固定半径
  let radiusScale
  if (minValue === maxValue) {
    radiusScale = () => (minRadius + maxRadius) / 2
  } else {
    radiusScale = d3.scaleLinear()
      .domain([minValue, maxValue])
      .range([minRadius, maxRadius])
  }
  
  // 获取指标的中文标签（用于显示）
  const metricLabel = getMetricLabel(metricKey)
  
  // 为每个节点设置半径、初始位置和标签宽度
  nodes.forEach((node, i) => {
    node.radius = radiusScale(node.metricValue)
    // 计算标签宽度（用于悬停提示框）
    const valueText = formatMetricValue(node.artist[metricKey], metricKey)
    node.labelWidth = Math.max(
      node.artist.name.length * 7,
      (`${metricLabel}: ${valueText}`).length * 6
    )
    // 初始位置：围绕中心均匀分布
    const angle = (i / nodes.length) * 2 * Math.PI
    const initialRadius = Math.min(width.value, height.value) * 0.3
    node.x = width.value / 2 + Math.cos(angle) * initialRadius
    node.y = height.value / 2 + Math.sin(angle) * initialRadius
    node.vx = 0
    node.vy = 0
  })
  
  // 更新响应式节点数据
  artistNodes.value = nodes
  
  // 创建力导向图模拟器
  simulation = d3.forceSimulation(nodes)
    // 排斥力：节点之间相互排斥，避免重叠
    // strength 为负值表示排斥，绝对值越大排斥力越强
    .force('charge', d3.forceManyBody()
      .strength(d => {
        // 根据节点大小调整排斥力，大节点排斥力更强
        // 音乐人节点较小，使用较小的排斥力
        return -d.radius * 1.5
      })
      .distanceMax(300) // 最大作用距离
    )
    // 中心力：将节点拉向画布中心，保持整体布局
    .force('center', d3.forceCenter(width.value / 2, height.value / 2)
      .strength(0.08) // 中心力强度，稍大于流派视图，让节点更集中
    )
    // 碰撞检测：确保节点之间保持最小距离，不会重叠
    .force('collision', d3.forceCollide()
      .radius(d => d.radius + 8) // 碰撞半径 = 节点半径 + 间距
      .strength(0.9) // 碰撞力强度，确保不重叠
    )
    // 边界约束：将节点保持在画布范围内
    .force('boundary', () => {
      nodes.forEach(node => {
        // 计算边界，留出一些边距
        const margin = node.radius + 5
        if (node.x < margin) {
          node.x = margin
          node.vx = 0
        } else if (node.x > width.value - margin) {
          node.x = width.value - margin
          node.vx = 0
        }
        if (node.y < margin) {
          node.y = margin
          node.vy = 0
        } else if (node.y > height.value - margin) {
          node.y = height.value - margin
          node.vy = 0
        }
      })
    })
    // 设置模拟参数
    .alphaDecay(0.025) // 衰减率，值越小模拟运行越久
    .velocityDecay(0.5) // 速度衰减，模拟摩擦力，稍大于流派视图让节点更快稳定
    .alpha(1) // 初始能量，1表示完全激活
  
  // 监听模拟的 tick 事件，更新节点位置
  simulation.on('tick', () => {
    // 应用边界约束
    nodes.forEach(node => {
      const margin = node.radius + 5
      node.x = Math.max(margin, Math.min(width.value - margin, node.x))
      node.y = Math.max(margin, Math.min(height.value - margin, node.y))
    })
    // 触发响应式更新（Vue 3 需要手动触发）
    artistNodes.value = [...nodes]
  })
  
  // 模拟结束后，确保所有节点都在边界内
  simulation.on('end', () => {
    nodes.forEach(node => {
      const margin = node.radius + 5
      node.x = Math.max(margin, Math.min(width.value - margin, node.x))
      node.y = Math.max(margin, Math.min(height.value - margin, node.y))
    })
    artistNodes.value = [...nodes]
  })
  
  console.log('[ArtistView] 力导向图初始化完成，音乐人数量:', nodes.length)
}

// ==================== 方法 ====================
/**
 * 获取指标的中文标签
 */
function getMetricLabel(metric) {
  const labels = {
    'score': '综合评分',
    'total_works': '总作品数',
    'notable_rate': '成名率',
    'notable_works': '成名作品数',
    'time_span': '活跃时长',
    'influence_score': '影响力分数',
    'collaborators_count': '合作者数量',
    'record_labels_count': '唱片公司数量',
    'role_count': '角色多样性'
  }
  return labels[metric] || metric
}

/**
 * 格式化指标值用于显示
 */
function formatMetricValue(value, metric) {
  if (value === null || value === undefined) return '0'
  
  // 对于比率类指标，显示为百分比
  if (metric === 'notable_rate') {
    return (value * 100).toFixed(1) + '%'
  }
  
  // 对于数值类指标，根据大小决定小数位数
  if (typeof value === 'number') {
    if (value >= 100) {
      return value.toFixed(0)
    } else if (value >= 10) {
      return value.toFixed(1)
    } else {
      return value.toFixed(2)
    }
  }
  
  return String(value)
}

/**
 * 处理音乐人圆圈点击事件
 */
function handleArtistClick(artist) {
  const metricValue = artist[props.sortMetric] ?? 0
  console.log(`[ArtistView] 点击音乐人: ${artist.name}, ${getMetricLabel(props.sortMetric)}: ${metricValue}`)
  // 通知父组件切换至第三层单曲视图
  emit('view-tracks', artist)
}

/**
 * 处理返回按钮点击事件
 */
function handleGoBack() {
  emit('go-back')
}

/**
 * 处理分页切换
 */
function changePage(page) {
  if (page === props.currentPage) return
  emit('page-change', page)
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
    // 窗口大小变化时，重新初始化力导向图
    if (props.artists && props.artists.length > 0) {
      nextTick(() => {
        initForceSimulation()
      })
    }
  })
  
  // 数据加载后初始化力导向图
  if (props.artists && props.artists.length > 0) {
    nextTick(() => {
      initForceSimulation()
    })
  }
})

// 当数据变化时，重新初始化力导向图
watch(() => [props.artists, props.genre, props.currentPage, props.sortMetric], () => {
  if (props.artists && props.artists.length > 0) {
    nextTick(() => {
      console.log(`[ArtistView] 数据更新，重新初始化力导向图，音乐人数量: ${props.artists.length}, 排序指标: ${props.sortMetric}`)
      initForceSimulation()
    })
  } else {
    artistNodes.value = []
    if (simulation) {
      simulation.stop()
      simulation = null
    }
  }
}, { deep: true })

// 当画布尺寸变化时，重新初始化力导向图
watch([width, height], () => {
  if (props.artists && props.artists.length > 0 && artistNodes.value.length > 0) {
    nextTick(() => {
      initForceSimulation()
    })
  }
})

// 组件卸载时停止模拟
onBeforeUnmount(() => {
  if (simulation) {
    simulation.stop()
    simulation = null
  }
})
</script>

<style scoped>
.artist-view {
  flex: 1;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.header {
  padding: 3px;
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

.artist-node {
  transition: transform 0.1s ease-out;
}

.artist-circle {
  cursor: pointer;
  transition: stroke-width 0.3s ease, filter 0.3s ease;
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
  bottom: 70px;
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

.pagination {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.92);
  padding: 8px 16px;
  border-radius: 16px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  font-size: 14px;
}

.page-btn {
  padding: 6px 14px;
  border: none;
  border-radius: 12px;
  background: #667eea;
  color: #fff;
  cursor: pointer;
  transition: background 0.2s ease;
}

.page-btn:disabled {
  background: rgba(102, 126, 234, 0.4);
  cursor: not-allowed;
}

.page-btn:not(:disabled):hover {
  background: #4c51bf;
}

.page-info {
  color: #333;
}
</style>

