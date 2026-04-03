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
        <div
          v-for="activity in filteredActivities"
          :key="activity.id || activity.name"
          :id="'activity-row-' + String(activity.id || (activity as any)._id || activity.name || '')"
        >
          <ActivityAccordionItem
            :activity="activity"
            :force-expand="String(activity.id || (activity as any)._id || '') === highlightedActivityId"
            :highlighted="String(activity.id || (activity as any)._id || '') === highlightedActivityId"
            @refreshed="loadAllActivities"
          />
        </div>
      </div>
    </div>

    <!-- 添加活动弹窗 -->
    <el-dialog
      v-model="addActivityDialogVisible"
      width="500px"
      :show-close="false"
      :align-center="true"
      class="add-entity-dialog rounded-2xl overflow-hidden"
      header-class="!p-0 !m-0 !border-0"
      body-class="!p-0"
      footer-class="!p-0"
    >
      <template #header>
        <div class="flex items-center justify-between border-b border-indigo-100 bg-indigo-50/50 px-6 py-4">
          <div class="flex items-center space-x-3">
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-100 text-indigo-600">
              <el-icon :size="18"><VideoPlay /></el-icon>
            </div>
            <h3 class="text-lg font-bold tracking-tight text-slate-800">添加活动</h3>
          </div>
          <el-button link class="text-slate-400 hover:text-slate-600" @click="addActivityDialogVisible = false">
            <el-icon :size="20"><Close /></el-icon>
          </el-button>
        </div>
      </template>

      <div class="bg-white p-6">
        <div class="grid grid-cols-1 gap-5">
          <div class="flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">
              <span class="mr-1 text-red-500">*</span>活动名称
            </label>
            <el-input v-model="addActivityForm.name" placeholder="请输入活动名称" class="custom-input-indigo w-full" />
          </div>

          <div class="grid grid-cols-2 gap-5">
            <div class="flex flex-col space-y-1.5">
              <label class="text-[13px] font-bold text-slate-700">
                <span class="mr-1 text-red-500">*</span>流程 ID
              </label>
              <el-select
                v-model="addActivityForm.process_id"
                class="custom-input-indigo w-full"
                @change="onAddProcessIdChange"
              >
                <el-option
                  v-for="item in processOptions.filter((o) => o.value !== 'ALL')"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
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
            </div>
            <div class="flex flex-col space-y-1.5">
              <label class="text-[13px] font-bold text-slate-700">初始状态</label>
              <el-select v-model="addActivityForm.status" class="custom-input-indigo w-full">
                <el-option label="待机" value="pending" />
                <el-option label="进行中" value="in_progress" />
              </el-select>
            </div>
          </div>

          <div class="flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">前置活动</label>
            <el-select
              v-model="addActivityForm.predecessor_ids"
              class="custom-input-indigo w-full"
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
          </div>

          <div class="flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">活动描述</label>
            <el-input
              v-model="addActivityForm.description"
              type="textarea"
              :rows="3"
              placeholder="请输入活动描述"
              class="custom-input-indigo"
            />
          </div>
        </div>
      </div>

      <template #footer>
        <div class="flex justify-end space-x-3 border-t border-slate-100 bg-slate-50 px-6 py-4">
          <button
            type="button"
            class="rounded-xl border border-slate-300 bg-white px-5 py-2 text-sm font-bold text-slate-600 transition-colors hover:bg-slate-50"
            @click="addActivityDialogVisible = false"
          >
            取消
          </button>
          <button
            type="button"
            class="rounded-xl bg-indigo-600 px-5 py-2 text-sm font-bold text-white shadow-sm transition-colors hover:bg-indigo-700"
            :disabled="addActivitySubmitting"
            @click="submitAddActivity"
          >
            {{ addActivitySubmitting ? '提交中…' : '确定添加' }}
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getActivities, createActivity } from '@/api/activity'
import type { Activity } from '@/types'
import ActivityAccordionItem from '@/components/ActivityAccordionItem.vue'
import { Plus, Search, VideoPlay, Close } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'

const DOMAIN_LIST = ['production', 'transport', 'sales', 'quality', 'warehouse']
const activities = ref<Activity[]>([])
const selectedFilter = ref('ALL')
const selectedProcessId = ref('ALL')
const searchQuery = ref('')
const highlightedActivityId = ref('')
const route = useRoute()
const router = useRouter()

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
    await handleRouteHighlight()
  } catch (error) {
    ElMessage.error('加载活动失败')
  }
}

const handleRouteHighlight = async () => {
  const rawId = route.query.highlightId
  const highlightId = Array.isArray(rawId) ? rawId[0] : rawId
  if (!highlightId) return

  const targetId = String(highlightId)
  const target = activities.value.find((item) => String(item.id || (item as any)._id || '') === targetId)
  if (!target) {
    ElMessage.warning('未找到目标活动，可能已被删除或无权限查看')
    highlightedActivityId.value = ''
    const nextQuery = { ...route.query } as Record<string, any>
    delete nextQuery.highlightId
    await router.replace({ query: nextQuery })
    return
  }

  selectedFilter.value = 'ALL'
  selectedProcessId.value = 'ALL'
  searchQuery.value = ''
  highlightedActivityId.value = targetId

  await nextTick()
  const targetEl = document.getElementById(`activity-row-${targetId}`)
  if (!targetEl) {
    ElMessage.warning('活动定位失败，请稍后重试')
    return
  }

  targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
  setTimeout(() => {
    highlightedActivityId.value = ''
  }, 1800)
  const nextQuery = { ...route.query } as Record<string, any>
  delete nextQuery.highlightId
  await router.replace({ query: nextQuery })
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

watch(
  () => route.query.highlightId,
  async () => {
    await handleRouteHighlight()
  }
)
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

:deep(.add-entity-dialog.el-dialog) {
  border-radius: 16px;
  padding: 0;
  overflow: hidden;
}

:deep(.add-entity-dialog .el-dialog__header) {
  padding: 0;
  margin: 0;
}

:deep(.custom-input-indigo .el-input__wrapper),
:deep(.custom-input-indigo .el-textarea__inner) {
  background-color: #f8fafc !important;
  border-radius: 0.75rem !important;
  box-shadow: 0 0 0 1px #e2e8f0 inset !important;
  padding-top: 0.25rem;
  padding-bottom: 0.25rem;
  transition: all 0.2s;
}

:deep(.custom-input-indigo .el-input__wrapper.is-focus),
:deep(.custom-input-indigo .el-textarea__inner:focus) {
  background-color: #ffffff !important;
  box-shadow: 0 0 0 1px #6366f1 inset, 0 0 0 4px #e0e7ff !important;
}

:deep(.custom-input-indigo .el-select .el-input__wrapper.is-focus) {
  background-color: #ffffff !important;
  box-shadow: 0 0 0 1px #6366f1 inset, 0 0 0 4px #e0e7ff !important;
}

</style>








