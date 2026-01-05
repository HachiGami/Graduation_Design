import type { GraphData, GraphNode } from '@/types'

export interface ResourceShortage {
  resourceId: string
  resourceName: string
  type: string
  totalDemand: number
  available: number
  shortage: number
  relatedActivityIds: string[]
}

export interface ResourceRisk {
  resourceId: string
  resourceName: string
  type: string
  referenceCount: number
  relatedActivityIds: string[]
}

export interface ResourceCheckResult {
  dataLevel: 'level0' | 'level1'
  shortageCount: number
  shortageList: ResourceShortage[]
  riskList: ResourceRisk[]
}

/**
 * 原料静态校验
 */
export function checkResources(
  graphData: GraphData,
  processId?: string
): ResourceCheckResult {
  const consumableResources = (graphData.resource_nodes || []).filter(
    r => r.type === 'material' || r.type === 'consumable'
  )
  
  if (consumableResources.length === 0) {
    return {
      dataLevel: 'level0',
      shortageCount: 0,
      shortageList: [],
      riskList: []
    }
  }
  
  const activityFilter = processId
    ? (actId: string) => {
        const node = graphData.nodes.find(n => n.id === actId)
        return node?.process_id === processId
      }
    : () => true
  
  const resourceUsages = (graphData.resource_edges || []).filter(
    edge => activityFilter(edge.source)
  )
  
  const hasQuantityData = checkDataLevel(consumableResources, resourceUsages)
  
  if (hasQuantityData) {
    return performLevel1Check(consumableResources, resourceUsages)
  } else {
    return performLevel0Check(consumableResources, resourceUsages)
  }
}

/**
 * 检查数据层级
 */
function checkDataLevel(
  resources: GraphNode[],
  usages: any[]
): boolean {
  const hasResourceQuantity = resources.some(r => 
    r.quantity !== undefined && r.quantity !== null
  )
  
  const hasUsageQuantity = usages.some(u => 
    u.quantity !== undefined && u.quantity !== null
  )
  
  return hasResourceQuantity && hasUsageQuantity
}

/**
 * Level 1：数量短缺判断
 */
function performLevel1Check(
  resources: GraphNode[],
  usages: any[]
): ResourceCheckResult {
  const demandMap = new Map<string, {
    totalDemand: number
    relatedActivityIds: string[]
  }>()
  
  usages.forEach(usage => {
    const resourceId = usage.target
    const quantity = parseFloat(usage.quantity) || 0
    const activityId = usage.source
    
    if (!demandMap.has(resourceId)) {
      demandMap.set(resourceId, { totalDemand: 0, relatedActivityIds: [] })
    }
    
    const data = demandMap.get(resourceId)!
    data.totalDemand += quantity
    if (!data.relatedActivityIds.includes(activityId)) {
      data.relatedActivityIds.push(activityId)
    }
  })
  
  const shortageList: ResourceShortage[] = []
  
  resources.forEach(resource => {
    const demand = demandMap.get(resource.id)
    if (!demand) return
    
    const available = parseFloat(resource.quantity as any) || 0
    const shortage = demand.totalDemand - available
    
    if (shortage > 0) {
      shortageList.push({
        resourceId: resource.id,
        resourceName: resource.name,
        type: resource.type || 'unknown',
        totalDemand: demand.totalDemand,
        available,
        shortage,
        relatedActivityIds: demand.relatedActivityIds
      })
    }
  })
  
  shortageList.sort((a, b) => b.shortage - a.shortage)
  
  return {
    dataLevel: 'level1',
    shortageCount: shortageList.length,
    shortageList,
    riskList: []
  }
}

/**
 * Level 0：关联风险排行
 */
function performLevel0Check(
  resources: GraphNode[],
  usages: any[]
): ResourceCheckResult {
  const referenceMap = new Map<string, Set<string>>()
  
  usages.forEach(usage => {
    const resourceId = usage.target
    const activityId = usage.source
    
    if (!referenceMap.has(resourceId)) {
      referenceMap.set(resourceId, new Set())
    }
    referenceMap.get(resourceId)!.add(activityId)
  })
  
  const riskList: ResourceRisk[] = []
  
  resources.forEach(resource => {
    const relatedActivities = referenceMap.get(resource.id)
    if (relatedActivities && relatedActivities.size > 0) {
      riskList.push({
        resourceId: resource.id,
        resourceName: resource.name,
        type: resource.type || 'unknown',
        referenceCount: relatedActivities.size,
        relatedActivityIds: Array.from(relatedActivities)
      })
    }
  })
  
  riskList.sort((a, b) => b.referenceCount - a.referenceCount)
  
  return {
    dataLevel: 'level0',
    shortageCount: 0,
    shortageList: [],
    riskList
  }
}

/**
 * 按流程汇总原料风险
 */
export function summarizeResourceRisksByProcess(
  graphData: GraphData
): Array<{
  processId: string
  processName: string
  shortageCount: number
  riskCount: number
}> {
  const processIds = new Set(
    graphData.nodes
      .filter(n => n.type === 'activity' && n.process_id)
      .map(n => n.process_id!)
  )
  
  const summary: Array<{
    processId: string
    processName: string
    shortageCount: number
    riskCount: number
  }> = []
  
  processIds.forEach(processId => {
    const result = checkResources(graphData, processId)
    
    summary.push({
      processId,
      processName: getProcessName(processId),
      shortageCount: result.shortageCount,
      riskCount: result.riskList.length
    })
  })
  
  return summary.sort((a, b) => {
    if (a.shortageCount !== b.shortageCount) {
      return b.shortageCount - a.shortageCount
    }
    return b.riskCount - a.riskCount
  })
}

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

