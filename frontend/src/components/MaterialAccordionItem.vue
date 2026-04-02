<template>
  <div class="border-b border-slate-100">
    <div class="flex px-9 py-4 items-center cursor-pointer hover:bg-slate-50/70 transition-colors" @click="toggle">
      <div class="w-8 flex items-center justify-center">
        <el-icon class="text-slate-400 transition-transform duration-300" :class="{ 'rotate-90': isOpen }">
          <ArrowRight />
        </el-icon>
      </div>
      <div class="flex-1 flex items-center">
        <div
          class="w-10 h-10 rounded-lg border flex items-center justify-center mr-3"
          :class="material.remaining_days > 0 && material.remaining_days <= 7 ? 'bg-red-50 text-red-500 border-red-100' : 'bg-slate-100 text-slate-500 border-slate-200'"
        >
          <el-icon><Box /></el-icon>
        </div>
        <div class="flex flex-col">
          <div class="text-base font-bold text-slate-800">{{ material.name }}</div>
          <div class="flex items-end gap-1">
            <span class="text-base font-black text-slate-700">{{ material.quantity }}</span>
            <span class="text-xs font-bold text-slate-500">{{ material.unit }}</span>
          </div>
        </div>
      </div>
      <div class="w-48">
        <div class="text-sm font-bold text-slate-700">
          {{ material.daily_consumption }}
          <span class="text-xs text-slate-400">{{ material.unit }}/天</span>
        </div>
      </div>
      <div class="w-48">
        <span
          v-if="material.remaining_days > 0 && material.remaining_days <= 7"
          class="flex items-center px-2.5 py-1 bg-red-50 text-red-600 border border-red-200 rounded-lg text-xs font-bold shadow-sm w-fit"
        >
          <div class="w-1.5 h-1.5 rounded-full bg-red-500 mr-1.5 animate-pulse"></div>
          仅剩 {{ material.remaining_days }} 天
        </span>
        <span v-else class="text-xs font-bold text-slate-400 flex items-center">
          <el-icon class="mr-1 text-emerald-400"><Select /></el-icon>
          充足
        </span>
      </div>
      <div class="w-32 flex justify-end space-x-1">
        <button
          type="button"
          class="p-2 text-blue-500 hover:bg-blue-50 rounded-lg transition-colors border border-transparent hover:border-blue-100"
          @click.stop="handleReplenish"
        >
          <el-icon><Operation /></el-icon>
        </button>
        <button
          type="button"
          class="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
          @click.stop="handleEdit"
        >
          <el-icon><Edit /></el-icon>
        </button>
        <button
          type="button"
          class="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          @click.stop="handleEdit"
        >
          <el-icon><Delete /></el-icon>
        </button>
      </div>
    </div>

    <el-collapse-transition>
      <div v-show="isOpen" class="bg-[#f8fafc] border-t border-blue-100 shadow-[inset_0_4px_6px_-6px_rgba(0,0,0,0.1)] p-6 px-12">
        <h4 class="text-sm font-bold text-slate-700 mb-4 flex items-center">
          <el-icon class="mr-2 text-blue-500"><DataAnalysis /></el-icon>
          正在使用的关联活动
        </h4>
        <div v-if="material.serving_activities_details && material.serving_activities_details.length > 0">
          <div
            v-for="(task, index) in material.serving_activities_details"
            :key="index"
            class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-2 shadow-sm hover:border-blue-200 transition-colors mb-3"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="flex min-w-0 items-center">
                <div class="w-6 h-6 rounded bg-indigo-50 flex items-center justify-center mr-2 text-indigo-500">
                  <el-icon><Link /></el-icon>
                </div>
                <span class="font-bold text-slate-800 text-sm mr-3 truncate">{{ task.activity_name }}</span>
                <span class="px-2 py-0.5 text-[10px] font-bold border rounded bg-emerald-50 text-emerald-600 border-emerald-200">进行中</span>
                <div class="ml-3 flex items-center text-[11px] font-bold text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  <el-icon class="mr-1.5 text-blue-500"><Share /></el-icon>
                  {{ task.process || formatProcessName(task.process_id) }}
                </div>
              </div>
              <el-button class="!border-blue-200 !bg-white !text-blue-600" plain @click="goToActivityDetail(task)">
                查看活动详情
              </el-button>
            </div>

            <div class="flex items-center text-xs font-medium text-blue-600 ml-8 bg-blue-50/50 w-fit px-2 py-1 rounded">
              消耗速率:
              <span class="font-bold mx-1">{{ task.hourly_rate ?? task.rate ?? task.hourly_consumption ?? '0.00' }}</span>
              {{ material.unit }}/小时，
              共计
              <span class="font-bold mx-1">{{ task.daily_rate ?? computeDailyConsumption(task).toFixed(1) }}</span>
              {{ material.unit }}/天
            </div>
          </div>
        </div>
        <div
          v-else
          class="py-8 border-2 border-dashed border-slate-200 rounded-xl text-center text-sm font-medium text-slate-400"
        >
          该原料当前未分配给任何进行中的活动，处于空闲状态
        </div>
      </div>
    </el-collapse-transition>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { ArrowRight, Box, DataAnalysis, Delete, Edit, Link, Operation, Select, Share } from '@element-plus/icons-vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';

