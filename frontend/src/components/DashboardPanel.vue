<template>
  <div class="dashboard-panel" :class="{ 'sidebar-mode': props.mode === 'sidebar' }">
    <div v-if="props.mode === 'full'" class="scope-switcher">
      <el-radio-group v-model="currentScope" size="small" @change="handleScopeChange">
        <el-radio-button label="global">全局</el-radio-button>
        <el-radio-button label="process" :disabled="!hasSelectedProcess">当前流程</el-radio-button>
      </el-radio-group>
      <el-text v-if="currentScope === 'process' && currentProcessId" type="info" size="small" style="margin-left: 10px;">
        {{ getProcessName(currentProcessId) }}
      </el-text>
      <el-text v-if="dataLevel !== 'level2'" type="warning" size="small" style="margin-left: 10px;">
        {{ dataLevelHint }}
      </el-text>
      <el-button size="small" @click="handleClearHighlight" style="margin-left: auto;">
        清空仪表盘高亮
      </el-button>
    </div>

    <div v-if="props.mode === 'full'" class="kpi-cards">
      <el-card class="kpi-card" shadow="hover" @click="handleKpiClick('activities')">
        <div class="kpi-value">{{ metrics.activityCount }}</div>
        <div class="kpi-label">活动数</div>
      </el-card>
      
      <el-card class="kpi-card" shadow="hover" @click="handleKpiClick('dependencies')">
        <div class="kpi-value">{{ metrics.internalDependencyCount }}</div>
        <div class="kpi-label">内部依赖</div>
      </el-card>
      
      <el-card class="kpi-card" shadow="hover" @click="handleKpiClick('health')">
        <div class="kpi-value">{{ metrics.healthScore }}</div>
        <div class="kpi-label">健康评分</div>
        <div class="kpi-sub">{{ metrics.issueCount }}个问题</div>
      </el-card>
      
      <el-card class="kpi-card" shadow="hover" @click="handleKpiClick('cpm')">
        <div class="kpi-value">{{ metrics.totalDuration }}</div>
        <div class="kpi-label">总工期(分钟)</div>
        <div class="kpi-sub">关键路径{{ metrics.criticalPathLength }}步</div>
      </el-card>
      
      <el-card class="kpi-card" shadow="hover" @click="handleKpiClick('resource')">
        <div class="kpi-value">{{ runnableTimeText }}</div>
        <div class="kpi-label">可运行时间</div>
      </el-card>
      
      <el-card class="kpi-card" shadow="hover" @click="handleKpiClick('dynamic')">
        <div class="kpi-value">{{ props.riskCount }}</div>
        <div class="kpi-label">风险数</div>
      </el-card>
    </div>

    <div v-if="props.mode === 'full' && currentScope === 'process' && metrics.externalDependencyCount > 0" class="external-deps">
      <el-tag type="info" @click="handleExternalDepsClick">
        外部依赖：入{{ metrics.externalDependencyInCount }} / 出{{ metrics.externalDependencyOutCount }}
      </el-tag>
    </div>

    <div v-if="props.mode === 'sidebar'" class="sidebar-header">
      <el-radio-group v-model="currentScope" size="small" @change="handleScopeChange">
        <el-radio-button label="global">全局</el-radio-button>
        <el-radio-button label="process" :disabled="!hasSelectedProcess">流程</el-radio-button>
      </el-radio-group>
      <el-button size="small" @click="handleClearHighlight" text>
        清空
      </el-button>
    </div>

    <el-tabs v-if="props.mode === 'sidebar'" v-model="activeTab" class="sidebar-tabs">
      <el-tab-pane label="健康度" name="health">
        <div v-if="currentScope === 'global' && processSummary.length > 0" class="process-ranking">
          <el-table :data="healthRanking" size="small" style="width: 100%" @row-click="handleProcessRankingClick" height="calc(100vh - 200px)">
            <el-table-column prop="processName" label="流程" min-width="140" show-overflow-tooltip />
            <el-table-column prop="healthScore" label="评分" width="70" />
            <el-table-column prop="issueCount" label="问题" width="70" />
            <el-table-column prop="activityCount" label="活动数" min-width="120" />
          </el-table>
        </div>
        <div v-else class="issue-list">
          <el-empty v-if="healthIssues.length === 0" description="无健康问题" :image-size="60" />
          <div v-else>
            <div v-for="issue in healthIssues" :key="issue.description" class="issue-item" @click="handleIssueClick(issue)">
              <el-tag :type="issue.severity === 'error' ? 'danger' : 'warning'" size="small">{{ getIssueTypeName(issue.type) }}</el-tag>
              <span class="issue-text">{{ issue.description }}</span>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="关键路径" name="cpm">
        <div v-if="currentScope === 'global' && processSummary.length > 0" class="process-ranking">
          <el-table :data="durationRanking" size="small" style="width: 100%" @row-click="handleProcessRankingClick" height="calc(100vh - 200px)">
            <el-table-column prop="processName" label="流程" min-width="140" show-overflow-tooltip />
            <el-table-column prop="totalDuration" label="工期" width="80" />
            <el-table-column prop="criticalPathLength" label="路径长度" min-width="120" />
          </el-table>
        </div>
        <div v-else>
          <div v-if="cpmError" class="error-hint">
            <el-alert type="warning" :title="cpmError" :closable="false" />
          </div>
          <div v-else>
            <div class="critical-path">
              <h4>关键路径</h4>
              <div class="path-sequence">
                <el-tag v-for="(actId, idx) in criticalPath" :key="actId" type="danger" size="small" @click="handleCriticalPathClick(actId)">
                  {{ getActivityName(actId) }}
                </el-tag>
                <el-empty v-if="criticalPath.length === 0" description="无关键路径" :image-size="60" />
              </div>
            </div>
            <div class="bottlenecks">
              <h4>瓶颈活动</h4>
              <div v-for="activity in topBottlenecks" :key="activity.id" class="bottleneck-item" @click="handleBottleneckClick(activity)">
                <span class="bottleneck-name">{{ activity.name }}</span>
                <el-tag size="small">{{ activity.duration }}分</el-tag>
              </div>
              <el-empty v-if="topBottlenecks.length === 0" description="无瓶颈活动" :image-size="60" />
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="风险" name="risk">
        <div v-if="currentScope === 'global'" class="process-ranking">
          <el-table :data="domainRiskSummary" size="small" style="width: 100%" @row-click="handleProcessRankingClick" height="calc(100vh - 200px)">
            <el-table-column label="流程" min-width="140" show-overflow-tooltip>
              <template #default="scope">
                {{ formatProcessDisplay(scope.row.processId, scope.row.domain) }}
              </template>
            </el-table-column>
            <el-table-column prop="riskCount" label="风险数" width="80" />
            <el-table-column label="最短可运行时间" min-width="140">
              <template #default="scope">
                {{ formatRunnableDays(scope.row.minRunnableDays) }}
              </template>
            </el-table-column>
          </el-table>
        </div>
        <div v-else>
          <div class="dynamic-risks">
            <h4>风险明细</h4>
            <el-collapse v-model="expandedRiskPanels" class="risk-collapse">
              <el-collapse-item
                v-for="(risk, idx) in currentDomainRisks"
                :key="`${risk.process_id || 'na'}-${risk.activity_name}-${idx}`"
                :name="String(idx)"
              >
                <template #title>
                  <div class="risk-title-row">
                    <el-tag size="small" :type="riskTagType(risk.risk_type)">
                      {{ riskTypeLabel(risk.risk_type) }}
                    </el-tag>
                    <span class="risk-title-text">{{ risk.activity_name }}</span>
                  </div>
                </template>
                <div class="risk-detail-text">{{ risk.message }}</div>
              </el-collapse-item>
            </el-collapse>
            <el-empty v-if="currentDomainRisks.length === 0" description="暂无风险" :image-size="60" />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-collapse v-if="props.mode === 'full'" v-model="activePanels" class="panels">
      <el-collapse-item title="模型健康度" name="health">
        <div v-if="currentScope === 'global' && processSummary.length > 0" class="process-ranking">
          <h4>按流程健康度排行</h4>
          <el-table :data="healthRanking" size="small" @row-click="handleProcessRankingClick">
            <el-table-column prop="processName" label="流程" width="180" />
            <el-table-column prop="healthScore" label="健康评分" width="100" />
            <el-table-column prop="issueCount" label="问题数" width="100" />
            <el-table-column prop="activityCount" label="活动数" width="100" />
          </el-table>
        </div>
        <div v-else class="issue-list">
          <el-empty v-if="healthIssues.length === 0" description="无健康问题" :image-size="80" />
          <div v-else>
            <div v-for="issue in healthIssues" :key="issue.description" class="issue-item" @click="handleIssueClick(issue)">
              <el-tag :type="issue.severity === 'error' ? 'danger' : 'warning'" size="small">{{ getIssueTypeName(issue.type) }}</el-tag>
              <span>{{ issue.description }}</span>
            </div>
          </div>
        </div>
      </el-collapse-item>

      <el-collapse-item title="关键路径与瓶颈" name="cpm">
        <div v-if="currentScope === 'global' && processSummary.length > 0" class="process-ranking">
          <h4>按流程工期排行</h4>
          <el-table :data="durationRanking" size="small" @row-click="handleProcessRankingClick">
            <el-table-column prop="processName" label="流程" width="180" />
            <el-table-column prop="totalDuration" label="总工期(分钟)" width="120" />
            <el-table-column prop="criticalPathLength" label="关键路径长度" width="120" />
          </el-table>
        </div>
        <div v-else>
          <div v-if="cpmError" class="error-hint">
            <el-alert type="warning" :title="cpmError" :closable="false" />
          </div>
          <div v-else>
            <div class="critical-path">
              <h4>关键路径</h4>
              <div class="path-sequence">
                <el-tag v-for="(actId, idx) in criticalPath" :key="actId" type="danger" size="small" @click="handleCriticalPathClick(actId)">
                  {{ getActivityName(actId) }}
                  <span v-if="idx < criticalPath.length - 1"> → </span>
                </el-tag>
                <el-empty v-if="criticalPath.length === 0" description="无关键路径" :image-size="60" />
              </div>
            </div>
            <div class="bottlenecks">
              <h4>瓶颈活动 Top5</h4>
              <div v-for="activity in topBottlenecks" :key="activity.id" class="bottleneck-item" @click="handleBottleneckClick(activity)">
                <span>{{ activity.name }}</span>
                <el-tag size="small">{{ activity.duration }}分钟</el-tag>
              </div>
              <el-empty v-if="topBottlenecks.length === 0" description="无瓶颈活动" :image-size="60" />
            </div>
          </div>
        </div>
      </el-collapse-item>

      <el-collapse-item title="约束风险" name="risk">
        <div v-if="currentScope === 'global' && processSummary.length > 0" class="process-ranking">
          <h4>按流程风险排行</h4>
          <el-table :data="riskRanking" size="small" @row-click="handleProcessRankingClick">
            <el-table-column prop="processName" label="流程" width="180" />
            <el-table-column prop="shortageCount" label="原料短缺" width="100" />
            <el-table-column prop="dynamicRiskCount" label="动态风险" width="100" />
          </el-table>
        </div>
        <div v-else>
          <div class="resource-risks">
            <h4>{{ dataLevel === 'level1' ? '原料短缺 Top5' : '原料关联风险 Top5' }}</h4>
            <div v-for="item in resourceRisks" :key="item.resourceId" class="risk-item" @click="handleResourceRiskClick(item)">
              <span>{{ item.resourceName }}</span>
              <el-tag size="small" :type="dataLevel === 'level1' && item.shortage > 0 ? 'danger' : 'info'">
                {{ dataLevel === 'level1' ? `缺口${item.shortage}` : `关联${item.referenceCount}次` }}
              </el-tag>
            </div>
            <el-empty v-if="resourceRisks.length === 0" description="无原料风险" :image-size="60" />
          </div>
          <div class="dynamic-risks">
            <h4>动态风险事件</h4>
            <div v-for="event in dynamicRiskEvents" :key="event.description" class="risk-item" @click="handleDynamicRiskClick(event)">
              <el-tag size="small" :type="event.type === 'equipment_shortage' ? 'warning' : 'danger'">
                {{ event.type === 'equipment_shortage' ? '设备' : '人力' }}
              </el-tag>
              <span>{{ event.description }}</span>
              <span class="time-window">{{ event.timeWindow }}</span>
            </div>
            <el-empty v-if="dynamicRiskEvents.length === 0" description="无动态风险" :image-size="60" />
          </div>
        </div>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { GraphData } from '@/types'
