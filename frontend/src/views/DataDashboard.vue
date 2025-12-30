<template>
  <div class="data-dashboard">
    <h2>数据面板</h2>
    
    <el-tabs v-model="activeTab">
      <el-tab-pane label="资源分配" name="resources">
        <AGGridTable 
          :columnDefs="resourceColumns" 
          :rowData="resources"
          height="500px"
        />
      </el-tab-pane>
      
      <el-tab-pane label="人力使用" name="personnel">
        <AGGridTable 
          :columnDefs="personnelColumns" 
          :rowData="personnel"
          height="500px"
        />
      </el-tab-pane>
      
      <el-tab-pane label="生产活动状态" name="activities">
        <AGGridTable 
          :columnDefs="activityColumns" 
          :rowData="activities"
          height="500px"
        />
      </el-tab-pane>
      
      <el-tab-pane label="依赖关系" name="dependencies">
        <AGGridTable 
          :columnDefs="dependencyColumns" 
          :rowData="dependencies"
          height="500px"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import AGGridTable from '@/components/AGGridTable.vue'
import { getResources } from '@/api/resource'
import { getPersonnel } from '@/api/personnel'
import { getActivities } from '@/api/activity'
import { getDependencies } from '@/api/dependency'

const activeTab = ref('resources')
const resources = ref<any[]>([])
const personnel = ref<any[]>([])
const activities = ref<any[]>([])
const dependencies = ref<any[]>([])

const resourceColumns = [
  { field: 'name', headerName: '资源名称', filter: true },
  { field: 'type', headerName: '类型', filter: true },
  { field: 'specification', headerName: '规格' },
  { field: 'supplier', headerName: '供应商' },
  { 
    field: 'quantity', 
    headerName: '数量',
    valueFormatter: (params: any) => `${params.value} ${params.data.unit}`
  },
  { 
    field: 'status', 
    headerName: '状态',
    cellStyle: (params: any) => {
      return params.value === 'available' 
        ? { color: 'green' } 
        : { color: 'red' }
    }
  },
  { 
    field: 'created_at', 
    headerName: '创建时间',
    valueFormatter: (params: any) => {
      return params.value ? new Date(params.value).toLocaleString('zh-CN') : ''
    }
  }
]

const personnelColumns = [
  { field: 'name', headerName: '姓名' },
  { field: 'role', headerName: '角色' },
  { field: 'responsibility', headerName: '职责' },
  { 
    field: 'skills', 
    headerName: '技能',
    valueFormatter: (params: any) => params.value?.join(', ') || ''
  },
  { field: 'work_hours', headerName: '工作时间' },
  { 
    field: 'assigned_tasks', 
    headerName: '任务数量',
    valueGetter: (params: any) => params.data.assigned_tasks?.length || 0
  },
  { field: 'status', headerName: '状态' }
]

const activityColumns = [
  { field: 'name', headerName: '活动名称' },
  { field: 'activity_type', headerName: '类型' },
  { field: 'description', headerName: '描述' },
  { 
    field: 'estimated_duration', 
    headerName: '预计时长',
    valueFormatter: (params: any) => `${params.value}分钟`
  },
  { 
    field: 'sop_steps', 
    headerName: 'SOP步骤数',
    valueGetter: (params: any) => params.data.sop_steps?.length || 0
  },
  { 
    field: 'required_resources', 
    headerName: '所需资源数',
    valueGetter: (params: any) => params.data.required_resources?.length || 0
  },
  { 
    field: 'required_personnel', 
    headerName: '所需人员数',
    valueGetter: (params: any) => params.data.required_personnel?.length || 0
  },
  { field: 'status', headerName: '状态' }
]

const dependencyColumns = [
  { field: 'name', headerName: '名称' },
  { field: 'predecessor_stage', headerName: '前置环节' },
  { field: 'successor_stage', headerName: '后置环节' },
  { field: 'dependency_type', headerName: '依赖类型' },
  { 
    field: 'time_constraint', 
    headerName: '时间约束',
    valueFormatter: (params: any) => params.value ? `${params.value}分钟` : '-'
  },
  { field: 'condition', headerName: '条件' }
]

const loadAllData = async () => {
  try {
    const [resourcesData, personnelData, activitiesData, dependenciesData] = await Promise.all([
      getResources(),
      getPersonnel(),
      getActivities(),
      getDependencies()
    ])
    
    resources.value = resourcesData.map(item => ({
      ...item,
      id: item.id || item._id
    }))
    personnel.value = personnelData.map(item => ({
      ...item,
      id: item.id || item._id
    }))
    activities.value = activitiesData.map(item => ({
      ...item,
      id: item.id || item._id
    }))
    dependencies.value = dependenciesData.map(item => ({
      ...item,
      id: item.id || item._id
    }))
  } catch (error) {
    ElMessage.error('加载数据失败')
  }
}

onMounted(() => {
  loadAllData()
})
</script>

<style scoped>
.data-dashboard {
  padding: 20px;
}

h2 {
  margin-bottom: 20px;
}
</style>

