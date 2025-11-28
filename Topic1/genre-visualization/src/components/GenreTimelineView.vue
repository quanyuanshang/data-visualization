<template>
  <div class="timeline-view">
    <div class="timeline-header">
      <div class="header-left">
        <h2>流派时间线发展</h2>
        <span class="subtitle" v-if="filteredLinksCount > 0">
          显示 {{ filteredLinksCount }} 条关键关系 (共 {{ totalLinksCount }} 条)
        </span>
      </div>

      <!-- 控制面板 -->
      <div class="controls-panel">
        <!-- 强度过滤器 -->
        <div class="control-group" v-if="displayMode !== 'timeline'">
          <span class="control-label">关系强度过滤</span>
          <div class="slider-container">
            <input 
              type="range" 
              min="0" 
              max="100" 
              v-model.number="strengthThreshold" 
              class="strength-slider"
            />
            <div class="slider-track" :style="{ width: strengthThreshold + '%' }"></div>
          </div>
        </div>

        <!-- 显示模式选择器 -->
        <div class="display-mode-selector">
          <label class="mode-option" :class="{ active: displayMode === 'both' }">
            <input type="radio" name="displayMode" value="both" v-model="displayMode" />
            <span>全部</span>
          </label>
          <label class="mode-option" :class="{ active: displayMode === 'timeline' }">
            <input type="radio" name="displayMode" value="timeline" v-model="displayMode" />
            <span>心电图</span>
          </label>
          <label class="mode-option" :class="{ active: displayMode === 'relations' }">
            <input type="radio" name="displayMode" value="relations" v-model="displayMode" />
            <span>关系网</span>
          </label>
        </div>
      </div>
    </div>
    
    <div v-if="!timelineData || !genres || genres.length === 0" class="loading-message">
      <p>正在加载时间线数据...</p>
    </div>
    
    <div v-else class="timeline-container" ref="containerRef">
      <div class="timeline-scroll-wrapper" ref="scrollWrapperRef" @scroll="handleScroll">
        <svg :width="svgWidth" :height="svgHeight" class="timeline-svg" ref="svgRef">
          <!-- 背景装饰 -->
          <defs>
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="2.5" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            <linearGradient id="fade-gradient" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stop-color="#1a1a1a" stop-opacity="1" />
              <stop offset="100%" stop-color="#1a1a1a" stop-opacity="0" />
            </linearGradient>
          </defs>
          
          <!-- 时间轴标签（左侧） -->
          <g class="time-axis">
            <line 
              :x1="timeLabelWidth" 
              y1="0" 
              :x2="timeLabelWidth" 
              :y2="svgHeight" 
              stroke="#333" 
              stroke-width="1"
            />
            <g v-for="year in visibleYears" :key="year">
              <text
                :x="timeLabelWidth - 10"
                :y="getYearYPosition(year) + 4"
                fill="#666"
                :font-size="getYearLabelFontSize()"
                text-anchor="end"
                class="year-label"
                :opacity="getYearLabelOpacity()"
              >
                {{ year }}
              </text>
              <!-- 只有在展开时显示横向网格线，且要非常淡 -->
              <line 
                v-if="props.expandRatio > 0.2"
                :x1="timeLabelWidth"
                :y1="getYearYPosition(year)"
                :x2="svgWidth"
                :y2="getYearYPosition(year)"
                stroke="#333"
                stroke-width="1"
                stroke-dasharray="4,4"
                opacity="0.1"
              />
            </g>
          </g>

          <!-- 流派竖线轨道 -->
          <g class="genre-tracks">
             <g
              v-for="(genre, index) in genres"
              :key="`track-${genre}`"
              :transform="`translate(${getGenreXPosition(index)}, 0)`"
            >
              <line
                x1="0"
                y1="50"
                x2="0"
                :y2="svgHeight"
                stroke="#333"
                stroke-width="1"
                opacity="0.2"
              />
            </g>
          </g>
          
          <!-- 关系连接线 (Bundle Links) - 放在底层 -->
          <g class="relation-links" v-if="showRelations">
            <path
              v-for="(link, index) in processedRelations.links"
              :key="`link-${index}`"
              :d="link.path"
              :stroke="link.color"
              fill="none"
              class="relation-link"
              :class="{ 'dimmed': hoveredLink && hoveredLink !== link }"
              :style="{ 
                'stroke-width': link.strokeWidth, 
                'opacity': link.opacity 
              }"
              @mouseenter="hoveredLink = link"
              @mouseleave="hoveredLink = null"
            />
          </g>

           <!-- 关系热点节点 (Hotspots) - 放在连接线之上 -->
          <g class="relation-hotspots" v-if="showRelations">
            <circle
              v-for="(spot, key) in processedRelations.hotspots"
              :key="`spot-${key}`"
              :cx="spot.x"
              :cy="spot.y"
              :r="spot.r"
              :fill="getGenreColor(spot.genre)"
              :stroke="getGenreColor(spot.genre)"
              stroke-width="1"
              stroke-opacity="0.5"
              fill-opacity="0.2"
              class="hotspot-node"
              :class="{ 'dimmed': hoveredLink && !isSpotRelatedToLink(spot, hoveredLink) }"
            >
              <animate 
                attributeName="r" 
                :values="`${spot.r};${spot.r + 2};${spot.r}`" 
                dur="3s" 
                repeatCount="indefinite" 
              />
              <animate 
                attributeName="fill-opacity" 
                values="0.2;0.4;0.2" 
                dur="3s" 
                repeatCount="indefinite" 
              />
            </circle>
            <!-- 热点核心实心点 -->
            <circle
              v-for="(spot, key) in processedRelations.hotspots"
              :key="`spot-core-${key}`"
              :cx="spot.x"
              :cy="spot.y"
              :r="spot.r * 0.4"
              :fill="getGenreColor(spot.genre)"
              class="hotspot-core"
              filter="url(#glow)"
              :class="{ 'dimmed': hoveredLink && !isSpotRelatedToLink(spot, hoveredLink) }"
              @mouseenter="showHotspotTooltip($event, spot)"
              @mouseleave="hideRelationTooltip"
            />
          </g>

          <!-- 流派时间线 (心电图) - 放在最上层 -->
          <g class="genre-columns">
            <g
              v-for="(genre, index) in genres"
              :key="genre"
              :transform="`translate(${getGenreXPosition(index)}, 0)`"
              class="genre-column"
            >
              <!-- 流派标签 -->
              <g transform="translate(0, 40)">
                <text
                  x="0"
                  y="0"
                  :fill="getGenreColor(genre)"
                  font-size="11"
                  font-weight="bold"
                  text-anchor="start"
                  class="genre-label"
                  transform="rotate(-45)"
                >
                  {{ genre }}
                </text>
              </g>
              
              <!-- 数据点和连线 -->
              <g class="data-points" v-if="showTimeline">
                <path
                  :d="getGenrePath(genre)"
                  :stroke="getGenreColor(genre)"
                  stroke-width="2"
                  fill="none"
                  class="data-line"
                  filter="url(#glow)"
                />
                <!-- 只显示重要节点或者在hover时显示的节点，减少视觉噪音 -->
                <circle
                  v-for="point in getMajorPoints(genre)"
                  :key="`${genre}-${point.year}`"
                  :cx="getPointXOffset(point.count)"
                  :cy="getYearYPosition(point.year)"
                  :r="3"
                  :fill="getGenreColor(genre)"
                  class="data-point-marker"
                  @mouseenter="showTooltip($event, genre, point.year, point.count)"
                  @mouseleave="hideTooltip"
                />
              </g>
            </g>
          </g>
        </svg>
      </div>
      
      <!-- 滚动提示 -->
      <div v-if="needsScroll" class="scroll-hint">
        <div class="scroll-arrow">↓</div>
      </div>
    </div>
    
    <!-- 工具提示 -->
    <div
      v-if="tooltip.visible"
      class="tooltip"
      :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
    >
      <div class="tooltip-content">
        <strong :style="{ color: getGenreColor(tooltip.genre) }">{{ tooltip.genre }}</strong>
        <div class="tooltip-row"><span>年份:</span> {{ tooltip.year }}</div>
        <div class="tooltip-row"><span>作品数:</span> {{ tooltip.count }}</div>
      </div>
    </div>
    
    <!-- 关系/热点工具提示 -->
    <div
      v-if="relationTooltip.visible"
      class="tooltip relation-tooltip"
      :style="{ left: relationTooltip.x + 'px', top: relationTooltip.y + 'px' }"
    >
      <!-- 热点提示 -->
      <div v-if="relationTooltip.isHotspot" class="tooltip-content">
         <strong :style="{ color: getGenreColor(relationTooltip.genre) }">{{ relationTooltip.genre }} 热点</strong>
         <div class="tooltip-row"><span>时间段:</span> {{ relationTooltip.yearRange }}</div>
         <div class="tooltip-row"><span>活跃度:</span> {{ relationTooltip.intensity }} (关联强度)</div>
      </div>
      <!-- 连接线提示 -->
      <div v-else class="tooltip-content">
        <div class="relation-header">
           <span :style="{ color: getGenreColor(relationTooltip.sourceGenre) }">{{ relationTooltip.sourceGenre }}</span>
           <span class="arrow">→</span>
           <span :style="{ color: getGenreColor(relationTooltip.targetGenre) }">{{ relationTooltip.targetGenre }}</span>
        </div>
        <div class="tooltip-type" :style="{ borderColor: relationTooltip.color }">
          {{ getRelationTypeLabel(relationTooltip.type) }}
        </div>
        <div class="tooltip-row"><span>时间:</span> {{ relationTooltip.sourceYear }} - {{ relationTooltip.targetYear }}</div>
        <div class="tooltip-row"><span>关系强度:</span> {{ relationTooltip.count }}</div>
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
const svgHeight = ref(4000)
const scrollTop = ref(0)
const containerHeight = ref(400)
const hoveredLink = ref(null)

