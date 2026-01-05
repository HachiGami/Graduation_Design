import type { GraphData, GraphNode, GraphEdge } from '@/types'

export interface AnalysisScope {
  type: 'global' | 'process'
  processId?: string
}

export interface ScaleMetrics {
  activityCount: number
  internalDependencyCount: number
  externalDependencyInCount: number
  externalDependencyOutCount: number
  resourceAssociationCount: number
  personnelAssociationCount: number
}

export interface HealthIssue {
  type: 'cycle' | 'duplicate' | 'isolated'
  severity: 'error' | 'warning'
  nodeIds: string[]
  edgeIds: string[]
  description: string
}

export interface HealthMetrics {
  score: number
  issues: HealthIssue[]
  issueCount: number
}

export interface ProcessMetrics {
  processId: string
  processName: string
  activityCount: number
  internalDependencyCount: number
  healthScore: number
  issueCount: number
}

export interface AnalysisResult {
  scale: ScaleMetrics
  health: HealthMetrics
  processSummary?: ProcessMetrics[]
}

/**
 * 分析图数据：规模统计、健康度校验、按流程聚合
 */
export function analyzeGraph(
  graphData: GraphData,
  scope: AnalysisScope = { type: 'global' }
): AnalysisResult {
  const activities = graphData.nodes.filter(n => n.type === 'activity')
  const dependencies = graphData.edges
  
  if (scope.type === 'process' && scope.processId) {
    return analyzeProcessScope(graphData, scope.processId)
  } else {
    return analyzeGlobalScope(graphData)
  }
}

/**
 * 全局口径分析
 */
function analyzeGlobalScope(graphData: GraphData): AnalysisResult {
  const activities = graphData.nodes.filter(n => n.type === 'activity')
  const dependencies = graphData.edges
  
  const scale: ScaleMetrics = {
    activityCount: activities.length,
    internalDependencyCount: dependencies.length,
    externalDependencyInCount: 0,
    externalDependencyOutCount: 0,
    resourceAssociationCount: graphData.resource_edges?.length || 0,
    personnelAssociationCount: graphData.personnel_edges?.length || 0
  }
  
  const health = analyzeHealth(activities, dependencies)
  
  const processSummary = generateProcessSummary(graphData)
  
  return { scale, health, processSummary }
}

/**
 * 当前流程口径分析
 */
function analyzeProcessScope(graphData: GraphData, processId: string): AnalysisResult {
  const activities = graphData.nodes.filter(
    n => n.type === 'activity' && n.process_id === processId
  )
  const activityIds = new Set(activities.map(a => a.id))
  
  const internalDeps: GraphEdge[] = []
  let externalInCount = 0
  let externalOutCount = 0
  
  graphData.edges.forEach(edge => {
    const sourceInProcess = activityIds.has(edge.source)
    const targetInProcess = activityIds.has(edge.target)
    
    if (sourceInProcess && targetInProcess) {
      internalDeps.push(edge)
    } else if (targetInProcess && !sourceInProcess) {
      externalInCount++
    } else if (sourceInProcess && !targetInProcess) {
      externalOutCount++
    }
  })
  
  const resourceAssocCount = (graphData.resource_edges || []).filter(
    e => activityIds.has(e.source)
  ).length
  
  const personnelAssocCount = (graphData.personnel_edges || []).filter(
    e => activityIds.has(e.source)
  ).length
  
  const scale: ScaleMetrics = {
    activityCount: activities.length,
    internalDependencyCount: internalDeps.length,
    externalDependencyInCount: externalInCount,
    externalDependencyOutCount: externalOutCount,
    resourceAssociationCount: resourceAssocCount,
    personnelAssociationCount: personnelAssocCount
  }
  
  const health = analyzeHealth(activities, internalDeps)
  
  return { scale, health }
}

/**
 * 健康度分析：环检测、重复边、孤立节点
 */
function analyzeHealth(activities: GraphNode[], dependencies: GraphEdge[]): HealthMetrics {
  const issues: HealthIssue[] = []
  
  const cycleIssues = detectCycles(activities, dependencies)
  issues.push(...cycleIssues)
  
  const duplicateIssues = detectDuplicates(dependencies)
  issues.push(...duplicateIssues)
  
  const isolatedIssues = detectIsolated(activities, dependencies)
  issues.push(...isolatedIssues)
  
  const score = calculateHealthScore(issues, activities.length)
  
  return {
    score,
    issues,
    issueCount: issues.length
  }
}

/**
 * 环检测（DFS + 三色标记）
 */
