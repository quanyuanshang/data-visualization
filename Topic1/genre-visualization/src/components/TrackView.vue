
<template>
  <div class="track-view">
    <header class="header">
      <button class="back-button" @click="emit('go-back')">
        ← 返回音乐人列表
      </button>
      <div class="title-block">
        <h1>{{ displayName }}</h1>
        <p class="subtitle">
          自有单曲 {{ ownTrackCount }} 首
          <span v-if="externalTrackCount > 0">｜关联外部曲目 {{ externalTrackCount }} 首</span>
        </p>
      </div>
      <div class="metrics">
        <div class="metric">
          <span class="metric-label">最大影响力</span>
          <span class="metric-value">{{ maxInfluenceValue }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">连线数量</span>
          <span class="metric-value">{{ linkCount }}</span>
        </div>
      </div>
    </header>

    <div class="canvas" ref="containerRef">
      <svg :width="width" :height="height" ref="svgRef">
        <g class="links">
          <line
            v-for="(link, index) in renderedLinks"
            :key="`link-${index}`"
            :x1="link.source.x"
            :y1="link.source.y"
            :x2="link.target.x"
            :y2="link.target.y"
            :stroke="linkColor(link.type)"
            stroke-width="2"
            stroke-linecap="round"
            stroke-opacity="0.65"
          />
        </g>

        <g class="nodes">
          <g
            v-for="node in renderedNodes"
            :key="node.id"
            class="node"
            :transform="`translate(${node.x},${node.y})`"
            @mouseenter="handleNodeEnter($event, node)"
            @mouseleave="handleNodeLeave"
          >
            <!-- 唱片/圆形节点 -->
            <circle
              v-if="node.own"
              class="track-circle"
              :r="node.radius"
              :fill="nodeFill(node)"
              :stroke="node.notable ? '#000000' : nodeStroke(node)"
              :stroke-width="node.notable ? 3 : 1.5"
              :stroke-dasharray="hasCollaborators(node) ? '4,3' : 'none'"
            />
            <!-- 外部/方形节点 -->
            <rect
              v-else
              class="external-rect"
              :x="-node.radius"
              :y="-node.radius"
              :width="node.radius * 2"
              :height="node.radius * 2"
              :rx="4"
              :fill="nodeFill(node)"
              :stroke="nodeStroke(node)"
              :stroke-width="node.notable ? 3 : 1.5"
              :stroke-dasharray="hasCollaborators(node) ? '4,3' : 'none'"
            />
            <text class="node-label" text-anchor="middle" dominant-baseline="middle">{{ node.shortTitle }}</text>
          </g>
        </g>
      </svg>

      <div v-if="hoveredNode" class="tooltip" :style="tooltipStyle">
        <h3>{{ hoveredNode.title }}</h3>
        <p v-if="hoveredNode.genre">流派：{{ hoveredNode.genre }}</p>
        <p v-if="hoveredNode.release_year">年份：{{ hoveredNode.release_year }}</p>
        <p>影响力：{{ hoveredNode.influence }}</p>
        
        <!-- 合作者显示 -->
        <p v-if="hasCollaborators(hoveredNode)" class="collab-row">
          <span class="icon">🤝</span> 
          <span>合作者：{{ formatCollaborators(hoveredNode.collaborators) }}</span>
        </p>

        <p>
          来源：翻唱 {{ hoveredNode.influence_breakdown?.cover ?? 0 }} ｜采样 {{ hoveredNode.influence_breakdown?.sample ?? 0 }} ｜引用 {{ hoveredNode.influence_breakdown?.reference ?? 0 }} ｜风格 {{ hoveredNode.influence_breakdown?.style ?? 0 }}
        </p>
        <p v-if="!hoveredNode.own && hoveredNode.artist_name">所属音乐人：{{ hoveredNode.artist_name }}</p>
        <p v-if="hoveredNode.relation_types && hoveredNode.relation_types.length">关联关系：{{ hoveredNode.relation_types.join('、') }}</p>
      </div>

      <div class="legend">
        <div class="legend-item">
          <span class="legend-symbol own"></span>
          <span>圆形：该音乐人的单曲</span>
        </div>
        <div class="legend-item">
          <span class="legend-symbol external"></span>
          <span>方形：外部引用作品</span>
        </div>
        <div class="legend-item">
          <span class="legend-symbol dashed"></span>
          <span>虚线描边：包含合作者</span>
        </div>
        <div class="legend-item">
          <span class="legend-symbol notable"></span>
          <span>黑色描边：成名曲</span>
        </div>
        <div class="legend-item">
          <span class="legend-line"></span>
          <span>线条：翻唱 / 采样 / 引用 / 模仿</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  artist: {
    type: Object,
    default: () => ({})
  },
  nodes: {
    type: Array,
    default: () => []
  },
  links: {
    type: Array,
    default: () => []
  },
  genreColorMap: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['go-back'])

