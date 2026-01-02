<template>
  <div class="graph-container">
    <div class="graph-controls">
      <el-button @click="resetView" :icon="'Refresh'">重置视图</el-button>
      <el-text type="info" size="small" style="margin-left: 10px;">左键查看详情 | 右键展开资源/人员</el-text>
    </div>
    <div ref="chartRef" class="dependency-graph" @contextmenu.prevent></div>
    
    <!-- 活动详情抽屉 -->
    <el-drawer
      v-model="detailDrawerVisible"
      :title="selectedActivity?.name || '活动详情'"
      size="50%"
      direction="rtl"
    >
      <div v-if="selectedActivity" class="activity-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="活动名称">{{ selectedActivity.name }}</el-descriptions-item>
          <el-descriptions-item label="流程域">{{ selectedActivity.domain || '未知' }}</el-descriptions-item>
          <el-descriptions-item label="流程ID">{{ selectedActivity.process_id || '未知' }}</el-descriptions-item>
          <el-descriptions-item label="活动类型">{{ selectedActivity.type }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedActivity.status)">{{ selectedActivity.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="预计时长">{{ selectedActivity.estimated_duration }}分钟</el-descriptions-item>
          <el-descriptions-item label="描述">{{ selectedActivity.description || '无' }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import dagre from 'dagre'
import type { GraphData } from '@/types'

const props = defineProps<{
  data: GraphData
  highlightActive?: boolean
  highlightSet?: {nodeIds: Set<string>, edgeIds: Set<string>}
}>()

const emit = defineEmits<{
  nodeClick: [node: any]
}>()

const chartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null
const expandedActivities = ref<Set<string>>(new Set())
const detailDrawerVisible = ref(false)
const selectedActivity = ref<any>(null)

// T5: 高亮状态管理
// let currentHoverNode: string | null = null

// 缓存布局结果
let cachedNodePositions: Map<string, { x: number, y: number, isVirtual?: boolean }> | null = null
let cachedVirtualNodes: string[] = []
let cachedDataHash = ''

const getStatusType = (status: string) => {
  const typeMap: Record<string, string> = {
    'pending': 'info',
    'in_progress': 'warning',
    'completed': 'success',
    'paused': 'warning',
    'cancelled': 'danger'
  }
  return typeMap[status] || 'info'
}

const resetView = () => {
  expandedActivities.value.clear()
  cachedNodePositions = null
  cachedVirtualNodes = []
  cachedDataHash = ''
  if (chartInstance) {
    chartInstance.resize()
    initChart()
  }
}

const toggleActivityExpansion = (activityId: string) => {
  if (expandedActivities.value.has(activityId)) {
    expandedActivities.value.delete(activityId)
    console.log('[CTX] collapse', activityId)
  } else {
    expandedActivities.value.add(activityId)
    console.log('[CTX] expand', activityId)
  }
  initChart({ preserveView: true })
}

// 通过 id 查找当前 series 数据索引
const getDataIndexById = (id: string): number => {
  if (!chartInstance) return -1
  const opt = chartInstance.getOption() as any
  const seriesData: any[] = opt?.series?.[0]?.data || []
  return seriesData.findIndex(d => d?.id === id)
}

// T5: 统一高亮控制（hover 状态）
const setHoverFocus = (nodeId: string | null) => {
  if (!chartInstance) return
  // console.log('[HOVER] set', nodeId ?? 'null')
  
  if (nodeId === null) {
    // 强制 downplay 全局，确保无残留
    chartInstance.dispatchAction({ type: 'downplay', seriesIndex: 0 })
    return
  }

  const idx = getDataIndexById(nodeId)
  if (idx >= 0) {
    chartInstance.dispatchAction({ type: 'highlight', seriesIndex: 0, dataIndex: idx })
  }
}

// T5: pinned（如有点击固定高亮需求，可复用）
const setPinnedFocus = (nodeId: string | null) => {
  console.log('[PIN] set', nodeId ?? 'null')
}

// const showActivityDetail = (activity: any) => {
//   selectedActivity.value = activity
//   detailDrawerVisible.value = true
// }

const truncateText = (text: string, maxLength: number = 6): string => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

// T1+T2+T3: 局部展开节点布局（扇形+去重叠）
const layoutExpandedNodes = (
  hostX: number, 
  hostY: number, 
  expandNodes: Array<{id: string, name: string, category: string}>,
  allNodes: Array<{id: string, x: number, y: number, category: string}>,
  allEdges: Array<{source: string, target: string}>
): Array<{id: string, x: number, y: number}> => {
  if (expandNodes.length === 0) return []
  
  // T1: 确定性排序
  const sorted = expandNodes.slice().sort((a, b) => a.id.localeCompare(b.id))
  
  // T2: 碰撞检测函数
  const getCollisionRect = (x: number, y: number, category: string) => {
    const padding = 80  // 增大 padding，确保标签不重叠
    
    // Activity 节点标签在底部，需要考虑标签区域
    if (category === 'Activity') {
      const r = 25
      const fontSize = 12
      const lineHeight = fontSize * 1.2
      const labelW = 100
      const labelMargin = 6
      const x1 = Math.min(x - r, x - labelW / 2) - padding
      const y1 = y - r - padding
      const x2 = Math.max(x + r, x + labelW / 2) + padding
      const y2 = y + r + labelMargin + lineHeight + padding
      return { x1, y1, x2, y2 }
    } else {
      // Resource/Personnel 节点标签在右侧，需要考虑标签向右延伸
      const r = 17.5
      const labelW = 80
      const labelDistance = 10
      const labelHeight = 12  // lineHeight
      // 右侧标签需要更大的右侧padding
      const x1 = x - r - padding
      const y1 = y - Math.max(r, labelHeight / 2) - padding
      const x2 = x + r + labelDistance + labelW + padding * 0.5  // 右侧适当缩小padding避免过度保守
      const y2 = y + Math.max(r, labelHeight / 2) + padding
      return { x1, y1, x2, y2 }
    }
  }
  
  const rectsOverlap = (r1: any, r2: any) => !(r1.x2 <= r2.x1 || r2.x2 <= r1.x1 || r1.y2 <= r2.y1 || r2.y2 <= r1.y1)
  
  // 点到线段的最短距离
  const pointToSegmentDistance = (px: number, py: number, x1: number, y1: number, x2: number, y2: number) => {
    const dx = x2 - x1
    const dy = y2 - y1
    const len2 = dx * dx + dy * dy
    if (len2 === 0) return Math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
    
    const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / len2))
    const projX = x1 + t * dx
    const projY = y1 + t * dy
    return Math.sqrt((px - projX) ** 2 + (py - projY) ** 2)
  }
  
  // 矩形与线段相交检测（考虑 clearance 距离）
  const rectIntersectsEdge = (rect: any, x1: number, y1: number, x2: number, y2: number, clearance: number = 15) => {
    // 检查矩形中心点到线段的距离
    const cx = (rect.x1 + rect.x2) / 2
    const cy = (rect.y1 + rect.y2) / 2
    const dist = pointToSegmentDistance(cx, cy, x1, y1, x2, y2)
    
    // 矩形半对角线长度
    const halfDiag = Math.sqrt(
      ((rect.x2 - rect.x1) / 2) ** 2 + ((rect.y2 - rect.y1) / 2) ** 2
    )
    
    return dist < halfDiag + clearance
  }
  
  // T3: 智能采样布局（Sampling Scoring）
  // 1. 分析边方向，确定首选扇区
  let preferredAngleStart = 210 * Math.PI / 180
  let preferredAngleEnd = 330 * Math.PI / 180
  
  const hostEdges = allEdges.filter(e => 
    allNodes.find(n => n.id === e.source)?.id === allNodes.find(n => Math.abs(n.x - hostX) < 5 && Math.abs(n.y - hostY) < 5)?.id ||
    allNodes.find(n => n.id === e.target)?.id === allNodes.find(n => Math.abs(n.x - hostX) < 5 && Math.abs(n.y - hostY) < 5)?.id
  )
  
  let hasRightEdge = false
  let hasLeftEdge = false
  
  for (const edge of hostEdges) {
    const sourceNode = allNodes.find(n => n.id === edge.source)
    const targetNode = allNodes.find(n => n.id === edge.target)
    if (sourceNode && targetNode) {
      if (Math.abs(sourceNode.x - hostX) < 5 && Math.abs(sourceNode.y - hostY) < 5) {
        if (targetNode.x > hostX) hasRightEdge = true
        else if (targetNode.x < hostX) hasLeftEdge = true
      } else if (Math.abs(targetNode.x - hostX) < 5 && Math.abs(targetNode.y - hostY) < 5) {
        if (sourceNode.x > hostX) hasRightEdge = true
        else if (sourceNode.x < hostX) hasLeftEdge = true
      }
    }
  }
  
  if (hasRightEdge && !hasLeftEdge) {
    preferredAngleStart = 150 * Math.PI / 180
    preferredAngleEnd = 270 * Math.PI / 180
  } else if (hasLeftEdge && !hasRightEdge) {
    preferredAngleStart = 270 * Math.PI / 180
    preferredAngleEnd = 390 * Math.PI / 180
  }
  
  // 2. 准备碰撞检测集合（所有节点 + 边）
  const obstacles = allNodes
  const hostRect = getCollisionRect(hostX, hostY, 'Activity')
  
  const finalPositions: Array<{id: string, x: number, y: number, category: string}> = []
  
  // 3. 为每个新节点寻找最佳位置
  sorted.forEach(node => {
    let bestPos = { x: hostX, y: hostY + 100, score: -Infinity }
    let foundValid = false
    
    // 采样参数：考虑资源节点标签在右侧占用空间，从更大半径开始
    const radii = [350, 400, 450, 500, 550, 600, 650, 700]
    const angleStep = 15 * Math.PI / 180
    
    for (const R of radii) {
      // 优化：如果已找到很好的位置，且当前半径远大于该位置（分数差距大），停止搜索
      if (foundValid && -R < bestPos.score - 200) break 
      
      for (let angle = 0; angle < 360 * Math.PI / 180; angle += angleStep) {
        const x = hostX + R * Math.cos(angle)
        const y = hostY + R * Math.sin(angle)
        
        // 碰撞检测
        const rect = getCollisionRect(x, y, node.category)
        let collision = false
        
        // 检查宿主
        if (rectsOverlap(rect, hostRect)) collision = true
        
        // 检查现有障碍物
        if (!collision) {
          for (const obs of obstacles) {
            const obsRect = getCollisionRect(obs.x, obs.y, obs.category)
            if (rectsOverlap(rect, obsRect)) {
              collision = true
              break
            }
          }
        }
        
        // 检查已放置的新节点
        if (!collision) {
          for (const placed of finalPositions) {
            const placedRect = getCollisionRect(placed.x, placed.y, placed.category)
            if (rectsOverlap(rect, placedRect)) {
              collision = true
              break
            }
          }
        }
        
        // 检查边
        if (!collision) {
          for (const edge of allEdges) {
            const sourceNode = allNodes.find(n => n.id === edge.source)
            const targetNode = allNodes.find(n => n.id === edge.target)
            if (sourceNode && targetNode) {
              if (rectIntersectsEdge(rect, sourceNode.x, sourceNode.y, targetNode.x, targetNode.y, 15)) {
                collision = true
                break
              }
            }
          }
        }
        
        if (!collision) {
          // 强制最小距离检查（参考活动节点间距~440px，设为300px）
          const distToHost = Math.sqrt((x - hostX) ** 2 + (y - hostY) ** 2)
          if (distToHost < 300) {
            continue // 跳过太近的位置
          }
          
          // 评分系统
          let score = -R // 距离越小越好（基础分）
          
          // 惩罚x坐标过于接近母节点的位置（避免垂直对齐造成视觉拥挤）
          const xDist = Math.abs(x - hostX)
          if (xDist < 150) {
            score -= 250 // 大惩罚：避免x轴接近
          } else if (xDist < 250) {
            score -= 100 // 中惩罚
          }
          
          // 角度偏好奖励
          let normalizedAngle = angle
          while (normalizedAngle < preferredAngleStart) normalizedAngle += 2 * Math.PI
          while (normalizedAngle > preferredAngleEnd + 2 * Math.PI) normalizedAngle -= 2 * Math.PI
          
          if (normalizedAngle >= preferredAngleStart && normalizedAngle <= preferredAngleEnd) {
            score += 200 // 优先扇区奖励
          } else {
            // 距离优先扇区的惩罚
            const dist1 = Math.abs(normalizedAngle - preferredAngleStart)
            const dist2 = Math.abs(normalizedAngle - preferredAngleEnd)
            const minDist = Math.min(dist1, dist2)
            score -= minDist * 50
          }
          
          // 下方偏好（符合人类直觉）
          const sinAngle = Math.sin(angle)
          if (sinAngle > 0) score += 50 // y > hostY (下方)
          
          if (score > bestPos.score) {
            bestPos = { x, y, score }
            foundValid = true
          }
        }
      }
    }
    
    if (foundValid) {
      finalPositions.push({ id: node.id, x: bestPos.x, y: bestPos.y, category: node.category })
    } else {
      // 兜底：如果没有合法位置，尝试放在默认位置
      finalPositions.push({ id: node.id, x: hostX + 100, y: hostY + 100, category: node.category })
    }
  })
  
  // 网格吸附
  finalPositions.forEach(node => {
    node.x = Math.round(node.x / 20) * 20
    node.y = Math.round(node.y / 20) * 20
  })
  
  return finalPositions
}

