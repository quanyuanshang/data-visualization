
<template>
  <div class="filter-panel">
    <div class="panel-header">
      <h2>探索与筛选</h2>
    </div>
    
    <div class="panel-content">
      <!-- 1. 流派核心筛选 (统一入口) -->
      <div class="filter-section">
        <div class="section-header">
          <label class="filter-label">选择流派 ({{ selectedGenresForTimeline.length }})</label>
          <div class="header-actions">
            <button class="text-btn" @click="selectAllGenres">全选</button>
            <button class="text-btn" @click="clearGenreSelection">清空</button>
          </div>
        </div>
        
        <div class="genre-checkboxes">
          <label 
            v-for="genre in genres" 
            :key="genre"
            class="genre-checkbox"
            :class="{ 'active': selectedGenresForTimeline.includes(genre) }"
          >
            <input 
              type="checkbox" 
              :value="genre"
              v-model="selectedGenresForTimeline"
            />
            <span class="genre-name">{{ genre }}</span>
            <!-- 如果有颜色映射，显示一个小色块 -->
            <span class="color-dot"></span>
          </label>
        </div>
        
        <div class="layout-hint">
          <span v-if="selectedGenresForTimeline.length > 0 && selectedGenresForTimeline.length <= 2">
            <i class="icon">↔</i> 横向视图 (详细对比)
          </span>
          <span v-else>
            <i class="icon">↕</i> 纵向视图 (宏观演变)
          </span>
        </div>
      </div>

      <div class="divider"></div>

      <!-- 2. 音乐人指标筛选 (仅在单选流派时出现) -->
      <div class="artist-filters-container" v-if="isSingleGenreSelected">
        <div class="section-title">
          <h3>{{ selectedGenresForTimeline[0] }} 音乐人筛选</h3>
        </div>

        <div class="filter-section">
          <label class="filter-label">排序指标</label>
          <select 
            v-model="selectedMetric" 
            class="filter-select"
            @change="handleFilterChange"
          >
            <option value="score">综合评分</option>
            <option value="total_works">总作品数</option>
            <option value="notable_rate">成名率</option>
            <option value="notable_works">成名作品数</option>
            <option value="time_span">活跃时长</option>
            <option value="influence_score">影响力分数</option>
            <option value="collaborators_count">合作者数量</option>
          </select>
        </div>

        <div class="filter-section">
          <label class="filter-label">显示前 N 名</label>
          <div class="range-input-group">
            <input 
              type="range" 
              v-model.number="topN" 
              min="10" 
              :max="maxTopN" 
              step="10"
              @change="handleFilterChange"
            />
            <span class="range-value">{{ topN }}</span>
          </div>
        </div>

        <div class="filter-section">
          <button 
            class="apply-button"
            @click="handleApplyArtistFilter"
          >
            更新音乐人视图
          </button>
        </div>
        
        <!-- 当前筛选状态展示 -->
        <div class="filter-info">
          <div class="info-item">
            <span class="info-label">可用音乐人：</span>
            <span class="info-value">{{ currentArtistsCount }} 位</span>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
        <p>👉 勾选<b>单个流派</b>以解锁音乐人深度筛选功能。</p>
        <p v-if="selectedGenresForTimeline.length > 1" class="hint">当前已选 {{ selectedGenresForTimeline.length }} 个流派，显示流派对比模式。</p>
      </div>

      <div class="divider"></div>

      <!-- 3. 全局功能 -->
      <div class="filter-section">
        <button 
          class="apply-button relation-view-button"
          @click="emit('open-relation-view')"
        >
          查看完整关系网络
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

// ==================== Props ====================
const props = defineProps({
  genres: {
    type: Array,
    default: () => []
  },
  currentGenre: {
    type: String,
    default: null
  },
  currentArtistsCount: {
    type: Number,
    default: 0
  },
  isArtistView: {
    type: Boolean,
    default: false
  }
})

// ==================== Emits ====================
const emit = defineEmits(['apply-filter', 'refine-filter', 'timeline-filter-change', 'open-relation-view'])

// ==================== 响应式数据 ====================
const selectedGenresForTimeline = ref([]) // 复选框绑定的数据
const selectedMetric = ref('score')
const topN = ref(100)

// ==================== 计算属性 ====================

/**
 * 是否只选中了一个流派 (触发音乐人筛选的条件)
 */
const isSingleGenreSelected = computed(() => {
  return selectedGenresForTimeline.value.length === 1
})

const maxTopN = computed(() => {
  return props.currentArtistsCount > 0 ? props.currentArtistsCount : 200
})

// ==================== 方法 ====================

/**
 * 监听复选框变化，这是核心驱动逻辑
 */
