<template>
  <div class="data-panel">
    <div class="panel-header">
      <h2>数据管理面板</h2>
      <el-button type="primary" @click="handleRefresh">刷新数据</el-button>
    </div>

    <el-tabs v-model="activeTab" class="data-tabs">
      <!-- 活动标签页 -->
      <el-tab-pane label="活动" name="activities">
        <!-- 分流程视图选择器 -->
        <div class="process-selector">
          <el-select v-model="selectedDomain" placeholder="选择流程域" style="width: 200px; margin-right: 10px">
            <el-option label="乳制品生产" value="dairy_production" />
            <el-option label="质量检测" value="quality_control" />
          </el-select>
          <el-select v-model="selectedProcessId" placeholder="选择流程实例" style="width: 200px; margin-right: 10px">
            <el-option label="生产批次-001" value="batch_001" />
            <el-option label="生产批次-002" value="batch_002" />
          </el-select>
          <el-button type="primary" @click="loadProcessActivities">加载活动</el-button>
        </div>

        <!-- 批量状态控制 -->
        <div class="batch-status-control" v-if="activities.length > 0">
          <span style="margin-right: 10px">批量状态控制：</span>
          <el-button-group>
            <el-button size="small" @click="batchUpdateStatus('pending')">待开始</el-button>
            <el-button size="small" type="warning" @click="batchUpdateStatus('in_progress')">进行中</el-button>
            <el-button size="small" type="success" @click="batchUpdateStatus('completed')">已完成</el-button>
          </el-button-group>
        </div>

        <el-table
          :data="activities"
          style="width: 100%; margin-top: 15px"
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
          <el-table-column label="合规状态" width="100">
            <template #default="scope">
              <span class="compliance-indicator">
                <span v-if="scope.row.compliance_status === 'compliant'" style="color: #67C23A">✓</span>
                <span v-else-if="scope.row.compliance_status === 'partial'" style="color: #E6A23C">⚠</span>
                <span v-else style="color: #F56C6C">✗</span>
              </span>
            </template>
          </el-table-column>
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
          <el-table-column prop="specification" label="设备种类" width="150" />
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
        <!-- 库存预警面板 -->
        <el-card class="inventory-forecast-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>原料库存预警面板</span>
              <el-button type="primary" size="small" @click="calculateInventoryForecast">刷新预测</el-button>
            </div>
          </template>
          <div class="forecast-list">
            <div v-for="forecast in inventoryForecasts" :key="forecast.material_model" 
                 class="forecast-item"
                 :class="getForecastClass(forecast.days_remaining)">
              <div class="forecast-header">
                <h4>{{ forecast.material_model }}</h4>
                <span class="forecast-status" :class="getForecastStatusClass(forecast.days_remaining)">
                  {{ getForecastStatusIcon(forecast.days_remaining) }}
                </span>
              </div>
              <div class="forecast-details">
                <p>库存：{{ forecast.current_stock }} {{ forecast.unit }}</p>
                <p>当前消耗：{{ forecast.consumption_rate }} {{ forecast.unit }}/天</p>
                <p class="forecast-days">预计可用：<strong>{{ forecast.days_remaining }}</strong> 天</p>
              </div>
            </div>
            <el-empty v-if="inventoryForecasts.length === 0" description="暂无预测数据，请先加载进行中的活动" />
          </div>
        </el-card>

        <el-table
          :data="materials"
          style="width: 100%; margin-top: 15px"
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

      <!-- 风险标签页 -->
      <el-tab-pane label="风险" name="risks">
        <el-table :data="riskTableRows" style="width: 100%" stripe>
          <el-table-column
            :label="isScopedRiskView ? '活动名称' : '流程域/流程'"
            prop="name"
            min-width="220"
            show-overflow-tooltip
          />
          <el-table-column label="风险数" prop="riskCount" width="120" />
          <el-table-column label="最短可运行时间" width="180">
            <template #default="scope">
              {{ formatRunnableDays(scope.row.minRunnableDays) }}
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="riskTableRows.length === 0" description="暂无风险数据" />
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
          <el-button v-if="!isEditing && currentType === 'activity'" 
                     type="success" 
                     @click="handleStartTask"
                     :disabled="currentItem.status !== 'pending'">
            开始任务
          </el-button>
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

          <!-- 资源需求配置（仅查看模式） -->
          <template v-if="!isEditing && currentItem.activityDetails">
            <el-divider content-position="left">资源需求定义</el-divider>
            <div class="resource-requirements">
              <div v-if="currentItem.activityDetails.material_requirements?.length > 0">
                <h4>原料需求（按型号）：</h4>
                <ul>
                  <li v-for="(req, idx) in currentItem.activityDetails.material_requirements" :key="idx">
                    {{ req.material_model }}：{{ req.consumption_rate_per_day }} {{ req.unit }}/天
                  </li>
                </ul>
              </div>
              
              <div v-if="currentItem.activityDetails.personnel_requirements?.length > 0">
                <h4>人员需求：</h4>
                <ul>
                  <li v-for="(req, idx) in currentItem.activityDetails.personnel_requirements" :key="idx">
                    {{ req.role }}：{{ req.count }} 人
                  </li>
                </ul>
              </div>
              
              <div v-if="currentItem.activityDetails.equipment_requirements?.length > 0">
                <h4>设备需求（按型号）：</h4>
                <ul>
                  <li v-for="(req, idx) in currentItem.activityDetails.equipment_requirements" :key="idx">
                    {{ req.equipment_model }}：{{ req.count }} 台
                  </li>
                </ul>
              </div>
            </div>

            <el-divider content-position="left">实际分配情况</el-divider>
            <div class="actual-allocations">
              <div v-if="currentItem.activityDetails.actual_allocations">
                <!-- 原料分配 -->
                <div v-if="currentItem.activityDetails.actual_allocations.materials?.length > 0">
                  <h4>原料分配（资产实例）：</h4>
                  <ul class="allocation-list">
                    <li v-for="(mat, idx) in currentItem.activityDetails.actual_allocations.materials" :key="idx">
                      <span class="status-icon" :class="getResourceStatus('material', mat, currentItem.activityDetails.material_requirements)">
                        {{ getResourceStatusIcon('material', mat, currentItem.activityDetails.material_requirements) }}
                      </span>
                      {{ mat.name }}：已分配 {{ mat.allocated_rate }} {{ mat.unit }}/天
                    </li>
                  </ul>
                </div>

                <!-- 人员分配 -->
                <div v-if="currentItem.activityDetails.actual_allocations.personnel?.length > 0">
                  <h4>人员分配：</h4>
                  <ul class="allocation-list">
                    <li v-for="(person, idx) in currentItem.activityDetails.actual_allocations.personnel" :key="idx">
                      <span class="status-icon compliant">✓</span>
                      {{ person.role }}：{{ person.name }}
                    </li>
                  </ul>
                </div>

                <!-- 设备分配 -->
                <div v-if="currentItem.activityDetails.actual_allocations.equipment?.length > 0">
                  <h4>设备分配（资产实例）：</h4>
                  <div v-for="(model, equipmentModel) in groupEquipmentByModel(currentItem.activityDetails.actual_allocations.equipment)" :key="equipmentModel">
                    <div class="equipment-group">
                      <span class="status-icon" :class="getEquipmentStatus(equipmentModel, model.length, currentItem.activityDetails.equipment_requirements)">
                        {{ getEquipmentStatusIcon(equipmentModel, model.length, currentItem.activityDetails.equipment_requirements) }}
                      </span>
                      <strong>{{ equipmentModel }}：</strong>
                      <span v-for="(eq, idx) in model" :key="idx">
                        {{ eq.name }}<span v-if="idx < model.length - 1">, </span>
                      </span>
                      <span class="count-badge">({{ model.length }}/{{ getRequiredCount(equipmentModel, currentItem.activityDetails.equipment_requirements) }} 台)</span>
                    </div>
                  </div>
                </div>

                <el-empty v-if="!currentItem.activityDetails.actual_allocations.materials?.length && 
                              !currentItem.activityDetails.actual_allocations.personnel?.length && 
                              !currentItem.activityDetails.actual_allocations.equipment?.length" 
                          description="暂无资源分配" />
              </div>
            </div>
          </template>
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
            <el-descriptions-item label="设备种类">{{ currentItem.specification }}</el-descriptions-item>
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
            <el-form-item label="设备种类">
              <el-input v-model="editForm.specification" />
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
                当前状态: {{ currentItem.status === 'in_use' ? '被占用' : '空闲' }}
              </span>
              <el-progress
                :percentage="currentItem.status === 'in_use' ? 100 : 0"
                :status="currentItem.status === 'in_use' ? 'exception' : 'success'"
              />
            </div>
            
            <div class="allocation-details">
              <h4>占用明细</h4>
              <el-table :data="currentItem.allocations || []" size="small" border>
                <el-table-column prop="activity_name" label="占用活动" />
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
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getActivities, batchUpdateStatus as batchUpdateStatusApi, getActivityDetails, updateActivity } from '@/api/activity'
import { getAssets } from '@/api/asset'
import { getPersonnel } from '@/api/personnel'
import type { ActivityDetails, ComplianceCheckResult } from '@/types'

