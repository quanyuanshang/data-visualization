
<template>
  <div class="timeline-view">
    <div class="timeline-header">
      <div class="header-left">
        <h2>流派时间线发展</h2>
        <span class="subtitle" v-if="filteredLinksCount > 0">
          显示 {{ filteredLinksCount }} 条主要脉络 (聚合自 {{ totalLinksCount }} 条关系)
        </span>
        <span class="mode-badge" :class="isHorizontal ? 'horizontal' : 'vertical'">
          {{ isHorizontal ? '横向对比模式' : '纵向演变模式' }}
        </span>
      </div>

      <!-- 控制面板 -->
      <div class="controls-panel">
        <!-- 强度过滤器 -->
        <div class="control-group" v-if="displayMode !== 'timeline'">
          <span class="control-label">关系阈值</span>
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

        <!-- 显示模式 -->
        <div class="display-mode-selector">
          <label class="mode-option" :class="{ active: displayMode === 'both' }">
            <input type="radio" name="displayMode" value="both" v-model="displayMode" />
            <span>全部</span>
          </label>
          <label class="mode-option" :class="{ active: displayMode === 'timeline' }">
            <input type="radio" name="displayMode" value="timeline" v-model="displayMode" />
            <span>趋势</span>
          </label>
          <label class="mode-option" :class="{ active: displayMode === 'relations' }">
            <input type="radio" name="displayMode" value="relations" v-model="displayMode" />
            <span>关系</span>
          </label>
        </div>
      </div>
    </div>
    
    <div v-if="!timelineData || !genres || genres.length === 0" class="loading-message">
      <p>请选择流派以查看数据...</p>
    </div>
    
    <div v-else class="timeline-container" ref="containerRef">
      <div class="timeline-scroll-wrapper" ref="scrollWrapperRef" @scroll="handleScroll">
        <svg :width="svgWidth" :height="svgHeight" class="timeline-svg" ref="svgRef">
          <defs>
            <!-- 增强的霓虹光晕滤镜 -->
            <filter id="glow-strong" x="-100%" y="-100%" width="300%" height="300%">
              <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
              <feGaussianBlur stdDeviation="2" in="SourceGraphic" result="coloredBlur2"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="coloredBlur2"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="2.5" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
          
          <!-- 时间轴 (根据模式变换位置) -->
          <g class="time-axis">
            <!-- 横向模式：隐藏X轴时间，直接标注在点上 -->
            <g v-if="isHorizontal">
              <line 
                :x1="0" :y1="svgHeight - 40" 
                :x2="svgWidth" :y2="svgHeight - 40" 
                stroke="#333" stroke-width="1" opacity="0.3"
              />
            </g>

            <!-- 纵向模式：时间在左侧Y轴 -->
            <g v-else>
              <line 
                :x1="60" :y1="0" 
                :x2="60" :y2="svgHeight" 
                stroke="#333" stroke-width="1"
              />
              <g v-for="year in visibleYears" :key="year">
                <text
                  :x="50"
                  :y="getTimePos(year) + 4"
                  fill="#888"
                  font-size="11"
                  text-anchor="end"
                >
                  {{ year }}
                </text>
                <!-- 横向网格线 -->
                <line 
                  :x1="60" :y1="getTimePos(year)"
                  :x2="svgWidth" :y2="getTimePos(year)"
                  stroke="#333" stroke-width="1" stroke-dasharray="4,4" opacity="0.1"
                />
              </g>
            </g>
          </g>

          <!-- 流派轨道背景 -->
          <g class="genre-tracks">
             <g
              v-for="(genre, index) in genres"
              :key="`track-${genre}`"
            >
              <!-- 横向模式：横线 -->
              <line v-if="isHorizontal"
                :x1="0" :y1="getGenrePos(index)"
                :x2="svgWidth" :y2="getGenrePos(index)"
                stroke="#333" stroke-width="1" opacity="0.2"
              />
              <!-- 纵向模式：竖线 -->
              <line v-else
                :x1="getGenrePos(index)" :y1="0"
                :x2="getGenrePos(index)" :y2="svgHeight"
                stroke="#333" stroke-width="1" opacity="0.15"
              />
            </g>
          </g>
          
          <!-- 关系连接线 -->
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

           <!-- 关系热点 (在连接点处) -->
          <g class="relation-hotspots" v-if="showRelations">
            <g v-for="(spot, key) in processedRelations.hotspots" :key="`spot-group-${key}`">
              <!-- 中层实心 -->
              <circle
                :cx="spot.x"
                :cy="spot.y"
                :r="spot.r"
                :fill="getGenreColor(spot.genre)"
                stroke-width="0"
                fill-opacity="0.8"
                class="hotspot-node"
                filter="url(#glow)"
                :class="{ 'dimmed': hoveredLink && !isSpotRelatedToLink(spot, hoveredLink) }"
              />
              <!-- 核心高亮 -->
              <circle
                :cx="spot.x"
                :cy="spot.y"
                :r="Math.max(2, spot.r * 0.3)"
                fill="#fff"
                fill-opacity="0.9"
                class="hotspot-core"
                :class="{ 'dimmed': hoveredLink && !isSpotRelatedToLink(spot, hoveredLink) }"
                @mouseenter="showHotspotTooltip($event, spot)"
                @mouseleave="hideRelationTooltip"
              />
            </g>
          </g>

          <!-- 流派心电图数据和标签 -->
          <g class="genre-columns">
            <g
              v-for="(genre, index) in genres"
              :key="genre"
              class="genre-column"
            >
              <!-- 流派标签 -->
              <text
                v-if="isHorizontal"
                :x="20"
                :y="getGenrePos(index) - 15"
                :fill="getGenreColor(genre)"
                font-size="14"
                font-weight="bold"
                text-anchor="start"
              >
                {{ genre }}
              </text>
              <!-- 纵向模式：如果流派很多，旋转标签以防重叠 -->
              <text
                v-else
                :x="getGenrePos(index)"
                :y="30"
                :fill="getGenreColor(genre)"
                :font-size="genres.length > 15 ? 10 : 12"
                font-weight="bold"
                text-anchor="start"
                :transform="`rotate(-45, ${getGenrePos(index)}, 30)`"
              >
                {{ genre }}
              </text>
              
              <!-- 数据线 (Path) -->
              <path v-if="showTimeline"
                :d="getGenrePath(genre, index)"
                :stroke="getGenreColor(genre)"
                stroke-width="1.5"
                fill="none"
                class="data-line"
                filter="url(#glow)"
                opacity="0.8"
              />

              <!-- 数据点 (Points) -->
              <g v-if="showTimeline">
                <g 
                  v-for="point in getMajorPoints(genre)"
                  :key="`${genre}-${point.year}`"
                >
                  <circle
                    :cx="isHorizontal ? getTimePos(point.year) : getGenrePos(index) + getAmplitudeOffset(point.count)"
                    :cy="isHorizontal ? getGenrePos(index) - getAmplitudeOffset(point.count) : getTimePos(point.year)"
                    :r="2"
                    :fill="getGenreColor(genre)"
                    class="data-point-marker"
                    @mouseenter="showTooltip($event, genre, point.year, point.count)"
                    @mouseleave="hideTooltip"
                  />
                  
                  <!-- 时间文字标注 (仅在横向模式显示) -->
                  <text
                    v-if="isHorizontal"
                    :x="getTimePos(point.year)"
                    :y="getGenrePos(index) - getAmplitudeOffset(point.count) - 10"
                    fill="#888"
                    font-size="10"
                    text-anchor="middle"
                    class="point-year-label"
                  >
                    {{ point.year }}
                  </text>
                </g>
              </g>
            </g>
          </g>
        </svg>
      </div>
      
      <!-- 滚动提示 -->
      <div v-if="needsScroll" class="scroll-hint">
        <div class="scroll-arrow">{{ isHorizontal ? '→' : '↓' }}</div>
      </div>
    </div>
    
    <!-- 悬浮提示组件 -->
    <div v-if="tooltip.visible" class="tooltip" :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }">
      <div class="tooltip-content">
        <strong :style="{ color: getGenreColor(tooltip.genre) }">{{ tooltip.genre }}</strong>
        <div class="tooltip-row"><span>年份:</span> {{ tooltip.year }}</div>
        <div class="tooltip-row"><span>作品数:</span> {{ tooltip.count }}</div>
      </div>
    </div>

    <div v-if="relationTooltip.visible" class="tooltip relation-tooltip" :style="{ left: relationTooltip.x + 'px', top: relationTooltip.y + 'px' }">
      <div v-if="relationTooltip.isHotspot" class="tooltip-content">
         <strong :style="{ color: getGenreColor(relationTooltip.genre) }">{{ relationTooltip.genre }} 热点</strong>
         <div class="tooltip-row"><span>时间段:</span> {{ relationTooltip.year }}</div>
         <div class="tooltip-row"><span>活跃度:</span> {{ relationTooltip.intensity }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  timelineData: { type: Object, required: true },
  genreColorMap: { type: Object, required: true },
  selectedGenres: { type: Array, default: () => [] }
})

