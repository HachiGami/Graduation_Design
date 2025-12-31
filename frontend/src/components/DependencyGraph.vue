<template>
  <div ref="chartRef" class="dependency-graph"></div>
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

const initChart = () => {
  if (!chartRef.value) return

  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(chartRef.value)

  const nodes = props.data.nodes.map(node => ({
    id: node.id,
    name: node.name,
    category: (node as any).category || 'Activity',
    symbolSize: (node as any).category === 'Resource' ? 40 : 50,
    symbol: (node as any).category === 'Resource' ? 'rect' : 'circle',
    itemStyle: {
      color: (node as any).category === 'Resource' ? getResourceColor(node.status) : getNodeColor(node.status)
    }
  }))

  const links = props.data.edges.map(edge => ({
    source: edge.source,
    target: edge.target,
    lineStyle: {
      color: (edge as any).relation === 'USES' ? '#E6A23C' : '#409EFF',
      type: (edge as any).relation === 'USES' ? 'dashed' : 'solid',
      width: 2
    },
    label: {
      show: true,
      formatter: () => {
        if ((edge as any).relation === 'USES') {
          const parts = ['使用']
          if ((edge as any).quantity) parts.push(`${(edge as any).quantity}${(edge as any).unit || ''}`)
          return parts.join('\n')
        } else {
          const parts = []
          if (edge.type) parts.push(edge.type)
          if (edge.time_constraint) parts.push(`${edge.time_constraint}分钟`)
          return parts.join('\n')
        }
      }
    }
  }))

  const categories = [
    { name: 'Activity' },
    { name: 'Resource' }
  ]

  const option: echarts.EChartsOption = {
    title: {
      text: '生产依赖关系图',
      left: 'center'
    },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const node = props.data.nodes.find(n => n.id === params.data.id)
          if (node) {
            const category = (node as any).category
            if (category === 'Resource') {
              return `资源: ${params.data.name}<br/>状态: ${node.status}`
            } else {
              return `活动: ${params.data.name}<br/>类型: ${node.type}<br/>状态: ${node.status}`
            }
          }
        } else if (params.dataType === 'edge') {
          const edge = props.data.edges.find(
            e => e.source === params.data.source && e.target === params.data.target
          )
          if (edge) {
            const relation = (edge as any).relation
            if (relation === 'USES') {
              let text = '关系: 使用资源'
              if ((edge as any).quantity) text += `<br/>数量: ${(edge as any).quantity}${(edge as any).unit || ''}`
              if ((edge as any).stage) text += `<br/>阶段: ${(edge as any).stage}`
              return text
            } else {
              let text = `依赖类型: ${edge.type}`
              if (edge.time_constraint) text += `<br/>时间约束: ${edge.time_constraint}分钟`
              if ((edge as any).status) text += `<br/>状态: ${(edge as any).status}`
              if (edge.description) text += `<br/>描述: ${edge.description}`
              return text
            }
          }
        }
        return ''
      }
    },
    legend: {
      data: categories.map(c => c.name),
      bottom: 10
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: nodes,
        links: links,
        categories: categories,
        roam: true,
        label: {
          show: true,
          position: 'right',
          formatter: '{b}'
        },
        edgeLabel: {
          fontSize: 12
        },
        force: {
          repulsion: 200,
          edgeLength: 150
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 5
          }
        }
      }
    ]
  }

  chartInstance.setOption(option)
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

watch(() => props.data, () => {
  initChart()
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
.dependency-graph {
  width: 100%;
  height: 600px;
}
</style>

