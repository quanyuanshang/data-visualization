<template>
  <div class="relation-view">
    <!-- 标题栏 -->
    <header class="header">
      <div class="header-left">
        <button class="back-button" @click="handleGoBack">
          ← 返回主视图
        </button>
        <div class="title-info">
          <h1>流派关系网络</h1>
          <p class="subtitle" v-if="filteredLinksCount > 0">
            显示 {{ filteredLinksCount }} 条关键路径 (共 {{ totalLinksCount }} 条)
          </p>
        </div>
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
            <span>数据流</span>
          </label>
          <label class="mode-option" :class="{ active: displayMode === 'relations' }">
            <input type="radio" name="displayMode" value="relations" v-model="displayMode" />
            <span>关系网</span>
          </label>
        </div>
      </div>
    </header>
    
    <!-- 时间线样式的容器 -->
    <div class="timeline-container" ref="containerRef">
      <div class="timeline-scroll-wrapper" ref="scrollWrapperRef" @scroll="handleScroll">
        <svg :width="svgWidth" :height="svgHeight" class="timeline-svg" ref="svgRef">
          <!-- 滤镜定义 -->
          <defs>
            <filter id="glow-relation" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            <pattern id="grid-pattern" width="1" height="1" patternUnits="userSpaceOnUse">
              <line x1="0" y1="0" x2="0" y2="1" stroke="#333" stroke-width="0.5" opacity="0.2" />
            </pattern>
          </defs>
          
          <!-- 时间轴标签（左侧） -->
          <g class="time-labels">
            <text
              v-for="year in visibleYears"
              :key="year"
              :x="timeLabelWidth"
              :y="getYearYPosition(year) + 4"
              fill="#666"
              font-size="11"
              text-anchor="end"
              class="year-label"
            >
              {{ year }}
            </text>
            <!-- 横向参考线 -->
            <line 
              v-for="year in visibleYears"
              :key="`line-${year}`"
              :x1="timeLabelWidth + 10"
              :y1="getYearYPosition(year)"
              :x2="svgWidth"
              :y2="getYearYPosition(year)"
              stroke="#333"
              stroke-width="1"
              stroke-dasharray="2,4"
              opacity="0.1"
            />
          </g>
          
          <!-- 流派轨道背景 -->
          <g class="genre-tracks">
             <g
              v-for="(genre, index) in genres"
              :key="`track-${genre}`"
              :transform="`translate(${getGenreXPosition(index)}, 0)`"
            >
              <line
                x1="0"
                y1="30"
                x2="0"
                :y2="svgHeight"
                stroke="#333"
                stroke-width="1"
                opacity="0.15"
              />
            </g>
          </g>

          <!-- 关系连接线 (Bundle Links) -->
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

          <!-- 关系热点节点 (Hotspots) -->
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
              fill-opacity="0.15"
              class="hotspot-node"
              :class="{ 'dimmed': hoveredLink && !isSpotRelatedToLink(spot, hoveredLink) }"
            >
               <animate 
                attributeName="r" 
                :values="`${spot.r};${spot.r + 3};${spot.r}`" 
                dur="4s" 
                repeatCount="indefinite" 
              />
            </circle>
            <!-- 热点核心 -->
            <circle
              v-for="(spot, key) in processedRelations.hotspots"
              :key="`spot-core-${key}`"
              :cx="spot.x"
              :cy="spot.y"
              :r="Math.max(2, spot.r * 0.4)"
              :fill="getGenreColor(spot.genre)"
              class="hotspot-core"
              filter="url(#glow-relation)"
              :class="{ 'dimmed': hoveredLink && !isSpotRelatedToLink(spot, hoveredLink) }"
              @mouseenter="showHotspotTooltip($event, spot)"
              @mouseleave="hideRelationTooltip"
            />
          </g>
          
          <!-- 流派心电图和流派标签 (置顶) -->
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
                font-weight="600"
                text-anchor="middle"
                class="genre-label"
                transform="rotate(-45 0 25)"
              >
                {{ genre }}
              </text>
              
              <!-- 时间点数据（圆圈） -->
              <g class="data-points" v-if="showTimeline">
                <!-- 连接线（心电图样式） -->
                <path
                  :d="getGenrePath(genre)"
                  :stroke="getGenreColor(genre)"
                  stroke-width="1.5"
                  fill="none"
                  opacity="0.8"
                  class="data-line"
                  filter="url(#glow-relation)"
                />
                
                <!-- 关键数据点 -->
                <circle
                  v-for="point in getMajorPoints(genre)"
                  :key="`${genre}-${point.year}`"
                  :cx="getPointXOffset(point.count)"
                  :cy="getYearYPosition(point.year)"
                  :r="getPointRadius(point.count)"
                  :fill="getGenreColor(genre)"
                  class="data-point"
                  @mouseenter="showTooltip($event, genre, point.year, point.count)"
                  @mouseleave="hideTooltip"
                />
              </g>
            </g>
          </g>
        </svg>
      </div>
      
      <!-- 滚动条提示 -->
      <div v-if="needsScroll" class="scroll-hint">
        <span>↓ 滚动查看更多年份</span>
      </div>
    </div>
    
    <!-- 普通数据工具提示 -->
    <div
      v-if="tooltip.visible"
      class="tooltip"
      :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
    >
      <div class="tooltip-content">
        <strong :style="{ color: getGenreColor(tooltip.genre) }">{{ tooltip.genre }}</strong>
        <div>年份: {{ tooltip.year }}</div>
        <div>作品数量: {{ tooltip.count }}</div>
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
    </div>

    <!-- 详细的关系悬停提示 (鼠标悬停在连线上时显示详细列表) -->
    <div
      v-if="hoveredLink"
      class="tooltip link-tooltip"
      :style="{ left: (svgWidth/2) + 'px', top: '80px', position: 'absolute', transform: 'translateX(-50%)' }"
    >
       <div class="link-tooltip-content">
         <div class="link-header">
            <span :style="{ color: getGenreColor(hoveredLink.sourceGenre) }">{{ hoveredLink.sourceGenre }}</span>
            <span class="arrow"> ➜ </span>
            <span :style="{ color: getGenreColor(hoveredLink.targetGenre) }">{{ hoveredLink.targetGenre }}</span>
            <span class="badge" :style="{ backgroundColor: hoveredLink.color }">{{ getRelationTypeLabel(hoveredLink.type) }}</span>
            <span class="count">强度: {{ hoveredLink.count }}</span>
         </div>
         
         <!-- 详细作品列表 -->
         <div class="relations-list">
           <div v-for="(rel, idx) in hoveredLink.relations.slice(0, 8)" :key="idx" class="relation-item">
             <span class="rel-time">{{ rel.source_year }}</span>
             <span class="rel-song">{{ getWorkTitle(rel.source_work_id, hoveredLink.sourceGenre, rel.source_year, rel.source_title) }}</span>
             <span class="rel-arrow">→</span>
             <span class="rel-time">{{ rel.target_year }}</span>
             <span class="rel-song">{{ getWorkTitle(rel.target_work_id, hoveredLink.targetGenre, rel.target_year, rel.target_title) }}</span>
           </div>
           <div v-if="hoveredLink.relations.length > 8" class="more-relations">
             ... 还有 {{ hoveredLink.relations.length - 8 }} 条记录
           </div>
         </div>
       </div>
    </div>

    <!-- 图例 -->
    <div class="legend">
      <div class="legend-title">关系类型图例</div>
      <div class="legend-grid">
        <div class="legend-item" v-for="(color, type) in relationTypeColors" :key="type">
          <div class="legend-dot" :style="{ background: color }"></div>
          <span>{{ getRelationTypeLabel(type) }}</span>
        </div>
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