// ==================== 状态 ====================
const containerRef = ref(null)
const scrollWrapperRef = ref(null)
const svgRef = ref(null)
const svgWidth = ref(1200)
const svgHeight = ref(800)
const hoveredLink = ref(null)
const strengthThreshold = ref(5) // 降低默认阈值以显示更多聚合后的粗线
const displayMode = ref('both')
const containerWidth = ref(1200)

// 聚合时间窗口大小 (年)
const TIME_SEGMENT_SIZE = 15

// Tooltips
const tooltip = ref({ visible: false, x: 0, y: 0, genre: '', year: '', count: 0 })
const relationTooltip = ref({ visible: false, x: 0, y: 0, isHotspot: false })

// ==================== 核心计算属性 ====================

// 1. 决定布局模式：1-2个流派横向展示，否则纵向
const isHorizontal = computed(() => {
  const count = props.selectedGenres ? props.selectedGenres.length : 0
  return count > 0 && count <= 2
})

// 2. 过滤流派
const genres = computed(() => {
  const all = props.timelineData?.genres ?? []
  // 如果没有选中，显示所有流派
  if (!props.selectedGenres || props.selectedGenres.length === 0) return all
  // 如果选中流派，只显示选中的
  return all.filter(g => props.selectedGenres.includes(g))
})

