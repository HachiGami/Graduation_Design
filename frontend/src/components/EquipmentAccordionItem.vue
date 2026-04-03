<template>
  <div
    class="rounded-xl border border-slate-200 bg-white"
    :id="anchorId || undefined"
    :class="{ 'equipment-highlight-flash': highlighted }"
  >
    <el-collapse-item :name="equipment._id">
      <template #title>
        <div class="flex w-full items-center gap-3 pr-3">
          <div class="flex flex-1 items-center gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
              <el-icon :size="18"><Monitor /></el-icon>
            </div>
            <span class="truncate text-sm font-semibold text-slate-800">{{ equipment.name }}</span>
          </div>

          <div class="w-[450px]">
            <div class="truncate text-sm font-semibold text-slate-700">
              {{ equipment.specification || '暂无' }}
            </div>
          </div>

          <div class="flex w-32 justify-end gap-1.5" @click.stop>
            <el-button link type="primary" @click="openEditModal">
              <el-icon :size="18"><Edit /></el-icon>
            </el-button>
            <el-button link type="danger" @click="handleDeleteEquipment">
              <el-icon :size="18"><Delete /></el-icon>
            </el-button>
          </div>
        </div>
      </template>

      <div class="rounded-xl bg-[#f8fafc] p-4 shadow-inner">
        <el-tabs>
          <el-tab-pane label="当前占用任务">
            <el-empty
              v-if="!equipment.serving_activities_details || equipment.serving_activities_details.length === 0"
              description="当前无占用任务，设备空闲"
              :image-size="60"
            />
            <div v-else class="space-y-3">
              <div
                v-for="(detail, index) in equipment.serving_activities_details"
                :key="index"
                class="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-blue-300 hover:shadow-md"
              >
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-2">
                    <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-500">
                      <el-icon :size="14"><Connection /></el-icon>
                    </div>
                    <span class="truncate text-sm font-semibold text-slate-800">{{ detail.activity_name }}</span>
                    <span class="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-600">
                      {{ getActivityStatusLabel(detail.status) }}
                    </span>
                  </div>
                  <div class="ml-10 mt-2 flex flex-wrap items-center gap-4 text-xs">
                    <span class="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-1 text-slate-600">
                      <el-icon><Share /></el-icon>
                      归属流程: {{ formatProcessName(detail.process_id) }}
                    </span>
                    <span
                      v-if="detail.working_hours && detail.working_hours.length > 0"
                      class="inline-flex items-center gap-1 font-medium text-blue-600"
                    >
                      <el-icon><Clock /></el-icon>
                      运行时间:
                      {{ detail.working_hours.map((wh: any) => `${wh.start_time}-${wh.end_time}`).join(', ') }}
                    </span>
                  </div>
                </div>
                <el-button plain class="!border-blue-200 !bg-white !text-blue-600" @click="goToActivityDetail(detail)">
                  查看活动详情
                </el-button>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="设备履历与参数">
            <div class="overflow-hidden rounded-xl border border-slate-200 bg-white">
              <div class="grid grid-cols-6 border-b border-slate-200 text-sm">
                <div class="bg-slate-100 px-3 py-2 font-medium text-slate-600">设备名称</div>
                <div class="border-l border-slate-200 px-3 py-2 text-slate-700">{{ equipment.name || '-' }}</div>
                <div class="border-l border-slate-200 bg-slate-100 px-3 py-2 font-medium text-slate-600">设备种类</div>
                <div class="border-l border-slate-200 px-3 py-2 text-slate-700">{{ equipment.specification || '-' }}</div>
                <div class="border-l border-slate-200 bg-slate-100 px-3 py-2 font-medium text-slate-600">当前状态</div>
                <div class="border-l border-slate-200 px-3 py-2 text-slate-700">{{ getStatusLabel(equipment.status) }}</div>
              </div>
              <div class="grid grid-cols-6 text-sm">
                <div class="bg-slate-100 px-3 py-2 font-medium text-slate-600">生产厂家</div>
                <div class="border-l border-slate-200 px-3 py-2 text-slate-700">{{ equipment.manufacturer || '-' }}</div>
                <div class="border-l border-slate-200 bg-slate-100 px-3 py-2 font-medium text-slate-600">生产时间</div>
                <div class="border-l border-slate-200 px-3 py-2 text-slate-700">{{ equipment.production_date || '-' }}</div>
                <div class="border-l border-slate-200 bg-slate-100 px-3 py-2 font-medium text-slate-600">设备ID</div>
                <div class="border-l border-slate-200 px-3 py-2 text-slate-700">{{ equipment._id || '-' }}</div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane :label="`检修与保养记录 (${(equipment.upcoming_maintenance || []).length})`">
            <div class="mb-3 flex justify-end">
              <el-button type="primary" @click.stop="openMaintenanceModal">+ 添加检修计划</el-button>
            </div>
            <div
              v-if="equipment.upcoming_maintenance && equipment.upcoming_maintenance.length > 0"
              class="grid grid-cols-3 gap-4"
            >
              <div
                v-for="(dateItem, idx) in equipment.upcoming_maintenance"
                :key="idx"
                class="group flex items-center justify-between rounded-xl border border-slate-200 bg-white p-3 shadow-sm transition-all hover:border-red-300 hover:shadow-md"
              >
                <div class="flex items-center">
                  <div class="mr-3 flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-red-500">
                    <el-icon :size="16"><Calendar /></el-icon>
                  </div>
                  <span class="text-sm font-bold text-slate-700">{{ dateItem }}</span>
                </div>
                <el-button
                  link
                  class="!text-slate-300 opacity-0 transition-opacity hover:!text-red-500 group-hover:opacity-100"
                  @click.stop
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
            <el-empty v-else description="暂无检修记录" :image-size="60" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-collapse-item>

    <!-- 编辑弹窗 -->
    <el-dialog
      v-model="isEditModalVisible"
      title="编辑设备"
      width="500px"
      append-to-body
    >
      <el-form :model="editForm" label-width="100px" size="default">
        <el-form-item label="设备名称" required>
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="设备种类" required>
          <el-input v-model="editForm.specification" />
        </el-form-item>
        <el-form-item label="生产厂家">
          <el-input v-model="editForm.manufacturer" />
        </el-form-item>
        <el-form-item label="生产时间">
          <el-date-picker
            v-model="editForm.production_date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div style="display: flex; justify-content: space-between; width: 100%;">
          <el-button type="danger" @click="handleDeleteEquipment">删除该设备</el-button>
          <div>
            <el-button @click="isEditModalVisible = false">取消</el-button>
            <el-button type="primary" @click="submitEdit" :loading="isSubmitting">保存</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 检修弹窗 -->
    <el-dialog
      v-model="isMaintenanceModalVisible"
      title="安排设备检修"
      width="400px"
      append-to-body
    >
      <el-form label-width="100px">
        <el-form-item label="检修日期">
          <el-select
            v-model="selectedMaintenanceDays"
            multiple
            placeholder="请选择检修日期"
            style="width: 100%"
          >
            <el-option
              v-for="item in maintenanceOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="isMaintenanceModalVisible = false">取消</el-button>
          <el-button type="primary" @click="submitMaintenance" :loading="isSubmittingMaintenance">
            确定
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { Edit, Delete, Monitor, Calendar, Clock, Share, Connection } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteResource } from '@/api/resource'

