<template>
  <div class="resources-panel" v-loading="loading" element-loading-text="加载资源数据中...">
    <!-- 横向 Tabs -->
    <el-tabs v-model="activeTab" type="border-card" class="resource-tabs">
      <!-- ── 人员配置 ───────────────────────────────────── -->
      <el-tab-pane name="personnel">
        <template #label>
          <span class="tab-label">
            人员配置
            <el-badge
              v-if="draftReqs.personnel.length"
              :value="draftReqs.personnel.length"
              type="primary"
              class="tab-badge"
            />
          </span>
        </template>
        <div class="tab-body">
          <div v-if="!draftReqs.personnel.length" class="empty-hint">
            暂无人员配置，点击下方按钮添加人员需求
          </div>
          <TransitionGroup name="row-fade" tag="div" class="entry-list">
            <div
              v-for="(entry, index) in draftReqs.personnel"
              :key="`p-${index}`"
              class="entry-row"
            >
              <span class="row-index">{{ index + 1 }}</span>
              <el-select
                v-model="entry.role"
                placeholder="选择职位"
                class="select-role"
                filterable
                @change="onRoleChange(index)"
              >
                <el-option
                  v-for="role in availableRoles"
                  :key="role"
                  :label="role"
                  :value="role"
                />
              </el-select>
              <el-select
                v-model="entry.personnel_id"
                placeholder="选择具体人员"
                class="select-person"
                filterable
                :disabled="!entry.role"
              >
                <el-option
                  v-for="person in getFilteredPersonnel(entry.role)"
                  :key="person.id"
                  :label="person.name"
                  :value="person.id"
                />
                <template #empty>
                  <div class="select-empty">{{ entry.role ? '该职位暂无可用人员' : '请先选择职位' }}</div>
                </template>
              </el-select>
              <el-button
                type="danger"
                :icon="Delete"
                circle
                size="small"
                @click="removePersonnelEntry(index)"
              />
            </div>
          </TransitionGroup>
          <el-button type="primary" plain size="small" class="add-btn" @click="addPersonnelEntry">
            <el-icon><Plus /></el-icon>
            添加人员
          </el-button>
        </div>
      </el-tab-pane>

      <!-- ── 设备配置 ───────────────────────────────────── -->
      <el-tab-pane name="equipment">
        <template #label>
          <span class="tab-label">
            设备配置
            <el-badge
              v-if="draftReqs.equipment.length"
              :value="draftReqs.equipment.length"
              type="primary"
              class="tab-badge"
            />
          </span>
        </template>
        <div class="tab-body">
          <div v-if="!draftReqs.equipment.length" class="empty-hint">
            暂无设备配置，点击下方按钮添加设备需求
          </div>
          <TransitionGroup name="row-fade" tag="div" class="entry-list">
            <div
              v-for="(entry, index) in draftReqs.equipment"
              :key="`e-${index}`"
              class="entry-row"
            >
              <span class="row-index">{{ index + 1 }}</span>
              <el-select
                v-model="entry.equipment_type"
                placeholder="选择设备种类"
                class="select-role"
                filterable
                @change="onEquipmentTypeChange(index)"
              >
                <el-option
                  v-for="type in availableEquipmentTypes"
                  :key="type"
                  :label="type"
                  :value="type"
                />
              </el-select>
              <el-select
                v-model="entry.equipment_id"
                placeholder="选择具体设备"
                class="select-person"
                filterable
                :disabled="!entry.equipment_type"
              >
                <el-option
                  v-for="eq in getFilteredEquipment(entry.equipment_type)"
                  :key="eq.id"
                  :label="eq.name"
                  :value="eq.id"
                />
                <template #empty>
                  <div class="select-empty">{{ entry.equipment_type ? '该种类暂无可用设备' : '请先选择设备种类' }}</div>
                </template>
              </el-select>
              <el-button
                type="danger"
                :icon="Delete"
                circle
                size="small"
                @click="removeEquipmentEntry(index)"
              />
            </div>
          </TransitionGroup>
          <el-button type="primary" plain size="small" class="add-btn" @click="addEquipmentEntry">
            <el-icon><Plus /></el-icon>
            添加设备
          </el-button>
        </div>
      </el-tab-pane>

      <!-- ── 原料配置 ───────────────────────────────────── -->
      <el-tab-pane name="materials">
        <template #label>
          <span class="tab-label">
            原料配置
            <el-badge
              v-if="draftReqs.materials.length"
              :value="draftReqs.materials.length"
              type="primary"
              class="tab-badge"
            />
          </span>
        </template>
        <div class="tab-body">
          <div v-if="!draftReqs.materials.length" class="empty-hint">
            暂无原料配置，点击下方按钮添加消耗原料
          </div>
          <TransitionGroup name="row-fade" tag="div" class="entry-list">
            <div
              v-for="(entry, index) in draftReqs.materials"
              :key="`m-${index}`"
              class="entry-row"
            >
              <span class="row-index">{{ index + 1 }}</span>
              <el-select
                v-model="entry.resource_id"
                placeholder="选择原料"
                class="select-material"
                filterable
              >
                <el-option
                  v-for="mat in allRawMaterials"
                  :key="mat.id"
                  :label="mat.name"
                  :value="mat.id"
                />
              </el-select>
              <div class="rate-group">
                <el-input-number
                  v-model="entry.rate"
                  :min="0"
                  :step="0.1"
                  :precision="2"
                  style="width: 130px"
                  placeholder="消耗速率"
                />
                <span class="unit-label">/ 小时</span>
              </div>
              <el-button
                type="danger"
                :icon="Delete"
                circle
                size="small"
                @click="removeMaterialEntry(index)"
              />
            </div>
          </TransitionGroup>
          <el-button type="primary" plain size="small" class="add-btn" @click="addMaterialEntry">
            <el-icon><Plus /></el-icon>
            添加原料
          </el-button>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- ── 底部保存栏 ──────────────────────────────────────────────── -->
    <div class="save-bar" :class="{ 'save-bar--dirty': isDirty }">
      <div class="save-status">
        <span v-if="isDirty" class="status-dot status-dot--warn">●</span>
        <span v-else class="status-dot status-dot--ok">●</span>
        <span class="status-text">{{ isDirty ? '有未保存的修改' : '配置已保存' }}</span>
      </div>
      <div class="save-actions">
        <el-button size="small" @click="cancelDraft" :disabled="!isDirty || saving">
          取消还原
        </el-button>
        <el-button
          type="primary"
          size="small"
          @click="saveResources"
          :loading="saving"
        >
          保存资源配置
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Plus } from '@element-plus/icons-vue'
import { TransitionGroup } from 'vue'
import { getPersonnelList } from '@/api/personnel'
import { getResources } from '@/api/resource'
import { getActivityResources, updateActivityResources } from '@/api/activity'
import type { Personnel, Resource } from '@/types'

