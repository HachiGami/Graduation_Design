<template>
  <el-collapse class="activity-accordion">
    <el-collapse-item :name="localActivity.id || localActivity.name">
      <template #title>
        <div class="activity-header">
          <div class="header-left">
            <div class="title-row">
              <span class="activity-name">{{ localActivity.name }}</span>
              <el-tag :type="statusTagType(localActivity.status)" size="small">{{ statusText(localActivity.status) }}</el-tag>
              <el-tag size="small">{{ localActivity.domain }}</el-tag>
            </div>
            <div class="sub-row">工作时间：{{ workingHoursText }}</div>
          </div>
          <div class="header-right" @click.stop>
            <el-button 
              v-if="localActivity.status === 'pending'" 
              type="primary" 
              size="small" 
              @click="toggleActivityStatus"
            >▶️ 启动</el-button>
            <el-button 
              v-else-if="localActivity.status === 'in_progress'" 
              type="warning" 
              size="small" 
              @click="toggleActivityStatus"
            >⏸️ 停机</el-button>
            <el-button size="small" @click="openEditDialog">✏️修改</el-button>
            <el-button type="primary" size="small" @click="locateInDependencyView">👁️视图</el-button>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="基本信息与SOP" name="basic">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="活动描述">{{ localActivity.description || '无' }}</el-descriptions-item>
            <el-descriptions-item label="SOP步骤">
              <div v-if="localActivity.sop_steps?.length">
                <div v-for="step in localActivity.sop_steps" :key="`${step.step_number}-${step.description}`" class="sop-row">
                  <el-tag size="small" type="info">步骤{{ step.step_number }}</el-tag>
                  <span>{{ step.description }}（{{ step.duration }}分钟）</span>
                </div>
              </div>
              <span v-else>暂无SOP步骤</span>
            </el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>

        <el-tab-pane label="发生风险" name="risks">
          <el-empty v-if="activityRisks.length === 0" description="当前活动暂无风险" />
          <el-alert
            v-for="(risk, index) in activityRisks"
            :key="`${risk.message}-${index}`"
            :title="risk.message"
            type="error"
            show-icon
            :closable="false"
            class="risk-alert"
          >
            <template #default>
              <el-button
                v-if="risk.risk_type === 'material_shortage' && inferMaterialModelFromRisk(risk.message)"
                text
                type="primary"
                @click="openReplenishDialog(inferMaterialModelFromRisk(risk.message)!)"
              >
                一键补货
              </el-button>
            </template>
          </el-alert>
        </el-tab-pane>

        <el-tab-pane label="占用员工" name="personnel">
          <el-table :data="localActivity.personnel_requirements || []" size="small" border>
            <el-table-column prop="role" label="角色" />
            <el-table-column prop="count" label="人数" width="120" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button type="danger" text @click="removePersonnel(row.role)">移除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="form-row">
            <el-input v-model="personnelForm.role" placeholder="角色" />
            <el-input-number v-model="personnelForm.count" :min="1" />
            <el-button type="primary" @click="addPersonnel">添加员工</el-button>
          </div>
        </el-tab-pane>

        <el-tab-pane label="使用设备" name="equipment">
          <el-table :data="localActivity.equipment_requirements || []" size="small" border>
            <el-table-column prop="equipment_model" label="设备型号" />
            <el-table-column prop="count" label="数量" width="120" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button type="danger" text @click="removeEquipment(row.equipment_model)">移除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="form-row">
            <el-input v-model="equipmentForm.equipment_model" placeholder="设备型号" />
            <el-input-number v-model="equipmentForm.count" :min="1" />
            <el-button type="primary" @click="addEquipment">添加设备</el-button>
          </div>
        </el-tab-pane>

        <el-tab-pane label="消耗原料" name="materials">
          <el-table :data="localActivity.material_requirements || []" size="small" border>
            <el-table-column prop="material_model" label="原料型号" />
            <el-table-column label="每小时消耗量" width="160">
              <template #default="{ row }">
                {{ row.hourly_consumption_rate ?? perDayToHourly(row.consumption_rate_per_day) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="220">
              <template #default="{ row }">
                <el-button text type="danger" @click="removeMaterial(row.material_model)">移除</el-button>
                <el-button text type="primary" @click="openReplenishDialog(row.material_model)">补充库存</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="form-row">
            <el-select v-model="materialForm.material_model" filterable allow-create placeholder="原料型号">
              <el-option v-for="model in materialModelOptions" :key="model" :label="model" :value="model" />
            </el-select>
            <el-input-number v-model="materialForm.hourly_consumption_rate" :min="0" :step="0.1" />
            <el-input v-model="materialForm.unit" placeholder="单位(可选)" />
            <el-button type="primary" @click="addMaterial">添加原料</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-collapse-item>
  </el-collapse>

  <el-dialog v-model="editDialogVisible" title="修改活动" width="620px">
    <el-form :model="editForm" label-width="110px">
      <el-form-item label="活动名称"><el-input v-model="editForm.name" /></el-form-item>
      <el-form-item label="活动描述"><el-input v-model="editForm.description" type="textarea" /></el-form-item>
      <el-form-item label="状态">
        <el-select v-model="editForm.status">
          <el-option label="待机" value="pending" />
          <el-option label="进行中" value="in_progress" />
        </el-select>
      </el-form-item>
      <el-form-item label="流程域"><el-input v-model="editForm.domain" /></el-form-item>
      <el-form-item label="流程ID"><el-input v-model="editForm.process_id" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="saveActivityEdit">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="replenishDialogVisible" title="补充原料库存" width="420px">
    <div class="replenish-tip">请输入要补充的【{{ replenishForm.material_model }}】原料数量</div>
    <el-input-number v-model="replenishForm.added_quantity" :min="0.1" :step="1" style="width: 100%" />
    <template #footer>
      <el-button @click="replenishDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="submitReplenish">提交补货</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { Activity } from '@/types'
import type { RiskItem } from '@/api/analytics'
import { getRisks } from '@/api/analytics'
import { replenishMaterialStock, getAssets } from '@/api/asset'
import {
  addActivityEquipmentRequirement,
  addActivityMaterialRequirement,
  addActivityPersonnelRequirement,
  getActivity,
  removeActivityEquipmentRequirement,
  removeActivityMaterialRequirement,
  removeActivityPersonnelRequirement,
  updateActivity
} from '@/api/activity'

const props = defineProps<{ activity: Activity }>()
const emit = defineEmits<{ refreshed: [] }>()
const router = useRouter()

const localActivity = ref<Activity>({ ...props.activity })
const activeTab = ref('basic')
const activityRisks = ref<RiskItem[]>([])
const editDialogVisible = ref(false)
const replenishDialogVisible = ref(false)
const materialModelOptions = ref<string[]>([])

const personnelForm = ref({ role: '', count: 1 })
const equipmentForm = ref({ equipment_model: '', count: 1 })
const materialForm = ref({ material_model: '', hourly_consumption_rate: 1, unit: '' })
const replenishForm = ref({ material_model: '', added_quantity: 1 })
const editForm = ref<Partial<Activity>>({})

const activityId = computed(() => localActivity.value.id || '')
const workingHoursText = computed(() => {
  const windows = localActivity.value.working_hours || []
  if (windows.length === 0) return '未配置'
  return windows.map(w => `${w.start_time}-${w.end_time}`).join(' / ')
})

const statusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '待机',
    in_progress: '进行中'
  }
  return map[status] || status
}