// DAG 分层布局计算
const computeDagreLayout = (nodes: any[], edges: any[]) => {
  const g = new dagre.graphlib.Graph()
  
  g.setGraph({
    rankdir: 'LR',
    ranksep: 280,
    nodesep: 140,
    edgesep: 30,
    marginx: 50,
    marginy: 50,
    ranker: 'longest-path'
  })
  
  g.setDefaultEdgeLabel(() => ({}))
  
  const nodeMetadata = new Map<string, any>()
  nodes.forEach(node => {
    const labelWidth = Math.max(80, (node.name?.length || 6) * 14 + 40)
    const labelHeight = 70
    
    g.setNode(node.id, {
      label: node.name,
      width: labelWidth,
      height: labelHeight
    })
    nodeMetadata.set(node.id, { ...node, width: labelWidth, height: labelHeight })
  })
  
  const edgeList: Array<{source: string, target: string}> = []
  const edgeSet = new Set<string>()
  edges.forEach(edge => {
    const edgeKey = `${edge.source}-${edge.target}`
    if (!edgeSet.has(edgeKey)) {
      edgeSet.add(edgeKey)
      edgeList.push({ source: edge.source, target: edge.target })
      g.setEdge(edge.source, edge.target)
    }
  })
  
  dagre.layout(g)
  
  const nodeRanks = new Map<string, number>()
  g.nodes().forEach(nodeId => {
    const node = g.node(nodeId) as any
    nodeRanks.set(nodeId, node.rank || 0)
  })
  
  const virtualNodes: Array<{id: string, rank: number}> = []
  const newEdges: Array<{source: string, target: string}> = []
  
  edgeList.forEach(edge => {
    const srcRank = nodeRanks.get(edge.source) || 0
    const tgtRank = nodeRanks.get(edge.target) || 0
    const rankDiff = tgtRank - srcRank
    
    if (rankDiff > 1) {
      let prevNode = edge.source
      for (let r = srcRank + 1; r < tgtRank; r++) {
        const vNodeId = `__v_${edge.source}_${edge.target}_${r}`
        virtualNodes.push({ id: vNodeId, rank: r })
        
        if (!g.hasNode(vNodeId)) {
          g.setNode(vNodeId, {
            label: '',
            width: 1,
            height: 1
          })
          nodeMetadata.set(vNodeId, { id: vNodeId, isVirtual: true })
        }
        
        newEdges.push({ source: prevNode, target: vNodeId })
        prevNode = vNodeId
      }
      newEdges.push({ source: prevNode, target: edge.target })
    } else {
      newEdges.push(edge)
    }
  })
  
  const g2 = new dagre.graphlib.Graph()
  g2.setGraph({
    rankdir: 'LR',
    ranksep: 280,
    nodesep: 140,
    edgesep: 30,
    marginx: 50,
    marginy: 50,
    ranker: 'longest-path'
  })
  g2.setDefaultEdgeLabel(() => ({}))
  
  g.nodes().forEach(nodeId => {
    const node = g.node(nodeId)
    g2.setNode(nodeId, node)
  })
  
  newEdges.forEach(edge => {
    g2.setEdge(edge.source, edge.target)
  })
  
  dagre.layout(g2)
  
  // 主干+泳道后处理
  const nodeLaneInfo = new Map<string, {processId: string, isBackbone: boolean, laneIndex: number, sign: number, y0: number}>()
  
  const postProcessBackboneLanes = () => {
    const allNodeIds = g2.nodes()
    const realNodes = allNodeIds.filter(id => !nodeMetadata.get(id)?.isVirtual)
    
    // T1: 按流程分组（从 nodeMetadata 获取 process_id）
    const processList = extractProcessSubgraphs(realNodes)
    
    const debugMode = (window as any).__debugBackboneLayout
    
    processList.forEach(({ processId, nodeIds, internalEdges }) => {
      if (nodeIds.length === 0) return
      
      // T2: 找最长路径作为主干
      const backbone = findLongestPathDAG(nodeIds, internalEdges)
      
      if (backbone.length === 0) return
      
      if (debugMode) {
        console.log(`[Process ${processId}] Backbone (${backbone.length} nodes):`, 
          backbone.map(id => ({ id, name: nodeMetadata.get(id)?.name })))
      }
      
      // T3: 分配泳道
      const laneInfo = assignLanes(nodeIds, internalEdges, backbone)
      
      // T4: 应用坐标
      const backboneYs = backbone.map(id => g2.node(id).y)
      backboneYs.sort((a, b) => a - b)
      const y0 = backboneYs[Math.floor(backboneYs.length / 2)]
      
      const laneGap = 200
      
      // 先设置主干和支路坐标，并保存 lane 信息
      nodeIds.forEach(nodeId => {
        const node = g2.node(nodeId)
        const info = laneInfo.get(nodeId)
        if (!info) return
        
        if (info.isBackbone) {
          node.y = y0
        } else {
          node.y = y0 + info.sign * info.laneIndex * laneGap
        }
        
        // 保存到全局 lane 信息
        nodeLaneInfo.set(nodeId, {
          processId,
          isBackbone: info.isBackbone,
          laneIndex: info.laneIndex,
          sign: info.sign,
          y0
        })
      })
      
      // 按列分组，防重叠
      const rankGroups = new Map<number, Array<{id: string, lane: number, topo: number}>>()
      nodeIds.forEach(nodeId => {
        const node = g2.node(nodeId) as any
        const info = laneInfo.get(nodeId)
        if (!info) return
        
        const rank = node.rank || 0
        if (!rankGroups.has(rank)) rankGroups.set(rank, [])
        rankGroups.get(rank)!.push({ 
          id: nodeId, 
          lane: info.isBackbone ? 0 : info.sign * info.laneIndex, 
          topo: info.topoIndex 
        })
      })
      
      // 列内排序+防重叠
      rankGroups.forEach(items => {
        items.sort((a, b) => {
          if (a.lane !== b.lane) return a.lane - b.lane
          if (a.topo !== b.topo) return a.topo - b.topo
          return a.id.localeCompare(b.id)
        })
        
        // 超大间距确保label不重叠：节点50 + label可能60 + 安全边距140
        const minSpacing = 250
        const grouped = new Map<number, string[]>()
        items.forEach(item => {
          if (!grouped.has(item.lane)) grouped.set(item.lane, [])
          grouped.get(item.lane)!.push(item.id)
        })
        
        grouped.forEach((ids, lane) => {
          if (ids.length <= 1) return
          
          const laneY = lane === 0 ? y0 : y0 + Math.sign(lane) * Math.abs(lane) * laneGap
          ids.forEach((id, idx) => {
            const offset = (idx - (ids.length - 1) / 2) * minSpacing
            g2.node(id).y = laneY + offset
          })
        })
      })
      
      if (debugMode) {
        console.log(`[Process ${processId}] Node positions:`)
        nodeIds.forEach(id => {
          const node = g2.node(id)
          const info = laneInfo.get(id)
          if (info) {
            console.log(`  ${id} (${nodeMetadata.get(id)?.name}): x=${Math.round(node.x)}, y=${Math.round(node.y)}, lane=${info.laneIndex}, sign=${info.sign > 0 ? '+' : '-'}, topo=${info.topoIndex}, backbone=${info.isBackbone}`)
          }
        })
      }
    })
  }
  
  // T1: 提取流程子图
  const extractProcessSubgraphs = (realNodes: string[]) => {
    const processMap = new Map<string, Set<string>>()
    
    realNodes.forEach(nodeId => {
      const meta = nodeMetadata.get(nodeId)
      const pid = meta?.process_id || 'default'
      if (!processMap.has(pid)) processMap.set(pid, new Set())
      processMap.get(pid)!.add(nodeId)
    })
    
    return Array.from(processMap.entries()).map(([processId, nodeSet]) => {
      const nodeIds = Array.from(nodeSet)
      const internalEdges: Array<{source: string, target: string}> = []
      
      newEdges.forEach(edge => {
        if (nodeSet.has(edge.source) && nodeSet.has(edge.target)) {
          internalEdges.push(edge)
        }
      })
      
      return { processId, nodeIds, internalEdges }
    })
  }
  
  // T2: 最长路径（拓扑DP）
  const findLongestPathDAG = (nodeIds: string[], edges: Array<{source: string, target: string}>) => {
    const nodeSet = new Set(nodeIds)
    const inDegree = new Map<string, number>()
    const outEdges = new Map<string, string[]>()
    const dist = new Map<string, number>()
    const prev = new Map<string, string | null>()
    
    nodeIds.forEach(id => {
      inDegree.set(id, 0)
      outEdges.set(id, [])
      dist.set(id, 0)
      prev.set(id, null)
    })
    
    edges.forEach(edge => {
      if (!nodeSet.has(edge.source) || !nodeSet.has(edge.target)) return
      inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1)
      outEdges.get(edge.source)!.push(edge.target)
    })
    
    const queue: string[] = []
    nodeIds.forEach(id => {
      if (inDegree.get(id) === 0) queue.push(id)
    })
    
    while (queue.length > 0) {
      const u = queue.shift()!
      const uDist = dist.get(u) || 0
      
      outEdges.get(u)!.forEach(v => {
        const newDist = uDist + 1
        if (newDist > (dist.get(v) || 0)) {
          dist.set(v, newDist)
          prev.set(v, u)
        }
        
        inDegree.set(v, inDegree.get(v)! - 1)
        if (inDegree.get(v) === 0) queue.push(v)
      })
    }
    
    let maxNode = nodeIds[0]
    let maxDist = dist.get(maxNode) || 0
    nodeIds.forEach(id => {
      const d = dist.get(id) || 0
      if (d > maxDist) {
        maxDist = d
        maxNode = id
      }
    })
    
    const path: string[] = []
    let cur: string | null = maxNode
    while (cur !== null) {
      path.unshift(cur)
      cur = prev.get(cur) || null
    }
    
    return path
  }
  
  // T3: 分配泳道
  const assignLanes = (
    nodeIds: string[], 
    edges: Array<{source: string, target: string}>, 
    backbone: string[]
  ) => {
    const backboneSet = new Set(backbone)
    const result = new Map<string, {isBackbone: boolean, laneIndex: number, sign: number, topoIndex: number}>()
    
    // 计算拓扑序
    const topoIndex = computeTopoIndex(nodeIds, edges)
    
    // 主干节点
    backbone.forEach((id) => {
      result.set(id, { isBackbone: true, laneIndex: 0, sign: 1, topoIndex: topoIndex.get(id) || 0 })
    })
    
    // BFS计算到主干的最短距离
    const distance = new Map<string, number>()
    const parent = new Map<string, string>()
    const queue: string[] = [...backbone]
    
    backbone.forEach(id => distance.set(id, 0))
    
    const adjList = new Map<string, string[]>()
    nodeIds.forEach(id => adjList.set(id, []))
    edges.forEach(edge => {
      adjList.get(edge.source)!.push(edge.target)
      adjList.get(edge.target)!.push(edge.source)
    })
    
    while (queue.length > 0) {
      const u = queue.shift()!
      const d = distance.get(u) || 0
      
      adjList.get(u)!.forEach(v => {
        if (!distance.has(v)) {
          distance.set(v, d + 1)
          parent.set(v, u)
          queue.push(v)
        }
      })
    }
    
    // 支路节点分配泳道
    nodeIds.forEach(id => {
      if (backboneSet.has(id)) return
      
      const d = distance.get(id) || 1
      const sign = determineSign(id, parent, backbone, nodeMetadata)
      
      result.set(id, { 
        isBackbone: false, 
        laneIndex: d, 
        sign, 
        topoIndex: topoIndex.get(id) || 0 
      })
    })
    
    return result
  }
  
  // 计算拓扑序（用于稳定排序）
  const computeTopoIndex = (nodeIds: string[], edges: Array<{source: string, target: string}>) => {
    const nodeSet = new Set(nodeIds)
    const inDegree = new Map<string, number>()
    const outEdges = new Map<string, string[]>()
    
    nodeIds.forEach(id => {
      inDegree.set(id, 0)
      outEdges.set(id, [])
    })
    
    edges.forEach(edge => {
      if (!nodeSet.has(edge.source) || !nodeSet.has(edge.target)) return
      inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1)
      outEdges.get(edge.source)!.push(edge.target)
    })
    
    const queue: string[] = []
    nodeIds.forEach(id => {
      if (inDegree.get(id) === 0) queue.push(id)
    })
    queue.sort()
    
    const topoIndex = new Map<string, number>()
    let idx = 0
    
    while (queue.length > 0) {
      queue.sort()
      const u = queue.shift()!
      topoIndex.set(u, idx++)
      
      const neighbors = outEdges.get(u)!
      neighbors.forEach(v => {
        inDegree.set(v, inDegree.get(v)! - 1)
        if (inDegree.get(v) === 0) queue.push(v)
      })
    }
    
    return topoIndex
  }
  
  // 确定性决定上下方向
  const determineSign = (
    nodeId: string, 
    parent: Map<string, string>,
    backbone: string[],
    metadata: Map<string, any>
  ) => {
    const meta = metadata.get(nodeId)
    const name = meta?.name || ''
    
    // 语义规则
    if (/检验|采集|检测|报告|质检/.test(name)) return 1
    if (/订单|计划|排产|调度/.test(name)) return -1
    
    // 找到支路根节点（从主干分叉的第一个节点）
    let cur = nodeId
    let root = cur
    while (parent.has(cur)) {
      const p = parent.get(cur)!
      if (backbone.includes(p)) {
        root = cur
        break
      }
      cur = p
    }
    
    // 根节点在主干中的索引
    let rootIndex = 0
    for (let i = 0; i < backbone.length; i++) {
      const bbNode = backbone[i]
      if (parent.get(root) === bbNode) {
        rootIndex = i
        break
      }
    }
    
    // 偶数下方，奇数上方
    return rootIndex % 2 === 0 ? 1 : -1
  }
  
  postProcessBackboneLanes()
  
  // ============ Label-aware 去重叠后处理 ============
  
  // T1: 计算碰撞包围盒（含 label）
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
    const padding = 25  // 增大 padding 确保标签不遮挡其他节点
    
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
  
  // 检查两个矩形是否重叠
  const rectsOverlap = (r1: any, r2: any) => {
    return !(r1.x2 <= r2.x1 || r2.x2 <= r1.x1 || r1.y2 <= r2.y1 || r2.y2 <= r1.y1)
  }
  
  // 计算重叠数量
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
  
  // T2: 局部增大 laneGap（优先策略）
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
      // 超大间距确保label不重叠
      const minLaneSeparation = 250
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
  
  expandLaneGapsPerProcess()
  
  // 更新虚拟节点位置（在去重叠过程中跟随）
  const updateVirtualNodes = () => {
    const allNodeIds = g2.nodes()
    allNodeIds.forEach(nodeId => {
      const meta = nodeMetadata.get(nodeId)
      if (!meta?.isVirtual) return
      
      const inEdges = g2.inEdges(nodeId) || []
      const outEdges = g2.outEdges(nodeId) || []
      const allEdges = [...inEdges, ...outEdges]
      const neighbors = allEdges.map((e: any) => e.v === nodeId ? e.w : e.v)
        .filter((n: string) => !nodeMetadata.get(n)?.isVirtual)
      
      if (neighbors.length > 0) {
        const avgY = neighbors.reduce((sum: number, n: string) => sum + g2.node(n).y, 0) / neighbors.length
        g2.node(nodeId).y = avgY
      }
    })
  }
  
  updateVirtualNodes()
  
  // T3: 同 lane 内小幅 jitter（兜底）
  const smallJitterInLaneIfNeeded = () => {
    let overlaps = countOverlaps()
    if (overlaps === 0) return
    
    const realNodes = g2.nodes().filter(id => !nodeMetadata.get(id)?.isVirtual)
    // 大幅增大jitter幅度以处理label重叠
    const jitterMax = 150
    
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
  
  smallJitterInLaneIfNeeded()
  updateVirtualNodes()
  
  // T4: 局部 ranksep 扩展（X 方向兜底）
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
        // X 方向推开（D策略：移除上限限制）
        const rightNode = node1.x > node2.x ? node1 : node2
        rightNode.x += overlapW + 100
      }
    })
  }
  
  expandRankSepsIfNeeded()
  updateVirtualNodes()
  
  // 强制去重叠：确保同列节点的垂直间距足够大
  const forceMinimumVerticalSpacing = () => {
    const realNodes = g2.nodes().filter(id => !nodeMetadata.get(id)?.isVirtual)
    
    // 按x坐标分组（容差50px）
    const xGroups = new Map<number, string[]>()
    realNodes.forEach(id => {
      const node = g2.node(id)
      const xRounded = Math.round(node.x / 50) * 50
      if (!xGroups.has(xRounded)) xGroups.set(xRounded, [])
      xGroups.get(xRounded)!.push(id)
    })
    
    xGroups.forEach(nodeIds => {
      if (nodeIds.length <= 1) return
      
      // 按y排序
      nodeIds.sort((a, b) => g2.node(a).y - g2.node(b).y)
      
      // 强制最小间距：必须足够大以防止label重叠
      const minVerticalGap = 250
      
      for (let i = 1; i < nodeIds.length; i++) {
        const prevNode = g2.node(nodeIds[i - 1])
        const currNode = g2.node(nodeIds[i])
        const gap = currNode.y - prevNode.y
        
        if (gap < minVerticalGap) {
          const needPush = minVerticalGap - gap
          // 向下推当前节点及之后所有节点
          for (let j = i; j < nodeIds.length; j++) {
            g2.node(nodeIds[j]).y += needPush
          }
        }
      }
    })
  }
  
  forceMinimumVerticalSpacing()
  updateVirtualNodes()
  
  const snapGraphToGrid = () => {
    g2.nodes().forEach(nodeId => {
      const node = g2.node(nodeId)
      node.x = Math.round(node.x / 20) * 20
      node.y = Math.round(node.y / 20) * 20
    })
  }
  
  snapGraphToGrid()
  
  const getProcessId = (meta: any) => meta?.process_id ?? meta?.processId ?? meta?.process ?? 'default'
  const getDomain = (meta: any) => meta?.domain ?? meta?.domain_name ?? meta?.domainName ?? 'default'
  
  const computeBlockBoundingBoxes = () => {
    const blocks = new Map<string, { nodes: string[], bbox: { x1: number, y1: number, x2: number, y2: number } }>()
    const realNodes = g2.nodes().filter(id => !nodeMetadata.get(id)?.isVirtual)
    realNodes.forEach(id => {
      const meta = nodeMetadata.get(id) || {}
      const key = `${getDomain(meta)}:${getProcessId(meta)}`
      const rect = computeCollisionRect(id)
      if (!blocks.has(key)) {
        blocks.set(key, { nodes: [], bbox: { ...rect } })
      }
      const entry = blocks.get(key)!
      entry.nodes.push(id)
      entry.bbox.x1 = Math.min(entry.bbox.x1, rect.x1)
      entry.bbox.y1 = Math.min(entry.bbox.y1, rect.y1)
      entry.bbox.x2 = Math.max(entry.bbox.x2, rect.x2)
      entry.bbox.y2 = Math.max(entry.bbox.y2, rect.y2)
    })
    return blocks
  }
  
  const resolveBlockOverlaps = () => {
    let iteration = 0
    let prevOverlapCount = Infinity
    const maxIteration = 20
    while (iteration < maxIteration) {
      iteration++
      const blocks = computeBlockBoundingBoxes()
      const keys = Array.from(blocks.keys()).sort()
      const overlaps: Array<{ a: string, b: string, overlapY: number }> = []
      for (let i = 0; i < keys.length; i++) {
        for (let j = i + 1; j < keys.length; j++) {
          const boxA = blocks.get(keys[i])!.bbox
          const boxB = blocks.get(keys[j])!.bbox
          if (rectsOverlap(boxA, boxB)) {
            const overlapY = Math.min(boxA.y2, boxB.y2) - Math.max(boxA.y1, boxB.y1)
            overlaps.push({ a: keys[i], b: keys[j], overlapY })
          }
        }
      }
      if (overlaps.length === 0) break
      if (overlaps.length >= prevOverlapCount) {
        console.warn('blockShift_stalled', overlaps.length)
        break
      }
      prevOverlapCount = overlaps.length
      const target = overlaps[0]
      const moverKey = target.b
      const mover = blocks.get(moverKey)!
      const anchor = blocks.get(target.a)!
      const anchorCenter = (anchor.bbox.y1 + anchor.bbox.y2) / 2
      const moverCenter = (mover.bbox.y1 + mover.bbox.y2) / 2
      const direction = moverCenter >= anchorCenter ? 1 : -1
      const push = Math.ceil((Math.max(target.overlapY, 0) + 20) / 20) * 20
      mover.nodes.forEach(id => {
        const node = g2.node(id)
        node.y += direction * push
      })
    }
  }
  
  resolveBlockOverlaps()
  updateVirtualNodes()
  
  const jitterWithinBlockIfNeeded = () => {
    let overlaps = countOverlaps()
    let guard = 20
    while (overlaps > 0 && guard > 0) {
      const realNodes = g2.nodes().filter(id => !nodeMetadata.get(id)?.isVirtual)
      let moved = false
      for (let i = 0; i < realNodes.length - 1; i++) {
        for (let j = i + 1; j < realNodes.length; j++) {
          const rect1 = computeCollisionRect(realNodes[i])
          const rect2 = computeCollisionRect(realNodes[j])
          if (rectsOverlap(rect1, rect2)) {
            const meta1 = nodeMetadata.get(realNodes[i]) || {}
            const meta2 = nodeMetadata.get(realNodes[j]) || {}
            const block1 = `${getDomain(meta1)}:${getProcessId(meta1)}`
            const block2 = `${getDomain(meta2)}:${getProcessId(meta2)}`
            if (block1 !== block2) {
              resolveBlockOverlaps()
              updateVirtualNodes()
              moved = true
              break
            } else {
              const overlapY = Math.min(rect1.y2, rect2.y2) - Math.max(rect1.y1, rect2.y1)
              const shift = Math.min(Math.ceil((overlapY + 4) / 20) * 20, 20)
              g2.node(realNodes[j]).y += shift
              moved = true
            }
          }
        }
        if (moved) break
      }
      guard--
      updateVirtualNodes()
      overlaps = countOverlaps()
    }
  }
  
  jitterWithinBlockIfNeeded()
  snapGraphToGrid()
  updateVirtualNodes()
  
  const overlapCountAfter = countOverlaps()
  
  if (debugMode || overlapCountAfter > 0) {
    console.log(`[Overlap Detection] After: ${overlapCountAfter} (before: ${overlapCountBefore})`)
    if (overlapCountAfter === 0) {
      console.log('✅ No overlaps detected!')
    } else {
      console.warn(`⚠️ Still have ${overlapCountAfter} overlaps`)
    }
  }
  
  // ============ 去重叠后处理结束 ============
  
  // ============ 简化布局策略：主链冻结 + 支链锚点化 ============
  
  // B2: 主链冻结 - 收集所有主链节点
  const backboneNodes = new Set<string>()
  nodeLaneInfo.forEach((info, nodeId) => {
    if (info.isBackbone) {
      backboneNodes.add(nodeId)
    }
  })
  
  if (debugMode) {
    console.log(`[FREEZE_BACKBONE] Froze ${backboneNodes.size} backbone nodes`)
  }
  
  // 辅助：计算节点+label 完整包围盒
  const getNodeBBox = (nodeId: string) => {
    const node = g2.node(nodeId)
    const meta = nodeMetadata.get(nodeId)
    
    if (meta?.isVirtual) {
      return { x1: node.x, y1: node.y, x2: node.x, y2: node.y }
    }
    
    const r = 25
    const labelW = 100
    const labelH = 14
    const labelMargin = 6
    const padding = 10
    
    const nodeX1 = node.x - r - padding
    const nodeY1 = node.y - r - padding
    const nodeX2 = node.x + r + padding
    const nodeY2 = node.y + r + padding
    
    const labelX1 = node.x - labelW / 2 - padding
    const labelY1 = node.y + r + labelMargin
    const labelX2 = node.x + labelW / 2 + padding
    const labelY2 = labelY1 + labelH + padding
    
    return {
      x1: Math.min(nodeX1, labelX1),
      y1: Math.min(nodeY1, labelY1),
      x2: Math.max(nodeX2, labelX2),
      y2: Math.max(nodeY2, labelY2)
    }
  }
  
  const bboxOverlap = (b1: any, b2: any) => {
    return !(b1.x2 <= b2.x1 || b2.x2 <= b1.x1 || b1.y2 <= b2.y1 || b2.y2 <= b1.y1)
  }
  
  // B3: 支链锚点化摆放
  const layoutBranchesNearAnchors = () => {
    const realNodes = g2.nodes().filter(id => !nodeMetadata.get(id)?.isVirtual)
    const branchNodes = realNodes.filter(id => !backboneNodes.has(id))
    
    // 为每个锚点维护已占用的扇区
    const anchorOccupancy = new Map<string, Array<{angle: number, ring: number}>>()
    
    branchNodes.forEach(branchId => {
      // 找到该支链节点连接的主链节点（锚点）
      const anchors: string[] = []
      newEdges.forEach(e => {
        if (e.source === branchId && backboneNodes.has(e.target)) {
          anchors.push(e.target)
        }
        if (e.target === branchId && backboneNodes.has(e.source)) {
          anchors.push(e.source)
        }
      })
      
      if (anchors.length === 0) return
      
      // 选择第一个锚点（如果有多个，选最近的）
      const anchorId = anchors[0]
      const anchorNode = g2.node(anchorId)
      
      if (!anchorOccupancy.has(anchorId)) {
        anchorOccupancy.set(anchorId, [])
      }
      const occupied = anchorOccupancy.get(anchorId)!
      
      // 确定左右侧：检测锚点左右哪边更空
      const leftCount = realNodes.filter(id => {
        const n = g2.node(id)
        return n.x < anchorNode.x && Math.abs(n.y - anchorNode.y) < 500
      }).length
      
      const rightCount = realNodes.filter(id => {
        const n = g2.node(id)
        return n.x > anchorNode.x && Math.abs(n.y - anchorNode.y) < 500
      }).length
      
      const preferLeft = leftCount < rightCount
      
      // 选择扇区和层级
      let bestAngle = preferLeft ? 180 : 0
      let bestRing = 1
      
      // 避开已占用扇区
      const angles = preferLeft ? [180, 210, 150, 240, 120] : [0, 30, 330, 60, 300]
      for (const angle of angles) {
        let ringFound = false
        for (let ring = 1; ring <= 3; ring++) {
          const conflict = occupied.some(occ => 
            Math.abs(occ.angle - angle) < 45 && occ.ring === ring
          )
          if (!conflict) {
            bestAngle = angle
            bestRing = ring
            ringFound = true
            break
          }
        }
        if (ringFound) break
      }
      
      occupied.push({ angle: bestAngle, ring: bestRing })
      
      // 计算位置
      const baseRadius = 300
      const radius = baseRadius + (bestRing - 1) * 300
      const rad = (bestAngle * Math.PI) / 180
      const newX = anchorNode.x + radius * Math.cos(rad)
      const newY = anchorNode.y + radius * Math.sin(rad)
      
      g2.node(branchId).x = newX
      g2.node(branchId).y = newY
    })
    
    if (debugMode) {
      console.log(`[ANCHOR_LAYOUT] Placed ${branchNodes.length} branch nodes near anchors`)
    }
  }
  
  layoutBranchesNearAnchors()
  updateVirtualNodes()
  
  // B4: 局部去重叠（仅支链）
  const resolveOverlapsLocally = () => {
    const realNodes = g2.nodes().filter(id => !nodeMetadata.get(id)?.isVirtual)
    const branchNodes = realNodes.filter(id => !backboneNodes.has(id))
    
    let maxIter = 30
    let resolved = 0
    
    while (maxIter > 0) {
      maxIter--
      let moved = false
      
      for (const branchId of branchNodes) {
        const branchNode = g2.node(branchId)
        const branchBBox = getNodeBBox(branchId)
        
        // 检测范围：锚点附近 800px + 所有实节点
        const nearbyNodes = realNodes.filter(otherId => {
          if (otherId === branchId) return false
          const otherNode = g2.node(otherId)
          const dist = Math.sqrt(
            (otherNode.x - branchNode.x) ** 2 +
            (otherNode.y - branchNode.y) ** 2
          )
          return dist < 800
        })
        
        for (const otherId of nearbyNodes) {
          const otherBBox = getNodeBBox(otherId)
          
          if (bboxOverlap(branchBBox, otherBBox)) {
            // 优先纵向分离
            const overlapY = Math.min(branchBBox.y2, otherBBox.y2) - Math.max(branchBBox.y1, otherBBox.y1)
            const overlapX = Math.min(branchBBox.x2, otherBBox.x2) - Math.max(branchBBox.x1, otherBBox.x1)
            
            if (overlapY < overlapX || backboneNodes.has(otherId)) {
              // 纵向推开
              if (branchNode.y > g2.node(otherId).y) {
                branchNode.y += overlapY + 20
              } else {
                branchNode.y -= overlapY + 20
              }
            } else {
              // 横向错位（限制 ±100px）
              const shift = Math.min(overlapX + 20, 100)
              if (branchNode.x > g2.node(otherId).x) {
                branchNode.x += shift
              } else {
                branchNode.x -= shift
              }
            }
            
            moved = true
            resolved++
            break
          }
        }
        
        if (moved) break
      }
      
      if (!moved) break
    }
    
    if (debugMode && resolved > 0) {
      console.log(`[RESOLVE_OVERLAP] Resolved ${resolved} overlaps`)
    }
  }
  
  resolveOverlapsLocally()
  updateVirtualNodes()
  
  // 网格吸附
  g2.nodes().forEach(nodeId => {
    const node = g2.node(nodeId)
    node.x = Math.round(node.x / 20) * 20
    node.y = Math.round(node.y / 20) * 20
  })
  
  // 网格吸附后复检重叠
  const recheckOverlaps = () => {
    const realNodes = g2.nodes().filter(id => !nodeMetadata.get(id)?.isVirtual)
    let overlapCount = 0
    
    for (let i = 0; i < realNodes.length; i++) {
      for (let j = i + 1; j < realNodes.length; j++) {
        const b1 = getNodeBBox(realNodes[i])
        const b2 = getNodeBBox(realNodes[j])
        if (bboxOverlap(b1, b2)) {
          overlapCount++
        }
      }
    }
    
    return overlapCount
  }
  
  let postSnapOverlaps = recheckOverlaps()
  
  if (postSnapOverlaps > 0) {
    if (debugMode) {
      console.log(`[POST_SNAP] Found ${postSnapOverlaps} overlaps after grid snap, re-resolving...`)
    }
    
    // 二次分离（仅支链，小范围）
    const realNodes = g2.nodes().filter(id => !nodeMetadata.get(id)?.isVirtual)
    const branchNodes = realNodes.filter(id => !backboneNodes.has(id))
    
    let maxIter = 20
    while (maxIter > 0 && postSnapOverlaps > 0) {
      maxIter--
      let moved = false
      
      for (const branchId of branchNodes) {
        const branchBBox = getNodeBBox(branchId)
        
        for (const otherId of realNodes) {
          if (otherId === branchId) continue
          
          const otherBBox = getNodeBBox(otherId)
          if (bboxOverlap(branchBBox, otherBBox)) {
            const branchNode = g2.node(branchId)
            const otherNode = g2.node(otherId)
            
            // 小范围纵向分离
            if (branchNode.y > otherNode.y) {
              branchNode.y += 30
            } else {
              branchNode.y -= 30
            }
            
            moved = true
            break
          }
        }
        
        if (moved) break
      }
      
      if (!moved) break
      
      postSnapOverlaps = recheckOverlaps()
    }
    
    if (debugMode) {
      console.log(`[POST_SNAP] After re-resolve: ${postSnapOverlaps} overlaps remaining`)
    }
  }
  
  updateVirtualNodes()
  
  // ============ 布局策略结束 ============
  
  const nodePositions = new Map<string, { x: number, y: number, isVirtual?: boolean }>()
  let minX = Infinity, minY = Infinity
  
  g2.nodes().forEach(nodeId => {
    const node = g2.node(nodeId)
    const meta = nodeMetadata.get(nodeId)
    
    nodePositions.set(nodeId, { 
      x: node.x, 
      y: node.y, 
      isVirtual: meta?.isVirtual || false 
    })
    
    minX = Math.min(minX, node.x)
    minY = Math.min(minY, node.y)
  })
  
  const padding = 100
  nodePositions.forEach((pos) => {
    pos.x = pos.x - minX + padding
    pos.y = pos.y - minY + padding
  })
  
  return { nodePositions, virtualNodes: virtualNodes.map(v => v.id) }
}

