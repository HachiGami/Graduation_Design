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
              v-if="!priorityList.length"
              description="当前无占用任务，设备空闲"
              :image-size="60"
            />
            <div v-else class="mb-4">
              <div class="text-xs font-bold text-slate-500 mb-2 flex items-center justify-between">
                <span>当前占用活动队列 (拖拽 ☰ 图标以调整执行优先级)</span>
                <span class="text-[10px] text-amber-500 bg-amber-50 px-2 py-1 rounded">顶部优先级最高</span>
              </div>

              <el-table
                :data="priorityList"
                row-key="activity_id"
                ref="priorityTableRef"
                border
                style="width: 100%; border-radius: 8px; overflow: hidden;"
              >
                <el-table-column label="优先级" width="80" align="center">
                  <template #default="scope">
                    <div
                      class="flex items-center justify-center text-slate-400 font-black drag-handle cursor-move hover:text-amber-500 transition-colors"
                    >
                      <el-icon class="mr-1"><Operation /></el-icon>
                      P{{ scope.$index + 1 }}
                    </div>
                  </template>
                </el-table-column>

                <el-table-column prop="activity_name" label="占用活动名称" min-width="150">
                  <template #default="scope">
                    <span class="font-bold text-slate-700">{{ scope.row.activity_name }}</span>
                  </template>
                </el-table-column>

                <el-table-column prop="process_id" label="所属流程" min-width="160">
                  <template #default="scope">
                    <span class="text-slate-600">{{ formatProcessName(scope.row.process_id || '') }}</span>
                  </template>
                </el-table-column>

                <el-table-column prop="status" label="状态" width="110">
                  <template #default="scope">
                    <el-tag size="small" type="info" class="!font-bold">
                      {{ getActivityStatusLabel(scope.row.status) }}
                    </el-tag>
                  </template>
                </el-table-column>

                <el-table-column label="操作" width="120" align="center">
                  <template #default="scope">
                    <el-button
                      link
                      type="primary"
                      class="!font-bold"
                      @click="goToActivityDetail(scope.row)"
                    >
                      查看活动
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-tab-pane>

          <el-tab-pane label="设备履历与参数">
            <div class="overflow-hidden rounded-xl border border-slate-200 bg-white">
              <div class="grid grid-cols-4 border-b border-slate-200 text-sm">
                <div class="bg-slate-100 px-3 py-2 font-medium text-slate-600">设备名称</div>
                <div class="border-l border-slate-200 px-3 py-2 text-slate-700">{{ equipment.name || '-' }}</div>
                <div class="border-l border-slate-200 bg-slate-100 px-3 py-2 font-medium text-slate-600">设备种类</div>
                <div class="border-l border-slate-200 px-3 py-2 text-slate-700">{{ equipment.specification || '-' }}</div>
              </div>
              <div class="grid grid-cols-4 text-sm">
                <div class="bg-slate-100 px-3 py-2 font-medium text-slate-600">生产厂家</div>
                <div class="border-l border-slate-200 px-3 py-2 text-slate-700">{{ equipment.manufacturer || '-' }}</div>
                <div class="border-l border-slate-200 bg-slate-100 px-3 py-2 font-medium text-slate-600">生产时间</div>
                <div class="border-l border-slate-200 px-3 py-2 text-slate-700">{{ equipment.production_date || '-' }}</div>
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
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import Sortable from 'sortablejs'
import { Edit, Delete, Monitor, Calendar, Operation } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteResource, updateResource } from '@/api/resource'

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

const emit = defineEmits<{
  update: []
  'edit-equipment': [equipment: any]
  'close-edit-equipment': []
}>()
const router = useRouter()

const isMaintenanceModalVisible = ref(false)
const isSubmittingMaintenance = ref(false)
const selectedMaintenanceDays = ref<string[]>([])

const priorityList = ref<any[]>([])
const priorityTableRef = ref<any>(null)
let prioritySortable: Sortable | null = null

const destroyPrioritySortable = () => {
  prioritySortable?.destroy()
  prioritySortable = null
}

const persistEquipmentPriority = async (activityIds: string[]) => {
  const id = props.equipment._id || props.equipment.id
  if (!id || !activityIds.length) return
  try {
    await updateResource(id, { equipment_activity_priority_order: activityIds })
    emit('update')
  } catch (e) {
    console.error(e)
    ElMessage.error('保存优先级失败')
  }
}

const initPrioritySortable = () => {
  nextTick(() => {
    destroyPrioritySortable()
    const table = priorityTableRef.value
    const tbody = table?.$el?.querySelector?.('.el-table__body-wrapper tbody') as HTMLElement | null
    if (!tbody || priorityList.value.length < 2) return

    prioritySortable = Sortable.create(tbody, {
      handle: '.drag-handle',
      animation: 150,
      ghostClass: 'equipment-priority-ghost',
      onEnd(evt: Sortable.SortableEvent) {
        const { newIndex, oldIndex } = evt
        if (newIndex == null || oldIndex == null || newIndex === oldIndex) return
        const row = priorityList.value.splice(oldIndex, 1)[0]
        priorityList.value.splice(newIndex, 0, row)
        const ids = priorityList.value.map((a) => a.activity_id).filter(Boolean)
        void persistEquipmentPriority(ids)
      }
    })
  })
}

watch(
  () => props.equipment.serving_activities_details,
  (d) => {
    priorityList.value = Array.isArray(d) ? [...d] : []
    initPrioritySortable()
  },
  { deep: true, immediate: true }
)

onBeforeUnmount(() => {
  destroyPrioritySortable()
})

const maintenanceOptions = [
  { label: '1天后', value: '1天后' },
  { label: '2天后', value: '2天后' },
  { label: '3天后', value: '3天后' },
  { label: '4天后', value: '4天后' },
  { label: '5天后', value: '5天后' },
  { label: '6天后', value: '6天后' },
  { label: '7天后', value: '7天后' }
]

// 流程映射字典（与 PersonnelAccordionItem 保持一致）
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

const formatProcessName = (id: string) => {
  if (!id || id === 'ALL') return '全部'
  return processMap[id] ? `${id} - ${processMap[id]}` : id
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
  emit('edit-equipment', props.equipment)
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
    emit('close-edit-equipment')
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

:deep(.equipment-priority-ghost) {
  background: #fffbeb !important;
}
</style>
