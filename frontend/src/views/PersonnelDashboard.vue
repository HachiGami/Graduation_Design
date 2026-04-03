<template>
  <div class="flex h-full min-h-0 flex-col">
    <div class="flex-1 rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div class="border-b border-slate-200 px-6 py-4">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div class="flex flex-wrap items-center gap-3">
            <el-input
              v-model="searchQuery"
              placeholder="按姓名模糊搜索"
              clearable
              class="!w-64"
            >
              <template #prefix>
                <i class="fas fa-search text-slate-400"></i>
              </template>
            </el-input>

            <el-select v-model="filters.department" placeholder="部门筛选" clearable class="!w-44">
              <el-option label="全部(ALL)" value="" />
              <el-option v-for="dept in uniqueDepartments" :key="dept" :label="dept" :value="dept" />
            </el-select>

            <el-select v-model="sortBy" placeholder="排序方式" class="!w-48">
              <el-option
                v-for="item in sortOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>

            <el-popover placement="bottom-start" :width="620" trigger="click">
              <template #reference>
                <el-button class="!border-slate-200 !bg-white !text-slate-700" plain>
                  更多筛选
                </el-button>
              </template>
              <div class="grid grid-cols-5 gap-3">
                <el-select v-model="filters.role" placeholder="职业" clearable>
                  <el-option label="全部(ALL)" value="" />
                  <el-option v-for="role in uniqueRoles" :key="role" :label="role" :value="role" />
                </el-select>
                <el-select v-model="filters.gender" placeholder="性别" clearable>
                  <el-option label="全部(ALL)" value="" />
                  <el-option label="男" value="男" />
                  <el-option label="女" value="女" />
                </el-select>
                <el-select v-model="filters.status" placeholder="状态" clearable>
                  <el-option label="全部(ALL)" value="" />
                  <el-option label="在职" value="active" />
                  <el-option label="离职" value="resigned" />
                </el-select>
                <el-select v-model="filters.education" placeholder="学历" clearable>
                  <el-option label="全部(ALL)" value="" />
                  <el-option v-for="edu in uniqueEducations" :key="edu" :label="edu" :value="edu" />
                </el-select>
                <el-select v-model="filters.process" placeholder="流程" clearable>
                  <el-option label="全部(ALL)" value="" />
                  <el-option v-for="(_, id) in processMap" :key="id" :label="formatProcessName(id)" :value="id" />
                </el-select>
              </div>
            </el-popover>
          </div>

          <div class="flex items-center gap-3">
            <el-button
              @click="isLeaveModalVisible = true"
              class="!border-amber-200 !bg-amber-50 !text-amber-600 hover:!bg-amber-100"
            >
              <span class="relative mr-2 inline-flex h-2 w-2">
                <span class="h-2 w-2 rounded-full bg-red-500"></span>
              </span>
              七天请假预警
              <el-badge :value="leaveStats.total" class="ml-2" type="danger" />
            </el-button>

            <div class="h-6 w-px bg-slate-200"></div>

            <el-button type="primary" :icon="Plus" @click="openAddPersonnelDialog">添加员工</el-button>
          </div>
        </div>
      </div>

      <div class="px-6 py-4">
        <div class="mb-3 flex items-center justify-between">
          <p class="text-sm font-semibold text-slate-700">员工列表 (共 {{ filteredAndSortedPersonnel.length }} 人)</p>
        </div>

        <div class="mb-2 flex items-center border-b border-slate-200 pb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          <div class="w-10"></div>
          <div class="flex-1">员工信息</div>
          <div class="w-48">所属部门/岗位</div>
          <div class="w-48 text-center">状态</div>
          <div class="w-40 text-center">入职时间</div>
          <div class="w-32 text-right">操作</div>
        </div>

        <div v-loading="loading">
          <el-collapse v-if="filteredAndSortedPersonnel.length > 0" v-model="personnelExpandedNames">
            <PersonnelAccordionItem
              v-for="person in filteredAndSortedPersonnel"
              :key="person.id"
              :personnel="person"
              :anchor-id="'personnel-row-' + String(person.id || (person as any)._id || '')"
              :highlighted="highlightedPersonnelId === String(person.id || (person as any)._id || '')"
              @updated="fetchData"
            />
          </el-collapse>
          <el-empty v-else description="暂无符合条件的员工数据" />
        </div>
      </div>
    </div>

    <!-- 添加员工弹窗 -->
    <el-dialog
      v-model="addPersonnelDialogVisible"
      width="600px"
      :show-close="false"
      :align-center="true"
      class="add-entity-dialog add-personnel-dialog rounded-2xl overflow-hidden"
      header-class="!p-0 !m-0 !border-0"
      body-class="!p-0"
      footer-class="!p-0"
    >
      <template #header>
        <div class="flex items-center justify-between border-b border-blue-100 bg-blue-50/50 px-6 py-4">
          <div class="flex items-center space-x-3">
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
              <el-icon :size="18"><User /></el-icon>
            </div>
            <h3 class="text-lg font-bold tracking-tight text-slate-800">添加员工</h3>
          </div>
          <el-button link class="text-slate-400 hover:text-slate-600" @click="addPersonnelDialogVisible = false">
            <el-icon :size="20"><Close /></el-icon>
          </el-button>
        </div>
      </template>

      <div class="bg-white p-6">
        <div class="grid grid-cols-2 gap-x-5 gap-y-4">
          <div class="flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">
              <span class="mr-1 text-red-500">*</span>姓名
            </label>
            <el-input v-model="addPersonnelForm.name" placeholder="请输入姓名" class="custom-input-blue w-full" />
          </div>
          <div class="flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">状态</label>
            <el-select v-model="addPersonnelForm.status" placeholder="状态" class="custom-input-blue w-full">
              <el-option label="在职" value="active" />
              <el-option label="离职" value="resigned" />
            </el-select>
          </div>

          <div class="flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">
              <span class="mr-1 text-red-500">*</span>角色
            </label>
            <el-input v-model="addPersonnelForm.role" placeholder="如：操作员、班长" class="custom-input-blue w-full" />
          </div>
          <div class="flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">
              <span class="mr-1 text-red-500">*</span>职责/部门
            </label>
            <el-input v-model="addPersonnelForm.responsibility" placeholder="如：生产部" class="custom-input-blue w-full" />
          </div>

          <div class="flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">年龄</label>
            <el-input-number
              v-model="addPersonnelForm.age"
              :min="18"
              :max="100"
              class="custom-input-blue personnel-input-number w-full"
              controls-position="right"
            />
          </div>
          <div class="flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">性别</label>
            <el-select v-model="addPersonnelForm.gender" placeholder="请选择" class="custom-input-blue w-full">
              <el-option label="男" value="男" />
              <el-option label="女" value="女" />
            </el-select>
          </div>

          <div class="flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">学历</label>
            <el-select v-model="addPersonnelForm.education" placeholder="请选择" class="custom-input-blue w-full">
              <el-option label="初中" value="初中" />
              <el-option label="高中" value="高中" />
              <el-option label="大专" value="大专" />
              <el-option label="本科" value="本科" />
              <el-option label="硕士及以上" value="硕士及以上" />
            </el-select>
          </div>
          <div class="flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">入职日期</label>
            <el-date-picker
              v-model="addPersonnelForm.hire_date"
              type="date"
              placeholder="选择日期"
              value-format="YYYY-MM-DD"
              class="custom-input-blue personnel-date-picker w-full"
            />
          </div>

          <div class="col-span-2 flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">薪资 (元/月)</label>
            <el-input-number
              v-model="addPersonnelForm.salary"
              :min="0"
              :step="100"
              class="custom-input-blue personnel-input-number w-full"
              controls-position="right"
            />
          </div>
        </div>
      </div>

      <template #footer>
        <div class="flex justify-end space-x-3 border-t border-slate-100 bg-slate-50 px-6 py-4">
          <button
            type="button"
            class="rounded-xl border border-slate-300 bg-white px-5 py-2 text-sm font-bold text-slate-600 transition-colors hover:bg-slate-50"
            @click="addPersonnelDialogVisible = false"
          >
            取消
          </button>
          <button
            type="button"
            class="rounded-xl bg-blue-600 px-5 py-2 text-sm font-bold text-white shadow-sm transition-colors hover:bg-blue-700"
            :disabled="addPersonnelSubmitting"
            @click="submitAddPersonnel"
          >
            {{ addPersonnelSubmitting ? '提交中…' : '确定添加' }}
          </button>
        </div>
      </template>
    </el-dialog>

    <!-- 请假预警弹窗 -->
    <el-dialog v-model="isLeaveModalVisible" title="未来7天请假与排班预警" width="70%" top="5vh">
      <!-- 风险提示 Banner -->
      <div class="bg-orange-50 border-l-4 border-orange-400 p-4 mb-6 rounded-r-md flex items-start">
        <i class="fas fa-exclamation-triangle text-orange-400 mt-1 mr-3"></i>
        <p class="text-sm text-orange-700">
          未来 7 天内共有 <strong>{{ leaveStats.total }}</strong> 人次请假，其中 <strong>{{ leaveStats.affectedTasks }}</strong> 项生产活动可能面临人员短缺风险，请及时在面板中重新调配资源！
        </p>
      </div>

      <!-- 按日期分组显示 -->
      <div v-if="Object.keys(groupedLeaves).length > 0" class="max-h-[60vh] overflow-y-auto pr-2">
        <div v-for="(group, date) in groupedLeaves" :key="date" class="mb-6">
          <div class="flex items-center mb-3">
            <el-tag effect="dark" type="primary" size="large" class="font-bold">
              <i class="far fa-calendar mr-1"></i> {{ formatLeaveDate(date) }}
            </el-tag>
            <div class="h-px bg-gray-200 flex-1 ml-4"></div>
          </div>
          
          <el-table
            :data="group"
            stripe
            class="!overflow-hidden !rounded-xl"
            :header-cell-style="{ background: '#f8fafc', color: '#475569', fontWeight: '600' }"
          >
            <el-table-column label="员工姓名" width="150">
              <template #default="{ row }">
                <span class="font-bold">{{ row.name }}</span>
              </template>
            </el-table-column>
            <el-table-column label="所属部门/岗位" width="200">
              <template #default="{ row }">
                <div class="text-gray-900">{{ row.department }}</div>
                <div class="text-gray-500 text-xs">{{ row.role }}</div>
              </template>
            </el-table-column>
            <el-table-column label="受影响的占用活动">
              <template #default="{ row }">
                <div v-if="row.assigned_tasks && row.assigned_tasks.length > 0" class="flex flex-wrap gap-2">
                  <el-tag v-for="task in row.assigned_tasks" :key="task" type="danger" size="small" effect="light">
                    <i class="fas fa-link mr-1"></i> {{ task }}
                  </el-tag>
                </div>
                <span v-else class="text-green-600 text-sm"><i class="fas fa-check-circle mr-1"></i> 无关联活动，安全</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
      
      <el-empty v-else description="未来 7 天内没有员工请假" />
      
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { getPersonnelList, createPersonnel } from '@/api/personnel'
import type { Personnel } from '@/types'
import PersonnelAccordionItem from '@/components/PersonnelAccordionItem.vue'
import { ElMessage } from 'element-plus'
import { Plus, User, Close } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'

