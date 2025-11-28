<template>
  <div class="relation-view">
    <!-- 标题栏 -->
    <header class="header">
      <button class="back-button" @click="handleGoBack">
        ← 返回主视图
      </button>
      <div class="title-info">
        <h1>流派关系网络</h1>
        <p class="subtitle">展示流派之间的音乐关系（翻唱、采样、引用、风格模仿等）</p>
      </div>
      <!-- 显示模式选择器 -->
      <div class="display-mode-selector">
        <label class="mode-option">
          <input 
            type="radio" 
            name="displayMode" 
            value="both" 
            v-model="displayMode"
          />
          <span>两者都有</span>
        </label>
        <label class="mode-option">
          <input 
            type="radio" 
            name="displayMode" 
            value="timeline" 
            v-model="displayMode"
          />
          <span>只有心电图</span>
        </label>
        <label class="mode-option">
          <input 
            type="radio" 
            name="displayMode" 
            value="relations" 
            v-model="displayMode"
          />
          <span>只有关系图</span>
        </label>
      </div>
    </header>
    
    <!-- 时间线样式的容器 -->
    <div class="timeline-container" ref="containerRef">
      <div class="timeline-scroll-wrapper" ref="scrollWrapperRef" @scroll="handleScroll">
        <svg :width="svgWidth" :height="svgHeight" class="timeline-svg" ref="svgRef">
          <!-- 背景网格线 -->
          <defs>
            <pattern id="grid-pattern" width="1" height="1" patternUnits="userSpaceOnUse">
              <line x1="0" y1="0" x2="0" y2="1" stroke="#333" stroke-width="0.5" opacity="0.3" />
            </pattern>
          </defs>
          
          <!-- 时间范围标注（顶部） -->
          <g class="time-range-label">
            <text
              :x="svgWidth / 2"
              y="20"
              fill="#aaa"
              font-size="14"
              text-anchor="middle"
              class="time-range-text"
            >
              {{ timeRange.min }} - {{ timeRange.max }}
            </text>
            <line
              :x1="timeLabelWidth + 20"
              y1="30"
              :x2="svgWidth - 20"
              y2="30"
              stroke="#555"
              stroke-width="1"
              opacity="0.5"
            />
          </g>
          
          <!-- 时间轴标签（左侧） -->
          <g class="time-labels">
            <text
              v-for="(year, index) in visibleYears"
              :key="year"
              :x="timeLabelWidth"
              :y="getYearYPosition(year) + 5"
              fill="#888"
              font-size="12"
              text-anchor="end"
              class="year-label"
            >
              {{ year }}
            </text>
          </g>
          
          <!-- 流派竖线和数据 -->
          <g class="genre-columns">
            <g
              v-for="(genre, index) in genres"
              :key="genre"
              :transform="`translate(${getGenreXPosition(index)}, 0)`"
              class="genre-column"
            >
              <!-- 流派标签（顶部） -->
              <text
                x="0"
                :y="25"
                :fill="getGenreColor(genre)"
                font-size="11"
                text-anchor="middle"
                class="genre-label"
                transform="rotate(-45 0 25)"
              >
                {{ genre }}
              </text>
              
              <!-- 竖线（基线，从标签下方开始） -->
              <line
                x1="0"
                y1="35"
                x2="0"
                :y2="svgHeight"
                :stroke="getGenreColor(genre)"
                stroke-width="1"
                opacity="0.3"
                class="genre-line"
              />
              
              <!-- 时间点数据（圆圈） -->
              <g class="data-points" v-if="showTimeline">
                <circle
                  v-for="point in genreDataPointsMap[genre]"
                  :key="`${genre}-${point.year}`"
                  :cx="getPointXOffset(point.count)"
                  :cy="getYearYPosition(point.year)"
                  :r="getPointRadius(point.count)"
                  :fill="getGenreColor(genre)"
                  :opacity="getPointOpacity(point.count)"
                  class="data-point"
                  @mouseenter="showTooltip($event, genre, point.year, point.count)"
                  @mouseleave="hideTooltip"
                />
                
                <!-- 连接线（心电图样式） -->
                <path
                  :d="getGenrePath(genre)"
                  :stroke="getGenreColor(genre)"
                  stroke-width="1.5"
                  fill="none"
                  opacity="0.6"
                  class="data-line"
                />
              </g>
            </g>
          </g>
          
          <!-- 流派间关系连接线（Bundle Line） -->
          <g class="relation-links" v-if="showRelations && relationLinks.length > 0">
            <path
              v-for="(link, index) in relationLinks"
              :key="`link-${index}`"
              :d="link.path"
              :stroke="link.color"
              :stroke-width="link.strokeWidth"
              :opacity="link.opacity"
              fill="none"
              class="relation-link"
              :class="`relation-${link.type}`"
              :style="{ '--stroke-width': link.strokeWidth + 'px' }"
              @mouseenter="showLinkTooltip($event, link)"
              @mouseleave="hideLinkTooltip"
            />
          </g>
        </svg>
      </div>
      
      <!-- 滚动条提示 -->
      <div v-if="needsScroll" class="scroll-hint">
        <span>可滚动查看更多时间数据</span>
      </div>
    </div>
    
    <!-- 工具提示 -->
    <div
      v-if="tooltip.visible"
      class="tooltip"
      :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
    >
      <div class="tooltip-content">
        <strong>{{ tooltip.genre }}</strong>
        <div>年份: {{ tooltip.year }}</div>
        <div>作品数量: {{ tooltip.count }}</div>
      </div>
    </div>
    
    <!-- 图例 -->
    <div class="legend">
      <div class="legend-title">关系类型</div>
      <div class="legend-item" v-for="(color, type) in relationTypeColors" :key="type">
        <div class="legend-line" :style="{ background: color }"></div>
        <span>{{ getRelationTypeLabel(type) }}</span>
      </div>
    </div>
    
    <!-- 工具提示 -->
    <div
      v-if="linkTooltip.visible"
      class="tooltip"
      :style="{ left: linkTooltip.x + 'px', top: linkTooltip.y + 'px' }"
    >
      <div class="tooltip-content">
        <strong>{{ linkTooltip.sourceGenre }} → {{ linkTooltip.targetGenre }}</strong>
        <div>关系类型: {{ getRelationTypeLabel(linkTooltip.type) }}</div>
        <div>时间段: {{ linkTooltip.sourceSegment }} → {{ linkTooltip.targetSegment }}</div>
        <div>关系数量: {{ linkTooltip.count }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  timelineData: {
    type: Object,
    required: true
  },
  genreColorMap: {
    type: Object,
    required: true
  },
  selectedGenres: {
    type: Array,
    default: () => []
  }
})

