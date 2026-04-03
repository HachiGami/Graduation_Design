import { getNodeDuration } from '@/utils/sopDuration'

const NEG = Number.NEGATIVE_INFINITY

function getNodeId(n: { id?: string; data?: { id?: string } }): string {
  if (n?.id != null && n.id !== '') return String(n.id)
  if (n?.data?.id != null && n.data.id !== '') return String(n.data.id)
  return ''
}

function normalizeNodePayload<T extends { id?: string; data?: unknown }>(n: T): unknown {
  return n.data !== undefined ? n.data : n
}

function getEdgeEndpoints(e: {
  source?: string
  target?: string
  data?: { source?: string; target?: string }
}): { source: string; target: string } | null {
  const source = e.source ?? e.data?.source
  const target = e.target ?? e.data?.target
  if (source == null || target === '' || target == null || source === '') return null
  return { source: String(source), target: String(target) }
}

export interface FindCriticalPathDPResult<T = unknown> {
  path: T[]
  pathIds: string[]
  edgeIds: string[]
  totalDuration: number
  /** 子图存在环，无法进行拓扑与最长路径 */
  hasCycle: boolean
}

/**
 * DAG 上基于节点耗时的最长路径（关键路径）：Kahn 拓扑序 + DP。
 * 不允许使用 Dijkstra/A*（最短路）。
 */
export function findCriticalPathDP<T extends { id?: string; data?: { id?: string } }>(
  nodes: T[],
  edges: Array<{
    source?: string
    target?: string
    data?: { source?: string; target?: string }
  }>,
  startId: string | null = null,
  endId: string | null = null
): FindCriticalPathDPResult<T> {
  const nodeMap = new Map<string, T>()
  for (const n of nodes) {
    const id = getNodeId(n)
    if (!id) continue
    nodeMap.set(id, n)
  }

  const ids = Array.from(nodeMap.keys())
  if (ids.length === 0) {
    return { path: [], pathIds: [], edgeIds: [], totalDuration: 0, hasCycle: false }
  }

  const adjList = new Map<string, string[]>()
  const inDegree = new Map<string, number>()
  for (const id of ids) {
    adjList.set(id, [])
    inDegree.set(id, 0)
  }

  for (const e of edges) {
    const ends = getEdgeEndpoints(e)
    if (!ends) continue
    if (!nodeMap.has(ends.source) || !nodeMap.has(ends.target)) continue
    adjList.get(ends.source)!.push(ends.target)
    inDegree.set(ends.target, (inDegree.get(ends.target) || 0) + 1)
  }

  const dist: Record<string, number> = {}
  const prev: Record<string, string | null> = {}
  for (const id of ids) {
    dist[id] = NEG
    prev[id] = null
  }

  if (startId) {
    if (!nodeMap.has(startId)) {
      return { path: [], pathIds: [], edgeIds: [], totalDuration: 0, hasCycle: false }
    }
    dist[startId] = getNodeDuration(normalizeNodePayload(nodeMap.get(startId)!))
  } else {
    for (const id of ids) {
      if ((inDegree.get(id) || 0) === 0) {
        dist[id] = getNodeDuration(normalizeNodePayload(nodeMap.get(id)!))
      }
    }
  }

  const inDegWork = new Map(inDegree)
  const queue: string[] = []
  for (const id of ids) {
    if ((inDegWork.get(id) || 0) === 0) queue.push(id)
  }

  const topoOrder: string[] = []
  while (queue.length > 0) {
    const u = queue.shift()!
    topoOrder.push(u)

    for (const v of adjList.get(u) || []) {
      inDegWork.set(v, (inDegWork.get(v) || 0) - 1)
      if ((inDegWork.get(v) || 0) === 0) queue.push(v)

      if (dist[u] !== NEG) {
        const vDur = getNodeDuration(normalizeNodePayload(nodeMap.get(v)!))
        const cand = dist[u] + vDur
        if (cand > dist[v]) {
          dist[v] = cand
          prev[v] = u
        }
      }
    }
  }

  if (topoOrder.length !== ids.length) {
    return { path: [], pathIds: [], edgeIds: [], totalDuration: 0, hasCycle: true }
  }

  let targetNodeId: string | null = endId ?? null

  if (endId) {
    if (!nodeMap.has(endId) || dist[endId] === NEG) {
      return { path: [], pathIds: [], edgeIds: [], totalDuration: 0, hasCycle: false }
    }
  } else {
    let maxDist = NEG
    for (const id of ids) {
      if (dist[id] > maxDist) {
        maxDist = dist[id]
        targetNodeId = id
      }
    }
    if (targetNodeId == null || maxDist === NEG) {
      return { path: [], pathIds: [], edgeIds: [], totalDuration: 0, hasCycle: false }
    }
  }

  const rev: string[] = []
  let cur: string | null = targetNodeId
  while (cur) {
    rev.push(cur)
    cur = prev[cur] ?? null
  }
  rev.reverse()
  const pathIds = rev
  const path = pathIds.map(id => nodeMap.get(id)!)

  const edgeIds: string[] = []
  for (let i = 0; i < pathIds.length - 1; i++) {
    edgeIds.push(`${pathIds[i]}-${pathIds[i + 1]}`)
  }

  return {
    path,
    pathIds,
    edgeIds,
    totalDuration: dist[targetNodeId!],
    hasCycle: false
  }
}