const loading = ref(false)
const rawPersonnelList = ref<Personnel[]>([])
const route = useRoute()
const router = useRouter()
const personnelExpandedNames = ref<(string | number)[]>([])
const highlightedPersonnelId = ref('')

// 请假预警状态与逻辑
const isLeaveModalVisible = ref(false)

const groupedLeaves = computed(() => {
  const list = rawPersonnelList.value || []
  const groups: Record<string, any[]> = {}
  
  list.forEach(person => {
    if (person.upcoming_leaves && person.upcoming_leaves.length > 0) {
      person.upcoming_leaves.forEach((date: string) => {
        if (!groups[date]) groups[date] = []
        groups[date].push(person)
      })
    }
  })
  
  // 按日期正序排列
  return Object.keys(groups).sort().reduce((acc, key) => {
    acc[key] = groups[key]
    return acc
  }, {} as Record<string, any[]>)
})

// 统计受影响的总人次和被波及的活动数
const leaveStats = computed(() => {
  let total = 0
  let affectedTasks = 0
  Object.values(groupedLeaves.value).forEach(group => {
    total += group.length
    group.forEach(p => {
      if (p.assigned_tasks && p.assigned_tasks.length > 0) {
        affectedTasks += p.assigned_tasks.length
      }
    })
  })
  return { total, affectedTasks }
})