interface RiskItem {
  risk_type: 'material_shortage' | 'allocation_shortage' | 'upcoming_absence'
  level: 'high' | 'medium' | 'low'
  activity_name: string
  message: string
  domain?: string | null
  process_id?: string | null
  runnable_days?: number | null
}

const props = withDefaults(defineProps<{
  risks?: RiskItem[]
  domain?: string
  processId?: string
}>(), {
  risks: () => []
})

// 类型定义
interface Activity {
  id: string
  name: string
  description: string
  sop_steps: string[]
  estimated_duration: number
  status: string
  compliance_status?: 'compliant' | 'partial' | 'non_compliant'
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

// 分流程选择器状态
const selectedDomain = ref('dairy_production')
const selectedProcessId = ref('batch_001')

// 库存预测数据
const inventoryForecasts = ref<any[]>([])

// 数据列表（从API获取）
const activities = ref<Activity[]>([])
const personnel = ref<Personnel[]>([])
const equipment = ref<Equipment[]>([])
const materials = ref<Material[]>([])

const isScopedRiskView = computed(() => !!props.domain || !!props.processId)

const riskTableRows = computed(() => {
  const source = props.risks || []
  const grouped = new Map<string, { name: string; riskCount: number; minRunnableDays: number | null }>()

  for (const item of source) {
    const runnable =
      typeof item.runnable_days === 'number' && Number.isFinite(item.runnable_days)
        ? item.runnable_days
        : null

    if (isScopedRiskView.value) {
      const key = item.activity_name || '未知活动'
      const existing = grouped.get(key) || { name: key, riskCount: 0, minRunnableDays: null }
      existing.riskCount += 1
      if (runnable !== null) {
        existing.minRunnableDays =
          existing.minRunnableDays === null ? runnable : Math.min(existing.minRunnableDays, runnable)
      }
      grouped.set(key, existing)
      continue
    }

    const groupName = item.process_id
      ? `${item.domain || '-'} / ${item.process_id}`
      : (item.domain || '未知流程域')
    const key = `${item.domain || ''}::${item.process_id || ''}`
    const existing = grouped.get(key) || { name: groupName, riskCount: 0, minRunnableDays: null }
    existing.riskCount += 1
    if (runnable !== null) {
      existing.minRunnableDays =
        existing.minRunnableDays === null ? runnable : Math.min(existing.minRunnableDays, runnable)
    }
    grouped.set(key, existing)
  }

  return Array.from(grouped.values()).sort((a, b) => b.riskCount - a.riskCount)
})

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
  fetchData()
}