import { analyzeGraph, type AnalysisScope, type HealthIssue, type ProcessMetrics } from '@/utils/graphAnalyzer'
import { calculateCPM, type CPMActivity } from '@/utils/cpmCalculator'
import { checkResources, summarizeResourceRisksByProcess, type ResourceShortage, type ResourceRisk } from '@/utils/resourceChecker'
import { getDynamicRisks, summarizeDynamicRisksByProcess, type DynamicRiskEvent } from '@/api/analytics'

const props = withDefaults(defineProps<{
  graphData: GraphData
  currentProcessId?: string
  currentDomain?: string
  mode?: 'full' | 'sidebar'
  minRunnableDays?: number | string
  riskCount?: number
  riskList?: Array<{
    risk_type: 'material_shortage' | 'allocation_shortage' | 'upcoming_absence'
    level: 'high' | 'medium' | 'low'
    activity_name: string
    message: string
    domain?: string | null
    process_id?: string | null
    runnable_days?: number | null
  }>
}>(), {
  mode: 'full',
  minRunnableDays: '',
  riskCount: 0,
  riskList: () => []
})

const emit = defineEmits<{
  highlightRequest: [{ nodeIds: string[], edgeIds: string[] }]
  processSelect: [{ processId: string }]
  clearHighlight: []
}>()

