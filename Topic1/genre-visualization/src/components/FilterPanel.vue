
<template>
  <div class="filter-panel">
    <div class="panel-header">
      <h2>探索与筛选</h2>
    </div>
    
    <div class="panel-content">
      
      <!-- 0. 超新星模式切换 (New Feature) -->
      <div class="filter-section superstar-section">
         <div class="section-header">
            <label class="filter-label" style="color: #ffd700;">★ 音乐超新星</label>
            <label class="switch">
              <input type="checkbox" :checked="isSuperstarMode" @change="toggleSuperstar">
              <span class="slider round"></span>
            </label>
         </div>
         
         <div v-if="isSuperstarMode" class="superstar-controls">
             <label class="filter-label-small">显示前 N 名候选人</label>
             <div class="range-input-group">
                <input 
                  type="range" 
                  v-model.number="superstarCount" 
                  min="10" 
                  max="1000" 
                  step="10"
                  @input="emitSuperstarCount"
                />
                <span class="range-value">{{ superstarCount }}</span>
              </div>
              <p class="hint-text">
                基于AI模型预测具有高潜力的未来之星。图表将显示他们在各流派的分布。
              </p>
         </div>
      </div>

      <div class="divider"></div>

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
          <h3>{{ selectedGenresForTimeline[0] }} {{ isSuperstarMode ? '超新星列表' : '音乐人筛选' }}</h3>
        </div>

        <!-- 普通模式下显示筛选器，超新星模式下大部分筛选器不适用，只显示更新按钮 -->
        <div v-if="!isSuperstarMode">
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
        </div>
        
        <div class="filter-section">
          <button 
            class="apply-button"
            :class="{ 'superstar-btn': isSuperstarMode }"
            @click="handleApplyArtistFilter"
          >
            {{ isSuperstarMode ? '查看超新星详情' : '更新音乐人视图' }}
          </button>
        </div>
        
        <!-- 当前筛选状态展示 -->
        <div class="filter-info">
          <div class="info-item">
            <span class="info-label">可用人数：</span>
            <span class="info-value">{{ currentArtistsCount }} 位</span>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
        <p>👉 勾选<b>单个流派</b>并点击“更新”以查看该流派下的详细{{ isSuperstarMode ? '超新星' : '音乐人' }}列表。</p>
        <p v-if="selectedGenresForTimeline.length > 1" class="hint">当前已选 {{ selectedGenresForTimeline.length }} 个流派，下方为流派对比模式。</p>
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
  },
  isSuperstarMode: {
    type: Boolean,
    default: false
  }
})

// ==================== Emits ====================
const emit = defineEmits([
  'apply-filter', 'refine-filter', 'timeline-filter-change', 'open-relation-view',
  'toggle-superstar-mode', 'update-superstar-count'
])

// ==================== 响应式数据 ====================
const selectedGenresForTimeline = ref([]) // 复选框绑定的数据
const selectedMetric = ref('score')
const topN = ref(100)
const superstarCount = ref(100)

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

function toggleSuperstar(e) {
  emit('toggle-superstar-mode', e.target.checked)
}

function emitSuperstarCount() {
  emit('update-superstar-count', superstarCount.value)
}

/**
 * 监听复选框变化
 * 修改：仅通知父组件更新时间线和高亮，不自动切换视图
 */
watch(selectedGenresForTimeline, (newVal) => {
  // 1. 通知父组件更新时间线视图 & 主视图高亮
  emit('timeline-filter-change', newVal)
}, { deep: true })

function handleFilterChange() {
  // 仅在用户交互时更新内部状态，不触发外部更新，等待点击按钮
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

.superstar-section {
  background: rgba(255, 215, 0, 0.05);
  border-bottom: 1px solid rgba(255, 215, 0, 0.1);
}

.superstar-controls {
  margin-top: 15px;
  padding-top: 10px;
  border-top: 1px dashed rgba(255, 255, 255, 0.1);
}

.hint-text {
  font-size: 11px;
  color: #999;
  margin-top: 8px;
  line-height: 1.4;
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

.filter-label-small {
  font-size: 12px;
  color: #ccc;
  display: block;
  margin-bottom: 4px;
}

/* Switch Toggle */
.switch {
  position: relative;
  display: inline-block;
  width: 34px;
  height: 18px;
}
.switch input { opacity: 0; width: 0; height: 0; }
.slider {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: #444;
  transition: .4s;
}
.slider:before {
  position: absolute;
  content: "";
  height: 14px; width: 14px;
  left: 2px; bottom: 2px;
  background-color: white;
  transition: .4s;
}
input:checked + .slider { background-color: #ffd700; }
input:checked + .slider:before { transform: translateX(16px); }
.slider.round { border-radius: 34px; }
.slider.round:before { border-radius: 50%; }


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

.apply-button.superstar-btn {
  background: #d4af37;
  color: #000;
}
.apply-button.superstar-btn:hover {
  background: #ffd700;
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
