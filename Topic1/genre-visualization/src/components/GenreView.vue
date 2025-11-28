<template>
  <div class="genre-view">
    <!-- 标题栏 -->
    <header class="header">
      <h1>音乐流派可视化</h1>
      <p class="subtitle">点击流派圆圈查看该流派下的音乐人</p>
    </header>
    
    <!-- SVG 画布容器 -->
    <div class="canvas-container" ref="containerRef">
      <svg :width="width" :height="height" ref="svgRef">
        <!-- 定义渐变和滤镜（用于视觉效果） -->
        <defs>
          <!-- 为每个流派创建不同的颜色渐变 -->
          <!-- 注意：使用流派名称作为ID的一部分，确保唯一性 -->
          <radialGradient
            v-for="genre in genres"
            :key="`gradient-${genre}`"
            :id="`gradient-${genre.replace(/\s+/g, '-').replace(/\//g, '-')}`"
            cx="30%" cy="30%"
          >
            <stop offset="0%" :stop-color="getGenreColor(genre)" stop-opacity="1" />
            <stop offset="100%" :stop-color="getGenreColor(genre)" stop-opacity="0.7" />
          </radialGradient>
        </defs>
        
        <!-- 流派圆圈组 -->
        <g class="genres-group">
          <g
            v-for="node in genreNodes"
            :key="node.genre"
            class="genre-node"
            :transform="`translate(${node.x},${node.y})`"
          >
            <circle
              :r="node.radius"
              :fill="`url(#gradient-${node.genre.replace(/\s+/g, '-').replace(/\//g, '-')})`"
              :stroke="getGenreColor(node.genre)"
              :stroke-width="2"
              class="genre-circle"
              :class="{ 'hovered': hoveredGenre === node.genre }"
              @click="handleGenreClick(node.genre)"
              @mouseenter="hoveredGenre = node.genre"
              @mouseleave="hoveredGenre = null"
            />
            
            <!-- 流派标签 -->
            <text
              :y="0"
              :fill="getTextColor(node.genre)"
              text-anchor="middle"
              dominant-baseline="middle"
              class="genre-label"
              :font-size="getLabelFontSize(node.radius)"
            >
              {{ node.genre }}
            </text>
            
            <!-- 音乐人数量标签 -->
            <text
              :y="getLabelFontSize(node.radius) + 8"
              :fill="getTextColor(node.genre)"
              text-anchor="middle"
              dominant-baseline="middle"
              class="genre-count"
              :font-size="12"
            >
              {{ node.count }}人
            </text>
          </g>
        </g>
      </svg>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as d3 from 'd3'

// ==================== Props ====================
const props = defineProps({
  genresData: {
    type: Object,
    required: true
  },
  genreColorMap: {
    type: Object,
    required: false,
    default: () => ({})
  }
})

// ==================== Emits ====================
const emit = defineEmits(['select-genre'])

// ==================== 响应式数据 ====================
const containerRef = ref(null)
const svgRef = ref(null)
const width = ref(1200)
const height = ref(800)
const hoveredGenre = ref(null)
// 力导向图模拟器
let simulation = null
// 节点数据（响应式，用于动画）
const genreNodes = ref([])

// ==================== 计算属性 ====================
/**
 * 获取所有流派列表
 */
const genres = computed(() => {
  return props.genresData?.genres || []
})

/**
 * 计算每个流派的音乐人数量
 * 判断标准：genre_share 中该流派占比超过 50%
 */
const genreCounts = computed(() => {
  if (!props.genresData?.genres_data) return {}
  
  const counts = {}
  genres.value.forEach(genre => {
    const genreData = props.genresData.genres_data[genre]
    // count 字段已经包含了符合条件（genre_share > 50%）的音乐人数量
    counts[genre] = genreData?.count || 0
  })
  return counts
})

/**
 * 初始化力导向图
 * 创建动态的力导向图模拟，让圆圈有引力和斥力效果
 */