const currentScope = ref<'global' | 'process'>('global')
const activePanels = ref(['health', 'cpm', 'risk'])
const activeTab = ref('health')
const expandedRiskPanels = ref<string[]>([])
const dataLevel = ref<'level0' | 'level1' | 'level2'>('level0')

const analysisResult = ref<any>(null)
const cpmResult = ref<any>(null)
const resourceCheckResult = ref<any>(null)
const dynamicRisksData = ref<DynamicRiskEvent[]>([])

const hasSelectedProcess = computed(() => !!props.currentProcessId)

const dataLevelHint = computed(() => {
  if (dataLevel.value === 'level0') return '当前为关联风险分析'
  if (dataLevel.value === 'level1') return '当前为静态短缺分析'
  return ''
})

const runnableTimeText = computed(() => {
  const raw = props.minRunnableDays
  if (raw === null || raw === undefined || raw === '') return '充足'
  const num = Number(raw)
  if (!Number.isFinite(num)) return String(raw)
  if (num > 999) return '无限制'
  if (num < 0) return '充足'
  return `${num.toFixed(1)}天`
})

const metrics = computed(() => {
  if (!analysisResult.value) {
    return {
      activityCount: 0,
      internalDependencyCount: 0,
      externalDependencyInCount: 0,
      externalDependencyOutCount: 0,
      externalDependencyCount: 0,
      healthScore: 0,
      issueCount: 0,
      totalDuration: 0,
      criticalPathLength: 0,
      resourceShortageCount: 0,
      dynamicRiskCount: 0
    }
  }

  const scale = analysisResult.value.scale
  const health = analysisResult.value.health
  const cpm = cpmResult.value || {}
  const resource = resourceCheckResult.value || {}
  
  return {
    activityCount: scale.activityCount,
    internalDependencyCount: scale.internalDependencyCount,
    externalDependencyInCount: scale.externalDependencyInCount || 0,
    externalDependencyOutCount: scale.externalDependencyOutCount || 0,
    externalDependencyCount: (scale.externalDependencyInCount || 0) + (scale.externalDependencyOutCount || 0),
    healthScore: health.score,
    issueCount: health.issueCount,
    totalDuration: cpm.totalDuration || 0,
    criticalPathLength: cpm.criticalPath?.length || 0,
    resourceShortageCount: resource.dataLevel === 'level1' ? resource.shortageCount : resource.riskList?.length || 0,
    dynamicRiskCount: dynamicRisksData.value.length
  }
})

