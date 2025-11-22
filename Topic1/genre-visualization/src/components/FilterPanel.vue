<template>
  <div class="filter-panel">
    <div class="panel-header">
      <h2>筛选音乐人</h2>
    </div>
    
    <div class="panel-content">
      <!-- 当前状态信息（音乐人视图模式） -->
      <div class="filter-section" v-if="isArtistView && currentGenre">
        <div class="current-status">
          <div class="status-item">
            <span class="status-label">当前流派：</span>
            <span class="status-value">{{ currentGenre }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">可用音乐人：</span>
            <span class="status-value">{{ currentArtistsCount }} 位</span>
          </div>
        </div>
      </div>

      <!-- 流派选择（仅在流派视图模式显示） -->
      <div class="filter-section" v-if="!isArtistView">
        <label class="filter-label">选择流派</label>
        <select 
          v-model="selectedGenre" 
          class="filter-select"
          @change="handleGenreChange"
        >
          <option value="">-- 请选择流派 --</option>
          <option 
            v-for="genre in genres" 
            :key="genre" 
            :value="genre"
          >
            {{ genre }}
          </option>
        </select>
      </div>

      <!-- 筛选指标选择 -->
      <div class="filter-section" v-if="canShowMetrics">
        <label class="filter-label">排序指标</label>
        <select 
          v-model="selectedMetric" 
          class="filter-select"
          @change="handleMetricChange"
        >
          <option value="score">综合评分</option>
          <option value="total_works">总作品数</option>
          <option value="notable_rate">成名率</option>
          <option value="notable_works">成名作品数</option>
          <option value="time_span">活跃时长</option>
          <option value="influence_score">影响力分数</option>
          <option value="collaborators_count">合作者数量</option>
          <option value="record_labels_count">唱片公司数量</option>
          <option value="role_count">角色多样性</option>
        </select>
      </div>

      <!-- 显示数量选择 -->
      <div class="filter-section" v-if="canShowMetrics">
        <label class="filter-label">显示前 N 名</label>
        <input 
          type="number" 
          v-model.number="topN" 
          class="filter-input"
          :min="1"
          :max="maxTopN"
          @change="handleTopNChange"
        />
        <span class="input-hint" v-if="isArtistView">
          最多 {{ currentArtistsCount }} 名
        </span>
      </div>

      <!-- 应用筛选按钮 -->
      <div class="filter-section" v-if="canShowMetrics">
        <button 
          class="apply-button"
          @click="handleApplyFilter"
          :disabled="!canApply"
        >
          {{ isArtistView ? '精炼筛选' : '应用筛选' }}
        </button>
      </div>

      <!-- 当前筛选信息 -->
      <div class="filter-info" v-if="appliedFilter">
        <div class="info-item">
          <span class="info-label">流派：</span>
          <span class="info-value">{{ appliedFilter.genre || currentGenre }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">指标：</span>
          <span class="info-value">{{ getMetricLabel(appliedFilter.metric) }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">显示：</span>
          <span class="info-value">前 {{ appliedFilter.topN }} 名</span>
        </div>
        <div class="info-item">
          <span class="info-label">结果：</span>
          <span class="info-value">{{ appliedFilter.resultCount || currentArtistsCount }} 位音乐人</span>
        </div>
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
const emit = defineEmits(['apply-filter', 'refine-filter'])

// ==================== 响应式数据 ====================
const selectedGenre = ref('')
const selectedMetric = ref('score')
const topN = ref(100)
const appliedFilter = ref(null)

// ==================== 计算属性 ====================
/**
 * 是否可以显示指标选择（流派视图需要选择流派，音乐人视图直接显示）
 */
const canShowMetrics = computed(() => {
  if (props.isArtistView) {
    return props.currentGenre && props.currentArtistsCount > 0
  }
  return selectedGenre.value
})

/**
 * 是否可以应用筛选
 */
const canApply = computed(() => {
  if (props.isArtistView) {
    return props.currentGenre && selectedMetric.value && topN.value > 0 && topN.value <= props.currentArtistsCount
  }
  return selectedGenre.value && selectedMetric.value && topN.value > 0
})

/**
 * 最大显示数量（音乐人视图时限制为当前可用数量）
 */
const maxTopN = computed(() => {
  if (props.isArtistView && props.currentArtistsCount > 0) {
    return props.currentArtistsCount
  }
  return 500
})

/**
 * 获取指标的中文标签
 */
function getMetricLabel(metric) {
  const labels = {
    'score': '综合评分',
    'total_works': '总作品数',
    'notable_rate': '成名率',
    'notable_works': '成名作品数',
    'time_span': '活跃时长',
    'influence_score': '影响力分数',
    'collaborators_count': '合作者数量',
    'record_labels_count': '唱片公司数量',
    'role_count': '角色多样性'
  }
  return labels[metric] || metric
}

// ==================== 方法 ====================
/**
 * 处理流派变化
 */
function handleGenreChange() {
  // 重置筛选状态
  appliedFilter.value = null
}

// 监听当前流派变化，同步到 selectedGenre（用于显示）
watch(() => props.currentGenre, (newGenre) => {
  if (props.isArtistView && newGenre) {
    selectedGenre.value = newGenre
  }
}, { immediate: true })

// 监听音乐人数量变化，更新 topN 的最大值
watch(() => props.currentArtistsCount, (newCount) => {
  if (props.isArtistView && newCount > 0 && topN.value > newCount) {
    topN.value = newCount
  }
})

/**
 * 处理指标变化
 */
function handleMetricChange() {
  // 可以在这里添加额外的逻辑
}

/**
 * 处理显示数量变化
 */
function handleTopNChange() {
  // 确保值在合理范围内
  if (topN.value < 1) topN.value = 1
  const max = maxTopN.value
  if (topN.value > max) topN.value = max
}

/**
 * 应用筛选
 */
function handleApplyFilter() {
  if (!canApply.value) return
  
  if (props.isArtistView) {
    // 音乐人视图模式：精炼筛选（二次筛选）
    const filter = {
      metric: selectedMetric.value,
      topN: topN.value
    }
    appliedFilter.value = {
      ...filter,
      genre: props.currentGenre,
      resultCount: Math.min(topN.value, props.currentArtistsCount)
    }
    emit('refine-filter', filter)
  } else {
    // 流派视图模式：初始筛选
    const filter = {
      genre: selectedGenre.value,
      metric: selectedMetric.value,
      topN: topN.value
    }
    appliedFilter.value = filter
    emit('apply-filter', filter)
  }
}
</script>

<style scoped>
.filter-panel {
  width: 280px;
  height: 100%;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.panel-header {
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  text-align: center;
}

.panel-header h2 {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.panel-content {
  flex: 1;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.filter-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-label {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.filter-select,
.filter-input {
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  color: #333;
  transition: border-color 0.2s ease;
}

.filter-select:focus,
.filter-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.filter-input {
  width: 100%;
}

.apply-button {
  padding: 12px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.apply-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.apply-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.filter-info {
  margin-top: 10px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 3px solid #667eea;
}

.info-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-label {
  color: #666;
  font-weight: 500;
}

.info-value {
  color: #333;
  font-weight: 600;
}

.current-status {
  padding: 12px;
  background: #f0f4ff;
  border-radius: 6px;
  border-left: 3px solid #667eea;
}

.status-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
}

.status-item:last-child {
  margin-bottom: 0;
}

.status-label {
  color: #666;
  font-weight: 500;
}

.status-value {
  color: #667eea;
  font-weight: 600;
}

.input-hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #999;
}
</style>