// 格式化日期的辅助函数
const formatLeaveDate = (dateStr: string) => {
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return dateStr
  const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${date.getMonth() + 1}月${date.getDate()}日 (${days[date.getDay()]})`
}

// 搜索和筛选状态
const searchQuery = ref('')
const filters = ref({
  role: '',
  gender: '',
  status: '',
  department: '',
  education: '',
  process: ''
})

// 流程映射字典
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
const formatProcessName = (id: string) => {
  if (!id || id === 'ALL') return '全部';
  return processMap[id] ? `${id} - ${processMap[id]}` : id;
};

// 排序状态
const sortBy = ref('NONE')
const sortOptions = [
  { label: '默认排序', value: 'NONE' },
  { label: '入职时间 (正序)', value: 'HIRE_DATE_ASC' },
  { label: '入职时间 (倒序)', value: 'HIRE_DATE_DESC' },
  { label: '年龄 (从小到大)', value: 'AGE_ASC' },
  { label: '年龄 (从大到小)', value: 'AGE_DESC' },
  { label: '薪资 (由低到高)', value: 'SALARY_ASC' },
  { label: '薪资 (由高到低)', value: 'SALARY_DESC' }
]

// 提取唯一值用于下拉框
const uniqueRoles = computed(() => {
  const roles = new Set(rawPersonnelList.value.map(p => p.role).filter(Boolean))
  return Array.from(roles)
})
const uniqueDepartments = computed(() => {
  const depts = new Set(rawPersonnelList.value.map(p => p.department).filter(Boolean))
  return Array.from(depts)
})
const uniqueEducations = computed(() => {
  const edus = new Set(rawPersonnelList.value.map(p => p.education).filter(Boolean))
  return Array.from(edus)
})

// 并发查询引擎：模糊搜索 -> 5维筛选 -> 排序
const filteredAndSortedPersonnel = computed(() => {
  let result = [...rawPersonnelList.value]

  // 1. 模糊搜索
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(p => p.name.toLowerCase().includes(query))
  }

  // 2. 5维并发筛选
  if (filters.value.role) {
    result = result.filter(p => p.role === filters.value.role)
  }
  if (filters.value.gender) {
    result = result.filter(p => p.gender === filters.value.gender)
  }
  if (filters.value.status) {
    result = result.filter(p => p.status === filters.value.status)
  }
  if (filters.value.department) {
    result = result.filter(p => p.department === filters.value.department)
  }
  if (filters.value.education) {
    result = result.filter(p => p.education === filters.value.education)
  }
  if (filters.value.process) {
    result = result.filter(p => p.serving_processes && p.serving_processes.includes(filters.value.process))
  }

  // 第三阶：动态排序
  if (sortBy.value !== 'NONE') {
    result.sort((a, b) => {
      // 提取对比值，加入兜底逻辑防止 NaN 报错
      const ageA = a.age || 0;
      const ageB = b.age || 0;
      const salaryA = a.salary || 0;
      const salaryB = b.salary || 0;
      const dateA = a.hire_date ? new Date(a.hire_date).getTime() : 0;
      const dateB = b.hire_date ? new Date(b.hire_date).getTime() : 0;

      switch (sortBy.value) {
        case 'AGE_ASC': return ageA - ageB;
        case 'AGE_DESC': return ageB - ageA;
        case 'SALARY_ASC': return salaryA - salaryB;
        case 'SALARY_DESC': return salaryB - salaryA;
        case 'HIRE_DATE_ASC': return dateA - dateB;
        case 'HIRE_DATE_DESC': return dateB - dateA;
        default: return 0;
      }
    });
  }

  return result
})

const addPersonnelDialogVisible = ref(false)
const addPersonnelSubmitting = ref(false)

const defaultAddPersonnelForm = () => ({
  name: '',
  role: '',
  responsibility: '',
  status: 'active',
  skills: [] as string[],
  upcoming_leaves: [] as string[],
  age: undefined as number | undefined,
  gender: '',
  education: '',
  salary: undefined as number | undefined,
  hire_date: ''
})

const addPersonnelForm = ref(defaultAddPersonnelForm())

const openAddPersonnelDialog = () => {
  addPersonnelForm.value = defaultAddPersonnelForm()
  addPersonnelDialogVisible.value = true
}

const submitAddPersonnel = async () => {
  if (!addPersonnelForm.value.name.trim()) {
    ElMessage.warning('姓名不能为空')
    return
  }
  if (!addPersonnelForm.value.role.trim()) {
    ElMessage.warning('角色不能为空')
    return
  }
  if (!addPersonnelForm.value.responsibility.trim()) {
    ElMessage.warning('职责/部门不能为空')
    return
  }
  addPersonnelSubmitting.value = true
  try {
    await createPersonnel(addPersonnelForm.value as Personnel)
    ElMessage.success('员工添加成功')
    addPersonnelDialogVisible.value = false
    await fetchData()
  } catch (error) {
    ElMessage.error('添加失败，请检查表单数据')
  } finally {
    addPersonnelSubmitting.value = false
  }
}

const handleRouteHighlight = async () => {
  const rawId = route.query.highlightId
  const highlightId = Array.isArray(rawId) ? rawId[0] : rawId
  if (!highlightId) return

  const targetId = String(highlightId)
  const target = rawPersonnelList.value.find(
    (p) => String(p.id || (p as any)._id || '') === targetId
  )
  if (!target) {
    ElMessage.warning('未找到目标员工，可能已被删除')
    highlightedPersonnelId.value = ''
    const nextQuery = { ...route.query } as Record<string, any>
    delete nextQuery.highlightId
    await router.replace({ query: nextQuery })
    return
  }

  searchQuery.value = ''
  filters.value = {
    role: '',
    gender: '',
    status: '',
    department: '',
    education: '',
    process: ''
  }
  sortBy.value = 'NONE'
  highlightedPersonnelId.value = targetId
  personnelExpandedNames.value = [targetId]

  await nextTick()
  const targetEl = document.getElementById(`personnel-row-${targetId}`)
  if (!targetEl) {
    ElMessage.warning('定位失败，请稍后重试')
    return
  }

  targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
  setTimeout(() => {
    highlightedPersonnelId.value = ''
  }, 1800)
  const nextQuery = { ...route.query } as Record<string, any>
  delete nextQuery.highlightId
  await router.replace({ query: nextQuery })
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getPersonnelList()
    // Axios 返回通常在 data 字段，根据项目封装可能直接返回数据
    const list = Array.isArray(res) ? res : (res.data || [])
    rawPersonnelList.value = list.map((item: any) => ({
      ...item,
      id: item.id || item._id
    }))
    await handleRouteHighlight()
  } catch (error) {
    console.error('Failed to fetch personnel:', error)
    ElMessage.error('获取员工数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})

watch(
  () => route.query.highlightId,
  async () => {
    if (rawPersonnelList.value.length) await handleRouteHighlight()
  }
)
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

:deep(.custom-input-blue .el-input__wrapper),
:deep(.custom-input-blue .el-textarea__inner) {
  background-color: #f8fafc !important;
  border-radius: 0.75rem !important;
  box-shadow: 0 0 0 1px #e2e8f0 inset !important;
  padding-top: 0.25rem;
  padding-bottom: 0.25rem;
  transition: all 0.2s;
}

:deep(.custom-input-blue .el-input__wrapper.is-focus),
:deep(.custom-input-blue .el-textarea__inner:focus) {
  background-color: #ffffff !important;
  box-shadow: 0 0 0 1px #2563eb inset, 0 0 0 4px #dbeafe !important;
}

:deep(.custom-input-blue .el-select .el-input__wrapper.is-focus) {
  background-color: #ffffff !important;
  box-shadow: 0 0 0 1px #2563eb inset, 0 0 0 4px #dbeafe !important;
}

:deep(.personnel-date-picker.el-date-editor .el-input__wrapper) {
  background-color: #f8fafc !important;
  border-radius: 0.75rem !important;
  box-shadow: 0 0 0 1px #e2e8f0 inset !important;
  transition: all 0.2s;
}

:deep(.personnel-date-picker.el-date-editor .el-input__wrapper.is-focus) {
  background-color: #ffffff !important;
  box-shadow: 0 0 0 1px #2563eb inset, 0 0 0 4px #dbeafe !important;
}

:deep(.personnel-input-number.el-input-number .el-input__wrapper) {
  background-color: #f8fafc !important;
  border-radius: 0.75rem !important;
  box-shadow: 0 0 0 1px #e2e8f0 inset !important;
  transition: all 0.2s;
}

:deep(.personnel-input-number.el-input-number .el-input__wrapper.is-focus) {
  background-color: #ffffff !important;
  box-shadow: 0 0 0 1px #2563eb inset, 0 0 0 4px #dbeafe !important;
}
</style>