const statusTagType = (status: string) => {
  const map: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = {
    pending: 'info',
    in_progress: 'primary'
  }
  return map[status] || ''
}

const toggleActivityStatus = async () => {
  if (!activityId.value) return
  const newStatus = localActivity.value.status === 'pending' ? 'in_progress' : 'pending'
  try {
    await updateActivity(activityId.value, { status: newStatus })
    ElMessage.success(`活动已${newStatus === 'in_progress' ? '启动' : '停机'}`)
    await refreshActivityAndRisk()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const perDayToHourly = (perDay?: number) => {
  if (!perDay || !Number.isFinite(perDay)) return 0
  return Number((perDay / 8).toFixed(2))
}

const inferMaterialModelFromRisk = (message: string) => {
  const match = message.match(/原料\[(.*?)\]/)
  return match?.[1] || ''
}

const locateInDependencyView = () => {
  if (!activityId.value) return
  router.push({
    name: 'Dependencies',
    query: {
      highlightDomain: localActivity.value.domain,
      focusActivity: activityId.value
    }
  })
}

const openEditDialog = () => {
  editForm.value = {
    name: localActivity.value.name,
    description: localActivity.value.description,
    status: localActivity.value.status,
    domain: localActivity.value.domain,
    process_id: localActivity.value.process_id
  }
  editDialogVisible.value = true
}

const refreshActivityAndRisk = async () => {
  await Promise.all([loadLatestActivity(), loadActivityRisks()])
  emit('refreshed')
}

const loadLatestActivity = async () => {
  if (!activityId.value) return
  const latest = await getActivity(activityId.value)
  if ((latest as any)._id && !latest.id) latest.id = (latest as any)._id
  localActivity.value = latest
}

const loadActivityRisks = async () => {
  try {
    const list = await getRisks(localActivity.value.domain)
    activityRisks.value = list.filter((item: RiskItem) => item.activity_name === localActivity.value.name)
  } catch (error) {
    activityRisks.value = []
  }
}

const loadMaterialOptions = async () => {
  try {
    const assets = await getAssets({ asset_type: 'material' })
    materialModelOptions.value = [...new Set(assets.map(item => item.model).filter(Boolean))]
  } catch (error) {
    materialModelOptions.value = []
  }
}

watch(
  () => props.activity,
  (next) => {
    localActivity.value = { ...next }
    void loadActivityRisks()
  },
  { deep: true, immediate: true }
)

watch(activeTab, async (tab) => {
  if (tab === 'risks') await loadActivityRisks()
  if (tab === 'materials') await loadMaterialOptions()
})

const saveActivityEdit = async () => {
  if (!activityId.value) return
  try {
    await updateActivity(activityId.value, editForm.value)
    ElMessage.success('活动已更新')
    editDialogVisible.value = false
    await refreshActivityAndRisk()
  } catch (error) {
    ElMessage.error('更新活动失败')
  }
}

const addPersonnel = async () => {
  if (!activityId.value || !personnelForm.value.role.trim()) return
  try {
    await addActivityPersonnelRequirement(activityId.value, { ...personnelForm.value })
    personnelForm.value = { role: '', count: 1 }
    await refreshActivityAndRisk()
  } catch (error) {
    ElMessage.error('添加员工需求失败')
  }
}

const removePersonnel = async (role: string) => {
  if (!activityId.value) return
  try {
    await removeActivityPersonnelRequirement(activityId.value, role)
    await refreshActivityAndRisk()
  } catch (error) {
    ElMessage.error('移除员工需求失败')
  }
}

const addEquipment = async () => {
  if (!activityId.value || !equipmentForm.value.equipment_model.trim()) return
  try {
    await addActivityEquipmentRequirement(activityId.value, { ...equipmentForm.value })
    equipmentForm.value = { equipment_model: '', count: 1 }
    await refreshActivityAndRisk()
  } catch (error) {
    ElMessage.error('添加设备需求失败')
  }
}

const removeEquipment = async (model: string) => {
  if (!activityId.value) return
  try {
    await removeActivityEquipmentRequirement(activityId.value, model)
    await refreshActivityAndRisk()
  } catch (error) {
    ElMessage.error('移除设备需求失败')
  }
}

const addMaterial = async () => {
  if (!activityId.value || !materialForm.value.material_model.trim()) return
  try {
    await addActivityMaterialRequirement(activityId.value, {
      material_model: materialForm.value.material_model,
      hourly_consumption_rate: materialForm.value.hourly_consumption_rate,
      unit: materialForm.value.unit
    })
    materialForm.value = { material_model: '', hourly_consumption_rate: 1, unit: '' }
    await refreshActivityAndRisk()
  } catch (error) {
    ElMessage.error('添加原料需求失败')
  }
}

const removeMaterial = async (materialModel: string) => {
  if (!activityId.value) return
  try {
    await removeActivityMaterialRequirement(activityId.value, materialModel)
    await refreshActivityAndRisk()
  } catch (error) {
    ElMessage.error('移除原料需求失败')
  }
}

const openReplenishDialog = (materialModel: string) => {
  replenishForm.value = { material_model: materialModel, added_quantity: 1 }
  activeTab.value = 'materials'
  replenishDialogVisible.value = true
}

const submitReplenish = async () => {
  const { material_model, added_quantity } = replenishForm.value
  if (!material_model || added_quantity <= 0) return
  try {
    await replenishMaterialStock(material_model, added_quantity)
    ElMessage.success('库存补充成功，正在重新计算风险')
    replenishDialogVisible.value = false
    await refreshActivityAndRisk()
  } catch (error) {
    ElMessage.error('补充库存失败')
  }
}
</script>

<style scoped>
.activity-accordion {
  margin-bottom: 12px;
}

.activity-header {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.activity-name {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
}

.sub-row {
  color: #606266;
  font-size: 12px;
}

.header-right {
  display: flex;
  gap: 8px;
}

.sop-row {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.risk-alert {
  margin-bottom: 10px;
}

.form-row {
  margin-top: 12px;
  display: grid;
  grid-template-columns: 1fr 140px 160px 120px;
  gap: 8px;
  align-items: center;
}

.replenish-tip {
  margin-bottom: 12px;
}
</style>