// 过滤器状态
const strengthThreshold = ref(20) // 默认过滤掉20%以下的弱关系
const displayMode = ref('both')

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
  // 联合类型数据
  isHotspot: false,
  sourceGenre: '',
  targetGenre: '',
  sourceYear: '',
  targetYear: '',
  type: '',
  count: 0,
  color: ''
})

// ==================== 计算属性 ====================
const genres = computed(() => {
  const allGenres = props.timelineData?.genres ?? []
  if (!props.selectedGenres || props.selectedGenres.length === 0) {
    return allGenres
  }
  return allGenres.filter(genre => props.selectedGenres.includes(genre))
})

const allYears = computed(() => props.timelineData?.time_range?.all_years ?? [])
const timeRange = computed(() => props.timelineData?.time_range ?? { min: 1975, max: 2040 })
const genreTimelines = computed(() => props.timelineData?.genre_timelines ?? {})

// 视图控制
const showTimeline = computed(() => displayMode.value === 'both' || displayMode.value === 'timeline')
const showRelations = computed(() => displayMode.value === 'both' || displayMode.value === 'relations')
const timeLabelWidth = 70
const columnWidth = computed(() => {
  const availableWidth = svgWidth.value - timeLabelWidth - 40
  return Math.max(40, availableWidth / genres.value.length) // 增加最小宽度
})

