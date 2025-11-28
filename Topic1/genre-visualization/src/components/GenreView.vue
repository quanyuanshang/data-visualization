
<template>
  <div class="genre-view">
    <!-- 标题栏 -->
    <header class="header">
      <h1>音乐流派可视化</h1>
      <p class="subtitle">点击唱片圆圈或使用左侧筛选框进行探索</p>
    </header>
    
    <!-- SVG 画布容器 -->
    <div class="canvas-container" ref="containerRef">
      <svg :width="width" :height="height" ref="svgRef">
        <!-- 定义滤镜 -->
        <defs>
          <filter id="vinyl-shine" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2" result="blur"/>
            <feSpecularLighting in="blur" surfaceScale="2" specularConstant="1" specularExponent="20" lighting-color="#ffffff" result="specular">
              <fePointLight x="0" y="-1000" z="500" />
            </feSpecularLighting>
            <feComposite in="specular" in2="SourceAlpha" operator="in" result="specular"/>
            <feComposite in="SourceGraphic" in2="specular" operator="arithmetic" k1="0" k2="1" k3="1" k4="0"/>
          </filter>
        </defs>
        
        <!-- 流派圆圈组 -->
        <g class="genres-group">
          <g
            v-for="node in genreNodes"
            :key="node.genre"
            class="genre-node"
            :transform="`translate(${node.x},${node.y})`"
            :style="{ opacity: getOpacity(node.genre) }"
          >
            <!-- 唱片盘体 -->
            <circle
              :r="node.radius"
              fill="#1a1a1a"
              stroke="#000"
              stroke-width="1"
              class="vinyl-disc"
              :class="{ 'hovered': hoveredGenre === node.genre, 'selected': isSelected(node.genre) }"
              @click="handleGenreClick(node.genre)"
              @mouseenter="hoveredGenre = node.genre"
              @mouseleave="hoveredGenre = null"
            />
            
            <!-- 唱片纹理 (同心圆) -->
            <circle :r="node.radius * 0.9" fill="none" stroke="#2a2a2a" stroke-width="1.5" class="pointer-events-none" />
            <circle :r="node.radius * 0.8" fill="none" stroke="#2a2a2a" stroke-width="1.5" class="pointer-events-none" />
            <circle :r="node.radius * 0.7" fill="none" stroke="#2a2a2a" stroke-width="1.5" class="pointer-events-none" />
            <circle :r="node.radius * 0.6" fill="none" stroke="#2a2a2a" stroke-width="1.5" class="pointer-events-none" />
            
            <!-- 唱片中心标签 (Label) -->
            <circle
              :r="node.radius * 0.4"
              :fill="getGenreColor(node.genre)"
              class="vinyl-label pointer-events-none"
            />
            
            <!-- 唱片中心孔 -->
            <circle :r="node.radius * 0.05" fill="#111" class="pointer-events-none" />

            <!-- 流派标签 -->
            <text
              :y="node.radius * 0.55 + 14"
              fill="#fff"
              text-anchor="middle"
              dominant-baseline="middle"
              class="genre-label"
              :font-size="getLabelFontSize(node.radius)"
              style="text-shadow: 0 2px 4px rgba(0,0,0,0.8);"
            >
              {{ node.genre }}
            </text>
            
            <!-- 音乐人数量标签 -->
            <text
              :y="node.radius * 0.55 + getLabelFontSize(node.radius) + 16"
              fill="#ccc"
              text-anchor="middle"
              dominant-baseline="middle"
              class="genre-count"
              font-size="10"
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
  },
  selectedGenres: {
    type: Array,
    default: () => []
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
const genres = computed(() => {
  return props.genresData?.genres || []
})

const genreCounts = computed(() => {
  if (!props.genresData?.genres_data) return {}
  const counts = {}
  genres.value.forEach(genre => {
    const genreData = props.genresData.genres_data[genre]
    counts[genre] = genreData?.count || 0
  })
  return counts
})

// ==================== 核心方法 ====================

/**
 * 判断流派是否被选中
 */
function isSelected(genre) {
  if (!props.selectedGenres || props.selectedGenres.length === 0) return false
  return props.selectedGenres.includes(genre)
}

/**
 * 获取透明度：如果处于筛选模式，未选中的变淡
 */
function getOpacity(genre) {
  if (!props.selectedGenres || props.selectedGenres.length === 0) return 1
  if (props.selectedGenres.includes(genre)) return 1
  return 0.2 // 未选中变淡
}

function getGenreColor(genre) {
  if (props.genreColorMap && Object.keys(props.genreColorMap).length > 0 && props.genreColorMap[genre]) {
    return props.genreColorMap[genre]
  }
  return '#888'
}

function getLabelFontSize(radius) {
  return Math.max(10, Math.min(16, radius * 0.15))
}

function handleGenreClick(genre) {
  const count = genreCounts.value[genre]
  if (count === 0) return
  emit('select-genre', genre)
}

function initForceSimulation() {
  if (!props.genresData) return
  if (simulation) simulation.stop()
  
  const nodes = genres.value.map(genre => ({
    genre,
    count: genreCounts.value[genre] || 0
  }))
  
  const counts = nodes.map(n => n.count)
  const minCount = Math.min(...counts.filter(c => c > 0)) || 1
  const maxCount = Math.max(...counts) || 100
  
  const radiusScale = d3.scaleSqrt()
    .domain([minCount, maxCount])
    .range([30, 140])
  
  nodes.forEach((node, i) => {
    node.radius = node.count > 0 ? radiusScale(node.count) : 30
    const angle = (i / nodes.length) * 2 * Math.PI
    node.x = width.value / 2 + Math.cos(angle) * 150
    node.y = height.value / 2 + Math.sin(angle) * 150
    node.vx = 0
    node.vy = 0
  })
  
  genreNodes.value = nodes
  
  simulation = d3.forceSimulation(nodes)
    .force('charge', d3.forceManyBody().strength(d => -d.radius * 1.8).distanceMax(500))
    .force('center', d3.forceCenter(width.value / 2, height.value / 2).strength(0.05))
    // 增加碰撞半径，防止遮挡：radius + 20
    .force('collision', d3.forceCollide().radius(d => d.radius + 20).strength(0.9))
    .force('boundary', () => {
      nodes.forEach(node => {
        const margin = node.radius + 10
        node.x = Math.max(margin, Math.min(width.value - margin, node.x))
        node.y = Math.max(margin, Math.min(height.value - margin, node.y))
      })
    })
    .alphaDecay(0.02)
    .velocityDecay(0.4)
    
  simulation.on('tick', () => {
    nodes.forEach(node => {
        const margin = node.radius + 10
        node.x = Math.max(margin, Math.min(width.value - margin, node.x))
        node.y = Math.max(margin, Math.min(height.value - margin, node.y))
    })
    genreNodes.value = [...nodes]
  })
}

function initCanvasSize() {
  if (containerRef.value) {
    width.value = containerRef.value.clientWidth || 1200
    height.value = containerRef.value.clientHeight || 800
  }
}

onMounted(() => {
  initCanvasSize()
  window.addEventListener('resize', () => {
    initCanvasSize()
    nextTick(initForceSimulation)
  })
  nextTick(initForceSimulation)
})

watch(() => props.genresData, () => {
  nextTick(initForceSimulation)
}, { deep: true })

watch([width, height], () => {
  if (genreNodes.value.length > 0) nextTick(initForceSimulation)
})

onBeforeUnmount(() => {
  if (simulation) simulation.stop()
})
</script>

<style scoped>
.genre-view {
  flex: 1;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  /* 统一为暗色背景，不再使用渐变色，保持风格一致 */
  background: #1a1a1a;
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
  transition: opacity 0.3s ease, transform 0.1s ease-out;
}

.vinyl-disc {
  cursor: pointer;
  transition: stroke-width 0.3s ease, filter 0.3s ease;
}

.vinyl-disc:hover {
  stroke: #fff;
  stroke-width: 2;
  filter: drop-shadow(0 0 8px rgba(255,255,255,0.4));
}

.vinyl-disc.selected {
  stroke: #fff !important;
  stroke-width: 3;
  filter: drop-shadow(0 0 15px rgba(255,255,255,0.6));
}

.pointer-events-none {
  pointer-events: none;
}

.genre-label {
  pointer-events: none;
  font-weight: 600;
}

.genre-count {
  pointer-events: none;
  font-weight: 400;
  opacity: 0.9;
}
</style>