const processSummary = computed(() => analysisResult.value?.processSummary || [])

const healthRanking = computed(() => {
  return [...processSummary.value]
    .sort((a: ProcessMetrics, b: ProcessMetrics) => {
      if (a.healthScore !== b.healthScore) return a.healthScore - b.healthScore
      return b.issueCount - a.issueCount
    })
    .slice(0, 10)
})

const durationRanking = computed(() => {
  return processSummary.value.map((p: ProcessMetrics) => {
    const scope: AnalysisScope = { type: 'process', processId: p.processId }
    const activities = props.graphData.nodes.filter(n => isActivityNode(n) && n.process_id === p.processId)
    const deps = props.graphData.edges.filter(e => {
      const source = props.graphData.nodes.find(n => n.id === e.source)
      const target = props.graphData.nodes.find(n => n.id === e.target)
      return source?.process_id === p.processId && target?.process_id === p.processId
    })
    const cpm = calculateCPM(activities, deps)
    
    return {
      processId: p.processId,
      processName: p.processName,
      totalDuration: cpm.totalDuration,
      criticalPathLength: cpm.criticalPath.length
    }
  }).sort((a, b) => b.totalDuration - a.totalDuration).slice(0, 10)
})

const riskRanking = computed(() => {
  const resourceSummary = summarizeResourceRisksByProcess(props.graphData)
  const dynamicSummary = summarizeDynamicRisksByProcess()
  
  const merged = new Map()
  
  processSummary.value.forEach((p: ProcessMetrics) => {
    merged.set(p.processId, {
      processId: p.processId,
      processName: p.processName,
      shortageCount: 0,
      dynamicRiskCount: 0
    })
  })
  
  resourceSummary.forEach(r => {
    const item = merged.get(r.processId)
    if (item) item.shortageCount = r.shortageCount || r.riskCount
  })
  
  dynamicSummary.forEach(d => {
    const item = merged.get(d.processId)
    if (item) item.dynamicRiskCount = d.totalRiskCount
  })
  
  return Array.from(merged.values())
    .sort((a, b) => (b.shortageCount + b.dynamicRiskCount) - (a.shortageCount + a.dynamicRiskCount))
    .slice(0, 10)
})

