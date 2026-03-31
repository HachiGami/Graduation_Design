<template>
  <div class="material-dashboard">
    <div class="dashboard-header">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <h2 style="margin: 0;">原料管理面板</h2>
        <el-button type="primary" :icon="Plus" @click="openAddMaterialDialog">添加原料</el-button>
      </div>
      <div class="filters-container">
        <el-input
          v-model="searchQuery"
          placeholder="按原料名称搜索"
          clearable
          class="filter-item search-input"
          :prefix-icon="Search"
        />
        
        <el-select v-model="sortBy" placeholder="排序方式" class="filter-item">
          <el-option label="默认排序" value="default" />
          <el-option label="存储量 (正序)" value="quantity_asc" />
          <el-option label="存储量 (倒序)" value="quantity_desc" />
          <el-option label="消耗速率 (正序)" value="consumption_asc" />
          <el-option label="消耗速率 (倒序)" value="consumption_desc" />
        </el-select>
        
        <el-select v-model="stockFilter" placeholder="库存状态" class="filter-item">
          <el-option label="全部 (ALL)" value="ALL" />
          <el-option label="库存不足 (SHORTAGE)" value="SHORTAGE" />
          <el-option label="库存充足 (SUFFICIENT)" value="SUFFICIENT" />
        </el-select>
        
        <el-select v-model="processFilter" placeholder="流程筛选" class="filter-item" clearable>
          <el-option
            v-for="(name, id) in processMap"
            :key="id"
            :label="`${id} - ${name}`"
            :value="id"
          />
        </el-select>
      </div>
    </div>

    <div class="dashboard-content" v-loading="loading">
      <div v-if="processedMaterials.length === 0" class="empty-state">
        <el-empty description="暂无符合条件的原料数据" />
      </div>
      <div v-else class="material-list">
        <MaterialAccordionItem
          v-for="material in processedMaterials"
          :key="material._id"
          :material="material"
          @replenish="openReplenishDialog"
          @edit="openEditDialog"
        />
      </div>
    </div>

    <!-- 补货弹窗 -->
    <el-dialog v-model="replenishDialogVisible" title="原料补货" width="400px">
      <el-form :model="replenishForm" label-width="100px">
        <el-form-item label="原料名称">
          <span>{{ currentMaterial?.name }}</span>
        </el-form-item>
        <el-form-item label="当前库存">
          <span>{{ currentMaterial?.quantity }} {{ currentMaterial?.unit }}</span>
        </el-form-item>
        <el-form-item label="补货数量" required>
          <el-input-number v-model="replenishForm.add_amount" :min="0.1" :step="10" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="replenishDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitReplenish" :loading="submitting">确认补货</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑原料信息" width="500px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="原料名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="editForm.unit" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div style="display: flex; justify-content: space-between; width: 100%;">
          <el-button type="danger" @click="handleDeleteMaterial">删除该原料</el-button>
          <div>
            <el-button @click="editDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="submitEdit" :loading="submitting">保存修改</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 添加原料弹窗 -->
    <el-dialog v-model="addMaterialDialogVisible" title="添加原料" width="520px">
      <el-form :model="addMaterialForm" label-width="100px" size="default">
        <el-form-item label="原料名称" required>
          <el-input v-model="addMaterialForm.name" placeholder="如：全脂生牛乳" />
        </el-form-item>
        <el-form-item label="型号/规格" required>
          <el-input v-model="addMaterialForm.specification" placeholder="如：生乳-A级" />
        </el-form-item>
        <el-form-item label="供应商" required>
          <el-input v-model="addMaterialForm.supplier" placeholder="供应商名称" />
        </el-form-item>
        <el-form-item label="初始库存" required>
          <el-input-number v-model="addMaterialForm.quantity" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="单位" required>
          <el-input v-model="addMaterialForm.unit" placeholder="如：吨、升、kg" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addMaterialDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAddMaterial" :loading="addMaterialSubmitting">确定添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { Search, Plus } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import MaterialAccordionItem from '../components/MaterialAccordionItem.vue';
import axios from 'axios';
import { createResource, deleteResource } from '@/api/resource';

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

const materials = ref<any[]>([]);
const loading = ref(false);

// Filters
const searchQuery = ref('');
const sortBy = ref('default');
const stockFilter = ref('ALL');
const processFilter = ref('');

// Dialogs
const replenishDialogVisible = ref(false);
const editDialogVisible = ref(false);
const submitting = ref(false);
const currentMaterial = ref<any>(null);

const replenishForm = ref({
  add_amount: 0
});

const editForm = ref({
  name: '',
  unit: ''
});

const fetchMaterials = async () => {
  loading.value = true;
  try {
    const response = await axios.get('http://localhost:8000/api/resources', {
      params: { type: '原料' }
    });
    materials.value = response.data;
  } catch (error) {
    console.error('Failed to fetch materials:', error);
    ElMessage.error('获取原料数据失败');
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchMaterials();
});