function initForceSimulation() {
  if (!props.genresData) return
  
  // 停止之前的模拟（如果存在）
  if (simulation) {
    simulation.stop()
  }
  
  // 准备节点数据
  const nodes = genres.value.map(genre => ({
    genre,
    count: genreCounts.value[genre] || 0
  }))
  
  // 计算半径（基于音乐人数量）
  const counts = nodes.map(n => n.count)
  const minCount = Math.min(...counts.filter(c => c > 0))
  const maxCount = Math.max(...counts)
  
  // 半径范围：最小20px，最大120px
  const minRadius = 20
  const maxRadius = 120
  const radiusScale = d3.scaleSqrt()
    .domain([minCount, maxCount])
    .range([minRadius, maxRadius])
  
  // 为每个节点设置半径和初始位置
  nodes.forEach((node, i) => {
    node.radius = node.count > 0 ? radiusScale(node.count) : minRadius
    // 初始位置：围绕中心均匀分布
    const angle = (i / nodes.length) * 2 * Math.PI
    node.x = width.value / 2 + Math.cos(angle) * 150
    node.y = height.value / 2 + Math.sin(angle) * 150
    node.vx = 0
    node.vy = 0
  })
  
  // 更新响应式节点数据
  genreNodes.value = nodes
  
  // 创建力导向图模拟器
  simulation = d3.forceSimulation(nodes)
    // 排斥力：节点之间相互排斥，避免重叠
    // strength 为负值表示排斥，绝对值越大排斥力越强
    .force('charge', d3.forceManyBody()
      .strength(d => {
        // 根据节点大小调整排斥力，大节点排斥力更强
        return -d.radius * 2
      })
      .distanceMax(400) // 最大作用距离
    )
    // 中心力：将节点拉向画布中心，保持整体布局
    .force('center', d3.forceCenter(width.value / 2, height.value / 2)
      .strength(0.05) // 中心力强度，较小值让节点更自由
    )
    // 碰撞检测：确保节点之间保持最小距离，不会重叠
    .force('collision', d3.forceCollide()
      .radius(d => d.radius + 15) // 碰撞半径 = 节点半径 + 间距
      .strength(0.8) // 碰撞力强度
    )
    // 边界约束：将节点保持在画布范围内
    .force('boundary', () => {
      nodes.forEach(node => {
        // 计算边界，留出一些边距
        const margin = node.radius + 10
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
    .alphaDecay(0.02) // 衰减率，值越小模拟运行越久
    .velocityDecay(0.4) // 速度衰减，模拟摩擦力
    .alpha(1) // 初始能量，1表示完全激活
  
  // 监听模拟的 tick 事件，更新节点位置
  simulation.on('tick', () => {
    // 应用边界约束
    nodes.forEach(node => {
      const margin = node.radius + 10
      node.x = Math.max(margin, Math.min(width.value - margin, node.x))
      node.y = Math.max(margin, Math.min(height.value - margin, node.y))
    })
    // 触发响应式更新（Vue 3 需要手动触发）
    genreNodes.value = [...nodes]
  })
  
  // 模拟结束后，确保所有节点都在边界内
  simulation.on('end', () => {
    nodes.forEach(node => {
      const margin = node.radius + 10
      node.x = Math.max(margin, Math.min(width.value - margin, node.x))
      node.y = Math.max(margin, Math.min(height.value - margin, node.y))
    })
    genreNodes.value = [...nodes]
  })
  
  console.log('[GenreView] 力导向图初始化完成，节点数量:', nodes.length)
}

// ==================== 方法 ====================
/**
 * 获取流派的颜色
 * 优先使用传入的genreColorMap，如果没有则使用内部颜色数组
 */
function getGenreColor(genre) {
  // 如果提供了genreColorMap且包含该流派，使用它
  if (props.genreColorMap && Object.keys(props.genreColorMap).length > 0 && props.genreColorMap[genre]) {
    return props.genreColorMap[genre]
  }
  
  // 否则使用内部颜色数组
  const index = getGenreIndex(genre)
  const colors = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
    '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5',
    '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7',
    '#dda15e'
  ]
  return colors[index % colors.length]
}

/**
 * 获取流派在列表中的索引
 */
function getGenreIndex(genre) {
  return genres.value.indexOf(genre)
}

/**
 * 获取文本颜色（根据背景色自动调整，确保可读性）
 */
function getTextColor(genre) {
  // 对于浅色背景使用深色文字，深色背景使用浅色文字
  // 这里简化处理，统一使用深色文字
  return '#333'
}

/**
 * 根据圆圈半径计算标签字体大小
 */
function getLabelFontSize(radius) {
  // 字体大小与半径成比例，但限制在合理范围内
  return Math.max(10, Math.min(16, radius * 0.15))
}

/**
 * 处理流派圆圈点击事件
 */
function handleGenreClick(genre) {
  const count = genreCounts.value[genre]
  if (count === 0) {
    console.warn(`[GenreView] 流派 ${genre} 没有音乐人`)
    return
  }
  console.log(`[GenreView] 点击流派: ${genre}, 音乐人数量: ${count}`)
  emit('select-genre', genre)
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
    if (props.genresData) {
      nextTick(() => {
        initForceSimulation()
      })
    }
  })
  
  // 数据加载后初始化力导向图
  if (props.genresData) {
    nextTick(() => {
      initForceSimulation()
    })
  }
})

// 当数据变化时，重新初始化力导向图
watch(() => props.genresData, () => {
  if (props.genresData) {
    nextTick(() => {
      console.log('[GenreView] 数据更新，重新初始化力导向图')
      initForceSimulation()
    })
  }
}, { deep: true })

// 当画布尺寸变化时，重新初始化力导向图
watch([width, height], () => {
  if (props.genresData && genreNodes.value.length > 0) {
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
.genre-view {
  flex: 1;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.header {
  padding: 20px;
  text-align: center;
  color: white;
  background: rgba(0, 0, 0, 0.2);
}

.header h1 {
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

.genre-node {
  transition: transform 0.1s ease-out;
}

.genre-circle {
  cursor: pointer;
  transition: stroke-width 0.3s ease, filter 0.3s ease;
}

.genre-circle:hover {
  stroke-width: 4;
  filter: brightness(1.2);
  transform-origin: center;
}

.genre-circle.hovered {
  stroke-width: 4;
  filter: brightness(1.2);
}

.genre-label {
  pointer-events: none;
  font-weight: 600;
  text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
}

.genre-count {
  pointer-events: none;
  font-weight: 400;
  opacity: 0.8;
  text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
}
</style>