const initChart = (options?: { preserveView?: boolean }) => {
  const preserveView = options?.preserveView ?? false
  if (!chartRef.value) return
  
  if (!props.data || !props.data.nodes || props.data.nodes.length === 0) {
    return
  }

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  const displayNodes: any[] = []
  const displayEdges: any[] = []

  const dataHash = JSON.stringify({
    nodeIds: props.data.nodes.map((n: any) => n.id).sort(),
    edgeIds: props.data.edges.map((e: any) => `${e.source}-${e.target}`).sort()
  })
  
  let layoutResult: { nodePositions: Map<string, any>, virtualNodes: string[] }
  if (dataHash !== cachedDataHash || !cachedNodePositions) {
    layoutResult = computeDagreLayout(props.data.nodes, props.data.edges)
    cachedNodePositions = layoutResult.nodePositions
    cachedVirtualNodes = layoutResult.virtualNodes
    cachedDataHash = dataHash
  } else {
    layoutResult = { nodePositions: cachedNodePositions, virtualNodes: cachedVirtualNodes }
  }
  
  const nodePositions = layoutResult.nodePositions
  const virtualNodeIds = new Set(layoutResult.virtualNodes)
  
  const nodeMap = new Map<string, any>()
  const activityNodes: any[] = []
  
  props.data.nodes.forEach(node => {
    if (!nodeMap.has(node.id)) {
      nodeMap.set(node.id, node)
      
      const pos = nodePositions.get(node.id)
      if (!pos) return
      
      const isHighlighted = !props.highlightActive || (props.highlightSet?.nodeIds.has(node.id) ?? false)
      const opacity = props.highlightActive && !isHighlighted ? 0.3 : 1
      
      activityNodes.push({
        id: node.id,
        name: truncateText(node.name),
        fullName: node.name,
        category: 'Activity',
        symbolSize: 50,
        symbol: 'circle',
        x: pos.x,
        y: pos.y,
        fixed: true,
        itemStyle: {
          color: getNodeColor(node.status),
          borderWidth: isHighlighted && props.highlightActive ? 3 : 2,
          borderColor: isHighlighted && props.highlightActive ? '#ff6b00' : '#fff',
          opacity: opacity
        },
        label: {
          show: true,
          fontSize: 12,
          fontWeight: isHighlighted && props.highlightActive ? 'bold' : 'normal',
          opacity: opacity,
          position: 'bottom',
          width: 100,
          overflow: 'truncate'
        },
        rawData: node
      })
    }
  })

  displayNodes.push(...activityNodes)
  
  virtualNodeIds.forEach(vNodeId => {
    const pos = nodePositions.get(vNodeId)
    if (pos) {
      displayNodes.push({
        id: vNodeId,
        name: '',
        category: 'Virtual',
        symbolSize: 1,
        symbol: 'circle',
        x: pos.x,
        y: pos.y,
        fixed: true,
        itemStyle: {
          color: 'transparent',
          opacity: 0
        },
        label: {
          show: false
        },
        silent: true
      })
    }
  })

  const edgeMap = new Map<string, any>()
  props.data.edges.forEach((edge, index) => {
    edgeMap.set(`${edge.source}-${edge.target}`, { ...edge, index })
  })
  
  const finalEdges: any[] = []
  
  const buildEdgesWithVirtual = (source: string, target: string, originalEdge: any) => {
    const srcPos = nodePositions.get(source)
    const tgtPos = nodePositions.get(target)
    
    if (!srcPos || !tgtPos) return
    
    const virtualPath: string[] = []
    
    virtualNodeIds.forEach(vNodeId => {
      if (vNodeId.includes(`__v_${originalEdge.source}_${originalEdge.target}_`)) {
        virtualPath.push(vNodeId)
      }
    })
    
    if (virtualPath.length === 0) {
      finalEdges.push({
        source,
        target,
        originalSource: originalEdge.source,
        originalTarget: originalEdge.target,
        edgeData: originalEdge
      })
    } else {
      virtualPath.sort((a, b) => {
        const aPos = nodePositions.get(a)!
        const bPos = nodePositions.get(b)!
        return aPos.x - bPos.x
      })
      
      const chain = [originalEdge.source, ...virtualPath, originalEdge.target]
      for (let i = 0; i < chain.length - 1; i++) {
        finalEdges.push({
          source: chain[i],
          target: chain[i + 1],
          originalSource: originalEdge.source,
          originalTarget: originalEdge.target,
          edgeData: originalEdge
        })
      }
    }
  }
  
  props.data.edges.forEach((edge) => {
    buildEdgesWithVirtual(edge.source, edge.target, edge)
  })
  
  const dependencyEdges = finalEdges.map((edge, index) => {
    const edgeKey = `${edge.originalSource}-${edge.originalTarget}-${edge.edgeData.index || index}`
    const isHighlighted = !props.highlightActive || (props.highlightSet?.edgeIds.has(edgeKey) ?? false)
    const opacity = props.highlightActive && !isHighlighted ? 0.2 : 1
    
    return {
      source: edge.source,
      target: edge.target,
      lineStyle: {
        color: isHighlighted && props.highlightActive ? '#ff6b00' : '#409EFF',
        type: 'solid',
        width: isHighlighted && props.highlightActive ? 3 : 2,
        curveness: 0,
        opacity: opacity
      },
      label: { show: false },
      edgeData: edge.edgeData
    }
  })

  displayEdges.push(...dependencyEdges)

  // 资源+人员节点：使用局部布局（T1+T2+T3）
  const resourceNodeMap = new Map<string, any>()
  const personnelNodeMap = new Map<string, any>()
  
  expandedActivities.value.forEach(activityId => {
    const activityNode = activityNodes.find(n => n.id === activityId)
    if (!activityNode) return
    
    const activityX = activityNode.x
    const activityY = activityNode.y
    
    // 收集该活动的资源+人员
    const toExpand: Array<{id: string, name: string, category: string, rawData: any}> = []
    
    if (props.data.resource_nodes) {
      props.data.resource_nodes
        .filter((rn: any) => rn.parent_activity === activityId && !resourceNodeMap.has(rn.id))
        .forEach((rn: any) => {
          toExpand.push({ id: rn.id, name: rn.name, category: 'Resource', rawData: rn })
          resourceNodeMap.set(rn.id, true)
        })
    }
    
    if (props.data.personnel_nodes) {
      props.data.personnel_nodes
        .filter((pn: any) => pn.parent_activity === activityId && !personnelNodeMap.has(pn.id))
        .forEach((pn: any) => {
          toExpand.push({ id: pn.id, name: pn.name, category: 'Personnel', rawData: pn })
          personnelNodeMap.set(pn.id, true)
        })
    }
    
    if (toExpand.length === 0) return
    
    // T1+T2+T3: 局部布局（包含边碰撞检测）
    const existingNodes = displayNodes.map(n => ({ id: n.id, x: n.x, y: n.y, category: n.category }))
    const allEdges = dependencyEdges.map(e => ({ source: e.source, target: e.target }))
    
    const positions = layoutExpandedNodes(activityX, activityY, toExpand, existingNodes, allEdges)
    
    // T4: 统计重叠（局部验证，含宿主）
    const localRects = [
      { id: activityId, rect: ((x: number, y: number) => {
        const r = 25, labelW = 100, fontSize = 12, lineHeight = fontSize * 1.2, labelMargin = 6, padding = 80
        return {
          x1: Math.min(x - r, x - labelW / 2) - padding,
          y1: y - r - padding,
          x2: Math.max(x + r, x + labelW / 2) + padding,
          y2: y + r + labelMargin + lineHeight + padding
        }
      })(activityX, activityY) }
    ]
    positions.forEach(p => {
      const nodeData = toExpand.find(n => n.id === p.id)!
      const r = nodeData.category === 'Activity' ? 25 : 17.5
      const padding = 80
      
      // Resource/Personnel 标签在右侧，需要考虑标签向右延伸
      if (nodeData.category === 'Resource' || nodeData.category === 'Personnel') {
        const labelW = 80
        const labelDistance = 10
        const labelHeight = 12
        localRects.push({
          id: p.id,
          rect: {
            x1: p.x - r - padding,
            y1: p.y - Math.max(r, labelHeight / 2) - padding,
            x2: p.x + r + labelDistance + labelW + padding * 0.5,
            y2: p.y + Math.max(r, labelHeight / 2) + padding
          }
        })
      } else {
        // Activity 节点标签在底部
        const fontSize = 12
        const lineHeight = fontSize * 1.2
        const labelW = 100
        const labelMargin = 6
        localRects.push({
          id: p.id,
          rect: {
            x1: Math.min(p.x - r, p.x - labelW / 2) - padding,
            y1: p.y - r - padding,
            x2: Math.max(p.x + r, p.x + labelW / 2) + padding,
            y2: p.y + r + labelMargin + lineHeight + padding
          }
        })
      }
    })
    let localOverlap = 0
    for (let i = 0; i < localRects.length; i++) {
      for (let j = i + 1; j < localRects.length; j++) {
        const a = localRects[i].rect
        const b = localRects[j].rect
        if (!(a.x2 <= b.x1 || b.x2 <= a.x1 || a.y2 <= b.y1 || b.y2 <= a.y1)) {
          localOverlap++
        }
      }
    }
    
    console.log('[EXPAND_LAYOUT] added', activityId, toExpand.length)
    console.log('[EXPAND_LAYOUT] localOverlapAfter', localOverlap)
    
    // 添加节点（使用 layoutExpandedNodes 返回的 x/y）
    positions.forEach((pos: {id: string, x: number, y: number}) => {
      const nodeData = toExpand.find(n => n.id === pos.id)!
      if (nodeData.category === 'Resource') {
        displayNodes.push({
          id: nodeData.id,
          name: truncateText(nodeData.name, 8),
          fullName: nodeData.name,
          category: 'Resource',
          symbolSize: 35,
          symbol: 'rect',
          x: pos.x,
          y: pos.y,
          fixed: true,
          itemStyle: {
            color: getResourceColor(nodeData.rawData.status),
            borderWidth: 1,
            borderColor: '#fff'
          },
          label: {
            show: true,
            fontSize: 10,
            position: 'right',
            distance: 10,
            width: 80,
            overflow: 'truncate',
            lineHeight: 12
          }
        })
      } else if (nodeData.category === 'Personnel') {
        displayNodes.push({
          id: nodeData.id,
          name: truncateText(nodeData.name, 8),
          fullName: nodeData.name,
          category: 'Personnel',
          symbolSize: 35,
          symbol: 'diamond',
          x: pos.x,
          y: pos.y,
          fixed: true,
          itemStyle: {
            color: '#67C23A',
            borderWidth: 1,
            borderColor: '#fff'
          },
          label: {
            show: true,
            fontSize: 10,
            position: 'right',
            distance: 10,
            width: 80,
            overflow: 'truncate',
            lineHeight: 12
          }
        })
      }
    })
    
    // 添加边
    if (props.data.resource_edges) {
      props.data.resource_edges
        .filter((re: any) => re.source === activityId)
        .forEach((edge: any) => {
          displayEdges.push({
            source: edge.source,
            target: edge.target,
            lineStyle: {
              color: '#E6A23C',
              type: 'dashed',
              width: 1.5,
              curveness: 0.1
            },
            label: { show: false },
            edgeData: edge
          })
        })
    }
    
    if (props.data.personnel_edges) {
      props.data.personnel_edges
        .filter((pe: any) => pe.source === activityId)
        .forEach((edge: any) => {
          displayEdges.push({
            source: edge.source,
            target: edge.target,
            lineStyle: {
              color: '#67C23A',
              type: 'dotted',
              width: 1.5,
              curveness: 0.1
            },
            label: { show: false },
            edgeData: edge
          })
        })
    }
  })

  const categories = [
    { name: 'Activity' },
    { name: 'Resource' },
    { name: 'Personnel' },
    { name: 'Virtual' }
  ]

  // FitView
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
  displayNodes.forEach(node => {
    if (node.x != null && node.y != null) {
      minX = Math.min(minX, node.x)
      maxX = Math.max(maxX, node.x)
      minY = Math.min(minY, node.y)
      maxY = Math.max(maxY, node.y)
    }
  })
  
  const containerWidth = chartRef.value?.clientWidth || 800
  const containerHeight = chartRef.value?.clientHeight || 650
  const graphWidth = maxX - minX + 200
  const graphHeight = maxY - minY + 200
  const scaleX = containerWidth / graphWidth
  const scaleY = containerHeight / graphHeight
  let zoom = Math.min(Math.max(Math.min(scaleX, scaleY), 0.2), 1.0)
  let centerValue: [number, number] = [(minX + maxX) / 2, (minY + maxY) / 2]

  if (preserveView && chartInstance) {
    const prevOption = chartInstance.getOption()
    const prevSeries = Array.isArray(prevOption.series) ? prevOption.series[0] as any : undefined
    if (prevSeries) {
      if (prevSeries.zoom != null) {
        zoom = Array.isArray(prevSeries.zoom) ? prevSeries.zoom[0] : prevSeries.zoom
      }
      if (prevSeries.center != null) {
        centerValue = prevSeries.center as [number, number]
      }
    }
  }

  const option: echarts.EChartsOption = {
    title: {
      text: '生产流程依赖与资源关联视图',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'item',
      confine: true,
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const category = params.data.category
          if (category === 'Activity') {
            return `<b>${params.data.fullName}</b><br/>左键: 查看详情<br/>右键: 展开/折叠资源人员`
          } else if (category === 'Resource') {
            return `<b>资源: ${params.data.fullName}</b><br/>左键: 查看详情`
          } else if (category === 'Personnel') {
            return `<b>人员: ${params.data.fullName}</b><br/>左键: 查看详情`
          }
        } else if (params.dataType === 'edge') {
          const edge = params.data.edgeData
          if (edge) {
            const relation = (edge as any).relation
            if (relation === 'DEPENDS_ON') {
              let text = `<b>依赖关系</b><br/>类型: ${edge.type || '顺序'}`
              if (edge.time_constraint) text += `<br/>时间约束: ${edge.time_constraint}分钟`
              return text
            } else if (relation === 'USES') {
              let text = '<b>使用资源</b>'
              if ((edge as any).quantity) text += `<br/>数量: ${(edge as any).quantity}${(edge as any).unit || ''}`
              return text
            } else if (relation === 'ASSIGNS') {
              return `<b>分配人员</b><br/>角色: ${(edge as any).role || '操作员'}`
            }
          }
        }
        return ''
      }
    },
    legend: {
      show: false
    },
    series: [
      {
        type: 'graph',
        layout: 'none',
        data: displayNodes,
        links: displayEdges,
        categories: categories,
        roam: true,
        draggable: false,
        zoom: zoom,
        center: centerValue,
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 8],
        label: {
          show: true,
          position: 'bottom',
          formatter: '{b}'
        },
        lineStyle: {
          width: 2,
          curveness: 0
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 4
          }
        }
      }
    ]
  }

  chartInstance.setOption(option, true)
  bindChartEvents()
}

