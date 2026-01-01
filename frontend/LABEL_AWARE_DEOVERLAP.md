# Label-Aware 去重叠实现文档

## 概述

在"主干+泳道"布局的基础上，实现 Label-aware 的去重叠后处理，确保所有节点（包括其 label）都不重叠，同时保持布局结构规整。

## 核心原则

1. **保持结构不变**：主干直线、lane 归属、确定性
2. **Label-aware**：使用真实渲染参数计算碰撞框
3. **优先级策略**：局部扩大 laneGap > 同 lane 微调 > X 方向兜底
4. **真实去重叠**：不隐藏 label，overlapCount 必须为 0

## 真实渲染参数

### Activity 节点
- **Symbol**: `circle`, `symbolSize=50` (直径) → 半径 `r=25`
- **Label**: 
  - `fontSize=12`, `lineHeight=14.4` (1.2倍)
  - `width=100` (固定显示宽度)
  - `position='bottom'` (在节点下方)
  - `overflow='truncate'` (不换行)

### Resource/Personnel 节点
- **Symbol**: `rect`/`diamond`, `symbolSize=35` → 外接圆半径 `r≈17.5`
- **Label**:
  - `fontSize=10`, `lineHeight=12` (1.2倍)
  - `width=100`
  - `position='bottom'`
  - `overflow='truncate'`

### Virtual 节点
- **Symbol**: `symbolSize=1`, `opacity=0`
- **不参与碰撞检测**（但坐标需跟随，保持边不倾斜）

## 实现细节

### T1: 计算 Label-Aware 碰撞包围盒

**函数**: `computeCollisionRect(nodeId: string)`

**位置**: 第 552-583 行

**算法**:
1. 获取节点类型和参数（r, fontSize, lineHeight）
2. 计算节点圆形外接矩形：`[x-r, y-r] ~ [x+r, y+r]`
3. 计算 label 矩形（position='bottom'）：
   - `labelTop = y + r + labelMargin` (labelMargin=6)
   - `labelRect = [x-50, labelTop] ~ [x+50, labelTop+lineHeight]`
4. 取 union(nodeRect, labelRect)
5. 四周扩展 padding=8

**返回**: `{ x1, y1, x2, y2 }`

**关键代码**:
```typescript
const r = category === 'Activity' ? 25 : 17.5
const fontSize = category === 'Activity' ? 12 : 10
const lineHeight = fontSize * 1.2
const labelW = 100
const labelMargin = 6
const padding = 8

// 节点外接框
const nodeX1 = node.x - r, nodeY1 = node.y - r
const nodeX2 = node.x + r, nodeY2 = node.y + r

// Label 在下方
const labelTop = node.y + r + labelMargin
const labelX1 = node.x - labelW / 2, labelX2 = node.x + labelW / 2
const labelY1 = labelTop, labelY2 = labelTop + lineHeight

// Union + padding
const x1 = Math.min(nodeX1, labelX1) - padding
const y1 = Math.min(nodeY1, labelY1) - padding
const x2 = Math.max(nodeX2, labelX2) + padding
const y2 = Math.max(nodeY2, labelY2) + padding
```

### T2: 优先局部扩大 laneGap

**函数**: `expandLaneGapsPerProcess()`

**位置**: 第 634-717 行

**目标**: 保持布局规整，优先通过增大 lane 间距消除重叠

**算法**:
1. 按流程分组节点
2. 对每个流程：
   - 按 lane 分组（使用 `nodeLaneInfo` 中的 lane 信息）
   - 按 y 坐标排序 lanes
   - 找到主干（lane=0）的索引
3. **向上处理**（负 lane，从主干向上）：
   - 对每对相邻 lanes (Upper, Lower)
   - 计算 Upper 层所有节点的最小 y1 和 Lower 层的最大 y2
   - 若间距 < minLaneSeparation (24px)：
     - 向上推 Upper 层：`node.y -= needExtra`
4. **向下处理**（正 lane，从主干向下）：
   - 对每对相邻 lanes (Upper, Lower)
   - 计算 Upper 层的最大 y2 和 Lower 层的最小 y1
   - 若间距 < minLaneSeparation (24px)：
     - 向下推 Lower 层：`node.y += needExtra`
5. **主干固定不动**（lane=0 不参与推移）

**关键特性**:
- **确定性**: 按固定顺序处理，相同输入产生相同结果
- **对称性**: 上方 lanes 向上推，下方 lanes 向下推
- **局部性**: 只调整拥挤的 lanes，不影响全局

