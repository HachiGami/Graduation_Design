<template>
  <div class="equipment-accordion-item">
    <el-collapse-item :name="equipment._id">
      <template #title>
        <div class="header-content">
          <div class="left-info">
            <span class="equipment-name">{{ equipment.name }}</span>
            <el-tag size="small" type="info" class="spec-tag" v-if="equipment.specification">
              {{ equipment.specification }}
            </el-tag>
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
          <el-descriptions-item label="生产时间">
            {{ equipment.production_date || '暂无' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(equipment.status)" size="small">
              {{ getStatusLabel(equipment.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="型号">
            {{ equipment.model || '暂无' }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="serving-activities" v-if="equipment.serving_activities && equipment.serving_activities.length > 0">
          <span class="label">正在服务活动：</span>
          <el-tag 
            v-for="activity in equipment.serving_activities" 
            :key="activity" 
            size="small" 
            type="success" 
            class="activity-tag"
          >
            {{ activity }}
          </el-tag>
        </div>
        <div class="serving-activities empty" v-else>
          <span class="label">正在服务活动：</span>
          <span class="empty-text">无关联活动，安全</span>
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
        <el-form-item label="设备名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="设备型号">
          <el-input v-model="editForm.model" />
        </el-form-item>
        <el-form-item label="技术规格">
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
        <el-form-item label="状态">
          <el-select v-model="editForm.status" style="width: 100%">
            <el-option label="空闲" value="idle" />
            <el-option label="使用中" value="in_use" />
            <el-option label="维护中" value="maintenance" />
          </el-select>
        </el-form-item>
        <el-form-item label="正在服务活动">
          <el-select
            v-model="editForm.serving_activities"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="请选择或输入活动"
            style="width: 100%"
          >
            <el-option
              v-for="item in equipment.serving_activities || []"
              :key="item"
              :label="item"
              :value="item"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="未来检修日期">
          <el-select
            v-model="editForm.upcoming_maintenance"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="请选择或输入日期(YYYY-MM-DD)"
            style="width: 100%"
          >
            <el-option
              v-for="item in equipment.upcoming_maintenance || []"
              :key="item"
              :label="item"
              :value="item"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="isEditModalVisible = false">取消</el-button>
          <el-button type="primary" @click="submitEdit" :loading="isSubmitting">
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { Edit, Warning } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  equipment: any
}>()

const emit = defineEmits(['update'])

const isEditModalVisible = ref(false)
const isSubmitting = ref(false)
const editForm = reactive({
  name: '',
  model: '',
  specification: '',
  manufacturer: '',
  production_date: '',
  status: '',
  serving_activities: [] as string[],
  upcoming_maintenance: [] as string[]
})

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

const openEditModal = () => {
  editForm.name = props.equipment.name || ''
  editForm.model = props.equipment.model || ''
  editForm.specification = props.equipment.specification || ''
  editForm.manufacturer = props.equipment.manufacturer || ''
  editForm.production_date = props.equipment.production_date || ''
  editForm.status = props.equipment.status || 'idle'
  editForm.serving_activities = [...(props.equipment.serving_activities || [])]
  editForm.upcoming_maintenance = [...(props.equipment.upcoming_maintenance || [])]
  isEditModalVisible.value = true
}

const submitEdit = async () => {
  isSubmitting.value = true
  try {
    const response = await fetch(`http://localhost:8000/api/resources/${props.equipment._id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name: editForm.name,
        model: editForm.model,
        specification: editForm.specification,
        manufacturer: editForm.manufacturer,
        production_date: editForm.production_date,
        status: editForm.status,
        serving_activities: editForm.serving_activities,
        upcoming_maintenance: editForm.upcoming_maintenance
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

.serving-activities {
  margin-top: 16px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.label {
  font-size: 13px;
  color: #606266;
}

.empty-text {
  font-size: 13px;
  color: #909399;
  font-style: italic;
}
</style>