// ==================== Emits ====================
const emit = defineEmits(['go-back'])

// ==================== 响应式数据 ====================
const containerRef = ref(null)
const scrollWrapperRef = ref(null)
const svgRef = ref(null)
const svgWidth = ref(1200)
const svgHeight = ref(4000)
const scrollTop = ref(0)
const containerHeight = ref(400)

// 显示模式：'both' | 'timeline' | 'relations'
const displayMode = ref('both')

const linkTooltip = ref({
  visible: false,
  x: 0,
  y: 0,
  sourceGenre: '',
  targetGenre: '',
  type: '',
  count: 0,
  sourceSegment: '',
  targetSegment: ''
})

const tooltip = ref({
  visible: false,
  x: 0,
  y: 0,
  genre: '',
  year: 0,
  count: 0
})

// ==================== 计算属性 ====================
// 根据筛选条件过滤流派
const genres = computed(() => {
  const allGenres = props.timelineData?.genres ?? []
  // 如果没有选择任何流派，显示所有流派
  if (!props.selectedGenres || props.selectedGenres.length === 0) {
    return allGenres
  }
  // 只显示选中的流派
  return allGenres.filter(genre => props.selectedGenres.includes(genre))
})

const relations = computed(() => {
  return props.timelineData?.relations ?? []
})

const allYears = computed(() => {
  return props.timelineData?.time_range?.all_years ?? []
})

const timeRange = computed(() => {
  return props.timelineData?.time_range ?? { min: 1975, max: 2040 }
})

const genreTimelines = computed(() => {
  return props.timelineData?.genre_timelines ?? {}
})

// 根据显示模式控制心电图和关系线的显示
const showTimeline = computed(() => {
  return displayMode.value === 'both' || displayMode.value === 'timeline'
})

const showRelations = computed(() => {
  return displayMode.value === 'both' || displayMode.value === 'relations'
})

// 计算时间段（30年一组，与时间线视图保持一致）
const timeSegmentSize = 30

