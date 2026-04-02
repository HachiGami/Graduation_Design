<template>
  <el-collapse-item :name="personnel.id">
    <template #title>
      <div class="flex w-full items-center pr-3">
        <div class="w-10"></div>

        <div class="flex flex-1 items-center gap-3">
          <div
            class="flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold"
            :class="personnel.status === 'active' ? 'bg-blue-50 text-blue-600' : 'bg-slate-100 text-slate-500'"
          >
            {{ (personnel.name || '?').slice(0, 1).toUpperCase() }}
          </div>
          <span class="text-sm font-semibold text-slate-800">{{ personnel.name }}</span>
        </div>

        <div class="w-48">
          <div class="truncate text-sm text-slate-700">{{ personnel.department || '-' }}</div>
          <div class="truncate text-xs text-slate-500">{{ personnel.role || '-' }}</div>
        </div>

        <div class="w-48 text-center">
          <span
            class="inline-flex min-w-[64px] items-center justify-center rounded-full px-3 py-1 text-xs font-semibold"
            :class="personnel.status === 'active' ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-600'"
          >
            {{ personnel.status === 'active' ? '在职' : '离职' }}
          </span>
        </div>

        <div class="w-40 text-center text-sm text-slate-600">
          {{ personnel.hire_date || '-' }}
        </div>

        <div class="w-32 flex justify-end space-x-2" @click.stop>
          <el-button link type="primary" @click="handleEdit">
            <el-icon :size="18"><Edit /></el-icon>
          </el-button>
          <el-button link type="danger" @click="handleDeletePersonnel">
            <el-icon :size="18"><Delete /></el-icon>
          </el-button>
        </div>
      </div>
    </template>

    <div class="rounded-xl bg-slate-50 p-4 shadow-inner">
      <el-tabs>
        <el-tab-pane label="当前分配任务">
          <el-empty
            v-if="!personnel.serving_activities_details || personnel.serving_activities_details.length === 0"
            description="目前无分配任务，待命中"
            :image-size="60"
          />
          <div v-else class="space-y-3">
            <div
              v-for="(act, index) in personnel.serving_activities_details"
              :key="index"
              class="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-blue-300 hover:shadow-md"
            >
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2">
                  <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-500">
                    <i class="fas fa-link text-xs"></i>
                  </div>
                  <span class="truncate text-sm font-semibold text-slate-800">{{ act.activity_name }}</span>
                  <span class="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-600">
                    {{ getActivityStatusLabel(act.status) }}
                  </span>
                </div>
                <div class="ml-11 mt-2 flex flex-wrap items-center gap-4 text-xs">
                  <span class="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-1 text-slate-600">
                    <i class="fas fa-project-diagram"></i>
                    归属: {{ formatProcessName(act.process_id) }}
                  </span>
                  <span
                    v-if="act.working_hours && act.working_hours.length > 0"
                    class="inline-flex items-center gap-1 font-medium text-blue-600"
                  >
                    <i class="far fa-clock"></i>
                    运行时间: {{ formatWorkingHours(act.working_hours) }}
                  </span>
                </div>
              </div>
              <el-button class="!border-blue-200 !bg-white !text-blue-600" plain @click="goToActivityDetail(act)">
                查看活动详情
                <i class="fas fa-chevron-right ml-1 text-xs"></i>
              </el-button>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="员工资料">
          <div class="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <div class="grid grid-cols-6 border-b border-slate-200 text-sm">
              <div class="bg-slate-100 px-3 py-2 font-medium text-slate-600">年龄</div>
              <div class="border-l border-slate-200 px-3 py-2 text-slate-700">{{ personnel.age || '-' }}</div>
              <div class="border-l border-slate-200 bg-slate-100 px-3 py-2 font-medium text-slate-600">性别</div>
              <div class="border-l border-slate-200 px-3 py-2 text-slate-700">{{ personnel.gender || '-' }}</div>
              <div class="border-l border-slate-200 bg-slate-100 px-3 py-2 font-medium text-slate-600">籍贯</div>
              <div class="border-l border-slate-200 px-3 py-2 text-slate-700">{{ personnel.native_place || '-' }}</div>
            </div>
            <div class="grid grid-cols-6 text-sm">
              <div class="bg-slate-100 px-3 py-2 font-medium text-slate-600">入职日期</div>
              <div class="border-l border-slate-200 px-3 py-2 text-slate-700">{{ personnel.hire_date || '-' }}</div>
              <div class="border-l border-slate-200 bg-slate-100 px-3 py-2 font-medium text-slate-600">学历</div>
              <div class="border-l border-slate-200 px-3 py-2 text-slate-700">{{ personnel.education || '-' }}</div>
              <div class="border-l border-slate-200 bg-slate-100 px-3 py-2 font-medium text-slate-600">薪资</div>
              <div class="border-l border-slate-200 px-3 py-2 text-slate-700">
                {{ personnel.salary ? `¥${personnel.salary}/月` : '-' }}
              </div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane :label="`请假记录 (${(personnel.upcoming_leaves || []).length})`">
          <div class="mb-3 flex justify-end">
            <el-button type="primary" @click.stop="handleLeave">+ 添加请假记录</el-button>
          </div>
          <div
            v-if="personnel.upcoming_leaves && personnel.upcoming_leaves.length > 0"
            class="grid grid-cols-3 gap-4"
          >
            <div
              v-for="(leave, idx) in personnel.upcoming_leaves"
              :key="idx"
              class="group flex items-center justify-between rounded-xl border border-slate-200 bg-white p-3 shadow-sm transition-all hover:border-amber-400 hover:shadow-md"
            >
              <div class="flex items-center">
                <div class="mr-3 flex h-8 w-8 items-center justify-center rounded-lg border border-amber-100 bg-amber-50 text-amber-500">
                  <el-icon :size="16"><Calendar /></el-icon>
                </div>
                <span class="text-sm font-bold text-slate-700">{{ leave }}</span>
              </div>
              <el-button
                link
                icon="Delete"
                class="!text-slate-300 opacity-0 transition-opacity hover:!text-red-500 group-hover:opacity-100"
                @click.stop
              />
            </div>
          </div>
          <el-empty v-else description="暂无请假记录" :image-size="60" />
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑员工信息" width="500px" append-to-body>
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="100px" size="default">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-input v-model="editForm.role" />
        </el-form-item>
        <el-form-item label="职责(部门)" prop="responsibility">
          <el-input v-model="editForm.responsibility" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="editForm.status" placeholder="请选择状态">
            <el-option label="在职" value="active" />
            <el-option label="离职" value="resigned" />
          </el-select>
        </el-form-item>
        <el-form-item label="年龄">
          <el-input-number v-model="editForm.age" :min="18" :max="100" />
        </el-form-item>
        <el-form-item label="性别">
          <el-select v-model="editForm.gender" placeholder="请选择性别">
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
          </el-select>
        </el-form-item>
        <el-form-item label="籍贯">
          <el-input v-model="editForm.native_place" />
        </el-form-item>
        <el-form-item label="入职日期">
          <el-date-picker v-model="editForm.hire_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="学历">
          <el-select v-model="editForm.education" placeholder="请选择学历">
            <el-option label="初中" value="初中" />
            <el-option label="高中" value="高中" />
            <el-option label="大专" value="大专" />
            <el-option label="本科" value="本科" />
            <el-option label="硕士及以上" value="硕士及以上" />
          </el-select>
        </el-form-item>
        <el-form-item label="薪资(元/月)">
          <el-input-number v-model="editForm.salary" :min="0" :step="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="flex justify-end gap-2">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitEdit" :loading="submitting">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 请假弹窗 -->
    <el-dialog v-model="leaveDialogVisible" title="安排员工请假" width="400px" append-to-body>
      <el-form label-width="100px">
        <el-form-item label="请假日期">
          <div class="flex flex-wrap gap-2.5">
            <button
              v-for="item in leaveOptions"
              :key="item.value"
              type="button"
              class="rounded-lg border px-4 py-2 text-sm font-bold transition-all"
              :class="selectedLeaveDays.includes(item.value)
                ? 'border-blue-400 bg-blue-50 text-blue-700 shadow-[0_0_0_2px_rgba(59,130,246,0.1)]'
                : 'border-slate-200 bg-white text-slate-600 hover:border-blue-300 hover:bg-slate-50'"
              @click="selectedLeaveDays.includes(item.value)
                ? selectedLeaveDays.splice(selectedLeaveDays.indexOf(item.value), 1)
                : selectedLeaveDays.push(item.value)"
            >
              {{ item.label }}
            </button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="leaveDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitLeave" :loading="submittingLeave">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </el-collapse-item>
