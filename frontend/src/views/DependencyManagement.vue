<template>
  <div class="dependency-management">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>依赖关系图</span>
          <el-button @click="loadGraphData">刷新</el-button>
        </div>
      </template>
      <DependencyGraph :data="graphData" />
    </el-card>

    <el-card style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>依赖关系管理</span>
          <el-button type="primary" @click="handleAdd">添加依赖</el-button>
        </div>
      </template>
      
      <el-table :data="dependencies" stripe>
        <el-table-column prop="source_activity_id" label="源活动ID" width="220" />
        <el-table-column prop="target_activity_id" label="目标活动ID" width="220" />
        <el-table-column prop="dependency_type" label="依赖类型">
          <template #default="{ row }">
            <el-tag v-if="row.dependency_type === 'sequential'" type="primary">顺序</el-tag>
            <el-tag v-else-if="row.dependency_type === 'parallel'" type="success">并行</el-tag>
            <el-tag v-else type="warning">条件</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="time_constraint" label="时间约束">
          <template #default="{ row }">
            {{ row.time_constraint ? row.time_constraint + '分钟' : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'active'" type="success">生效中</el-tag>
            <el-tag v-else-if="row.status === 'inactive'" type="info">未生效</el-tag>
            <el-tag v-else type="warning">待确认</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
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
      :title="isEdit ? '编辑依赖关系' : '添加依赖关系'"
      width="600px"
    >
      <el-form :model="form" label-width="120px">
        <el-form-item label="源活动">
          <el-select v-model="form.source_activity_id" placeholder="选择源活动" filterable>
            <el-option 
              v-for="activity in activities" 
              :key="activity.id" 
              :label="activity.name" 
              :value="activity.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="目标活动">
          <el-select v-model="form.target_activity_id" placeholder="选择目标活动" filterable>
            <el-option 
              v-for="activity in activities" 
              :key="activity.id" 
              :label="activity.name" 
              :value="activity.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="依赖类型">
          <el-select v-model="form.dependency_type">
            <el-option label="顺序" value="sequential" />
            <el-option label="并行" value="parallel" />
            <el-option label="条件" value="conditional" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间约束">
          <el-input-number v-model="form.time_constraint" :min="0" placeholder="分钟" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status">
            <el-option label="生效中" value="active" />
            <el-option label="未生效" value="inactive" />
            <el-option label="待确认" value="pending" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" />
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
import { getDependencies, createDependency, updateDependency, deleteDependency, getGraphData } from '@/api/dependency'
import { getActivities } from '@/api/activity'
import type { Dependency, GraphData, Activity } from '@/types'
import DependencyGraph from '@/components/DependencyGraph.vue'

const dependencies = ref<Dependency[]>([])
const activities = ref<Activity[]>([])
const graphData = ref<GraphData>({ nodes: [], edges: [] })
const dialogVisible = ref(false)
const isEdit = ref(false)
const form = ref<Dependency>({
  source_activity_id: '',
  target_activity_id: '',
  dependency_type: 'sequential',
  status: 'active'
})

const loadDependencies = async () => {
  try {
    dependencies.value = await getDependencies()
  } catch (error) {
    ElMessage.error('加载依赖关系失败')
  }
}

const loadActivities = async () => {
  try {
    activities.value = await getActivities()
  } catch (error) {
    ElMessage.error('加载活动失败')
  }
}

const loadGraphData = async () => {
  try {
    graphData.value = await getGraphData()
  } catch (error) {
    ElMessage.error('加载图数据失败')
  }
}

const handleAdd = () => {
  isEdit.value = false
  form.value = {
    source_activity_id: '',
    target_activity_id: '',
    dependency_type: 'sequential',
    status: 'active'
  }
  dialogVisible.value = true
}

const handleEdit = (row: Dependency) => {
  isEdit.value = true
  form.value = { ...row }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    if (isEdit.value && form.value.id) {
      await updateDependency(form.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createDependency(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadDependencies()
    loadGraphData()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (row: Dependency) => {
  try {
    await ElMessageBox.confirm('确定删除该依赖关系?', '提示', {
      type: 'warning'
    })
    if (row.id) {
      await deleteDependency(row.id)
      ElMessage.success('删除成功')
      loadDependencies()
      loadGraphData()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadActivities()
  loadDependencies()
  loadGraphData()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>





