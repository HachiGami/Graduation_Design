<template>
  <div class="p-5">
    <div class="mb-5 flex flex-wrap items-center justify-between gap-4">
      <div class="flex flex-wrap items-center gap-3">
        <el-input
          v-model="searchQuery"
          placeholder="搜索设备名称/ID"
          clearable
          class="!w-[250px]"
          :prefix-icon="Search"
        />

        <el-select v-model="sortOption" placeholder="排序方式" class="!w-[150px]">
          <el-option label="默认排序" value="default" />
          <el-option label="生产日期(正序)" value="date_asc" />
          <el-option label="生产日期(倒序)" value="date_desc" />
        </el-select>


        <el-select v-model="processFilter" placeholder="流程" clearable class="!w-[150px]">
          <el-option label="全部" value="" />
          <el-option
            v-for="pid in uniqueProcesses"
            :key="pid"
            :label="formatProcessName(pid)"
            :value="pid"
          />
        </el-select>

        <el-select
          v-model="filterSpecification"
          placeholder="请选择设备种类"
          clearable
          class="!w-[180px]"
        >
          <el-option
            v-for="spec in availableSpecifications"
            :key="spec"
            :label="spec"
            :value="spec"
          />
        </el-select>
      </div>
      
      <div class="flex items-center gap-3">
        <el-badge :value="maintenanceEquipments.length" :hidden="maintenanceEquipments.length === 0" class="item">
          <el-button type="danger" @click="isMaintenanceModalVisible = true">
            <el-icon><Tools /></el-icon> 七天检修预警
          </el-button>
        </el-badge>
        <span class="text-slate-300">|</span>
        <el-button type="primary" :icon="Plus" @click="openAddEquipmentDialog">添加设备</el-button>
      </div>
    </div>

    <div class="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div class="flex items-center border-b border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-600">
        <div class="flex flex-1 items-center">设备信息</div>
        <div class="w-[450px]">设备种类</div>
        <div class="w-32 text-right">操作</div>
      </div>
      <div class="p-2" v-loading="loading">
      <el-collapse v-if="processedEquipments.length > 0" v-model="equipmentExpandedNames">
        <EquipmentAccordionItem
          v-for="equipment in processedEquipments"
          :key="equipment._id"
          :equipment="equipment"
          :anchor-id="'equipment-row-' + String(equipment._id || equipment.id || '')"
          :highlighted="highlightedEquipmentId === String(equipment._id || equipment.id || '')"
          @update="fetchEquipments"
          @edit-equipment="openEditEquipmentDialog"
          @close-edit-equipment="editEquipmentDialogVisible = false"
        />
      </el-collapse>
      <el-empty v-else description="暂无匹配的设备数据" />
      </div>
    </div>

    <!-- 添加设备弹窗 -->
    <el-dialog
      v-model="addEquipmentDialogVisible"
      width="500px"
      :show-close="false"
      :align-center="true"
      class="add-entity-dialog add-equipment-dialog rounded-2xl overflow-hidden"
      header-class="!p-0 !m-0 !border-0"
      body-class="!p-0"
      footer-class="!p-0"
    >
      <template #header>
        <div class="flex items-center justify-between border-b border-amber-100 bg-amber-50/50 px-6 py-4">
          <div class="flex items-center space-x-3">
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
              <el-icon :size="18"><Box /></el-icon>
            </div>
            <h3 class="text-lg font-bold tracking-tight text-slate-800">添加设备</h3>
          </div>
          <el-button link class="text-slate-400 hover:text-slate-600" @click="addEquipmentDialogVisible = false">
            <el-icon :size="20"><Close /></el-icon>
          </el-button>
        </div>
      </template>

      <el-form
        ref="addEquipmentFormRef"
        :model="addEquipmentForm"
        :rules="addEquipmentRules"
        label-width="0"
        class="add-equipment-inline-form"
        hide-required-asterisk
      >
        <div class="grid grid-cols-2 gap-5 bg-white p-6">
          <el-form-item prop="name" class="col-span-2 !mb-0">
            <div class="flex w-full flex-col space-y-1.5">
              <label class="text-[13px] font-bold text-slate-700">
                <span class="mr-1 text-red-500">*</span>设备名称
              </label>
              <el-input v-model="addEquipmentForm.name" placeholder="如：灌装机-03" class="custom-input-amber w-full" />
            </div>
          </el-form-item>

          <el-form-item prop="specification" class="!mb-0">
            <div class="flex w-full flex-col space-y-1.5">
              <label class="text-[13px] font-bold text-slate-700">
                <span class="mr-1 text-red-500">*</span>设备种类
              </label>
              <el-input v-model="addEquipmentForm.specification" placeholder="如：灌装设备" class="custom-input-amber w-full" />
            </div>
          </el-form-item>

          <el-form-item class="!mb-0">
            <div class="flex w-full flex-col space-y-1.5">
              <label class="text-[13px] font-bold text-slate-700">
                <span class="mr-1 text-red-500">*</span>单位
              </label>
              <el-input v-model="addEquipmentForm.unit" placeholder="如：台" class="custom-input-amber w-full" />
            </div>
          </el-form-item>

          <div class="col-span-2 flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">生产厂家</label>
            <el-input v-model="addEquipmentForm.manufacturer" placeholder="生产厂家" class="custom-input-amber w-full" />
          </div>

          <div class="col-span-2 flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">生产时间</label>
            <el-date-picker
              v-model="addEquipmentForm.production_date"
              type="date"
              placeholder="选择日期"
              value-format="YYYY-MM-DD"
              class="custom-input-amber equipment-date-picker w-full"
            />
          </div>
        </div>
      </el-form>

      <template #footer>
        <div class="flex justify-end space-x-3 border-t border-slate-100 bg-slate-50 px-6 py-4">
          <button
            type="button"
            class="rounded-xl border border-slate-300 bg-white px-5 py-2 text-sm font-bold text-slate-600 transition-colors hover:bg-slate-50"
            @click="addEquipmentDialogVisible = false"
          >
            取消
          </button>
          <button
            type="button"
            class="rounded-xl bg-amber-500 px-5 py-2 text-sm font-bold text-white shadow-sm transition-colors hover:bg-amber-600"
            :disabled="addEquipmentSubmitting"
            @click="submitAddEquipment"
          >
            {{ addEquipmentSubmitting ? '提交中…' : '确定添加' }}
          </button>
        </div>
      </template>
    </el-dialog>

    <!-- 编辑设备弹窗（与添加弹窗同页挂载，避免子组件内 Teleport 导致样式不生效） -->
    <el-dialog
      v-model="editEquipmentDialogVisible"
      width="500px"
      :show-close="false"
      :align-center="true"
      class="add-entity-dialog add-equipment-dialog rounded-2xl overflow-hidden"
      header-class="!p-0 !m-0 !border-0"
      body-class="!p-0"
      footer-class="!p-0"
    >
      <template #header>
        <div class="flex items-center justify-between border-b border-amber-100 bg-amber-50/50 px-6 py-4">
          <div class="flex items-center space-x-3">
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
              <el-icon :size="18"><Edit /></el-icon>
            </div>
            <h3 class="text-lg font-bold tracking-tight text-slate-800">编辑设备</h3>
          </div>
          <el-button link class="text-slate-400 hover:text-slate-600" @click="editEquipmentDialogVisible = false">
            <el-icon :size="20"><Close /></el-icon>
          </el-button>
        </div>
      </template>

      <div class="bg-white p-6">
        <div class="grid grid-cols-2 gap-5">
          <div class="col-span-2 flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">
              <span class="mr-1 text-red-500">*</span>设备名称
            </label>
            <el-input v-model="editEquipmentForm.name" placeholder="如：巴氏消毒机-001" class="custom-input-amber w-full" />
          </div>

          <div class="col-span-2 flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">
              <span class="mr-1 text-red-500">*</span>设备种类
            </label>
            <el-input v-model="editEquipmentForm.specification" placeholder="如：巴氏消毒机" class="custom-input-amber w-full" />
          </div>

          <div class="col-span-2 flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">生产厂家</label>
            <el-input v-model="editEquipmentForm.manufacturer" placeholder="生产厂家" class="custom-input-amber w-full" />
          </div>

          <div class="col-span-2 flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">生产时间</label>
            <el-date-picker
              v-model="editEquipmentForm.production_date"
              type="date"
              placeholder="选择日期"
              value-format="YYYY-MM-DD"
              class="custom-input-amber equipment-date-picker w-full"
            />
          </div>
        </div>
      </div>

      <template #footer>
        <div class="flex justify-end space-x-3 border-t border-slate-100 bg-slate-50 px-6 py-4">
          <button
            type="button"
            class="rounded-xl border border-slate-300 bg-white px-5 py-2 text-sm font-bold text-slate-600 transition-colors hover:bg-slate-50"
            @click="editEquipmentDialogVisible = false"
          >
            取消
          </button>
          <button
            type="button"
            class="rounded-xl bg-amber-500 px-5 py-2 text-sm font-bold text-white shadow-sm transition-colors hover:bg-amber-600"
            :disabled="editEquipmentSubmitting"
            @click="submitEditEquipment"
          >
            {{ editEquipmentSubmitting ? '提交中…' : '保存' }}
          </button>
        </div>
      </template>
    </el-dialog>

    <!-- 七天检修预警弹窗 -->
    <el-dialog
      v-model="isMaintenanceModalVisible"
      :show-close="false"
      width="680px"
      style="border-radius: 16px; padding: 0; overflow: hidden;"
      header-class="!hidden"
      body-class="!p-0"
      align-center
    >
      <div class="flex max-h-[85vh] min-h-0 flex-col">
        <!-- 弹窗 Header -->
        <div class="px-6 py-4 bg-white border-b border-slate-100 flex items-center justify-between shrink-0">
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 rounded-lg bg-red-100 flex items-center justify-center text-red-600">
              <el-icon :size="18"><WarningFilled /></el-icon>
            </div>
            <h3 class="text-lg font-black text-slate-800 tracking-tight">七天检修预警</h3>
          </div>
          <button @click="isMaintenanceModalVisible = false" class="p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 rounded-lg transition-colors">
            <el-icon :size="20"><Close /></el-icon>
          </button>
        </div>

        <!-- 弹窗 Warning Banner -->
        <div class="bg-red-50/80 border-b border-red-100 p-4 shrink-0 flex items-start">
          <el-icon class="text-red-500 mt-0.5 mr-3 shrink-0" style="animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;" :size="20"><WarningFilled /></el-icon>
          <div class="text-sm font-bold text-red-800 leading-relaxed">
            未来 7 天内共有 <span class="text-red-600 text-base mx-1 font-black">{{ maintenanceWarningList.length }}</span> 台设备需要检修，
            其中 <span class="text-red-600 text-base mx-1 font-black bg-red-200 px-1 rounded">{{ maintenanceWarningList.filter(item => item.affectedActivity).length }}</span> 项生产活动面临设备停机风险，请及时调配资源！
          </div>
        </div>

        <template v-if="groupedEquipmentWarnings.length > 0">
          <div class="flex-1 overflow-y-auto p-6 bg-slate-50 max-h-[60vh]">
            <div class="relative border-l-2 border-slate-200 ml-3 pl-6 space-y-8 pb-4">
              <div v-for="group in groupedEquipmentWarnings" :key="group.days" class="relative">
                <div :class="['absolute -left-[35px] top-1 w-6 h-6 border-2 rounded-full flex items-center justify-center z-10 shadow-sm', group.hasRisk ? 'bg-red-50 border-red-500' : 'bg-white border-slate-300']">
                  <el-icon v-if="group.hasRisk" class="text-red-600" :size="12"><Clock /></el-icon>
                  <div v-else class="w-2 h-2 bg-slate-300 rounded-full"></div>
                </div>

                <div :class="['text-sm font-black mb-3 inline-block px-3 py-1 rounded-lg border shadow-sm flex items-center w-max', group.hasRisk ? 'text-red-600 bg-red-50 border-red-200' : 'text-slate-800 bg-white border-slate-200']">
                  {{ group.days }} 天后 <span v-if="group.hasRisk" class="ml-2 w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                </div>

                <div class="space-y-3">
                  <div v-for="equip in group.items" :key="equip.id" :class="['group flex items-center justify-between p-3.5 bg-white border rounded-xl shadow-sm transition-all', equip.affectedActivity ? 'border-red-200 bg-red-50/30' : 'border-slate-200 hover:border-amber-300 hover:shadow-md']">
                    <div class="flex items-center space-x-3">
                      <div :class="['w-10 h-10 rounded-xl flex items-center justify-center transition-colors', equip.affectedActivity ? 'bg-red-100 text-red-600 border border-red-200' : 'bg-slate-50 border border-slate-100 text-slate-500 group-hover:bg-amber-50 group-hover:text-amber-500']">
                        <el-icon :size="18"><Tools /></el-icon>
                      </div>
                      <div>
                        <div class="text-sm font-black text-slate-800">{{ equip.name }}</div>
                        <div class="text-[11px] font-bold text-slate-400 mt-0.5 uppercase tracking-wider">需执行周期检修</div>
                      </div>
                    </div>
                    <div>
                      <div v-if="!equip.affectedActivity" class="flex items-center px-2.5 py-1 bg-emerald-50 text-emerald-600 border border-emerald-100 rounded-md text-xs font-bold">
                        <el-icon class="mr-1.5" :size="14"><CircleCheck /></el-icon> 无关联活动，安全
                      </div>
                      <div v-else class="flex items-center px-2.5 py-1 bg-red-50 text-red-600 border border-red-200 rounded-md text-xs font-bold shadow-sm">
                        <el-icon class="mr-1.5" :size="14"><WarningFilled /></el-icon> 影响: <span class="ml-1 underline underline-offset-2">{{ equip.affectedActivity }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
        <div v-else class="flex-1 bg-slate-50 p-6">
          <el-empty description="未来 7 天内无检修计划" />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Search,
  Tools,
  Plus,
  Box,
  Close,
  Edit,
  WarningFilled,
  Clock,
  CircleCheck
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import EquipmentAccordionItem from '../components/EquipmentAccordionItem.vue'
import { createResource } from '@/api/resource'

const equipments = ref<any[]>([])
const loading = ref(false)
const route = useRoute()
const router = useRouter()
const equipmentExpandedNames = ref<(string | number)[]>([])
const highlightedEquipmentId = ref('')

const searchQuery = ref('')
const sortOption = ref('default')
const processFilter = ref('')
const filterSpecification = ref('')

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

const addEquipmentDialogVisible = ref(false)
const addEquipmentSubmitting = ref(false)
const addEquipmentFormRef = ref<FormInstance>()
const addEquipmentRules: FormRules = {
  name: [{ required: true, message: '设备名称不能为空', trigger: 'blur' }],
  specification: [{ required: true, message: '请输入或选择设备种类', trigger: 'blur' }]
}

const defaultAddEquipmentForm = () => ({
  name: '',
  type: '设备',
  specification: '',
  supplier: '',
  quantity: 1,
  manufacturer: '',
  production_date: '',
  unit: '台',
  status: 'available'
})

const addEquipmentForm = ref(defaultAddEquipmentForm())

const openAddEquipmentDialog = () => {
  addEquipmentForm.value = defaultAddEquipmentForm()
  addEquipmentDialogVisible.value = true
}

const editEquipmentDialogVisible = ref(false)
const editEquipmentSubmitting = ref(false)
const editingEquipmentId = ref('')
const editEquipmentForm = reactive({
  name: '',
  specification: '',
  manufacturer: '',
  production_date: ''
})

const openEditEquipmentDialog = (equipment: any) => {
  editingEquipmentId.value = String(equipment._id || equipment.id || '')
  editEquipmentForm.name = equipment.name || ''
  editEquipmentForm.specification = equipment.specification || ''
  editEquipmentForm.manufacturer = equipment.manufacturer || ''
  editEquipmentForm.production_date = equipment.production_date || ''
  editEquipmentDialogVisible.value = true
}

const submitEditEquipment = async () => {
  if (!editEquipmentForm.name.trim()) {
    ElMessage.warning('设备名称不能为空')
    return
  }
  if (!editEquipmentForm.specification.trim()) {
    ElMessage.warning('请输入或选择设备种类')
    return
  }
  const id = editingEquipmentId.value
  if (!id) {
    ElMessage.warning('设备 ID 缺失')
    return
  }
  editEquipmentSubmitting.value = true
  try {
    const response = await fetch(`http://localhost:8000/api/resources/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name: editEquipmentForm.name,
        specification: editEquipmentForm.specification,
        manufacturer: editEquipmentForm.manufacturer,
        production_date: editEquipmentForm.production_date
      })
    })

    if (!response.ok) {
      throw new Error('更新失败')
    }

    ElMessage.success('设备信息更新成功')
    editEquipmentDialogVisible.value = false
    await fetchEquipments()
  } catch (error) {
    console.error('Failed to update equipment:', error)
    ElMessage.error('更新失败，请重试')
  } finally {
    editEquipmentSubmitting.value = false
  }
}

const submitAddEquipment = async () => {
  const valid = await addEquipmentFormRef.value?.validate().catch((validationError) => {
    console.warn('设备表单校验失败:', validationError)
    return false
  })
  if (!valid) {
    ElMessage.warning('请检查表单填写是否有误')
    return
  }

  const payload = {
    ...addEquipmentForm.value,
    // 强制注入并归一化，避免资源类型和设备种类丢失
    type: '设备',
    specification: (addEquipmentForm.value.specification || '').trim(),
    // 后端 ResourceCreate 必填字段，表单未展示时给默认值
    supplier: addEquipmentForm.value.supplier || '未填写',
    quantity: typeof addEquipmentForm.value.quantity === 'number' ? addEquipmentForm.value.quantity : 1
  }

  addEquipmentSubmitting.value = true
  try {
    await createResource(payload as any)
    ElMessage.success('设备添加成功')
    addEquipmentDialogVisible.value = false
    await fetchEquipments()
  } catch (error) {
    const err = error as any
    const detail = err?.response?.data?.detail
    const detailText = Array.isArray(detail)
      ? detail.map((item: any) => `${item?.loc?.join?.('.') || ''}: ${item?.msg || ''}`).join('; ')
      : (typeof detail === 'string' ? detail : (err?.message || '未知错误'))
    ElMessage.error(`添加失败: ${detailText}`)
  } finally {
    addEquipmentSubmitting.value = false
  }
}

const handleRouteHighlight = async () => {
  const rawId = route.query.highlightId
  const highlightId = Array.isArray(rawId) ? rawId[0] : rawId
  if (!highlightId) return

  const targetId = String(highlightId)
  const target = equipments.value.find(
    (eq) => String(eq._id || eq.id || '') === targetId
  )
  if (!target) {
    ElMessage.warning('未找到目标设备，可能已被删除')
    highlightedEquipmentId.value = ''
    const nextQuery = { ...route.query } as Record<string, any>
    delete nextQuery.highlightId
    await router.replace({ query: nextQuery })
    return
  }

  searchQuery.value = ''
  sortOption.value = 'default'
  processFilter.value = ''
  filterSpecification.value = ''
  highlightedEquipmentId.value = targetId
  equipmentExpandedNames.value = [target._id || target.id]

  await nextTick()
  const targetEl = document.getElementById(`equipment-row-${targetId}`)
  if (!targetEl) {
    ElMessage.warning('定位失败，请稍后重试')
    return
  }

  targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
  setTimeout(() => {
    highlightedEquipmentId.value = ''
  }, 1800)
  const nextQuery = { ...route.query } as Record<string, any>
  delete nextQuery.highlightId
  await router.replace({ query: nextQuery })
}

const fetchEquipments = async () => {
  loading.value = true
  try {
    const response = await fetch('http://localhost:8000/api/resources?type=设备')
    if (response.ok) {
      equipments.value = await response.json()
    }
    await handleRouteHighlight()
  } catch (error) {
    console.error('Failed to fetch equipments:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchEquipments()
})

watch(
  () => route.query.highlightId,
  async () => {
    if (equipments.value.length) await handleRouteHighlight()
  }
)


const uniqueProcesses = computed(() => Object.keys(processMap))

const availableSpecifications = computed(() => {
  const specs = equipments.value.map(item => item.specification).filter(Boolean)
  return [...new Set(specs)]
})

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
  if (processFilter.value) {
    result = result.filter(eq => eq.serving_processes && eq.serving_processes.includes(processFilter.value))
  }

  if (filterSpecification.value) {
    const specQuery = filterSpecification.value.toLowerCase()
    result = result.filter(eq => eq.specification && eq.specification.toLowerCase().includes(specQuery))
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

function getMaintenanceDayOffset(str: string): number {
  if (str === '今天') return 0
  if (str === '明天') return 1
  if (str === '后天') return 2
  const match = str.match(/(\d+)天后/)
  if (match) return parseInt(match[1], 10)
  const t = new Date(str).getTime()
  if (!isNaN(t)) {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const d = new Date(str)
    d.setHours(0, 0, 0, 0)
    return Math.round((d.getTime() - today.getTime()) / 86400000)
  }
  return 999
}

const maintenanceWarningList = computed(() => {
  const items: Array<{
    id: string
    name: string
    affectedActivity?: string
    days: number
  }> = []
  maintenanceEquipments.value.forEach((eq) => {
    eq.upcoming_maintenance?.forEach((date: string) => {
      const details = eq.serving_activities_details || []
      const affected = details.length
        ? details.map((d: { activity_name?: string }) => d.activity_name).filter(Boolean).join('、')
        : ''
      items.push({
        id: `${eq._id || eq.id}-${date}`,
        name: eq.name,
        affectedActivity: affected || undefined,
        days: getMaintenanceDayOffset(date)
      })
    })
  })
  return items
})

const groupedEquipmentWarnings = computed(() => {
  const groups: Record<
    number,
    {
      days: number
      hasRisk: boolean
      items: Array<{ id: string; name: string; affectedActivity?: string }>
    }
  > = {}
  for (const item of maintenanceWarningList.value) {
    const d = item.days
    if (!groups[d]) {
      groups[d] = { days: d, hasRisk: false, items: [] }
    }
    groups[d].items.push({
      id: item.id,
      name: item.name,
      affectedActivity: item.affectedActivity
    })
    if (item.affectedActivity) {
      groups[d].hasRisk = true
    }
  }
  return Object.values(groups).sort((a, b) => a.days - b.days)
})

</script>

<style scoped>
:deep(.add-entity-dialog.el-dialog) {
  border-radius: 16px;
  padding: 0;
  overflow: hidden;
}

:deep(.add-entity-dialog .el-dialog__header) {
  padding: 0;
  margin: 0;
}

:deep(.add-equipment-inline-form .el-form-item__content) {
  margin-left: 0 !important;
  line-height: normal;
}

:deep(.custom-input-amber .el-input__wrapper),
:deep(.custom-input-amber .el-textarea__inner) {
  background-color: #f8fafc !important;
  border-radius: 0.75rem !important;
  box-shadow: 0 0 0 1px #e2e8f0 inset !important;
  padding-top: 0.25rem;
  padding-bottom: 0.25rem;
  transition: all 0.2s;
}

:deep(.custom-input-amber .el-input__wrapper.is-focus),
:deep(.custom-input-amber .el-textarea__inner:focus) {
  background-color: #ffffff !important;
  box-shadow: 0 0 0 1px #f59e0b inset, 0 0 0 4px #fef3c7 !important;
}

:deep(.custom-input-amber .el-select .el-input__wrapper.is-focus) {
  background-color: #ffffff !important;
  box-shadow: 0 0 0 1px #f59e0b inset, 0 0 0 4px #fef3c7 !important;
}

:deep(.equipment-date-picker.el-date-editor .el-input__wrapper) {
  background-color: #f8fafc !important;
  border-radius: 0.75rem !important;
  box-shadow: 0 0 0 1px #e2e8f0 inset !important;
  transition: all 0.2s;
}

:deep(.equipment-date-picker.el-date-editor .el-input__wrapper.is-focus) {
  background-color: #ffffff !important;
  box-shadow: 0 0 0 1px #f59e0b inset, 0 0 0 4px #fef3c7 !important;
}
</style>