async function fetchData() {
  try {
    // 并行加载所有数据
    await Promise.all([
      loadPersonnel(),
      loadEquipment(),
      loadMaterials()
    ])
    ElMessage.success('数据已刷新')
  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败')
  }
}

// 加载人员数据
async function loadPersonnel() {
  try {
    const data = await getPersonnel()
    personnel.value = data.map((p: any) => ({
      id: p.id || p._id,
      name: p.name,
      role: p.role,
      department: p.responsibility || '未知部门',
      allocations: []
    }))
  } catch (error) {
    console.error('加载人员数据失败:', error)
  }
}

// 加载设备数据
async function loadEquipment() {
  try {
    const data = await getAssets({ asset_type: 'equipment' })
    equipment.value = data.map((asset: any) => ({
      id: asset.id || asset._id,
      name: asset.name,
      model: asset.model,
      specification: asset.specification || '',
      status: asset.status || 'available',
      allocations: []
    }))
  } catch (error) {
    console.error('加载设备数据失败:', error)
  }
}

// 加载原料数据
async function loadMaterials() {
  try {
    const data = await getAssets({ asset_type: 'material' })
    materials.value = data.map((asset: any) => ({
      id: asset.id || asset._id,
      name: asset.name,
      specification: asset.specification || '',
      quantity: asset.quantity || 0,
      unit: asset.unit || '',
      allocations: []
    }))
  } catch (error) {
    console.error('加载原料数据失败:', error)
  }
}

