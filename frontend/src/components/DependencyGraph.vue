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
  } else {
    expandedActivities.value.add(activityId)
  }
  initChart()
}

const showActivityDetail = (activity: any) => {
  selectedActivity.value = activity
  detailDrawerVisible.value = true
}

const truncateText = (text: string, maxLength: number = 6): string => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
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
    const node = g.node(nodeId)
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
  
  const optimizeLayerOrder = (iterations: number = 2) => {
    for (let iter = 0; iter < iterations; iter++) {
      const rankGroups = new Map<number, string[]>()
      g2.nodes().forEach(nodeId => {
        const node = g2.node(nodeId)
        const rank = node.rank || 0
        if (!rankGroups.has(rank)) {
          rankGroups.set(rank, [])
        }
        rankGroups.get(rank)!.push(nodeId)
      })
      
      rankGroups.forEach((nodeIds, rank) => {
        const barycenters = nodeIds.map(nodeId => {
          const edges = g2.nodeEdges(nodeId) || []
          let sumY = 0
          let count = 0
          
          edges.forEach(e => {
            const other = e.v === nodeId ? e.w : e.v
            const otherNode = g2.node(other)
            if (otherNode && otherNode.rank !== rank) {
              sumY += otherNode.y
              count++
            }
          })
          
          return { nodeId, barycenter: count > 0 ? sumY / count : g2.node(nodeId).y }
        })
        
        barycenters.sort((a, b) => a.barycenter - b.barycenter)
        
        const spacing = 140
        barycenters.forEach((item, idx) => {
          const node = g2.node(item.nodeId)
          node.y = idx * spacing
        })
      })
    }
  }
  
  optimizeLayerOrder(2)
  
  const nodePositions = new Map<string, { x: number, y: number, isVirtual?: boolean }>()
  let minX = Infinity, minY = Infinity
  
  g2.nodes().forEach(nodeId => {
    const node = g2.node(nodeId)
    const meta = nodeMetadata.get(nodeId)
    
    const x = Math.round(node.x / 20) * 20
    const y = Math.round(node.y / 20) * 20
    
    nodePositions.set(nodeId, { 
      x, 
      y, 
      isVirtual: meta?.isVirtual || false 
    })
    
    minX = Math.min(minX, x)
    minY = Math.min(minY, y)
  })
  
  const padding = 100
  nodePositions.forEach((pos) => {
    pos.x = pos.x - minX + padding
    pos.y = pos.y - minY + padding
  })
  
  return { nodePositions, virtualNodes: virtualNodes.map(v => v.id) }
}

const initChart = () => {
  if (!chartRef.value) return
  
  if (!props.data || !props.data.nodes || props.data.nodes.length === 0) {
    return
  }

  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(chartRef.value)

  const displayNodes: any[] = []
  const displayEdges: any[] = []

  const dataHash = JSON.stringify({
    nodeIds: props.data.nodes.map((n: any) => n.id).sort(),
    edgeIds: props.data.edges.map((e: any) => `${e.source}-${e.target}`).sort(),
    expanded: Array.from(expandedActivities.value).sort()
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
  
  props.data.edges.forEach((edge, index) => {
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

  // 资源节点
  if (props.data.resource_nodes && props.data.resource_edges) {
    const resourceNodeMap = new Map<string, any>()
    
    expandedActivities.value.forEach(activityId => {
      const activityNode = activityNodes.find(n => n.id === activityId)
      if (!activityNode) return

      const activityX = activityNode.x
      const activityY = activityNode.y
      const activityResources = props.data.resource_nodes!.filter(
        (rn: any) => rn.parent_activity === activityId
      )

      activityResources.forEach((resourceNode: any, idx: number) => {
        if (!resourceNodeMap.has(resourceNode.id)) {
          resourceNodeMap.set(resourceNode.id, true)
          displayNodes.push({
            id: resourceNode.id,
            name: truncateText(resourceNode.name),
            fullName: resourceNode.name,
            category: 'Resource',
            symbolSize: 35,
            symbol: 'rect',
            x: activityX - 40 + idx * 40,
            y: activityY + 120,
            fixed: true,
            itemStyle: {
              color: getResourceColor(resourceNode.status),
              borderWidth: 1,
              borderColor: '#fff'
            },
            label: {
              show: true,
              fontSize: 10
            }
          })
        }
      })

      const activityResourceEdges = props.data.resource_edges!.filter(
        (re: any) => re.source === activityId
      )
      activityResourceEdges.forEach((edge: any) => {
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
    })
  }

  // 人员节点
  if (props.data.personnel_nodes && props.data.personnel_edges) {
    const personnelNodeMap = new Map<string, any>()
    
    expandedActivities.value.forEach(activityId => {
      const activityNode = activityNodes.find(n => n.id === activityId)
      if (!activityNode) return

      const activityX = activityNode.x
      const activityY = activityNode.y
      const activityPersonnel = props.data.personnel_nodes!.filter(
        (pn: any) => pn.parent_activity === activityId
      )

      activityPersonnel.forEach((personnelNode: any, idx: number) => {
        if (!personnelNodeMap.has(personnelNode.id)) {
          personnelNodeMap.set(personnelNode.id, true)
          displayNodes.push({
            id: personnelNode.id,
            name: truncateText(personnelNode.name),
            fullName: personnelNode.name,
            category: 'Personnel',
            symbolSize: 35,
            symbol: 'diamond',
            x: activityX - 40 + idx * 40,
            y: activityY - 120,
            fixed: true,
            itemStyle: {
              color: '#67C23A',
              borderWidth: 1,
              borderColor: '#fff'
            },
            label: {
              show: true,
              fontSize: 10
            }
          })
        }
      })

      const activityPersonnelEdges = props.data.personnel_edges!.filter(
        (pe: any) => pe.source === activityId
      )
      activityPersonnelEdges.forEach((edge: any) => {
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
    })
  }

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
  const zoom = Math.min(Math.max(Math.min(scaleX, scaleY), 0.2), 1.0)

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
        center: [(minX + maxX) / 2, (minY + maxY) / 2],
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

  chartInstance.setOption(option)
  
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
    }
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

const handleContextMenu = (e: MouseEvent) => {
  e.preventDefault()
  
  if (!chartRef.value || !chartInstance) return
  
  const rect = chartRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  
  const currentOption = chartInstance.getOption()
  const seriesData = currentOption.series?.[0]?.data || []
  
  for (const node of seriesData as any[]) {
    if (node.category !== 'Activity') continue
    
    const nodeX = node.x
    const nodeY = node.y
    
    const pixelPoint = chartInstance.convertToPixel({ seriesIndex: 0 }, [nodeX, nodeY])
    
    const distance = Math.sqrt(
      Math.pow(pixelPoint[0] - x, 2) + Math.pow(pixelPoint[1] - y, 2)
    )
    
    if (distance < 30) {
      toggleActivityExpansion(node.id)
      break
    }
  }
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
    initChart()
  }
}, { deep: true })

onMounted(() => {
  initChart()
  
  if (chartRef.value) {
    chartRef.value.addEventListener('contextmenu', handleContextMenu)
  }
  
  window.addEventListener('resize', () => {
    chartInstance?.resize()
  })
})

onUnmounted(() => {
  if (chartRef.value) {
    chartRef.value.removeEventListener('contextmenu', handleContextMenu)
  }
  
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
