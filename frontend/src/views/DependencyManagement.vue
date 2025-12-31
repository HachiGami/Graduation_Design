<template>
  <div class="dependency-management">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>依赖关系管理</span>
          <el-button type="primary" @click="handleAdd">添加依赖</el-button>
        </div>
      </template>
      
      <el-table :data="dependencies" stripe>
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="predecessor_stage" label="前置环节" />
        <el-table-column prop="successor_stage" label="后置环节" />
        <el-table-column prop="dependency_type" label="依赖类型">
          <template #default="{ row }">
            <el-tag v-if="row.dependency_type === 'sequential'" type="primary">顺序</el-tag>
            <el-tag v-else-if="row.dependency_type === 'parallel'" type="success">并行</el-tag>
            <el-tag v-else type="warning">条件</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="time_constraint" label="时间约束">
          <template #default="{ row }">
            {{ row.time_constraint ? row.time_constraint + '分钟' : '-' }}
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
      :title="isEdit ? '编辑依赖关系' : '添加依赖关系'"
      width="600px"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="前置环节">
          <el-select v-model="form.predecessor_stage" placeholder="选择前置环节">
            <el-option label="牛奶接收" value="牛奶接收" />
            <el-option label="消毒处理" value="消毒处理" />
            <el-option label="加热" value="加热" />
            <el-option label="冷却" value="冷却" />
            <el-option label="包装" value="包装" />
            <el-option label="储存" value="储存" />
          </el-select>
        </el-form-item>
        <el-form-item label="后置环节">
          <el-select v-model="form.successor_stage" placeholder="选择后置环节">
            <el-option label="消毒处理" value="消毒处理" />
            <el-option label="加热" value="加热" />
            <el-option label="冷却" value="冷却" />
            <el-option label="包装" value="包装" />
            <el-option label="储存" value="储存" />
            <el-option label="出库" value="出库" />
          </el-select>
        </el-form-item>
        <el-form-item label="依赖类型">
          <el-select v-model="form.dependency_type">
            <el-option label="顺序" value="sequential" />
            <el-option label="并行" value="parallel" />
            <el-option label="条件" value="conditional" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间约束">
          <el-input-number v-model="form.time_constraint" :min="0" placeholder="分钟" />
        </el-form-item>
        <el-form-item label="条件描述" v-if="form.dependency_type === 'conditional'">
          <el-input v-model="form.condition" type="textarea" />
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
import { getDependencies, createDependency, updateDependency, deleteDependency } from '@/api/dependency'
import type { Dependency } from '@/types'

const dependencies = ref<Dependency[]>([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const form = ref<Dependency>({
  name: '',
  predecessor_stage: '',
  successor_stage: '',
  dependency_type: 'sequential'
})

const loadDependencies = async () => {
  try {
    dependencies.value = await getDependencies()
  } catch (error) {
    ElMessage.error('加载依赖关系失败')
  }
}

const handleAdd = () => {
  isEdit.value = false
  form.value = {
    name: '',
    predecessor_stage: '',
    successor_stage: '',
    dependency_type: 'sequential'
  }
  dialogVisible.value = true
}

const handleEdit = (row: Dependency) => {
  isEdit.value = true
  form.value = { ...row }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    if (isEdit.value && form.value.id) {
      await updateDependency(form.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createDependency(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadDependencies()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (row: Dependency) => {
  try {
    await ElMessageBox.confirm('确定删除该依赖关系?', '提示', {
      type: 'warning'
    })
    if (row.id) {
      await deleteDependency(row.id)
      ElMessage.success('删除成功')
      loadDependencies()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadDependencies()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>




