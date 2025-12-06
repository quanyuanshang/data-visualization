
<template>
  <div class="app-container">
    <!-- 数据加载中提示 -->
    <div v-if="(!genresData || (isSuperstarMode && !superstarData)) && currentView === 'genres'" class="loading">
      <p>正在加载数据...</p>
    </div>
    
    <!-- 主视图：显示26个流派圆圈 + 左侧筛选面板 + 时间线视图 -->
    <div v-if="currentView === 'genres' && genresData" class="genres-view-wrapper">
      <div class="genres-view-container">
        <FilterPanel
          :genres="genresData.genres"
          :is-superstar-mode="isSuperstarMode"
          @apply-filter="handleFilterApply"
          @timeline-filter-change="handleTimelineFilterChange"
          @open-relation-view="handleOpenRelationView"
          @toggle-superstar-mode="handleToggleSuperstarMode"
          @update-superstar-count="handleUpdateSuperstarCount"
        />
        <GenreView 
          :genres-data="currentDisplayData"
          :genre-color-map="genreColorMap"
          :selected-genres="selectedGenresForTimeline"
          @select-genre="handleGenreSelect"
        />
      </div>
      <GenreTimelineView
        v-if="timelineData"
        :timeline-data="timelineData"
        :genre-color-map="genreColorMap"
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
        :is-superstar-mode="isSuperstarMode"
        @apply-filter="handleFilterApply"
        @refine-filter="handleRefineFilter"
        @timeline-filter-change="handleTimelineFilterChange"
        @open-relation-view="handleOpenRelationView"
        @toggle-superstar-mode="handleToggleSuperstarMode"
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
import { ref, onMounted, computed, watch } from 'vue'
import GenreView from './components/GenreView.vue'
import ArtistView from './components/ArtistView.vue'
import TrackView from './components/TrackView.vue'
import FilterPanel from './components/FilterPanel.vue'
import GenreTimelineView from './components/GenreTimelineView.vue'
import RelationView from './components/RelationView.vue'

// ==================== 状态管理 ====================
const currentView = ref('genres')
const selectedGenresForTimeline = ref([])
const selectedGenre = ref(null)
const selectedArtists = ref([])
const selectedArtistsAll = ref([])
const totalArtists = ref(0)
const currentPage = ref(1)
const pageSize = 100
const genresData = ref(null)
const timelineData = ref(null)
const selectedArtist = ref(null)
const trackData = ref(null)
const trackLoading = ref(false)
const trackError = ref('')
const personEvaluations = ref(null)
const currentSortMetric = ref('score')

// 超新星模式相关
const isSuperstarMode = ref(false)
const superstarData = ref(null) // 原始JSON数据
const superstarCountFilter = ref(100) // 默认显示多少个

const palette = [
  '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
  '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
  '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5',
  '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7',
  '#dda15e'
]

const genreColorMap = computed(() => {
  const map = {}
  const list = genresData.value?.genres ?? []
  list.forEach((genre, index) => {
    map[genre] = palette[index % palette.length]
  })
  return map
})

// 计算当前传递给 GenreView 的数据
// 如果是超新星模式，则聚合 superstarData 生成类似 genresData 的结构
const currentDisplayData = computed(() => {
  if (!isSuperstarMode.value) {
    return genresData.value
  }

  if (!superstarData.value || !genresData.value) return null

  // 1. 过滤前N名候选人
  // superstarData is array of objects
  let candidates = [...superstarData.value]
  // sort by predicted_score desc
  candidates.sort((a, b) => (b.metrics?.predicted_score || 0) - (a.metrics?.predicted_score || 0))
  candidates = candidates.slice(0, superstarCountFilter.value)

  // 2. 映射候选人到流派 (需要通过 name 或 ID 从主数据中查找流派)
  // 建立 ID -> Genre 映射
  const artistGenreMap = new Map()
  Object.entries(genresData.value.genres_data).forEach(([genre, data]) => {
    data.artists.forEach(artist => {
      artistGenreMap.set(artist.person_id, genre)
    })
  })

  // 3. 聚合数据
  const genreGroups = {}
  genresData.value.genres.forEach(g => {
    genreGroups[g] = { count: 0, artists: [] }
  })

  candidates.forEach(candidate => {
    const genre = artistGenreMap.get(candidate.id)
    if (genre && genreGroups[genre]) {
      genreGroups[genre].count++
      // 将 candidate 数据 (含 shap_explanation) 这里的 metrics 映射到 artist 字段
      genreGroups[genre].artists.push({
        ...candidate,
        person_id: candidate.id,
        score: candidate.metrics?.predicted_score || 0,
        genre_share: 1, // 假定值，确保显示
        isSuperstar: true // 标记
      })
    }
  })

  return {
    genres: genresData.value.genres,
    genres_data: genreGroups
  }
})