function getTimeSegment(year) {
  const minYear = timeRange.value.min
  return Math.floor((year - minYear) / timeSegmentSize)
}

function getSegmentCenterYear(segment) {
  const minYear = timeRange.value.min
  return minYear + segment * timeSegmentSize + Math.floor(timeSegmentSize / 2)
}

// 计算可见的年份（显示所有年份）
const visibleYears = computed(() => {
  return allYears.value
})

// 计算是否需要滚动
const needsScroll = computed(() => {
  return svgHeight.value > containerHeight.value
})

// 时间标签宽度
const timeLabelWidth = 80

// 列宽度（每个流派占用的宽度）
const columnWidth = computed(() => {
  const availableWidth = svgWidth.value - timeLabelWidth - 20
  return Math.max(40, availableWidth / genres.value.length)
})

// 缓存最大作品数量，避免重复计算
const maxCount = computed(() => {
  let max = 0
  for (const genre of genres.value) {
    const timeline = genreTimelines.value[genre]
    if (timeline && timeline.yearly_counts) {
      for (const count of Object.values(timeline.yearly_counts)) {
        if (count > max) max = count
      }
    }
  }
  return max
})

// 缓存每个流派的数据点，避免在模板中重复计算
const genreDataPointsMap = computed(() => {
  const map = {}
  for (const genre of genres.value) {
    const timeline = genreTimelines.value[genre]
    if (!timeline || !timeline.yearly_counts) {
      map[genre] = []
      continue
    }
    
    const points = []
    for (const year of allYears.value) {
      const count = timeline.yearly_counts[String(year)] || 0
      if (count > 0) {
        points.push({ year, count })
      }
    }
    map[genre] = points
  }
  return map
})

// 关系类型颜色映射
const relationTypeColors = {
  'CoverOf': '#ff6b6b',        // 翻唱 - 红色
  'DirectlySamples': '#4ecdc4', // 采样 - 青色
  'InterpolatesFrom': '#45b7d1', // 插值引用 - 蓝色
  'LyricalReferenceTo': '#96ceb4', // 歌词引用 - 绿色
  'InStyleOf': '#ffeaa7'        // 风格模仿 - 黄色
}

// 缓存关系连接线计算结果，避免频繁重新计算
let cachedRelationLinks = []
let cachedRelationsHash = ''

