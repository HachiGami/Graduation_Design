<template>
  <div class="dashboard-page">
    <el-card>
      <template #header>
        <div class="toolbar">
          <span class="toolbar-title">数据管理面板</span>
          <div class="filter-group">
            <el-select v-model="selectedProcessId" placeholder="流程筛选" style="width: 200px;" class="mr-4">
              <el-option
                v-for="item in processOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
            <el-select v-model="selectedFilter" style="width: 200px">
              <el-option label="全部状态" value="ALL" />
              <el-option label="待机" value="pending" />
              <el-option label="进行中" value="in_progress" />
            </el-select>
          </div>
        </div>
      </template>

      <el-empty v-if="filteredActivities.length === 0" description="暂无活动数据" />
      <ActivityAccordionItem
        v-for="activity in filteredActivities"
        :key="activity.id || activity.name"
        :activity="activity"
        @refreshed="loadAllActivities"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getActivities } from '@/api/activity'
import type { Activity } from '@/types'
import ActivityAccordionItem from '@/components/ActivityAccordionItem.vue'

const DOMAIN_LIST = ['production', 'transport', 'sales', 'quality', 'warehouse']
const activities = ref<Activity[]>([])
const selectedFilter = ref('ALL')
const selectedProcessId = ref('ALL')

const processMap: Record<string, string> = {
  'P001': '主生产线',
  'P002': '副生产线',
  'T001': '冷链运输',
  'T002': '常温运输',
  'S001': '线上销售',
  'S002': '线下销售',
  'Q001': '常规质检',
  'Q002': '专项质检',
  'W001': '主仓库',
  'W002': '分仓库'
}

/**
 * 格式化流程名称
 * @param id 流程ID (如 P001)
 */
const formatProcessName = (id: string) => {
  if (!id || id === 'ALL') return '全部流程'
  return processMap[id] ? `${id} - ${processMap[id]}` : id
}

// 新增或替换下拉选项的计算属性
const processOptions = computed(() => {
  const ids = new Set<string>()
  activities.value.forEach((act) => {
    if (act.process_id) {
      ids.add(act.process_id)
    }
  })

  const options = Array.from(ids).map((id) => ({
    value: id,
    label: formatProcessName(id)
  }))

  return [{ value: 'ALL', label: '全部流程' }, ...options]
})

const filteredActivities = computed(() => {
  let result = activities.value

  // 1. 状态过滤
  if (selectedFilter.value !== 'ALL') {
    result = result.filter((item) => item.status === selectedFilter.value)
  }

  // 2. 流程 ID 过滤
  if (selectedProcessId.value !== 'ALL') {
    result = result.filter((item) => item.process_id === selectedProcessId.value)
  }

  return result
})

const loadAllActivities = async () => {
  try {
    const result = await Promise.all(DOMAIN_LIST.map((domain) => getActivities({ domain })))
    const merged = result.flat().map((item) => {
      if ((item as any)._id && !item.id) item.id = (item as any)._id
      return item
    })
    activities.value = merged
  } catch (error) {
    ElMessage.error('加载活动失败')
  }
}

onMounted(async () => {
  await loadAllActivities()
})
</script>

<style scoped>
.dashboard-page {
  padding: 12px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.filter-group {
  display: flex;
  align-items: center;
}

.mr-4 {
  margin-right: 16px;
}

.toolbar-title {
  font-size: 18px;
  font-weight: 700;
}
</style>








