<template>
  <div class="dependency-management">
    <el-card class="fullscreen-container">
      <template #header>
        <div class="card-header">
          <span>节点关联视图</span>
          <div class="header-actions">
            <el-button @click="loadGraphData" :icon="'Refresh'">刷新</el-button>
            <el-button type="primary" @click="handleAddDependency" :icon="'Plus'">添加依赖</el-button>
            <el-button type="success" @click="handleAddActivity" :icon="'Plus'">添加活动</el-button>
            <el-button type="warning" @click="handleAddResource" :icon="'Plus'">添加资源</el-button>
            <el-button type="info" @click="handleAddPersonnel" :icon="'Plus'">添加人员</el-button>
          </div>
        </div>
      </template>
      
      <div class="toolbar">
        <ProcessSelector
          :domain="currentDomain"
          :process-id="currentProcessId"
          @change="handleProcessChange"
          @clear="clearFlowHighlight"
        />
        
        <div class="mini-kpi-hud">
          <div class="mini-kpi-item" @click="handleKpiClick('activities')">
            <div class="mini-value">{{ metrics.activityCount }}</div>
            <div class="mini-label">活动数</div>
          </div>
          <div class="mini-kpi-item" @click="handleKpiClick('dependencies')">
            <div class="mini-value">{{ metrics.internalDependencyCount }}</div>
            <div class="mini-label">内部依赖</div>
          </div>
          <div class="mini-kpi-item" @click="handleKpiClick('health')">
            <div class="mini-value">{{ metrics.healthScore }}</div>
            <div class="mini-label">健康评分</div>
          </div>
          <div class="mini-kpi-item" @click="handleKpiClick('cpm')">
            <div class="mini-value">{{ metrics.totalDuration }}</div>
            <div class="mini-label">总工期</div>
          </div>
          <div class="mini-kpi-item" @click="handleKpiClick('resource')">
            <div class="mini-value">{{ miniRunnableTimeText }}</div>
            <div class="mini-label">可运行时间</div>
          </div>
          <div class="mini-kpi-item" @click="handleKpiClick('dynamic')">
            <div class="mini-value">{{ riskList.length }}</div>
            <div class="mini-label">风险数</div>
          </div>
        </div>
      </div>
      
      <div class="main-layout">
        <div class="graph-panel">
          <DependencyGraph 
            :data="graphData" 
            :highlight-active="highlightActive"
            :highlight-set="highlightSet"
            @node-click="handleNodeClick"
            @edit-activity="handleEditActivityFromGraph"
            @edit-personnel="handleEditPersonnelFromGraph"
            @edit-resource="handleEditResourceFromGraph"
          />
        </div>
        
        <aside class="sidebar">
          <DashboardPanel
            mode="sidebar"
            :graph-data="graphData"
            :current-process-id="currentProcessId"
            :current-domain="currentDomain"
            :min-runnable-days="minRunnableDays"
            :risk-count="riskList.length"
            :risk-list="riskList"
            @highlight-request="handleDashboardHighlight"
            @process-select="handleProcessSelect"
            @clear-highlight="clearDashboardHighlight"
          />
        </aside>
      </div>
    </el-card>

    <!-- 依赖关系对话框 -->
    <el-dialog 
      v-model="dependencyDialogVisible" 
      :title="isEditDependency ? '编辑依赖关系' : '添加依赖关系'"
      width="600px"
    >
      <el-form :model="dependencyForm" label-width="120px">
        <el-form-item label="源活动">
          <el-select v-model="dependencyForm.source_activity_id" placeholder="选择源活动" filterable>
            <el-option 
              v-for="activity in activities" 
              :key="activity.id" 
              :label="activity.name" 
              :value="activity.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="目标活动">
          <el-select v-model="dependencyForm.target_activity_id" placeholder="选择目标活动" filterable>
            <el-option 
              v-for="activity in activities" 
              :key="activity.id" 
              :label="activity.name" 
              :value="activity.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="依赖类型">
          <el-select v-model="dependencyForm.dependency_type">
            <el-option label="顺序" value="sequential" />
            <el-option label="并行" value="parallel" />
            <el-option label="条件" value="conditional" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间约束">
          <el-input-number v-model="dependencyForm.time_constraint" :min="0" placeholder="分钟" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="dependencyForm.status">
            <el-option label="生效中" value="active" />
            <el-option label="未生效" value="inactive" />
            <el-option label="待确认" value="pending" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="dependencyForm.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dependencyDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleDependencySubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 活动详情对话框 -->
    <el-dialog 
      v-model="activityDialogVisible" 
      :title="isEditActivity ? '编辑活动' : (currentActivity?.id ? '活动详情' : '添加活动')"
      width="800px"
    >
      <!-- 详情展示模式 -->
      <div v-if="currentActivity?.id && !isEditActivity">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="活动名称" :span="2">{{ activityForm.name }}</el-descriptions-item>
          <el-descriptions-item label="活动类型">{{ getDomainName(activityForm.domain) || '未知' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag v-if="activityForm.status === 'pending'" type="info">待开始</el-tag>
            <el-tag v-else-if="activityForm.status === 'in_progress'" type="warning">进行中</el-tag>
            <el-tag v-else-if="activityForm.status === 'completed'" type="success">已完成</el-tag>
            <el-tag v-else-if="activityForm.status === 'paused'" type="warning">已暂停</el-tag>
            <el-tag v-else type="danger">已取消</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="预计时长">{{ activityForm.estimated_duration }} 分钟</el-descriptions-item>
          <el-descriptions-item label="截止日期">{{ activityForm.deadline || '未设置' }}</el-descriptions-item>
          <el-descriptions-item label="流程ID">{{ activityForm.process_id }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{ activityForm.version || 1 }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ activityForm.description || '无' }}</el-descriptions-item>
          
          <el-descriptions-item label="SOP步骤" :span="2">
            <div v-if="activityForm.sop_steps && activityForm.sop_steps.length > 0">
              <div v-for="(step, index) in activityForm.sop_steps" :key="index" style="margin-bottom: 8px;">
                <el-tag type="primary" style="margin-right: 8px;">步骤{{ step.step_number }}</el-tag>
                {{ step.description }} ({{ step.duration }}分钟)
              </div>
            </div>
            <span v-else>无</span>
          </el-descriptions-item>
          
          <el-descriptions-item label="所需资源" :span="2">
            <div v-if="activityForm.required_resources && activityForm.required_resources.length > 0">
              <el-tag v-for="resourceId in activityForm.required_resources" :key="resourceId" style="margin-right: 5px;">
                {{ getResourceNameById(resourceId) }}
              </el-tag>
            </div>
            <span v-else>无</span>
          </el-descriptions-item>
          
          <el-descriptions-item label="所需人员" :span="2">
            <div v-if="activityForm.required_personnel && activityForm.required_personnel.length > 0">
              <el-tag v-for="personnelId in activityForm.required_personnel" :key="personnelId" style="margin-right: 5px;" type="success">
                {{ getPersonnelNameById(personnelId) }}
              </el-tag>
            </div>
            <span v-else>无</span>
          </el-descriptions-item>
          
          <el-descriptions-item label="创建时间" v-if="activityForm.created_at">
            {{ new Date(activityForm.created_at).toLocaleString('zh-CN') }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间" v-if="activityForm.updated_at">
            {{ new Date(activityForm.updated_at).toLocaleString('zh-CN') }}
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 编辑/添加模式 -->
      <el-form v-else :model="activityForm" label-width="120px">
        <el-form-item label="活动名称">
          <el-input v-model="activityForm.name" />
        </el-form-item>
        <el-form-item label="活动类型">
          <el-input v-model="activityForm.activity_type" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="activityForm.description" type="textarea" />
        </el-form-item>
        <el-form-item label="预计时长">
          <el-input-number v-model="activityForm.estimated_duration" :min="0" />
          <span style="margin-left: 10px;">分钟</span>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="activityForm.status">
            <el-option label="待开始" value="pending" />
            <el-option label="进行中" value="in_progress" />
            <el-option label="已完成" value="completed" />
            <el-option label="已暂停" value="paused" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <div style="display: flex; justify-content: space-between;">
          <div>
            <el-button v-if="currentActivity?.id && !isEditActivity" type="primary" @click="isEditActivity = true">编辑</el-button>
            <el-button v-if="currentActivity?.id" type="danger" @click="handleDeleteActivity">删除</el-button>
          </div>
          <div>
            <el-button @click="closeActivityDialog">{{ currentActivity?.id && !isEditActivity ? '关闭' : '取消' }}</el-button>
            <el-button v-if="!currentActivity?.id || isEditActivity" type="primary" @click="handleActivitySubmit">确定</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 资源详情对话框 -->
    <el-dialog 
      v-model="resourceDialogVisible" 
      :title="isEditResource ? '编辑资源' : (currentResource?.id ? '资源详情' : '添加资源')"
      width="600px"
    >
      <!-- 详情展示模式 -->
      <div v-if="currentResource?.id && !isEditResource">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="资源名称" :span="2">{{ resourceForm.name }}</el-descriptions-item>
          <el-descriptions-item label="资源类型">{{ resourceForm.type }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag v-if="resourceForm.status === 'available'" type="success">可用</el-tag>
            <el-tag v-else-if="resourceForm.status === 'in_use'" type="warning">使用中</el-tag>
            <el-tag v-else-if="resourceForm.status === 'maintenance'" type="info">维护中</el-tag>
            <el-tag v-else type="danger">不可用</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="规格" :span="2">{{ resourceForm.specification }}</el-descriptions-item>
          <el-descriptions-item label="供应商">{{ resourceForm.supplier }}</el-descriptions-item>
          <el-descriptions-item label="单位">{{ resourceForm.unit }}</el-descriptions-item>
          <el-descriptions-item label="数量">{{ resourceForm.quantity }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 编辑/添加模式 -->
      <el-form v-else :model="resourceForm" label-width="120px">
        <el-form-item label="资源名称">
          <el-input v-model="resourceForm.name" />
        </el-form-item>
        <el-form-item label="资源类型">
          <el-input v-model="resourceForm.type" />
        </el-form-item>
        <el-form-item label="规格">
          <el-input v-model="resourceForm.specification" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="resourceForm.supplier" />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="resourceForm.quantity" :min="0" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="resourceForm.unit" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="resourceForm.status">
            <el-option label="可用" value="available" />
            <el-option label="使用中" value="in_use" />
            <el-option label="维护中" value="maintenance" />
            <el-option label="不可用" value="unavailable" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <div style="display: flex; justify-content: space-between;">
          <div>
            <el-button v-if="currentResource?.id && !isEditResource" type="primary" @click="isEditResource = true">编辑</el-button>
            <el-button v-if="currentResource?.id" type="danger" @click="handleDeleteResource">删除</el-button>
          </div>
          <div>
            <el-button @click="closeResourceDialog">{{ currentResource?.id && !isEditResource ? '关闭' : '取消' }}</el-button>
            <el-button v-if="!currentResource?.id || isEditResource" type="primary" @click="handleResourceSubmit">确定</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 人员详情对话框 -->
    <el-dialog 
      v-model="personnelDialogVisible" 
      :title="isEditPersonnel ? '编辑人员' : (currentPersonnel?.id ? '人员详情' : '添加人员')"
      width="600px"
    >
      <!-- 详情展示模式 -->
      <div v-if="currentPersonnel?.id && !isEditPersonnel">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="姓名" :span="2">{{ personnelForm.name }}</el-descriptions-item>
          <el-descriptions-item label="角色">{{ personnelForm.role }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag v-if="personnelForm.status === 'available'" type="success">可用</el-tag>
            <el-tag v-else-if="personnelForm.status === 'busy'" type="warning">忙碌</el-tag>
            <el-tag v-else-if="personnelForm.status === 'on_leave'" type="info">休假</el-tag>
            <el-tag v-else type="danger">离职</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="职责" :span="2">{{ personnelForm.responsibility }}</el-descriptions-item>
          <el-descriptions-item label="工作时间" :span="2">{{ personnelForm.work_hours }}</el-descriptions-item>
          <el-descriptions-item label="技能" :span="2">
            <el-tag v-for="skill in personnelForm.skills" :key="skill" style="margin-right: 5px;">{{ skill }}</el-tag>
            <span v-if="!personnelForm.skills || personnelForm.skills.length === 0">无</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 编辑/添加模式 -->
      <el-form v-else :model="personnelForm" label-width="120px">
        <el-form-item label="姓名">
          <el-input v-model="personnelForm.name" />
        </el-form-item>
        <el-form-item label="角色">
          <el-input v-model="personnelForm.role" />
        </el-form-item>
        <el-form-item label="职责">
          <el-input v-model="personnelForm.responsibility" type="textarea" />
        </el-form-item>
        <el-form-item label="技能">
          <el-select v-model="personnelForm.skills" multiple filterable allow-create placeholder="输入技能">
            <el-option 
              v-for="skill in personnelForm.skills" 
              :key="skill" 
              :label="skill" 
              :value="skill" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="工作时间">
          <el-input v-model="personnelForm.work_hours" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="personnelForm.status">
            <el-option label="可用" value="available" />
            <el-option label="忙碌" value="busy" />
            <el-option label="休假" value="on_leave" />
            <el-option label="离职" value="resigned" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <div style="display: flex; justify-content: space-between;">
          <div>
            <el-button v-if="currentPersonnel?.id && !isEditPersonnel" type="primary" @click="isEditPersonnel = true">编辑</el-button>
            <el-button v-if="currentPersonnel?.id" type="danger" @click="handleDeletePersonnel">删除</el-button>
          </div>
          <div>
            <el-button @click="closePersonnelDialog">{{ currentPersonnel?.id && !isEditPersonnel ? '关闭' : '取消' }}</el-button>
            <el-button v-if="!currentPersonnel?.id || isEditPersonnel" type="primary" @click="handlePersonnelSubmit">确定</el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { createDependency, updateDependency, getGraphData } from '@/api/dependency'
import { getActivities, getActivity, createActivity, updateActivity, deleteActivity } from '@/api/activity'
import { getResources, getResource, createResource, updateResource, deleteResource } from '@/api/resource'
import { getPersonnelList as getPersonnel, getPersonnelById, createPersonnel, updatePersonnel, deletePersonnel } from '@/api/personnel'
import type { Dependency, GraphData, Activity, Resource, Personnel } from '@/types'
import DependencyGraph from '@/components/DependencyGraph.vue'
import ProcessSelector from '@/components/ProcessSelector.vue'
import DashboardPanel from '@/components/DashboardPanel.vue'
import { analyzeGraph, type AnalysisScope } from '@/utils/graphAnalyzer'
import { calculateCPM } from '@/utils/cpmCalculator'
import { checkResources } from '@/utils/resourceChecker'
import { getDynamicRisks, getRisks, type RiskItem } from '@/api/analytics'

const route = useRoute()
const router = useRouter()

// 当前选择的流程
const currentDomain = ref<string>('')
const currentProcessId = ref<string>('')
const highlightDomainFromQuery = ref<string>('')
const focusActivityFromQuery = ref<string>('')

// 从URL读取初始值
const initFromUrl = () => {
  const domain = route.query.domain as string
  const processId = route.query.process_id as string
  const highlightDomain = route.query.highlightDomain as string
  const focusActivity = route.query.focusActivity as string
  
  if (domain) {
    currentDomain.value = domain
  }
  if (processId) {
    currentProcessId.value = processId
  }
  highlightDomainFromQuery.value = highlightDomain || ''
  focusActivityFromQuery.value = focusActivity || ''
}

// 更新URL参数
const updateUrl = () => {
  router.replace({
    query: {
      domain: currentDomain.value,
      process_id: currentProcessId.value
    }
  })
}

// 处理流程切换
const handleProcessChange = (domain: string, processId: string) => {
  currentDomain.value = domain
  currentProcessId.value = processId
  updateUrl()
  
  loadActivities()
  loadResources()
  
  applyProcessHighlight()
}

const activities = ref<Activity[]>([])
const resources = ref<Resource[]>([])
const personnel = ref<Personnel[]>([])
const graphData = ref<GraphData>({ nodes: [], edges: [] })
const riskList = ref<RiskItem[]>([])

const minRunnableDays = computed<number | string>(() => {
  const list = riskList.value
    .map((risk) => risk.runnable_days)
    .filter((day): day is number => typeof day === 'number' && Number.isFinite(day))
  if (list.length === 0) return ''
  return Math.min(...list)
})

const miniRunnableTimeText = computed(() => {
  const value = minRunnableDays.value
  if (value === '' || value === null || value === undefined) return '充足'
  const num = Number(value)
  if (!Number.isFinite(num)) return String(value)
  if (num > 999) return '无限制'
  return `${num.toFixed(1)}天`
})

// 高亮状态：FlowHighlightSet（流程选择器）和 DashboardHighlightSet（仪表盘）
const flowHighlightSet = ref<{nodeIds: Set<string>, edgeIds: Set<string>}>({
  nodeIds: new Set(),
  edgeIds: new Set()
})

const dashboardHighlightSet = ref<{nodeIds: Set<string>, edgeIds: Set<string>}>({
  nodeIds: new Set(),
  edgeIds: new Set()
})

// 最终高亮集合（并集）
const highlightActive = ref(false)
const highlightSet = ref<{nodeIds: Set<string>, edgeIds: Set<string>}>({
  nodeIds: new Set(),
  edgeIds: new Set()
})

// 计算并集并更新最终高亮集合
// 策略：仪表盘高亮优先，如果仪表盘有高亮则覆盖流程高亮
const updateHighlightUnion = () => {
  const hasDashboardHighlight = dashboardHighlightSet.value.nodeIds.size > 0 || dashboardHighlightSet.value.edgeIds.size > 0
  
  let nodeIds: Set<string>
  let edgeIds: Set<string>
  
  if (hasDashboardHighlight) {
    // 仪表盘有高亮时，完全使用仪表盘的高亮（覆盖流程高亮）
    nodeIds = new Set(dashboardHighlightSet.value.nodeIds)
    edgeIds = new Set(dashboardHighlightSet.value.edgeIds)
  } else {
    // 仪表盘无高亮时，使用流程高亮
    nodeIds = new Set(flowHighlightSet.value.nodeIds)
    edgeIds = new Set(flowHighlightSet.value.edgeIds)
  }
  highlightSet.value = { nodeIds, edgeIds }
  highlightActive.value = nodeIds.size > 0 || edgeIds.size > 0
}

const loadActivities = async () => {
  try {
    activities.value = await getActivities({ 
      domain: currentDomain.value, 
      process_id: currentProcessId.value 
    })
  } catch (error) {
    ElMessage.error('加载活动失败')
  }
}

const loadResources = async () => {
  try {
    resources.value = await getResources({
      domain: currentDomain.value,
      process_id: currentProcessId.value
    })
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

// 通过ID获取资源名称
const getResourceNameById = (id: string) => {
  const resource = resources.value.find(r => r.id === id)
  return resource?.name || id
}

// 通过ID获取人员名称
const getPersonnelNameById = (id: string) => {
  const person = personnel.value.find(p => p.id === id)
  return person?.name || id
}

// 获取流程域中文名称
const getDomainName = (domain: string) => {
  const domainMap: Record<string, string> = {
    'production': '生产',
    'transport': '运输',
    'sales': '销售',
    'quality': '质检',
    'warehouse': '仓储'
  }
  return domainMap[domain] || domain
}

// 加载全局图数据
const loadGlobalGraphData = async () => {
  try {
    graphData.value = await getGraphData({ scope: 'global' })
  } catch (error) {
    ElMessage.error('加载图数据失败')
  }
}

// 应用流程高亮
const applyProcessHighlight = () => {
  if (!currentDomain.value || !currentProcessId.value) {
    ElMessage.warning('请先选择流程域和流程ID')
    return
  }
  
  const nodeIds = new Set<string>()
  const edgeIds = new Set<string>()
  
  graphData.value.nodes?.forEach((node: any) => {
    if (node.domain === currentDomain.value && node.process_id === currentProcessId.value) {
      nodeIds.add(node.id)
    }
  })
  
  graphData.value.edges?.forEach((edge: any) => {
    if (edge.domain === currentDomain.value && edge.process_id === currentProcessId.value) {
      edgeIds.add(`${edge.source}-${edge.target}`)
    }
  })
  
  if (nodeIds.size === 0) {
    ElMessage.warning(`未找到 ${currentDomain.value}/${currentProcessId.value} 相关节点`)
    return
  }
  
  // 清除仪表盘高亮（如导航带来的 focusActivity），让流程高亮生效
  dashboardHighlightSet.value = { nodeIds: new Set(), edgeIds: new Set() }
  flowHighlightSet.value = { nodeIds, edgeIds }
  updateHighlightUnion()
  
  ElMessage.success(`已定位到 ${currentDomain.value}/${currentProcessId.value}（${nodeIds.size}个节点）`)
}

// 清除流程高亮
const clearFlowHighlight = () => {
  currentDomain.value = ''
  currentProcessId.value = ''
  flowHighlightSet.value = { nodeIds: new Set(), edgeIds: new Set() }
  // 同时清除仪表盘高亮，确保完全恢复全局视图
  dashboardHighlightSet.value = { nodeIds: new Set(), edgeIds: new Set() }
  updateHighlightUnion()
  updateUrl()
  ElMessage.success('已恢复全局视图')
}

// 清除仪表盘高亮
const clearDashboardHighlight = () => {
  dashboardHighlightSet.value = { nodeIds: new Set(), edgeIds: new Set() }
  updateHighlightUnion()
}

const applyRouteFocusHighlight = () => {
  const focusId = focusActivityFromQuery.value
  const domain = highlightDomainFromQuery.value
  if (!focusId && !domain) return

  if (domain) {
    currentDomain.value = domain
  }

  if (!focusId) return
  const node = graphData.value.nodes.find((item: any) => item.id === focusId)
  if (node) {
    if (node.domain) currentDomain.value = node.domain
    if (node.process_id) currentProcessId.value = node.process_id
  }

  dashboardHighlightSet.value = {
    nodeIds: new Set([focusId]),
    edgeIds: new Set()
  }
  updateHighlightUnion()
}

// 计算 KPI 指标
const metrics = computed(() => {
  const scope: AnalysisScope = currentProcessId.value 
    ? { type: 'process', processId: currentProcessId.value }
    : { type: 'global' }
  
  const analysis = analyzeGraph(graphData.value, scope)
  
  const activities = currentProcessId.value
    ? graphData.value.nodes.filter((n: any) => (n.type === 'activity' || n.category === 'Activity') && n.process_id === currentProcessId.value)
    : graphData.value.nodes.filter((n: any) => n.type === 'activity' || n.category === 'Activity')
  
  const dependencies = currentProcessId.value
    ? graphData.value.edges.filter((e: any) => {
        const source = graphData.value.nodes.find((n: any) => n.id === e.source)
        const target = graphData.value.nodes.find((n: any) => n.id === e.target)
        return source?.process_id === currentProcessId.value && target?.process_id === currentProcessId.value
      })
    : graphData.value.edges
  
  const cpm = calculateCPM(activities, dependencies)
  const resourceCheck = checkResources(graphData.value, currentProcessId.value)
  
  return {
    activityCount: analysis.scale.activityCount,
    internalDependencyCount: analysis.scale.internalDependencyCount,
    healthScore: analysis.health.score,
    issueCount: analysis.health.issueCount,
    totalDuration: cpm.totalDuration || 0,
    criticalPathLength: cpm.criticalPath?.length || 0,
    resourceShortageCount: resourceCheck.dataLevel === 'level1' ? resourceCheck.shortageCount : resourceCheck.riskList?.length || 0,
    dynamicRiskCount: 0
  }
})

// KPI 点击处理
const handleKpiClick = (type: string) => {
  if (type === 'activities') {
    const activityIds = graphData.value.nodes.filter((n: any) => n.type === 'activity' || n.category === 'Activity').map((n: any) => n.id)
    handleDashboardHighlight({ nodeIds: activityIds, edgeIds: [] })
  } else if (type === 'dependencies') {
    const edgeIds = graphData.value.edges.map((e: any) => `${e.source}-${e.target}`)
    handleDashboardHighlight({ nodeIds: [], edgeIds })
  }
}

// 全清空
const clearAllHighlights = () => {
  flowHighlightSet.value = { nodeIds: new Set(), edgeIds: new Set() }
  dashboardHighlightSet.value = { nodeIds: new Set(), edgeIds: new Set() }
  updateHighlightUnion()
}

// 处理仪表盘高亮请求
const handleDashboardHighlight = (payload: { nodeIds: string[], edgeIds: string[] }) => {
  dashboardHighlightSet.value = {
    nodeIds: new Set(payload.nodeIds),
    edgeIds: new Set(payload.edgeIds)
  }
  updateHighlightUnion()
}

// 处理流程选择请求（来自仪表盘全局排行点击）
const handleProcessSelect = (payload: { processId: string }) => {
  const node = graphData.value.nodes?.find((n: any) => n.process_id === payload.processId)
  if (node) {
    currentDomain.value = node.domain || ''
    currentProcessId.value = payload.processId
    updateUrl()
    applyProcessHighlight()
  }
}

// 刷新图数据
const loadGraphData = async () => {
  await loadGlobalGraphData()
  if (highlightActive.value && currentDomain.value && currentProcessId.value) {
    applyProcessHighlight()
  }
}

const loadRiskList = async () => {
  try {
    riskList.value = await getRisks(currentDomain.value || undefined)
  } catch (error) {
    riskList.value = []
    ElMessage.error('加载风险数据失败')
  }
}

// 依赖关系对话框
const dependencyDialogVisible = ref(false)
const isEditDependency = ref(false)
const dependencyForm = ref<Dependency>({
  source_activity_id: '',
  target_activity_id: '',
  dependency_type: 'sequential',
  status: 'active',
  domain: 'production',
  process_id: 'P001'
})

// 活动对话框
const activityDialogVisible = ref(false)
const isEditActivity = ref(false)
const currentActivity = ref<Activity | null>(null)
const activityForm = ref<Activity>({
  name: '',
  description: '',
  activity_type: '',
  sop_steps: [],
  estimated_duration: 0,
  required_resources: [],
  required_personnel: [],
  status: 'pending',
  domain: 'production',
  process_id: 'P001'
})

// 资源对话框
const resourceDialogVisible = ref(false)
const isEditResource = ref(false)
const currentResource = ref<Resource | null>(null)
const resourceForm = ref<Resource>({
  name: '',
  type: '',
  specification: '',
  supplier: '',
  quantity: 0,
  unit: '',
  status: 'available'
})

// 人员对话框
const personnelDialogVisible = ref(false)
const isEditPersonnel = ref(false)
const currentPersonnel = ref<Personnel | null>(null)
const personnelForm = ref<Personnel>({
  name: '',
  role: '',
  responsibility: '',
  skills: [],
  work_hours: '',
  assigned_tasks: [],
  status: 'available'
})

// 节点点击处理
const handleNodeClick = async (node: any) => {
  if (node.category === 'Activity') {
    try {
      const activity = await getActivity(node.id)
      if ((activity as any)._id && !activity.id) {
        activity.id = (activity as any)._id
      }
      currentActivity.value = activity
      activityForm.value = { ...activity }
      isEditActivity.value = false
      activityDialogVisible.value = true
    } catch (error) {
      ElMessage.error('加载活动详情失败')
    }
  } else if (node.category === 'Resource') {
    try {
      // 优先从 rawData 获取原始ID，否则使用节点ID
      // 注意：节点ID可能是组合ID（如 id_inst_parent），需要解析或使用 rawData.original_id
      const resourceId = node.rawData?.original_id || node.id
      
      // 如果依然是组合ID，尝试从字符串解析
      let finalResourceId = resourceId;
      if (finalResourceId && finalResourceId.includes('_inst_')) {
          finalResourceId = finalResourceId.split('_inst_')[0];
      }

      const resource = await getResource(finalResourceId)
      if ((resource as any)._id && !resource.id) {
        resource.id = (resource as any)._id
      }
      currentResource.value = resource
      resourceForm.value = { ...resource }
      isEditResource.value = false
      resourceDialogVisible.value = true
    } catch (error) {
      ElMessage.error('加载资源详情失败')
    }
  } else if (node.category === 'Personnel') {
    try {
      const personnelId = node.rawData?.original_id || node.id
      
      // 如果依然是组合ID，尝试从字符串解析
      let finalPersonnelId = personnelId;
      if (finalPersonnelId && finalPersonnelId.includes('_inst_')) {
          finalPersonnelId = finalPersonnelId.split('_inst_')[0];
      }

      const person = await getPersonnelById(finalPersonnelId)
      if ((person as any)._id && !person.id) {
        person.id = (person as any)._id
      }
      currentPersonnel.value = person
      personnelForm.value = { ...person }
      isEditPersonnel.value = false
      personnelDialogVisible.value = true
    } catch (error) {
      ElMessage.error('加载人员详情失败')
    }
  }
}

// 从图表编辑活动
const handleEditActivityFromGraph = async (activity: any) => {
  try {
    const fullActivity = await getActivity(activity.id)
    if ((fullActivity as any)._id && !fullActivity.id) {
      fullActivity.id = (fullActivity as any)._id
    }
    currentActivity.value = fullActivity
    activityForm.value = { ...fullActivity }
    isEditActivity.value = true
    activityDialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载活动详情失败')
  }
}

// 从图表编辑人员
const handleEditPersonnelFromGraph = async (personnel: any) => {
  try {
    const personnelId = personnel.rawData?.original_id || personnel.id
    let finalPersonnelId = personnelId
    if (finalPersonnelId && finalPersonnelId.includes('_inst_')) {
      finalPersonnelId = finalPersonnelId.split('_inst_')[0]
    }
    const person = await getPersonnelById(finalPersonnelId)
    if ((person as any)._id && !person.id) {
      person.id = (person as any)._id
    }
    currentPersonnel.value = person
    personnelForm.value = { ...person }
    isEditPersonnel.value = true
    personnelDialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载人员详情失败')
  }
}

// 从图表编辑资源
const handleEditResourceFromGraph = async (resource: any) => {
  try {
    const resourceId = resource.rawData?.original_id || resource.id
    let finalResourceId = resourceId
    if (finalResourceId && finalResourceId.includes('_inst_')) {
      finalResourceId = finalResourceId.split('_inst_')[0]
    }
    const fullResource = await getResource(finalResourceId)
    if ((fullResource as any)._id && !fullResource.id) {
      fullResource.id = (fullResource as any)._id
    }
    currentResource.value = fullResource
    resourceForm.value = { ...fullResource }
    isEditResource.value = true
    resourceDialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载资源详情失败')
  }
}

// 依赖关系操作
const handleAddDependency = () => {
  isEditDependency.value = false
  dependencyForm.value = {
    source_activity_id: '',
    target_activity_id: '',
    dependency_type: 'sequential',
    status: 'active',
    domain: currentDomain.value || 'production',
    process_id: currentProcessId.value || 'P001'
  }
  dependencyDialogVisible.value = true
}

const handleDependencySubmit = async () => {
  try {
    if (isEditDependency.value && dependencyForm.value.id) {
      await updateDependency(dependencyForm.value.id, dependencyForm.value)
      ElMessage.success('更新成功')
    } else {
      await createDependency(dependencyForm.value)
      ElMessage.success('创建成功')
    }
    dependencyDialogVisible.value = false
    await loadGraphData()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

// 活动操作
const handleAddActivity = () => {
  currentActivity.value = null
  isEditActivity.value = true
  activityForm.value = {
    name: '',
    description: '',
    activity_type: '',
    sop_steps: [],
    estimated_duration: 0,
    required_resources: [],
    required_personnel: [],
    status: 'pending',
    domain: currentDomain.value || 'production',
    process_id: currentProcessId.value || 'P001'
  }
  activityDialogVisible.value = true
}

const handleActivitySubmit = async () => {
  try {
    if (currentActivity.value?.id) {
      await updateActivity(currentActivity.value.id, activityForm.value)
      ElMessage.success('更新成功')
    } else {
      await createActivity(activityForm.value)
      ElMessage.success('创建成功')
    }
    activityDialogVisible.value = false
    isEditActivity.value = false
    await loadActivities()
    await loadGraphData()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const closeActivityDialog = () => {
  activityDialogVisible.value = false
  isEditActivity.value = false
}

const handleDeleteActivity = async () => {
  try {
    await ElMessageBox.confirm('确定删除该活动?', '提示', {
      type: 'warning'
    })
    if (currentActivity.value?.id) {
      await deleteActivity(currentActivity.value.id)
      ElMessage.success('删除成功')
      activityDialogVisible.value = false
      await loadActivities()
      await loadGraphData()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 资源操作
const handleAddResource = () => {
  currentResource.value = null
  isEditResource.value = true
  resourceForm.value = {
    name: '',
    type: '',
    specification: '',
    supplier: '',
    quantity: 0,
    unit: '',
    status: 'available'
  }
  resourceDialogVisible.value = true
}

const handleResourceSubmit = async () => {
  try {
    if (currentResource.value?.id) {
      await updateResource(currentResource.value.id, resourceForm.value)
      ElMessage.success('更新成功')
    } else {
      await createResource(resourceForm.value)
      ElMessage.success('创建成功')
    }
    resourceDialogVisible.value = false
    isEditResource.value = false
    await loadResources()
    await loadGraphData()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const closeResourceDialog = () => {
  resourceDialogVisible.value = false
  isEditResource.value = false
}

const handleDeleteResource = async () => {
  try {
    await ElMessageBox.confirm('确定删除该资源?', '提示', {
      type: 'warning'
    })
    if (currentResource.value?.id) {
      await deleteResource(currentResource.value.id)
      ElMessage.success('删除成功')
      resourceDialogVisible.value = false
      await loadResources()
      await loadGraphData()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 人员操作
const handleAddPersonnel = () => {
  currentPersonnel.value = null
  isEditPersonnel.value = true
  personnelForm.value = {
    name: '',
    role: '',
    responsibility: '',
    skills: [],
    work_hours: '',
    assigned_tasks: [],
    status: 'available'
  }
  personnelDialogVisible.value = true
}

const handlePersonnelSubmit = async () => {
  try {
    if (currentPersonnel.value?.id) {
      await updatePersonnel(currentPersonnel.value.id, personnelForm.value)
      ElMessage.success('更新成功')
    } else {
      await createPersonnel(personnelForm.value)
      ElMessage.success('创建成功')
    }
    personnelDialogVisible.value = false
    isEditPersonnel.value = false
    await loadPersonnel()
    await loadGraphData()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const closePersonnelDialog = () => {
  personnelDialogVisible.value = false
  isEditPersonnel.value = false
}

const handleDeletePersonnel = async () => {
  try {
    await ElMessageBox.confirm('确定删除该人员?', '提示', {
      type: 'warning'
    })
    if (currentPersonnel.value?.id) {
      await deletePersonnel(currentPersonnel.value.id)
      ElMessage.success('删除成功')
      personnelDialogVisible.value = false
      await loadPersonnel()
      await loadGraphData()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(async () => {
  initFromUrl()
  await loadGlobalGraphData()
  applyRouteFocusHighlight()
  
  if (currentDomain.value && currentProcessId.value) {
    await loadActivities()
    await loadResources()
  }
  await loadPersonnel()
  await loadRiskList()
})

watch([currentDomain, currentProcessId], async () => {
  await loadRiskList()
})

watch(
  () => [route.query.highlightDomain, route.query.focusActivity],
  async () => {
    const newHighlightDomain = (route.query.highlightDomain as string) || ''
    const newFocusActivity = (route.query.focusActivity as string) || ''
    highlightDomainFromQuery.value = newHighlightDomain
    focusActivityFromQuery.value = newFocusActivity
    // 只有在新参数非空时（真正从外部导航过来）才重载图，
    // 避免 updateUrl() 清除参数时触发不必要的图重建并导致高亮丢失
    if (newHighlightDomain || newFocusActivity) {
      await loadGlobalGraphData()
      applyRouteFocusHighlight()
    }
  }
)
</script>

<style scoped>
.dependency-management {
  height: 100vh;
  overflow: hidden;
}

.fullscreen-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.fullscreen-container :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}

.mini-kpi-hud {
  display: flex;
  gap: 12px;
  margin-left: auto;
  background: #fff;
  padding: 6px 12px;
  border-radius: 4px;
  border: 1px solid #dcdfe6;
}

.mini-kpi-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4px 12px;
  cursor: pointer;
  transition: background 0.2s;
  border-radius: 4px;
  min-width: 60px;
}

.mini-kpi-item:hover {
  background: #f0f9ff;
}

.mini-value {
  font-size: 18px;
  font-weight: bold;
  color: #409eff;
  line-height: 1.2;
}

.mini-label {
  font-size: 11px;
  color: #606266;
  margin-top: 2px;
  white-space: nowrap;
}

.main-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.graph-panel {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.sidebar {
  width: 450px;
  background: #fff;
  border-left: 1px solid #e4e7ed;
  overflow-y: auto;
  overflow-x: hidden;
}
</style>