const domainRiskSummary = computed(() => {
  const grouped = new Map<string, { processId: string; domain: string; riskCount: number; minRunnableDays: number | null }>()
  const list = props.riskList || []

  for (const risk of list) {
    const domain = risk.domain || '-'
    const pid = risk.process_id || 'unknown'
    const key = `${domain}::${pid}`
    const existing = grouped.get(key) || {
      processId: pid,
      domain,
      riskCount: 0,
      minRunnableDays: null as number | null
    }

    existing.riskCount += 1
    if (risk.risk_type === 'material_shortage' && typeof risk.runnable_days === 'number' && Number.isFinite(risk.runnable_days)) {
      existing.minRunnableDays =
        existing.minRunnableDays === null ? risk.runnable_days : Math.min(existing.minRunnableDays, risk.runnable_days)
    }

    grouped.set(key, existing)
  }

  return Array.from(grouped.values()).sort((a, b) => b.riskCount - a.riskCount)
})

const currentDomainRisks = computed(() => {
  const list = props.riskList || []
  if (props.currentProcessId) {
    return list.filter((risk) => risk.process_id === props.currentProcessId)
  }
  if (props.currentDomain) {
    return list.filter((risk) => risk.domain === props.currentDomain)
  }
  return list
})

const healthIssues = computed(() => analysisResult.value?.health.issues || [])

