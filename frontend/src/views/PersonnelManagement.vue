<template>
  <div class="personnel-management">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>人员管理</span>
          <el-button type="primary" @click="handleAdd">添加人员</el-button>
        </div>
      </template>
      
      <el-table :data="personnelList" stripe>
        <el-table-column prop="name" label="姓名" />
        <el-table-column prop="role" label="角色" />
        <el-table-column prop="responsibility" label="职责" />
        <el-table-column prop="skills" label="技能">
          <template #default="{ row }">
            <el-tag v-for="skill in row.skills" :key="skill" style="margin-right: 5px">
              {{ skill }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="work_hours" label="工作时间" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '在职' : '离职' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑人员' : '添加人员'"
      width="600px"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="姓名">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="角色">
          <el-input v-model="form.role" />
        </el-form-item>
        <el-form-item label="职责">
          <el-input v-model="form.responsibility" type="textarea" />
        </el-form-item>
        <el-form-item label="技能">
          <el-select v-model="form.skills" multiple placeholder="选择技能">
            <el-option label="质检" value="质检" />
            <el-option label="操作设备" value="操作设备" />
            <el-option label="维护保养" value="维护保养" />
            <el-option label="安全管理" value="安全管理" />
          </el-select>
        </el-form-item>
        <el-form-item label="工作时间">
          <el-input v-model="form.work_hours" placeholder="例如: 8:00-17:00" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status">
            <el-option label="在职" value="active" />
            <el-option label="离职" value="inactive" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPersonnel, createPersonnel, updatePersonnel, deletePersonnel } from '@/api/personnel'
import type { Personnel } from '@/types'

const personnelList = ref<Personnel[]>([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const form = ref<Personnel>({
  name: '',
  role: '',
  responsibility: '',
  skills: [],
  work_hours: '',
  assigned_tasks: [],
  status: 'active'
})

const loadPersonnel = async () => {
  try {
    personnelList.value = await getPersonnel()
  } catch (error) {
    ElMessage.error('加载人员失败')
  }
}

const handleAdd = () => {
  isEdit.value = false
  form.value = {
    name: '',
    role: '',
    responsibility: '',
    skills: [],
    work_hours: '',
    assigned_tasks: [],
    status: 'active'
  }
  dialogVisible.value = true
}

const handleEdit = (row: Personnel) => {
  isEdit.value = true
  form.value = { ...row }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    if (isEdit.value && form.value.id) {
      await updatePersonnel(form.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createPersonnel(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadPersonnel()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (row: Personnel) => {
  try {
    await ElMessageBox.confirm('确定删除该人员?', '提示', {
      type: 'warning'
    })
    if (row.id) {
      await deletePersonnel(row.id)
      ElMessage.success('删除成功')
      loadPersonnel()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadPersonnel()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>