const props = withDefaults(
  defineProps<{
    equipment: any
    anchorId?: string
    highlighted?: boolean
  }>(),
  {
    anchorId: '',
    highlighted: false
  }
)

const emit = defineEmits(['update'])
const router = useRouter()

const isEditModalVisible = ref(false)
const isSubmitting = ref(false)
const editForm = reactive({
  name: '',
  specification: '',
  manufacturer: '',
  production_date: ''
})

const isMaintenanceModalVisible = ref(false)
const isSubmittingMaintenance = ref(false)
const selectedMaintenanceDays = ref<string[]>([])

const maintenanceOptions = [
  { label: '1天后', value: '1天后' },
  { label: '2天后', value: '2天后' },
  { label: '3天后', value: '3天后' },
  { label: '4天后', value: '4天后' },
  { label: '5天后', value: '5天后' },
  { label: '6天后', value: '6天后' },
  { label: '7天后', value: '7天后' }
]

const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    idle: '空闲',
    in_use: '使用中',
    maintenance: '维护中',
    available: '可用'
  }
  return map[status] || status
}

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

const formatProcessName = (processId: string) => {
  if (!processId) return '未知流程'
  if (processMap[processId]) return `${processId} - ${processMap[processId]}`
  const prefix = processId.charAt(0).toUpperCase()
  const typeMap: Record<string, string> = {
    'P': '生产流程', 'Q': '质检流程',
    'S': '销售流程', 'W': '仓储流程', 'T': '运输流程'
  }
  return `${processId} - ${typeMap[prefix] || '未知流程'}`
}

