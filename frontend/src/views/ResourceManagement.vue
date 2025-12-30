<template>
  <div class="resource-management">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>资源管理</span>
          <el-button type="primary" @click="handleAdd">添加资源</el-button>
        </div>
      </template>
      
      <el-table :data="resources" stripe>
        <el-table-column prop="name" label="资源名称" />
        <el-table-column prop="type" label="类型" />
        <el-table-column prop="specification" label="规格" />
        <el-table-column prop="supplier" label="供应商" />
        <el-table-column prop="quantity" label="数量">
          <template #default="{ row }">
            {{ row.quantity }} {{ row.unit }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="row.status === 'available' ? 'success' : 'danger'">
              {{ row.status === 'available' ? '可用' : '不可用' }}
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
      :title="isEdit ? '编辑资源' : '添加资源'"
      width="600px"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="资源名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="资源类型">
          <el-input v-model="form.type" />
        </el-form-item>
        <el-form-item label="规格">
          <el-input v-model="form.specification" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="form.supplier" />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="form.quantity" :min="0" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="form.unit" />
        </el-form-item>
        <el-form-item label="使用期限">
          <el-date-picker 
            v-model="form.expiry_date" 
            type="date"
            value-format="YYYY-MM-DDTHH:mm:ss"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status">
            <el-option label="可用" value="available" />
            <el-option label="不可用" value="unavailable" />
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
import { getResources, createResource, updateResource, deleteResource } from '@/api/resource'
import type { Resource } from '@/types'

const resources = ref<Resource[]>([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const form = ref<Resource>({
  name: '',
  type: '',
  specification: '',
  supplier: '',
  quantity: 0,
  unit: '',
  status: 'available'
})

const loadResources = async () => {
  try {
    resources.value = await getResources()
  } catch (error) {
    ElMessage.error('加载资源失败')
  }
}

const handleAdd = () => {
  isEdit.value = false
  form.value = {
    name: '',
    type: '',
    specification: '',
    supplier: '',
    quantity: 0,
    unit: '',
    status: 'available'
  }
  dialogVisible.value = true
}

const handleEdit = (row: Resource) => {
  isEdit.value = true
  form.value = { ...row }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    if (isEdit.value && form.value.id) {
      await updateResource(form.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createResource(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadResources()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (row: Resource) => {
  try {
    await ElMessageBox.confirm('确定删除该资源?', '提示', {
      type: 'warning'
    })
    if (row.id) {
      await deleteResource(row.id)
      ElMessage.success('删除成功')
      loadResources()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadResources()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

