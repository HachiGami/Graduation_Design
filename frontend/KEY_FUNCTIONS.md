# 关键函数完整代码

本文档包含去重叠功能的所有关键函数完整实现代码，可直接查阅。

## 接入点位置

```typescript
// 在 computeDagreLayout() 函数中，第 550 行开始

postProcessBackboneLanes()  // 主干+泳道布局（已完成）

// ===== 以下是 Label-aware 去重叠部分 =====
```

## T1: 计算 Label-Aware 碰撞包围盒

```typescript
// 第 552-583 行
const computeCollisionRect = (nodeId: string) => {
  const node = g2.node(nodeId)
  const meta = nodeMetadata.get(nodeId)
  
  if (meta?.isVirtual) {
    return { x1: node.x, y1: node.y, x2: node.x, y2: node.y }
  }
  
  const category = meta?.category || 'Activity'
  const r = category === 'Activity' ? 25 : 17.5
  const fontSize = category === 'Activity' ? 12 : 10
  const lineHeight = fontSize * 1.2
  const labelW = 100
  const labelMargin = 6
  const padding = 8
  
  // 节点圆形外接框
  const nodeX1 = node.x - r
  const nodeY1 = node.y - r
  const nodeX2 = node.x + r
  const nodeY2 = node.y + r
  
  // Label 在下方
  const labelTop = node.y + r + labelMargin
  const labelX1 = node.x - labelW / 2
  const labelX2 = node.x + labelW / 2
  const labelY1 = labelTop
  const labelY2 = labelTop + lineHeight
  
  // Union + padding
  const x1 = Math.min(nodeX1, labelX1) - padding
  const y1 = Math.min(nodeY1, labelY1) - padding
  const x2 = Math.max(nodeX2, labelX2) + padding
  const y2 = Math.max(nodeY2, labelY2) + padding
  
  return { x1, y1, x2, y2 }
}
```

## 矩形重叠检测

```typescript
// 第 586-588 行
const rectsOverlap = (r1: any, r2: any) => {
  return !(r1.x2 <= r2.x1 || r2.x2 <= r1.x1 || r1.y2 <= r2.y1 || r2.y2 <= r1.y1)
}
```

## 统计重叠数量

```typescript
// 第 591-602 行
const countOverlaps = () => {
  const realNodes = g2.nodes().filter(id => !nodeMetadata.get(id)?.isVirtual)
  let count = 0
  
  for (let i = 0; i < realNodes.length; i++) {
    const r1 = computeCollisionRect(realNodes[i])
    for (let j = i + 1; j < realNodes.length; j++) {
      const r2 = computeCollisionRect(realNodes[j])
      if (rectsOverlap(r1, r2)) count++
    }
  }
  
  return count
}

const overlapCountBefore = countOverlaps()
const debugMode = (window as any).__debugBackboneLayout

if (debugMode) {
  console.log(`[Overlap Detection] Before: ${overlapCountBefore}`)
}
```

## T2: 局部增大 laneGap（优先策略）