// 缓存计算
let cachedVisibleYears = []
let cachedExpandRatio = -1
const visibleYears = computed(() => {
  if (cachedExpandRatio === props.expandRatio && cachedVisibleYears.length > 0) {
    return cachedVisibleYears
  }
  const totalYears = allYears.value.length
  // 增加基础显示的年份密度
  const showCount = props.expandRatio === 0 ? 
    Math.min(totalYears, 10) : // 即使在压缩模式下也至少显示10个刻度
    Math.ceil(totalYears * Math.max(0.2, props.expandRatio))
  
  const step = Math.max(1, Math.floor(totalYears / showCount))
  const visible = []
  for (let i = 0; i < totalYears; i += step) {
    visible.push(allYears.value[i])
  }
  if (visible[visible.length - 1] !== allYears.value[totalYears - 1]) {
    visible.push(allYears.value[totalYears - 1])
  }
  
  cachedVisibleYears = visible
  cachedExpandRatio = props.expandRatio
  return visible
})

const needsScroll = computed(() => svgHeight.value > containerHeight.value)

// 关系颜色映射
const relationTypeColors = {
  'CoverOf': '#ff6b6b',
  'DirectlySamples': '#4ecdc4',
  'InterpolatesFrom': '#45b7d1',
  'LyricalReferenceTo': '#96ceb4',
  'InStyleOf': '#ffeaa7'
}

