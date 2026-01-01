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
import type { GraphData } from '@/types'

const props = defineProps<{
  data: GraphData
}>()

const chartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null
const expandedActivities = ref<Set<string>>(new Set())
const detailDrawerVisible = ref(false)
const selectedActivity = ref<any>(null)

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

// 拓扑排序计算节点层级
const calculateNodeLayers = (nodes: any[], edges: any[]): Map<string, number> => {
  const layers = new Map<string, number>()
  const inDegree = new Map<string, number>()
  const adjacencyList = new Map<string, string[]>()
  
  // 初始化：所有节点入度为0，层级为0
  nodes.forEach(node => {
    layers.set(node.id, 0)
    inDegree.set(node.id, 0)
    adjacencyList.set(node.id, [])
  })
  
  // 构建图：计算入度和邻接表
  edges.forEach(edge => {
    if (edge.source && edge.target) {
      const currentInDegree = inDegree.get(edge.target) || 0
      inDegree.set(edge.target, currentInDegree + 1)
      
      const neighbors = adjacencyList.get(edge.source) || []
      neighbors.push(edge.target)
      adjacencyList.set(edge.source, neighbors)
    }
  })
  
  // BFS拓扑排序
  const queue: string[] = []
  
  // 入度为0的节点放入队列（起始节点）
  nodes.forEach(node => {
    if (inDegree.get(node.id) === 0) {
      queue.push(node.id)
      layers.set(node.id, 0)
    }
  })
  
  // 处理队列
  while (queue.length > 0) {
    const current = queue.shift()!
    const currentLayer = layers.get(current) || 0
    
    const neighbors = adjacencyList.get(current) || []
    neighbors.forEach(neighbor => {
      // 更新后继节点的层级：取所有前驱节点层级+1的最大值
      const newLayer = currentLayer + 1
      const existingLayer = layers.get(neighbor) || 0
      layers.set(neighbor, Math.max(existingLayer, newLayer))
      
      // 减少入度
      const degree = (inDegree.get(neighbor) || 0) - 1
      inDegree.set(neighbor, degree)
      
      // 入度为0时加入队列
      if (degree === 0) {
        queue.push(neighbor)
      }
    })
  }
  
  return layers
}

const initChart = () => {
  if (!chartRef.value) return

  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(chartRef.value)

  // 构建显示的节点和边
  const displayNodes: any[] = []
  const displayEdges: any[] = []

  // 1. 计算活动节点的层级（拓扑排序）
  const nodeLayers = calculateNodeLayers(props.data.nodes, props.data.edges)
  
  // 按层级分组节点
  const layerGroups = new Map<number, any[]>()
  const nodeMap = new Map<string, any>() // 用于节点去重
  
  props.data.nodes.forEach(node => {
    // 确保每个节点只处理一次（去重）
    if (!nodeMap.has(node.id)) {
      nodeMap.set(node.id, node)
      const layer = nodeLayers.get(node.id) || 0
      if (!layerGroups.has(layer)) {
        layerGroups.set(layer, [])
      }
      layerGroups.get(layer)!.push(node)
    }
  })
  
  // 2. 根据层级生成节点坐标
  const gapX = 220 // 层级间距
  const gapY = 80  // 同层节点间距
  const startX = 100
  const startY = 200
  
  const activityNodes: any[] = []
  
  // 按层级处理节点
  Array.from(layerGroups.keys()).sort((a, b) => a - b).forEach(layer => {
    const nodesInLayer = layerGroups.get(layer)!
    const layerHeight = (nodesInLayer.length - 1) * gapY
    const layerStartY = startY - layerHeight / 2
    
    nodesInLayer.forEach((node, indexInLayer) => {
      activityNodes.push({
        id: node.id,
        name: truncateText(node.name),
        fullName: node.name,
        category: 'Activity',
        symbolSize: 50,
        symbol: 'circle',
        x: startX + layer * gapX,
        y: layerStartY + indexInLayer * gapY,
        fixed: true,
        itemStyle: {
          color: getNodeColor(node.status),
          borderWidth: 2,
          borderColor: '#fff'
        },
        label: {
          show: true,
          fontSize: 12,
          fontWeight: 'bold'
        },
        rawData: node,
        layer: layer
      })
    })
  })

  displayNodes.push(...activityNodes)

  // 2. 添加活动依赖关系
  const dependencyEdges = props.data.edges.map(edge => ({
    source: edge.source,
    target: edge.target,
    lineStyle: {
      color: '#409EFF',
      type: 'solid',
      width: 3,
      curveness: 0.15
    },
    label: { show: false },
    edgeData: edge
  }))

  displayEdges.push(...dependencyEdges)

  // 3. 为展开的活动添加资源节点和边
  if (props.data.resource_nodes && props.data.resource_edges) {
    const resourceNodeMap = new Map<string, any>() // 资源节点去重
    
    expandedActivities.value.forEach(activityId => {
      const activityNode = activityNodes.find(n => n.id === activityId)
      if (!activityNode) return

      const activityX = activityNode.x
      const activityY = activityNode.y
      const activityResources = props.data.resource_nodes!.filter(
        (rn: any) => rn.parent_activity === activityId
      )

      activityResources.forEach((resourceNode: any, idx: number) => {
        // 确保资源节点不重复
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

  // 4. 为展开的活动添加人员节点和边
  if (props.data.personnel_nodes && props.data.personnel_edges) {
    const personnelNodeMap = new Map<string, any>() // 人员节点去重
    
    expandedActivities.value.forEach(activityId => {
      const activityNode = activityNodes.find(n => n.id === activityId)
      if (!activityNode) return

      const activityX = activityNode.x
      const activityY = activityNode.y
      const activityPersonnel = props.data.personnel_nodes!.filter(
        (pn: any) => pn.parent_activity === activityId
      )

      activityPersonnel.forEach((personnelNode: any, idx: number) => {
        // 确保人员节点不重复
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
    { name: 'Personnel' }
  ]

  const option: echarts.EChartsOption = {
    title: {
      text: '生产流程依赖图',
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
            return `<b>资源: ${params.data.fullName}</b>`
          } else if (category === 'Personnel') {
            return `<b>人员: ${params.data.fullName}</b>`
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
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 10],
        label: {
          show: true,
          position: 'bottom',
          formatter: '{b}'
        },
        lineStyle: {
          color: 'source',
          curveness: 0.15
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
  
  // 左键点击：显示活动详情（移除旧监听器后重新绑定）
  chartInstance.off('click')
  chartInstance.on('click', (params: any) => {
    if (params.dataType === 'node' && params.data.category === 'Activity') {
      showActivityDetail(params.data.rawData)
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

// 右键点击处理函数（只绑定一次）
const handleContextMenu = (e: MouseEvent) => {
  e.preventDefault()
  
  if (!chartRef.value || !chartInstance) return
  
  const rect = chartRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  
  // 获取当前的节点列表
  const currentOption = chartInstance.getOption()
  const seriesData = currentOption.series?.[0]?.data || []
  
  // 遍历节点查找被点击的节点
  for (const node of seriesData as any[]) {
    if (node.category !== 'Activity') continue
    
    const nodeX = node.x
    const nodeY = node.y
    
    // 将图表坐标转换为像素坐标
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
  initChart()
}, { deep: true })

onMounted(() => {
  initChart()
  
  // 添加右键事件监听器（只添加一次）
  if (chartRef.value) {
    chartRef.value.addEventListener('contextmenu', handleContextMenu)
  }
  
  window.addEventListener('resize', () => {
    chartInstance?.resize()
  })
})

onUnmounted(() => {
  // 清理事件监听器
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

