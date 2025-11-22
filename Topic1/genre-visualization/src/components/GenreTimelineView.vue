<template>
  <div class="timeline-view">
    <div class="timeline-header">
      <h2>流派时间线发展</h2>
    </div>
    
    <div v-if="!timelineData || !genres || genres.length === 0" class="loading-message">
      <p>正在加载时间线数据...</p>
    </div>
    
    <div v-else class="timeline-container" ref="containerRef">
      <div class="timeline-scroll-wrapper" ref="scrollWrapperRef" @scroll="handleScroll">
        <svg :width="svgWidth" :height="svgHeight" class="timeline-svg" ref="svgRef">
          <!-- 背景网格线 -->
          <defs>
            <pattern id="grid-pattern" width="1" height="1" patternUnits="userSpaceOnUse">
              <line x1="0" y1="0" x2="0" y2="1" stroke="#333" stroke-width="0.5" opacity="0.3" />
            </pattern>
          </defs>
          
          <!-- 时间轴标签（左侧，根据展开比例显示） -->
          <g class="time-labels" v-if="props.expandRatio > 0">
            <text
              v-for="(year, index) in visibleYears"
              :key="year"
              :x="timeLabelWidth"
              :y="getYearYPosition(year) + 5"
              fill="#888"
              :font-size="11 * props.expandRatio"
              text-anchor="end"
              class="year-label"
              :opacity="props.expandRatio"
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
              <!-- 流派标签（顶部，往下移） -->
              <text
                x="0"
                :y="25"
                :fill="getGenreColor(genre)"
                font-size="10"
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
              <g class="data-points">
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
        <div>作品数: {{ tooltip.count }}</div>
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
  expandRatio: {
    type: Number,
    default: 0,
    validator: (value) => value >= 0 && value <= 1
  }
})

// ==================== 响应式数据 ====================
const containerRef = ref(null)
const scrollWrapperRef = ref(null)
const svgRef = ref(null)
const svgWidth = ref(1200)
const svgHeight = ref(4000) // 初始高度，根据时间范围调整
const scrollTop = ref(0)
const containerHeight = ref(400)

const tooltip = ref({
  visible: false,
  x: 0,
  y: 0,
  genre: '',
  year: '',
  count: 0
})