const timeSegmentSize = 30
function getSegmentCenterYear(segment) {
  return timeRange.value.min + segment * timeSegmentSize + Math.floor(timeSegmentSize / 2)
}

// ==================== 核心逻辑：关系处理与筛选 ====================

const rawRelations = computed(() => {
  if (!props.timelineData?.relations) return []
  const selected = props.selectedGenres && props.selectedGenres.length > 0
  
  // 预聚合
  const bundles = new Map()
  
  for (const rel of props.timelineData.relations) {
    // 筛选逻辑
    if (selected && (!props.selectedGenres.includes(rel.source_genre) || !props.selectedGenres.includes(rel.target_genre))) {
      continue
    }
    if (!genres.value.includes(rel.source_genre) || !genres.value.includes(rel.target_genre)) {
      continue
    }

    const sourceSegment = Math.floor((rel.source_year - timeRange.value.min) / timeSegmentSize)
    const targetSegment = Math.floor((rel.target_year - timeRange.value.min) / timeSegmentSize)
    const key = `${rel.relation_type}_${rel.source_genre}_${sourceSegment}_${rel.target_genre}_${targetSegment}`
    
    if (!bundles.has(key)) {
      bundles.set(key, {
        ...rel,
        sourceSegment,
        targetSegment,
        count: 0
      })
    }
    bundles.get(key).count++
  }
  return Array.from(bundles.values())
})

// 计算关系数据的最大值，用于归一化
const maxRelationCount = computed(() => {
  if (rawRelations.value.length === 0) return 0
  return Math.max(...rawRelations.value.map(r => r.count))
})

