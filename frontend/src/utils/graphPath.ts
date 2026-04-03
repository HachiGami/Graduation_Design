/**
 * 在有向依赖边上求最短路径（BFS，边权为 1，即最少依赖步数）。
 */
export function shortestDirectedPath(
  edges: Array<{ source: string; target: string }>,
  sourceId: string,
  targetId: string
): { nodeIds: string[]; edgeIds: string[] } | null {
  if (sourceId === targetId) {
    return { nodeIds: [sourceId], edgeIds: [] }
  }

  const adj = new Map<string, Array<{ to: string; edgeId: string }>>()
  for (const e of edges) {
    if (!e?.source || !e?.target) continue
    const edgeId = `${e.source}-${e.target}`
    if (!adj.has(e.source)) adj.set(e.source, [])
    adj.get(e.source)!.push({ to: e.target, edgeId })
  }

  const queue: string[] = [sourceId]
  const parent = new Map<string, { from: string; edgeId: string }>()

  while (queue.length > 0) {
    const u = queue.shift()!
    if (u === targetId) break
    for (const { to, edgeId } of adj.get(u) || []) {
      if (parent.has(to)) continue
      parent.set(to, { from: u, edgeId })
      queue.push(to)
    }
  }

  if (!parent.has(targetId)) return null

  const nodeIds: string[] = []
  const edgeIds: string[] = []
  let cur = targetId
  while (cur !== sourceId) {
    const info = parent.get(cur)
    if (!info) return null
    nodeIds.push(cur)
    edgeIds.push(info.edgeId)
    cur = info.from
  }
  nodeIds.push(sourceId)
  nodeIds.reverse()
  edgeIds.reverse()
  return { nodeIds, edgeIds }
}
