<template>
  <div class="app-container">
    <!-- 数据加载中提示 -->
    <div v-if="!genresData && currentView === 'genres'" class="loading">
      <p>正在加载数据...</p>
    </div>
    
    <!-- 主视图：显示26个流派圆圈 + 左侧筛选面板 + 时间线视图 -->
    <div v-if="currentView === 'genres' && genresData" class="genres-view-wrapper">
      <div class="genres-view-container">
        <FilterPanel
          :genres="genresData.genres"
          @apply-filter="handleFilterApply"
          @timeline-filter-change="handleTimelineFilterChange"
          @open-relation-view="handleOpenRelationView"
        />
        <GenreView 
          :genres-data="genresData"
          :genre-color-map="genreColorMap"
          @select-genre="handleGenreSelect"
        />
      </div>
      <GenreTimelineView
        v-if="timelineData"
        :timeline-data="timelineData"
        :genre-color-map="genreColorMap"
        :expand-ratio="0"
        :selected-genres="selectedGenresForTimeline"
        class="timeline-view-container"
      />
    </div>
    
    <!-- 第二层视图：显示选中流派的音乐人 + 左侧筛选面板 -->
    <div v-if="currentView === 'artists'" class="artists-view-container">
      <FilterPanel
        :genres="genresData?.genres ?? []"
        :current-genre="selectedGenre"
        :current-artists-count="selectedArtistsAll.length"
        :is-artist-view="true"
        @apply-filter="handleFilterApply"
        @refine-filter="handleRefineFilter"
      />
      <ArtistView 
        :genre="selectedGenre"
        :artists="selectedArtists"
        :total-artists="totalArtists"
        :current-page="currentPage"
        :page-size="pageSize"
        :all-genres="genresData?.genres ?? []"
        :sort-metric="currentSortMetric"
        :timeline-data="timelineData"
        :genre-color-map="genreColorMap"
        @go-back="handleGoBack"
        @page-change="handlePageChange"
        @view-tracks="handleViewTracks"
      />
    </div>

    <!-- 关系视图：显示流派之间的关系网络 -->
    <div v-if="currentView === 'relations'" class="relation-view-wrapper">
      <RelationView
        :timeline-data="timelineData"
        :genre-color-map="genreColorMap"
        :selected-genres="selectedGenresForTimeline"
        @go-back="handleRelationViewGoBack"
      />
    </div>

    <!-- 第三层视图：显示音乐人的单曲网络 -->
    <div v-if="currentView === 'tracks'" class="track-view-wrapper">
      <div v-if="trackLoading" class="loading">
        <p>正在加载该音乐人的单曲网络...</p>
      </div>
      <div v-else-if="trackError" class="error">
        <p>单曲数据加载失败：{{ trackError }}</p>
        <div class="error-actions">
          <button @click="reloadTrackData">重试</button>
          <button @click="handleTrackGoBack">返回上一层</button>
        </div>
      </div>
      <TrackView
        v-else
        :artist="selectedArtist"
        :nodes="trackData?.nodes ?? []"
        :links="trackData?.links ?? []"
        :genre-color-map="genreColorMap"
        @go-back="handleTrackGoBack"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import GenreView from './components/GenreView.vue'
import ArtistView from './components/ArtistView.vue'
import TrackView from './components/TrackView.vue'
import FilterPanel from './components/FilterPanel.vue'
import GenreTimelineView from './components/GenreTimelineView.vue'
import RelationView from './components/RelationView.vue'

