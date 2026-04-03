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

/** 与图谱/CPM 展示一致：优先 SOP 步骤合计，否则 duration_minutes，再否则 estimated_duration（图数据常不带 sop_steps） */
export function resolveActivityDurationMinutes(node: unknown): number {
  if (!node || typeof node !== 'object') return 0
  const n = node as Record<string, unknown>
  const sopSum = sumSopStepDurations(n.sop_steps)
  if (sopSum > 0) return sopSum
  const dm = Number(n.duration_minutes)
  if (Number.isFinite(dm) && dm > 0) return dm
  const ed = Number(n.estimated_duration)
  if (Number.isFinite(ed) && ed > 0) return ed
  return 0
}
