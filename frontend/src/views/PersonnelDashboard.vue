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
      </div>
    </el-card>

    <el-card class="list-card mt-4">
      <template #header>
        <div class="card-header">
          <span>员工列表 (共 {{ filteredAndSortedPersonnel.length }} 人)</span>
          <el-button type="primary" icon="Refresh" @click="fetchData" circle />
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getPersonnelList } from '@/api/personnel'
import type { Personnel } from '@/types'
import PersonnelAccordionItem from '@/components/PersonnelAccordionItem.vue'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const rawPersonnelList = ref<Personnel[]>([])

// 搜索和筛选状态
const searchQuery = ref('')
const filters = ref({
  role: '',
  gender: '',
  status: '',
  department: '',
  education: ''
})

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