const emit = defineEmits(['go-back'])

// ==================== 响应式数据 ====================
const containerRef = ref(null)
const scrollWrapperRef = ref(null)
const svgRef = ref(null)
const svgWidth = ref(1200)
const svgHeight = ref(4000)
const scrollTop = ref(20)
const containerHeight = ref(400)

// 控制状态
const displayMode = ref('both')
const strengthThreshold = ref(15) // 默认过滤掉15%以下的弱关系
const hoveredLink = ref(null)

const relationTooltip = ref({
  visible: false,
  x: 0,
  y: 0,
  isHotspot: false,
  genre: '',
  sourceGenre: '',
  targetGenre: '',
  type: '',
  count: 0,
  yearRange: '',
  intensity: 0,
  color: ''
})

const tooltip = ref({
  visible: false,
  x: 0,
  y: 0,
  genre: '',
  year: 0,
  count: 0
})

// ==================== 颜色定义 ====================
const relationTypeColors = {
  'CoverOf': '#ff6b6b',         // 红色: 翻唱
  'DirectlySamples': '#4ecdc4', // 青色: 直接采样
  'InterpolatesFrom': '#45b7d1', // 蓝色: 旋律引用
  'LyricalReferenceTo': '#96ceb4', // 绿色: 歌词致敬
  'InStyleOf': '#ffeaa7'        // 黄色: 风格模仿
}

