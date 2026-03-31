<template>
  <el-collapse-item :name="personnel.id">
    <template #title>
      <div class="accordion-header">
        <div class="header-left">
          <span class="name">{{ personnel.name }}</span>
          <el-tag size="small" type="info" class="ml-2">{{ personnel.role }}</el-tag>
          <el-tag size="small" type="warning" class="ml-2" v-if="personnel.department">{{ personnel.department }}</el-tag>
          <el-tag size="small" :type="personnel.status === 'active' ? 'success' : 'info'" class="ml-2">
            {{ personnel.status === 'active' ? '在职' : '离职' }}
          </el-tag>
          <el-tag size="small" type="danger" class="ml-2" v-if="personnel.upcoming_leaves && personnel.upcoming_leaves.length > 0">
            请假: {{ personnel.upcoming_leaves.join(', ') }}
          </el-tag>
        </div>
        <div class="header-right" @click.stop>
          <el-button type="primary" link icon="Edit" @click="handleEdit">✏️编辑</el-button>
        </div>
      </div>
    </template>
    
    <div class="accordion-body">
      <el-descriptions border :column="3" size="small" class="detail-grid">
        <el-descriptions-item label="年龄">{{ personnel.age || '-' }}</el-descriptions-item>
        <el-descriptions-item label="性别">{{ personnel.gender || '-' }}</el-descriptions-item>
        <el-descriptions-item label="籍贯">{{ personnel.native_place || '-' }}</el-descriptions-item>
        <el-descriptions-item label="入职日期">{{ personnel.hire_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="学历">{{ personnel.education || '-' }}</el-descriptions-item>
        <el-descriptions-item label="薪资">{{ personnel.salary ? `¥${personnel.salary}/月` : '-' }}</el-descriptions-item>
      </el-descriptions>

      <div class="tasks-section mt-3">
        <h4>从事的工作 (分配的任务)</h4>
        <el-empty v-if="!personnel.assigned_tasks || personnel.assigned_tasks.length === 0" description="暂无分配任务" :image-size="60"></el-empty>
        <ul v-else>
          <li v-for="(task, index) in personnel.assigned_tasks" :key="index">{{ task }}</li>
        </ul>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑员工信息" width="500px" append-to-body>
      <el-form :model="editForm" label-width="100px" size="default">
        <el-form-item label="姓名">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="角色">
          <el-input v-model="editForm.role" />
        </el-form-item>
        <el-form-item label="职责(部门)">
          <el-input v-model="editForm.responsibility" />
        </el-form-item>
        <el-form-item label="状态">
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
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitEdit" :loading="submitting">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </el-collapse-item>
</template>

<script setup lang="ts">
import { ref, PropType } from 'vue'
import { ElMessage } from 'element-plus'
import { updatePersonnel } from '@/api/personnel'
import type { Personnel } from '@/types'

const props = defineProps({
  personnel: {
    type: Object as PropType<Personnel>,
    required: true
  }
})

const emit = defineEmits(['updated'])

const editDialogVisible = ref(false)
const submitting = ref(false)
const editForm = ref<Partial<Personnel>>({})

const handleEdit = () => {
  editForm.value = { ...props.personnel }
  editDialogVisible.value = true
}

const submitEdit = async () => {
  if (!props.personnel.id) return
  submitting.value = true
  try {
    await updatePersonnel(props.personnel.id, editForm.value)
    ElMessage.success('更新成功')
    editDialogVisible.value = false
    emit('updated')
  } catch (error) {
    console.error('Update failed:', error)
    ElMessage.error('更新失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.accordion-header {
  display: flex;
  justify-content: space-between;
  align-width: center;
  width: 100%;
  padding-right: 10px;
}
.header-left {
  display: flex;
  align-items: center;
}
.name {
  font-weight: bold;
  font-size: 16px;
}
.ml-2 {
  margin-left: 8px;
}
.mt-3 {
  margin-top: 12px;
}
.tasks-section h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #606266;
}
.tasks-section ul {
  margin: 0;
  padding-left: 20px;
  color: #606266;
  font-size: 13px;
}
</style>
