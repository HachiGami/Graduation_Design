<template>
  <div class="activity-management">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>生产活动管理</span>
          <el-button type="primary" @click="handleAdd">添加活动</el-button>
        </div>
      </template>
      
      <el-table :data="activities" stripe>
        <el-table-column prop="name" label="活动名称" />
        <el-table-column prop="activity_type" label="活动类型" />
        <el-table-column prop="estimated_duration" label="预计时长">
          <template #default="{ row }">
            {{ row.estimated_duration }}分钟
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'pending'" type="info">待执行</el-tag>
            <el-tag v-else-if="row.status === 'in_progress'" type="warning">进行中</el-tag>
            <el-tag v-else-if="row.status === 'completed'" type="success">已完成</el-tag>
            <el-tag v-else type="danger">已取消</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250">
          <template #default="{ row }">
            <el-button size="small" @click="handleViewDetail(row)">详情</el-button>
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑活动' : '添加活动'"
      width="700px"
    >
      <el-form :model="form" label-width="120px">
        <el-form-item label="活动名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="活动描述">
          <el-input v-model="form.description" type="textarea" rows="3" />
        </el-form-item>
        <el-form-item label="活动类型">
          <el-select v-model="form.activity_type">
            <el-option label="消毒" value="消毒" />
            <el-option label="加热" value="加热" />
            <el-option label="冷却" value="冷却" />
            <el-option label="包装" value="包装" />
            <el-option label="质检" value="质检" />
          </el-select>
        </el-form-item>
        <el-form-item label="预计时长（分钟）">
          <el-input-number v-model="form.estimated_duration" :min="1" />
        </el-form-item>
        <el-form-item label="截止时间">
          <el-date-picker 
            v-model="form.deadline" 
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
          />
        </el-form-item>
        <el-form-item label="SOP流程步骤">
          <div v-for="(step, index) in form.sop_steps" :key="index" style="margin-bottom: 10px;">
            <el-row :gutter="10">
              <el-col :span="3">
                <el-input-number v-model="step.step_number" :min="1" placeholder="步骤" style="width: 100%;" />
              </el-col>
              <el-col :span="12">
                <el-input v-model="step.description" placeholder="步骤描述" />
              </el-col>
              <el-col :span="5">
                <el-input-number v-model="step.duration" :min="1" placeholder="时长(分钟)" style="width: 100%;" />
              </el-col>
              <el-col :span="4">
                <el-button type="danger" size="small" @click="removeStep(index)">删除</el-button>
              </el-col>
            </el-row>
          </div>
          <el-button @click="addStep">添加步骤</el-button>
        </el-form-item>
        <el-form-item label="所需资源">
          <el-select v-model="form.required_resources" multiple placeholder="选择资源">
            <el-option 
              v-for="resource in resources" 
              :key="resource.id || (resource as any)._id" 
              :label="resource.name" 
              :value="resource.id || (resource as any)._id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="所需人员">
          <el-select v-model="form.required_personnel" multiple placeholder="选择人员">
            <el-option 
              v-for="person in personnel" 
              :key="person.id || (person as any)._id" 
              :label="person.name" 
              :value="person.id || (person as any)._id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status">
            <el-option label="待执行" value="pending" />
            <el-option label="进行中" value="in_progress" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="活动详情" width="800px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="活动名称">{{ detailData.name }}</el-descriptions-item>
        <el-descriptions-item label="活动类型">{{ detailData.activity_type }}</el-descriptions-item>
        <el-descriptions-item label="预计时长">{{ detailData.estimated_duration }}分钟</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag v-if="detailData.status === 'pending'" type="info">待执行</el-tag>
          <el-tag v-else-if="detailData.status === 'in_progress'" type="warning">进行中</el-tag>
          <el-tag v-else-if="detailData.status === 'completed'" type="success">已完成</el-tag>
          <el-tag v-else type="danger">已取消</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="活动描述" :span="2">{{ detailData.description }}</el-descriptions-item>
      </el-descriptions>

      <el-divider>SOP操作步骤</el-divider>
      <el-table :data="detailData.sop_steps" border>
        <el-table-column prop="step_number" label="步骤" width="80" />
        <el-table-column prop="description" label="操作描述" />
        <el-table-column prop="duration" label="所需时长" width="120">
          <template #default="{ row }">
            {{ row.duration }}分钟
          </template>
        </el-table-column>
      </el-table>

      <el-divider>资源需求</el-divider>
      <el-table :data="getDetailResources()" border>
        <el-table-column prop="name" label="资源名称" />
        <el-table-column prop="type" label="类型" />
        <el-table-column prop="specification" label="规格" />
        <el-table-column prop="quantity" label="数量">
          <template #default="{ row }">
            {{ row.quantity }}{{ row.unit }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'available'" type="success">可用</el-tag>
            <el-tag v-else type="danger">不可用</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <el-divider>人员需求</el-divider>
      <el-table :data="getDetailPersonnel()" border>
        <el-table-column prop="name" label="姓名" />
        <el-table-column prop="role" label="角色" />
        <el-table-column prop="responsibility" label="职责" />
        <el-table-column prop="skills" label="技能">
          <template #default="{ row }">
            {{ row.skills.join(', ') }}
          </template>
        </el-table-column>
        <el-table-column prop="work_hours" label="工作时间" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getActivities, createActivity, updateActivity, deleteActivity } from '@/api/activity'
