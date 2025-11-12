<template>
  <div class="app-container">
    <!-- 数据加载中提示 -->
    <div v-if="!genresData && currentView === 'genres'" class="loading">
      <p>正在加载数据...</p>
    </div>
    
    <!-- 主视图：显示26个流派圆圈 -->
    <GenreView 
      v-if="currentView === 'genres' && genresData"
      :genres-data="genresData"
      @select-genre="handleGenreSelect"
    />
    
    <!-- 第二层视图：显示选中流派的音乐人 -->
    <ArtistView 
      v-if="currentView === 'artists'"
      :genre="selectedGenre"
      :artists="selectedArtists"
      :total-artists="totalArtists"
      :current-page="currentPage"
      :page-size="pageSize"
      :all-genres="genresData?.genres ?? []"
      @go-back="handleGoBack"
      @page-change="handlePageChange"
      @view-tracks="handleViewTracks"
    />

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

// ==================== 状态管理 ====================
// 当前视图状态：'genres' 表示流派视图，'artists' 表示音乐人视图
const currentView = ref('genres')
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
// 选中的音乐人信息（第三层视图使用）
const selectedArtist = ref(null)
// 音乐人单曲网络
const trackData = ref(null)
const trackLoading = ref(false)
const trackError = ref('')

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
 */
onMounted(async () => {
  try {
    // 从 public/data/ 目录加载数据（Vite 会自动处理 public 目录下的文件）
    // 如果文件不在 public 目录，请将 data/visualization_data.json 复制到 genre-visualization/public/data/ 目录
    const response = await fetch('/data/visualization_data.json')
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: 数据文件未找到，请确保文件在 public/data/ 目录下`)
    }
    const data = await response.json()
    genresData.value = data
    console.log('[App] 数据加载成功，流派数量:', data.genres.length)
  } catch (error) {
    console.error('[App] 数据加载失败:', error)
    alert('数据加载失败！\n\n请确保以下文件存在：\ngenre-visualization/public/data/visualization_data.json\n\n如果文件不存在，请从项目根目录的 data/ 目录复制该文件。\n\n错误信息: ' + error.message)
  }
})

// ==================== 事件处理 ====================
/**
 * 处理流派选择事件
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
  
  // 过滤出 genre_share >= 0.3 的音乐人，并按分数从高到低排序
  const filtered = (genreData.artists || [])
    .filter(artist => (artist.genre_share ?? 0) >= 0.3)
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
  
  selectedArtistsAll.value = filtered
  totalArtists.value = filtered.length
  currentPage.value = 1
  selectedArtists.value = filtered.slice(0, pageSize)
  selectedGenre.value = genre
  currentView.value = 'artists'
  
  console.log(`[App] 切换到音乐人视图，流派: ${genre}, 音乐人总数: ${totalArtists.value}`)
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
</script>

<style scoped>
.app-container {
  width: 100%;
  height: 100%;
  overflow: hidden;
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