// ==================== 计算属性 ====================
// 过滤后的流派列表
const genres = computed(() => {
  const allGenres = props.timelineData?.genres ?? []
  if (!props.selectedGenres || props.selectedGenres.length === 0) {
    return allGenres
  }
  return allGenres.filter(genre => props.selectedGenres.includes(genre))
})

// 基础时间范围数据
const allYears = computed(() => props.timelineData?.time_range?.all_years ?? [])
const timeRange = computed(() => {
  const range = props.timelineData?.time_range ?? { min: 1975, max: 2040 }
  return { min: Number(range.min), max: Number(range.max) }
})
const genreTimelines = computed(() => props.timelineData?.genre_timelines ?? {})

// 视图模式判断
const showTimeline = computed(() => displayMode.value === 'both' || displayMode.value === 'timeline')
const showRelations = computed(() => displayMode.value === 'both' || displayMode.value === 'relations')

// 布局参数
const topMargin = 80
const bottomMargin = 80
const labelHeight = 40
const timeLabelWidth = 60

// 动态计算 SVG 高度以适应时间范围
const pixelsPerYear = 20 // 压缩高度，每一年20px

// 计算可见年份（每5年一个标签）
const visibleYears = computed(() => {
  const min = timeRange.value.min
  const max = timeRange.value.max
  const years = []
  for (let y = min; y <= max; y++) {
    if (y % 5 === 0 || y === min || y === max) years.push(y)
  }
  return [...new Set(years)].sort((a,b) => a-b)
})

const needsScroll = computed(() => svgHeight.value > containerHeight.value)

const columnWidth = computed(() => {
  const availableWidth = svgWidth.value - timeLabelWidth - 40
  return Math.max(50, availableWidth / Math.max(1, genres.value.length))
})

// 心电图数据处理
const maxCount = computed(() => {
  let max = 0
  for (const genre of genres.value) {
    const timeline = genreTimelines.value[genre]
    if (timeline?.yearly_counts) {
      Object.values(timeline.yearly_counts).forEach(c => { if (c > max) max = c })
    }
  }
  return max
})

const genreDataPointsMap = computed(() => {
  const map = {}
  for (const genre of genres.value) {
    const timeline = genreTimelines.value[genre]
    map[genre] = []
    
    const counts = timeline?.yearly_counts || {}
    const min = timeRange.value.min
    const max = timeRange.value.max
    
    for (let y = min; y <= max; y++) {
      const count = counts[String(y)] || 0
      // 包含所有年份数据，即使 count 为 0，以保持心电图线条连续
      map[genre].push({ year: y, count })
    }
  }
  return map
})

