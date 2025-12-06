
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
          共 {{ props.totalArtists }} 位{{ isSuperstarView ? '超新星候选人' : '音乐人' }}
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
          <radialGradient id="superstar-gradient" cx="30%" cy="30%">
            <stop offset="0%" stop-color="#ffd700" stop-opacity="1" />
            <stop offset="100%" stop-color="#b8860b" stop-opacity="0.8" />
          </radialGradient>
        </defs>
        
        <!-- 中心流派圆圈（黑胶唱片样式）和音波环绕 -->
        <g class="center-group">
          <!-- 音波环绕 (Soundwave Bars) -->
          <g class="soundwave-ring" v-if="soundWaveBars.length > 0">
            <g v-for="(bar, index) in soundWaveBars" :key="index"
               :transform="`translate(${centerX}, ${centerY}) rotate(${bar.angleDeg})`">
              <line
                :x1="ringInnerRadius"
                y1="0"
                :x2="ringInnerRadius + bar.len"
                y2="0"
                :stroke="bar.color"
                stroke-width="4"
                stroke-linecap="round"
                :opacity="hoveredSoundWaveBar === index ? 1 : 0.6"
                class="soundwave-bar"
                @mouseenter="(e) => handleSoundWaveHover(e, index)"
                @mouseleave="hoveredSoundWaveBar = null"
              >
                <!-- 增加轻微的音波跳动动画 -->
                <animate attributeName="x2" 
                  :values="`${ringInnerRadius + bar.len};${ringInnerRadius + bar.len * 1.1};${ringInnerRadius + bar.len}`" 
                  dur="0.5s" 
                  :begin="`${index * 0.05}s`"
                  repeatCount="indefinite" />
              </line>
            </g>
          </g>
          
          <!-- 中心唱片盘体 -->
          <circle
            :cx="centerX"
            :cy="centerY"
            :r="centerRadius"
            fill="#1a1a1a"
            stroke="#000"
            stroke-width="1"
            class="center-vinyl-disc"
          />
          
          <!-- 唱片纹理 (同心圆) -->
          <circle :cx="centerX" :cy="centerY" :r="centerRadius * 0.9" fill="none" stroke="#2a2a2a" stroke-width="2" class="pointer-events-none" />
          <circle :cx="centerX" :cy="centerY" :r="centerRadius * 0.8" fill="none" stroke="#2a2a2a" stroke-width="2" class="pointer-events-none" />
          <circle :cx="centerX" :cy="centerY" :r="centerRadius * 0.7" fill="none" stroke="#2a2a2a" stroke-width="2" class="pointer-events-none" />
          <circle :cx="centerX" :cy="centerY" :r="centerRadius * 0.6" fill="none" stroke="#2a2a2a" stroke-width="2" class="pointer-events-none" />
          
          <!-- 唱片中心标签 (Label) -->
          <circle
            :cx="centerX"
            :cy="centerY"
            :r="centerRadius * 0.4"
            :fill="genreColor"
            class="center-vinyl-label"
          />
          
          <!-- 唱片中心孔 -->
          <circle :cx="centerX" :cy="centerY" :r="centerRadius * 0.05" fill="#111" class="pointer-events-none" />

          <!-- 流派名称标签 (位于唱片下方) -->
          <text
            :x="centerX"
            :y="centerY + centerRadius * 0.4 + 25"
            fill="#fff"
            text-anchor="middle"
            dominant-baseline="middle"
            class="center-genre-label"
            font-size="16"
            font-weight="600"
            style="text-shadow: 0 2px 4px rgba(0,0,0,0.8);"
          >
            {{ genre }}
          </text>
        </g>
        
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
              :fill="node.isSuperstar ? 'url(#superstar-gradient)' : 'url(#artist-gradient)'"
              :stroke="node.isSuperstar ? '#fff' : genreColor"
              :stroke-width="node.isSuperstar ? 2 : 1.5"
              class="artist-circle"
              :class="{ 'hovered': hoveredArtist === node.artist.person_id }"
              @click="handleArtistClick(node.artist)"
              @mouseenter="handleArtistHover($event, node)"
              @mouseleave="handleArtistLeave"
            />
          </g>
        </g>
      </svg>
      
      <!-- 音乐人名称标签/Tooltip（悬停显示，位置跟随） -->
      <div
        v-if="hoveredNode"
        class="artist-tooltip"
        :style="{ left: tooltipPos.x + 'px', top: tooltipPos.y + 'px' }"
      >
        <div class="tooltip-header">
           <strong class="tooltip-name">{{ hoveredNode.artist.name }}</strong>
           <span class="tooltip-score" v-if="!isSuperstarView">{{ getMetricLabel(props.sortMetric) }}: {{ formatMetricValue(hoveredNode.artist[props.sortMetric], props.sortMetric) }}</span>
           <span class="tooltip-score" v-else>预测潜力: {{ formatMetricValue(hoveredNode.artist.score, 'score') }}</span>
        </div>

        <!-- 超新星模式：SHAP 因子图表 -->
        <div v-if="isSuperstarView && hoveredNode.artist.shap_explanation" class="shap-chart">
          <div class="shap-title">✨ 核心潜力因素 (Top 5)</div>
          <div class="shap-bar-container" v-for="(factor, idx) in getTopPositiveFactors(hoveredNode.artist.shap_explanation)" :key="idx">
             <div class="shap-label">{{ getFeatureLabel(factor.feature) }}</div>
             <div class="shap-bar-bg">
                <div class="shap-bar-fill" :style="{ width: (factor.impact * 100) + '%' }"></div>
             </div>
          </div>
        </div>
      </div>
      
      <!-- 图例 -->
      <div class="legend">
        <div class="legend-item">
          <div class="legend-circle" :style="{ background: isSuperstarView ? '#ffd700' : genreColor }"></div>
          <span>圆圈大小 = {{ isSuperstarView ? 'AI预测潜力值' : getMetricLabel(props.sortMetric) }}</span>
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
    
    <!-- 音波工具提示 -->
    <div
      v-if="hoveredSoundWaveBar !== null && soundWaveBars[hoveredSoundWaveBar]"
      class="sankey-tooltip"
      :style="{ left: sankeyTooltipX + 'px', top: sankeyTooltipY + 'px' }"
    >
      <div class="tooltip-content">
        <strong>{{ genre }}</strong>
        <div>年份: {{ soundWaveBars[hoveredSoundWaveBar].year }}</div>
        <div>作品数: {{ soundWaveBars[hoveredSoundWaveBar].count }}</div>
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
  },
  timelineData: {
    type: Object,
    default: null
  },
  genreColorMap: {
    type: Object,
    default: () => ({})
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
const hoveredNode = ref(null) // 存储当前悬停的节点对象，用于Tooltip
const tooltipPos = ref({ x: 0, y: 0 })

const hoveredSoundWaveBar = ref(null)
const sankeyTooltipX = ref(0)
const sankeyTooltipY = ref(0)
// 力导向图模拟器
let simulation = null
// 节点数据（响应式，用于动画）
const artistNodes = ref([])

// 中心圆圈参数
const centerX = computed(() => width.value / 2)
const centerY = computed(() => height.value / 2)
const centerRadius = computed(() => Math.min(width.value, height.value) * 0.15) // 增大一点中心半径以展示唱片细节
const ringInnerRadius = computed(() => centerRadius.value + 15) // 音波起始半径
const maxWaveLength = computed(() => 120) // 音波最大长度

// 判断是否为超新星视图
const isSuperstarView = computed(() => {
  return props.artists.length > 0 && props.artists[0].isSuperstar
})

// ==================== 计算属性 ====================
/**
 * 获取流派的颜色（与 GenreView 中的颜色保持一致）
 */
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
  if (props.genreColorMap && props.genreColorMap[props.genre]) {
    return props.genreColorMap[props.genre]
  }
  const available = Array.isArray(props.allGenres) && props.allGenres.length
    ? props.allGenres
    : []
  const index = available.indexOf(props.genre)
  if (index >= 0) {
    return palette[index % palette.length]
  }
  return palette[hashToColorIndex(props.genre)]
})