// 计算流派间的关系连接线（使用bundle line，与时间线视图一致）
const relationLinks = computed(() => {
  if (!relations.value || relations.value.length === 0) return []
  
  // 生成缓存键（包含筛选的流派信息）
  const selectedGenresKey = props.selectedGenres ? props.selectedGenres.sort().join(',') : 'all'
  const currentHash = `${selectedGenresKey}_${genres.value.join(',')}_${relations.value.length}_${timeSegmentSize}`
  if (currentHash === cachedRelationsHash && cachedRelationLinks.length > 0) {
    return cachedRelationLinks
  }
  
  // 按关系类型、源时间段、目标流派分组
  const bundles = new Map()
  
  for (const relation of relations.value) {
    const sourceGenre = relation.source_genre
    const targetGenre = relation.target_genre
    const sourceYear = relation.source_year
    const targetYear = relation.target_year
    const relationType = relation.relation_type
    
    // 检查两个流派是否都在流派列表中
    if (!genres.value.includes(sourceGenre) || !genres.value.includes(targetGenre)) {
      continue
    }
    
    // 检查年份是否在时间范围内
    if (!allYears.value.includes(sourceYear) || !allYears.value.includes(targetYear)) {
      continue
    }
    
    // 获取时间段
    const sourceSegment = getTimeSegment(sourceYear)
    const targetSegment = getTimeSegment(targetYear)
    
    // 创建bundle key
    const bundleKey = `${relationType}_${sourceGenre}_${sourceSegment}_${targetGenre}_${targetSegment}`
    
    if (!bundles.has(bundleKey)) {
      bundles.set(bundleKey, {
        relationType,
        sourceGenre,
        targetGenre,
        sourceSegment,
        targetSegment,
        sourceYear,
        targetYear,
        count: 0
      })
    }
    
    bundles.get(bundleKey).count++
  }
  
  // 生成bundle line路径
  const links = []
  
  for (const bundle of bundles.values()) {
    const sourceGenreIndex = genres.value.indexOf(bundle.sourceGenre)
    const targetGenreIndex = genres.value.indexOf(bundle.targetGenre)
    
    // 源位置：源流派的中心，时间段中心年份
    const sourceSegmentCenterYear = getSegmentCenterYear(bundle.sourceSegment)
    const sourceX = getGenreXPosition(sourceGenreIndex)
    const sourceY = getYearYPosition(sourceSegmentCenterYear)
    
    // 目标位置：目标流派的中心，时间段中心年份
    const targetSegmentCenterYear = getSegmentCenterYear(bundle.targetSegment)
    const targetX = getGenreXPosition(targetGenreIndex)
    const targetY = getYearYPosition(targetSegmentCenterYear)
    
    // 创建bundle line路径（使用更平滑的曲线）
    const dx = targetX - sourceX
    const dy = targetY - sourceY
    const distance = Math.sqrt(dx * dx + dy * dy)
    
    // 控制点偏移，形成平滑的弧线
    const curvature = Math.min(distance * 0.3, 100)
    const perpX = -dy / distance * curvature
    const perpY = dx / distance * curvature
    
    const controlX1 = sourceX + dx * 0.3 + perpX
    const controlY1 = sourceY + dy * 0.3 + perpY
    const controlX2 = sourceX + dx * 0.7 + perpX
    const controlY2 = sourceY + dy * 0.7 + perpY
    
    const path = `M ${sourceX} ${sourceY} C ${controlX1} ${controlY1}, ${controlX2} ${controlY2}, ${targetX} ${targetY}`
    
    // 线条粗细根据数量计算（最小1.5，最大8）
    const strokeWidth = Math.min(1.5 + (bundle.count / 10), 8)
    
    // 透明度根据数量调整（最小0.3，最大0.7）
    const opacity = Math.min(0.3 + (bundle.count / 50), 0.7)
    
    links.push({
      sourceGenre: bundle.sourceGenre,
      targetGenre: bundle.targetGenre,
      sourceSegment: `${timeRange.value.min + bundle.sourceSegment * timeSegmentSize}-${timeRange.value.min + (bundle.sourceSegment + 1) * timeSegmentSize - 1}`,
      targetSegment: `${timeRange.value.min + bundle.targetSegment * timeSegmentSize}-${timeRange.value.min + (bundle.targetSegment + 1) * timeSegmentSize - 1}`,
      type: bundle.relationType,
      count: bundle.count,
      path,
      color: relationTypeColors[bundle.relationType] || '#888',
      strokeWidth,
      opacity
    })
  }
  
  cachedRelationLinks = links
  cachedRelationsHash = currentHash
  return links
})

// ==================== 方法 ====================
function getGenreColor(genre) {
  return props.genreColorMap[genre] || '#888'
}

function getGenreXPosition(index) {
  return timeLabelWidth + 20 + (index + 0.5) * columnWidth.value
}

// 缓存年份位置计算结果
const yearPositionCache = computed(() => {
  const cache = {}
  const yearCount = allYears.value.length
  if (yearCount === 0) return cache
  
  const spacing = 20 // 固定间距
  const labelHeight = 35
  const topMargin = 50
  const bottomMargin = 50
  const availableHeight = svgHeight.value - labelHeight - topMargin - bottomMargin
  
  for (let i = 0; i < yearCount; i++) {
    const year = allYears.value[i]
    const ratio = i / (yearCount - 1)
    cache[year] = labelHeight + topMargin + ratio * availableHeight
  }
  
  return cache
})

function getYearYPosition(year) {
  return yearPositionCache.value[year] || 0
}

// 心电图相关方法
function getPointXOffset(count) {
  if (maxCount.value === 0) return 0
  const ratio = count / maxCount.value
  return ratio * (columnWidth.value * 0.4)
}

function getPointRadius(count) {
  if (maxCount.value === 0) return 2
  const ratio = count / maxCount.value
  return Math.max(2, Math.min(6, 2 + ratio * 4))
}

function getPointOpacity(count) {
  if (maxCount.value === 0) return 0.5
  const ratio = count / maxCount.value
  return Math.max(0.4, Math.min(1, 0.4 + ratio * 0.6))
}

