<template>
  <div class="h-full flex flex-col p-5">
    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm flex-1 flex flex-col overflow-hidden">
      <div class="p-5 border-b border-slate-100 flex justify-between items-center bg-white rounded-t-2xl z-10 relative">
        <div class="flex items-center space-x-3">
          <el-input
            v-model="searchQuery"
            placeholder="按原料名称搜索"
            clearable
            class="!w-64"
            :prefix-icon="Search"
          />
          <el-select v-model="sortBy" placeholder="排序方式" class="!w-52">
            <el-option label="默认排序" value="default" />
            <el-option label="存储量 (正序)" value="quantity_asc" />
            <el-option label="存储量 (倒序)" value="quantity_desc" />
            <el-option label="消耗速率 (正序)" value="consumption_asc" />
            <el-option label="消耗速率 (倒序)" value="consumption_desc" />
          </el-select>
          <el-select v-model="stockFilter" placeholder="库存状态" class="!w-52">
            <el-option label="ALL" value="ALL" />
            <el-option label="SHORTAGE" value="SHORTAGE" />
            <el-option label="SUFFICIENT" value="SUFFICIENT" />
          </el-select>
          <el-select v-model="processFilter" placeholder="流程筛选" class="!w-52" clearable>
            <el-option
              v-for="(name, id) in processMap"
              :key="id"
              :label="`${id} - ${name}`"
              :value="id"
            />
          </el-select>
        </div>
        <el-button
          @click="openAddMaterialDialog"
          class="!px-5 !py-2 !bg-blue-600 !text-white !text-sm !font-bold !rounded-lg hover:!bg-blue-700 !shadow-sm !transition-colors !border-0"
        >
          + 添加原料
        </el-button>
      </div>

      <div class="flex-1 overflow-y-auto" v-loading="loading">
        <div
          class="flex px-9 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider items-center sticky top-0 bg-slate-50/95 backdrop-blur-sm border-b border-slate-100 z-10"
        >
          <div class="w-8"></div>
          <div class="flex-1">原料信息与库存</div>
          <div class="w-48">总消耗速度</div>
          <div class="w-48">预估可用时长</div>
          <div class="w-32 text-right">操作</div>
        </div>

        <div v-if="processedMaterials.length === 0" class="h-full flex items-center justify-center">
          <el-empty description="暂无符合条件的原料数据" />
        </div>
        <div v-else class="flex flex-col">
          <MaterialAccordionItem
            v-for="material in processedMaterials"
            :key="material._id"
            :material="material"
            :anchor-id="'material-row-' + String(material._id || material.id || '')"
            :highlighted="highlightedMaterialId === String(material._id || material.id || '')"
            :force-open="highlightedMaterialId === String(material._id || material.id || '')"
            @replenish="openReplenishDialog"
            @edit="openEditDialog"
          />
        </div>
      </div>
    </div>

    <!-- 库存调整弹窗 -->
    <el-dialog v-model="replenishDialogVisible" title="库存调整" width="400px">
      <el-form :model="replenishForm" label-width="100px">
        <el-form-item label="原料名称">
          <span>{{ currentMaterial?.name }}</span>
        </el-form-item>
        <el-form-item label="当前库存">
          <span>{{ currentMaterial?.quantity }} {{ currentMaterial?.unit }}</span>
        </el-form-item>
        <el-form-item label="变动数量" required>
          <el-input-number v-model="replenishForm.change_amount" :step="1" />
          <div class="mt-1.5 text-xs text-slate-400">输入正数增加库存，输入负数减少库存</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="replenishDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitReplenish" :loading="submitting">确认修改</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑弹窗 -->
    <el-dialog
      v-model="editDialogVisible"
      width="450px"
      :show-close="false"
      :align-center="true"
      class="add-entity-dialog edit-material-dialog rounded-2xl overflow-hidden"
      header-class="!p-0 !m-0 !border-0"
      body-class="!p-0"
      footer-class="!p-0"
    >
      <template #header>
        <div class="flex items-center justify-between border-b border-emerald-100 bg-emerald-50/50 px-6 py-4">
          <div class="flex items-center space-x-3">
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-100 text-emerald-600">
              <el-icon :size="18"><Edit /></el-icon>
            </div>
            <h3 class="text-lg font-bold tracking-tight text-slate-800">编辑原料信息</h3>
          </div>
          <el-button link class="text-slate-400 hover:text-slate-600" @click="editDialogVisible = false">
            <el-icon :size="20"><Close /></el-icon>
          </el-button>
        </div>
      </template>

      <div class="bg-white p-6">
        <div class="grid grid-cols-1 gap-5">
          <div class="flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">
              <span class="mr-1 text-red-500">*</span>原料名称
            </label>
            <el-input v-model="editForm.name" placeholder="如：包装材料-1L纸盒" class="custom-input-emerald w-full" />
          </div>
          <div class="flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">单位</label>
            <el-input v-model="editForm.unit" placeholder="如：个" class="custom-input-emerald w-full" />
          </div>
        </div>
      </div>

      <template #footer>
        <div class="flex justify-end space-x-3 border-t border-slate-100 bg-slate-50 px-6 py-4">
          <button
            type="button"
            class="rounded-xl border border-slate-300 bg-white px-5 py-2 text-sm font-bold text-slate-600 transition-colors hover:bg-slate-50"
            @click="editDialogVisible = false"
          >
            取消
          </button>
          <button
            type="button"
            class="rounded-xl bg-emerald-500 px-5 py-2 text-sm font-bold text-white shadow-sm transition-colors hover:bg-emerald-600"
            :disabled="submitting"
            @click="submitEdit"
          >
            {{ submitting ? '提交中…' : '保存修改' }}
          </button>
        </div>
      </template>
    </el-dialog>

    <!-- 添加原料弹窗 -->
    <el-dialog
      v-model="addMaterialDialogVisible"
      width="450px"
      :show-close="false"
      :align-center="true"
      class="add-entity-dialog add-material-dialog rounded-2xl overflow-hidden"
      header-class="!p-0 !m-0 !border-0"
      body-class="!p-0"
      footer-class="!p-0"
    >
      <template #header>
        <div class="flex items-center justify-between border-b border-emerald-100 bg-emerald-50/50 px-6 py-4">
          <div class="flex items-center space-x-3">
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-100 text-emerald-600">
              <el-icon :size="18"><Goods /></el-icon>
            </div>
            <h3 class="text-lg font-bold tracking-tight text-slate-800">添加原料</h3>
          </div>
          <el-button link class="text-slate-400 hover:text-slate-600" @click="addMaterialDialogVisible = false">
            <el-icon :size="20"><Close /></el-icon>
          </el-button>
        </div>
      </template>

      <el-form
        ref="addMaterialFormRef"
        :model="addMaterialForm"
        :rules="addMaterialRules"
        label-width="0"
        class="add-material-inline-form"
        hide-required-asterisk
      >
        <div class="grid grid-cols-1 gap-5 bg-white p-6">
          <el-form-item prop="name" class="!mb-0">
            <div class="flex w-full flex-col space-y-1.5">
              <label class="text-[13px] font-bold text-slate-700">
                <span class="mr-1 text-red-500">*</span>原料名称
              </label>
              <el-input v-model="addMaterialForm.name" placeholder="如：全脂生牛乳" class="custom-input-emerald w-full" />
            </div>
          </el-form-item>
          <el-form-item prop="unit" class="!mb-0">
            <div class="flex w-full flex-col space-y-1.5">
              <label class="text-[13px] font-bold text-slate-700">
                <span class="mr-1 text-red-500">*</span>单位
              </label>
              <el-input v-model="addMaterialForm.unit" placeholder="如：吨、升、kg" class="custom-input-emerald w-full" />
            </div>
          </el-form-item>
        </div>
      </el-form>

      <template #footer>
        <div class="flex justify-end space-x-3 border-t border-slate-100 bg-slate-50 px-6 py-4">
          <button
            type="button"
            class="rounded-xl border border-slate-300 bg-white px-5 py-2 text-sm font-bold text-slate-600 transition-colors hover:bg-slate-50"
            @click="addMaterialDialogVisible = false"
          >
            取消
          </button>
          <button
            type="button"
            class="rounded-xl bg-emerald-500 px-5 py-2 text-sm font-bold text-white shadow-sm transition-colors hover:bg-emerald-600"
            :disabled="addMaterialSubmitting"
            @click="submitAddMaterial"
          >
            {{ addMaterialSubmitting ? '提交中…' : '确定添加' }}
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Search, Goods, Close, Edit } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import type { FormInstance, FormRules } from 'element-plus';
import MaterialAccordionItem from '../components/MaterialAccordionItem.vue';
import axios from 'axios';
import { createResource } from '@/api/resource';

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
const route = useRoute();
const router = useRouter();
const highlightedMaterialId = ref('');

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
  change_amount: 0
});

