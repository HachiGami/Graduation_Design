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
            <el-select v-model="selectedFilter" style="width: 200px" class="mr-4">
              <el-option label="全部状态" value="ALL" />
              <el-option label="待机" value="pending" />
              <el-option label="进行中" value="in_progress" />
            </el-select>
            <el-button type="primary" :icon="Plus" @click="openAddActivityDialog">添加活动</el-button>
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

    <!-- 添加活动弹窗 -->
    <el-dialog v-model="addActivityDialogVisible" title="添加活动" width="580px">
      <el-form :model="addActivityForm" label-width="110px" size="default">
        <el-form-item label="活动名称" required>
          <el-input v-model="addActivityForm.name" placeholder="请输入活动名称" />
        </el-form-item>
        <el-form-item label="活动描述">
          <el-input v-model="addActivityForm.description" type="textarea" :rows="2" placeholder="请输入活动描述" />
        </el-form-item>
        <el-form-item label="流程ID" required>
          <el-select v-model="addActivityForm.process_id" style="width: 100%" @change="onAddProcessIdChange">
            <el-option v-for="item in processOptions.filter(o => o.value !== 'ALL')" :key="item.value" :label="item.label" :value="item.value" />
            <el-option label="P001 - 主生产线" value="P001" />
            <el-option label="P002 - 副生产线" value="P002" />
            <el-option label="T001 - 冷链运输" value="T001" />
            <el-option label="T002 - 常温运输" value="T002" />
            <el-option label="S001 - 线上销售" value="S001" />
            <el-option label="S002 - 线下销售" value="S002" />
            <el-option label="Q001 - 常规质检" value="Q001" />
            <el-option label="Q002 - 专项质检" value="Q002" />
            <el-option label="W001 - 主仓库" value="W001" />
            <el-option label="W002 - 分仓库" value="W002" />
          </el-select>
        </el-form-item>
        <el-form-item label="前置活动">
          <el-select
            v-model="addActivityForm.predecessor_ids"
            style="width: 100%"
            multiple
            clearable
            filterable
            placeholder="输入活动名称进行搜索"
          >
            <el-option
              v-for="item in addPredecessorOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="初始状态">
          <el-select v-model="addActivityForm.status" style="width: 100%">
            <el-option label="待机" value="pending" />
            <el-option label="进行中" value="in_progress" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addActivityDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAddActivity" :loading="addActivitySubmitting">确定添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getActivities, createActivity } from '@/api/activity'
import type { Activity } from '@/types'
import ActivityAccordionItem from '@/components/ActivityAccordionItem.vue'
import { Plus } from '@element-plus/icons-vue'

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

const addActivityDialogVisible = ref(false)
const addActivitySubmitting = ref(false)

const prefixToDomainMap: Record<string, string> = {
  'P': 'production', 'T': 'transport', 'S': 'sales', 'Q': 'quality', 'W': 'warehouse'
}

const defaultAddActivityForm = () => ({
  name: '',
  description: '',
  process_id: 'P001',
  domain: 'production',
  predecessor_ids: [] as string[],
  status: 'pending' as 'pending' | 'in_progress',
  sop_steps: [],
  estimated_duration: 0,
  required_resources: [] as string[],
  required_personnel: [] as string[],
  working_hours: [
    { start_time: '08:00', end_time: '11:00' },
    { start_time: '13:00', end_time: '18:00' }
  ]
})

const addActivityForm = ref(defaultAddActivityForm())

const addPredecessorOptions = computed(() => {
  return activities.value.filter((item) => item.id)
})

const openAddActivityDialog = () => {
  addActivityForm.value = defaultAddActivityForm()
  addActivityDialogVisible.value = true
}

const onAddProcessIdChange = (val: string) => {
  if (!val) return
  const prefix = val.charAt(0).toUpperCase()
  if (!prefixToDomainMap[prefix]) return
  addActivityForm.value.predecessor_ids = []
  addActivityForm.value.domain = prefixToDomainMap[prefix]
}

const submitAddActivity = async () => {
  if (!addActivityForm.value.name.trim()) {
    ElMessage.warning('活动名称不能为空')
    return
  }
  if (!addActivityForm.value.process_id) {
    ElMessage.warning('请选择流程ID')
    return
  }
  addActivitySubmitting.value = true
  try {
    await createActivity(addActivityForm.value as Activity)
    ElMessage.success('活动添加成功')
    addActivityDialogVisible.value = false
    await loadAllActivities()
  } catch (error) {
    ElMessage.error('添加失败，请检查表单数据')
  } finally {
    addActivitySubmitting.value = false
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