// 缓存心电图路径计算结果
const genrePathsCache = computed(() => {
  const cache = {}
  for (const genre of genres.value) {
    const points = genreDataPointsMap.value[genre]
    if (!points || points.length === 0) {
      cache[genre] = ''
      continue
    }
    
    const line = d3.line()
      .x(d => {
        // 根据作品数量偏移
        if (maxCount.value === 0) return 0
        const ratio = d.count / maxCount.value
        return ratio * (columnWidth.value * 0.4)
      })
      .y(d => getYearYPosition(d.year))
      .curve(d3.curveMonotoneX) // 使用单调曲线
    
    cache[genre] = line(points)
  }
  return cache
})

function getGenrePath(genre) {
  return genrePathsCache.value[genre] || ''
}

// 使用 requestAnimationFrame 优化 tooltip 显示性能
let tooltipRafId = null

function showTooltip(event, genre, year, count) {
  // 取消之前的动画帧请求
  if (tooltipRafId) {
    cancelAnimationFrame(tooltipRafId)
  }
  
  // 使用 requestAnimationFrame 批量更新，避免频繁触发响应式更新
  tooltipRafId = requestAnimationFrame(() => {
    tooltip.value = {
      visible: true,
      x: event.clientX + 10,
      y: event.clientY - 10,
      genre,
      year,
      count
    }
  })
}

function hideTooltip() {
  if (tooltipRafId) {
    cancelAnimationFrame(tooltipRafId)
    tooltipRafId = null
  }
  tooltip.value.visible = false
}

function getRelationTypeLabel(type) {
  const labels = {
    'CoverOf': '翻唱',
    'DirectlySamples': '采样',
    'InterpolatesFrom': '插值引用',
    'LyricalReferenceTo': '歌词引用',
    'InStyleOf': '风格模仿'
  }
  return labels[type] || type
}

// 使用 requestAnimationFrame 优化关系线 tooltip 显示性能
let linkTooltipRafId = null

function showLinkTooltip(event, link) {
  // 取消之前的动画帧请求
  if (linkTooltipRafId) {
    cancelAnimationFrame(linkTooltipRafId)
  }
  
  // 使用 requestAnimationFrame 批量更新
  linkTooltipRafId = requestAnimationFrame(() => {
    linkTooltip.value = {
      visible: true,
      x: event.clientX + 10,
      y: event.clientY - 10,
      sourceGenre: link.sourceGenre,
      targetGenre: link.targetGenre,
      type: link.type,
      count: link.count,
      sourceSegment: link.sourceSegment,
      targetSegment: link.targetSegment
    }
  })
}

function hideLinkTooltip() {
  if (linkTooltipRafId) {
    cancelAnimationFrame(linkTooltipRafId)
    linkTooltipRafId = null
  }
  linkTooltip.value.visible = false
}

function handleGoBack() {
  emit('go-back')
}

function handleScroll() {
  if (scrollWrapperRef.value) {
    scrollTop.value = scrollWrapperRef.value.scrollTop
  }
}

// 缓存上一次的计算结果
let lastContainerHeight = 0
let lastSvgHeight = 0

function updateDimensions() {
  if (!containerRef.value) return
  
  const currentContainerHeight = containerRef.value.clientHeight
  const currentSvgWidth = containerRef.value.clientWidth
  
  if (currentContainerHeight === lastContainerHeight && 
      currentSvgWidth === svgWidth.value) {
    return
  }
  
  containerHeight.value = currentContainerHeight
  svgWidth.value = currentSvgWidth
  
  // 根据年份数量计算SVG高度
  const yearCount = allYears.value.length
  const spacing = 20
  const labelHeight = 35
  const topMargin = 50
  const bottomMargin = 50
  
  const newSvgHeight = Math.max(currentContainerHeight, labelHeight + topMargin + yearCount * spacing + bottomMargin)
  
  if (newSvgHeight !== lastSvgHeight) {
    svgHeight.value = newSvgHeight
    lastSvgHeight = newSvgHeight
  }
  
  lastContainerHeight = currentContainerHeight
}


// ==================== 生命周期 ====================
let resizeObserver = null
let handleResize = null

onMounted(() => {
  updateDimensions()
  
  // 监听窗口大小变化
  handleResize = () => {
    requestAnimationFrame(() => {
      updateDimensions()
    })
  }
  
  window.addEventListener('resize', handleResize)
  
  // 定期更新尺寸（用于处理容器尺寸变化）
  resizeObserver = new ResizeObserver(() => {
    requestAnimationFrame(() => {
      updateDimensions()
    })
  })
  
  if (containerRef.value) {
    resizeObserver.observe(containerRef.value)
  }
})