const allYears = computed(() => props.timelineData?.time_range?.all_years ?? [])
const timeRange = computed(() => props.timelineData?.time_range ?? { min: 1975, max: 2040 })
const genreTimelines = computed(() => props.timelineData?.genre_timelines ?? {})

// 3. 可见年份
const visibleYears = computed(() => {
  const totalYears = allYears.value.length
  // 横向模式显示更多年份刻度
  const step = isHorizontal.value ? 2 : 5 
  return allYears.value.filter((y, i) => i % step === 0 || i === 0 || i === totalYears - 1)
})

const showTimeline = computed(() => displayMode.value !== 'relations')
const showRelations = computed(() => displayMode.value !== 'timeline')

// 4. 布局参数
// 压缩尺度：横向40px/年，纵向20px/年
const yearSpacing = computed(() => isHorizontal.value ? 40 : 20) 

// 动态计算轨道宽度/高度
const trackSize = computed(() => {
  if (isHorizontal.value) return 160 
  
  // 纵向模式：强制适应容器宽度，不再设置最小宽度
  const count = genres.value.length
  if (count === 0) return 120
  
  // 容器宽度减去左侧时间轴和右侧内边距
  const leftPadding = 60
  const rightPadding = 40
  const safeContainerWidth = containerWidth.value || 1200
  const availableWidth = Math.max(600, safeContainerWidth) - leftPadding - rightPadding
  
  // 直接均分，不设下限
  return availableWidth / count
})

const needsScroll = computed(() => {
  if (!containerRef.value) return false
  if (isHorizontal.value) return svgWidth.value > containerRef.value.clientWidth
  // 纵向模式下宽度自适应，只有高度（时间）可能需要滚动
  return svgHeight.value > containerRef.value.clientHeight
})

// ==================== 坐标计算核心 ====================

/**
 * 获取时间的坐标位置 (X if Horizontal, Y if Vertical)
 */
function getTimePos(year) {
  const startYear = timeRange.value.min
  const offset = (year - startYear) * yearSpacing.value
  if (isHorizontal.value) {
    return 60 + offset // left padding
  } else {
    return 60 + offset // top padding (header/margin)
  }
}

/**
 * 获取流派轨道的中心坐标 (Y if Horizontal, X if Vertical)
 */
function getGenrePos(index) {
  // 居中显示
  if (isHorizontal.value) {
    return 100 + index * trackSize.value + trackSize.value * 0.5 // top padding + center
  } else {
    return 60 + index * trackSize.value + trackSize.value * 0.5 // left padding + center
  }
}

/**
 * 获取振幅偏移量 (心电图波动)
 */
