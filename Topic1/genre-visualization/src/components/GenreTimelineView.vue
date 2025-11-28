<template>
  <div class="timeline-view">
    <div class="timeline-header">
      <h2>流派时间线发展</h2>
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
          
          <!-- 时间范围标注（顶部） -->
          <g class="time-range-label">
            <text
              :x="svgWidth / 2"
              y="20"
              fill="#aaa"
              font-size="12"
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
          
          <!-- 时间轴标签（左侧，根据展开比例显示） -->
          <g class="time-labels">
            <text
              v-for="(year, index) in visibleYears"
              :key="year"
              :x="timeLabelWidth"
              :y="getYearYPosition(year) + 5"
              fill="#888"
              :font-size="getYearLabelFontSize()"
              text-anchor="end"
              class="year-label"
              :opacity="getYearLabelOpacity()"
            >
              {{ year }}
            </text>
          </g>
          
          <!-- 主要时间点标注（在时间轴上显示关键年份） -->
          <g class="major-time-markers" v-if="props.expandRatio === 0">
            <line
              v-for="year in majorTimeMarkers"
              :key="`marker-${year}`"
              :x1="timeLabelWidth + 20"
              :y1="getYearYPosition(year)"
              :x2="svgWidth - 20"
              :y2="getYearYPosition(year)"
              stroke="#666"
              stroke-width="0.5"
              stroke-dasharray="2,2"
              opacity="0.4"
              class="time-marker-line"
            />
            <text
              v-for="year in majorTimeMarkers"
              :key="`marker-text-${year}`"
              :x="timeLabelWidth + 25"
              :y="getYearYPosition(year) + 4"
              fill="#999"
              font-size="9"
              class="time-marker-label"
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
              @mouseenter="showRelationTooltip($event, link)"
              @mouseleave="hideRelationTooltip"
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
        <div>作品数: {{ tooltip.count }}</div>
      </div>
    </div>
    
    <!-- 关系连接线工具提示 -->
    <div
      v-if="relationTooltip.visible"
      class="tooltip relation-tooltip"
      :style="{ left: relationTooltip.x + 'px', top: relationTooltip.y + 'px' }"
    >
      <div class="tooltip-content">
        <strong>{{ relationTooltip.sourceGenre }} → {{ relationTooltip.targetGenre }}</strong>
        <div>关系类型: {{ getRelationTypeLabel(relationTooltip.type) }}</div>
        <div>源时间段: {{ relationTooltip.sourceYear }}</div>
        <div>目标时间段: {{ relationTooltip.targetYear }}</div>
        <div>关系数量: {{ relationTooltip.count }}</div>
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
  },
  selectedGenres: {
    type: Array,
    default: () => []
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

const relationTooltip = ref({
  visible: false,
  x: 0,
  y: 0,
  sourceGenre: '',
  targetGenre: '',
  sourceYear: '',
  targetYear: '',
  type: '',
  count: 0
})

// 显示模式：'both' | 'timeline' | 'relations'
const displayMode = ref('both')

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
  
  // 当expandRatio为0时，显示少量关键年份
  // 当expandRatio增加时，逐渐显示更多年份
  const totalYears = allYears.value.length
  
  if (props.expandRatio === 0) {
    // 压缩状态：只显示开始、中间、结束等关键年份
    const visible = []
    if (totalYears > 0) {
      visible.push(allYears.value[0]) // 开始年份
      if (totalYears > 1) {
        visible.push(allYears.value[Math.floor(totalYears / 2)]) // 中间年份
        visible.push(allYears.value[totalYears - 1]) // 结束年份
      }
    }
    cachedVisibleYears = visible
    cachedExpandRatio = props.expandRatio
    return visible
  }
  
  // 根据展开比例决定显示多少年份
  // expandRatio为1时显示所有年份
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

// 主要时间点标注（用于压缩状态）
const majorTimeMarkers = computed(() => {
  const totalYears = allYears.value.length
  if (totalYears === 0) return []
  
  // 选择几个关键时间点：开始、1/4、1/2、3/4、结束
  const markers = []
  markers.push(allYears.value[0]) // 开始
  if (totalYears > 4) {
    markers.push(allYears.value[Math.floor(totalYears / 4)])
    markers.push(allYears.value[Math.floor(totalYears / 2)])
    markers.push(allYears.value[Math.floor(totalYears * 3 / 4)])
  }
  if (totalYears > 1) {
    markers.push(allYears.value[totalYears - 1]) // 结束
  }
  
  return markers
})

// 计算是否需要滚动
const needsScroll = computed(() => {
  return svgHeight.value > containerHeight.value
})

// 根据显示模式控制心电图和关系线的显示
const showTimeline = computed(() => {
  return displayMode.value === 'both' || displayMode.value === 'timeline'
})

const showRelations = computed(() => {
  return displayMode.value === 'both' || displayMode.value === 'relations'
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

// 关系类型颜色映射
const relationTypeColors = {
  'CoverOf': '#ff6b6b',        // 翻唱 - 红色
  'DirectlySamples': '#4ecdc4', // 采样 - 青色
  'InterpolatesFrom': '#45b7d1', // 插值引用 - 蓝色
  'LyricalReferenceTo': '#96ceb4', // 歌词引用 - 绿色
  'InStyleOf': '#ffeaa7'        // 风格模仿 - 黄色
}

// 计算时间段（15年一组）
const timeSegmentSize = 30

function getTimeSegment(year) {
  const minYear = timeRange.value.min
  return Math.floor((year - minYear) / timeSegmentSize)
}

function getSegmentCenterYear(segment) {
  const minYear = timeRange.value.min
  return minYear + segment * timeSegmentSize + Math.floor(timeSegmentSize / 2)
}

// 计算流派间的关系连接线（使用bundle line）
const relationLinks = computed(() => {
  if (!props.timelineData) {
    console.log('[GenreTimelineView] 没有时间线数据')
    return []
  }
  
  if (!props.timelineData.relations) {
    console.log('[GenreTimelineView] 时间线数据中没有relations字段')
    return []
  }
  
  if (props.timelineData.relations.length === 0) {
    console.log('[GenreTimelineView] relations数组为空，需要运行extract_timeline_relations.py提取关系数据')
    return []
  }
  
  console.log(`[GenreTimelineView] 找到 ${props.timelineData.relations.length} 条关系`)
  
  const relations = props.timelineData.relations
  
  // 按关系类型、源时间段、目标流派分组
  const bundles = new Map()
  
  for (const relation of relations) {
    const sourceGenre = relation.source_genre
    const targetGenre = relation.target_genre
    const sourceYear = relation.source_year
    const targetYear = relation.target_year
    const relationType = relation.relation_type
    
    // 检查两个流派是否都在筛选后的流派列表中
    // 如果没有筛选，显示所有关系；如果有筛选，只显示选中流派之间的关系
    const shouldShow = props.selectedGenres && props.selectedGenres.length > 0
      ? props.selectedGenres.includes(sourceGenre) && props.selectedGenres.includes(targetGenre)
      : genres.value.includes(sourceGenre) && genres.value.includes(targetGenre)
    
    if (!shouldShow) {
      continue
    }
    
    // 检查年份是否在时间范围内
    if (!allYears.value.includes(sourceYear) || !allYears.value.includes(targetYear)) {
      continue
    }
    
    // 获取时间段
    const sourceSegment = getTimeSegment(sourceYear)
    const targetSegment = getTimeSegment(targetYear)
    
    // 创建bundle key: relationType_sourceGenre_sourceSegment_targetGenre_targetSegment
    const bundleKey = `${relationType}_${sourceGenre}_${sourceSegment}_${targetGenre}_${targetSegment}`
    
    if (!bundles.has(bundleKey)) {
      bundles.set(bundleKey, {
        relationType,
        sourceGenre,
        targetGenre,
        sourceSegment,
        targetSegment,
        sourceYear, // 保存第一个年份作为代表
        targetYear, // 保存第一个年份作为代表
        count: 0
      })
    }
    
    bundles.get(bundleKey).count++
  }
  
  console.log(`[GenreTimelineView] 分组后得到 ${bundles.size} 个bundle`)
  
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
    // 使用三次贝塞尔曲线，控制点在中点附近，形成平滑的弧线
    const midX = (sourceX + targetX) / 2
    const midY = (sourceY + targetY) / 2
    
    // 计算控制点，使曲线更平滑
    const dx = targetX - sourceX
    const dy = targetY - sourceY
    const distance = Math.sqrt(dx * dx + dy * dy)
    
    // 控制点偏移，形成平滑的弧线
    const curvature = Math.min(distance * 0.3, 100) // 最大弯曲度
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
      sourceYear: bundle.sourceYear,
      targetYear: bundle.targetYear,
      sourceSegment: bundle.sourceSegment,
      targetSegment: bundle.targetSegment,
      type: bundle.relationType,
      count: bundle.count,
      path,
      color: relationTypeColors[bundle.relationType] || '#888',
      strokeWidth,
      opacity
    })
  }
  
  console.log(`[GenreTimelineView] 生成了 ${links.length} 条bundle连接线`)
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

function getYearLabelFontSize() {
  // 根据展开比例调整字体大小
  if (props.expandRatio === 0) {
    return 10 // 压缩状态下使用较小字体
  }
  return 11 * props.expandRatio
}

function getYearLabelOpacity() {
  // 根据展开比例调整透明度
  if (props.expandRatio === 0) {
    return 0.6 // 压缩状态下降低透明度
  }
  return props.expandRatio
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

function showRelationTooltip(event, link) {
  const sourceSegmentStart = timeRange.value.min + link.sourceSegment * timeSegmentSize
  const sourceSegmentEnd = sourceSegmentStart + timeSegmentSize - 1
  const targetSegmentStart = timeRange.value.min + link.targetSegment * timeSegmentSize
  const targetSegmentEnd = targetSegmentStart + timeSegmentSize - 1
  
  relationTooltip.value = {
    visible: true,
    x: event.clientX + 10,
    y: event.clientY - 10,
    sourceGenre: link.sourceGenre,
    targetGenre: link.targetGenre,
    sourceYear: `${sourceSegmentStart}-${sourceSegmentEnd}`,
    targetYear: `${targetSegmentStart}-${targetSegmentEnd}`,
    type: link.type,
    count: link.count
  }
}

function hideRelationTooltip() {
  relationTooltip.value.visible = false
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 15px;
}

.timeline-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

/* 显示模式选择器 */
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

/* 关系连接线样式（Bundle Line） */
.relation-links {
  pointer-events: all;
}

.relation-link {
  cursor: pointer;
  transition: opacity 0.2s ease, stroke-width 0.2s ease;
  filter: blur(0.5px); /* 轻微模糊，使bundle效果更自然 */
}

.relation-link:hover {
  opacity: 0.9 !important;
  filter: blur(0px); /* 悬停时取消模糊 */
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

