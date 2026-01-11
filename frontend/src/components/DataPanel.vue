<template>
  <div class="data-panel">
    <div class="panel-header">
      <h2>数据管理面板</h2>
      <el-button type="primary" @click="handleRefresh">刷新数据</el-button>
    </div>

    <el-tabs v-model="activeTab" class="data-tabs">
      <!-- 活动标签页 -->
      <el-tab-pane label="活动" name="activities">
        <el-table
          :data="activities"
          style="width: 100%"
          @row-click="handleActivityRowClick"
          stripe
          highlight-current-row
        >
          <el-table-column prop="name" label="名称" width="180" />
          <el-table-column label="状态" width="120">
            <template #default="scope">
              <el-tag :type="getStatusTagType(scope.row.status)">
                {{ getStatusText(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="estimated_duration" label="预估时长(分钟)" width="140" />
          <el-table-column prop="description" label="描述" show-overflow-tooltip />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="scope">
              <el-button type="primary" size="small" @click.stop="handleActivityRowClick(scope.row)">
                查看详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 员工标签页 -->
      <el-tab-pane label="员工" name="personnel">
        <el-table
          :data="personnel"
          style="width: 100%"
          @row-click="handlePersonnelRowClick"
          stripe
          highlight-current-row
        >
          <el-table-column prop="name" label="姓名" width="150" />
          <el-table-column prop="role" label="职位" width="150" />
          <el-table-column prop="department" label="部门" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="scope">
              <el-button type="primary" size="small" @click.stop="handlePersonnelRowClick(scope.row)">
                查看详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 设备标签页 -->
      <el-tab-pane label="设备" name="equipment">
        <el-table
          :data="equipment"
          style="width: 100%"
          @row-click="handleEquipmentRowClick"
          stripe
          highlight-current-row
        >
          <el-table-column prop="name" label="名称" width="180" />
          <el-table-column prop="specification" label="规格" width="150" />
          <el-table-column prop="quantity" label="总量" width="100" />
          <el-table-column label="状态" width="120">
            <template #default="scope">
              <el-tag :type="getStatusTagType(scope.row.status)">
                {{ getStatusText(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="scope">
              <el-button type="primary" size="small" @click.stop="handleEquipmentRowClick(scope.row)">
                查看详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 原料标签页 -->
      <el-tab-pane label="原料" name="materials">
        <el-table
          :data="materials"
          style="width: 100%"
          @row-click="handleMaterialRowClick"
          stripe
          highlight-current-row
        >
          <el-table-column prop="name" label="名称" width="180" />
          <el-table-column prop="specification" label="规格" width="150" />
          <el-table-column prop="quantity" label="库存总量" width="120" />
          <el-table-column prop="unit" label="单位" width="100" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="scope">
              <el-button type="primary" size="small" @click.stop="handleMaterialRowClick(scope.row)">
                查看详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="drawerTitle"
      size="60%"
      :before-close="handleDrawerClose"
    >
      <div class="drawer-content">
        <!-- 操作按钮组 -->
        <div class="action-buttons">
          <el-button v-if="!isEditing" type="primary" @click="handleEdit">
            编辑
          </el-button>
          <template v-else>
            <el-button type="success" @click="handleSave">保存</el-button>
            <el-button @click="handleCancel">取消</el-button>
          </template>
        </div>

        <!-- 活动详情 -->
        <template v-if="currentType === 'activity' && currentItem">
          <el-divider content-position="left">基本信息</el-divider>
          
          <el-descriptions v-if="!isEditing" :column="2" border>
            <el-descriptions-item label="名称">{{ currentItem.name }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="getStatusTagType(currentItem.status)">
                {{ getStatusText(currentItem.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="预估时长">{{ currentItem.estimated_duration }} 分钟</el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">{{ currentItem.description }}</el-descriptions-item>
          </el-descriptions>

          <el-form v-else :model="editForm" label-width="120px">
            <el-form-item label="名称">
              <el-input v-model="editForm.name" />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="editForm.status">
                <el-option label="未开始" value="pending" />
                <el-option label="进行中" value="in_progress" />
                <el-option label="已完成" value="completed" />
              </el-select>
            </el-form-item>
            <el-form-item label="预估时长">
              <el-input-number v-model="editForm.estimated_duration" :min="0" />
            </el-form-item>
            <el-form-item label="描述">
              <el-input v-model="editForm.description" type="textarea" :rows="3" />
            </el-form-item>
          </el-form>

          <el-divider content-position="left">SOP 步骤</el-divider>
          
          <div v-if="!isEditing" class="sop-steps">
            <el-tag v-for="(step, idx) in currentItem.sop_steps" :key="idx" class="sop-tag">
              {{ (idx as number) + 1 }}. {{ step }}
            </el-tag>
            <el-empty v-if="!currentItem.sop_steps || currentItem.sop_steps.length === 0" description="暂无步骤" />
          </div>

          <div v-else class="sop-edit">
            <div v-for="(_, idx) in editForm.sop_steps" :key="idx" class="sop-item">
              <el-input v-model="editForm.sop_steps[idx as number]" :placeholder="`步骤 ${(idx as number) + 1}`" />
              <el-button type="danger" size="small" @click="removeStep(idx as number)">删除</el-button>
            </div>
            <el-button type="primary" size="small" @click="addStep">添加步骤</el-button>
          </div>
        </template>

        <!-- 员工详情 -->
        <template v-if="currentType === 'personnel' && currentItem">
          <el-divider content-position="left">基本信息</el-divider>
          
          <el-descriptions v-if="!isEditing" :column="2" border>
            <el-descriptions-item label="姓名">{{ currentItem.name }}</el-descriptions-item>
            <el-descriptions-item label="职位">{{ currentItem.role }}</el-descriptions-item>
            <el-descriptions-item label="部门">{{ currentItem.department }}</el-descriptions-item>
          </el-descriptions>

          <el-form v-else :model="editForm" label-width="120px">
            <el-form-item label="姓名">
              <el-input v-model="editForm.name" />
            </el-form-item>
            <el-form-item label="职位">
              <el-input v-model="editForm.role" />
            </el-form-item>
            <el-form-item label="部门">
              <el-input v-model="editForm.department" />
            </el-form-item>
          </el-form>

          <!-- 资源占用可视化 -->
          <el-divider content-position="left">资源占用情况</el-divider>
          <div class="resource-utilization">
            <div class="utilization-progress">
              <span class="utilization-label">
                当前占用: {{ calculateUsedAmount(currentItem.allocations) }} / 总量: 1 (人)
              </span>
              <el-progress
                :percentage="calculateUsagePercentage(currentItem.allocations, 1)"
                :status="calculateUsagePercentage(currentItem.allocations, 1) > 100 ? 'exception' : 'success'"
              />
            </div>
            
            <div class="allocation-details">
              <h4>占用明细</h4>
              <el-table :data="currentItem.allocations || []" size="small" border>
                <el-table-column prop="activity_name" label="占用活动" />
                <el-table-column prop="amount" label="占用数量" width="100" />
                <el-table-column prop="duration" label="占用时长(分钟)" width="150" />
              </el-table>
              <el-empty v-if="!currentItem.allocations || currentItem.allocations.length === 0" description="暂无占用记录" />
            </div>
          </div>
        </template>

        <!-- 设备详情 -->
        <template v-if="currentType === 'equipment' && currentItem">
          <el-divider content-position="left">基本信息</el-divider>
          
          <el-descriptions v-if="!isEditing" :column="2" border>
            <el-descriptions-item label="名称">{{ currentItem.name }}</el-descriptions-item>
            <el-descriptions-item label="规格">{{ currentItem.specification }}</el-descriptions-item>
            <el-descriptions-item label="总量">{{ currentItem.quantity }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="getStatusTagType(currentItem.status)">
                {{ getStatusText(currentItem.status) }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <el-form v-else :model="editForm" label-width="120px">
            <el-form-item label="名称">
              <el-input v-model="editForm.name" />
            </el-form-item>
            <el-form-item label="规格">
              <el-input v-model="editForm.specification" />
            </el-form-item>
            <el-form-item label="总量">
              <el-input-number v-model="editForm.quantity" :min="0" />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="editForm.status">
                <el-option label="可用" value="available" />
                <el-option label="维护中" value="maintenance" />
                <el-option label="故障" value="broken" />
              </el-select>
            </el-form-item>
          </el-form>

          <!-- 资源占用可视化 -->
          <el-divider content-position="left">资源占用情况</el-divider>
          <div class="resource-utilization">
            <div class="utilization-progress">
              <span class="utilization-label">
                当前占用: {{ calculateUsedAmount(currentItem.allocations) }} / 总量: {{ currentItem.quantity }}
              </span>
              <el-progress
                :percentage="calculateUsagePercentage(currentItem.allocations, currentItem.quantity)"
                :status="calculateUsagePercentage(currentItem.allocations, currentItem.quantity) > 100 ? 'exception' : 'success'"
              />
            </div>
            
            <div class="allocation-details">
              <h4>占用明细</h4>
              <el-table :data="currentItem.allocations || []" size="small" border>
                <el-table-column prop="activity_name" label="占用活动" />
                <el-table-column prop="amount" label="占用数量" width="100" />
                <el-table-column prop="duration" label="占用时长(分钟)" width="150" />
              </el-table>
              <el-empty v-if="!currentItem.allocations || currentItem.allocations.length === 0" description="暂无占用记录" />
            </div>
          </div>
        </template>

        <!-- 原料详情 -->
        <template v-if="currentType === 'material' && currentItem">
          <el-divider content-position="left">基本信息</el-divider>
          
          <el-descriptions v-if="!isEditing" :column="2" border>
            <el-descriptions-item label="名称">{{ currentItem.name }}</el-descriptions-item>
            <el-descriptions-item label="规格">{{ currentItem.specification }}</el-descriptions-item>
            <el-descriptions-item label="库存总量">{{ currentItem.quantity }}</el-descriptions-item>
            <el-descriptions-item label="单位">{{ currentItem.unit }}</el-descriptions-item>
          </el-descriptions>

          <el-form v-else :model="editForm" label-width="120px">
            <el-form-item label="名称">
              <el-input v-model="editForm.name" />
            </el-form-item>
            <el-form-item label="规格">
              <el-input v-model="editForm.specification" />
            </el-form-item>
            <el-form-item label="库存总量">
              <el-input-number v-model="editForm.quantity" :min="0" />
            </el-form-item>
            <el-form-item label="单位">
              <el-input v-model="editForm.unit" />
            </el-form-item>
          </el-form>

          <!-- 资源占用可视化 -->
          <el-divider content-position="left">资源占用情况</el-divider>
          <div class="resource-utilization">
            <div class="utilization-progress">
              <span class="utilization-label">
                当前占用: {{ calculateUsedAmount(currentItem.allocations) }} / 总量: {{ currentItem.quantity }} {{ currentItem.unit }}
              </span>
              <el-progress
                :percentage="calculateUsagePercentage(currentItem.allocations, currentItem.quantity)"
                :status="calculateUsagePercentage(currentItem.allocations, currentItem.quantity) > 100 ? 'exception' : 'success'"
              />
            </div>
            
            <div class="allocation-details">
              <h4>占用明细</h4>
              <el-table :data="currentItem.allocations || []" size="small" border>
                <el-table-column prop="activity_name" label="占用活动" />
                <el-table-column prop="amount" label="占用数量" width="100" />
                <el-table-column prop="duration" label="占用时长(分钟)" width="150" />
              </el-table>
              <el-empty v-if="!currentItem.allocations || currentItem.allocations.length === 0" description="暂无占用记录" />
            </div>
          </div>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

// 类型定义
interface Activity {
  id: string
  name: string
  description: string
  sop_steps: string[]
  estimated_duration: number
  status: string
}

interface Personnel {
  id: string
  name: string
  role: string
  department: string
  allocations?: Allocation[]
}

interface Equipment {
  id: string
  name: string
  specification: string
  quantity: number
  status: string
  allocations?: Allocation[]
}

interface Material {
  id: string
  name: string
  specification: string
  quantity: number
  unit: string
  allocations?: Allocation[]
}

interface Allocation {
  activity_name: string
  amount: number
  duration: number
}

// 状态变量
const activeTab = ref('activities')
const drawerVisible = ref(false)
const isEditing = ref(false)
const currentType = ref<'activity' | 'personnel' | 'equipment' | 'material' | null>(null)
const currentItem = ref<any>(null)
const editForm = ref<any>({})

// Mock 数据
const activities = ref<Activity[]>([
  {
    id: 'A001',
    name: '牛奶接收',
    description: '接收并验收原奶',
    sop_steps: ['检查温度', '检查质量', '称重记录', '转移至储罐'],
    estimated_duration: 30,
    status: 'completed'
  },
  {
    id: 'A002',
    name: '巴氏杀菌',
    description: '对牛奶进行巴氏杀菌处理',
    sop_steps: ['加热至72℃', '保持15秒', '快速冷却', '质检'],
    estimated_duration: 45,
    status: 'in_progress'
  },
  {
    id: 'A003',
    name: '灌装',
    description: '将处理后的牛奶灌装到包装容器中',
    sop_steps: ['准备包装材料', '消毒灌装设备', '灌装', '封口'],
    estimated_duration: 60,
    status: 'pending'
  },
  {
    id: 'A004',
    name: '质量检测',
    description: '对成品进行质量检测',
    sop_steps: ['抽样', '微生物检测', '营养成分检测', '记录结果'],
    estimated_duration: 90,
    status: 'pending'
  }
])

const personnel = ref<Personnel[]>([
  {
    id: 'P001',
    name: '张三',
    role: '生产主管',
    department: '生产部',
    allocations: [
      { activity_name: '牛奶接收', amount: 0.5, duration: 30 },
      { activity_name: '巴氏杀菌', amount: 0.5, duration: 45 }
    ]
  },
  {
    id: 'P002',
    name: '李四',
    role: '质检员',
    department: '质检部',
    allocations: [
      { activity_name: '质量检测', amount: 1, duration: 90 }
    ]
  },
  {
    id: 'P003',
    name: '王五',
    role: '操作员',
    department: '生产部',
    allocations: [
      { activity_name: '灌装', amount: 0.8, duration: 60 }
    ]
  }
])

const equipment = ref<Equipment[]>([
  {
    id: 'E001',
    name: '巴氏杀菌机',
    specification: '2000L/H',
    quantity: 2,
    status: 'available',
    allocations: [
      { activity_name: '巴氏杀菌', amount: 1, duration: 45 }
    ]
  },
  {
    id: 'E002',
    name: '灌装机',
    specification: '5000瓶/H',
    quantity: 3,
    status: 'available',
    allocations: [
      { activity_name: '灌装', amount: 2, duration: 60 }
    ]
  },
  {
    id: 'E003',
    name: '储罐',
    specification: '5000L',
    quantity: 5,
    status: 'available',
    allocations: [
      { activity_name: '牛奶接收', amount: 2, duration: 30 },
      { activity_name: '巴氏杀菌', amount: 1, duration: 45 }
    ]
  }
])

const materials = ref<Material[]>([
  {
    id: 'M001',
    name: '原奶',
    specification: 'A级',
    quantity: 10000,
    unit: 'L',
    allocations: [
      { activity_name: '牛奶接收', amount: 2000, duration: 30 },
      { activity_name: '巴氏杀菌', amount: 3000, duration: 45 }
    ]
  },
  {
    id: 'M002',
    name: '包装瓶',
    specification: '1L装',
    quantity: 20000,
    unit: '个',
    allocations: [
      { activity_name: '灌装', amount: 5000, duration: 60 }
    ]
  },
  {
    id: 'M003',
    name: '瓶盖',
    specification: '标准型',
    quantity: 20000,
    unit: '个',
    allocations: [
      { activity_name: '灌装', amount: 5000, duration: 60 }
    ]
  }
])

// 计算属性
const drawerTitle = computed(() => {
  if (!currentItem.value) return ''
  const typeMap = {
    activity: '活动详情',
    personnel: '员工详情',
    equipment: '设备详情',
    material: '原料详情'
  }
  return typeMap[currentType.value as keyof typeof typeMap] || ''
})

// 方法
function handleRefresh() {
  ElMessage.success('数据已刷新')
  // 这里可以调用 API 获取最新数据
  fetchData()
}

function fetchData() {
  // Mock API 调用
  console.log('正在获取数据...')
}

function handleActivityRowClick(row: Activity) {
  currentType.value = 'activity'
  currentItem.value = { ...row }
  drawerVisible.value = true
  isEditing.value = false
}

function handlePersonnelRowClick(row: Personnel) {
  currentType.value = 'personnel'
  currentItem.value = { ...row }
  drawerVisible.value = true
  isEditing.value = false
}

function handleEquipmentRowClick(row: Equipment) {
  currentType.value = 'equipment'
  currentItem.value = { ...row }
  drawerVisible.value = true
  isEditing.value = false
}

function handleMaterialRowClick(row: Material) {
  currentType.value = 'material'
  currentItem.value = { ...row }
  drawerVisible.value = true
  isEditing.value = false
}

function handleEdit() {
  isEditing.value = true
  editForm.value = JSON.parse(JSON.stringify(currentItem.value))
}

function handleSave() {
  // 验证并保存数据
  updateData(editForm.value)
  
  // 更新当前项
  currentItem.value = { ...editForm.value }
  
  // 更新列表数据
  switch (currentType.value) {
    case 'activity':
      const activityIndex = activities.value.findIndex(a => a.id === editForm.value.id)
      if (activityIndex !== -1) {
        activities.value[activityIndex] = { ...editForm.value }
      }
      break
    case 'personnel':
      const personnelIndex = personnel.value.findIndex(p => p.id === editForm.value.id)
      if (personnelIndex !== -1) {
        personnel.value[personnelIndex] = { ...editForm.value }
      }
      break
    case 'equipment':
      const equipmentIndex = equipment.value.findIndex(e => e.id === editForm.value.id)
      if (equipmentIndex !== -1) {
        equipment.value[equipmentIndex] = { ...editForm.value }
      }
      break
    case 'material':
      const materialIndex = materials.value.findIndex(m => m.id === editForm.value.id)
      if (materialIndex !== -1) {
        materials.value[materialIndex] = { ...editForm.value }
      }
      break
  }
  
  isEditing.value = false
  ElMessage.success('保存成功')
}

function handleCancel() {
  isEditing.value = false
  editForm.value = {}
}

function handleDrawerClose(done: () => void) {
  if (isEditing.value) {
    ElMessage.warning('请先保存或取消编辑')
    return
  }
  done()
}

function updateData(data: any) {
  // Mock API 调用
  console.log('正在更新数据:', data)
}

function addStep() {
  if (!editForm.value.sop_steps) {
    editForm.value.sop_steps = []
  }
  editForm.value.sop_steps.push('')
}

function removeStep(index: number) {
  editForm.value.sop_steps.splice(index, 1)
}

function getStatusTagType(status: string) {
  const typeMap: Record<string, any> = {
    pending: 'info',
    in_progress: 'warning',
    completed: 'success',
    available: 'success',
    maintenance: 'warning',
    broken: 'danger'
  }
  return typeMap[status] || 'info'
}

function getStatusText(status: string) {
  const textMap: Record<string, string> = {
    pending: '未开始',
    in_progress: '进行中',
    completed: '已完成',
    available: '可用',
    maintenance: '维护中',
    broken: '故障'
  }
  return textMap[status] || status
}

function calculateUsedAmount(allocations?: Allocation[]): number {
  if (!allocations || allocations.length === 0) return 0
  return allocations.reduce((sum, alloc) => sum + alloc.amount, 0)
}

function calculateUsagePercentage(allocations: Allocation[] | undefined, total: number): number {
  if (!total || total === 0) return 0
  const used = calculateUsedAmount(allocations)
  return Math.round((used / total) * 100)
}
</script>

<style scoped>
.data-panel {
  padding: 20px;
  background: #f5f7fa;
  min-height: 100vh;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.panel-header h2 {
  margin: 0;
  color: #303133;
  font-size: 24px;
}

.data-tabs {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.drawer-content {
  padding: 0 20px 20px;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #e4e7ed;
}

.sop-steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sop-tag {
  padding: 10px 15px;
  font-size: 14px;
}

.sop-edit {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sop-item {
  display: flex;
  gap: 10px;
  align-items: center;
}

.resource-utilization {
  margin-top: 20px;
}

.utilization-progress {
  margin-bottom: 20px;
}

.utilization-label {
  display: block;
  margin-bottom: 10px;
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.allocation-details h4 {
  margin: 20px 0 10px;
  color: #303133;
  font-size: 16px;
  font-weight: 500;
}

:deep(.el-table__row) {
  cursor: pointer;
  transition: background-color 0.3s;
}

:deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}

:deep(.el-divider__text) {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

:deep(.el-descriptions) {
  margin-top: 10px;
}

:deep(.el-form) {
  margin-top: 10px;
}
</style>