const maxCount = computed(() => {
  let max = 0
  for (const g of genres.value) {
    const tl = genreTimelines.value[g]
    if (tl?.yearly_counts) Object.values(tl.yearly_counts).forEach(c => { if(c > max) max = c })
  }
  return max || 1
})

function getAmplitudeOffset(count) {
  // 限制最大振幅不超过轨道的一半 (留出边距)
  const maxAmp = trackSize.value * 0.4 
  return (count / maxCount.value) * maxAmp
}

// ==================== 路径生成 ====================

function getGenrePath(genre, index) {
  const points = genreDataPointsMap.value[genre] || []
  if (points.length === 0) return ''

  const line = d3.line()
    .curve(d3.curveMonotoneX) // 默认平滑

  if (isHorizontal.value) {
    // 横向：X=Time, Y=GenreCenter - Amplitude
    const centerY = getGenrePos(index)
    line.x(d => getTimePos(d.year))
        .y(d => centerY - getAmplitudeOffset(d.count))
  } else {
    // 纵向：X=GenreCenter + Amplitude, Y=Time
    const centerX = getGenrePos(index)
    // 使用 monotoneY 适合纵向时间轴
    line.curve(d3.curveMonotoneY)
        .x(d => centerX + getAmplitudeOffset(d.count))
        .y(d => getTimePos(d.year))
  }
  
  return line(points)
}

// ==================== 关系数据处理 ====================

// 1. 颜色映射
const relationTypeColors = {
  'CoverOf': '#ff6b6b',           // 红色
  'DirectlySamples': '#4ecdc4',   // 青色
  'InterpolatesFrom': '#45b7d1',  // 蓝色
  'LyricalReferenceTo': '#96ceb4',// 绿色
  'InStyleOf': '#ffeaa7'          // 黄色
}

const processedRelations = computed(() => {
  const rawRels = props.timelineData?.relations || []
  if (rawRels.length === 0) return { links: [], hotspots: {} }

  // Aggregation Logic: 15年分割
  // 将时间段聚合，大幅减少线条数量
  const bundles = new Map()
  const timeSeg = TIME_SEGMENT_SIZE // 使用全局常量
  
  for (const rel of rawRels) {
    // 过滤：只显示当前可见流派之间的关系
    if (!genres.value.includes(rel.source_genre) || !genres.value.includes(rel.target_genre)) continue
    
    // 计算时间段 (例如 1975-2004, 2005-2034)
    const sSegment = Math.floor(rel.source_year / timeSeg)
    const tSegment = Math.floor(rel.target_year / timeSeg)
    
    // 使用段时间的中心点作为显示位置
    const sYear = sSegment * timeSeg + timeSeg / 2
    const tYear = tSegment * timeSeg + timeSeg / 2
    
    // Key: SourceGenre + TargetGenre + TimeSegments + Type
    const key = `${rel.source_genre}_${sSegment}_${rel.target_genre}_${tSegment}_${rel.relation_type}`
    
    if (!bundles.has(key)) {
      bundles.set(key, { 
        ...rel, 
        sYear: Math.min(Math.max(sYear, timeRange.value.min), timeRange.value.max), // Clamp to visible range
        tYear: Math.min(Math.max(tYear, timeRange.value.min), timeRange.value.max),
        count: 0 
      })
    }
    bundles.get(key).count++
  }

  // 阈值过滤
  const allBundles = Array.from(bundles.values())
  const maxVal = Math.max(...allBundles.map(b => b.count)) || 1
  const threshold = Math.ceil(maxVal * (strengthThreshold.value / 100))
  const filtered = allBundles.filter(b => b.count >= threshold)

  const links = []
  const hotspots = {}

  filtered.forEach(b => {
    const sIdx = genres.value.indexOf(b.source_genre)
    const tIdx = genres.value.indexOf(b.target_genre)
    
    let sx, sy, tx, ty
    
    if (isHorizontal.value) {
      sx = getTimePos(b.sYear)
      sy = getGenrePos(sIdx)
      tx = getTimePos(b.tYear)
      ty = getGenrePos(tIdx)
    } else {
      sx = getGenrePos(sIdx)
      sy = getTimePos(b.sYear)
      tx = getGenrePos(tIdx)
      ty = getTimePos(b.tYear)
    }

    // 生成路径
    let path = ''
    if (isHorizontal.value) {
      const midX = (sx + tx) / 2
      path = `M ${sx} ${sy} C ${midX} ${sy}, ${midX} ${ty}, ${tx} ${ty}`
    } else {
      const midY = (sy + ty) / 2
      // 增加一点曲率控制，让线更自然
      path = `M ${sx} ${sy} C ${sx} ${midY}, ${tx} ${midY}, ${tx} ${ty}`
    }

    // 视觉编码 Visual Encoding - 增强版
    const weight = b.count / maxVal
    
    // B. 粗细 (Thickness) = 1.5 + weight^1.5 * 12
    // 基础1.5px让弱连接可见，最大增量12px让强连接非常醒目
    const strokeWidth = 1.5 + Math.pow(weight, 1.5) * 12
    
    // C. 透明度 (Opacity) = 0.15 + weight^1.2 * 0.85
    // 弱连接更淡，强连接更实
    const opacity = 0.15 + Math.pow(weight, 1.2) * 0.85

    links.push({
      ...b,
      path,
      color: relationTypeColors[b.relation_type] || '#888',
      strokeWidth,
      opacity,
      weight
    })

    // 热点
    const sKey = `${b.source_genre}_${b.sYear}`
    const tKey = `${b.target_genre}_${b.tYear}`
    
    if(!hotspots[sKey]) hotspots[sKey] = { x: sx, y: sy, r: 0, val: 0, genre: b.source_genre, year: b.sYear }
    if(!hotspots[tKey]) hotspots[tKey] = { x: tx, y: ty, r: 0, val: 0, genre: b.target_genre, year: b.tYear }
    
    hotspots[sKey].val += b.count
    hotspots[tKey].val += b.count
  })

  // 计算热点半径 - 稍微增大以匹配更粗的线条
  Object.values(hotspots).forEach(h => {
    h.intensity = h.val
    h.r = 3 + Math.sqrt(h.val) * 1.5
  })
  
  // 排序：让细线在下，粗线在上
  links.sort((a,b) => a.weight - b.weight)

  return { links, hotspots }
})