// Computed pipeline
const processedMaterials = computed(() => {
  let result = [...materials.value];

  // 1. Search
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    result = result.filter(m => m.name && m.name.toLowerCase().includes(query));
  }

  // 2. Stock Filter
  if (stockFilter.value === 'SHORTAGE') {
    result = result.filter(m => m.remaining_days > 0 && m.remaining_days <= 7);
  } else if (stockFilter.value === 'SUFFICIENT') {
    result = result.filter(m => m.remaining_days > 7 || m.remaining_days === -1);
  }

  // 3. Process Filter
  if (processFilter.value) {
    result = result.filter(m => m.serving_processes && m.serving_processes.includes(processFilter.value));
  }

  // 4. Sort
  if (sortBy.value === 'quantity_asc') {
    result.sort((a, b) => a.quantity - b.quantity);
  } else if (sortBy.value === 'quantity_desc') {
    result.sort((a, b) => b.quantity - a.quantity);
  } else if (sortBy.value === 'consumption_asc') {
    result.sort((a, b) => a.daily_consumption - b.daily_consumption);
  } else if (sortBy.value === 'consumption_desc') {
    result.sort((a, b) => b.daily_consumption - a.daily_consumption);
  }

  return result;
});

const openReplenishDialog = (material: any) => {
  currentMaterial.value = material;
  replenishForm.value.add_amount = 10;
  replenishDialogVisible.value = true;
};

const submitReplenish = async () => {
  if (!currentMaterial.value) return;
  
  submitting.value = true;
  try {
    const currentQty = Number(currentMaterial.value.quantity) || 0;
    await axios.put(`http://localhost:8000/api/resources/${currentMaterial.value._id}`, {
      quantity: currentQty + Number(replenishForm.value.add_amount)
    });
    ElMessage.success('补货成功');
    replenishDialogVisible.value = false;
    fetchMaterials();
  } catch (error) {
    console.error('Failed to replenish:', error);
    ElMessage.error('补货失败');
  } finally {
    submitting.value = false;
  }
};

const openEditDialog = (material: any) => {
  currentMaterial.value = material;
  editForm.value = {
    name: material.name || '',
    unit: material.unit || ''
  };
  editDialogVisible.value = true;
};

const submitEdit = async () => {
  if (!currentMaterial.value) return;
  
  submitting.value = true;
  try {
    await axios.put(`http://localhost:8000/api/resources/${currentMaterial.value._id}`, editForm.value);
    ElMessage.success('修改成功');
    editDialogVisible.value = false;
    fetchMaterials();
  } catch (error) {
    console.error('Failed to edit:', error);
    ElMessage.error('修改失败');
  } finally {
    submitting.value = false;
  }
};

const handleDeleteMaterial = async () => {
  if (!currentMaterial.value?._id) return;
  try {
    await ElMessageBox.confirm(
      '此操作将从数据库和图谱中永久删除该原料数据，是否继续？',
      '警告',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
    );
    await deleteResource(currentMaterial.value._id);
    ElMessage.success('原料已删除');
    editDialogVisible.value = false;
    fetchMaterials();
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error('删除失败');
  }
};

const addMaterialDialogVisible = ref(false);
const addMaterialSubmitting = ref(false);

const defaultAddMaterialForm = () => ({
  name: '',
  type: '原料',
  specification: '',
  supplier: '',
  quantity: 0,
  unit: '',
  status: 'available'
});

const addMaterialForm = ref(defaultAddMaterialForm());

const openAddMaterialDialog = () => {
  addMaterialForm.value = defaultAddMaterialForm();
  addMaterialDialogVisible.value = true;
};

const submitAddMaterial = async () => {
  if (!addMaterialForm.value.name.trim()) {
    ElMessage.warning('原料名称不能为空');
    return;
  }
  if (!addMaterialForm.value.unit.trim()) {
    ElMessage.warning('单位不能为空');
    return;
  }
  addMaterialSubmitting.value = true;
  try {
    await createResource(addMaterialForm.value as any);
    ElMessage.success('原料添加成功');
    addMaterialDialogVisible.value = false;
    fetchMaterials();
  } catch (error) {
    ElMessage.error('添加失败，请检查表单数据');
  } finally {
    addMaterialSubmitting.value = false;
  }
};
</script>

<style scoped>
.material-dashboard {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.dashboard-header {
  margin-bottom: 20px;
}

.dashboard-header h2 {
  margin: 0 0 16px 0;
  color: #303133;
}

.filters-container {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-item {
  width: 200px;
}

.search-input {
  width: 250px;
}

.dashboard-content {
  flex: 1;
  overflow-y: auto;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.material-list {
  display: flex;
  flex-direction: column;
}
</style>