```typescript
// 第 634-717 行
const expandLaneGapsPerProcess = () => {
  const realNodes = g2.nodes().filter(id => !nodeMetadata.get(id)?.isVirtual)
  
  // 按流程分组
  const processMap = new Map<string, string[]>()
  realNodes.forEach(nodeId => {
    const laneInfo = nodeLaneInfo.get(nodeId)
    const pid = laneInfo?.processId || 'default'
    if (!processMap.has(pid)) processMap.set(pid, [])
    processMap.get(pid)!.push(nodeId)
  })
  
  processMap.forEach((nodeIds, processId) => {
    if (nodeIds.length === 0) return
    
    // 按 lane 分组（使用 sign * laneIndex 作为 lane key）
    const laneGroups = new Map<number, string[]>()
    nodeIds.forEach(id => {
      const info = nodeLaneInfo.get(id)
      if (!info) return
      const laneKey = info.isBackbone ? 0 : info.sign * info.laneIndex
      if (!laneGroups.has(laneKey)) laneGroups.set(laneKey, [])
      laneGroups.get(laneKey)!.push(id)
    })
    
    const sortedLanes = Array.from(laneGroups.keys()).sort((a, b) => {
      // 负数（上方）在前，0（主干）中间，正数（下方）在后
      const yA = g2.node(laneGroups.get(a)![0]).y
      const yB = g2.node(laneGroups.get(b)![0]).y
      return yA - yB
    })
    
    // 检查相邻 lane 间距，分上下两个方向处理
    const minLaneSeparation = 24
    const backboneIdx = sortedLanes.indexOf(0)
    
    if (backboneIdx === -1) return // 没有主干，跳过
    
    // 向上处理（负 lane）
    for (let i = backboneIdx - 1; i >= 0; i--) {
      const laneUpper = sortedLanes[i]
      const laneLower = sortedLanes[i + 1]
      const nodesUpper = laneGroups.get(laneUpper)!
      const nodesLower = laneGroups.get(laneLower)!
      
      // Upper 层最小 y1 和 Lower 层最大 y2
      let minY1Upper = Infinity
      nodesUpper.forEach(id => {
        const rect = computeCollisionRect(id)
        minY1Upper = Math.min(minY1Upper, rect.y1)
      })
      
      let maxY2Lower = -Infinity
      nodesLower.forEach(id => {
        const rect = computeCollisionRect(id)
        maxY2Lower = Math.max(maxY2Lower, rect.y2)
      })
      
      const currentSep = minY1Upper - maxY2Lower
      if (currentSep < minLaneSeparation) {
        const needExtra = minLaneSeparation - currentSep
        
        // 向上推 Upper 层
        nodesUpper.forEach(id => {
          g2.node(id).y -= needExtra
        })
        
        if (debugMode) {
          console.log(`[Process ${processId}] Expanding gap above, lane=${laneUpper}, extra=${needExtra.toFixed(1)}`)
        }
      }
    }
    
    // 向下处理（正 lane）
    for (let i = backboneIdx; i < sortedLanes.length - 1; i++) {
      const laneUpper = sortedLanes[i]
      const laneLower = sortedLanes[i + 1]
      const nodesUpper = laneGroups.get(laneUpper)!
      const nodesLower = laneGroups.get(laneLower)!
      
      // Upper 层最大 y2 和 Lower 层最小 y1
      let maxY2Upper = -Infinity
      nodesUpper.forEach(id => {
        const rect = computeCollisionRect(id)
        maxY2Upper = Math.max(maxY2Upper, rect.y2)
      })
      
      let minY1Lower = Infinity
      nodesLower.forEach(id => {
        const rect = computeCollisionRect(id)
        minY1Lower = Math.min(minY1Lower, rect.y1)
      })
      
      const currentSep = minY1Lower - maxY2Upper
      if (currentSep < minLaneSeparation) {
        const needExtra = minLaneSeparation - currentSep
        
        // 向下推 Lower 层
        nodesLower.forEach(id => {
          g2.node(id).y += needExtra
        })
        
        if (debugMode) {
          console.log(`[Process ${processId}] Expanding gap below, lane=${laneLower}, extra=${needExtra.toFixed(1)}`)
        }
      }
    }
  })
}
```

## 虚拟节点跟随

```typescript
// 第 719-731 行
const updateVirtualNodes = () => {
  const allNodeIds = g2.nodes()
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
}
```

## T3: 同 Lane 内小幅 Jitter（兜底）

```typescript
// 第 733-766 行
const smallJitterInLaneIfNeeded = () => {
  let overlaps = countOverlaps()
  if (overlaps === 0) return
  
  const realNodes = g2.nodes().filter(id => !nodeMetadata.get(id)?.isVirtual)
  const jitterMax = 20
  
  // 按 x 分组（同列）
  const xGroups = new Map<number, string[]>()
  realNodes.forEach(id => {
    const node = g2.node(id)
    const xRounded = Math.round(node.x / 100) * 100
    if (!xGroups.has(xRounded)) xGroups.set(xRounded, [])
    xGroups.get(xRounded)!.push(id)
  })
  
  xGroups.forEach(nodeIds => {
    // 按 y 排序
    nodeIds.sort((a, b) => {
      const ya = g2.node(a).y
      const yb = g2.node(b).y
      return ya - yb
    })
    
    // 检测并推开
    for (let i = 0; i < nodeIds.length - 1; i++) {
      const idA = nodeIds[i]
      const idB = nodeIds[i + 1]
      const rectA = computeCollisionRect(idA)
      const rectB = computeCollisionRect(idB)
      
      if (rectsOverlap(rectA, rectB)) {
        const overlapAmount = rectA.y2 - rectB.y1
        if (overlapAmount > 0 && overlapAmount < jitterMax) {
          // 向下推 B
          const nodeB = g2.node(idB)
          nodeB.y += overlapAmount + 4
        }
      }
    }
  })
}
```

## T4: X 方向兜底