const criticalPath = computed(() => cpmResult.value?.criticalPath || [])

const cpmError = computed(() => cpmResult.value?.errorMessage || '')

const topBottlenecks = computed(() => cpmResult.value?.topBottlenecks || [])

const resourceRisks = computed(() => {
  if (!resourceCheckResult.value) return []
  if (resourceCheckResult.value.dataLevel === 'level1') {
    return resourceCheckResult.value.shortageList.slice(0, 5).map((s: ResourceShortage) => ({
      resourceId: s.resourceId,
      resourceName: s.resourceName,
      shortage: s.shortage,
      referenceCount: 0,
      relatedActivityIds: s.relatedActivityIds
    }))
  } else {
    return resourceCheckResult.value.riskList.slice(0, 5)
  }
})

const dynamicRiskEvents = computed(() => dynamicRisksData.value.slice(0, 5))

const isActivityNode = (n: any) => n?.type === 'activity' || n?.category === 'Activity'

watch(() => props.currentProcessId, (newId) => {
  if (newId) {
    currentScope.value = 'process'
  } else {
    currentScope.value = 'global'
  }
  performAnalysis()
}, { immediate: true })

watch(() => props.graphData, () => {
  performAnalysis()
}, { deep: true })

watch(activeTab, (newTab, oldTab) => {
  if (currentScope.value !== 'process' || !props.currentProcessId) return
  
  if (newTab === 'cpm') {
    // 进入关键路径Tab，只高亮关键路径
    const criticalNodeIds = cpmResult.value?.criticalPath || []
    if (criticalNodeIds.length === 0) return
    
    // 提取关键路径的边
    const criticalNodeSet = new Set(criticalNodeIds)
    const criticalEdgeIds: string[] = []
    props.graphData.edges.forEach(e => {
      if (criticalNodeSet.has(e.source) && criticalNodeSet.has(e.target)) {
        criticalEdgeIds.push(`${e.source}-${e.target}`)
      }
    })
    
    emit('highlightRequest', { nodeIds: criticalNodeIds, edgeIds: criticalEdgeIds })
  } else if (oldTab === 'cpm') {
    // 离开关键路径Tab，恢复全流程高亮
    const processNodeIds: string[] = []
    const processEdgeIds: string[] = []
    
    props.graphData.nodes.forEach(n => {
      if ((n.type === 'activity' || n.category === 'Activity') && n.process_id === props.currentProcessId) {
        processNodeIds.push(n.id)
      }
    })
    
    props.graphData.edges.forEach(e => {
      const source = props.graphData.nodes.find(n => n.id === e.source)
      const target = props.graphData.nodes.find(n => n.id === e.target)
      if (source?.process_id === props.currentProcessId && target?.process_id === props.currentProcessId) {
        processEdgeIds.push(`${e.source}-${e.target}`)
      }
    })
    
    emit('highlightRequest', { nodeIds: processNodeIds, edgeIds: processEdgeIds })
  }
})

function handleScopeChange() {
  performAnalysis()
}

function performAnalysis() {
  const scope: AnalysisScope = currentScope.value === 'process' && props.currentProcessId
    ? { type: 'process', processId: props.currentProcessId }
    : { type: 'global' }
  
  analysisResult.value = analyzeGraph(props.graphData, scope)
  
  const activities = scope.type === 'process'
    ? props.graphData.nodes.filter(n => isActivityNode(n) && n.process_id === scope.processId)
    : props.graphData.nodes.filter(isActivityNode)
  
  const dependencies = scope.type === 'process'
    ? props.graphData.edges.filter(e => {
        const source = props.graphData.nodes.find(n => n.id === e.source)
        const target = props.graphData.nodes.find(n => n.id === e.target)
        return source?.process_id === scope.processId && target?.process_id === scope.processId
      })
    : props.graphData.edges
  
  cpmResult.value = calculateCPM(activities, dependencies)
  
  resourceCheckResult.value = checkResources(props.graphData, scope.type === 'process' ? scope.processId : undefined)
  dataLevel.value = resourceCheckResult.value.dataLevel
  
  loadDynamicRisks()
}