const bindChartEvents = () => {
  if (!chartInstance) return

  chartInstance.off('click')
  chartInstance.on('click', (params: any) => {
    if (params.dataType === 'node') {
      const nodeData = {
        id: params.data.id,
        name: params.data.fullName || params.data.name,
        category: params.data.category,
        rawData: params.data.rawData
      }
      emit('nodeClick', nodeData)
      setPinnedFocus(nodeData.id)
    }
  })

  chartInstance.off('contextmenu')
  chartInstance.on('contextmenu', handleContextMenu)
  
  // T7: hover 进入/离开
  chartInstance.off('mouseover')
  chartInstance.on('mouseover', (params: any) => {
    if (params.dataType === 'node') {
      setHoverFocus(params.data.id)
    }
  })
  chartInstance.off('mouseout')
  chartInstance.on('mouseout', () => {
    setHoverFocus(null)
  })
  
  chartInstance.off('globalout')
  chartInstance.on('globalout', () => {
    setHoverFocus(null)
  })
}

const getNodeColor = (status: string) => {
  const colorMap: Record<string, string> = {
    'pending': '#909399',
    'in_progress': '#409EFF',
    'completed': '#67C23A',
    'paused': '#E6A23C',
    'cancelled': '#F56C6C'
  }
  return colorMap[status] || '#909399'
}

