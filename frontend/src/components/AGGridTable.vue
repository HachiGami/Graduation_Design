<template>
  <div class="ag-grid-wrapper">
    <ag-grid-vue
      :style="{ width: '100%', height: height }"
      class="ag-theme-alpine"
      :columnDefs="columnDefs"
      :rowData="rowData"
      :defaultColDef="defaultColDef"
      :pagination="true"
      :paginationPageSize="20"
      @grid-ready="onGridReady"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'

interface Props {
  columnDefs: any[]
  rowData: any[]
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  height: '600px'
})

const gridApi = ref<any>(null)

const defaultColDef = {
  sortable: true,
  filter: true,
  resizable: true,
  flex: 1
}

const onGridReady = (params: any) => {
  gridApi.value = params.api
}

defineExpose({
  gridApi
})
</script>

<style scoped>
.ag-grid-wrapper {
  width: 100%;
}
</style>