async function loadDynamicRisks() {
  const processId = currentScope.value === 'process' && props.currentProcessId ? props.currentProcessId : undefined
  const result = await getDynamicRisks(processId)
  dynamicRisksData.value = [...result.equipmentShortages, ...result.personnelOverloads]
}

function handleKpiClick(type: string) {
  if (type === 'activities') {
    const activityIds = props.graphData.nodes.filter(isActivityNode).map(n => n.id)
    emit('highlightRequest', { nodeIds: activityIds, edgeIds: [] })
  } else if (type === 'dependencies') {
    const edgeIds = props.graphData.edges.map(e => `${e.source}-${e.target}`)
    emit('highlightRequest', { nodeIds: [], edgeIds })
  }
}

function handleExternalDepsClick() {
  if (currentScope.value !== 'process' || !props.currentProcessId) return
  
  const activityIds = new Set(
    props.graphData.nodes
      .filter(n => n.type === 'activity' && n.process_id === props.currentProcessId)
      .map(n => n.id)
  )
  
  const externalEdges: string[] = []
  const externalNodes: string[] = []
  
  props.graphData.edges.forEach(e => {
    const sourceIn = activityIds.has(e.source)
    const targetIn = activityIds.has(e.target)
    
    if (sourceIn !== targetIn) {
      externalEdges.push(`${e.source}-${e.target}`)
      if (!sourceIn) externalNodes.push(e.source)
      if (!targetIn) externalNodes.push(e.target)
    }
  })
  
  emit('highlightRequest', { nodeIds: externalNodes, edgeIds: externalEdges })
}

function handleIssueClick(issue: HealthIssue) {
  emit('highlightRequest', { nodeIds: issue.nodeIds, edgeIds: issue.edgeIds })
}

function handleCriticalPathClick(actId: string) {
  emit('highlightRequest', { nodeIds: [actId], edgeIds: [] })
}

function handleBottleneckClick(activity: CPMActivity) {
  emit('highlightRequest', { nodeIds: [activity.id], edgeIds: [] })
}

function handleResourceRiskClick(item: any) {
  // 验证activityIds是否存在于图中
  const validNodeIds = (item.relatedActivityIds || []).filter((id: string) => 
    props.graphData.nodes.some(n => n.id === id)
  )
  
  if (validNodeIds.length === 0) {
    ElMessage.warning('该风险条目无关联活动或活动不在当前视图中')
    return
  }
  
  emit('highlightRequest', { nodeIds: validNodeIds, edgeIds: [] })
}

function handleDynamicRiskClick(event: DynamicRiskEvent) {
  // 验证activityIds是否存在于图中
  const validNodeIds = (event.activityIds || []).filter((id: string) => 
    props.graphData.nodes.some(n => n.id === id)
  )
  
  if (validNodeIds.length === 0) {
    ElMessage.warning('该风险条目无关联活动或活动不在当前视图中')
    return
  }
  
  emit('highlightRequest', { nodeIds: validNodeIds, edgeIds: [] })
}

function handleProcessRankingClick(row: any) {
  emit('processSelect', { processId: row.processId })
}

function handleClearHighlight() {
  emit('clearHighlight')
  ElMessage.success('已清空仪表盘高亮')
}

function getProcessName(processId: string): string {
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
  return processMap[processId] ? `${processId} - ${processMap[processId]}` : processId
}

function getActivityName(actId: string): string {
  const node = props.graphData.nodes.find(n => n.id === actId)
  return node?.name || actId
}

