<template>
  <div class="equipment-accordion-item">
    <el-collapse-item :name="equipment._id">
      <template #title>
        <div class="header-content">
          <div class="left-info">
            <span class="equipment-name">{{ equipment.name }}</span>
            <el-tag 
              v-if="equipment.upcoming_maintenance && equipment.upcoming_maintenance.length > 0" 
              size="small" 
              type="danger" 
              class="maintenance-tag"
            >
              <el-icon><Warning /></el-icon>
              下次检修: {{ equipment.upcoming_maintenance[0] }}
            </el-tag>
          </div>
          <div class="right-actions" @click.stop>
            <el-button type="warning" link size="small" @click="openMaintenanceModal">
              <el-icon><Tools /></el-icon> 检修
            </el-button>
            <el-button type="primary" link size="small" @click="openEditModal">
              <el-icon><Edit /></el-icon> 编辑设备
            </el-button>
          </div>
        </div>
      </template>

      <div class="body-content">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="生产厂家">
            {{ equipment.manufacturer || '暂无' }}
          </el-descriptions-item>
          <el-descriptions-item label="设备种类">
            {{ equipment.specification || '暂无' }}
          </el-descriptions-item>
          <el-descriptions-item label="生产时间">
            {{ equipment.production_date || '暂无' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(equipment.status)" size="small">
              {{ getStatusLabel(equipment.status) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div class="serving-activities-block" v-if="equipment.serving_activities_details && equipment.serving_activities_details.length > 0">
          <span class="label">正在服务活动：</span>
          <div
            v-for="(detail, index) in equipment.serving_activities_details"
            :key="index"
            class="activity-detail-row"
          >
            <span class="activity-name">{{ detail.activity_name }}</span>
            <el-tag size="small" :type="getActivityStatusType(detail.status)">
              {{ getActivityStatusLabel(detail.status) }}
            </el-tag>
            <span class="activity-meta">
              归属: {{ formatProcessName(detail.process_id) }}
            </span>
            <span class="activity-hours" v-if="detail.working_hours && detail.working_hours.length > 0">
              | 运行时间:
              {{ detail.working_hours.map((wh: any) => `${wh.start_time}-${wh.end_time}`).join(', ') }}
            </span>
          </div>
        </div>
        <div class="serving-activities empty" v-else>
          <span class="label">正在服务活动：</span>
          <span class="empty-text">无关联活动，空闲</span>
        </div>
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
import { Edit, Warning, Tools, Plus, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteResource } from '@/api/resource'

const props = defineProps<{
  equipment: any
}>()

const emit = defineEmits(['update'])

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

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    idle: 'info',
    in_use: 'success',
    maintenance: 'warning',
    available: 'success'
  }
  return map[status] || 'info'
}

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

const getActivityStatusType = (status: string) => {
  const normalized = (status || '').toLowerCase()
  if (normalized === 'in_progress' || normalized === '进行中') return 'success'
  if (normalized === 'stopped' || normalized === '已停机') return 'danger'
  return 'info'
}

const getActivityStatusLabel = (status: string) => {
  const normalized = (status || '').toLowerCase()
  if (normalized === 'in_progress' || normalized === '进行中') return '进行中'
  if (normalized === 'stopped' || normalized === '已停机') return '已停机'
  if (normalized === 'pending' || normalized === '待机') return '待机中'
  return status || '未知状态'
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
.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding-right: 16px;
}

.left-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.equipment-name {
  font-weight: bold;
  font-size: 15px;
}

.maintenance-tag {
  display: flex;
  align-items: center;
  gap: 4px;
}

.body-content {
  padding: 0 16px 16px;
}

.serving-activities-block {
  margin-top: 16px;
}

.serving-activities.empty {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.activity-detail-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
}

.activity-name {
  flex-shrink: 0;
  font-size: 13px;
  color: #303133;
  font-weight: 500;
}

.activity-meta {
  font-size: 12px;
  color: #606266;
}

.activity-hours {
  font-size: 12px;
  color: #409eff;
}

.label {
  font-size: 13px;
  color: #606266;
  font-weight: 500;
}

.empty-text {
  font-size: 13px;
  color: #909399;
  font-style: italic;
}
</style>