const filteredLinksCount = computed(() => processedRelations.value.links.length)
const totalLinksCount = computed(() => (props.timelineData?.relations || []).length)

// ==================== 辅助 ====================

const genreDataPointsMap = computed(() => {
  const map = {}
  for (const g of genres.value) {
    const tl = genreTimelines.value[g]
    map[g] = []
    // 即使该流派没有 yearly_counts，也要填充 0 值以保持线条连续（平直线）
    const counts = tl?.yearly_counts || {}
    
    for(let y = timeRange.value.min; y <= timeRange.value.max; y++) {
      const c = counts[y] || 0
      // 关键修改：不再过滤 if (c > 0)
      // 包含所有年份，这样 count=0 时线条会回归基线，形成完整的心电图效果
      map[g].push({ year: y, count: c })
    }
  }
  return map
})

function getMajorPoints(genre) {
  // 对于圆点标记（Tooltip触发点），我们仍然只显示有数据的点
  return (genreDataPointsMap.value[genre] || []).filter(p => p.count > 0)
}

function getGenreColor(genre) {
  return props.genreColorMap[genre] || '#888'
}

function updateDimensions() {
  if (!containerRef.value) return
  
  containerWidth.value = containerRef.value.clientWidth
  const containerH = containerRef.value.clientHeight
  
  const years = timeRange.value.max - timeRange.value.min
  const genreCount = genres.value.length
  
  if (isHorizontal.value) {
    svgWidth.value = Math.max(containerWidth.value, 100 + years * yearSpacing.value)
    svgHeight.value = Math.max(containerH, 150 + genreCount * trackSize.value)
  } else {
    // 纵向模式：强制适应宽度，不产生横向滚动
    svgWidth.value = containerWidth.value
    // 高度随时间增长
    svgHeight.value = Math.max(containerH, 120 + years * yearSpacing.value)
  }
}

function handleScroll() {
  // optional scroll logic
}

// Tooltip Logic
function showTooltip(e, genre, year, count) {
  if(hoveredLink.value) return
  tooltip.value = { visible: true, x: e.clientX+15, y: e.clientY-10, genre, year, count }
}
function hideTooltip() { tooltip.value.visible = false }