// ==================== 状态管理 ====================
// 当前视图状态：'genres' 表示流派视图，'artists' 表示音乐人视图，'relations' 表示关系视图
// 默认显示流派圆圈视图，确保页面打开时显示正确的视图
const currentView = ref('genres')
// 时间线视图的流派筛选
const selectedGenresForTimeline = ref([])
// 选中的流派名称
const selectedGenre = ref(null)
// 当前页展示的音乐人列表
const selectedArtists = ref([])
// 当前流派的全部音乐人（满足筛选条件）
const selectedArtistsAll = ref([])
// 当前流派音乐人总数
const totalArtists = ref(0)
// 分页信息
const currentPage = ref(1)
const pageSize = 100
// 所有流派的数据
const genresData = ref(null)
// 时间线数据（用于时间线视图）
const timelineData = ref(null)
// 选中的音乐人信息（第三层视图使用）
const selectedArtist = ref(null)
// 音乐人单曲网络
const trackData = ref(null)
const trackLoading = ref(false)
const trackError = ref('')
// 所有音乐人评估数据（用于筛选）
const personEvaluations = ref(null)
// 当前排序指标（用于 ArtistView 的半径计算）
const currentSortMetric = ref('score')

// 与 GenreView / ArtistView 保持一致的颜色序列
const palette = [
  '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
  '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
  '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5',
  '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7',
  '#dda15e'
]

const genreColorMap = computed(() => {
  // 生成一个 {genre: color} 映射，让所有视图使用同一套颜色
  const map = {}
  const list = genresData.value?.genres ?? []
  list.forEach((genre, index) => {
    map[genre] = palette[index % palette.length]
  })
  return map
})

// ==================== 数据加载 ====================
/**
 * 加载可视化数据
 * 从 data/visualization_data.json 加载流派和音乐人数据
 * 从 data/person_evaluations_labeled.json 加载所有音乐人的评估数据（用于筛选）
 */