onBeforeUnmount(() => {
  if (handleResize) {
    window.removeEventListener('resize', handleResize)
  }
  if (resizeObserver && containerRef.value) {
    resizeObserver.unobserve(containerRef.value)
  }
})

// 当数据变化时，更新尺寸
watch(() => [genres.value, allYears.value], () => {
  nextTick(() => {
    updateDimensions()
  })
})
</script>

<style scoped>
.relation-view {
  flex: 1;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #1a1a1a;
  color: #fff;
  overflow: hidden;
}

.header {
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 20px;
  background: #222;
  border-bottom: 1px solid #333;
  color: white;
  flex-shrink: 0;
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

.display-mode-selector {
  display: flex;
  align-items: center;
  gap: 15px;
  background: rgba(255, 255, 255, 0.05);
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.mode-option {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #ccc;
  font-size: 13px;
  user-select: none;
  transition: color 0.2s ease;
}

.mode-option:hover {
  color: #fff;
}

.mode-option input[type="radio"] {
  margin: 0;
  cursor: pointer;
  accent-color: #667eea;
}

.mode-option input[type="radio"]:checked + span {
  color: #fff;
  font-weight: 500;
}

.mode-option span {
  transition: color 0.2s ease, font-weight 0.2s ease;
}

.timeline-container {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: #1a1a1a;
}

.timeline-scroll-wrapper {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  overflow-x: auto;
}

.timeline-svg {
  display: block;
  background: #1a1a1a;
}

.time-labels {
  font-family: 'Arial', sans-serif;
}

.year-label {
  fill: #888;
  user-select: none;
}

.genre-column {
  cursor: pointer;
}

.genre-line {
  pointer-events: none;
}

.genre-label {
  font-size: 10px;
  font-weight: 500;
  pointer-events: none;
  user-select: none;
}

.data-point {
  cursor: pointer;
  transition: r 0.2s ease, opacity 0.2s ease;
}

.data-point:hover {
  r: 8;
  opacity: 1 !important;
}

.data-line {
  pointer-events: none;
}

/* 关系连接线样式（Bundle Line） */
.relation-links {
  pointer-events: all;
}

.relation-link {
  cursor: pointer;
  transition: opacity 0.2s ease, stroke-width 0.2s ease;
  filter: blur(0.5px);
}

.relation-link:hover {
  opacity: 0.9 !important;
  filter: blur(0px);
  z-index: 10;
}

/* 不同关系类型的样式 */
.relation-CoverOf {
  stroke-dasharray: 5, 3;
}

.relation-DirectlySamples {
  stroke-dasharray: 3, 3;
}

.relation-InterpolatesFrom {
  stroke-dasharray: 2, 2;
}

.relation-LyricalReferenceTo {
  stroke-dasharray: 4, 2;
}

.relation-InStyleOf {
  stroke-dasharray: 6, 3;
}

.scroll-hint {
  position: absolute;
  bottom: 10px;
  right: 10px;
  padding: 6px 12px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 4px;
  font-size: 11px;
  color: #aaa;
  pointer-events: none;
}

.legend {
  position: absolute;
  bottom: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.95);
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  font-size: 12px;
  z-index: 100;
}

.legend-title {
  font-weight: 600;
  margin-bottom: 10px;
  color: #333;
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

.legend-line {
  width: 30px;
  height: 2px;
  border-radius: 1px;
}

.tooltip {
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

.tooltip-content strong {
  display: block;
  margin-bottom: 4px;
  color: #fff;
  font-weight: 600;
}

.tooltip-content div {
  margin-top: 2px;
  color: #ccc;
}

/* 滚动条样式 */
.timeline-scroll-wrapper::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.timeline-scroll-wrapper::-webkit-scrollbar-track {
  background: #1a1a1a;
}

.timeline-scroll-wrapper::-webkit-scrollbar-thumb {
  background: #444;
  border-radius: 4px;
}

.timeline-scroll-wrapper::-webkit-scrollbar-thumb:hover {
  background: #555;
}

.time-range-label {
  pointer-events: none;
}

.time-range-text {
  fill: #aaa;
  user-select: none;
}
</style>

