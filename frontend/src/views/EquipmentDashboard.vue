<template>
  <div class="equipment-dashboard">
    <div class="header-actions">
      <div class="left-actions">
        <el-input
          v-model="searchQuery"
          placeholder="搜索设备名称/ID"
          clearable
          class="search-input"
          :prefix-icon="Search"
        />
        
        <el-select v-model="sortOption" placeholder="排序方式" class="filter-select">
          <el-option label="默认排序" value="default" />
          <el-option label="生产日期(正序)" value="date_asc" />
          <el-option label="生产日期(倒序)" value="date_desc" />
        </el-select>

        <el-select v-model="specFilter" placeholder="设备种类" clearable class="filter-select">
          <el-option label="全部" value="" />
          <el-option
            v-for="spec in uniqueSpecs"
            :key="spec"
            :label="spec"
            :value="spec"
          />
        </el-select>

        <el-select v-model="processFilter" placeholder="流程" clearable class="filter-select">
          <el-option label="全部" value="" />
          <el-option
            v-for="pid in uniqueProcesses"
            :key="pid"
            :label="formatProcessName(pid)"
            :value="pid"
          />
        </el-select>
      </div>
      
      <div class="right-actions">
        <el-button type="primary" :icon="Plus" @click="openAddEquipmentDialog">添加设备</el-button>
        <el-badge :value="maintenanceEquipments.length" :hidden="maintenanceEquipments.length === 0" class="item">
          <el-button type="danger" @click="isMaintenanceModalVisible = true">
            <el-icon><Tools /></el-icon> 七天检修预警
          </el-button>
        </el-badge>
      </div>
    </div>

    <div class="equipment-list" v-loading="loading">
      <el-collapse v-if="processedEquipments.length > 0">
        <EquipmentAccordionItem
          v-for="equipment in processedEquipments"
          :key="equipment._id"
          :equipment="equipment"
          @update="fetchEquipments"
        />
      </el-collapse>
      <el-empty v-else description="暂无匹配的设备数据" />
    </div>

    <!-- 添加设备弹窗 -->
    <el-dialog v-model="addEquipmentDialogVisible" title="添加设备" width="520px">
      <el-form :model="addEquipmentForm" label-width="100px" size="default">
        <el-form-item label="设备名称" required>
          <el-input v-model="addEquipmentForm.name" placeholder="如：灌装机-03" />
        </el-form-item>
        <el-form-item label="设备种类" required>
          <el-input v-model="addEquipmentForm.specification" placeholder="如：灌装设备" />
        </el-form-item>
        <el-form-item label="型号规格" required>
          <el-input v-model="addEquipmentForm.model" placeholder="如：GZ-2000" />
        </el-form-item>
        <el-form-item label="供应商" required>
          <el-input v-model="addEquipmentForm.supplier" placeholder="供应商名称" />
        </el-form-item>
        <el-form-item label="生产厂家">
          <el-input v-model="addEquipmentForm.manufacturer" placeholder="生产厂家" />
        </el-form-item>
        <el-form-item label="生产时间">
          <el-date-picker v-model="addEquipmentForm.production_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="单位" required>
          <el-input v-model="addEquipmentForm.unit" placeholder="如：台" />
        </el-form-item>
        <el-form-item label="数量" required>
          <el-input-number v-model="addEquipmentForm.quantity" :min="1" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addEquipmentDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAddEquipment" :loading="addEquipmentSubmitting">确定添加</el-button>
      </template>
    </el-dialog>

    <!-- 七天检修预警弹窗 -->
    <el-dialog
      v-model="isMaintenanceModalVisible"
      title="七天检修预警"
      width="70%"
      center
    >
      <el-alert
        :title="`未来 7 天内共有 ${totalMaintenanceEquipments} 台设备需要检修，其中 ${totalAffectedActivities} 项生产活动可能面临设备停机风险，请及时在面板中重新调配资源！`"
        type="warning"
        show-icon
        :closable="false"
        class="warning-banner"
      />

      <div class="maintenance-groups">
        <div 
          v-for="(group, date) in groupedMaintenanceEquipments" 
          :key="date"
          class="date-group"
        >
          <div class="date-header">
            <el-tag type="danger" effect="dark" size="large">{{ formatDateLabel(date) }}</el-tag>
            <el-divider class="date-divider" />
          </div>
          
          <el-table :data="group" border style="width: 100%">
            <el-table-column prop="name" label="设备名称">
              <template #default="scope">
                <strong>{{ scope.row.name }}</strong>
              </template>
            </el-table-column>
            <el-table-column prop="specification" label="设备种类" width="150" />
            <el-table-column label="受影响的占用活动">
              <template #default="scope">
                <template v-if="scope.row.serving_activities_details && scope.row.serving_activities_details.length > 0">
                  <el-tag
                    v-for="detail in scope.row.serving_activities_details"
                    :key="detail.activity_name"
                    type="danger"
                    size="small"
                    class="activity-tag"
                  >
                    {{ detail.activity_name }}
                  </el-tag>
                </template>
                <span v-else class="safe-text">无关联活动，安全</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-if="Object.keys(groupedMaintenanceEquipments).length === 0" description="未来 7 天内无检修计划" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Search, Tools, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import EquipmentAccordionItem from '../components/EquipmentAccordionItem.vue'