</template>

<script setup lang="ts">
import { ref, PropType } from 'vue'
import { useRouter } from 'vue-router'
import { Calendar, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { updatePersonnel, deletePersonnel } from '@/api/personnel'
import type { Personnel } from '@/types'
import type { FormInstance, FormRules } from 'element-plus'

const props = defineProps({
  personnel: {
    type: Object as PropType<Personnel>,
    required: true
  }
})

const emit = defineEmits(['updated'])
const router = useRouter()

const editDialogVisible = ref(false)
const submitting = ref(false)
const editForm = ref<Partial<Personnel>>({})
const editFormRef = ref<FormInstance>()
const editRules: FormRules = {
  name: [{ required: true, message: '姓名不能为空', trigger: 'blur' }],
  role: [{ required: true, message: '角色不能为空', trigger: 'blur' }],
  responsibility: [{ required: true, message: '职责不能为空', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }]
}

const leaveDialogVisible = ref(false)
const submittingLeave = ref(false)
const selectedLeaveDays = ref<string[]>([])

const leaveOptions = [
  { label: '1天后', value: '1天后' },
  { label: '2天后', value: '2天后' },
  { label: '3天后', value: '3天后' },
  { label: '4天后', value: '4天后' },
  { label: '5天后', value: '5天后' },
  { label: '6天后', value: '6天后' },
  { label: '7天后', value: '7天后' }
]

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

const formatWorkingHours = (workingHours: Array<{ start_time?: string; end_time?: string }>) => {
  if (!Array.isArray(workingHours) || workingHours.length === 0) return ''
  return workingHours
    .filter(period => period?.start_time && period?.end_time)
    .map(period => `${period.start_time}-${period.end_time}`)
    .join(', ')
}

const getActivityStatusType = (status: string) => {
  const normalized = (status || '').toLowerCase()
  if (normalized === 'in_progress' || normalized === '进行中') return 'success'
  if (normalized === 'stopped' || normalized === '已停机') return 'danger'
  return 'info'
}

const getActivityStatusLabel = (status: string) => {
  const normalized = (status || '').toLowerCase()
  if (normalized === 'in_progress' || normalized === '进行中') return '进行中'
  if (normalized === 'stopped' || normalized === '已停机') return '已停机'
  if (normalized === 'pending' || normalized === '待机') return '待机中'
  return status || '未知状态'
}

const goToActivityDetail = (task: any) => {
  const activityId = task?.activity_id || task?.id || task?._id
  if (!activityId) {
    ElMessage.warning('当前任务缺少 activity_id，暂无法定位活动详情')
    return
  }
  router.push({
    name: 'Dashboard',
    query: {
      highlightId: String(activityId)
    }
  })
}

const handleEdit = () => {
  editForm.value = { ...props.personnel }
  editDialogVisible.value = true
}

const handleLeave = () => {
  selectedLeaveDays.value = [...(props.personnel.upcoming_leaves || [])]
  leaveDialogVisible.value = true
}

const submitLeave = async () => {
  if (!props.personnel.id) return
  submittingLeave.value = true
  try {
    await updatePersonnel(props.personnel.id, {
      upcoming_leaves: selectedLeaveDays.value
    })
    ElMessage.success('请假计划更新成功')
    leaveDialogVisible.value = false
    emit('updated')
  } catch (error) {
    console.error('Update leave failed:', error)
    ElMessage.error('更新失败')
  } finally {
    submittingLeave.value = false
  }
}

const submitEdit = async () => {
  const personnelId = props.personnel.id || (props.personnel as any)._id
  if (!personnelId) {
    console.error('表单校验失败: 缺少员工ID')
    ElMessage.warning('员工ID缺失，无法保存')
    return
  }
  const valid = await editFormRef.value?.validate().catch(() => false)
  if (!valid) {
    console.error('表单校验失败')
    ElMessage.warning('请检查表单填写是否有误')
    return
  }

  const { id, work_hours, assigned_tasks, created_at, updated_at, ...rest } = editForm.value as Personnel
  const payload = {
    ...rest,
    // 后端 PersonnelUpdate 接受的字段，不发送废弃字段
    name: rest.name,
    role: rest.role,
    responsibility: rest.responsibility,
    skills: rest.skills,
    status: rest.status,
    upcoming_leaves: rest.upcoming_leaves,
    age: rest.age,
    gender: rest.gender,
    native_place: rest.native_place,
    hire_date: rest.hire_date,
    education: rest.education,
    salary: rest.salary
  }

  submitting.value = true
  try {
    await updatePersonnel(personnelId, payload)
    ElMessage.success('更新成功')
    editDialogVisible.value = false
    emit('updated')
  } catch (error) {
    console.error('Update failed:', error)
    ElMessage.error(`保存失败: ${error instanceof Error ? error.message : String(error)}`)
  } finally {
    submitting.value = false
  }
}

const handleDeletePersonnel = async () => {
  if (!props.personnel.id) return
  try {
    await ElMessageBox.confirm(
      '此操作将从数据库和图谱中永久删除该员工数据，是否继续？',
      '警告',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deletePersonnel(props.personnel.id)
    ElMessage.success('员工已删除')
    editDialogVisible.value = false
    emit('updated')
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}
</script>