// ── Props ─────────────────────────────────────────────────────────
const props = defineProps<{ activityId: string }>()

// ── Raw data ──────────────────────────────────────────────────────
type PersonnelWithId = Personnel & { id: string }
type ResourceWithId = Resource & { id: string }

const allPersonnel = ref<PersonnelWithId[]>([])
const allResources = ref<ResourceWithId[]>([])
const loading = ref(false)
const saving = ref(false)
const activeTab = ref('personnel')

// ── Computed dictionaries ─────────────────────────────────────────
const availableRoles = computed<string[]>(() =>
  [...new Set(allPersonnel.value.map(p => p.role).filter(Boolean))].sort()
)

const allEquipments = computed<ResourceWithId[]>(() =>
  allResources.value.filter(r => r.type === '设备')
)

const availableEquipmentTypes = computed<string[]>(() =>
  [...new Set(allEquipments.value.map(e => e.specification).filter(Boolean))].sort()
)

const allRawMaterials = computed<ResourceWithId[]>(() =>
  allResources.value.filter(r => r.type === '原料')
)

// ── Draft state types ─────────────────────────────────────────────
interface PersonnelEntry {
  role: string
  personnel_id: string
}
interface EquipmentEntry {
  equipment_type: string
  equipment_id: string
}
interface MaterialEntry {
  resource_id: string
  rate: number
}
interface DraftReqs {
  personnel: PersonnelEntry[]
  equipment: EquipmentEntry[]
  materials: MaterialEntry[]
}

const savedReqs = ref<DraftReqs>({ personnel: [], equipment: [], materials: [] })
const draftReqs = ref<DraftReqs>({ personnel: [], equipment: [], materials: [] })

const isDirty = computed(
  () => JSON.stringify(draftReqs.value) !== JSON.stringify(savedReqs.value)
)

// ── Cascade filter helpers ────────────────────────────────────────
const getFilteredPersonnel = (role: string): PersonnelWithId[] => {
  if (!role) return []
  return allPersonnel.value.filter(
    p => p.role === role && p.status !== 'resigned' && p.status !== 'inactive'
  )
}

const getFilteredEquipment = (type: string): ResourceWithId[] => {
  if (!type) return []
  return allEquipments.value.filter(e => e.specification === type)
}

// ── Entry management ──────────────────────────────────────────────
const addPersonnelEntry = () =>
  draftReqs.value.personnel.push({ role: '', personnel_id: '' })

const removePersonnelEntry = (i: number) =>
  draftReqs.value.personnel.splice(i, 1)

const onRoleChange = (i: number) => {
  draftReqs.value.personnel[i].personnel_id = ''
}

const addEquipmentEntry = () =>
  draftReqs.value.equipment.push({ equipment_type: '', equipment_id: '' })

const removeEquipmentEntry = (i: number) =>
  draftReqs.value.equipment.splice(i, 1)

const onEquipmentTypeChange = (i: number) => {
  draftReqs.value.equipment[i].equipment_id = ''
}

const addMaterialEntry = () =>
  draftReqs.value.materials.push({ resource_id: '', rate: 1.0 })

const removeMaterialEntry = (i: number) =>
  draftReqs.value.materials.splice(i, 1)

// ── Cancel / Restore ──────────────────────────────────────────────
const cancelDraft = () => {
  draftReqs.value = JSON.parse(JSON.stringify(savedReqs.value))
}