function showHotspotTooltip(e, spot) {
  // 修正：使用 +/- timeSeg/2 来计算范围，确保是 15 年跨度而不是 30 年
  const halfSeg = TIME_SEGMENT_SIZE / 2
  const startYear = Math.floor(spot.year - halfSeg)
  const endYear = Math.floor(spot.year + halfSeg)
  
  relationTooltip.value = { 
    visible: true, 
    x: e.clientX+15, 
    y: e.clientY-10, 
    isHotspot: true, 
    genre: spot.genre, 
    year: `${startYear}-${endYear}`, 
    intensity: spot.intensity 
  }
}
function hideRelationTooltip() { relationTooltip.value.visible = false }

function isSpotRelatedToLink(spot, link) {
  if(!link) return false
  return (spot.genre === link.source_genre && Math.abs(spot.year - link.sYear) < 5) ||
         (spot.genre === link.target_genre && Math.abs(spot.year - link.tYear) < 5)
}

// Lifecycle
watch([() => props.selectedGenres, () => props.timelineData], () => {
  nextTick(updateDimensions)
}, { deep: true })

onMounted(() => {
  window.addEventListener('resize', updateDimensions)
  updateDimensions()
})
onBeforeUnmount(() => window.removeEventListener('resize', updateDimensions))

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

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.timeline-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

.subtitle {
  font-size: 12px;
  color: #888;
}

.mode-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  background: #333;
  color: #aaa;
}
.mode-badge.horizontal { color: #667eea; border: 1px solid rgba(102, 126, 234, 0.3); }
.mode-badge.vertical { color: #4ecdc4; border: 1px solid rgba(78, 205, 196, 0.3); }

.controls-panel {
  display: flex;
  align-items: center;
  gap: 20px;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-label {
  font-size: 12px;
  color: #888;
}

.slider-container {
  position: relative;
  width: 100px;
  height: 4px;
  background: #444;
  border-radius: 2px;
  display: flex;
  align-items: center;
}

.strength-slider {
  -webkit-appearance: none;
  width: 100%;
  height: 100%;
  background: transparent;
  position: absolute;
  z-index: 2;
  cursor: pointer;
}
.strength-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #fff;
  cursor: pointer;
  margin-top: -4px; /* Center align */
}

.slider-track {
  height: 100%;
  background: #667eea;
  border-radius: 2px;
  position: absolute;
  left: 0;
  top: 0;
  z-index: 1;
}

.display-mode-selector {
  display: flex;
  background: #333;
  padding: 2px;
  border-radius: 6px;
}

.mode-option {
  padding: 4px 12px;
  font-size: 12px;
  color: #888;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
}
.mode-option:hover { color: #ccc; }
.mode-option.active { background: #555; color: #fff; font-weight: 500; }
.mode-option input { display: none; }

.timeline-container {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: #1a1a1a;
}

.timeline-scroll-wrapper {
  width: 100%;
  height: 100%;
  overflow: auto;
}

.timeline-svg {
  display: block;
}

.loading-message {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-size: 14px;
}

.scroll-hint {
  position: absolute;
  bottom: 20px;
  right: 20px;
  background: rgba(0,0,0,0.6);
  padding: 8px;
  border-radius: 50%;
  pointer-events: none;
  animation: pulse 2s infinite;
}
@keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }
.scroll-arrow { color: white; font-size: 16px; font-weight: bold; }

.relation-link {
  transition: opacity 0.3s, stroke-width 0.3s;
  pointer-events: visibleStroke;
  cursor: pointer;
}
.relation-link.dimmed { opacity: 0.05 !important; }

.hotspot-node {
  transition: r 0.3s;
}
.hotspot-core {
  cursor: pointer;
  transition: r 0.3s;
}
.hotspot-node.dimmed, .hotspot-core.dimmed {
  opacity: 0.05;
}

.tooltip {
  position: fixed;
  pointer-events: none;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.9);
  border: 1px solid #444;
  border-radius: 6px;
  padding: 10px;
  font-size: 12px;
  color: #fff;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  transform: translate(10px, 10px);
}
.tooltip-content strong { display: block; margin-bottom: 4px; font-size: 13px; }
.tooltip-row { display: flex; justify-content: space-between; gap: 12px; color: #ccc; margin-top: 2px; }

/* 滚动条样式 */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #1a1a1a; }
::-webkit-scrollbar-thumb { background: #444; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #555; }

.point-year-label {
  pointer-events: none;
}
.data-point-marker {
  cursor: pointer;
  transition: r 0.2s;
}
.data-point-marker:hover {
  r: 4;
}
</style>