const containerRef = ref(null)
const svgRef = ref(null)
const width = ref(1200)
const height = ref(720)
// d3 模拟更新后，用响应式数组驱动视图刷新
const renderedNodes = ref([])
const renderedLinks = ref([])
const hoveredNode = ref(null)
const tooltipPosition = ref({ x: 0, y: 0 })
let simulation = null

const fallbackPalette = [
  '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
  '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
  '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5',
  '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7',
  '#dda15e'
]

const displayName = computed(() => {
  if (!props.artist) return '未知音乐人'
  if (props.artist.stage_name) {
    if (props.artist.stage_name === props.artist.name) {
      return props.artist.name
    }
    return `${props.artist.name}（${props.artist.stage_name}）`
  }
  return props.artist.name || '未知音乐人'
})

const ownTrackCount = computed(() => props.nodes.filter(node => node.own).length)
const externalTrackCount = computed(() => props.nodes.filter(node => !node.own).length)
const maxInfluenceValue = computed(() => {
  if (!props.nodes.length) return 0
  return Math.max(0, ...props.nodes.map(node => node.influence ?? 0))
})
const linkCount = computed(() => props.links.length)

const tooltipStyle = computed(() => ({
  left: `${tooltipPosition.value.x}px`,
  top: `${tooltipPosition.value.y}px`
}))

function hashToColorIndex(input) {
  if (!input) return 0
  let hash = 0
  for (let i = 0; i < input.length; i++) {
    hash = (hash << 5) - hash + input.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash) % fallbackPalette.length
}

function baseColor(genre) {
  if (genre && props.genreColorMap && props.genreColorMap[genre]) {
    return props.genreColorMap[genre]
  }
  if (!genre) {
    return '#9aa0a6'
  }
  return fallbackPalette[hashToColorIndex(genre)]
}

function nodeFill(node) {
  const color = baseColor(node.genre)
  if (!maxInfluenceValue.value) {
    return d3.interpolateLab('#f6f7fb', color)(0.65)
  }
  const influence = Math.max(0, node.influence ?? 0)
  const ratio = Math.min(1, influence / maxInfluenceValue.value)
  return d3.interpolateLab('#f6f7fb', color)(0.35 + ratio * 0.6)
}

function nodeStroke(node) {
  const color = d3.color(baseColor(node.genre))
  if (!color) return '#555'
  return color.darker(node.own ? 0.6 : 0.2).formatHex()
}

function linkColor(type) {
  const map = {
    CoverOf: '#ff6b6b',
    DirectlySamples: '#feca57',
    InterpolatesFrom: '#54a0ff',
    LyricalReferenceTo: '#5f27cd',
    InStyleOf: '#10ac84'
  }
  return map[type] || '#94a3b8'
}

function hasCollaborators(node) {
  return node.collaborators && node.collaborators.length > 0
}

function formatCollaborators(list) {
  if (!list || !list.length) return ''
  return list
    .map(item => {
      if (!item) return ''
      const displayName = item.stage_name || item.name || '未知音乐人'
      const score = typeof item.predicted_score === 'number'
        ? item.predicted_score.toFixed(2)
        : '未评分'
      const roles = Array.isArray(item.roles) && item.roles.length
        ? `（${item.roles.join(' / ')}）`
        : ''
      return `${displayName}${roles}｜预测 ${score}`
    })
    .filter(Boolean)
    .join('、')
}

function updateCanvasSize() {
  if (!containerRef.value) return
  width.value = containerRef.value.clientWidth || 1200
  height.value = containerRef.value.clientHeight || 720
}

function initSimulation() {
  if (!props.nodes || props.nodes.length === 0) {
    renderedNodes.value = []
    renderedLinks.value = []
    if (simulation) {
      simulation.stop()
      simulation = null
    }
    return
  }

  if (simulation) {
    simulation.stop()
    simulation = null
  }

  const maxInfluence = maxInfluenceValue.value || 1
  const ownRadiusScale = d3.scaleSqrt()
    .domain([0, maxInfluence])
    .range([14, 34])

  const preparedNodes = props.nodes.map(raw => {
    const baseTitle = raw.title || '未命名曲目'
    const short = baseTitle.length > 12 ? `${baseTitle.slice(0, 11)}…` : baseTitle
    return {
      ...raw,
      influence_breakdown: raw.influence_breakdown || { cover: 0, sample: 0, reference: 0, style: 0 },
      relation_types: raw.relation_types || [],
      collaborators: raw.collaborators || [], // 确保合作者数据传递
      radius: raw.own ? ownRadiusScale(raw.influence ?? 0) : 12,
      x: width.value / 2 + (Math.random() - 0.5) * 60,
      y: height.value / 2 + (Math.random() - 0.5) * 60,
      vx: 0,
      vy: 0,
      shortTitle: short
    }
  })

  const preparedLinks = props.links.map(link => ({ ...link }))

  renderedNodes.value = preparedNodes
  renderedLinks.value = preparedLinks.map(link => ({
    source: { x: width.value / 2, y: height.value / 2 },
    target: { x: width.value / 2, y: height.value / 2 },
    type: link.type
  }))

  simulation = d3.forceSimulation(preparedNodes)
    .force('charge', d3.forceManyBody().strength(node => (node.own ? -120 : -70)).distanceMax(420))
    .force('center', d3.forceCenter(width.value / 2, height.value / 2))
    .force('collision', d3.forceCollide().radius(node => node.radius + 6).strength(0.9))
    .force('link', d3.forceLink(preparedLinks)
      .id(node => node.id)
      .distance(link => link.type === 'CoverOf' ? 150 : 170)
      .strength(0.8)
    )
    .force('radial', d3.forceRadial(node => node.own ? Math.min(width.value, height.value) * 0.28 : Math.min(width.value, height.value) * 0.42, width.value / 2, height.value / 2).strength(0.06))
    .alpha(1)
    .alphaDecay(0.025)
    .velocityDecay(0.45)
    .on('tick', () => {
      renderedNodes.value = preparedNodes.map(node => ({ ...node }))
      renderedLinks.value = preparedLinks.map(link => ({
        source: { x: link.source.x, y: link.source.y },
        target: { x: link.target.x, y: link.target.y },
        type: link.type
      }))
    })
}