// 组件挂载时加载数据
onMounted(() => {
  fetchData()
})

// 加载流程活动
async function loadProcessActivities() {
  if (!selectedDomain.value || !selectedProcessId.value) {
    ElMessage.warning('请选择流程域和流程实例')
    return
  }
  
  try {
    const data = await getActivities({
      domain: selectedDomain.value,
      process_id: selectedProcessId.value
    })
    activities.value = data.map((act: any) => ({
      ...act,
      compliance_status: 'compliant' // 默认合规，实际应从详情API获取
    }))
    ElMessage.success(`加载了 ${data.length} 个活动`)
  } catch (error) {
    console.error('加载活动失败:', error)
    ElMessage.error('加载活动失败')
  }
}

// 批量更新状态
async function batchUpdateStatus(newStatus: string) {
  if (!selectedDomain.value || !selectedProcessId.value) {
    ElMessage.warning('请先选择流程')
    return
  }
  
  const statusText = {
    'pending': '待开始',
    'in_progress': '进行中',
    'completed': '已完成'
  }[newStatus] || newStatus
  
  try {
    await ElMessageBox.confirm(
      `确定将当前流程的所有活动状态更新为"${statusText}"吗？`,
      '批量状态更新',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await batchUpdateStatusApi(selectedDomain.value, selectedProcessId.value, newStatus)
    ElMessage.success('批量更新成功')
    await loadProcessActivities() // 重新加载数据
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('批量更新失败:', error)
      ElMessage.error('批量更新失败')
    }
  }
}

// 合规性卫士：开始任务
async function handleStartTask() {
  if (!currentItem.value || !currentItem.value.id) {
    ElMessage.warning('无效的活动')
    return
  }
  
  try {
    // 获取活动详情（包含需求和实际分配）
    const details: ActivityDetails = await getActivityDetails(currentItem.value.id)
    
    // 执行合规性校验
    const checkResult = await checkCompliance(details)
    
    if (checkResult.is_compliant) {
      // 合规，直接开始任务
      await updateActivity(currentItem.value.id, { status: 'in_progress' })
      ElMessage.success('任务已开始')
      currentItem.value.status = 'in_progress'
    } else {
      // 不合规，显示缺失资源并询问是否强制开始
      const missingText = checkResult.missing_resources.map(m => {
        let text = `- ${m.resource}：需要 ${m.required}，实际分配 ${m.actual}`
        if (m.available && m.available.length > 0) {
          text += `\n  可用闲置实例：${m.available.join(', ')}`
        }
        return text
      }).join('\n')
      
      await ElMessageBox.confirm(
        `资源配置不合规，缺少以下资产：\n\n${missingText}\n\n是否强制开始任务？`,
        '资源合规性检查',
        {
          confirmButtonText: '强制开始',
          cancelButtonText: '取消',
          type: 'warning',
          dangerouslyUseHTMLString: false
        }
      )
      
      // 用户确认强制开始
      await updateActivity(currentItem.value.id, { status: 'in_progress' })
      ElMessage.success('任务已强制开始')
      currentItem.value.status = 'in_progress'
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('开始任务失败:', error)
      ElMessage.error('开始任务失败')
    }
  }
}

