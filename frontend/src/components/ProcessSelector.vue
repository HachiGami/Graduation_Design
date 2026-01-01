<template>
  <div class="process-selector">
    <el-form :inline="true" :model="selection">
      <el-form-item label="流程域">
        <el-select v-model="selection.domain" placeholder="选择流程域" @change="handleDomainChange" clearable style="width: 150px">
          <el-option label="生产" value="production" />
          <el-option label="运输" value="transport" />
          <el-option label="销售" value="sales" />
          <el-option label="质检" value="quality" />
          <el-option label="仓储" value="warehouse" />
        </el-select>
      </el-form-item>
      <el-form-item label="流程ID">
        <el-select v-model="selection.process_id" placeholder="选择流程" clearable style="width: 150px">
          <el-option
            v-for="process in processOptions"
            :key="process.value"
            :label="process.label"
            :value="process.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="handleApply">定位并高亮</el-button>
        <el-button @click="handleClear">清除高亮</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  domain?: string
  processId?: string
}>()

const emit = defineEmits<{
  change: [domain: string, processId: string]
  clear: []
}>()

const selection = ref({
  domain: props.domain || '',
  process_id: props.processId || ''
})

const processOptionsMap: Record<string, Array<{label: string, value: string}>> = {
  production: [
    { label: 'P001 - 主生产线', value: 'P001' },
    { label: 'P002 - 副生产线', value: 'P002' }
  ],
  transport: [
    { label: 'T001 - 冷链运输', value: 'T001' },
    { label: 'T002 - 常温运输', value: 'T002' }
  ],
  sales: [
    { label: 'S001 - 线上销售', value: 'S001' },
    { label: 'S002 - 线下销售', value: 'S002' }
  ],
  quality: [
    { label: 'Q001 - 常规质检', value: 'Q001' },
    { label: 'Q002 - 专项质检', value: 'Q002' }
  ],
  warehouse: [
    { label: 'W001 - 主仓库', value: 'W001' },
    { label: 'W002 - 分仓库', value: 'W002' }
  ]
}

const processOptions = ref(selection.value.domain ? processOptionsMap[selection.value.domain] : [])

const handleDomainChange = () => {
  processOptions.value = processOptionsMap[selection.value.domain] || []
  if (processOptions.value.length > 0) {
    selection.value.process_id = processOptions.value[0].value
  }
}

const handleApply = () => {
  emit('change', selection.value.domain, selection.value.process_id)
}

const handleClear = () => {
  selection.value.domain = ''
  selection.value.process_id = ''
  processOptions.value = []
  emit('clear')
}

watch(() => [props.domain, props.processId], () => {
  if (props.domain) {
    selection.value.domain = props.domain
    processOptions.value = processOptionsMap[props.domain] || []
  }
  if (props.processId) {
    selection.value.process_id = props.processId
  }
})
</script>

<style scoped>
.process-selector {
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 20px;
}
</style>
