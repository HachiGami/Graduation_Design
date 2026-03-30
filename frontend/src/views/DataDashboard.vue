<template>
  <div class="dashboard-page">
    <el-card>
      <template #header>
        <div class="toolbar">
          <span class="toolbar-title">数据管理面板</span>
          <el-select v-model="selectedFilter" style="width: 320px">
            <el-option label="全部活动" value="all" />
            <el-option
              v-for="option in filterOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
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
const selectedFilter = ref('all')

const filterOptions = computed(() => {
  const processSet = new Set<string>()
  const domainSet = new Set<string>()
  activities.value.forEach((item) => {
    if (item.process_id) processSet.add(item.process_id)
    if (item.domain) domainSet.add(item.domain)
  })
  return [
    ...Array.from(processSet).map((processId) => ({
      value: `process:${processId}`,
      label: `流程ID：${processId}`
    })),
    ...Array.from(domainSet).map((domain) => ({
      value: `domain:${domain}`,
      label: `流程域：${domain}`
    }))
  ]
})

const filteredActivities = computed(() => {
  if (selectedFilter.value === 'all') return activities.value
  if (selectedFilter.value.startsWith('process:')) {
    const processId = selectedFilter.value.replace('process:', '')
    return activities.value.filter((item) => item.process_id === processId)
  }
  if (selectedFilter.value.startsWith('domain:')) {
    const domain = selectedFilter.value.replace('domain:', '')
    return activities.value.filter((item) => item.domain === domain)
  }
  return activities.value
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








