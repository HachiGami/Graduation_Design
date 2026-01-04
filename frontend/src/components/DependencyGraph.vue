<template>
  <div class="graph-container">
    <div class="graph-controls">
      <el-button @click="resetView" :icon="'Refresh'">重置视图</el-button>
      <el-button @click="fitToView" :icon="'FullScreen'">适配视图</el-button>
      <el-text type="info" size="small" style="margin-left: 10px;">左键查看详情 | 右键展开资源/人员</el-text>
    </div>
    <div class="graph-wrapper">
      <div ref="chartRef" class="dependency-graph"></div>
    </div>
    
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
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import cytoscape from 'cytoscape'
import fcose from 'cytoscape-fcose'
import cxtmenu from 'cytoscape-cxtmenu'
import { computeELKLayout } from '@/utils/elkLayout'
import type { GraphData } from '@/types'

cytoscape.use(fcose)
cytoscape.use(cxtmenu)

const props = defineProps<{
  data: GraphData
  highlightActive?: boolean
  highlightSet?: {nodeIds: Set<string>, edgeIds: Set<string>}
}>()

const emit = defineEmits<{
  nodeClick: [node: any]
}>()

const chartRef = ref<HTMLElement>()
let cy: any = null
let cxtMenu: any = null
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

const initCytoscape = async () => {
  if (!chartRef.value) return

  const layoutResult = await computeELKLayout(
    props.data.nodes.map(n => ({ 
      id: n.id, 
      width: 100, 
      height: 60 
    })),
    props.data.edges.map(e => ({ 
      source: e.source, 
      target: e.target 
    })),
    {
      direction: 'RIGHT',
      nodeSpacing: 100,
      layerSpacing: 180
    }
  )

  const elements = [
    ...props.data.nodes.map(node => {
      const pos = layoutResult.positions.get(node.id)
      return {
        data: { 
          id: node.id, 
          label: node.name,
          nodeType: 'activity',
          rawData: node
        },
        position: pos || { x: 0, y: 0 },
        classes: 'activity-node'
      }
    }),
    ...props.data.edges.map(edge => ({
      data: { 
        id: `${edge.source}-${edge.target}`,
        source: edge.source, 
        target: edge.target,
        label: edge.type || '',
        crossDomain: edge.source && edge.target && 
          props.data.nodes.find(n => n.id === edge.source)?.domain !== 
          props.data.nodes.find(n => n.id === edge.target)?.domain,
        rawData: edge
      },
      classes: edge.source && edge.target && 
        props.data.nodes.find(n => n.id === edge.source)?.domain !== 
        props.data.nodes.find(n => n.id === edge.target)?.domain ? 'cross-domain' : ''
    }))
  ]

  cy = cytoscape({
    container: chartRef.value,
    elements: elements,
    style: [
      {
        selector: 'node',
        style: {
          'label': 'data(label)',
          'text-valign': 'center',
          'text-halign': 'center',
          'background-color': '#909399',
          'width': 100,
          'height': 60,
          'shape': 'ellipse',
          'font-size': '12px',
          'color': '#fff',
          'text-wrap': 'wrap',
          'text-max-width': '90px',
          'border-width': 2,
          'border-color': '#fff'
        }
      },
      {
        selector: 'node.activity-node',
        style: {
          'background-color': '#409EFF',
          'shape': 'ellipse'
        }
      },
      {
        selector: 'node.resource-node',
        style: {
          'background-color': '#67C23A',
          'shape': 'rectangle',
          'width': 80,
          'height': 50
        }
      },
      {
        selector: 'node.personnel-node',
        style: {
          'background-color': '#E6A23C',
          'shape': 'diamond',
          'width': 70,
          'height': 70
        }
      },
      {
        selector: 'node.expanded-node',
        style: {
          'border-color': '#F56C6C',
          'border-width': 3
        }
      },
      {
        selector: 'node.highlighted',
        style: {
          'border-color': '#F56C6C',
          'border-width': 4,
          'background-color': '#F56C6C'
        }
      },
      {
        selector: 'node.dimmed',
        style: {
          'opacity': 0.3
        }
      },
      {
        selector: 'edge',
        style: {
          'width': 2,
          'line-color': '#ccc',
          'target-arrow-color': '#ccc',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'label': 'data(label)',
          'font-size': '10px',
          'text-rotation': 'autorotate',
          'text-margin-y': -10
        }
      },
      {
        selector: 'edge.cross-domain',
        style: {
          'line-color': '#E6A23C',
          'target-arrow-color': '#E6A23C',
          'line-style': 'dashed',
          'width': 3
        }
      },
      {
        selector: 'edge.highlighted',
        style: {
          'line-color': '#F56C6C',
          'target-arrow-color': '#F56C6C',
          'width': 4
        }
      },
      {
        selector: 'edge.dimmed',
        style: {
          'opacity': 0.2
        }
      }
    ],
    layout: { name: 'preset' },
    minZoom: 0.1,
    maxZoom: 3,
    wheelSensitivity: 0.2
  })

  cy.fit(cy.elements(), 50)
  
  const currentZoom = cy.zoom()
  if (currentZoom < 0.5) {
    cy.zoom(0.5)
    cy.center()
  }

  cy.on('tap', 'node', (evt: any) => {
    const node = evt.target
    if (node.data('nodeType') === 'activity') {
      selectedActivity.value = node.data('rawData')
      detailDrawerVisible.value = true
      emit('nodeClick', node.data())
    }
  })

  setupContextMenu()

  cy.on('mouseover', 'node', (evt: any) => {
    const node = evt.target
    node.addClass('hover')
  })

  cy.on('mouseout', 'node', (evt: any) => {
    const node = evt.target
    node.removeClass('hover')
  })
}