// 合规性校验函数
async function checkCompliance(details: ActivityDetails): Promise<ComplianceCheckResult> {
  const missing: any[] = []
  
  // 检查原料
  for (const req of details.material_requirements || []) {
    const allocated = details.actual_allocations.materials.find(
      m => m.name === req.material_model || m.name.includes(req.material_model)
    )
    const actualRate = allocated?.allocated_rate || 0
    
    if (actualRate < req.consumption_rate_per_day) {
      missing.push({
        type: 'material',
        resource: req.material_model,
        required: `${req.consumption_rate_per_day} ${req.unit}/天`,
        actual: `${actualRate} ${req.unit}/天`
      })
    }
  }
  
  // 检查人员
  const personnelByRole: Record<string, number> = {}
  details.actual_allocations.personnel.forEach(p => {
    personnelByRole[p.role] = (personnelByRole[p.role] || 0) + 1
  })
  
  for (const req of details.personnel_requirements || []) {
    const actualCount = personnelByRole[req.role] || 0
    if (actualCount < req.count) {
      missing.push({
        type: 'personnel',
        resource: req.role,
        required: `${req.count} 人`,
        actual: `${actualCount} 人`
      })
    }
  }
  
  // 检查设备
  const equipmentByModel: Record<string, number> = {}
  details.actual_allocations.equipment.forEach(e => {
    equipmentByModel[e.model] = (equipmentByModel[e.model] || 0) + 1
  })
  
  for (const req of details.equipment_requirements || []) {
    const actualCount = equipmentByModel[req.equipment_model] || 0
    if (actualCount < req.count) {
      // 查询可用的闲置实例
      try {
        const availableAssets = await getAssets({
          asset_type: 'equipment',
          model: req.equipment_model,
          status: 'idle'
        })
        const availableNames = availableAssets.map(a => a.name)
        
        missing.push({
          type: 'equipment',
          resource: `${req.equipment_model}（型号）`,
          required: `${req.count} 台`,
          actual: `${actualCount} 台`,
          available: availableNames
        })
      } catch (error) {
        missing.push({
          type: 'equipment',
          resource: `${req.equipment_model}（型号）`,
          required: `${req.count} 台`,
          actual: `${actualCount} 台`
        })
      }
    }
  }
  
  return {
    is_compliant: missing.length === 0,
    missing_resources: missing
  }
}