const props = defineProps({
  material: {
    type: Object,
    required: true
  }
});

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
}

const formatProcessName = (processId: string) => {
  if (!processId) return '未知流程'
  if (processMap[processId]) return `${processId} - ${processMap[processId]}`
  const prefix = processId.charAt(0).toUpperCase()
  const typeMap: Record<string, string> = {
    'P': '生产流程', 'Q': '质检流程',
    'S': '销售流程', 'W': '仓储流程', 'T': '运输流程'
  }
  return `${processId} - ${typeMap[prefix] || '未知流程'}`
}

const parseWorkingHours = (workingHours: any): number => {
  if (!workingHours) return 0;
  const calcPeriod = (start: string, end: string): number => {
    if (!start || !end || !start.includes(':') || !end.includes(':')) return 0;
    const [sh, sm] = start.split(':').map(Number);
    const [eh, em] = end.split(':').map(Number);
    if ([sh, sm, eh, em].some(Number.isNaN)) return 0;
    return ((eh * 60 + em) - (sh * 60 + sm)) / 60;
  };
  if (Array.isArray(workingHours)) {
    return workingHours.reduce((sum: number, item: any) => sum + calcPeriod(item?.start_time, item?.end_time), 0);
  }
  if (typeof workingHours === 'string') {
    return workingHours.split(',').reduce((sum: number, period: string) => {
      const [start, end] = period.trim().split('-').map(s => s.trim());
      return sum + calcPeriod(start, end);
    }, 0);
  }
  return 0;
};

const computeDailyConsumption = (detail: any): number => {
  if (detail?.daily_consumption != null) return Number(detail.daily_consumption) || 0;
  const rate = detail?.rate ?? detail?.hourly_consumption ?? 0;
  const totalHours = parseWorkingHours(detail?.working_hours);
  return Number(rate || 0) * totalHours;
};

const emit = defineEmits(['replenish', 'edit']);
const router = useRouter();

const isOpen = ref(false);

const toggle = () => {
  isOpen.value = !isOpen.value;
};

const handleReplenish = () => {
  emit('replenish', props.material);
};

const handleEdit = () => {
  emit('edit', props.material);
};

const goToActivityDetail = (task: any) => {
  const activityId = task?.activity_id || task?.id || task?._id;
  if (!activityId) {
    ElMessage.warning('当前任务缺少 activity_id，暂无法定位活动详情');
    return;
  }
  router.push({
    name: 'Dashboard',
    query: {
      highlightId: String(activityId)
    }
  });
};
</script>
