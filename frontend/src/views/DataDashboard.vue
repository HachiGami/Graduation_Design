<template>
  <div class="dashboard-page">
    <el-card>
      <template #header>
        <div class="toolbar">
          <span class="toolbar-title">数据管理面板</span>
          <el-select v-model="selectedFilter" style="width: 320px">
            <el-option
              v-for="item in processOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
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

/**
 * 格式化流程名称
 * @param processId 流程ID (如 P001)
 */
const formatProcessName = (processId: string) => {
  const mapping: Record<string, string> = {
    P001: '主生产线',
    P002: '副生产线',
    T001: '冷链运输',
    T002: '常温运输',
    S001: '线上销售',
    S002: '线下销售',
    Q001: '常规质检',
    Q002: '专项质检',
    W001: '主仓库',
    W002: '分仓库'
  }
  return mapping[processId] ? `${processId} - ${mapping[processId]}` : processId
}

// 新增或替换下拉选项的计算属性
const processOptions = computed(() => {
  // 1. 提取所有的 process_id 并去重，排除空值和 domain
  const ids = new Set<string>()
  activities.value.forEach((act) => {
    // 防御性处理：有些脏数据可能存成了 "production/P001"，这里只取纯 ID
    const rawId = act.process_id
    if (rawId) {
      const cleanId = rawId.includes('/') ? rawId.split('/').pop() : rawId
      if (cleanId && !cleanId.includes('production') && !cleanId.includes('transport')) {
        ids.add(cleanId)
      }
    }
  })

  // 2. 构造下拉框需要的 label 和 value，强制使用 formatProcessName 翻译成中文
  const options = Array.from(ids).map((id) => ({
    value: id,
    label: formatProcessName(id) // 这里会生成 "P001 - 主生产线" 这样的文本
  }))

  // 3. 在最前面加上“全部”选项
  return [{ value: 'ALL', label: '全部流程' }, ...options]
})

const filteredActivities = computed(() => {
  if (selectedFilter.value === 'ALL') return activities.value
  return activities.value.filter((item) => {
    const rawId = item.process_id
    const cleanId = rawId?.includes('/') ? rawId.split('/').pop() : rawId
    return cleanId === selectedFilter.value
  })
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

.toolbar-title {
  font-size: 18px;
  font-weight: 700;
}
</style>








