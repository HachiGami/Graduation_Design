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
          <el-descriptions-item label="所属流程">{{ getProcessName(selectedActivity.process_id) || '未知' }}</el-descriptions-item>
          <el-descriptions-item label="活动类型">{{ getDomainName(selectedActivity.domain) || '未知' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedActivity.status)">{{ getStatusName(selectedActivity.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="预计时长">{{ selectedActivity.estimated_duration }}分钟</el-descriptions-item>
          <el-descriptions-item label="描述">{{ selectedActivity.description || '无' }}</el-descriptions-item>
          <el-descriptions-item label="SOP步骤" v-if="selectedActivity.sop_steps && selectedActivity.sop_steps.length > 0">
            <div v-for="(step, index) in selectedActivity.sop_steps" :key="index" style="margin-bottom: 8px;">
              <el-tag type="primary" size="small" style="margin-right: 8px;">步骤{{ step.step_number }}</el-tag>
              {{ step.description }} ({{ step.duration }}分钟)
            </div>
          </el-descriptions-item>
        </el-descriptions>
        <div style="margin-top: 20px; text-align: right;">
          <el-button type="primary" @click="handleEditActivity">编辑活动</el-button>
        </div>
      </div>
    </el-drawer>

    <el-drawer
      v-model="personnelDrawerVisible"
      :title="selectedPersonnel?.name || '人员详情'"
      size="50%"
      direction="rtl"
    >
      <div v-if="selectedPersonnel" class="personnel-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="姓名">{{ selectedPersonnel.name }}</el-descriptions-item>
          <el-descriptions-item label="角色">{{ getRoleName(selectedPersonnel.role) || '未知' }}</el-descriptions-item>
          <el-descriptions-item label="职责">{{ selectedPersonnel.responsibility || '无' }}</el-descriptions-item>
          <el-descriptions-item label="工作时间">{{ selectedPersonnel.work_hours || '未知' }}</el-descriptions-item>
          <el-descriptions-item label="技能">
            <el-tag v-for="skill in selectedPersonnel.skills" :key="skill" style="margin-right: 5px;">{{ skill }}</el-tag>
            <span v-if="!selectedPersonnel.skills || selectedPersonnel.skills.length === 0">无</span>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedPersonnel.status)">
              {{ getStatusName(selectedPersonnel.status) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <div style="margin-top: 20px; text-align: right;">
          <el-button type="primary" @click="handleEditPersonnel">编辑人员</el-button>
        </div>
      </div>
    </el-drawer>

    <el-drawer
      v-model="resourceDrawerVisible"
      :title="selectedResource?.name || '资源详情'"
      size="50%"
      direction="rtl"
    >
      <div v-if="selectedResource" class="resource-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="资源名称">{{ selectedResource.name }}</el-descriptions-item>
          <el-descriptions-item label="资源类型">{{ getResourceTypeName(selectedResource.type) || '未知' }}</el-descriptions-item>
          <el-descriptions-item label="规格">{{ selectedResource.specification || '无' }}</el-descriptions-item>
          <el-descriptions-item label="供应商">{{ selectedResource.supplier || '无' }}</el-descriptions-item>
          <el-descriptions-item label="数量">{{ selectedResource.quantity }} {{ selectedResource.unit }}</el-descriptions-item>
          <el-descriptions-item label="过期日期" v-if="selectedResource.expiry_date">{{ selectedResource.expiry_date }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedResource.status)">
              {{ getStatusName(selectedResource.status) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <div style="margin-top: 20px; text-align: right;">
          <el-button type="primary" @click="handleEditResource">编辑资源</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import cytoscape from 'cytoscape'
import fcose from 'cytoscape-fcose'
import { computeELKLayout } from '@/utils/elkLayout'
import type { GraphData } from '@/types'
import { getActivity } from '@/api/activity'
import { getPersonnelById } from '@/api/personnel'
import { getResource } from '@/api/resource'

cytoscape.use(fcose)

const props = defineProps<{
  data: GraphData
  highlightActive?: boolean
  highlightSet?: {nodeIds: Set<string>, edgeIds: Set<string>}
}>()

const emit = defineEmits<{
  nodeClick: [node: any]
  editActivity: [activity: any]
  editPersonnel: [personnel: any]
  editResource: [resource: any]
}>()

const chartRef = ref<HTMLElement>()
let cy: any = null
const expandedActivities = ref<Set<string>>(new Set())
const detailDrawerVisible = ref(false)
const selectedActivity = ref<any>(null)
const selectedPersonnel = ref<any>(null)
const selectedResource = ref<any>(null)
const personnelDrawerVisible = ref(false)
const resourceDrawerVisible = ref(false)

const getStatusType = (status: string) => {
  const typeMap: Record<string, string> = {
    'pending': 'info',
    'in_progress': 'warning',
    'completed': 'success',
    'paused': 'warning',
    'cancelled': 'danger',
    'available': 'success',
    'in_use': 'warning',
    'maintenance': 'danger'
  }
  return typeMap[status] || 'info'
}

const getDomainName = (domain: string) => {
  const domainMap: Record<string, string> = {
    'production': '生产',
    'transport': '运输',
    'sales': '销售',
    'quality': '质检',
    'warehouse': '仓储'
  }
  return domainMap[domain] || domain
}

const getProcessName = (processId: string) => {
  const processMap: Record<string, string> = {
    'P001': 'P001 - 主生产线',
    'P002': 'P002 - 副生产线',
    'T001': 'T001 - 冷链运输',
    'T002': 'T002 - 常温运输',
    'S001': 'S001 - 线上销售',
    'S002': 'S002 - 线下销售',
    'Q001': 'Q001 - 常规质检',
    'Q002': 'Q002 - 专项质检',
    'W001': 'W001 - 主仓库',
    'W002': 'W002 - 分仓库'
  }
  return processMap[processId] || processId
}

const getStatusName = (status: string) => {
  const statusMap: Record<string, string> = {
    'pending': '待处理',
    'in_progress': '进行中',
    'completed': '已完成',
    'paused': '已暂停',
    'cancelled': '已取消',
    'available': '可用',
    'in_use': '使用中',
    'maintenance': '维护中',
    'active': '活跃',
    'inactive': '非活跃'
  }
  return statusMap[status] || status
}

const getRoleName = (role: string) => {
  const roleMap: Record<string, string> = {
    'operator': '操作员',
    'supervisor': '主管',
    'manager': '经理',
    'technician': '技术员',
    'quality_inspector': '质检员',
    'driver': '司机',
    'warehouse_keeper': '仓管员',
    'sales_representative': '销售代表'
  }
  return roleMap[role] || role
}

const getResourceTypeName = (type: string) => {
  const typeMap: Record<string, string> = {
    'material': '材料',
    'equipment': '设备',
    'tool': '工具',
    'vehicle': '车辆',
    'consumable': '耗材'
  }
  return typeMap[type] || type
}

const handleEditActivity = () => {
  detailDrawerVisible.value = false
  emit('editActivity', selectedActivity.value)
}

const handleEditPersonnel = () => {
  personnelDrawerVisible.value = false
  emit('editPersonnel', selectedPersonnel.value)
}

const handleEditResource = () => {
  resourceDrawerVisible.value = false
  emit('editResource', selectedResource.value)
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
          'curve-style': 'bezier'
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
    wheelSensitivity: 2
  })

  cy.fit(cy.elements(), 50)
  
  const currentZoom = cy.zoom()
  if (currentZoom < 0.5) {
    cy.zoom(0.5)
    cy.center()
  }

  cy.on('tap', 'node', async (evt: any) => {
    const node = evt.target
    const nodeType = node.data('nodeType')
    const rawData = node.data('rawData')
    
    if (nodeType === 'activity') {
      try {
        const fullActivity = await getActivity(rawData.id)
        if ((fullActivity as any)._id && !fullActivity.id) {
          fullActivity.id = (fullActivity as any)._id
        }
        selectedActivity.value = fullActivity
      } catch (error) {
        selectedActivity.value = rawData
      }
      detailDrawerVisible.value = true
      emit('nodeClick', node.data())
    } else if (nodeType === 'personnel' && rawData) {
      try {
        let personnelId = rawData.original_id || rawData.id
        if (personnelId && personnelId.includes('_inst_')) {
          personnelId = personnelId.split('_inst_')[0]
        }
        const fullPersonnel = await getPersonnelById(personnelId)
        if ((fullPersonnel as any)._id && !fullPersonnel.id) {
          fullPersonnel.id = (fullPersonnel as any)._id
        }
        selectedPersonnel.value = fullPersonnel
      } catch (error) {
        selectedPersonnel.value = rawData
      }
      personnelDrawerVisible.value = true
    } else if (nodeType === 'resource' && rawData) {
      try {
        let resourceId = rawData.original_id || rawData.id
        if (resourceId && resourceId.includes('_inst_')) {
          resourceId = resourceId.split('_inst_')[0]
        }
        const fullResource = await getResource(resourceId)
        if ((fullResource as any)._id && !fullResource.id) {
          fullResource.id = (fullResource as any)._id
        }
        selectedResource.value = fullResource
      } catch (error) {
        selectedResource.value = rawData
      }
      resourceDrawerVisible.value = true
    }
  })

  cy.on('cxttap', 'node.activity-node', (evt: any) => {
    const node = evt.target
    const nodeId = node.id()
    if (expandedActivities.value.has(nodeId)) {
      collapseActivity(nodeId)
    } else {
      expandActivity(nodeId)
    }
  })

  cy.on('mouseover', 'node', (evt: any) => {
    const node = evt.target
    node.addClass('hover')
  })

  cy.on('mouseout', 'node', (evt: any) => {
    const node = evt.target
    node.removeClass('hover')
  })
}


const expandActivity = (activityId: string) => {
  if (!cy) return

  const toExpand: Array<{id: string, name: string, category: string, rawData?: any}> = []

  if (props.data.resource_nodes) {
    props.data.resource_nodes
      .filter((rn: any) => rn.parent_activity === activityId)
      .forEach((rn: any) => {
        if (!cy.$id(rn.id).length) {
          toExpand.push({ id: rn.id, name: rn.name, category: 'resource', rawData: rn })
        }
      })
  }

  if (props.data.personnel_nodes) {
    props.data.personnel_nodes
      .filter((pn: any) => pn.parent_activity === activityId)
      .forEach((pn: any) => {
        if (!cy.$id(pn.id).length) {
          toExpand.push({ id: pn.id, name: pn.name, category: 'personnel', rawData: pn })
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
        expandedFrom: activityId,
        rawData: item.rawData
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

watch([() => props.highlightActive, () => props.highlightSet], ([active]) => {
  if (!cy) return

  // 如果highlightActive为false，或者highlightSet为空，则恢复全亮状态
  const hasHighlight = active && props.highlightSet && (props.highlightSet.nodeIds.size > 0 || props.highlightSet.edgeIds.size > 0)
  
  if (hasHighlight) {
    cy.elements().removeClass('highlighted')
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