const getResourceColor = (status: string) => {
  const colorMap: Record<string, string> = {
    'available': '#67C23A',
    'in_use': '#E6A23C',
    'depleted': '#F56C6C',
    'reserved': '#409EFF'
  }
  return colorMap[status] || '#67C23A'
}

// T6: 右键处理（不造成 sticky 高亮）
const handleContextMenu = (params: any) => {
  params.event?.event?.preventDefault?.()
  if (params.dataType !== 'node') return
  if (params.data?.category !== 'Activity') return
  
  // T6: 清理 hover，让 mouseout 事件自然触发（在图表更新前先清理）
  setHoverFocus(null)
  
  const activityId = params.data.id
  toggleActivityExpansion(activityId)
}

watch(() => props.data, () => {
  expandedActivities.value.clear()
  cachedNodePositions = null
  cachedVirtualNodes = []
  cachedDataHash = ''
  initChart()
}, { deep: true })

watch(() => [props.highlightActive, props.highlightSet], () => {
  if (chartInstance && props.data && props.data.nodes && props.data.nodes.length > 0) {
    initChart({ preserveView: true })
  }
}, { deep: true })

onMounted(() => {
  initChart()
  window.addEventListener('resize', () => {
    chartInstance?.resize()
  })
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.graph-container {
  position: relative;
  width: 100%;
  height: 650px;
}

.graph-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 10;
  display: flex;
  align-items: center;
}

.dependency-graph {
  width: 100%;
  height: 100%;
}

.activity-detail {
  padding: 10px;
}
</style>