async function handleActivityRowClick(row: Activity) {
  currentType.value = 'activity'
  currentItem.value = { ...row }
  
  // 加载活动详细信息（包含需求和分配）
  try {
    const details = await getActivityDetails(row.id!)
    currentItem.value.activityDetails = details
  } catch (error) {
    console.error('加载活动详情失败:', error)
  }
  
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

function formatRunnableDays(days: number | null) {
  if (days === null || days === undefined) return '无限制'
  return `${days.toFixed(1)} 天`
}

// 按型号分组设备
function groupEquipmentByModel(equipment: any[]) {
  const grouped: Record<string, any[]> = {}
  equipment.forEach(eq => {
    if (!grouped[eq.model]) {
      grouped[eq.model] = []
    }
    grouped[eq.model].push(eq)
  })
  return grouped
}

// 获取资源状态
function getResourceStatus(type: string, resource: any, requirements: any[]) {
  if (type === 'material') {
    const req = requirements.find(r => r.material_model === resource.name || resource.name.includes(r.material_model))
    if (!req) return 'unknown'
    if (resource.allocated_rate >= req.consumption_rate_per_day) return 'compliant'
    if (resource.allocated_rate > 0) return 'partial'
    return 'non-compliant'
  }
  return 'compliant'
}

function getResourceStatusIcon(type: string, resource: any, requirements: any[]) {
  const status = getResourceStatus(type, resource, requirements)
  if (status === 'compliant') return '✓'
  if (status === 'partial') return '⚠'
  return '✗'
}

// 获取设备合规状态
function getEquipmentStatus(model: string, actualCount: number, requirements: any[]) {
  const req = requirements.find(r => r.equipment_model === model)
  if (!req) return 'unknown'
  if (actualCount >= req.count) return 'compliant'
  if (actualCount > 0) return 'partial'
  return 'non-compliant'
}

function getEquipmentStatusIcon(model: string, actualCount: number, requirements: any[]) {
  const status = getEquipmentStatus(model, actualCount, requirements)
  if (status === 'compliant') return '✓'
  if (status === 'partial') return '⚠'
  return '✗'
}

// 获取需求数量
function getRequiredCount(model: string, requirements: any[]) {
  const req = requirements.find(r => r.equipment_model === model)
  return req ? req.count : 0
}

// 计算库存维持力预测
async function calculateInventoryForecast() {
  try {
    // 获取所有进行中的活动
    const allActivities = await getActivities({
      domain: selectedDomain.value
    })
    
    const inProgressActivities = allActivities.filter(act => act.status === 'in_progress')
    
    if (inProgressActivities.length === 0) {
      ElMessage.warning('当前没有进行中的活动')
      inventoryForecasts.value = []
      return
    }
    
    // 聚合每种原料的消耗速率
    const consumptionByMaterial: Record<string, { rate: number, unit: string }> = {}
    
    for (const activity of inProgressActivities) {
      if (activity.material_requirements) {
        activity.material_requirements.forEach((req: any) => {
          if (!consumptionByMaterial[req.material_model]) {
            consumptionByMaterial[req.material_model] = { rate: 0, unit: req.unit }
          }
          consumptionByMaterial[req.material_model].rate += req.consumption_rate_per_day
        })
      }
    }
    
    // 计算每种原料的维持天数
    const forecasts = []
    for (const [materialModel, consumption] of Object.entries(consumptionByMaterial)) {
      // 从materials数据中找到对应的库存
      const material = materials.value.find(m => m.name === materialModel || m.name.includes(materialModel))
      
      if (material && material.quantity) {
        const daysRemaining = consumption.rate > 0 
          ? Math.floor(material.quantity / consumption.rate)
          : 999
        
        forecasts.push({
          material_model: materialModel,
          current_stock: material.quantity,
          unit: consumption.unit,
          consumption_rate: consumption.rate,
          days_remaining: daysRemaining
        })
      }
    }
    
    // 按剩余天数排序（危急的在前）
    forecasts.sort((a, b) => a.days_remaining - b.days_remaining)
    inventoryForecasts.value = forecasts
    
    ElMessage.success(`已计算 ${forecasts.length} 种原料的库存预测`)
  } catch (error) {
    console.error('计算库存预测失败:', error)
    ElMessage.error('计算库存预测失败')
  }
}

// 获取预测卡片样式
function getForecastClass(days: number) {
  if (days < 7) return 'forecast-critical'
  if (days < 30) return 'forecast-warning'
  return 'forecast-normal'
}

function getForecastStatusClass(days: number) {
  if (days < 7) return 'status-critical'
  if (days < 30) return 'status-warning'
  return 'status-normal'
}

function getForecastStatusIcon(days: number) {
  if (days < 7) return '🔴'
  if (days < 30) return '🟡'
  return '🟢'
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

.process-selector {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
}

.batch-status-control {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
  padding: 10px;
  background: #ecf5ff;
  border-radius: 4px;
  border-left: 3px solid #409EFF;
}

.compliance-indicator {
  font-size: 18px;
  font-weight: bold;
}

.resource-requirements h4,
.actual-allocations h4 {
  margin: 15px 0 10px;
  font-size: 14px;
  font-weight: 600;
  color: #606266;
}

.resource-requirements ul,
.actual-allocations ul {
  margin: 0;
  padding-left: 20px;
}

.resource-requirements li,
.allocation-list li {
  margin: 8px 0;
  list-style: none;
}

.status-icon {
  display: inline-block;
  width: 20px;
  height: 20px;
  line-height: 20px;
  text-align: center;
  border-radius: 50%;
  margin-right: 8px;
  font-weight: bold;
}

.status-icon.compliant {
  color: #67C23A;
  background: #f0f9ff;
}

.status-icon.partial {
  color: #E6A23C;
  background: #fdf6ec;
}

.status-icon.non-compliant {
  color: #F56C6C;
  background: #fef0f0;
}

.equipment-group {
  margin: 10px 0;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.count-badge {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}

/* 库存预警面板样式 */
.inventory-forecast-card {
  margin-bottom: 15px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.forecast-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 15px;
}

.forecast-item {
  padding: 15px;
  border-radius: 8px;
  border: 2px solid;
  transition: all 0.3s;
}

.forecast-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.forecast-normal {
  background: #f0f9ff;
  border-color: #67C23A;
}

.forecast-warning {
  background: #fdf6ec;
  border-color: #E6A23C;
}

.forecast-critical {
  background: #fef0f0;
  border-color: #F56C6C;
}

.forecast-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.forecast-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.forecast-status {
  font-size: 24px;
}

.forecast-details p {
  margin: 5px 0;
  font-size: 14px;
  color: #606266;
}

.forecast-days {
  margin-top: 10px;
  font-size: 15px;
  color: #303133;
}

.forecast-days strong {
  font-size: 20px;
  font-weight: 700;
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