const editForm = ref({
  name: '',
  unit: ''
});

const handleRouteHighlight = async () => {
  const rawId = route.query.highlightId;
  const highlightId = Array.isArray(rawId) ? rawId[0] : rawId;
  if (!highlightId) return;

  const targetId = String(highlightId);
  const target = materials.value.find(
    (m) => String(m._id || m.id || '') === targetId
  );
  if (!target) {
    ElMessage.warning('未找到目标原料，可能已被删除');
    highlightedMaterialId.value = '';
    const nextQuery = { ...route.query } as Record<string, any>;
    delete nextQuery.highlightId;
    await router.replace({ query: nextQuery });
    return;
  }

  searchQuery.value = '';
  sortBy.value = 'default';
  stockFilter.value = 'ALL';
  processFilter.value = '';
  highlightedMaterialId.value = targetId;

  await nextTick();
  const targetEl = document.getElementById(`material-row-${targetId}`);
  if (!targetEl) {
    ElMessage.warning('定位失败，请稍后重试');
    return;
  }

  targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
  setTimeout(() => {
    highlightedMaterialId.value = '';
  }, 1800);
  const nextQuery = { ...route.query } as Record<string, any>;
  delete nextQuery.highlightId;
  await router.replace({ query: nextQuery });
};

const fetchMaterials = async () => {
  loading.value = true;
  try {
    const response = await axios.get('http://localhost:8000/api/resources', {
      params: { type: '原料' }
    });
    materials.value = response.data;
    await handleRouteHighlight();
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

watch(
  () => route.query.highlightId,
  async () => {
    if (materials.value.length) await handleRouteHighlight();
  }
);

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
  replenishForm.value.change_amount = 0;
  replenishDialogVisible.value = true;
};

const submitReplenish = async () => {
  if (!currentMaterial.value) return;
  
  submitting.value = true;
  try {
    await axios.patch(`http://localhost:8000/api/resources/${currentMaterial.value._id}/stock`, {
      change_amount: Number(replenishForm.value.change_amount)
    });
    ElMessage.success('库存修改成功');
    replenishDialogVisible.value = false;
    await fetchMaterials();
  } catch (error: any) {
    console.error('Failed to replenish:', error);
    ElMessage.error(error?.response?.data?.detail || '库存修改失败');
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

const addMaterialDialogVisible = ref(false);
const addMaterialSubmitting = ref(false);
const addMaterialFormRef = ref<FormInstance>();
const addMaterialRules: FormRules = {
  name: [{ required: true, message: '原料名称不能为空', trigger: 'blur' }],
  unit: [{ required: true, message: '单位不能为空', trigger: 'blur' }]
};

const defaultAddMaterialForm = () => ({
  name: '',
  unit: '',
  status: 'available'
});

const addMaterialForm = ref(defaultAddMaterialForm());

const openAddMaterialDialog = () => {
  addMaterialForm.value = defaultAddMaterialForm();
  addMaterialDialogVisible.value = true;
};

const submitAddMaterial = async () => {
  const valid = await addMaterialFormRef.value?.validate().catch((validationError) => {
    console.warn('原料表单校验失败:', validationError);
    return false;
  });
  if (!valid) {
    ElMessage.warning('请检查表单填写是否有误');
    return;
  }

  const payload = {
    name: addMaterialForm.value.name.trim(),
    unit: addMaterialForm.value.unit.trim(),
    type: '原料',
    status: addMaterialForm.value.status || 'available'
  };

  addMaterialSubmitting.value = true;
  try {
    await createResource(payload as any);
    ElMessage.success('原料添加成功');
    addMaterialDialogVisible.value = false;
    fetchMaterials();
  } catch (error: any) {
    const detail = error?.response?.data?.detail;
    const detailText = Array.isArray(detail)
      ? detail.map((item: any) => `${item?.loc?.join?.('.') || ''}: ${item?.msg || ''}`).join('; ')
      : (typeof detail === 'string' ? detail : (error?.message || '未知错误'));
    ElMessage.error(`添加失败: ${detailText}`);
  } finally {
    addMaterialSubmitting.value = false;
  }
};
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

:deep(.add-material-inline-form .el-form-item__content) {
  margin-left: 0 !important;
  line-height: normal;
}

:deep(.custom-input-emerald .el-input__wrapper),
:deep(.custom-input-emerald .el-textarea__inner) {
  background-color: #f8fafc !important;
  border-radius: 0.75rem !important;
  box-shadow: 0 0 0 1px #e2e8f0 inset !important;
  padding-top: 0.25rem;
  padding-bottom: 0.25rem;
  transition: all 0.2s;
}

:deep(.custom-input-emerald .el-input__wrapper.is-focus),
:deep(.custom-input-emerald .el-textarea__inner:focus) {
  background-color: #ffffff !important;
  box-shadow: 0 0 0 1px #10b981 inset, 0 0 0 4px #d1fae5 !important;
}

:deep(.custom-input-emerald .el-select .el-input__wrapper.is-focus) {
  background-color: #ffffff !important;
  box-shadow: 0 0 0 1px #10b981 inset, 0 0 0 4px #d1fae5 !important;
}
</style>