// ==================== 计算属性 ====================
const genres = computed(() => {
  return props.timelineData?.genres ?? []
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

// 计算可见的年份（根据展开比例）
// 使用缓存优化，避免频繁计算
let cachedVisibleYears = []
let cachedExpandRatio = -1

const visibleYears = computed(() => {
  // 如果展开比例没有变化，返回缓存的结果
  if (cachedExpandRatio === props.expandRatio && cachedVisibleYears.length > 0) {
    return cachedVisibleYears
  }
  
  // 当expandRatio为0时，不显示年份标签
  // 当expandRatio增加时，逐渐显示更多年份
  if (props.expandRatio === 0) {
    cachedVisibleYears = []
    cachedExpandRatio = props.expandRatio
    return []
  }
  
  // 根据展开比例决定显示多少年份
  // expandRatio为1时显示所有年份
  const totalYears = allYears.value.length
  const showCount = Math.ceil(totalYears * props.expandRatio)
  
  // 均匀选择要显示的年份
  if (showCount >= totalYears) {
    cachedVisibleYears = allYears.value
    cachedExpandRatio = props.expandRatio
    return allYears.value
  }
  
  const step = Math.max(1, Math.floor(totalYears / showCount))
  const visible = []
  for (let i = 0; i < totalYears; i += step) {
    visible.push(allYears.value[i])
  }
  // 确保最后一个年份总是显示
  if (visible[visible.length - 1] !== allYears.value[totalYears - 1]) {
    visible.push(allYears.value[totalYears - 1])
  }
  
  cachedVisibleYears = visible
  cachedExpandRatio = props.expandRatio
  return visible
})

// 计算是否需要滚动
const needsScroll = computed(() => {
  return svgHeight.value > containerHeight.value
})

// 时间标签宽度
const timeLabelWidth = 60

// 列宽度（每个流派占用的宽度）
const columnWidth = computed(() => {
  const availableWidth = svgWidth.value - timeLabelWidth - 20
  return Math.max(30, availableWidth / genres.value.length)
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
  
  // 压缩模式：使用更小的间距
  // 展开模式：使用更大的间距
  const minSpacing = 5  // 压缩时的最小间距
  const maxSpacing = 20 // 展开时的最大间距
  const spacing = minSpacing + (maxSpacing - minSpacing) * props.expandRatio
  
  // 流派标签占据35px高度，数据从35px开始
  const labelHeight = 35
  const topMargin = props.expandRatio > 0 ? 50 : 20 // 压缩时减少上边距
  const bottomMargin = props.expandRatio > 0 ? 50 : 20 // 压缩时减少下边距
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

function getPointXOffset(count) {
  // 根据作品数量计算X偏移，形成心电图效果
  // 作品数量越多，偏移越大（向右）
  if (maxCount.value === 0) return 0
  const ratio = count / maxCount.value
  // 最大偏移为列宽的一半
  return ratio * (columnWidth.value * 0.4)
}

function getPointRadius(count) {
  // 根据作品数量计算圆圈半径，最大6，最小2
  if (maxCount.value === 0) return 2
  const ratio = count / maxCount.value
  return 2 + ratio * 4
}

function getPointOpacity(count) {
  // 根据作品数量调整透明度
  if (maxCount.value === 0) return 0.3
  const ratio = count / maxCount.value
  return 0.4 + ratio * 0.6
}

// 缓存路径计算结果
const genrePathsCache = computed(() => {
  const cache = {}
  for (const genre of genres.value) {
    const points = genreDataPointsMap.value[genre]
    if (points.length === 0) {
      cache[genre] = ''
      continue
    }
    
    // 使用d3的line生成器创建平滑曲线
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


function handleScroll() {
  if (scrollWrapperRef.value) {
    scrollTop.value = scrollWrapperRef.value.scrollTop
  }
}

// 缓存上一次的计算结果，避免不必要的更新
let lastContainerHeight = 0
let lastExpandRatio = -1
let lastSvgHeight = 0

function updateDimensions() {
  if (!containerRef.value) return
  
  const currentContainerHeight = containerRef.value.clientHeight
  const currentSvgWidth = containerRef.value.clientWidth
  
  // 只有在容器高度或展开比例变化时才重新计算
  if (currentContainerHeight === lastContainerHeight && 
      props.expandRatio === lastExpandRatio &&
      currentSvgWidth === svgWidth.value) {
    return
  }
  
  containerHeight.value = currentContainerHeight
  svgWidth.value = currentSvgWidth
  
  // 根据年份数量和展开比例计算SVG高度
  const yearCount = allYears.value.length
  // 压缩时使用更小的间距，展开时使用更大的间距
  const minSpacing = 5
  const maxSpacing = 20
  const spacing = minSpacing + (maxSpacing - minSpacing) * props.expandRatio
  
  const labelHeight = 35 // 流派标签高度
  const topMargin = props.expandRatio > 0 ? 50 : 20
  const bottomMargin = props.expandRatio > 0 ? 50 : 20
  
  const newSvgHeight = Math.max(currentContainerHeight, labelHeight + topMargin + yearCount * spacing + bottomMargin)
  
  // 只有在高度真正变化时才更新
  if (newSvgHeight !== lastSvgHeight) {
    svgHeight.value = newSvgHeight
    lastSvgHeight = newSvgHeight
  }
  
  lastContainerHeight = currentContainerHeight
  lastExpandRatio = props.expandRatio
}

// ==================== 生命周期 ====================
onMounted(() => {
  updateDimensions()
  window.addEventListener('resize', updateDimensions)
  
  nextTick(() => {
    updateDimensions()
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateDimensions)
  // 清理 tooltip 相关的资源
  if (tooltipRafId) {
    cancelAnimationFrame(tooltipRafId)
  }
})

watch(() => props.timelineData, () => {
  nextTick(() => {
    updateDimensions()
  })
}, { deep: true })

watch(() => props.expandRatio, () => {
  // 使用 requestAnimationFrame 优化性能，避免频繁的 DOM 更新
  requestAnimationFrame(() => {
    updateDimensions()
  })
}, { flush: 'post' })
</script>

<style scoped>
.timeline-view {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #1a1a1a;
  color: #fff;
  overflow: hidden;
}

.timeline-header {
  padding: 12px 20px;
  border-bottom: 1px solid #333;
  background: #222;
}

.timeline-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

.timeline-header .subtitle {
  margin: 4px 0 0 0;
  font-size: 12px;
  color: #aaa;
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
  font-size: 9px;
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

.loading-message {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #888;
  font-size: 14px;
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
</style>