**关键代码**:
```typescript
// 向上处理（负 lane）
for (let i = backboneIdx - 1; i >= 0; i--) {
  // 计算 Upper 和 Lower 间距
  const currentSep = minY1Upper - maxY2Lower
  if (currentSep < minLaneSeparation) {
    const needExtra = minLaneSeparation - currentSep
    // 向上推 Upper 层
    nodesUpper.forEach(id => {
      g2.node(id).y -= needExtra
    })
  }
}

// 向下处理（正 lane）
for (let i = backboneIdx; i < sortedLanes.length - 1; i++) {
  // 计算间距并向下推 Lower 层
  if (currentSep < minLaneSeparation) {
    nodesLower.forEach(id => {
      g2.node(id).y += needExtra
    })
  }
}
```

### T3: 同 Lane 内小幅 Jitter

**函数**: `smallJitterInLaneIfNeeded()`

**位置**: 第 733-766 行

**目标**: 若 T2 后仍有重叠，在不改变 lane 归属的前提下做极小调整

**算法**:
1. 检查是否还有重叠，若无则返回
2. 按 x 分组（同列节点）
3. 对每列：
   - 按 y 排序节点
   - 检测相邻节点是否重叠
   - 若重叠且 overlapAmount < jitterMax (20px)：
     - 向下推下方节点：`nodeB.y += overlapAmount + 4`
4. 保持列内排序不变

**限制**:
- 最大调整幅度：20px
- 仅处理相邻节点的小重叠
- 不改变节点的 lane 归属

**关键代码**:
```typescript
xGroups.forEach(nodeIds => {
  nodeIds.sort((a, b) => g2.node(a).y - g2.node(b).y)
  
  for (let i = 0; i < nodeIds.length - 1; i++) {
    const rectA = computeCollisionRect(nodeIds[i])
    const rectB = computeCollisionRect(nodeIds[i + 1])
    
    if (rectsOverlap(rectA, rectB)) {
      const overlapAmount = rectA.y2 - rectB.y1
      if (overlapAmount > 0 && overlapAmount < jitterMax) {
        g2.node(nodeIds[i + 1]).y += overlapAmount + 4
      }
    }
  }
})
```

### T4: X 方向兜底

**函数**: `expandRankSepsIfNeeded()`

**位置**: 第 770-801 行

**目标**: 处理 X 方向间距不足导致的重叠

**算法**:
1. 若仍有重叠，找出所有重叠节点对
2. 对每对重叠节点：
   - 计算重叠宽度和高度
   - 若 overlapW > overlapH（主要是 X 方向问题）
   - 且两节点 X 距离 < 150px
   - 则向右推右侧节点：`rightNode.x += min(overlapW + 20, 120)`

**限制**:
- 仅处理 X 方向为主的重叠
- 最大追加间距：120px
- 慎用，通常 T2+T3 已足够

**关键代码**:
```typescript
overlapPairs.forEach(pair => {
  const overlapW = Math.min(r1.x2, r2.x2) - Math.max(r1.x1, r2.x1)
  const overlapH = Math.min(r1.y2, r2.y2) - Math.max(r1.y1, r2.y1)
  
  if (overlapW > overlapH && Math.abs(node1.x - node2.x) < 150) {
    const rightNode = node1.x > node2.x ? node1 : node2
    rightNode.x += Math.min(overlapW + 20, 120)
  }
})
```

### 虚拟节点跟随

**函数**: `updateVirtualNodes()`

**位置**: 第 719-731 行（调用 3 次：T2 后、T3 后、T4 后）

**目标**: 保持虚拟节点跟随真实节点，确保边不倾斜

**算法**:
1. 遍历所有虚拟节点
2. 找到相邻的真实节点（通过边连接）
3. 虚拟节点 y 坐标 = 相邻真实节点 y 的平均值

**调用时机**:
- 每次调整真实节点坐标后都需调用
- 确保边的路径保持水平/规则

**关键代码**:
```typescript
allNodeIds.forEach(nodeId => {
  const meta = nodeMetadata.get(nodeId)
  if (!meta?.isVirtual) return
  
  const edges = g2.nodeEdges(nodeId) || []
  const neighbors = edges.map(e => e.v === nodeId ? e.w : e.v)
    .filter(n => !nodeMetadata.get(n)?.isVirtual)
  
  if (neighbors.length > 0) {
    const avgY = neighbors.reduce((sum, n) => sum + g2.node(n).y, 0) / neighbors.length
    g2.node(nodeId).y = avgY
  }
})
```

## 调试输出

