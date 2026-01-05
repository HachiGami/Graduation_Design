import type { GraphNode, GraphEdge } from '@/types'

export interface CPMActivity {
  id: string
  name: string
  duration: number
  es: number
  ef: number
  ls: number
  lf: number
  tf: number
  isCritical: boolean
}

export interface CPMResult {
  totalDuration: number
  criticalPath: string[]
  criticalActivities: CPMActivity[]
  topBottlenecks: CPMActivity[]
  allActivities: CPMActivity[]
  hasCycle: boolean
  errorMessage?: string
}

/**
 * 计算关键路径（CPM算法）
 */
export function calculateCPM(
  activities: GraphNode[],
  dependencies: GraphEdge[]
): CPMResult {
  if (activities.length === 0) {
    return {
      totalDuration: 0,
      criticalPath: [],
      criticalActivities: [],
      topBottlenecks: [],
      allActivities: [],
      hasCycle: false
    }
  }
  
  const topoResult = topologicalSort(activities, dependencies)
  
  if (!topoResult.success) {
    return {
      totalDuration: 0,
      criticalPath: [],
      criticalActivities: [],
      topBottlenecks: [],
      allActivities: [],
      hasCycle: true,
      errorMessage: '检测到环，无法计算关键路径'
    }
  }
  
  const activityMap = new Map<string, CPMActivity>()
  activities.forEach(a => {
    activityMap.set(a.id, {
      id: a.id,
      name: a.name,
      duration: a.estimated_duration || 0,
      es: 0,
      ef: 0,
      ls: 0,
      lf: 0,
      tf: 0,
      isCritical: false
    })
  })
  
  const adjList = buildAdjacencyList(activities, dependencies)
  const predecessors = buildPredecessorList(activities, dependencies)
  
  forwardPass(topoResult.sorted, activityMap, adjList)
  
  const totalDuration = Math.max(...Array.from(activityMap.values()).map(a => a.ef))
  
  backwardPass(topoResult.sorted, activityMap, predecessors, totalDuration)
  
  calculateFloats(activityMap)
  
  const criticalActivities = Array.from(activityMap.values()).filter(a => a.isCritical)
  
  const criticalPath = extractCriticalPath(criticalActivities, dependencies)
  
  const topBottlenecks = Array.from(activityMap.values())
    .sort((a, b) => b.duration - a.duration)
    .slice(0, 5)
  
  return {
    totalDuration,
    criticalPath,
    criticalActivities,
    topBottlenecks,
    allActivities: Array.from(activityMap.values()),
    hasCycle: false
  }
}

/**
 * 拓扑排序（检测环）
 */
function topologicalSort(
  activities: GraphNode[],
  dependencies: GraphEdge[]
): { success: boolean; sorted: string[] } {
  const inDegree = new Map<string, number>()
  const adjList = new Map<string, string[]>()
  
  activities.forEach(a => {
    inDegree.set(a.id, 0)
    adjList.set(a.id, [])
  })
  
  dependencies.forEach(dep => {
    if (adjList.has(dep.source)) {
      adjList.get(dep.source)!.push(dep.target)
    }
    if (inDegree.has(dep.target)) {
      inDegree.set(dep.target, inDegree.get(dep.target)! + 1)
    }
  })
  
  const queue: string[] = []
  inDegree.forEach((degree, id) => {
    if (degree === 0) queue.push(id)
  })
  
  const sorted: string[] = []
  
  while (queue.length > 0) {
    const current = queue.shift()!
    sorted.push(current)
    
    const neighbors = adjList.get(current) || []
    neighbors.forEach(neighbor => {
      const newDegree = inDegree.get(neighbor)! - 1
      inDegree.set(neighbor, newDegree)
      if (newDegree === 0) {
        queue.push(neighbor)
      }
    })
  }
  
  return {
    success: sorted.length === activities.length,
    sorted
  }
}

/**
 * 构建邻接表
 */
function buildAdjacencyList(
  activities: GraphNode[],
  dependencies: GraphEdge[]
): Map<string, string[]> {
  const adjList = new Map<string, string[]>()
  
  activities.forEach(a => adjList.set(a.id, []))
  
  dependencies.forEach(dep => {
    const list = adjList.get(dep.source)
    if (list) list.push(dep.target)
  })
  
  return adjList
}

/**
 * 构建前驱列表
 */
function buildPredecessorList(
  activities: GraphNode[],
  dependencies: GraphEdge[]
): Map<string, string[]> {
  const predecessors = new Map<string, string[]>()
  
  activities.forEach(a => predecessors.set(a.id, []))
  
  dependencies.forEach(dep => {
    const list = predecessors.get(dep.target)
    if (list) list.push(dep.source)
  })
  
  return predecessors
}

/**
 * 前推计算ES/EF
 */
function forwardPass(
  sorted: string[],
  activityMap: Map<string, CPMActivity>,
  adjList: Map<string, string[]>
): void {
  sorted.forEach(id => {
    const activity = activityMap.get(id)!
    activity.ef = activity.es + activity.duration
    
    const successors = adjList.get(id) || []
    successors.forEach(succId => {
      const successor = activityMap.get(succId)
      if (successor) {
        successor.es = Math.max(successor.es, activity.ef)
      }
    })
  })
}

/**
 * 后推计算LS/LF
 */
function backwardPass(
  sorted: string[],
  activityMap: Map<string, CPMActivity>,
  predecessors: Map<string, string[]>,
  totalDuration: number
): void {
  const reversed = [...sorted].reverse()
  
  reversed.forEach(id => {
    const activity = activityMap.get(id)!
    
    if (activity.lf === 0) {
      activity.lf = totalDuration
    }
    
    activity.ls = activity.lf - activity.duration
    
    const preds = predecessors.get(id) || []
    preds.forEach(predId => {
      const predecessor = activityMap.get(predId)
      if (predecessor) {
        if (predecessor.lf === 0) {
          predecessor.lf = activity.ls
        } else {
          predecessor.lf = Math.min(predecessor.lf, activity.ls)
        }
      }
    })
  })
}

/**
 * 计算时差并标记关键活动
 */
function calculateFloats(activityMap: Map<string, CPMActivity>): void {
  activityMap.forEach(activity => {
    activity.tf = activity.ls - activity.es
    activity.isCritical = activity.tf === 0
  })
}

/**
 * 提取关键路径序列
 */
function extractCriticalPath(
  criticalActivities: CPMActivity[],
  dependencies: GraphEdge[]
): string[] {
  if (criticalActivities.length === 0) return []
  
  const criticalIds = new Set(criticalActivities.map(a => a.id))
  const criticalEdges = dependencies.filter(
    dep => criticalIds.has(dep.source) && criticalIds.has(dep.target)
  )
  
  const adjList = new Map<string, string[]>()
  const inDegree = new Map<string, number>()
  
  criticalActivities.forEach(a => {
    adjList.set(a.id, [])
    inDegree.set(a.id, 0)
  })
  
  criticalEdges.forEach(edge => {
    adjList.get(edge.source)!.push(edge.target)
    inDegree.set(edge.target, inDegree.get(edge.target)! + 1)
  })
  
  const startNodes = Array.from(inDegree.entries())
    .filter(([_, degree]) => degree === 0)
    .map(([id, _]) => id)
  
  if (startNodes.length === 0) {
    return criticalActivities.map(a => a.id)
  }
  
  const path: string[] = []
  let current = startNodes[0]
  
  while (current) {
    path.push(current)
    const neighbors = adjList.get(current) || []
    current = neighbors[0]
  }
  
  return path
}