// ==================== 数据加载 ====================
onMounted(async () => {
  currentView.value = 'genres'
  try {
    const response = await fetch('/data/visualization_data.json')
    if (!response.ok) throw new Error('Data file not found')
    genresData.value = await response.json()
    
    try {
      const evalResponse = await fetch('/data/person_evaluations_labeled.json')
      if (evalResponse.ok) personEvaluations.value = await evalResponse.json()
    } catch (e) { console.warn('Eval data failed', e) }
    
    try {
      const timelineResponse = await fetch('/data/genre_timeline_data.json')
      if (timelineResponse.ok) timelineData.value = await timelineResponse.json()
    } catch (e) { console.warn('Timeline data failed', e) }

    // 加载超新星数据
    try {
      const superstarResponse = await fetch('/data/potential_artists_shap_viz.json')
      if (superstarResponse.ok) {
        superstarData.value = await superstarResponse.json()
        console.log('Loaded superstar candidates:', superstarData.value.length)
      }
    } catch (e) { console.warn('Superstar data failed', e) }
    
  } catch (error) {
    console.error('Load failed:', error)
  }
})

// ==================== 事件处理 ====================

// 超新星模式切换
function handleToggleSuperstarMode(isActive) {
  isSuperstarMode.value = isActive
  if (currentView.value === 'artists' || currentView.value === 'tracks') {
    // 如果在详情页切换模式，最好返回主视图以免数据混乱
    handleGoBack() 
  }
}

function handleUpdateSuperstarCount(count) {
  superstarCountFilter.value = count
}

// 1. Timeline Filter Change: 仅更新时间线和高亮，不切换视图
function handleTimelineFilterChange(genres) {
  selectedGenresForTimeline.value = genres
}

// 2. Genre Click (Circle): 选中流派 -> 加载所有音乐人 -> 切换视图
function handleGenreSelect(genre) {
  if (!genresData.value) return
  resetTrackState()
  selectedGenresForTimeline.value = [genre]
  
  // 这里的逻辑需要区分普通模式和超新星模式
  if (isSuperstarMode.value) {
    loadSuperstarsForGenre(genre)
  } else {
    loadAllArtistsForGenre(genre, 'score')
  }
}

// 3. Filter Apply Button: 只有点击按钮才切换视图
function handleFilterApply(filter) {
  if (!filter || !filter.genre) return
  resetTrackState()
  currentSortMetric.value = filter.metric || 'score'
  
  if (isSuperstarMode.value) {
     loadSuperstarsForGenre(filter.genre)
  } else {
     applyFilterToGenre(filter.genre, filter.metric, filter.topN)
  }
}

// 4. Refine Filter (in Artist View)
function handleRefineFilter(filter) {
  if (!filter || !selectedArtistsAll.value.length) return
  resetTrackState()
  currentSortMetric.value = filter.metric || 'score'
  
  let refined = [...selectedArtistsAll.value]
  refined.sort((a, b) => (b[filter.metric] ?? 0) - (a[filter.metric] ?? 0))
  refined = refined.slice(0, filter.topN)
  
  selectedArtistsAll.value = refined
  totalArtists.value = refined.length
  currentPage.value = 1
  selectedArtists.value = refined.slice(0, pageSize)
}

// 逻辑核心：加载流派数据 (普通模式)
function loadAllArtistsForGenre(genre, metric = 'score') {
  const genreData = genresData.value.genres_data[genre]
  if (!genreData || !genreData.artists) return

  let filtered = (genreData.artists || []).filter(a => (a.genre_share ?? 0) >= 0.3)
  
  if (personEvaluations.value) {
    const evalMap = new Map(personEvaluations.value.map(e => [e.person_id, e]))
    filtered = filtered.map(artist => {
      const evaluation = evalMap.get(artist.person_id)
      return evaluation ? { ...artist, ...evaluation } : artist
    })
  }
  
  filtered.sort((a, b) => (b[metric] ?? 0) - (a[metric] ?? 0))
  
  selectedArtistsAll.value = filtered
  totalArtists.value = filtered.length
  currentPage.value = 1
  selectedArtists.value = filtered.slice(0, pageSize)
  selectedGenre.value = genre
  currentSortMetric.value = metric
  currentView.value = 'artists'
}

