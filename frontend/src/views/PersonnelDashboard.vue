<template>
  <div class="personnel-dashboard">
    <el-card class="filter-card">
      <div class="filter-container">
        <!-- 搜索框 -->
        <div class="filter-item">
          <span class="label">搜索:</span>
          <el-input v-model="searchQuery" placeholder="按姓名模糊搜索" clearable style="width: 200px" />
        </div>

        <!-- 5个维度筛选 -->
        <div class="filter-item">
          <span class="label">职业:</span>
          <el-select v-model="filters.role" placeholder="全部" clearable style="width: 120px">
            <el-option label="全部(ALL)" value="" />
            <el-option v-for="role in uniqueRoles" :key="role" :label="role" :value="role" />
          </el-select>
        </div>

        <div class="filter-item">
          <span class="label">性别:</span>
          <el-select v-model="filters.gender" placeholder="全部" clearable style="width: 100px">
            <el-option label="全部(ALL)" value="" />
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
          </el-select>
        </div>

        <div class="filter-item">
          <span class="label">状态:</span>
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 100px">
            <el-option label="全部(ALL)" value="" />
            <el-option label="在职" value="active" />
            <el-option label="离职" value="resigned" />
          </el-select>
        </div>

        <div class="filter-item">
          <span class="label">部门:</span>
          <el-select v-model="filters.department" placeholder="全部" clearable style="width: 150px">
            <el-option label="全部(ALL)" value="" />
            <el-option v-for="dept in uniqueDepartments" :key="dept" :label="dept" :value="dept" />
          </el-select>
        </div>

        <div class="filter-item">
          <span class="label">学历:</span>
          <el-select v-model="filters.education" placeholder="全部" clearable style="width: 120px">
            <el-option label="全部(ALL)" value="" />
            <el-option v-for="edu in uniqueEducations" :key="edu" :label="edu" :value="edu" />
          </el-select>
        </div>

        <!-- 流程筛选 -->
        <div class="filter-item">
          <span class="label">流程:</span>
          <el-select v-model="filters.process" placeholder="全部" clearable style="width: 150px">
            <el-option label="全部(ALL)" value="" />
            <el-option v-for="(name, id) in processMap" :key="id" :label="formatProcessName(id)" :value="id" />
          </el-select>
        </div>

        <!-- 复合排序 -->
        <div class="filter-item">
          <span class="label">排序:</span>
          <el-select v-model="sortBy" placeholder="请选择排序方式" style="width: 160px;">
            <el-option
              v-for="item in sortOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </div>

        <!-- 请假预警按钮 -->
        <div class="filter-item ml-auto">
          <el-button type="warning" @click="isLeaveModalVisible = true">
            <i class="fas fa-calendar-alt mr-2"></i> 七天请假预警
            <el-badge :value="leaveStats.total" class="ml-2" type="danger" />
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card class="list-card mt-4">
      <template #header>
        <div class="card-header">
          <span>员工列表 (共 {{ filteredAndSortedPersonnel.length }} 人)</span>
          <div style="display: flex; gap: 8px;">
            <el-button type="primary" :icon="Plus" @click="openAddPersonnelDialog">添加员工</el-button>
            <el-button type="primary" icon="Refresh" @click="fetchData" circle />
          </div>
        </div>
      </template>

      <div v-loading="loading">
        <el-collapse v-if="filteredAndSortedPersonnel.length > 0">
          <PersonnelAccordionItem
            v-for="person in filteredAndSortedPersonnel"
            :key="person.id"
            :personnel="person"
            @updated="fetchData"
          />
        </el-collapse>
        <el-empty v-else description="暂无符合条件的员工数据" />
      </div>
    </el-card>

    <!-- 添加员工弹窗 -->
    <el-dialog v-model="addPersonnelDialogVisible" title="添加员工" width="520px">
      <el-form :model="addPersonnelForm" label-width="100px" size="default">
        <el-form-item label="姓名" required>
          <el-input v-model="addPersonnelForm.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-input v-model="addPersonnelForm.role" placeholder="如：操作员、班长" />
        </el-form-item>
        <el-form-item label="职责/部门" required>
          <el-input v-model="addPersonnelForm.responsibility" placeholder="如：生产部" />
        </el-form-item>
        <el-form-item label="工作时间" required>
          <el-input v-model="addPersonnelForm.work_hours" placeholder="如：08:00-18:00" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="addPersonnelForm.status" style="width: 100%">
            <el-option label="在职" value="active" />
            <el-option label="离职" value="resigned" />
          </el-select>
        </el-form-item>
        <el-form-item label="年龄">
          <el-input-number v-model="addPersonnelForm.age" :min="18" :max="100" />
        </el-form-item>
        <el-form-item label="性别">
          <el-select v-model="addPersonnelForm.gender" placeholder="请选择" style="width: 100%">
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
          </el-select>
        </el-form-item>
        <el-form-item label="学历">
          <el-select v-model="addPersonnelForm.education" placeholder="请选择" style="width: 100%">
            <el-option label="初中" value="初中" />
            <el-option label="高中" value="高中" />
            <el-option label="大专" value="大专" />
            <el-option label="本科" value="本科" />
            <el-option label="硕士及以上" value="硕士及以上" />
          </el-select>
        </el-form-item>
        <el-form-item label="薪资(元/月)">
          <el-input-number v-model="addPersonnelForm.salary" :min="0" :step="100" style="width: 100%" />
        </el-form-item>
        <el-form-item label="入职日期">
          <el-date-picker v-model="addPersonnelForm.hire_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addPersonnelDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAddPersonnel" :loading="addPersonnelSubmitting">确定添加</el-button>
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
          
          <el-table :data="group" border stripe style="width: 100%">
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
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="isLeaveModalVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getPersonnelList, createPersonnel } from '@/api/personnel'
import type { Personnel } from '@/types'
import PersonnelAccordionItem from '@/components/PersonnelAccordionItem.vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

const loading = ref(false)
const rawPersonnelList = ref<Personnel[]>([])

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
  work_hours: '08:00-18:00',
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

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getPersonnelList()
    // Axios 返回通常在 data 字段，根据项目封装可能直接返回数据
    rawPersonnelList.value = Array.isArray(res) ? res : (res.data || [])
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
</script>

<style scoped>
.personnel-dashboard {
  padding: 0;
}
.filter-card {
  margin-bottom: 20px;
}
.filter-container {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  align-items: center;
}
.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.filter-item .label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.mt-4 {
  margin-top: 16px;
}
</style>