// 处理后的关系数据：包含连线和热点
const processedRelations = computed(() => {
  if (rawRelations.value.length === 0) return { links: [], hotspots: {} }

  // 1. 根据滑块阈值过滤
  const maxVal = maxRelationCount.value
  const thresholdVal = Math.ceil(maxVal * (strengthThreshold.value / 100))
  
  const filteredBundles = rawRelations.value.filter(b => b.count >= thresholdVal)
  
  // 2. 生成连线 path
  const links = []
  // 3. 聚合热点数据 (key: genre_segment)
  const hotspotsMap = {}

  filteredBundles.forEach(bundle => {
    const sIndex = genres.value.indexOf(bundle.source_genre)
    const tIndex = genres.value.indexOf(bundle.target_genre)
    
    const sYear = getSegmentCenterYear(bundle.sourceSegment)
    const tYear = getSegmentCenterYear(bundle.targetSegment)
    
    const sx = getGenreXPosition(sIndex)
    const sy = getYearYPosition(sYear)
    const tx = getGenreXPosition(tIndex)
    const ty = getYearYPosition(tYear)

    // 记录热点强度
    const sKey = `${bundle.source_genre}_${bundle.sourceSegment}`
    const tKey = `${bundle.target_genre}_${bundle.targetSegment}`
    
    if(!hotspotsMap[sKey]) hotspotsMap[sKey] = { x: sx, y: sy, intensity: 0, genre: bundle.source_genre, year: sYear }
    if(!hotspotsMap[tKey]) hotspotsMap[tKey] = { x: tx, y: ty, intensity: 0, genre: bundle.target_genre, year: tYear }
    
    hotspotsMap[sKey].intensity += bundle.count
    hotspotsMap[tKey].intensity += bundle.count

    // 生成贝塞尔曲线
    // 增加曲线曲率，使线更"圆"，减少中间的视觉交叉
    const dy = ty - sy
    const controlDist = Math.abs(dy) * 0.6 // 垂直距离越大，控制点拉得越远
    
    // 简单的垂直C型曲线效果通常比S型更适合长垂直时间轴
    // 但为了显示跨度，我们可以让线向外鼓出
    // 这里使用带方向性的曲线
    const midY = (sy + ty) / 2
    
    // 尝试：从左向右连时，控制点向下；从右向左连时，控制点向上？
    // 或者统一使用水平出发
    const path = `M ${sx} ${sy} 
                  C ${sx} ${sy + controlDist}, 
                    ${tx} ${ty - controlDist}, 
                    ${tx} ${ty}`

    // 计算视觉属性
    const normalizedWeight = Math.min(bundle.count / maxVal, 1)
    
    links.push({
      ...bundle,
      sourceYear: sYear,
      targetYear: tYear,
      path,
      color: relationTypeColors[bundle.relation_type] || '#888',
      // 动态线宽：重要的非常粗，不重要的细
      strokeWidth: 1 + Math.pow(normalizedWeight, 2) * 6, 
      // 动态透明度：重要的不透明
      opacity: 0.2 + Math.pow(normalizedWeight, 1.5) * 0.7,
      weight: normalizedWeight
    })
  })

  // 对链接排序，画在后面的会覆盖前面的。让粗线(重要)画在最后
  links.sort((a, b) => a.weight - b.weight)

  // 处理热点可视化数据
  const hotspots = {}
  Object.keys(hotspotsMap).forEach(key => {
    const item = hotspotsMap[key]
    // 半径映射：最小3px，最大12px
    const r = 3 + Math.sqrt(item.intensity) * 1.5
    hotspots[key] = { ...item, r: Math.min(r, 15) }
  })

  return { links, hotspots, count: links.length, total: rawRelations.value.length }
})

const filteredLinksCount = computed(() => processedRelations.value.links.length)
const totalLinksCount = computed(() => rawRelations.value.length)

// ==================== 辅助方法 ====================
function getGenreColor(genre) {
  return props.genreColorMap[genre] || '#888'
}

function getGenreXPosition(index) {
  return timeLabelWidth + 30 + (index + 0.5) * columnWidth.value
}

// 优化：只显示重要的心电图数据点（峰值）
function getMajorPoints(genre) {
  const points = genreDataPointsMap.value[genre] || []
  if (points.length < 20) return points
  
  // 简单筛选：保留波峰和波谷，以及一定间隔的点
  return points.filter((p, i) => {
     if (i === 0 || i === points.length - 1) return true
     const prev = points[i-1].count
     const curr = p.count
     const next = points[i+1].count
     // 局部极值
     if ((curr > prev && curr > next) || (curr < prev && curr < next)) return true
     // 降采样
     return i % 5 === 0
  })
}

// 坐标映射缓存
const yearPositionCache = computed(() => {
  const cache = {}
  const yearCount = allYears.value.length
  if (yearCount === 0) return cache
  
  const minSpacing = 6
  const maxSpacing = 25
  const spacing = minSpacing + (maxSpacing - minSpacing) * props.expandRatio
  
  const topMargin = 80
  const bottomMargin = 50
  
  for (let i = 0; i < yearCount; i++) {
    const year = allYears.value[i]
    const ratio = i / (yearCount - 1)
    // 线性分布，也可以改为非线性从而聚焦中间年份
    cache[year] = topMargin + i * spacing
  }
  return cache
})

function getYearYPosition(year) {
  return yearPositionCache.value[year] || 0
}

function getYearLabelFontSize() {
  return props.expandRatio < 0.2 ? 10 : 12
}

function getYearLabelOpacity() {
  return props.expandRatio < 0.2 ? 0.5 : 0.8
}

// 心电图相关
const maxCount = computed(() => {
  let max = 0
  for (const genre of genres.value) {
    const timeline = genreTimelines.value[genre]
    if (timeline?.yearly_counts) {
      Object.values(timeline.yearly_counts).forEach(c => { if(c > max) max = c })
    }
  }
  return max
})