import { getResources } from '@/api/resource'
import { getPersonnel } from '@/api/personnel'
import type { Activity, Resource, Personnel } from '@/types'

const activities = ref<Activity[]>([])
const resources = ref<Resource[]>([])
const personnel = ref<Personnel[]>([])
const dialogVisible = ref(false)
const detailVisible = ref(false)
const isEdit = ref(false)
const form = ref<Activity>({
  name: '',
  description: '',
  activity_type: '',
  sop_steps: [],
  estimated_duration: 0,
  required_resources: [],
  required_personnel: [],
  status: 'pending'
})
const detailData = ref<Activity>({
  name: '',
  description: '',
  activity_type: '',
  sop_steps: [],
  estimated_duration: 0,
  required_resources: [],
  required_personnel: [],
  status: 'pending'
})

const loadActivities = async () => {
  try {
    activities.value = await getActivities()
  } catch (error) {
    ElMessage.error('加载活动失败')
  }
}

const loadResources = async () => {
  try {
    resources.value = await getResources()
  } catch (error) {
    ElMessage.error('加载资源失败')
  }
}

const loadPersonnel = async () => {
  try {
    personnel.value = await getPersonnel()
  } catch (error) {
    ElMessage.error('加载人员失败')
  }
}

const getDetailResources = () => {
  if (!detailData.value.required_resources || detailData.value.required_resources.length === 0) return []
  return detailData.value.required_resources
    .map(id => resources.value.find(r => r.id === id || (r as any)._id === id))
    .filter(r => r !== undefined)
}

const getDetailPersonnel = () => {
  if (!detailData.value.required_personnel || detailData.value.required_personnel.length === 0) return []
  return detailData.value.required_personnel
    .map(id => personnel.value.find(p => p.id === id || (p as any)._id === id))
    .filter(p => p !== undefined)
}

const handleViewDetail = (row: Activity) => {
  detailData.value = { ...row }
  detailVisible.value = true
}

const handleAdd = () => {
  isEdit.value = false
  form.value = {
    name: '',
    description: '',
    activity_type: '',
    sop_steps: [],
    estimated_duration: 0,
    required_resources: [],
    required_personnel: [],
    status: 'pending'
  }
  dialogVisible.value = true
}

const handleEdit = (row: Activity) => {
  isEdit.value = true
  form.value = { 
    ...row,
    required_resources: (row.required_resources || []).filter(r => r != null),
    required_personnel: (row.required_personnel || []).filter(p => p != null)
  }
  dialogVisible.value = true
}

const addStep = () => {
  form.value.sop_steps.push({
    step_number: form.value.sop_steps.length + 1,
    description: '',
    duration: 0
  })
}

const removeStep = (index: number) => {
  form.value.sop_steps.splice(index, 1)
}

const handleSubmit = async () => {
  try {
    const activityId = form.value.id || (form.value as any)._id
    if (isEdit.value && activityId) {
      const submitData = {
        ...form.value,
        required_resources: form.value.required_resources.filter(r => r != null),
        required_personnel: form.value.required_personnel.filter(p => p != null)
      }
      delete (submitData as any)._id
      delete (submitData as any).created_at
      delete (submitData as any).updated_at
      await updateActivity(activityId, submitData)
      ElMessage.success('更新成功')
    } else {
      const submitData = {
        ...form.value,
        required_resources: form.value.required_resources.filter(r => r != null),
        required_personnel: form.value.required_personnel.filter(p => p != null)
      }
      await createActivity(submitData)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadActivities()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (row: Activity) => {
  try {
    await ElMessageBox.confirm('确定删除该活动?', '提示', {
      type: 'warning'
    })
    if (row.id) {
      await deleteActivity(row.id)
      ElMessage.success('删除成功')
      loadActivities()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadActivities()
  loadResources()
  loadPersonnel()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

