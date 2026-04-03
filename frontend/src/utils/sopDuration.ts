/**
 * 根据 SOP 步骤汇总时长（分钟）。用于展示与废弃的手动 estimated_duration 解耦后的时长。
 */
export function sumSopStepDurations(steps: unknown): number {
  if (!Array.isArray(steps)) return 0
  return steps.reduce((sum, step: { duration?: unknown }) => {
    const d = Number((step as { duration?: unknown })?.duration)
    return sum + (Number.isFinite(d) ? d : 0)
  }, 0)
}

/**
 * 关键路径/DP 使用的单节点耗时（分钟），与图谱 node.data 对齐。
 * 优先：SOP 步骤累加（若有正数和）；否则 duration、working_hours_duration；
 * 再否则 duration_minutes、estimated_duration。
 */
export function getNodeDuration(nodeData: unknown): number {
  if (!nodeData || typeof nodeData !== 'object') return 0
  const n = nodeData as Record<string, unknown>
  const sopSum = sumSopStepDurations(n.sop_steps)
  if (sopSum > 0) return sopSum
  const d = Number(n.duration)
  if (Number.isFinite(d) && d > 0) return d
  const wh = Number(n.working_hours_duration)
  if (Number.isFinite(wh) && wh > 0) return wh
  const dm = Number(n.duration_minutes)
  if (Number.isFinite(dm) && dm > 0) return dm
  const ed = Number(n.estimated_duration)
  if (Number.isFinite(ed) && ed > 0) return ed
  return 0
}

/** 与 getNodeDuration 相同，供图谱/组件历史别名使用 */
export function resolveActivityDurationMinutes(node: unknown): number {
  return getNodeDuration(node)
}