const genreDataPointsMap = computed(() => {
  const map = {}
  for (const genre of genres.value) {
    const timeline = genreTimelines.value[genre]
    if (!timeline?.yearly_counts) {
      map[genre] = []
      continue
    }
    map[genre] = allYears.value
      .map(year => ({ year, count: timeline.yearly_counts[String(year)] || 0 }))
      .filter(p => p.count > 0)
  }
  return map
})

function getPointXOffset(count) {
  if (maxCount.value === 0) return 0
  // 心电图振幅
  const maxOffset = columnWidth.value * 0.35
  return (count / maxCount.value) * maxOffset
}

function getGenrePath(genre) {
  const points = genreDataPointsMap.value[genre]
  if (!points || points.length === 0) return ''
  
  const line = d3.line()
    .x(d => getPointXOffset(d.count))
    .y(d => getYearYPosition(d.year))
    .curve(d3.curveMonotoneY) // Y轴单调，适合垂直时间轴
  
  return line(points)
}

// ==================== 交互处理 ====================
// 优化 tooltip 显示，增加去抖动
let tooltipTimer = null

function showTooltip(event, genre, year, count) {
  if (hoveredLink.value) return // 如果正在查看关系，不显示普通tooltip
  
  clearTimeout(tooltipTimer)
  tooltip.value = {
    visible: true,
    x: event.clientX + 15,
    y: event.clientY - 10,
    genre,
    year,
    count
  }
}

function showHotspotTooltip(event, spot) {
  if (hoveredLink.value && !isSpotRelatedToLink(spot, hoveredLink.value)) return
  
  // 查找连接到该热点的连线，高亮它们
  // 这里暂时简化，只显示Tooltip
  const rangeStart = spot.year - 15
  const rangeEnd = spot.year + 15

  relationTooltip.value = {
    visible: true,
    x: event.clientX + 15,
    y: event.clientY - 10,
    isHotspot: true,
    genre: spot.genre,
    yearRange: `${rangeStart} - ${rangeEnd}`,
    intensity: spot.intensity
  }
}

function isSpotRelatedToLink(spot, link) {
  if (!link) return false
  const isSource = spot.genre === link.source_genre && Math.abs(spot.year - link.sourceYear) < 5
  const isTarget = spot.genre === link.target_genre && Math.abs(spot.year - link.targetYear) < 5
  return isSource || isTarget
}

function hideTooltip() {
  tooltipTimer = setTimeout(() => {
    tooltip.value.visible = false
  }, 100)
}

function hideRelationTooltip() {
  relationTooltip.value.visible = false
}

function getRelationTypeLabel(type) {
  const map = {
    'CoverOf': '翻唱 (Cover)',
    'DirectlySamples': '直接采样 (Sample)',
    'InterpolatesFrom': '旋律引用 (Interpolate)',
    'LyricalReferenceTo': '歌词致敬 (Lyrics)',
    'InStyleOf': '风格模仿 (Style)'
  }
  return map[type] || type
}

function handleScroll() {
  if (scrollWrapperRef.value) {
    scrollTop.value = scrollWrapperRef.value.scrollTop
  }
}

// 尺寸更新
function updateDimensions() {
  if (!containerRef.value) return
  containerHeight.value = containerRef.value.clientHeight
  svgWidth.value = containerRef.value.clientWidth
  
  const yearCount = allYears.value.length
  const lastYearPos = getYearYPosition(allYears.value[yearCount-1] || 2024)
  const newSvgHeight = Math.max(containerHeight.value, lastYearPos + 100)
  
  if (newSvgHeight !== svgHeight.value) {
    svgHeight.value = newSvgHeight
  }
}

onMounted(() => {
  updateDimensions()
  window.addEventListener('resize', updateDimensions)
  nextTick(updateDimensions)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateDimensions)
})

watch(() => [props.timelineData, props.expandRatio], () => {
  nextTick(updateDimensions)
}, { deep: true })