onMounted(async () => {
  // 确保页面初始化时显示流派视图
  currentView.value = 'genres'
  console.log('[App] 页面初始化，设置视图为流派视图')
  
  try {
    // 加载流派数据
    const response = await fetch('/data/visualization_data.json')
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: 数据文件未找到，请确保文件在 public/data/ 目录下`)
    }
    const data = await response.json()
    genresData.value = data
    console.log('[App] 流派数据加载成功，流派数量:', data.genres.length)
    
    // 加载音乐人评估数据（用于筛选功能）
    try {
      const evalResponse = await fetch('/data/person_evaluations_labeled.json')
      if (evalResponse.ok) {
        const evalData = await evalResponse.json()
        personEvaluations.value = evalData
        console.log('[App] 音乐人评估数据加载成功，音乐人数量:', evalData.length)
      } else {
        console.warn('[App] 音乐人评估数据加载失败，筛选功能可能不可用')
      }
    } catch (evalError) {
      console.warn('[App] 音乐人评估数据加载失败:', evalError)
    }
    
    // 加载时间线数据（用于时间线视图）
    try {
      const timelineResponse = await fetch('/data/genre_timeline_data.json')
      if (timelineResponse.ok) {
        const timelineDataJson = await timelineResponse.json()
        timelineData.value = timelineDataJson
        console.log('[App] 时间线数据加载成功，流派数量:', timelineDataJson.genres?.length ?? 0)
      } else {
        console.warn('[App] 时间线数据加载失败，时间线视图可能不可用')
      }
    } catch (timelineError) {
      console.warn('[App] 时间线数据加载失败:', timelineError)
    }
  } catch (error) {
    console.error('[App] 数据加载失败:', error)
    alert('数据加载失败！\n\n请确保以下文件存在：\ngenre-visualization/public/data/visualization_data.json\n\n如果文件不存在，请从项目根目录的 data/ 目录复制该文件。\n\n错误信息: ' + error.message)
  }
})

// ==================== 事件处理 ====================
/**
 * 处理流派选择事件（从流派圆圈点击）
 * 显示所有符合条件的音乐人，支持翻页查看全部
 * @param {string} genre - 选中的流派名称
 */
function handleGenreSelect(genre) {
  if (!genresData.value) return
  // 切换流派前，先清空潜在的第三层状态
  resetTrackState()
  
  const genreData = genresData.value.genres_data[genre]
  if (!genreData || !genreData.artists) {
    console.warn(`[App] 流派 ${genre} 没有音乐人数据`)
    return
  }
  
  // 加载所有符合条件的音乐人（genre_share >= 0.3），按 score 排序，不限制数量
  loadAllArtistsForGenre(genre, 'score')
}

/**
 * 处理筛选面板的筛选应用事件（初始筛选：从流派选择）
 * @param {Object} filter - 筛选条件 { genre, metric, topN }
 */
function handleFilterApply(filter) {
  if (!filter || !filter.genre) return
  
  resetTrackState()
  currentSortMetric.value = filter.metric || 'score'
  applyFilterToGenre(filter.genre, filter.metric, filter.topN)
}

/**
 * 处理筛选面板的精炼筛选事件（二次筛选：在当前音乐人列表中进一步筛选）
 * @param {Object} filter - 筛选条件 { metric, topN }
 */
function handleRefineFilter(filter) {
  if (!filter || !selectedArtistsAll.value || selectedArtistsAll.value.length === 0) return
  
  resetTrackState()
  currentSortMetric.value = filter.metric || 'score'
  
  // 在当前音乐人列表中进行二次筛选
  let refined = [...selectedArtistsAll.value]
  
  // 根据选定的指标重新排序
  refined.sort((a, b) => {
    const aValue = a[filter.metric] ?? 0
    const bValue = b[filter.metric] ?? 0
    return bValue - aValue // 降序排列
  })
  
  // 取前 topN 名
  refined = refined.slice(0, filter.topN)
  
  selectedArtistsAll.value = refined
  totalArtists.value = refined.length
  currentPage.value = 1
  selectedArtists.value = refined.slice(0, pageSize)
  
  console.log(`[App] 二次筛选完成，指标: ${filter.metric}, 显示前 ${filter.topN} 名，结果: ${refined.length} 位音乐人`)
}

/**
 * 加载指定流派的所有符合条件的音乐人（用于点击流派圆圈的场景）
 * 不限制数量，支持翻页查看全部
 * @param {string} genre - 流派名称
 * @param {string} metric - 排序指标
 */
function loadAllArtistsForGenre(genre, metric = 'score') {
  if (!genresData.value) return
  
  const genreData = genresData.value.genres_data[genre]
  if (!genreData || !genreData.artists) {
    console.warn(`[App] 流派 ${genre} 没有音乐人数据`)
    return
  }
  
  // 基础过滤：genre_share >= 0.3
  let filtered = (genreData.artists || [])
    .filter(artist => (artist.genre_share ?? 0) >= 0.3)
  
  // 如果加载了评估数据，可以基于评估数据进行更精确的筛选和排序
  if (personEvaluations.value) {
    // 创建 person_id 到评估数据的映射
    const evalMap = new Map()
    personEvaluations.value.forEach(evaluation => {
      evalMap.set(evaluation.person_id, evaluation)
    })
    
    // 为每个音乐人补充评估数据
    filtered = filtered.map(artist => {
      const evaluation = evalMap.get(artist.person_id)
      if (evaluation) {
        // 合并评估数据
        return {
          ...artist,
          ...evaluation,
          // 确保使用评估数据中的指标值
          score: evaluation.score ?? artist.score ?? 0,
          total_works: evaluation.total_works ?? 0,
          notable_rate: evaluation.notable_rate ?? 0,
          notable_works: evaluation.notable_works ?? 0,
          time_span: evaluation.time_span ?? 0,
          influence_score: evaluation.influence_score ?? 0,
          collaborators_count: evaluation.collaborators_count ?? 0,
          record_labels_count: evaluation.record_labels_count ?? 0,
          role_count: evaluation.role_count ?? 0
        }
      }
      return artist
    })
  }
  
  // 根据选定的指标排序
  filtered.sort((a, b) => {
    const aValue = a[metric] ?? 0
    const bValue = b[metric] ?? 0
    return bValue - aValue // 降序排列
  })
  
  // 不限制数量，保留所有符合条件的音乐人
  selectedArtistsAll.value = filtered
  totalArtists.value = filtered.length
  currentPage.value = 1
  selectedArtists.value = filtered.slice(0, pageSize)
  selectedGenre.value = genre
  currentSortMetric.value = metric
  currentView.value = 'artists'
  
  console.log(`[App] 加载流派所有音乐人，流派: ${genre}, 指标: ${metric}, 总数: ${filtered.length} 位音乐人，支持翻页查看`)
}

/**
 * 应用筛选条件到指定流派（用于筛选面板的筛选功能）
 * 会限制显示数量为 topN
 * @param {string} genre - 流派名称
 * @param {string} metric - 排序指标
 * @param {number} topN - 显示前 N 名
 */
function applyFilterToGenre(genre, metric = 'score', topN = 100) {
  if (!genresData.value) return
  
  const genreData = genresData.value.genres_data[genre]
  if (!genreData || !genreData.artists) {
    console.warn(`[App] 流派 ${genre} 没有音乐人数据`)
    return
  }
  
  // 基础过滤：genre_share >= 0.3
  let filtered = (genreData.artists || [])
    .filter(artist => (artist.genre_share ?? 0) >= 0.3)
  
  // 如果加载了评估数据，可以基于评估数据进行更精确的筛选和排序
  if (personEvaluations.value) {
    // 创建 person_id 到评估数据的映射
    const evalMap = new Map()
    personEvaluations.value.forEach(evaluation => {
      evalMap.set(evaluation.person_id, evaluation)
    })
    
    // 为每个音乐人补充评估数据
    filtered = filtered.map(artist => {
      const evaluation = evalMap.get(artist.person_id)
      if (evaluation) {
        // 合并评估数据
        return {
          ...artist,
          ...evaluation,
          // 确保使用评估数据中的指标值
          score: evaluation.score ?? artist.score ?? 0,
          total_works: evaluation.total_works ?? 0,
          notable_rate: evaluation.notable_rate ?? 0,
          notable_works: evaluation.notable_works ?? 0,
          time_span: evaluation.time_span ?? 0,
          influence_score: evaluation.influence_score ?? 0,
          collaborators_count: evaluation.collaborators_count ?? 0,
          record_labels_count: evaluation.record_labels_count ?? 0,
          role_count: evaluation.role_count ?? 0
        }
      }
      return artist
    })
  }
  
  // 根据选定的指标排序
  filtered.sort((a, b) => {
    const aValue = a[metric] ?? 0
    const bValue = b[metric] ?? 0
    return bValue - aValue // 降序排列
  })
  
  // 取前 topN 名（筛选面板的筛选功能会限制数量）
  filtered = filtered.slice(0, topN)
  
  selectedArtistsAll.value = filtered
  totalArtists.value = filtered.length
  currentPage.value = 1
  selectedArtists.value = filtered.slice(0, pageSize)
  selectedGenre.value = genre
  currentSortMetric.value = metric
  currentView.value = 'artists'
  
  console.log(`[App] 应用筛选，流派: ${genre}, 指标: ${metric}, 显示前 ${topN} 名，结果: ${filtered.length} 位音乐人`)
}

/**
 * 处理分页变化
 * @param {number} page - 新的页码
 */
function handlePageChange(page) {
  if (page < 1) return
  const maxPage = Math.max(1, Math.ceil(totalArtists.value / pageSize))
  if (page > maxPage) return
  currentPage.value = page
  const start = (page - 1) * pageSize
  selectedArtists.value = selectedArtistsAll.value.slice(start, start + pageSize)
  console.log(`[App] 切换到第 ${page} 页，当前展示 ${selectedArtists.value.length} 位音乐人`)
}

/**
 * 处理返回按钮点击事件
 * 从音乐人视图返回到流派视图
 */
function handleGoBack() {
  currentView.value = 'genres'
  selectedGenre.value = null
  selectedArtists.value = []
  selectedArtistsAll.value = []
  totalArtists.value = 0
  currentPage.value = 1
  resetTrackState()
  console.log('[App] 返回到流派视图')
}

/**
 * 处理音乐人点击事件，加载第三层视图
 */
async function handleViewTracks(artist) {
  if (!artist || !artist.person_id) {
    console.warn('[App] 无法识别音乐人信息，取消加载单曲视图')
    return
  }

  // 保存基础信息（得分、流派等），文件加载后再补充 name/stage_name
  selectedArtist.value = {
    id: artist.person_id,
    name: artist.name,
    stage_name: artist.stage_name ?? null,
    score: artist.score ?? null,
    genre: selectedGenre.value
  }
  currentView.value = 'tracks'
  await fetchTrackData(artist.person_id)
}

async function fetchTrackData(personId) {
  if (!personId) return
  trackLoading.value = true
  trackError.value = ''
  trackData.value = null

  try {
    // 第三层数据按 person_id 切片存放
    const response = await fetch(`/data/person_tracks/${personId}.json`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    const data = await response.json()
    trackData.value = data
    if (data?.name) {
      selectedArtist.value = {
        ...selectedArtist.value,
        name: data.name ?? selectedArtist.value?.name,
        stage_name: data.stage_name ?? selectedArtist.value?.stage_name
      }
    }
    console.log('[App] 成功加载单曲网络，节点数:', data?.nodes?.length ?? 0)
  } catch (error) {
    console.error('[App] 单曲数据加载失败:', error)
    trackError.value = error.message || '未知错误'
  } finally {
    trackLoading.value = false
  }
}

function reloadTrackData() {
  if (selectedArtist.value?.id) {
    fetchTrackData(selectedArtist.value.id)
  }
}

function handleTrackGoBack() {
  // 返回音乐人层级，保留列表页状态
  currentView.value = 'artists'
}

function resetTrackState() {
  // 清空第三层所有状态，避免旧数据残留
  selectedArtist.value = null
  trackData.value = null
  trackError.value = ''
  trackLoading.value = false
}

// ==================== 时间线视图筛选功能 ====================
/**
 * 处理时间线视图的流派筛选变化
 */
function handleTimelineFilterChange(selectedGenres) {
  selectedGenresForTimeline.value = selectedGenres
  console.log('[App] 时间线视图流派筛选更新:', selectedGenres)
}

/**
 * 打开关系视图
 */
function handleOpenRelationView() {
  currentView.value = 'relations'
  console.log('[App] 打开关系视图')
}

/**
 * 从关系视图返回
 */
function handleRelationViewGoBack() {
  currentView.value = 'genres'
  console.log('[App] 从关系视图返回')
}
</script>

<style scoped>
.app-container {
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.genres-view-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
}

.genres-view-container {
  width: 100%;
  height: 65%;
  display: flex;
  flex-direction: row;
  flex-shrink: 0;
}

.timeline-view-container {
  width: 100%;
  height: 35%;
  flex-shrink: 0;
  border-top: 2px solid #333;
  overflow: hidden;
}

.artists-view-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: row;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  font-size: 18px;
  color: #666;
  background: #f5f5f5;
}

.relation-view-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
}

.track-view-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
}

.error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  width: 100%;
  height: 100%;
  color: #fff;
  background: linear-gradient(135deg, rgba(220, 53, 69, 0.8), rgba(214, 48, 49, 0.9));
}

.error-actions {
  display: flex;
  gap: 12px;
}

.error-actions button {
  padding: 8px 18px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.85);
  color: #d63031;
  transition: all 0.2s ease;
}

.error-actions button:hover {
  transform: translateY(-1px);
  background: #fff;
}
</style>

