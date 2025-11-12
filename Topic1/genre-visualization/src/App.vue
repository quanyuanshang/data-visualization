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
      @go-back="handleGoBack"
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
// 选中流派的音乐人列表
const selectedArtists = ref([])
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
  
  // 获取该流派的音乐人数据（最多50名）
  const genreData = genresData.value.genres_data[genre]
  if (!genreData || !genreData.artists) {
    console.warn(`[App] 流派 ${genre} 没有音乐人数据`)
    return
  }
  
  // 只取前50名（数据已经预处理过，但这里再确认一下）
  selectedArtists.value = genreData.artists.slice(0, 50)
  selectedGenre.value = genre
  currentView.value = 'artists'
  
  console.log(`[App] 切换到音乐人视图，流派: ${genre}, 音乐人数量: ${selectedArtists.value.length}`)
}

/**
 * 处理返回按钮点击事件
 * 从音乐人视图返回到流派视图
 */
function handleGoBack() {
  currentView.value = 'genres'
  selectedGenre.value = null
  selectedArtists.value = []
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