</script>

<style scoped>
.timeline-view {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #121212; /* 更深的背景色 */
  color: #eee;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.timeline-header {
  padding: 10px 20px;
  background: #1e1e1e;
  border-bottom: 1px solid #333;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 50px;
  flex-shrink: 0;
  z-index: 10;
}

.header-left h2 {
  margin: 0;
  font-size: 16px;
  color: #fff;
  display: inline-block;
  margin-right: 10px;
}

.subtitle {
  font-size: 12px;
  color: #888;
}

.controls-panel {
  display: flex;
  align-items: center;
  gap: 20px;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.control-label {
  font-size: 12px;
  color: #aaa;
}

/* 自定义滑块样式 */
.slider-container {
  position: relative;
  width: 120px;
  height: 20px;
  display: flex;
  align-items: center;
}

.strength-slider {
  -webkit-appearance: none;
  width: 100%;
  height: 4px;
  background: #333;
  border-radius: 2px;
  outline: none;
  z-index: 2;
  position: relative;
  background: transparent;
}

.slider-track {
  position: absolute;
  left: 0;
  top: 8px; /* (20 - 4)/2 */
  height: 4px;
  background: #667eea;
  border-radius: 2px;
  z-index: 1;
  pointer-events: none;
}

.strength-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  cursor: pointer;
  box-shadow: 0 0 5px rgba(0,0,0,0.5);
  transition: transform 0.1s;
}

.strength-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.display-mode-selector {
  display: flex;
  background: #2a2a2a;
  border-radius: 4px;
  padding: 2px;
}

.mode-option {
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
  color: #888;
  border-radius: 2px;
  transition: all 0.2s;
}

.mode-option:hover {
  color: #ccc;
}

.mode-option.active {
  background: #444;
  color: #fff;
  font-weight: 500;
}

.mode-option input {
  display: none;
}

.timeline-container {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.timeline-scroll-wrapper {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden; /* 隐藏横向滚动条，依赖SVG内部适配 */
  scrollbar-width: thin;
  scrollbar-color: #444 #1a1a1a;
}

.timeline-svg {
  display: block;
}

.relation-link {
  transition: opacity 0.3s ease;
  pointer-events: stroke; /* 只有线条本身响应鼠标 */
}

/* 调暗效果：当有一个link被hover时，其他的变暗 */
.relation-link.dimmed {
  opacity: 0.05 !important;
}

.hotspot-node {
  transition: opacity 0.3s ease;
}

.hotspot-node.dimmed, .hotspot-core.dimmed {
  opacity: 0.1;
  fill-opacity: 0.05;
}

.hotspot-core {
  cursor: pointer;
  transition: r 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.hotspot-core:hover {
  r: 8;
  stroke: #fff;
  stroke-width: 2px;
}

/* 滚动提示 */
.scroll-hint {
  position: absolute;
  bottom: 20px;
  right: 20px;
  pointer-events: none;
  animation: bounce 2s infinite;
}

.scroll-arrow {
  width: 30px;
  height: 30px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
}

@keyframes bounce {
  0%, 20%, 50%, 80%, 100% {transform: translateY(0);}
  40% {transform: translateY(-10px);}
  60% {transform: translateY(-5px);}
}

.tooltip {
  position: fixed;
  z-index: 1000;
  background: rgba(20, 20, 20, 0.95);
  border: 1px solid #444;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
  color: #eee;
  pointer-events: none;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  min-width: 180px;
}

.tooltip-content strong {
  display: block;
  font-size: 14px;
  margin-bottom: 8px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  padding-bottom: 4px;
}

.tooltip-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.tooltip-row span {
  color: #888;
  margin-right: 10px;
}

.relation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: bold;
  font-size: 14px;
  margin-bottom: 8px;
}

.relation-header .arrow {
  color: #666;
  font-size: 16px;
}

.tooltip-type {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255,255,255,0.1);
  border-left: 3px solid #888;
  font-size: 11px;
  margin-bottom: 8px;
}

.loading-message {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #666;
}
</style>