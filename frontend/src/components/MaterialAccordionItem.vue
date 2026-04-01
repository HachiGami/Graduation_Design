<template>
  <div class="material-accordion-item">
    <div class="accordion-header" @click="toggle" :class="{ 'is-open': isOpen }">
      <div class="header-left">
        <span class="material-name">{{ material.name }}</span>
        <span class="material-quantity">{{ material.quantity }} {{ material.unit }}</span>
        <el-tag 
          v-if="material.remaining_days > 0 && material.remaining_days <= 7" 
          type="danger" 
          effect="dark" 
          size="small"
          class="warning-tag"
        >
          会在 {{ material.remaining_days.toFixed(1) }} 天内耗尽
        </el-tag>
      </div>
      <div class="header-right">
        <el-icon class="toggle-icon" :class="{ 'is-rotated': isOpen }"><ArrowRight /></el-icon>
      </div>
    </div>
    
    <el-collapse-transition>
      <div v-show="isOpen" class="accordion-body">
        <div class="info-section">
          <div class="info-item">
            <span class="label">总消耗速度:</span>
            <span class="value">{{ material.daily_consumption != null ? Number(material.daily_consumption).toFixed(2) : '暂无' }} {{ material.unit }}/天</span>
          </div>
          <div class="info-item">
            <span class="label">预估可运行时间:</span>
            <span class="value">{{ material.remaining_days == null ? '暂无' : (material.remaining_days === -1 ? '充足' : Number(material.remaining_days).toFixed(1) + ' 天') }}</span>
          </div>
        </div>
        
        <div class="activities-section" v-if="material.serving_activities_details && material.serving_activities_details.length > 0">
          <div class="section-title">正在使用的活动:</div>
          <ul class="activity-list">
            <li v-for="(detail, index) in material.serving_activities_details" :key="index">
              <span class="act-name">
                {{ detail.activity_name }}
                <span class="act-process">(归属: {{ formatProcessName(detail.process_id) }})</span>
              </span>
              <span class="act-rate">
                消耗速率: {{ detail.hourly_consumption != null ? Number(detail.hourly_consumption).toFixed(2) : '0.00' }} {{ material.unit }}/小时,
                共 {{ detail.daily_consumption != null ? Number(detail.daily_consumption).toFixed(1) : '0.0' }} {{ material.unit }}/天
              </span>
            </li>
          </ul>
        </div>
        <div class="activities-section" v-else>
          <div class="empty-text">无关联活动，空闲</div>
        </div>
        
        <div class="actions-section">
          <el-button type="primary" size="small" :icon="Operation" @click.stop="handleReplenish">修改库存</el-button>
          <el-button type="default" size="small" @click.stop="handleEdit">✏️ 编辑</el-button>
        </div>
      </div>
    </el-collapse-transition>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { ArrowRight, Operation } from '@element-plus/icons-vue';

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

const emit = defineEmits(['replenish', 'edit']);

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
</script>

<style scoped>
.material-accordion-item {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  margin-bottom: 10px;
  background-color: #fff;
  overflow: hidden;
}

.accordion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  background-color: #f8f9fa;
  transition: background-color 0.3s;
}

.accordion-header:hover {
  background-color: #f0f2f5;
}

.accordion-header.is-open {
  border-bottom: 1px solid #ebeef5;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.material-name {
  font-weight: bold;
  font-size: 16px;
  color: #303133;
}

.material-quantity {
  color: #606266;
  font-size: 14px;
}

.warning-tag {
  margin-left: 8px;
}

.toggle-icon {
  transition: transform 0.3s;
  color: #909399;
}

.toggle-icon.is-rotated {
  transform: rotate(90deg);
}

.accordion-body {
  padding: 16px;
}

.info-section {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-item .label {
  color: #909399;
  font-size: 14px;
}

.info-item .value {
  color: #303133;
  font-size: 14px;
  font-weight: 500;
}

.section-title {
  font-size: 14px;
  font-weight: bold;
  color: #606266;
  margin-bottom: 8px;
}

.activity-list {
  list-style: none;
  padding: 0;
  margin: 0 0 16px 0;
  background-color: #f5f7fa;
  border-radius: 4px;
  padding: 8px 12px;
}

.activity-list li {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 0;
  font-size: 13px;
  color: #606266;
}

.act-process {
  font-size: 12px;
  color: #909399;
  margin-left: 4px;
}

.act-rate {
  font-size: 12px;
  color: #409eff;
}

.activity-list li:not(:last-child) {
  border-bottom: 1px dashed #ebeef5;
}

.empty-text {
  color: #909399;
  font-size: 13px;
  margin-bottom: 16px;
  font-style: italic;
}

.actions-section {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
