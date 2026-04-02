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