// 快速查找作品详情的 Map { id: { title, year, genre } }
// 使用数字ID作为key，同时支持字符串和数字类型的查找
const workLookup = computed(() => {
  const map = new Map()
  if (!props.timelineData?.genre_timelines) {
    return map
  }
  
  let totalWorks = 0
  Object.entries(props.timelineData.genre_timelines).forEach(([genre, data]) => {
    if (data.timeline) {
      data.timeline.forEach(entry => {
        const year = entry[0]
        const works = entry[1]?.works || []
        works.forEach(work => {
          const workId = Number(work.id)
          if (!isNaN(workId)) {
            const workInfo = {
              title: work.title || 'Unknown Work',
              year: year,
              genre: genre
            }
            map.set(workId, workInfo)
            map.set(String(workId), workInfo)
            if (work.id !== workId && work.id !== String(workId)) {
              map.set(work.id, workInfo)
            }
            totalWorks++
          }
        })
      })
    }
  })
  return map
})

function getWorkTitle(id, genreHint, yearHint, directTitle = null) {
  if (directTitle && directTitle.trim() && directTitle !== 'Unknown' && directTitle !== 'Unknown Work') {
    return directTitle
  }
  
  if (id === null || id === undefined || id === '') {
    return '未知作品'
  }
  
  let work = workLookup.value.get(id)
  if (!work) {
    const numId = Number(id)
    if (!isNaN(numId)) {
      work = workLookup.value.get(numId) || workLookup.value.get(String(numId))
    }
  }
  
  if (work) {
    if (work.title) {
      if (work.title === 'Unknown' || work.title === 'Unknown Work') {
        return '未知歌曲'
      }
      return work.title
    }
  }
  
  if (directTitle === 'Unknown' || directTitle === 'Unknown Work') {
    return '未知歌曲'
  }
  
  if (genreHint && yearHint) {
    return `作品 #${id} (${genreHint}, ${yearHint})`
  }
  return `作品 #${id}`
}

// ==================== 核心逻辑：关系处理与可视化 ====================

// 1. 获取并聚合原始关系数据
const rawRelations = computed(() => {
  if (!props.timelineData?.relations) return []
  
  const selected = props.selectedGenres && props.selectedGenres.length > 0
  // 聚合粒度
  const timeSegmentSize = 10 
  const bundles = new Map()
  
  for (const rel of props.timelineData.relations) {
    const sGenre = rel.source_genre
    const tGenre = rel.target_genre
    
    if (selected && (!props.selectedGenres.includes(sGenre) || !props.selectedGenres.includes(tGenre))) continue
    if (!genres.value.includes(sGenre) || !genres.value.includes(tGenre)) continue
    
    const sYear = Number(rel.source_year)
    const tYear = Number(rel.target_year)
    
    if (sYear < timeRange.value.min || sYear > timeRange.value.max) continue
    if (tYear < timeRange.value.min || tYear > timeRange.value.max) continue

    const sSeg = Math.floor((sYear - timeRange.value.min) / timeSegmentSize)
    const tSeg = Math.floor((tYear - timeRange.value.min) / timeSegmentSize)
    
    const key = `${rel.relation_type}_${sGenre}_${sSeg}_${tGenre}_${tSeg}`
    
    if (!bundles.has(key)) {
      bundles.set(key, {
        relationType: rel.relation_type,
        sourceGenre: sGenre,
        targetGenre: tGenre,
        sourceYearSum: 0,
        targetYearSum: 0,
        count: 0,
        sSeg,
        tSeg,
        relations: []
      })
    }
    const b = bundles.get(key)
    b.sourceYearSum += sYear
    b.targetYearSum += tYear
    b.count++
    b.relations.push(rel)
  }
  
  return Array.from(bundles.values()).map(b => ({
    ...b,
    avgSourceYear: b.sourceYearSum / b.count,
    avgTargetYear: b.targetYearSum / b.count,
    relations: b.relations.sort((a, b) => a.source_year - b.source_year)
  }))
})

const maxRelationCount = computed(() => {
  if (rawRelations.value.length === 0) return 0
  return Math.max(...rawRelations.value.map(r => r.count))
})