const setupContextMenu = () => {
  if (!cy) return

  cxtMenu = cy.cxtmenu({
    selector: 'node.activity-node',
    commands: [
      {
        content: '<span style="color: #409EFF;">展开</span>',
        select: function(ele: any) {
          const nodeId = ele.id()
          if (expandedActivities.value.has(nodeId)) {
            collapseActivity(nodeId)
          } else {
            expandActivity(nodeId)
          }
        }
      }
    ],
    fillColor: 'rgba(255, 255, 255, 0.95)',
    activeFillColor: 'rgba(64, 158, 255, 0.2)',
    activePadding: 8,
    indicatorSize: 20,
    separatorWidth: 3,
    spotlightPadding: 4,
    minSpotlightRadius: 28,
    maxSpotlightRadius: 38,
    openMenuEvents: 'cxttapstart taphold',
    itemColor: '#333',
    itemTextShadowColor: 'transparent',
    zIndex: 9999,
    atMouse: false
  })
}

const expandActivity = (activityId: string) => {
  if (!cy) return

  const toExpand: Array<{id: string, name: string, category: string}> = []

  if (props.data.resource_nodes) {
    props.data.resource_nodes
      .filter((rn: any) => rn.parent_activity === activityId)
      .forEach((rn: any) => {
        if (!cy.$id(rn.id).length) {
          toExpand.push({ id: rn.id, name: rn.name, category: 'resource' })
        }
      })
  }

  if (props.data.personnel_nodes) {
    props.data.personnel_nodes
      .filter((pn: any) => pn.parent_activity === activityId)
      .forEach((pn: any) => {
        if (!cy.$id(pn.id).length) {
          toExpand.push({ id: pn.id, name: pn.name, category: 'personnel' })
        }
      })
  }

  if (toExpand.length === 0) return

  const hostNode = cy.$id(activityId)
  const hostPos = hostNode.position()

  const angleStep = (2 * Math.PI) / toExpand.length
  const radius = 200

  toExpand.forEach((item, index) => {
    const angle = angleStep * index
    const x = hostPos.x + radius * Math.cos(angle)
    const y = hostPos.y + radius * Math.sin(angle)

    cy.add({
      data: {
        id: item.id,
        label: item.name,
        nodeType: item.category,
        expandedFrom: activityId
      },
      position: { x, y },
      classes: `expanded-node ${item.category}-node`
    })

    cy.add({
      data: {
        id: `${activityId}-${item.id}`,
        source: activityId,
        target: item.id
      }
    })
  })

  localDeoverlap(activityId, radius + 100)
  expandedActivities.value.add(activityId)
}

const collapseActivity = (activityId: string) => {
  if (!cy) return

  cy.remove(`[expandedFrom="${activityId}"]`)
  cy.edges().filter((edge: any) => {
    const source = edge.data('source')
    const target = edge.data('target')
    return source === activityId && !cy.$id(target).length
  }).remove()

  expandedActivities.value.delete(activityId)
}