function detectCycles(activities: GraphNode[], dependencies: GraphEdge[]): HealthIssue[] {
  const adjList = new Map<string, string[]>()
  activities.forEach(a => adjList.set(a.id, []))
  
  dependencies.forEach(dep => {
    const targets = adjList.get(dep.source)
    if (targets) targets.push(dep.target)
  })
  
  const color = new Map<string, 'white' | 'gray' | 'black'>()
  const parent = new Map<string, string>()
  activities.forEach(a => color.set(a.id, 'white'))
  
  const cycles: HealthIssue[] = []
  
  function dfs(node: string, path: string[]): boolean {
    color.set(node, 'gray')
    path.push(node)
    
    const neighbors = adjList.get(node) || []
    for (const neighbor of neighbors) {
      if (color.get(neighbor) === 'gray') {
        const cycleStart = path.indexOf(neighbor)
        const cycleNodes = path.slice(cycleStart)
        const cycleEdges = cycleNodes.map((n, i) => {
          const next = cycleNodes[(i + 1) % cycleNodes.length]
          return `${n}-${next}`
        })
        
        cycles.push({
          type: 'cycle',
          severity: 'error',
          nodeIds: cycleNodes,
          edgeIds: cycleEdges,
          description: `检测到环：${cycleNodes.join(' → ')}`
        })
        return true
      } else if (color.get(neighbor) === 'white') {
        parent.set(neighbor, node)
        if (dfs(neighbor, path)) return true
      }
    }
    
    color.set(node, 'black')
    path.pop()
    return false
  }
  
  for (const activity of activities) {
    if (color.get(activity.id) === 'white') {
      dfs(activity.id, [])
    }
  }
  
  return cycles
}

/**
 * 重复边检测
 */
function detectDuplicates(dependencies: GraphEdge[]): HealthIssue[] {
  const edgeMap = new Map<string, number>()
  const issues: HealthIssue[] = []
  
  dependencies.forEach(dep => {
    const key = `${dep.source}-${dep.target}`
    edgeMap.set(key, (edgeMap.get(key) || 0) + 1)
  })
  
  edgeMap.forEach((count, key) => {
    if (count > 1) {
      const [source, target] = key.split('-')
      issues.push({
        type: 'duplicate',
        severity: 'warning',
        nodeIds: [source, target],
        edgeIds: [key],
        description: `重复依赖：${key}（${count}次）`
      })
    }
  })
  
  return issues
}

/**
 * 孤立节点检测
 */
function detectIsolated(activities: GraphNode[], dependencies: GraphEdge[]): HealthIssue[] {
  const connectedNodes = new Set<string>()
  
  dependencies.forEach(dep => {
    connectedNodes.add(dep.source)
    connectedNodes.add(dep.target)
  })
  
  const isolated = activities.filter(a => !connectedNodes.has(a.id))
  
  if (isolated.length > 0) {
    return [{
      type: 'isolated',
      severity: 'warning',
      nodeIds: isolated.map(a => a.id),
      edgeIds: [],
      description: `孤立节点：${isolated.length}个`
    }]
  }
  
  return []
}

/**
 * 计算健康评分（0-100）
 */
function calculateHealthScore(issues: HealthIssue[], totalNodes: number): number {
  let score = 100
  
  issues.forEach(issue => {
    if (issue.type === 'cycle') {
      score -= 30
    } else if (issue.type === 'duplicate') {
      score -= 5
    } else if (issue.type === 'isolated') {
      score -= Math.min(20, issue.nodeIds.length * 2)
    }
  })
  
  return Math.max(0, score)
}

/**
 * 按流程生成汇总统计
 */
function generateProcessSummary(graphData: GraphData): ProcessMetrics[] {
  const processMap = new Map<string, {
    activities: GraphNode[]
    internalDeps: GraphEdge[]
  }>()
  
  graphData.nodes
    .filter(n => n.type === 'activity')
    .forEach(activity => {
      const pid = activity.process_id || 'unknown'
      if (!processMap.has(pid)) {
        processMap.set(pid, { activities: [], internalDeps: [] })
      }
      processMap.get(pid)!.activities.push(activity)
    })
  
  graphData.edges.forEach(edge => {
    const sourceNode = graphData.nodes.find(n => n.id === edge.source)
    const targetNode = graphData.nodes.find(n => n.id === edge.target)
    
    if (sourceNode?.process_id && sourceNode.process_id === targetNode?.process_id) {
      const data = processMap.get(sourceNode.process_id)
      if (data) data.internalDeps.push(edge)
    }
  })
  
  const summary: ProcessMetrics[] = []
  
  processMap.forEach((data, processId) => {
    const health = analyzeHealth(data.activities, data.internalDeps)
    
    summary.push({
      processId,
      processName: getProcessName(processId),
      activityCount: data.activities.length,
      internalDependencyCount: data.internalDeps.length,
      healthScore: health.score,
      issueCount: health.issueCount
    })
  })
  
  return summary.sort((a, b) => a.processId.localeCompare(b.processId))
}

/**
 * 获取流程名称映射
 */
function getProcessName(processId: string): string {
  const processMap: Record<string, string> = {
    'P001': 'P001 - 主生产线',
    'P002': 'P002 - 副生产线',
    'T001': 'T001 - 冷链运输',
    'T002': 'T002 - 常温运输',
    'S001': 'S001 - 线上销售',
    'S002': 'S002 - 线下销售',
    'Q001': 'Q001 - 常规质检',
    'Q002': 'Q002 - 专项质检',
    'W001': 'W001 - 主仓库',
    'W002': 'W002 - 分仓库'
  }
  return processMap[processId] || processId
}