// 2. 处理渲染数据 (Filtering, Geometry, Hotspots)
const processedRelations = computed(() => {
  if (rawRelations.value.length === 0) return { links: [], hotspots: {} }

  const maxVal = maxRelationCount.value
  const thresholdVal = Math.max(1, Math.ceil(maxVal * (strengthThreshold.value / 100)))
  
  const filtered = rawRelations.value.filter(b => b.count >= thresholdVal)
  
  const links = []
  const hotspotsMap = {}

  filtered.forEach(bundle => {
    const sIdx = genres.value.indexOf(bundle.sourceGenre)
    const tIdx = genres.value.indexOf(bundle.targetGenre)
    
    // --- 对齐逻辑修正 ---
    // 将平均年份强制吸附到最近的5年刻度
    const gridSnap = 5
    const snappedSourceYear = Math.round(bundle.avgSourceYear / gridSnap) * gridSnap
    const snappedTargetYear = Math.round(bundle.avgTargetYear / gridSnap) * gridSnap

    const sx = getGenreXPosition(sIdx)
    const sy = getYearYPosition(snappedSourceYear)
    const tx = getGenreXPosition(tIdx)
    const ty = getYearYPosition(snappedTargetYear)
    
    const sKey = `${bundle.sourceGenre}_${snappedSourceYear}`
    const tKey = `${bundle.targetGenre}_${snappedTargetYear}`
    
    if(!hotspotsMap[sKey]) hotspotsMap[sKey] = { x: sx, y: sy, intensity: 0, genre: bundle.sourceGenre, year: snappedSourceYear }
    if(!hotspotsMap[tKey]) hotspotsMap[tKey] = { x: tx, y: ty, intensity: 0, genre: bundle.targetGenre, year: snappedTargetYear }
    
    hotspotsMap[sKey].intensity += bundle.count
    hotspotsMap[tKey].intensity += bundle.count

    const dy = ty - sy
    const dx = tx - sx
    
    const controlY = Math.abs(dy) * 0.5
    
    let path = ''
    if (Math.abs(dx) < 10 && Math.abs(dy) < 10) {
       path = `M ${sx} ${sy} L ${tx} ${ty}` 
    } else {
       path = `M ${sx} ${sy} 
               C ${sx} ${sy + controlY}, 
                 ${tx} ${ty - controlY}, 
                 ${tx} ${ty}`
    }

    const normWeight = Math.min(bundle.count / maxVal, 1)
    
    links.push({
      ...bundle,
      relations: bundle.relations,
      avgSourceYear: snappedSourceYear, 
      avgTargetYear: snappedTargetYear,
      path,
      color: relationTypeColors[bundle.relationType] || '#888',
      strokeWidth: 1 + Math.pow(normWeight, 0.8) * 8,
      opacity: 0.3 + Math.pow(normWeight, 0.5) * 0.7,
      weight: normWeight
    })
  })

  links.sort((a, b) => a.weight - b.weight)

  const hotspots = {}
  Object.keys(hotspotsMap).forEach(k => {
     const h = hotspotsMap[k]
     const r = 3 + Math.sqrt(h.intensity) * 1.2
     hotspots[k] = { ...h, r: Math.min(r, 20) }
  })

  return { links, hotspots }
})

const filteredLinksCount = computed(() => processedRelations.value.links.length)
const totalLinksCount = computed(() => rawRelations.value.length)

// ==================== 辅助方法 ====================
function getGenreColor(genre) {
  return props.genreColorMap[genre] || '#888'
}

function getGenreXPosition(index) {
  return timeLabelWidth + 40 + (index + 0.5) * columnWidth.value
}

function getYearYPosition(year) {
  return labelHeight + topMargin + (year - timeRange.value.min) * pixelsPerYear
}

// 心电图辅助
function getPointXOffset(count) {
  if (maxCount.value === 0) return 0
  return (count / maxCount.value) * (columnWidth.value * 0.4)
}