const getActivityStatusLabel = (status: string) => {
  const normalized = (status || '').toLowerCase()
  if (normalized === 'in_progress' || normalized === '进行中') return '进行中'
  if (normalized === 'stopped' || normalized === '已停机') return '已停机'
  if (normalized === 'pending' || normalized === '待机') return '待机中'
  return status || '未知状态'
}

const goToActivityDetail = (task: any) => {
  const activityId = task?.activity_id || task?.id || task?._id
  if (!activityId) {
    ElMessage.warning('当前任务缺少 activity_id，暂无法定位活动详情')
    return
  }
  router.push({
    name: 'Dashboard',
    query: {
      highlightId: String(activityId)
    }
  })
}

const openEditModal = () => {
  editForm.name = props.equipment.name || ''
  editForm.specification = props.equipment.specification || ''
  editForm.manufacturer = props.equipment.manufacturer || ''
  editForm.production_date = props.equipment.production_date || ''
  isEditModalVisible.value = true
}

const openMaintenanceModal = () => {
  selectedMaintenanceDays.value = [...(props.equipment.upcoming_maintenance || [])]
  isMaintenanceModalVisible.value = true
}

const submitMaintenance = async () => {
  isSubmittingMaintenance.value = true
  try {
    const response = await fetch(`http://localhost:8000/api/resources/${props.equipment._id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        upcoming_maintenance: selectedMaintenanceDays.value
      })
    })
    
    if (!response.ok) {
      throw new Error('更新失败')
    }
    
    ElMessage.success('设备检修计划更新成功')
    isMaintenanceModalVisible.value = false
    emit('update')
  } catch (error) {
    console.error('Failed to update maintenance:', error)
    ElMessage.error('更新失败，请重试')
  } finally {
    isSubmittingMaintenance.value = false
  }
}

const submitEdit = async () => {
  if (!editForm.name.trim()) {
    ElMessage.warning('设备名称不能为空')
    return
  }
  if (!editForm.specification.trim()) {
    ElMessage.warning('请输入或选择设备种类')
    return
  }
  isSubmitting.value = true
  try {
    const response = await fetch(`http://localhost:8000/api/resources/${props.equipment._id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name: editForm.name,
        specification: editForm.specification,
        manufacturer: editForm.manufacturer,
        production_date: editForm.production_date
      })
    })
    
    if (!response.ok) {
      throw new Error('更新失败')
    }
    
    ElMessage.success('设备信息更新成功')
    isEditModalVisible.value = false
    emit('update')
  } catch (error) {
    console.error('Failed to update equipment:', error)
    ElMessage.error('更新失败，请重试')
  } finally {
    isSubmitting.value = false
  }
}

const handleDeleteEquipment = async () => {
  const id = props.equipment._id || props.equipment.id
  if (!id) return
  try {
    await ElMessageBox.confirm(
      '此操作将从数据库和图谱中永久删除该设备数据，是否继续？',
      '警告',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteResource(id)
    ElMessage.success('设备已删除')
    isEditModalVisible.value = false
    emit('update')
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}
</script>

<style scoped>
.equipment-highlight-flash {
  animation: equipment-highlight-flash 1.8s ease;
}

@keyframes equipment-highlight-flash {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0);
  }
  20%,
  60% {
    box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.35);
  }
}
</style>