// ── Save ──────────────────────────────────────────────────────────
const saveResources = async () => {
  if (!props.activityId) return
  saving.value = true
  try {
    const payload = {
      personnel_roles: draftReqs.value.personnel.map(p => p.role).filter(Boolean),
      equipment_types: draftReqs.value.equipment.map(e => e.equipment_type).filter(Boolean),
      assigned_personnel_ids: draftReqs.value.personnel
        .map(p => p.personnel_id)
        .filter(Boolean),
      assigned_equipment_ids: draftReqs.value.equipment
        .map(e => e.equipment_id)
        .filter(Boolean),
      consumed_resources: draftReqs.value.materials
        .filter(m => m.resource_id)
        .map(m => ({ resource_id: m.resource_id, rate: m.rate })),
    }
    await updateActivityResources(props.activityId, payload)
    savedReqs.value = JSON.parse(JSON.stringify(draftReqs.value))
    ElMessage.success('资源配置已保存')
  } catch {
    ElMessage.error('保存失败，请重试')
  } finally {
    saving.value = false
  }
}

// ── Load initial data ─────────────────────────────────────────────
const loadData = async () => {
  if (!props.activityId) return
  loading.value = true
  try {
    // 第一步：并发加载人员与资源字典（必须成功，用于填充下拉选项）
    const [personnelList, resourceList] = await Promise.all([
      getPersonnelList(),
      getResources(),
    ])

    allPersonnel.value = (personnelList as any[]).map(p => ({
      ...p,
      id: p._id || p.id || '',
    })) as PersonnelWithId[]

    allResources.value = (resourceList as any[]).map(r => ({
      ...r,
      id: r._id || r.id || '',
    })) as ResourceWithId[]

    // 第二步：独立加载该活动当前已保存的资源分配（非致命，失败时以空状态启动）
    let currentResources: {
      assigned_personnel?: { id: string; role: string }[]
      assigned_equipment?: { id: string; specification: string }[]
      consumed_resources?: { resource_id: string; rate: number }[]
    } = {}
    try {
      currentResources = await getActivityResources(props.activityId)
    } catch {
      // 新活动或后端路由尚未就绪时正常静默，字典已加载，用户可正常操作
    }

    const initial: DraftReqs = {
      personnel: (currentResources.assigned_personnel || []).map(p => ({
        role: p.role || '',
        personnel_id: p.id || '',
      })),
      equipment: (currentResources.assigned_equipment || []).map(e => ({
        equipment_type: e.specification || '',
        equipment_id: e.id || '',
      })),
      materials: (currentResources.consumed_resources || []).map(m => ({
        resource_id: m.resource_id || '',
        rate: m.rate || 0,
      })),
    }

    savedReqs.value = JSON.parse(JSON.stringify(initial))
    draftReqs.value = JSON.parse(JSON.stringify(initial))
  } catch {
    ElMessage.error('加载人员/资源字典失败，请刷新页面重试')
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.resources-panel {
  display: flex;
  flex-direction: column;
}

.resource-tabs {
  border-bottom: none;
  border-radius: 4px 4px 0 0;
}

/* Tab 标签 */
.tab-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab-badge {
  line-height: 1;
}

/* Tab 内容区 */
.tab-body {
  min-height: 100px;
  padding: 4px 0 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.empty-hint {
  color: #909399;
  font-size: 13px;
  padding: 20px 0;
  text-align: center;
  background: #fafafa;
  border-radius: 4px;
  border: 1px dashed #dcdfe6;
}

/* 条目行 */
.entry-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.entry-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #ebeef5;
  transition: border-color 0.2s;
}

.entry-row:hover {
  border-color: #c0c4cc;
}

.row-index {
  color: #c0c4cc;
  font-size: 12px;
  min-width: 18px;
  text-align: right;
  flex-shrink: 0;
}

.select-role {
  width: 160px;
  flex-shrink: 0;
}

.select-person,
.select-material {
  flex: 1;
  min-width: 0;
}

.rate-group {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.unit-label {
  font-size: 12px;
  color: #606266;
  white-space: nowrap;
}

.select-empty {
  padding: 10px 16px;
  color: #909399;
  font-size: 13px;
  text-align: center;
}

.add-btn {
  align-self: flex-start;
  margin-top: 2px;
}

/* 底部保存栏 */
.save-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f0f9eb;
  border: 1px solid #b3e19d;
  border-top: none;
  border-radius: 0 0 4px 4px;
  transition: background 0.25s, border-color 0.25s;
}

.save-bar--dirty {
  background: #fdf6ec;
  border-color: #f5dab1;
}

.save-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
}

.status-dot {
  font-size: 10px;
}

.status-dot--ok {
  color: #67c23a;
}

.status-dot--warn {
  color: #e6a23c;
}

.status-text {
  font-size: 12px;
}

.save-actions {
  display: flex;
  gap: 8px;
}

/* 行淡入淡出动画 */
.row-fade-enter-active,
.row-fade-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}

.row-fade-enter-from,
.row-fade-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}
</style>
