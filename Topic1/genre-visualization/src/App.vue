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
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import GenreView from './components/GenreView.vue'
import ArtistView from './components/ArtistView.vue'

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
  console.log('[App] 返回到流派视图')
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
</style>