### 控制台信息

开启调试模式后（`window.__debugBackboneLayout = true`），会输出：

```
[Overlap Detection] Before: 5
[Process P001] Expanding gap below, lane=1, extra=18.5
[Process P001] Expanding gap below, lane=2, extra=12.0
[Process P002] Expanding gap above, lane=-1, extra=6.3
[Overlap Detection] After: 0 (before: 5)
✅ No overlaps detected!
```

### 信息解读

- **Before**: 初始重叠数量（T2 之前）
- **Expanding gap**: 具体扩大了哪些 lanes，扩大量是多少
- **After**: 最终重叠数量（必须为 0）
- **✅ No overlaps detected!**: 验收通过标志

## 验收方法

### 1. 自动验收（控制台）

```javascript
window.__debugBackboneLayout = true
// 刷新页面或点击"重置视图"
// 查看控制台输出，确认：
// - [Overlap Detection] After: 0
// - ✅ No overlaps detected!
```

### 2. 视觉验收

1. **缩放到 100%**
2. **逐列检查**：
   - 节点圆形不重叠
   - Label 不重叠（label 在节点下方，宽度 100px）
3. **检查主干**：
   - 主干节点仍在一条水平线上
   - Lane 归属未改变

### 3. 稳定性验收

1. 点击"重置视图" 5 次
2. 每次检查：
   - 坐标完全一致
   - overlapCount 都是 0

### 4. 高亮验收

1. 点击节点高亮
2. 取消高亮
3. 确认：
   - 坐标未改变
   - overlapCount 未重新计算

## 配置参数

| 参数 | 默认值 | 建议范围 | 说明 |
|------|--------|---------|------|
| `minLaneSeparation` | 24 | 16-32 | 触发扩大 laneGap 的阈值，越大越宽松 |
| `labelMargin` | 6 | 4-10 | Label 与节点圆形的间距 |
| `padding` | 8 | 6-12 | 碰撞包围盒四周 padding |
| `jitterMax` | 20 | 10-30 | 同 lane 内最大微调幅度 |
| `extraDx` (max) | 120 | 80-160 | X 方向最大追加间距 |

## 性能考虑

### 时间复杂度

- `computeCollisionRect()`: O(1)
- `countOverlaps()`: O(n²) - 仅调试时使用
- `expandLaneGapsPerProcess()`: O(p * l * n/p) ≈ O(n * l)
  - p: 流程数, l: 平均 lane 数, n: 节点数
- `smallJitterInLaneIfNeeded()`: O(n log n) - 排序
- `expandRankSepsIfNeeded()`: O(n²) - 最坏情况，通常不触发

### 优化建议

1. **生产环境**: 关闭 `countOverlaps()` 的频繁调用，只在最后验证一次
2. **大图**: 若节点数 > 500，可考虑用空间索引（如四叉树）加速碰撞检测
3. **调试模式**: 仅在需要时开启，避免 console.log 影响性能

## 常见问题

### Q1: overlapCount 不为 0 怎么办？

**A**: 检查以下参数：
1. `minLaneSeparation` 是否太小（建议 ≥24）
2. `jitterMax` 是否太小（建议 ≥20）
3. 是否需要增大 `labelMargin` 或 `padding`

### Q2: 布局变得不规整（节点上下乱跳）？

**A**: 检查：
1. T2 是否正常工作（应优先扩大 laneGap）
2. T3 的 `jitterMax` 是否太大（应 ≤20）
3. 是否主干被移动（主干应固定不动）

### Q3: 主干不再是直线？

**A**: 检查：
1. `expandLaneGapsPerProcess()` 中主干是否被排除（`lane=0` 不参与调整）
2. `postProcessBackboneLanes()` 中主干 y0 是否正确设置

### Q4: 刷新后布局变化？

**A**: 检查确定性：
1. 所有排序是否稳定（使用 `id` 作为 tie-breaker）
2. T2 处理顺序是否固定（从上到下/从下到上）
3. 是否有随机因素（如 Math.random()）

## 总结

Label-aware 去重叠通过三层策略（局部扩大 laneGap → 同 lane 微调 → X 方向兜底），在保持布局结构规整的前提下，真实消除所有重叠，实现 overlapCount=0 的硬指标。

核心优势：
- ✅ 使用真实渲染参数，无视觉误差
- ✅ 优先保持结构规整（局部扩大 laneGap）
- ✅ 确定性可复现
- ✅ 主干固定不动，lane 归属不变
- ✅ 虚拟节点跟随，边保持规则