// 计算音波（Soundwave）数据：每个年份对应一根 Bar
const soundWaveBars = computed(() => {
  if (!props.timelineData || !props.genre) return []
  
  const genreTimeline = props.timelineData.genre_timelines?.[props.genre]
  if (!genreTimeline || !genreTimeline.yearly_counts) return []
  
  const allYears = props.timelineData.time_range?.all_years || []
  if (allYears.length === 0) return []
  
  // 获取每年的作品数量
  const yearCounts = allYears.map(year => {
    return {
      year,
      count: genreTimeline.yearly_counts[String(year)] || 0
    }
  })
  
  // 计算最大值用于归一化
  const maxCount = Math.max(...yearCounts.map(y => y.count), 1)
  
  const bars = []
  const totalYears = yearCounts.length
  const anglePerYear = 360 / totalYears
  
  yearCounts.forEach((item, index) => {
    const angleDeg = index * anglePerYear
    
    // 归一化长度
    const normalizedCount = item.count / maxCount
    // 基础长度 + 动态长度
    const len = 5 + normalizedCount * maxWaveLength.value
    
    bars.push({
      year: item.year,
      count: item.count,
      angleDeg, // 旋转角度
      len,      // 柱子长度
      color: genreColor.value
    })
  })
  
  return bars
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
  
  if (simulation) {
    simulation.stop()
  }
  
  const metricKey = isSuperstarView.value ? 'score' : (props.sortMetric || 'score')
  const nodes = props.artists.map(artist => {
    const metricValue = artist[metricKey] ?? 0
    return {
      artist,
      score: artist.score || 0,
      metricValue,
      isSuperstar: artist.isSuperstar // Pass through flag
    }
  })
  
  const metricValues = nodes.map(n => n.metricValue)
  const minValue = Math.min(...metricValues)
  const maxValue = Math.max(...metricValues)
  
  const minRadius = 8
  const maxRadius = 40
  
  let radiusScale
  if (minValue === maxValue) {
    radiusScale = () => (minRadius + maxRadius) / 2
  } else {
    radiusScale = d3.scaleLinear()
      .domain([minValue, maxValue])
      .range([minRadius, maxRadius])
  }
  
  nodes.forEach((node, i) => {
    node.radius = radiusScale(node.metricValue)
    // 初始位置：围绕中心圆圈均匀分布，距离中心稍远一点
    const angle = (i / nodes.length) * 2 * Math.PI
    const initialRadius = centerRadius.value + maxWaveLength.value + 80 
    node.x = centerX.value + Math.cos(angle) * initialRadius
    node.y = centerY.value + Math.sin(angle) * initialRadius
    node.vx = 0
    node.vy = 0
  })
  
  artistNodes.value = nodes
  
  simulation = d3.forceSimulation(nodes)
    .force('charge', d3.forceManyBody()
      .strength(d => -d.radius * 1.5)
      .distanceMax(300)
    )
    .force('radial', d3.forceRadial()
      .radius(d => centerRadius.value + maxWaveLength.value + 100) 
      .x(centerX.value)
      .y(centerY.value)
      .strength(0.1) 
    )
    .force('collision', d3.forceCollide()
      .radius(d => d.radius + 8) 
      .strength(0.9)
    )
    .force('boundary', () => {
      nodes.forEach(node => {
        const dx = node.x - centerX.value
        const dy = node.y - centerY.value
        const distance = Math.sqrt(dx * dx + dy * dy)
        // 最小距离包含音波长度
        const minDistance = centerRadius.value + maxWaveLength.value + node.radius + 20 
        
        if (distance < minDistance) {
          const angle = Math.atan2(dy, dx)
          node.x = centerX.value + Math.cos(angle) * minDistance
          node.y = centerY.value + Math.sin(angle) * minDistance
          node.vx = 0
          node.vy = 0
        }
        
        const margin = node.radius + 5
        if (node.x < margin) node.x = margin
        else if (node.x > width.value - margin) node.x = width.value - margin
        if (node.y < margin) node.y = margin
        else if (node.y > height.value - margin) node.y = height.value - margin
      })
    })
    .alphaDecay(0.025)
    .velocityDecay(0.5) 
    .alpha(1)
  
  simulation.on('tick', () => {
    nodes.forEach(node => {
      const dx = node.x - centerX.value
      const dy = node.y - centerY.value
      const distance = Math.sqrt(dx * dx + dy * dy)
      const minDistance = centerRadius.value + maxWaveLength.value + node.radius + 20
      
      if (distance < minDistance) {
        const angle = Math.atan2(dy, dx)
        node.x = centerX.value + Math.cos(angle) * minDistance
        node.y = centerY.value + Math.sin(angle) * minDistance
        node.vx = 0
        node.vy = 0
      }
      
      const margin = node.radius + 5
      node.x = Math.max(margin, Math.min(width.value - margin, node.x))
      node.y = Math.max(margin, Math.min(height.value - margin, node.y))
    })
    artistNodes.value = [...nodes]
  })
}

// ==================== 方法 ====================
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

function formatMetricValue(value, metric) {
  if (value === null || value === undefined) return '0'
  if (metric === 'notable_rate') return (value * 100).toFixed(1) + '%'
  if (typeof value === 'number') {
    if (value >= 100) return value.toFixed(0)
    else if (value >= 10) return value.toFixed(1)
    else return value.toFixed(2)
  }
  return String(value)
}

function handleArtistClick(artist) {
  emit('view-tracks', artist)
}

function handleArtistHover(event, node) {
  hoveredArtist.value = node.artist.person_id
  hoveredNode.value = node
  tooltipPos.value = { x: event.clientX + 15, y: event.clientY - 15 }
}

function handleArtistLeave() {
  hoveredArtist.value = null
  hoveredNode.value = null
}

function getTopPositiveFactors(shapExplanation) {
  if (!shapExplanation || !shapExplanation.factors) return []
  // Filter positive impacts and sort descending
  return shapExplanation.factors
    .filter(f => f.impact > 0)
    .sort((a, b) => b.impact - a.impact)
    .slice(0, 5)
}

function getFeatureLabel(featureKey) {
   const map = {
     'total_works': '作品总量',
     'pagerank': '核心程度 (PageRank)',
     'hub_score': '枢纽指数',
     'authority_score': '权威指数',
     'leverage_ratio': '杠杆率',
     'notable_works': '成名作数量',
     'time_span': '生涯跨度'
   }
   return map[featureKey] || featureKey
}

function handleGoBack() {
  emit('go-back')
}

function changePage(page) {
  if (page === props.currentPage) return
  emit('page-change', page)
}

function handleSoundWaveHover(event, index) {
  hoveredSoundWaveBar.value = index
  sankeyTooltipX.value = event.clientX + 10
  sankeyTooltipY.value = event.clientY - 10
}

function initCanvasSize() {
  if (containerRef.value) {
    width.value = containerRef.value.clientWidth || 1200
    height.value = containerRef.value.clientHeight || 800
  }
}

// ==================== 生命周期 ====================
onMounted(() => {
  initCanvasSize()
  window.addEventListener('resize', () => {
    initCanvasSize()
    if (props.artists && props.artists.length > 0) {
      nextTick(() => initForceSimulation())
    }
  })
  if (props.artists && props.artists.length > 0) {
    nextTick(() => initForceSimulation())
  }
})

watch(() => [props.artists, props.genre, props.currentPage, props.sortMetric], () => {
  if (props.artists && props.artists.length > 0) {
    nextTick(() => initForceSimulation())
  } else {
    artistNodes.value = []
    if (simulation) {
      simulation.stop()
      simulation = null
    }
  }
}, { deep: true })

watch([width, height], () => {
  if (props.artists && props.artists.length > 0 && artistNodes.value.length > 0) {
    nextTick(() => initForceSimulation())
  }
})

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
  /* 统一暗色背景，与主视图一致 */
  background: #1a1a1a;
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

.artist-tooltip {
  position: fixed; /* Ensure it's on top of everything */
  z-index: 2000;
  background: rgba(20, 20, 20, 0.95);
  border: 1px solid #444;
  border-radius: 8px;
  padding: 12px 16px;
  color: white;
  pointer-events: none;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  min-width: 200px;
}

.tooltip-header {
  margin-bottom: 8px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  padding-bottom: 6px;
}

.tooltip-name {
  display: block;
  font-size: 14px;
  margin-bottom: 2px;
}

.tooltip-score {
  font-size: 12px;
  color: #aaa;
}

/* SHAP Chart Styles */
.shap-chart {
  margin-top: 8px;
}

.shap-title {
  font-size: 11px;
  font-weight: bold;
  color: #ffd700;
  margin-bottom: 6px;
}

.shap-bar-container {
  margin-bottom: 4px;
}

.shap-label {
  font-size: 10px;
  color: #ccc;
  margin-bottom: 2px;
}

.shap-bar-bg {
  width: 100%;
  height: 6px;
  background: rgba(255,255,255,0.1);
  border-radius: 3px;
  overflow: hidden;
}

.shap-bar-fill {
  height: 100%;
  background: #667eea; /* Default blueish */
  border-radius: 3px;
}

/* Use yellow/gold for superstar positive factors */
.artist-view:has(.shap-chart) .shap-bar-fill {
  background: #ffd700;
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

/* 中心圆圈样式 */
.center-group {
  pointer-events: none;
}

.center-vinyl-disc {
  pointer-events: none;
  filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.5));
}

.center-vinyl-label {
  pointer-events: none;
}

.center-genre-label {
  pointer-events: none;
  text-shadow: 0 2px 4px rgba(0,0,0,0.5);
}

.pointer-events-none {
  pointer-events: none;
}

/* 音波样式 */
.soundwave-ring {
  pointer-events: all;
}

.soundwave-bar {
  cursor: pointer;
  transition: stroke-width 0.2s ease, opacity 0.2s ease;
  pointer-events: all;
}

.soundwave-bar:hover {
  opacity: 1 !important;
  stroke-width: 6;
  filter: brightness(1.5);
}

/* 工具提示 */
.sankey-tooltip {
  position: fixed;
  pointer-events: none;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.9);
  border: 1px solid #444;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
}

.sankey-tooltip .tooltip-content strong {
  display: block;
  margin-bottom: 4px;
  color: #fff;
  font-weight: 600;
}

.sankey-tooltip .tooltip-content div {
  margin-top: 2px;
  color: #ccc;
}
</style>