// 逻辑核心：加载流派数据 (超新星模式)
function loadSuperstarsForGenre(genre) {
  // 从 computed 属性 currentDisplayData 获取已经聚合好的数据
  const genreGroup = currentDisplayData.value.genres_data[genre]
  if (!genreGroup || !genreGroup.artists) {
    selectedArtistsAll.value = []
    totalArtists.value = 0
    selectedArtists.value = []
  } else {
    let artists = genreGroup.artists.map(artist => ({
      ...artist,
      person_id: artist.person_id ?? artist.id
    }))
    // 超新星按预测分排序
    artists.sort((a, b) => b.score - a.score)
    
    selectedArtistsAll.value = artists
    totalArtists.value = artists.length
    currentPage.value = 1
    selectedArtists.value = artists.slice(0, pageSize)
  }
  
  selectedGenre.value = genre
  currentSortMetric.value = 'score' // 这里的 score 实际上是 predicted_score
  currentView.value = 'artists'
}

function applyFilterToGenre(genre, metric, topN) {
   loadAllArtistsForGenre(genre, metric)
   if(selectedArtistsAll.value.length > topN) {
      selectedArtistsAll.value = selectedArtistsAll.value.slice(0, topN)
      totalArtists.value = selectedArtistsAll.value.length
      selectedArtists.value = selectedArtistsAll.value.slice(0, pageSize)
   }
}

function handlePageChange(page) {
  if (page < 1) return
  const maxPage = Math.max(1, Math.ceil(totalArtists.value / pageSize))
  if (page > maxPage) return
  currentPage.value = page
  const start = (page - 1) * pageSize
  selectedArtists.value = selectedArtistsAll.value.slice(start, start + pageSize)
}

function handleGoBack() {
  currentView.value = 'genres'
  selectedGenre.value = null
}

// View Tracks / Level 3
async function handleViewTracks(artist) {
  if (!artist) return
  const artistId = artist.person_id ?? artist.id
  if (!artistId) return
  selectedArtist.value = {
    id: artistId,
    name: artist.name,
    stage_name: artist.stage_name,
    score: artist.score,
    genre: selectedGenre.value,
    // 传递超新星特有数据
    isSuperstar: artist.isSuperstar,
    shap_explanation: artist.shap_explanation,
    metrics: artist.metrics
  }
  currentView.value = 'tracks'
  await fetchTrackData(artistId)
}

async function fetchTrackData(personId) {
  trackLoading.value = true
  trackError.value = ''
  trackData.value = null
  try {
    const response = await fetch(`/data/person_tracks/${personId}.json`)
    if (!response.ok) throw new Error('Track data not found')
    trackData.value = await response.json()
  } catch (e) {
    trackError.value = e.message
  } finally {
    trackLoading.value = false
  }
}

function handleTrackGoBack() {
  currentView.value = 'artists'
}

function resetTrackState() {
  selectedArtist.value = null
  trackData.value = null
  trackError.value = ''
}

function handleOpenRelationView() {
  currentView.value = 'relations'
}
function handleRelationViewGoBack() {
  currentView.value = 'genres'
}
function reloadTrackData() {
  if (selectedArtist.value?.id) fetchTrackData(selectedArtist.value.id)
}

</script>

<style scoped>
.app-container { width: 100%; height: 100%; overflow: hidden; }
.genres-view-wrapper { width: 100%; height: 100%; display: flex; flex-direction: column; }
.genres-view-container { width: 100%; height: 65%; display: flex; flex-direction: row; flex-shrink: 0; }
.timeline-view-container { width: 100%; height: 35%; flex-shrink: 0; border-top: 2px solid #333; overflow: hidden; }
.artists-view-container { width: 100%; height: 100%; display: flex; flex-direction: row; }
.loading { display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; font-size: 18px; color: #666; background: #f5f5f5; }
.relation-view-wrapper, .track-view-wrapper { width: 100%; height: 100%; position: relative; }
.error { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; width: 100%; height: 100%; color: #fff; background: #d63031; }
.error-actions { display: flex; gap: 12px; }
.error-actions button { padding: 8px 18px; border: none; border-radius: 6px; cursor: pointer; background: #fff; color: #d63031; }
</style>