const localDeoverlap = (hostId: string, checkRadius: number) => {
  if (!cy) return

  const expandedNodes = cy.$(`[expandedFrom="${hostId}"]`)
  const hostPos = cy.$id(hostId).position()

  const nearbyNodes = cy.nodes().filter((node: any) => {
    if (node.id() === hostId) return false
    if (node.data('expandedFrom') === hostId) return false
    
    const pos = node.position()
    const dist = Math.sqrt((pos.x - hostPos.x) ** 2 + (pos.y - hostPos.y) ** 2)
    return dist < checkRadius
  })

  const allCheckNodes = nearbyNodes.union(cy.$id(hostId))

  let maxIterations = 20
  while (maxIterations > 0) {
    maxIterations--
    let moved = false

    expandedNodes.forEach((expNode: any) => {
      const expBB = expNode.boundingBox()
      
      allCheckNodes.forEach((otherNode: any) => {
        const otherBB = otherNode.boundingBox()
        
        const overlap = !(expBB.x2 < otherBB.x1 || expBB.x1 > otherBB.x2 ||
                         expBB.y2 < otherBB.y1 || expBB.y1 > otherBB.y2)
        
        if (overlap) {
          const expPos = expNode.position()
          const otherPos = otherNode.position()
          
          const dx = expPos.x - otherPos.x
          const dy = expPos.y - otherPos.y
          const dist = Math.sqrt(dx * dx + dy * dy) || 1
          
          const pushDist = 30
          expNode.position({
            x: expPos.x + (dx / dist) * pushDist,
            y: expPos.y + (dy / dist) * pushDist
          })
          
          moved = true
        }
      })
    })

    if (!moved) break
  }
}

const resetView = async () => {
  expandedActivities.value.clear()
  
  if (cy) {
    cy.remove('.expanded-node')
    cy.edges().filter((e: any) => {
      const target = e.data('target')
      return !cy.$id(target).length
    }).remove()

    // 重新运行 ELK 布局确保规整
    const mainNodes = cy.nodes().filter((n: any) => n.data('nodeType') === 'activity')
    const mainEdges = cy.edges()

    const layoutResult = await computeELKLayout(
      mainNodes.map((n: any) => ({ 
        id: n.id(), 
        width: 100, 
        height: 60 
      })),
      mainEdges.map((e: any) => ({ 
        source: e.data('source'), 
        target: e.data('target') 
      }))
    )

    cy.layout({
      name: 'preset',
      positions: (node: any) => {
        const pos = layoutResult.positions.get(node.id())
        return pos || node.position()
      },
      animate: true,
      animationDuration: 500
    }).run()
  }
  
  detailDrawerVisible.value = false
  selectedActivity.value = null
}

const fitToView = () => {
  if (cy) {
    cy.fit(cy.elements(), 50)
  }
}

watch(() => props.highlightActive, (active) => {
  if (!cy) return

  if (active && props.highlightSet) {
    cy.elements().addClass('dimmed')
    
    props.highlightSet.nodeIds.forEach(nodeId => {
      cy.$id(nodeId).removeClass('dimmed').addClass('highlighted')
    })
    
    props.highlightSet.edgeIds.forEach(edgeId => {
      cy.$id(edgeId).removeClass('dimmed').addClass('highlighted')
    })

    const highlightedElements = cy.$('.highlighted')
    if (highlightedElements.length > 0) {
      const currentZoom = cy.zoom()
      cy.fit(highlightedElements, 50)
      const newZoom = cy.zoom()
      if (newZoom < Math.max(currentZoom, 0.5)) {
        cy.zoom(Math.max(currentZoom, 0.5))
        cy.center(highlightedElements)
      }
    }
  } else {
    cy.elements().removeClass('dimmed highlighted')
  }
}, { immediate: true })

watch(() => props.data, async () => {
  if (cy) {
    cy.destroy()
    cy = null
  }
  await nextTick()
  await initCytoscape()
}, { deep: true })

onMounted(async () => {
  await initCytoscape()
})

onUnmounted(() => {
  if (cxtMenu) {
    cxtMenu.destroy()
  }
  if (cy) {
    cy.destroy()
  }
})
</script>

<style scoped>
.graph-container {
  width: 100%;
  height: calc(100vh - 200px);
  position: relative;
  display: flex;
  flex-direction: column;
}

.graph-controls {
  padding: 10px;
  background: #f5f7fa;
  border-bottom: 1px solid #dcdfe6;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.graph-wrapper {
  flex: 1;
  position: relative;
  display: flex;
  overflow: hidden;
}

.dependency-graph {
  flex: 1;
  background: #fff;
}

.activity-detail {
  padding: 20px;
}
</style>