```typescript
// 第 770-801 行
const expandRankSepsIfNeeded = () => {
  let overlaps = countOverlaps()
  if (overlaps === 0) return
  
  const realNodes = g2.nodes().filter(id => !nodeMetadata.get(id)?.isVirtual)
  
  // 找出重叠对
  const overlapPairs: Array<{id1: string, id2: string}> = []
  for (let i = 0; i < realNodes.length; i++) {
    const r1 = computeCollisionRect(realNodes[i])
    for (let j = i + 1; j < realNodes.length; j++) {
      const r2 = computeCollisionRect(realNodes[j])
      if (rectsOverlap(r1, r2)) {
        overlapPairs.push({ id1: realNodes[i], id2: realNodes[j] })
      }
    }
  }
  
  // 检查是否主要是 X 方向问题
  overlapPairs.forEach(pair => {
    const node1 = g2.node(pair.id1)
    const node2 = g2.node(pair.id2)
    const r1 = computeCollisionRect(pair.id1)
    const r2 = computeCollisionRect(pair.id2)
    
    const overlapW = Math.min(r1.x2, r2.x2) - Math.max(r1.x1, r2.x1)
    const overlapH = Math.min(r1.y2, r2.y2) - Math.max(r1.y1, r2.y1)
    
    if (overlapW > overlapH && Math.abs(node1.x - node2.x) < 150) {
      // X 方向推开
      const rightNode = node1.x > node2.x ? node1 : node2
      rightNode.x += Math.min(overlapW + 20, 120)
    }
  })
}
```

## 调用顺序和最终验证

```typescript
// 第 718-810 行
expandLaneGapsPerProcess()      // T2: 优先局部扩大 laneGap

updateVirtualNodes()            // 更新虚拟节点

smallJitterInLaneIfNeeded()    // T3: 同 lane 内微调
updateVirtualNodes()            // 再次更新虚拟节点

expandRankSepsIfNeeded()        // T4: X 方向兜底
updateVirtualNodes()            // 最后更新虚拟节点

const overlapCountAfter = countOverlaps()

if (debugMode || overlapCountAfter > 0) {
  console.log(`[Overlap Detection] After: ${overlapCountAfter} (before: ${overlapCountBefore})`)
  if (overlapCountAfter === 0) {
    console.log('✅ No overlaps detected!')
  } else {
    console.warn(`⚠️ Still have ${overlapCountAfter} overlaps`)
  }
}
```

## 完整执行流程

```
1. postProcessBackboneLanes()           // 主干+泳道布局
   ↓
2. computeCollisionRect() 定义         // T1: Label-aware 包围盒
   ↓
3. countOverlaps() → overlapCountBefore // 统计初始重叠
   ↓
4. expandLaneGapsPerProcess()          // T2: 局部扩大 laneGap
   ↓
5. updateVirtualNodes()                // 虚拟节点跟随
   ↓
6. smallJitterInLaneIfNeeded()        // T3: 同 lane 内微调
   ↓
7. updateVirtualNodes()                // 虚拟节点跟随
   ↓
8. expandRankSepsIfNeeded()           // T4: X 方向兜底
   ↓
9. updateVirtualNodes()                // 虚拟节点跟随
   ↓
10. countOverlaps() → overlapCountAfter // 统计最终重叠（必须为 0）
    ↓
11. 网格吸附和 fitView                 // 原有逻辑继续
```

## 验收检查点

在浏览器控制台执行：

```javascript
// 1. 开启调试模式
window.__debugBackboneLayout = true

// 2. 刷新页面或点击"重置视图"

// 3. 查看控制台输出，确认以下内容：
// [Overlap Detection] Before: X
// [Process P001] Expanding gap below, lane=1, extra=Y
// ...
// [Overlap Detection] After: 0 (before: X)
// ✅ No overlaps detected!
```

## 关键参数速查

| 参数名 | 行号 | 默认值 | 说明 |
|--------|------|--------|------|
| `r` (Activity) | 559 | 25 | Activity 节点半径 |
| `r` (Resource) | 559 | 17.5 | Resource/Personnel 节点半径 |
| `fontSize` (Activity) | 560 | 12 | Activity label 字体大小 |
| `fontSize` (Resource) | 560 | 10 | Resource label 字体大小 |
| `lineHeight` | 561 | fontSize * 1.2 | Label 行高 |
| `labelW` | 562 | 100 | Label 宽度 |
| `labelMargin` | 563 | 6 | Label 与节点间距 |
| `padding` | 564 | 8 | 碰撞框 padding |
| `minLaneSeparation` | 649 | 24 | 触发扩大 laneGap 阈值 |
| `jitterMax` | 736 | 20 | 同 lane 内最大微调幅度 |
| `extraDx` (max) | 799 | 120 | X 方向最大追加间距 |

## 注意事项

1. **虚拟节点**：每次调整真实节点后必须调用 `updateVirtualNodes()`
2. **主干固定**：在 `expandLaneGapsPerProcess()` 中，lane=0（主干）不参与推移
3. **确定性**：所有排序和处理顺序必须固定，不使用随机数
4. **性能**：`countOverlaps()` 是 O(n²)，生产环境可考虑只在最后验证一次
5. **调试**：只在 `debugMode=true` 或 `overlapCountAfter > 0` 时输出日志