import { createResource } from '@/api/resource'

const equipments = ref<any[]>([])
const loading = ref(false)

const searchQuery = ref('')
const sortOption = ref('default')
const specFilter = ref('')
const processFilter = ref('')

const isMaintenanceModalVisible = ref(false)

// 真实的流程映射字典
const processMap: Record<string, string> = {
  'P001': '主生产线',
  'P002': '副生产线',
  'T001': '冷链运输',
  'T002': '常温运输',
  'S001': '线上销售',
  'S002': '线下销售',
  'Q001': '常规质检',
  'Q002': '专项质检',
  'W001': '主仓库',
  'W002': '分仓库'
};

// 格式化流程名称，包含兜底逻辑
const formatProcessName = (processId: string) => {
  if (processMap[processId]) {
    return `${processId} - ${processMap[processId]}`;
  }
  
  // 兜底逻辑：根据首字母判断类型
  const prefix = processId.charAt(0).toUpperCase();
  const typeMap: Record<string, string> = {
    'P': '生产流程',
    'Q': '质检流程',
    'S': '销售流程',
    'W': '仓储流程',
    'T': '运输流程'
  };
  
  return `${processId} - ${typeMap[prefix] || '未知流程'}`;
}

const formatDateLabel = (dateStr: string) => {
  try {
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) {
      return dateStr
    }
    const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
    return `${date.getMonth() + 1}月${date.getDate()}日 (${days[date.getDay()]})`
  } catch {
    return dateStr
  }
}

const addEquipmentDialogVisible = ref(false)
const addEquipmentSubmitting = ref(false)

const defaultAddEquipmentForm = () => ({
  name: '',
  type: '设备',
  specification: '',
  model: '',
  supplier: '',
  manufacturer: '',
  production_date: '',
  unit: '台',
  quantity: 1,
  status: 'available'
})

const addEquipmentForm = ref(defaultAddEquipmentForm())

const openAddEquipmentDialog = () => {
  addEquipmentForm.value = defaultAddEquipmentForm()
  addEquipmentDialogVisible.value = true
}

const submitAddEquipment = async () => {
  if (!addEquipmentForm.value.name.trim()) {
    ElMessage.warning('设备名称不能为空')
    return
  }
  if (!addEquipmentForm.value.specification.trim()) {
    ElMessage.warning('设备种类不能为空')
    return
  }
  addEquipmentSubmitting.value = true
  try {
    await createResource(addEquipmentForm.value as any)
    ElMessage.success('设备添加成功')
    addEquipmentDialogVisible.value = false
    await fetchEquipments()
  } catch (error) {
    ElMessage.error('添加失败，请检查表单数据')
  } finally {
    addEquipmentSubmitting.value = false
  }
}

