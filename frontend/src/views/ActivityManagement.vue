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
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
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
              <el-col :span="4">
                <el-input-number v-model="step.step_number" :min="1" placeholder="步骤" />
              </el-col>
              <el-col :span="12">
                <el-input v-model="step.description" placeholder="步骤描述" />
              </el-col>
              <el-col :span="6">
                <el-input-number v-model="step.duration" :min="1" placeholder="时长(分钟)" />
              </el-col>
              <el-col :span="2">
                <el-button type="danger" @click="removeStep(index)">删除</el-button>
              </el-col>
            </el-row>
          </div>
          <el-button @click="addStep">添加步骤</el-button>
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getActivities, createActivity, updateActivity, deleteActivity } from '@/api/activity'
import type { Activity, SOPStep } from '@/types'

const activities = ref<Activity[]>([])
const dialogVisible = ref(false)
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

const loadActivities = async () => {
  try {
    activities.value = await getActivities()
  } catch (error) {
    ElMessage.error('加载活动失败')
  }
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
  form.value = { ...row }
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
    if (isEdit.value && form.value.id) {
      await updateActivity(form.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createActivity(form.value)
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
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