function handleNodeEnter(event, node) {
  // 保存悬停节点并计算 tooltip 位置
  hoveredNode.value = node
  if (!containerRef.value) return
  const rect = containerRef.value.getBoundingClientRect()
  tooltipPosition.value = {
    x: event.clientX - rect.left + 16,
    y: event.clientY - rect.top + 16
  }
}

function handleNodeLeave() {
  hoveredNode.value = null
}

const handleResize = () => {
  updateCanvasSize()
  nextTick(() => {
    initSimulation()
  })
}

onMounted(() => {
  updateCanvasSize()
  nextTick(() => {
    initSimulation()
  })
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  if (simulation) {
    simulation.stop()
    simulation = null
  }
  window.removeEventListener('resize', handleResize)
})

watch(() => props.nodes, () => {
  nextTick(() => {
    initSimulation()
  })
}, { deep: true })

watch(() => props.links, () => {
  nextTick(() => {
    initSimulation()
  })
}, { deep: true })

watch([width, height], () => {
  nextTick(() => {
    initSimulation()
  })
})
</script>

<style scoped>
.track-view {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: radial-gradient(circle at top left, #1b2735, #090a0f);
  color: #edf2ff;
}

.header {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 16px 24px;
  background: rgba(9, 10, 15, 0.75);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
}

.back-button {
  padding: 10px 20px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.35);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.08));
  color: #f1f5f9;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-button:hover {
  transform: translateX(-4px);
  background: rgba(255, 255, 255, 0.2);
}

.title-block {
  flex: 1;
}

.title-block h1 {
  font-size: 26px;
  margin-bottom: 6px;
}

.subtitle {
  font-size: 14px;
  opacity: 0.85;
}

.metrics {
  display: flex;
  gap: 18px;
}

.metric {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  min-width: 100px;
}

.metric-label {
  font-size: 12px;
  opacity: 0.7;
}

.metric-value {
  font-size: 18px;
  font-weight: 600;
}

.canvas {
  position: relative;
  flex: 1;
  overflow: hidden;
}

svg {
  width: 100%;
  height: 100%;
}

.node-label {
  fill: rgba(255, 255, 255, 0.88);
  pointer-events: none;
  font-size: 10px;
  font-weight: 600;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.6);
}

.track-circle,
.external-rect {
  cursor: pointer;
  transition: filter 0.2s ease, transform 0.2s ease;
}

.track-circle:hover,
.external-rect:hover {
  filter: brightness(1.2);
  transform: scale(1.04);
}

.tooltip {
  position: absolute;
  min-width: 220px;
  max-width: 320px;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.92);
  color: #e2e8f0;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  pointer-events: none;
  line-height: 1.4;
  font-size: 12px;
  backdrop-filter: blur(6px);
}

.tooltip h3 {
  font-size: 16px;
  margin-bottom: 8px;
  color: #f8fafc;
}

.collab-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  color: #667eea;
  font-weight: 500;
  background: rgba(102, 126, 234, 0.1);
  padding: 4px;
  border-radius: 4px;
  margin: 4px 0;
}

.legend {
  position: absolute;
  right: 20px;
  bottom: 24px;
  background: rgba(15, 23, 42, 0.85);
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 12px;
  line-height: 1.6;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.28);
  backdrop-filter: blur(8px);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.legend-item:last-child {
  margin-bottom: 0;
}

.legend-symbol {
  display: inline-block;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.6);
}

.legend-symbol.external {
  border-radius: 4px;
}

.legend-symbol.notable {
  border: 2px solid #000;
  background: transparent;
}

.legend-symbol.dashed {
  border: 2px dashed #fff;
  background: transparent;
}

.legend-line {
  width: 24px;
  height: 2px;
  background: linear-gradient(90deg, #ff6b6b, #10ac84);
  border-radius: 1px;
}
</style>