const fetchEquipments = async () => {
  loading.value = true
  try {
    const response = await fetch('http://localhost:8000/api/resources?type=设备')
    if (response.ok) {
      equipments.value = await response.json()
    }
  } catch (error) {
    console.error('Failed to fetch equipments:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchEquipments()
})

const uniqueSpecs = computed(() => {
  const specs = new Set<string>()
  equipments.value.forEach(eq => {
    if (eq.specification) specs.add(eq.specification)
  })
  return Array.from(specs)
})

const uniqueProcesses = computed(() => Object.keys(processMap))

const processedEquipments = computed(() => {
  let result = [...equipments.value]

  // 1. 搜索
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(eq => 
      (eq.name && eq.name.toLowerCase().includes(query)) ||
      (eq._id && eq._id.toLowerCase().includes(query))
    )
  }

  // 2. 过滤
  if (specFilter.value) {
    result = result.filter(eq => eq.specification === specFilter.value)
  }
  if (processFilter.value) {
    result = result.filter(eq => eq.serving_processes && eq.serving_processes.includes(processFilter.value))
  }

  // 3. 排序
  if (sortOption.value === 'date_asc') {
    result.sort((a, b) => {
      const timeA = new Date(a.production_date || 0).getTime()
      const timeB = new Date(b.production_date || 0).getTime()
      return (Number.isNaN(timeA) ? 0 : timeA) - (Number.isNaN(timeB) ? 0 : timeB)
    })
  } else if (sortOption.value === 'date_desc') {
    result.sort((a, b) => {
      const timeA = new Date(a.production_date || 0).getTime()
      const timeB = new Date(b.production_date || 0).getTime()
      return (Number.isNaN(timeB) ? 0 : timeB) - (Number.isNaN(timeA) ? 0 : timeA)
    })
  }

  return result
})

const maintenanceEquipments = computed(() => {
  return equipments.value.filter(eq => eq.upcoming_maintenance && eq.upcoming_maintenance.length > 0)
})

const groupedMaintenanceEquipments = computed(() => {
  const groups: Record<string, any[]> = {}
  
  maintenanceEquipments.value.forEach(eq => {
    eq.upcoming_maintenance.forEach((date: string) => {
      if (!groups[date]) {
        groups[date] = []
      }
      // 避免同一个设备在同一个日期重复添加
      if (!groups[date].find(item => item._id === eq._id)) {
        groups[date].push(eq)
      }
    })
  })

  // 按日期排序
  const sortedGroups: Record<string, any[]> = {}
  Object.keys(groups).sort((a, b) => {
    // 尝试解析相对时间，如 "明天", "1天后"
    const getDays = (str: string) => {
      if (str === '今天') return 0
      if (str === '明天') return 1
      if (str === '后天') return 2
      const match = str.match(/(\d+)天后/)
      if (match) return parseInt(match[1], 10)
      
      const time = new Date(str).getTime()
      return isNaN(time) ? 999 : time
    }
    return getDays(a) - getDays(b)
  }).forEach(key => {
    sortedGroups[key] = groups[key]
  })

  return sortedGroups
})

const totalMaintenanceEquipments = computed(() => {
  const uniqueIds = new Set()
  maintenanceEquipments.value.forEach(eq => uniqueIds.add(eq._id))
  return uniqueIds.size
})

const totalAffectedActivities = computed(() => {
  let count = 0
  maintenanceEquipments.value.forEach(eq => {
    if (eq.serving_activities_details && eq.serving_activities_details.length > 0) {
      count += eq.serving_activities_details.length
    }
  })
  return count
})

</script>

<style scoped>
.equipment-dashboard {
  padding: 20px;
}

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 16px;
}

.left-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.search-input {
  width: 250px;
}

.filter-select {
  width: 150px;
}

.warning-banner {
  margin-bottom: 20px;
}

.maintenance-groups {
  max-height: 60vh;
  overflow-y: auto;
}

.date-group {
  margin-bottom: 24px;
}

.date-header {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.date-divider {
  flex-grow: 1;
  margin-left: 16px;
}

.activity-tag {
  margin-right: 8px;
  margin-bottom: 4px;
}

.safe-text {
  color: #67c23a;
  font-weight: bold;
}
</style>