function getPointRadius(count) {
  if (maxCount.value === 0) return 2
  const ratio = count / maxCount.value
  return Math.max(2, Math.min(5, 2 + ratio * 4))
}

function getGenrePath(genre) {
  const points = genreDataPointsMap.value[genre]
  if (!points || points.length === 0) return ''
  
  const line = d3.line()
    .x(d => getPointXOffset(d.count))
    .y(d => getYearYPosition(d.year))
    .curve(d3.curveMonotoneY)
  
  return line(points)
}

// 筛选主要数据点（避免心电图过于密集），只显示有数据的点
function getMajorPoints(genre) {
  const points = genreDataPointsMap.value[genre] || []
  return points.filter(p => p.count > 0) 
}

// ==================== 交互事件 ====================
let tooltipTimer = null

function showTooltip(event, genre, year, count) {
  if (hoveredLink.value) return 
  
  tooltip.value = {
    visible: true,
    x: event.clientX + 15,
    y: event.clientY - 10,
    genre,
    year,
    count
  }
}

function hideTooltip() {
  tooltip.value.visible = false
}

function showHotspotTooltip(event, spot) {
  relationTooltip.value = {
    visible: true,
    x: event.clientX + 15,
    y: event.clientY - 10,
    isHotspot: true,
    genre: spot.genre,
    yearRange: `${spot.year - 2} - ${spot.year + 3}`,
    intensity: spot.intensity
  }
}

function hideRelationTooltip() {
  relationTooltip.value.visible = false
}

function isSpotRelatedToLink(spot, link) {
  if (!link) return false
  const isSource = spot.genre === link.sourceGenre && Math.abs(spot.year - link.avgSourceYear) < 2
  const isTarget = spot.genre === link.targetGenre && Math.abs(spot.year - link.avgTargetYear) < 2
  return isSource || isTarget
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

function handleGoBack() {
  emit('go-back')
}

function handleScroll() {
  if (scrollWrapperRef.value) {
    scrollTop.value = scrollWrapperRef.value.scrollTop
  }
}

function updateDimensions() {
  if (!containerRef.value) return
  
  const currentContainerHeight = containerRef.value.clientHeight
  const currentSvgWidth = containerRef.value.clientWidth
  
  svgWidth.value = currentSvgWidth
  containerHeight.value = currentContainerHeight
  
  // 计算需要的总高度
  const yearSpan = timeRange.value.max - timeRange.value.min
  const contentHeight = labelHeight + topMargin + (yearSpan * pixelsPerYear) + bottomMargin
  
  svgHeight.value = Math.max(currentContainerHeight, contentHeight)
}

onMounted(() => {
  updateDimensions()
  window.addEventListener('resize', updateDimensions)
  nextTick(updateDimensions)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateDimensions)
})

watch([genres, strengthThreshold], () => {
  // 触发重绘计算在 computed 中自动完成
}, { deep: true })

</script>

<style scoped>
/* ... styles ... */
/* 复用之前的样式，不做修改 */
.relation-view {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #121212;
  color: #eee;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.header {
  padding: 12px 24px;
  background: #1e1e1e;
  border-bottom: 1px solid #333;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  z-index: 10;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.back-button {
  align-self: flex-start;
  background: none;
  border: none;
  color: #888;
  cursor: pointer;
  font-size: 12px;
  padding: 0;
  margin-bottom: 4px;
}

.back-button:hover {
  color: #fff;
  text-decoration: underline;
}

.title-info h1 {
  font-size: 20px;
  margin: 0;
  color: #fff;
  font-weight: 600;
}

.subtitle {
  font-size: 12px;
  color: #888;
  margin: 2px 0 0 0;
}