watch(selectedGenresForTimeline, (newVal) => {
  // 1. 通知父组件更新时间线视图
  emit('timeline-filter-change', newVal)

  // 2. 如果正好选中一个，尝试自动切换到该流派的音乐人视图(或者预备状态)
  if (newVal.length === 1) {
    const genre = newVal[0]
    // 触发一次默认筛选，让父组件加载该流派数据
    emit('apply-filter', {
      genre: genre,
      metric: selectedMetric.value,
      topN: topN.value
    })
  }
}, { deep: true })

function handleFilterChange() {
  // 仅在用户拖动滑块或改下拉框时触发
  if (isSingleGenreSelected.value) {
    // 不立即触发，等点击按钮？或者立即触发？这里选择点击按钮触发以减少闪烁，
    // 但为了响应性，也可以做防抖。这里保持简单，依靠按钮。
  }
}

function handleApplyArtistFilter() {
  if (!isSingleGenreSelected.value) return
  
  const genre = selectedGenresForTimeline.value[0]
  const filter = {
    genre: genre,
    metric: selectedMetric.value,
    topN: topN.value
  }
  
  // 无论当前是否在 artist view，都发送 refine 或 apply
  if (props.isArtistView) {
    emit('refine-filter', { metric: selectedMetric.value, topN: topN.value })
  } else {
    emit('apply-filter', filter)
  }
}

function selectAllGenres() {
  selectedGenresForTimeline.value = [...props.genres]
}

function clearGenreSelection() {
  selectedGenresForTimeline.value = []
}

// 初始化：如果父组件传入了 currentGenre，同步到复选框
watch(() => props.currentGenre, (newGenre) => {
  if (newGenre && !selectedGenresForTimeline.value.includes(newGenre)) {
    // 如果是单选模式切换过来，重置为该流派
    selectedGenresForTimeline.value = [newGenre]
  }
}, { immediate: true })

</script>

<style scoped>
.filter-panel {
  width: 300px;
  height: 100%;
  background: #1e1e1e;
  border-right: 1px solid #333;
  display: flex;
  flex-direction: column;
  color: #eee;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.panel-header {
  padding: 16px 20px;
  background: #252525;
  border-bottom: 1px solid #333;
}

.panel-header h2 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: #fff;
}

.panel-content {
  flex: 1;
  padding: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.filter-section {
  padding: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.filter-label {
  font-size: 13px;
  font-weight: 600;
  color: #aaa;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.text-btn {
  background: none;
  border: none;
  color: #667eea;
  font-size: 12px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}

.text-btn:hover {
  background: rgba(102, 126, 234, 0.1);
}

/* 复选框列表 */
.genre-checkboxes {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 240px;
  overflow-y: auto;
  background: #161616;
  border: 1px solid #333;
  border-radius: 6px;
  padding: 4px;
}

.genre-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}

.genre-checkbox:hover {
  background: #2a2a2a;
}

.genre-checkbox.active {
  background: rgba(102, 126, 234, 0.15);
}

.genre-checkbox input {
  accent-color: #667eea;
}

.genre-name {
  font-size: 13px;
  color: #ccc;
  flex: 1;
}

.genre-checkbox.active .genre-name {
  color: #fff;
  font-weight: 500;
}

.layout-hint {
  margin-top: 10px;
  font-size: 12px;
  color: #888;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #252525;
  padding: 6px;
  border-radius: 4px;
}

.layout-hint .icon {
  margin-right: 6px;
  font-style: normal;
  font-weight: bold;
}

.divider {
  height: 1px;
  background: #333;
  margin: 0 20px;
}

/* 音乐人筛选部分 */
.artist-filters-container {
  background: #252525;
  padding-bottom: 10px;
}

.section-title {
  padding: 15px 20px 5px;
}

.section-title h3 {
  margin: 0;
  font-size: 14px;
  color: #fff;
  border-left: 3px solid #667eea;
  padding-left: 8px;
}

.filter-select {
  width: 100%;
  padding: 8px;
  background: #333;
  border: 1px solid #444;
  color: #eee;
  border-radius: 4px;
  font-size: 13px;
  margin-top: 5px;
}

.range-input-group {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 5px;
}

.range-input-group input {
  flex: 1;
}

.range-value {
  font-size: 13px;
  width: 30px;
  text-align: right;
  color: #fff;
}

.apply-button {
  width: 100%;
  padding: 10px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.2s;
}

.apply-button:hover {
  background: #5a6fd6;
}

.relation-view-button {
  background: #444;
  border: 1px solid #555;
}

.relation-view-button:hover {
  background: #555;
}

.empty-state {
  padding: 30px 20px;
  text-align: center;
  color: #666;
  font-size: 13px;
  line-height: 1.5;
}

.empty-state .hint {
  margin-top: 10px;
  color: #888;
  font-size: 12px;
}

.filter-info {
  padding: 0 20px 15px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #888;
}

.info-value {
  color: #fff;
}
</style>