function getIssueTypeName(type: string): string {
  const typeMap: Record<string, string> = {
    'cycle': '环',
    'duplicate': '重复',
    'isolated': '孤立'
  }
  return typeMap[type] || type
}

function formatRunnableDays(value: number | null) {
  if (value === null || value === undefined) return '>7天'
  return `${value.toFixed(1)}天`
}

const processLabelMap: Record<string, string> = {
  P001: 'P001 - 主生产线',
  P002: 'P002 - 副生产线',
  T001: 'T001 - 冷链运输',
  T002: 'T002 - 常温运输',
  S001: 'S001 - 线上销售',
  S002: 'S002 - 线下销售',
  Q001: 'Q001 - 常规质检',
  Q002: 'Q002 - 专项质检',
  W001: 'W001 - 主仓库',
  W002: 'W002 - 分仓库'
}

function formatProcessDisplay(processId: string, domain?: string) {
  if (processLabelMap[processId]) return processLabelMap[processId]
  if (!processId) return domain || '-'
  const prefix = processId[0]?.toUpperCase()
  const domainHint =
    prefix === 'P' ? '生产线' :
    prefix === 'T' ? '运输' :
    prefix === 'S' ? '销售' :
    prefix === 'Q' ? '质检' :
    prefix === 'W' ? '仓库' : (domain || '流程')
  return `${processId} - ${domainHint}`
}

function riskTypeLabel(type: string) {
  if (type === 'material_shortage') return '缺料'
  if (type === 'allocation_shortage') return '缺人/缺设备'
  return '请假/检修'
}

function riskTagType(type: string) {
  if (type === 'material_shortage') return 'danger'
  if (type === 'allocation_shortage') return 'warning'
  return 'info'
}

onMounted(() => {
  performAnalysis()
})
</script>

<style scoped>
.dashboard-panel {
  padding: 20px;
  background: #f5f7fa;
}

.dashboard-panel.sidebar-mode {
  padding: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid #e4e7ed;
  background: #f5f7fa;
}

.sidebar-tabs {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.sidebar-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 12px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.sidebar-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.sidebar-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.scope-switcher {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}

.kpi-cards {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.kpi-card {
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
  padding: 20px;
}

.kpi-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.kpi-value {
  font-size: 32px;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 8px;
}

.kpi-label {
  font-size: 14px;
  color: #606266;
}

.kpi-sub {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.external-deps {
  margin-bottom: 20px;
}

.external-deps .el-tag {
  cursor: pointer;
}

.panels {
  background: white;
}

.process-ranking {
  padding: 10px;
}

.process-ranking h4 {
  margin: 0 0 10px 0;
  color: #303133;
}

.process-ranking :deep(.el-table__row) {
  cursor: pointer;
}

.process-ranking :deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}

.issue-list, .critical-path, .bottlenecks, .resource-risks, .dynamic-risks {
  padding: 10px;
}

.issue-item, .bottleneck-item, .risk-item {
  padding: 8px 12px;
  margin-bottom: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.3s;
}

.issue-text, .risk-text, .bottleneck-name, .risk-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.issue-item:hover, .bottleneck-item:hover, .risk-item:hover {
  background: #e8f4ff;
}

.path-sequence {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.sidebar-mode .path-sequence {
  gap: 4px;
}

.sidebar-mode .path-sequence .el-tag {
  font-size: 11px;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.path-sequence .el-tag {
  cursor: pointer;
}

h4 {
  margin: 0 0 10px 0;
  color: #303133;
  font-size: 14px;
}

.error-hint {
  margin-bottom: 10px;
}

.time-window {
  font-size: 12px;
  color: #909399;
  margin-left: auto;
}

.risk-collapse {
  border: none;
}

.risk-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: calc(100% - 24px);
}

.risk-title-text {
  font-size: 13px;
  color: #303133;
}

.risk-detail-text {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  white-space: normal;
  word-break: break-word;
  padding: 4px 0 8px;
}

@media (max-width: 1400px) {
  .kpi-cards {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .kpi-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>