.controls-panel {
  display: flex;
  align-items: center;
  gap: 24px;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.control-label {
  font-size: 12px;
  color: #aaa;
}

.slider-container {
  position: relative;
  width: 140px;
  height: 24px;
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
  top: 10px;
  height: 4px;
  background: linear-gradient(90deg, #667eea, #764ba2);
  border-radius: 2px;
  z-index: 1;
  pointer-events: none;
}

.strength-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  cursor: pointer;
  box-shadow: 0 0 8px rgba(0,0,0,0.5);
  transition: transform 0.1s;
  margin-top: -6px;
}

.strength-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.display-mode-selector {
  display: flex;
  background: #2a2a2a;
  border-radius: 6px;
  padding: 3px;
}

.mode-option {
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  color: #888;
  border-radius: 4px;
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
  overflow-x: hidden;
  scrollbar-width: thin;
  scrollbar-color: #444 #1a1a1a;
}

.timeline-svg {
  display: block;
}

.year-label {
  user-select: none;
  font-family: 'Arial', sans-serif;
}

.genre-label {
  user-select: none;
  letter-spacing: 0.5px;
  text-shadow: 0 2px 4px rgba(0,0,0,0.8);
}

.data-line {
  pointer-events: none;
  transition: opacity 0.3s;
}

.data-point {
  cursor: pointer;
  transition: r 0.2s ease;
}

.data-point:hover {
  r: 6;
  stroke: #fff;
  stroke-width: 2px;
}

.relation-link {
  transition: opacity 0.3s ease, stroke-width 0.3s ease;
  stroke-linecap: round;
  mix-blend-mode: screen;
}

.relation-link.dimmed {
  opacity: 0.05 !important;
  filter: grayscale(100%);
}

.relation-link:hover {
  opacity: 1 !important;
  z-index: 100;
  filter: brightness(1.5);
}

.hotspot-node {
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.hotspot-core {
  cursor: pointer;
  transition: r 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.3s ease;
}

.hotspot-node.dimmed, .hotspot-core.dimmed {
  opacity: 0.1;
}

.hotspot-core:hover {
  stroke: #fff;
  stroke-width: 2px;
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

.link-tooltip {
  pointer-events: none;
  border: 1px solid #555;
  background: rgba(10, 10, 15, 0.95);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  max-height: 400px;
  overflow-y: auto;
  min-width: 300px;
}

.link-tooltip-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.link-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  font-size: 14px;
}

.link-header .arrow {
  color: #888;
}

.link-header .badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  color: #000;
  font-weight: bold;
  margin-left: auto;
}

.link-header .count {
  font-size: 11px;
  color: #888;
  margin-left: 8px;
}

.relations-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
}

.relation-item {
  display: grid;
  grid-template-columns: 35px 1fr 15px 35px 1fr;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  color: #ccc;
}

.relation-item:last-child {
  border-bottom: none;
}

.rel-time {
  color: #666;
  font-variant-numeric: tabular-nums;
}

.rel-song {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
  font-weight: 500;
}

.rel-arrow {
  color: #555;
  text-align: center;
}

.more-relations {
  text-align: center;
  color: #666;
  font-style: italic;
  padding-top: 4px;
  font-size: 11px;
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
  color: #ccc;
}

.relation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: bold;
  margin-bottom: 8px;
}

.tooltip-type {
  display: inline-block;
  padding: 2px 8px;
  background: rgba(255,255,255,0.1);
  border-radius: 4px;
  font-size: 11px;
  margin-bottom: 6px;
  border-left: 3px solid;
}

.legend {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background: rgba(30, 30, 30, 0.9);
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #444;
  z-index: 20;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  max-height: 200px;
  overflow-y: auto;
}

.legend-title {
  font-size: 12px;
  color: #aaa;
  margin-bottom: 8px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.legend-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #ddd;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  box-shadow: 0 0 4px currentColor;
}

.scroll-hint {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0,0,0,0.6);
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  color: #fff;
  pointer-events: none;
  animation: bounce 2s infinite;
}

@keyframes bounce {
  0%, 20%, 50%, 80%, 100% {transform: translate(-50%, 0);}
  40% {transform: translate(-50%, -5px);}
  60% {transform: translate(-50%, -3px);}
}
</style>
