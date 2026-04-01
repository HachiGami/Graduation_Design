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
              <div class="sop-header">
                <span>总耗时: {{ totalSopDuration }} 分钟</span>
                <el-button type="primary" size="small" @click="openSopEditDialog">编辑 SOP</el-button>
              </div>
              <div v-if="localActivity.sop_steps?.length">
                <div v-for="(step, index) in localActivity.sop_steps" :key="index" class="sop-row">
                  <el-tag size="small" type="info">步骤 {{ index + 1 }}</el-tag>
                  <span>{{ step.content }} (耗时: {{ step.duration }} 分钟)</span>
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

        <el-tab-pane label="资源分配" name="resources" lazy>
          <ActivityResourcesPanel :activity-id="activityId" />
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
      <el-form-item label="流程ID" prop="process_id">
        <el-select 
          v-model="editForm.process_id" 
          placeholder="请选择所属流程ID" 
          style="width: 100%"
          @change="handleProcessIdChange"
        >
          <el-option
            v-for="item in processOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <div style="display: flex; justify-content: space-between; width: 100%;">
        <el-button type="danger" @click="handleDeleteActivity">删除该活动</el-button>
        <div>
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveActivityEdit">保存</el-button>
        </div>
      </div>
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

  <el-dialog v-model="sopDialogVisible" title="编辑活动 SOP 与详情" width="700px">
    <el-form :model="sopEditForm" label-width="100px">
      <el-form-item label="活动描述">
        <el-input type="textarea" v-model="sopEditForm.description" :rows="3" />
      </el-form-item>
      
      <div class="sop-edit-section">
        <div class="section-title">
          <span>SOP 步骤列表</span>
          <span class="total-hint">当前总耗时: {{ currentSopTotalDuration }} 分钟</span>
        </div>
        
        <div v-for="(step, index) in sopEditForm.sop_steps" :key="index" class="sop-step-item">
          <el-tag type="info" class="step-tag">步骤 {{ index + 1 }}</el-tag>
          <el-input v-model="step.content" placeholder="请输入步骤详情" class="flex-1" />
          <el-input-number v-model="step.duration" :min="0" placeholder="耗时(分)" class="duration-input" />
          <el-button type="danger" icon="Delete" circle @click="removeSopStep(index)" />
        </div>
        
        <el-button type="primary" plain class="w-full mt-4" @click="addSopStep">
          + 添加新步骤
        </el-button>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="sopDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="saveSopEdit">保存 SOP</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { Activity } from '@/types'
import type { RiskItem } from '@/api/analytics'
import ActivityResourcesPanel from './ActivityResourcesPanel.vue'
import { getRisks } from '@/api/analytics'
import {
  getActivity,
  updateActivity,
  deleteActivity
} from '@/api/activity'
import { ElMessageBox } from 'element-plus'

const props = defineProps<{ activity: Activity }>()
const emit = defineEmits<{ refreshed: [] }>()
const router = useRouter()

const localActivity = ref<Activity>({ ...props.activity })
const activeTab = ref('basic')
const activityRisks = ref<RiskItem[]>([])
const editDialogVisible = ref(false)
const sopDialogVisible = ref(false)
const replenishDialogVisible = ref(false)

const editForm = ref<Partial<Activity>>({})
const sopEditForm = ref({
  description: '',
  sop_steps: [] as { content: string, duration: number }[]
})

const currentSopTotalDuration = computed(() => {
  return sopEditForm.value.sop_steps.reduce((sum, step) => sum + (step.duration || 0), 0)
})

// 定义流程域下拉选项
const domainOptions = [
  { label: '生产 (production)', value: 'production' },
  { label: '质检 (quality)', value: 'quality' },
  { label: '仓储 (warehouse)', value: 'warehouse' },
  { label: '运输 (transport)', value: 'transport' },
  { label: '销售 (sales)', value: 'sales' }
];

// 定义/引入黄金映射字典
const processMap: Record<string, string> = {
  'P001': '主生产线', 'P002': '副生产线',
  'T001': '冷链运输', 'T002': '常温运输',
  'S001': '线上销售', 'S002': '线下销售',
  'Q001': '常规质检', 'Q002': '专项质检',
  'W001': '主仓库', 'W002': '分仓库'
};

// 将字典转换为 el-select 需要的数组格式
const processOptions = Object.entries(processMap).map(([value, label]) => ({
  value,
  label: `${value} - ${label}`
}));

const prefixToDomainMap: Record<string, string> = {
  'P': 'production',
  'T': 'transport',
  'S': 'sales',
  'Q': 'quality',
  'W': 'warehouse'
};

const handleProcessIdChange = (newProcessId: string) => {
  if (!newProcessId) return;
  const prefix = newProcessId.charAt(0).toUpperCase();
  if (prefixToDomainMap[prefix]) {
    // 自动将隐藏的 domain 字段设置为对应的值，以便提交给后端
    editForm.value.domain = prefixToDomainMap[prefix];
  }
};

const activityId = computed(() => localActivity.value.id || '')
const totalSopDuration = computed(() => {
  if (!localActivity.value.sop_steps || localActivity.value.sop_steps.length === 0) return localActivity.value.estimated_duration || 0;
  return localActivity.value.sop_steps.reduce((sum, step) => sum + (step.duration || 0), 0);
});
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

const openSopEditDialog = () => {
  sopEditForm.value = {
    description: localActivity.value.description || '',
    sop_steps: localActivity.value.sop_steps ? JSON.parse(JSON.stringify(localActivity.value.sop_steps)) : []
  }
  sopDialogVisible.value = true
}

const addSopStep = () => {
  sopEditForm.value.sop_steps.push({ content: '', duration: 0 })
}

const removeSopStep = (index: number) => {
  sopEditForm.value.sop_steps.splice(index, 1)
}

const saveSopEdit = async () => {
  if (!activityId.value) return
  try {
    const payload = {
      description: sopEditForm.value.description,
      sop_steps: sopEditForm.value.sop_steps,
      estimated_duration: currentSopTotalDuration.value
    }
    await updateActivity(activityId.value, payload)
    ElMessage.success('SOP 已更新')
    sopDialogVisible.value = false
    await refreshActivityAndRisk()
  } catch (error) {
    ElMessage.error('更新 SOP 失败')
  }
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

const handleDeleteActivity = async () => {
  if (!activityId.value) return
  try {
    await ElMessageBox.confirm(
      '此操作将从数据库和图谱中永久删除该活动及其所有关联数据，是否继续？',
      '警告',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteActivity(activityId.value)
    ElMessage.success('活动已删除')
    editDialogVisible.value = false
    emit('refreshed')
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error('删除失败')
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

.sop-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  background: #f5f7fa;
  padding: 8px 12px;
  border-radius: 4px;
  font-weight: bold;
}

.sop-edit-section {
  margin-top: 20px;
  border-top: 1px solid #ebeef5;
  padding-top: 20px;
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  font-weight: bold;
  color: #303133;
}

.total-hint {
  color: #409eff;
  font-size: 14px;
}

.sop-step-item {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  align-items: center;
}

.step-tag {
  flex-shrink: 0;
  width: 60px;
  text-align: center;
}

.duration-input {
  width: 130px;
}

.w-full {
  width: 100%;
}

.mt-4 {
  margin-top: 16px;
}

.flex-1 {
  flex: 1;
}

.risk-alert {
  margin-bottom: 10px;
}

.form-row {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  align-items: center;
}

.replenish-tip {
  margin-bottom: 12px;
}
</style>
