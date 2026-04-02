<template>
  <div class="h-full p-0">
    <div class="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm">
      <div class="flex items-center justify-between px-6 py-5">
        <div class="flex items-center gap-3">
          <el-input
            v-model="searchQuery"
            class="w-72"
            placeholder="搜索活动名称或ID..."
            clearable
            :prefix-icon="Search"
          />
          <el-select v-model="selectedProcessId" placeholder="流程筛选" class="custom-select w-[200px]">
            <el-option
              v-for="item in processOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
          <el-select v-model="selectedFilter" class="custom-select w-[200px]">
            <el-option label="全部状态" value="ALL" />
            <el-option label="待机" value="pending" />
            <el-option label="进行中" value="in_progress" />
          </el-select>
        </div>
        <el-button type="primary" class="rounded-lg border-blue-500 bg-blue-500 px-5 py-2 font-medium" :icon="Plus" @click="openAddActivityDialog">添加活动</el-button>
      </div>

      <div class="flex items-center border-b border-slate-100 px-6 pb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
        <div class="w-10 shrink-0"></div>
        <div class="min-w-0 flex-1">活动信息</div>
        <div class="w-48 shrink-0">所属流程</div>
        <div class="w-32 shrink-0">当前状态</div>
        <div class="w-72 shrink-0 text-right">操作</div>
      </div>

      <div class="flex-1 overflow-y-auto px-6 py-4">
        <el-empty v-if="filteredActivities.length === 0" description="暂无活动数据" />
        <ActivityAccordionItem
          v-for="activity in filteredActivities"
          :key="activity.id || activity.name"
          :activity="activity"
          @refreshed="loadAllActivities"
        />
      </div>
    </div>

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
import { Plus, Search } from '@element-plus/icons-vue'

const DOMAIN_LIST = ['production', 'transport', 'sales', 'quality', 'warehouse']
const activities = ref<Activity[]>([])
const selectedFilter = ref('ALL')
const selectedProcessId = ref('ALL')
const searchQuery = ref('')

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

  // 3. 文本搜索（与上述条件 AND；清空后仅受流程/状态筛选影响）
  const q = searchQuery.value.trim().toLowerCase()
  if (q) {
    result = result.filter((item) => {
      const name = (item.name ?? '').toLowerCase()
      const idStr = String(item.id ?? '').toLowerCase()
      return name.includes(q) || idStr.includes(q)
    })
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
:deep(.custom-select .el-input__wrapper) {
  background-color: #f8fafc;
  box-shadow: none !important;
  border-radius: 8px;
}

:deep(.custom-select .el-input__inner) {
  color: #475569;
}

:deep(.el-dialog) {
  border-radius: 12px;
}
</style>








