<template>
  <el-collapse
    v-model="expandedPanels"
    :class="[
      'mb-3 overflow-hidden rounded-xl border border-slate-100 bg-white',
      highlighted ? 'activity-highlight-flash' : ''
    ]"
  >
    <el-collapse-item :name="localActivity.id || localActivity.name">
      <template #title>
        <div class="flex w-full items-center gap-4">
          <div class="flex min-w-0 flex-1 flex-col gap-1">
            <div class="flex items-center gap-2">
              <svg
                class="workflow-icon h-[18px] w-[18px]"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <rect x="3" y="3" width="6" height="6" rx="1"></rect>
                <rect x="15" y="3" width="6" height="6" rx="1"></rect>
                <rect x="15" y="15" width="6" height="6" rx="1"></rect>
                <path d="M9 6h6"></path>
                <path d="M18 9v6"></path>
                <path d="M9 6v12h6"></path>
              </svg>
              <span class="truncate text-[15px] font-semibold text-slate-800">{{ localActivity.name }}</span>
            </div>
          </div>
          
          <div class="w-48 shrink-0">
            <el-tag type="info" class="!rounded-full !border-0 !bg-slate-100 !px-3 !py-1 !text-slate-600" disable-transitions>
              {{ localActivity.process_id }} - {{ processMap[localActivity.process_id || ''] || '未知流程' }}
            </el-tag>
          </div>

          <div class="w-32 shrink-0">
            <div
              :class="[
                'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium',
                localActivity.status === 'pending' ? 'bg-slate-100 text-slate-500' : 'bg-blue-50 text-blue-600'
              ]"
            >
              <el-icon v-if="localActivity.status === 'pending'"><Clock /></el-icon>
              <span v-else-if="localActivity.status === 'in_progress'" class="relative flex size-2">
                <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75"></span>
                <span class="relative inline-flex size-2 rounded-full bg-blue-500"></span>
              </span>
              <span>{{ statusText(localActivity.status) }}</span>
            </div>
          </div>

          <div class="flex w-72 shrink-0 items-center justify-end gap-2" @click.stop>
            <el-button 
              v-if="localActivity.status === 'pending'" 
              type="success" 
              class="rounded-md px-4 py-2 font-medium"
              @click="toggleActivityStatus"
            >启动</el-button>
            <el-button 
              v-else-if="localActivity.status === 'in_progress'" 
              type="danger" 
              class="rounded-md px-4 py-2 font-medium"
              @click="toggleActivityStatus"
            >停机</el-button>
            
            <el-button class="rounded-md border-0 !bg-blue-50 !text-blue-600 hover:!bg-blue-100" @click="locateInDependencyView">在视图中查看</el-button>
            
            <div class="mx-1 h-4 w-px bg-slate-200"></div>
            
            <el-button class="border-0 bg-transparent p-2 text-base text-slate-400 hover:!bg-slate-100 hover:!text-blue-500" @click="openEditDialog" title="编辑">
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-button class="border-0 bg-transparent p-2 text-base text-slate-400 hover:!bg-slate-100 hover:!text-blue-500" @click="handleDeleteActivity" title="删除">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
      </template>

      <div class="bg-slate-50 px-6 py-5 shadow-inner shadow-black/5">
        <el-tabs v-model="activeTab" class="custom-tabs">
          <el-tab-pane label="SOP 步骤与详情" name="basic">
            <div class="mb-6 flex gap-4 rounded-xl border border-slate-100 bg-white p-4">
              <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-slate-50">
                <el-icon class="text-2xl text-slate-400"><Document /></el-icon>
              </div>
              <div class="flex-1">
                <div class="mb-1 text-sm font-semibold text-slate-800">活动描述</div>
                <div class="text-[13px] leading-relaxed text-slate-500">{{ localActivity.description || '暂无描述信息' }}</div>
              </div>
            </div>

            <div class="mb-4 flex items-center justify-between">
              <div class="rounded-full bg-indigo-50 px-4 py-1.5 text-[13px] font-semibold text-indigo-600">
                总耗时：{{ totalSopDuration }} 分钟
              </div>
              <el-button type="primary" class="rounded-md" @click="openSopEditDialog">
                <el-icon><Plus /></el-icon> 添加步骤
              </el-button>
            </div>

            <el-table :data="localActivity.sop_steps || []" class="sop-table overflow-hidden rounded-lg border border-slate-100" :show-header="true">
              <el-table-column type="index" label="步骤序号" width="100" align="center" />
              <el-table-column prop="content" label="步骤名称" />
              <el-table-column prop="duration" label="耗时(分钟)" width="150" align="center" />
              <el-table-column label="操作" width="120" align="center">
                <template #default>
                  <el-button type="primary" link @click="openSopEditDialog">编辑</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="发生风险" name="risks">
            <div class="risk-panel">
              <div v-if="activityRisks.length === 0" class="risk-empty-state">
                <el-empty description="当前环节运行健康" :image-size="72">
                  <template #description>
                    <div class="risk-empty-title">当前环节运行健康</div>
                    <div class="risk-empty-subtitle">资源供需平衡，未检测到近期异常</div>
                  </template>
                </el-empty>
              </div>

              <section v-if="shortageRisks.length > 0" class="risk-section risk-section-shortage">
                <div class="risk-section-header">
                  <el-icon class="risk-header-icon danger"><WarningFilled /></el-icon>
                  <span class="risk-section-title">当前短缺</span>
                </div>
                <el-card
                  v-for="(risk, index) in shortageRisks"
                  :key="`shortage-${risk}-${index}`"
                  shadow="never"
                  class="risk-card risk-card-shortage"
                >
                  <div class="risk-card-content">
                    <div class="risk-main-line">
                      <el-icon class="risk-item-icon"><component :is="getShortageRiskIcon(risk)" /></el-icon>
                      <span class="risk-item-text">
                        <template v-for="(segment, segIndex) in splitRiskSegments(risk)" :key="`${risk}-${index}-${segIndex}`">
                          <span :class="{ 'risk-segment-highlight': segment.highlight }">{{ segment.text }}</span>
                        </template>
                      </span>
                    </div>
                    <button
                      v-if="risk.includes('名') || risk.includes('台')"
                      class="risk-action-btn risk-action-alloc"
                      @click="switchToAllocationTab"
                    >
                      去分配
                    </button>
                    <button
                      v-else-if="risk.includes('原料') || risk.includes('不足')"
                      class="risk-action-btn risk-action-replenish"
                      @click="goToMaterialPage"
                    >
                      去补货
                    </button>
                  </div>
                </el-card>
              </section>

              <section v-if="scheduleRisks.length > 0" class="risk-section risk-section-schedule">
                <div class="risk-section-header">
                  <el-icon class="risk-header-icon warning"><Clock /></el-icon>
                  <span class="risk-section-title">排期预警</span>
                </div>
                <el-card
                  v-for="(risk, index) in scheduleRisks"
                  :key="`schedule-${risk}-${index}`"
                  shadow="never"
                  class="risk-card risk-card-schedule"
                >
                  <div class="risk-main-line">
                    <el-icon class="risk-item-icon"><component :is="getScheduleRiskIcon(risk)" /></el-icon>
                    <span class="risk-item-text">
                      <template v-for="(segment, segIndex) in splitRiskSegments(risk)" :key="`${risk}-${index}-${segIndex}`">
                        <span :class="{ 'risk-segment-highlight': segment.highlight }">{{ segment.text }}</span>
                      </template>
                    </span>
                  </div>
                </el-card>
              </section>
            </div>
          </el-tab-pane>

          <el-tab-pane label="资源配置" name="resources" lazy>
            <div class="py-4">
              <div>
                <el-tabs type="card" class="capsule-tabs">
                  <el-tab-pane label="人员配置" name="personnel">
                    <div class="mb-4 flex justify-end">
                      <div class="flex items-center shadow-sm rounded-lg">
                        <select
                          v-model="selectedPersonnelRole"
                          class="border border-slate-200 border-r-0 rounded-l-lg p-2 text-sm outline-none bg-slate-50 w-48 font-medium text-slate-700"
                        >
                          <option value="" disabled>选择职业</option>
                          <option
                            v-for="role in availableRoles"
                            :key="role"
                            :value="role"
                          >
                            {{ role }}
                          </option>
                        </select>
                        <button
                          class="px-4 py-2 bg-blue-50 text-blue-600 text-sm font-bold border border-slate-200 rounded-r-lg hover:bg-blue-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          :disabled="!selectedPersonnelRole"
                          @click="addPersonnelRequirement"
                        >
                          + 增加需求
                        </button>
                      </div>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                      <div
                        v-for="slot in personnelSlots"
                        :key="`person-slot-${slot.index}`"
                        :class="[
                          'rounded-xl border p-4 transition',
                          slot.assigned
                            ? 'border-slate-200 bg-white shadow-sm'
                            : 'border-dashed border-orange-300 bg-orange-50/50'
                        ]"
                      >
                        <div class="mb-3 flex items-start justify-between">
                          <div>
                            <div class="text-sm font-semibold text-slate-800">岗位需求 #{{ slot.index + 1 }}</div>
                            <div class="text-xs text-slate-500">职业：{{ slot.role }}</div>
                          </div>
                          <button class="text-slate-400 hover:text-red-500 tooltip" @click="removePersonnelRequirement(slot.index)">
                            <el-icon :size="16"><Delete /></el-icon>
                          </button>
                        </div>
                        <div v-if="slot.assigned" class="flex items-center justify-between gap-3">
                          <div class="flex items-center gap-3">
                            <div class="w-10 h-10 flex-shrink-0 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold text-sm mr-3 shadow-inner">
                              {{ (slot.assigned.name || '').charAt(0) }}
                            </div>
                            <div>
                              <div class="text-sm font-semibold text-slate-800">{{ slot.assigned.name }}</div>
                              <div class="text-xs text-slate-500">已分配 · {{ slot.assigned.role }}</div>
                            </div>
                          </div>
                          <button
                            class="flex items-center px-3 py-1.5 bg-white border border-red-200 text-red-600 text-xs font-bold rounded-lg hover:bg-red-50 shadow-sm transition-colors"
                            @click="removePersonnel(slot.assigned.id)"
                          >
                            移除解绑
                          </button>
                        </div>
                        <div v-else class="flex items-center justify-between gap-2">
                          <div class="text-sm text-orange-700">待分配：{{ slot.role }}</div>
                          <div class="flex items-center gap-2">
                            <template v-if="activePersonnelAssignIndex === slot.index">
                              <el-select
                                v-model="personnelSlotSelection[slot.index]"
                                placeholder="选择具体人员"
                                style="width: 220px"
                              >
                                <el-option
                                  v-for="person in getFilteredPersonsByRole(slot.role)"
                                  :key="person.id"
                                  :label="person.name"
                                  :value="person.id"
                                />
                              </el-select>
                              <el-button type="primary" size="small" :disabled="!personnelSlotSelection[slot.index]" @click="confirmPersonnelAssign(slot.index)">
                                保存
                              </el-button>
                              <el-button size="small" @click="cancelPersonnelAssign">取消</el-button>
                            </template>
                            <button
                              v-else
                              class="flex items-center px-3 py-1.5 bg-white border border-orange-200 text-orange-600 text-xs font-bold rounded-lg hover:bg-orange-50 shadow-sm transition-colors"
                              @click="startPersonnelAssign(slot.index)"
                            >
                              执行分配
                            </button>
                          </div>
                        </div>
                      </div>
                      <el-empty v-if="!personnelSlots.length" description="暂无岗位需求" :image-size="60" />
                    </div>
                  </el-tab-pane>
                  <el-tab-pane label="设备配置" name="equipment">
                    <div class="mb-4 flex justify-end">
                      <div class="flex items-center shadow-sm rounded-lg">
                        <select
                          v-model="selectedEquipmentSpec"
                          class="border border-slate-200 border-r-0 rounded-l-lg p-2 text-sm outline-none bg-slate-50 w-48 font-medium text-slate-700"
                        >
                          <option value="" disabled>选择设备种类</option>
                          <option
                            v-for="spec in availableSpecs"
                            :key="spec"
                            :value="spec"
                          >
                            {{ spec }}
                          </option>
                        </select>
                        <button
                          class="px-4 py-2 bg-blue-50 text-blue-600 text-sm font-bold border border-slate-200 rounded-r-lg hover:bg-blue-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          :disabled="!selectedEquipmentSpec"
                          @click="addEquipmentRequirement"
                        >
                          + 增加需求
                        </button>
                      </div>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                      <div
                        v-for="slot in equipmentSlots"
                        :key="`equipment-slot-${slot.index}`"
                        :class="[
                          'rounded-xl border p-4 transition',
                          slot.assigned
                            ? 'border-slate-200 bg-white shadow-sm'
                            : 'border-dashed border-orange-300 bg-orange-50/50'
                        ]"
                      >
                        <div class="mb-3 flex items-start justify-between">
                          <div>
                            <div class="text-sm font-semibold text-slate-800">设备需求 #{{ slot.index + 1 }}</div>
                            <div class="text-xs text-slate-500">种类：{{ slot.specification }}</div>
                          </div>
                          <button class="text-slate-400 hover:text-red-500 tooltip" @click="removeEquipmentRequirement(slot.index)">
                            <el-icon :size="16"><Delete /></el-icon>
                          </button>
                        </div>
                        <div v-if="slot.assigned" class="flex items-center justify-between gap-3">
                          <div class="flex items-center gap-3">
                            <div class="resource-icon-wrap"><el-icon><Setting /></el-icon></div>
                            <div>
                              <div class="text-sm font-semibold text-slate-800">{{ slot.assigned.name }}</div>
                              <div class="text-xs text-slate-500">已分配 · {{ slot.assigned.specification }}</div>
                            </div>
                          </div>
                          <button
                            class="flex items-center px-3 py-1.5 bg-white border border-red-200 text-red-600 text-xs font-bold rounded-lg hover:bg-red-50 shadow-sm transition-colors"
                            @click="removeEquipment(slot.assigned.id)"
                          >
                            移除解绑
                          </button>
                        </div>
                        <div v-else class="flex items-center justify-between gap-2">
                          <div class="text-sm text-orange-700">待分配：{{ slot.specification }}</div>
                          <div class="flex items-center gap-2">
                            <template v-if="activeEquipmentAssignIndex === slot.index">
                              <el-select
                                v-model="equipmentSlotSelection[slot.index]"
                                placeholder="选择具体设备"
                                style="width: 220px"
                              >
                                <el-option
                                  v-for="equipment in getFilteredEquipmentBySpec(slot.specification)"
                                  :key="equipment.id"
                                  :label="equipment.name"
                                  :value="equipment.id"
                                />
                              </el-select>
                              <el-button type="primary" size="small" :disabled="!equipmentSlotSelection[slot.index]" @click="confirmEquipmentAssign(slot.index)">
                                保存
                              </el-button>
                              <el-button size="small" @click="cancelEquipmentAssign">取消</el-button>
                            </template>
                            <button
                              v-else
                              class="flex items-center px-3 py-1.5 bg-white border border-orange-200 text-orange-600 text-xs font-bold rounded-lg hover:bg-orange-50 shadow-sm transition-colors"
                              @click="startEquipmentAssign(slot.index)"
                            >
                              执行分配
                            </button>
                          </div>
                        </div>
                      </div>
                      <el-empty v-if="!equipmentSlots.length" description="暂无设备需求" :image-size="60" />
                    </div>
                  </el-tab-pane>
                  <el-tab-pane label="原料配置" name="material">
                    <div class="flex justify-between items-center mb-6">
                      <div class="text-sm font-bold text-slate-700 flex items-center">
                        <Package size="16" class="mr-2 text-emerald-500" />
                        原料配置
                      </div>
                      <button
                        class="flex items-center px-4 py-2 bg-emerald-50 text-emerald-600 text-sm font-bold border border-emerald-200 rounded-lg hover:bg-emerald-100 transition-colors shadow-sm disabled:opacity-50"
                        :disabled="isMaterialAssigning"
                        @click="openMaterialAssignForm"
                      >
                        + 分配原料
                      </button>
                    </div>

                    <div
                      v-if="isMaterialAssigning"
                      class="p-4 bg-emerald-50/50 border border-dashed border-emerald-300 rounded-xl flex items-center space-x-4 mb-3"
                    >
                      <div class="flex-1">
                        <div class="text-[10px] font-bold text-emerald-600 uppercase mb-1">选择原料</div>
                        <select
                          v-model="selectedMaterialId"
                          class="w-full bg-white border border-emerald-200 rounded-lg p-2 text-sm font-medium outline-none"
                        >
                          <option value="" disabled>请选择原料</option>
                          <option
                            v-for="mat in availableMaterials"
                            :key="mat.id"
                            :value="mat.id"
                          >
                            {{ mat.name }}
                          </option>
                        </select>
                      </div>
                      <div class="flex-1">
                        <div class="text-[10px] font-bold text-emerald-600 uppercase mb-1">消耗数量</div>
                        <div class="relative flex items-center">
                          <input
                            v-model.number="selectedMaterialRate"
                            type="number"
                            min="0"
                            step="0.1"
                            class="w-full bg-white border border-emerald-200 rounded-lg p-2 pr-10 text-sm font-medium outline-none"
                            placeholder="请输入消耗数量"
                          />
                          <span class="absolute right-3 text-slate-400 font-bold text-sm">{{ selectedUnit ? `${selectedUnit}/h` : '' }}</span>
                        </div>
                      </div>
                      <div class="flex items-center space-x-2">
                        <button
                          class="p-2 bg-emerald-500 text-white rounded-lg shadow-sm hover:bg-emerald-600"
                          :disabled="!selectedMaterialId"
                          @click="assignMaterial"
                        >
                          <span class="block w-4 text-center text-sm font-bold leading-none">✓</span>
                        </button>
                        <button
                          class="p-2 bg-red-500 text-white rounded-lg shadow-sm hover:bg-red-600"
                          @click="cancelMaterialAssign"
                        >
                          <span class="block w-4 text-center text-sm font-bold leading-none">✕</span>
                        </button>
                      </div>
                    </div>

                    <template v-if="activityResourceState.consumed_resources.length">
                      <div
                        v-for="material in activityResourceState.consumed_resources"
                        :key="material.resource_id"
                        class="p-3 bg-white border border-slate-200 rounded-xl flex items-center justify-between shadow-sm hover:shadow-md hover:border-emerald-200 transition-all group mb-3"
                      >
                        <div class="w-1/3 flex items-center">
                          <div class="w-10 h-10 flex-shrink-0 rounded-xl bg-emerald-50 text-emerald-500 border border-emerald-100 flex items-center justify-center mr-3">
                            <Box size="20" />
                          </div>
                          <div class="text-sm font-bold text-slate-800">{{ material.name }}</div>
                        </div>

                        <div class="flex-1 flex justify-center">
                          <template v-if="editingMaterialId === material.resource_id">
                            <div class="flex items-center space-x-2">
                              <input
                                v-model="editQuantityValue"
                                type="number"
                                min="0"
                                step="0.1"
                                class="w-24 border-b-2 border-emerald-500 bg-emerald-50 px-2 py-1 text-center font-bold text-emerald-700 outline-none"
                              />
                              <span class="text-xs font-bold text-slate-400">{{ getMaterialUnit(material.resource_id) ? `${getMaterialUnit(material.resource_id)}/h` : '' }}</span>
                              <el-button
                                link
                                type="success"
                                :icon="Check"
                                @click.stop="saveEdit(material.resource_id)"
                              >
                                应用
                              </el-button>
                              <el-button
                                link
                                :icon="X"
                                @click.stop="cancelEdit"
                              >
                                取消
                              </el-button>
                            </div>
                          </template>
                          <template v-else>
                            <div
                              class="flex items-baseline space-x-1 px-4 py-1.5 bg-slate-50 rounded-lg border border-slate-100 cursor-pointer hover:bg-emerald-50 transition-colors"
                              @click="startEdit(material)"
                            >
                              <span class="text-lg font-black text-slate-700">{{ material.rate }}</span>
                              <span class="text-xs font-bold text-slate-400">{{ getMaterialUnit(material.resource_id) ? `${getMaterialUnit(material.resource_id)}/h` : '' }}</span>
                            </div>
                          </template>
                        </div>

                        <div class="w-1/3 flex justify-end">
                          <el-button
                            link
                            type="danger"
                            :icon="Delete"
                            @click.stop="removeMaterial(material.resource_id)"
                          >
                            移除
                          </el-button>
                        </div>
                      </div>
                    </template>

                    <div
                      v-else-if="!isMaterialAssigning"
                      class="py-10 text-center text-sm text-slate-400 border-2 border-dashed border-slate-200 rounded-xl"
                    >
                      该活动暂无原料消耗配置
                    </div>
                  </el-tab-pane>
                </el-tabs>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-collapse-item>
  </el-collapse>

  <el-dialog
    v-model="editDialogVisible"
    width="500px"
    :show-close="false"
    :align-center="true"
    append-to-body
    class="add-entity-dialog edit-activity-dialog rounded-2xl overflow-hidden"
    header-class="!p-0 !m-0 !border-0"
    body-class="!p-0"
    footer-class="!p-0"
  >
    <template #header>
      <div class="flex items-center justify-between border-b border-indigo-100 bg-indigo-50/50 px-6 py-4">
        <div class="flex items-center space-x-3">
          <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-100 text-indigo-600">
            <el-icon :size="18"><Edit /></el-icon>
          </div>
          <h3 class="text-lg font-bold tracking-tight text-slate-800">修改活动</h3>
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
            <span class="mr-1 text-red-500">*</span>活动名称
          </label>
          <el-input v-model="editForm.name" placeholder="请输入活动名称" class="custom-input-indigo w-full" />
        </div>

        <div class="grid grid-cols-2 gap-5">
          <div class="flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">
              <span class="mr-1 text-red-500">*</span>流程 ID
            </label>
            <el-select
              v-model="editForm.process_id"
              placeholder="请选择所属流程ID"
              class="custom-input-indigo w-full"
              @change="handleProcessIdChange"
            >
              <el-option
                v-for="item in processOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </div>
          <div class="flex flex-col space-y-1.5">
            <label class="text-[13px] font-bold text-slate-700">状态</label>
            <el-select v-model="editForm.status" class="custom-input-indigo w-full">
              <el-option label="待机中" value="pending" />
              <el-option label="进行中" value="in_progress" />
            </el-select>
          </div>
        </div>

        <div class="flex flex-col space-y-1.5">
          <label class="text-[13px] font-bold text-slate-700">前置活动</label>
          <el-select
            v-model="editForm.predecessor_ids"
            placeholder="输入活动名称进行搜索"
            class="custom-input-indigo w-full"
            clearable
            multiple
            filterable
          >
            <el-option
              v-for="item in predecessorOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </div>

        <div class="flex flex-col space-y-1.5">
          <label class="text-[13px] font-bold text-slate-700">活动描述</label>
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入活动描述"
            class="custom-input-indigo"
          />
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
          class="rounded-xl bg-indigo-600 px-5 py-2 text-sm font-bold text-white shadow-sm transition-colors hover:bg-indigo-700"
          @click="saveActivityEdit"
        >
          保存
        </button>
      </div>
    </template>
  </el-dialog>

  <el-dialog v-model="sopDialogVisible" title="编辑活动 SOP 与详情" width="700px">
    <el-form :model="sopEditForm" label-width="100px">
      <el-form-item label="活动描述">
        <el-input type="textarea" v-model="sopEditForm.description" :rows="3" />
      </el-form-item>
      
      <div class="sop-edit-section">
        <div class="section-title">
          <span>SOP 步骤列表</span>
          <span class="total-hint">当前总耗时: {{ currentSopTotalDuration }} 分钟</span>
        </div>
        
        <div v-for="(step, index) in sopEditForm.sop_steps" :key="index" class="sop-step-item">
          <el-tag type="info" class="step-tag">步骤 {{ index + 1 }}</el-tag>
          <el-input v-model="step.content" placeholder="请输入步骤详情" class="flex-1" />
          <el-input-number v-model="step.duration" :min="0" placeholder="耗时(分)" class="duration-input" />
          <el-button type="danger" icon="Delete" circle @click="removeSopStep(index)" />
        </div>
        
        <el-button type="primary" plain class="w-full mt-4" @click="addSopStep">
          + 添加新步骤
        </el-button>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="sopDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="saveSopEdit">保存 SOP</el-button>
    </template>
  </el-dialog>
  <div v-show="false" class="hidden">
    {{ workingHoursText }}
    {{ statusTagType(localActivity.status) }}
    {{ inferMaterialModelFromRisk('') }}
    {{ domainOptions.length }}
    {{ replenishDialogVisible }}
    <ActivityResourcesPanel :activity-id="activityId" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { WarningFilled, User, Setting, Box, Calendar, Tools, Clock, Document, Edit, Delete, Plus, Check as CheckIcon, Close } from '@element-plus/icons-vue'
import type { Activity } from '@/types'
import ActivityResourcesPanel from './ActivityResourcesPanel.vue'
import {
  getActivity,
  getActivities,
  updateActivity,
  deleteActivity,
  getActivityResources,
  updateActivityResources,
  getOccupiedResources
} from '@/api/activity'
import { getDependencies } from '@/api/dependency'
import { getPersonnelList } from '@/api/personnel'
import { getResources } from '@/api/resource'
import { ElMessageBox } from 'element-plus'
import type { ActivityResourcesData, Personnel, Resource } from '@/types'

const props = withDefaults(defineProps<{
  activity: Activity
  forceExpand?: boolean
  highlighted?: boolean
}>(), {
  forceExpand: false,
  highlighted: false
})
const emit = defineEmits<{ refreshed: [] }>()
const router = useRouter()

const localActivity = ref<Activity>({ ...props.activity })
const expandedPanels = ref<Array<string | number>>([])
const activeTab = ref('basic')
const activityRisks = ref<string[]>([])
const editDialogVisible = ref(false)
const sopDialogVisible = ref(false)
const replenishDialogVisible = ref(false)
type PersonnelWithId = Personnel & { id: string }
type ResourceWithId = Resource & { id: string }
const allPersonnel = ref<PersonnelWithId[]>([])
const allResources = ref<ResourceWithId[]>([])
const occupiedIds = ref<string[]>([])
const selectedPersonnelRole = ref('')
const selectedEquipmentSpec = ref('')
const activePersonnelAssignIndex = ref<number | null>(null)
const activeEquipmentAssignIndex = ref<number | null>(null)
const personnelSlotSelection = ref<Record<number, string>>({})
const equipmentSlotSelection = ref<Record<number, string>>({})
const selectedMaterialId = ref('')
const selectedMaterialRate = ref(1)
const isMaterialAssigning = ref(false)
const editingMaterialId = ref<string | null>(null)
const editQuantityValue = ref<number | string>('')
const activityResourceState = ref<ActivityResourcesData>({
  personnel_roles_required: [],
  equipment_types_required: [],
  assigned_personnel: [],
  assigned_equipment: [],
  consumed_resources: []
})

const editForm = ref<Partial<Activity>>({})
const allActivities = ref<Activity[]>([])
const sopEditForm = ref({
  description: '',
  sop_steps: [] as { content: string, duration: number }[]
})

const currentSopTotalDuration = computed(() => {
  return sopEditForm.value.sop_steps.reduce((sum, step) => sum + (step.duration || 0), 0)
})
const occupiedIdSet = computed<Set<string>>(() => new Set(occupiedIds.value))
const availableRoles = computed(() =>
  [...new Set(allPersonnel.value.map(p => p.role).filter(Boolean))].sort()
)
const availableEquipments = computed(() => allResources.value.filter(r => r.type === '设备'))
const availableSpecs = computed(() =>
  [...new Set(availableEquipments.value.map(e => e.specification).filter(Boolean))].sort()
)
const availableMaterials = computed(() => allResources.value.filter(r => r.type === '原料'))
const selectedUnit = computed(() => {
  if (!selectedMaterialId.value) return ''
  const target = availableMaterials.value.find(r => r.id === selectedMaterialId.value)
  return target?.unit || ''
})
const materialUnitMap = computed(() => {
  const map: Record<string, string> = {}
  availableMaterials.value.forEach((item) => {
    if (item.id) map[item.id] = item.unit || ''
  })
  return map
})
const assignedPersonnelIdSet = computed(() => new Set(activityResourceState.value.assigned_personnel.map(p => p.id)))
const assignedEquipmentIdSet = computed(() => new Set(activityResourceState.value.assigned_equipment.map(e => e.id)))
const personnelSlots = computed(() => {
  const roleQueue = new Map<string, { id: string; name: string; role: string }[]>()
  activityResourceState.value.assigned_personnel.forEach((item) => {
    const key = item.role || ''
    if (!roleQueue.has(key)) roleQueue.set(key, [])
    roleQueue.get(key)!.push(item)
  })
  return (activityResourceState.value.personnel_roles_required || []).map((role, index) => {
    const queue = roleQueue.get(role) || []
    return {
      index,
      role,
      assigned: queue.length > 0 ? queue.shift() : undefined
    }
  })
})
const equipmentSlots = computed(() => {
  const specQueue = new Map<string, { id: string; name: string; specification: string }[]>()
  activityResourceState.value.assigned_equipment.forEach((item) => {
    const key = item.specification || ''
    if (!specQueue.has(key)) specQueue.set(key, [])
    specQueue.get(key)!.push(item)
  })
  return (activityResourceState.value.equipment_types_required || []).map((specification, index) => {
    const queue = specQueue.get(specification) || []
    return {
      index,
      specification,
      assigned: queue.length > 0 ? queue.shift() : undefined
    }
  })
})

// 定义流程域下拉选项
const domainOptions = [
  { label: '生产 (production)', value: 'production' },
  { label: '质检 (quality)', value: 'quality' },
  { label: '仓储 (warehouse)', value: 'warehouse' },
  { label: '运输 (transport)', value: 'transport' },
  { label: '销售 (sales)', value: 'sales' }
];

// 定义/引入黄金映射字典
const processMap: Record<string, string> = {
  'P001': '主生产线', 'P002': '副生产线',
  'T001': '冷链运输', 'T002': '常温运输',
  'S001': '线上销售', 'S002': '线下销售',
  'Q001': '常规质检', 'Q002': '专项质检',
  'W001': '主仓库', 'W002': '分仓库'
};

// 将字典转换为 el-select 需要的数组格式
const processOptions = Object.entries(processMap).map(([value, label]) => ({
  value,
  label: `${value} - ${label}`
}));

const prefixToDomainMap: Record<string, string> = {
  'P': 'production',
  'T': 'transport',
  'S': 'sales',
  'Q': 'quality',
  'W': 'warehouse'
};

const handleProcessIdChange = (newProcessId: string) => {
  if (!newProcessId) return;
  const prefix = newProcessId.charAt(0).toUpperCase();
  if (prefixToDomainMap[prefix]) {
    // 自动将隐藏的 domain 字段设置为对应的值，以便提交给后端
    editForm.value.domain = prefixToDomainMap[prefix];
  }
  editForm.value.predecessor_ids = []
  void loadAllActivitiesForPredecessor()
};

const predecessorOptions = computed(() => {
  const selfId = activityId.value
  return allActivities.value.filter((item) => item.id && item.id !== selfId)
})

const loadAllActivitiesForPredecessor = async () => {
  try {
    const domains = ['production', 'transport', 'sales', 'quality', 'warehouse']
    const result = await Promise.all(domains.map((domain) => getActivities({ domain })))
    const merged = result.flat().map((item) => {
      if ((item as any)._id && !item.id) item.id = (item as any)._id
      return item
    })
    const dedupMap = new Map<string, Activity>()
    merged.forEach((item) => {
      if (item.id) dedupMap.set(item.id, item)
    })
    allActivities.value = Array.from(dedupMap.values())
  } catch {
    allActivities.value = []
  }
}

const activityId = computed(() => localActivity.value.id || '')
const collapseName = computed(() => localActivity.value.id || localActivity.value.name || '')
const totalSopDuration = computed(() => {
  if (!localActivity.value.sop_steps || localActivity.value.sop_steps.length === 0) return 0
  return localActivity.value.sop_steps.reduce((sum, step) => sum + (step.duration || 0), 0)
})
const workingHoursText = computed(() => {
  const windows = localActivity.value.working_hours || []
  if (windows.length === 0) return '未配置'
  return windows.map(w => `${w.start_time}-${w.end_time}`).join(' / ')
})

const shortageRisks = computed(() => activityRisks.value.filter((r) => {
  if (!(r.includes('缺') || r.includes('不足'))) return false
  const equipmentShortageMatch = r.match(/缺\s*(\d+)\s*台\s*(.+)/)
  if (!equipmentShortageMatch) return true
  const spec = (equipmentShortageMatch[2] || '').trim()
  if (!spec) return true
  const requiredCount = (activityResourceState.value.equipment_types_required || []).filter(item => item === spec).length
  const assignedCount = (activityResourceState.value.assigned_equipment || []).filter(item => item.specification === spec).length
  const shouldKeepRisk = assignedCount < requiredCount
  return shouldKeepRisk
}))
const scheduleRisks = computed(() => activityRisks.value.filter(r => r.includes('请假') || r.includes('检修')))

function getShortageRiskIcon(message: string) {
  if (message.includes('名')) return User
  if (message.includes('台')) return Setting
  if (message.includes('原料') || message.includes('库存')) return Box
  return WarningFilled
}

function getScheduleRiskIcon(message: string) {
  if (message.includes('请假')) return Calendar
  if (message.includes('检修')) return Tools
  return Clock
}

function splitRiskSegments(message: string) {
  const regex = /((?:缺|不足)\s*\d+(?:\.\d+)?\s*(?:名|台|天|个|件)?)/g
  const highlightRegex = /(?:缺|不足)\s*\d+(?:\.\d+)?\s*(?:名|台|天|个|件)?/
  const parts = message.split(regex).filter(Boolean)
  return parts.map(text => ({ text, highlight: highlightRegex.test(text) }))
}

function switchToAllocationTab() {
  activeTab.value = 'resources'
}

function goToMaterialPage() {
  router.push('/material')
}

const statusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '待机中',
    in_progress: '进行中'
  }
  return map[status] || status
}

const statusTagType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'info',
    in_progress: 'primary'
  }
  return map[status] || ''
}

const toggleActivityStatus = async () => {
  if (!activityId.value) return
  const newStatus = localActivity.value.status === 'pending' ? 'in_progress' : 'pending'
  try {
    await updateActivity(activityId.value, { status: newStatus })
    ElMessage.success(`活动已${newStatus === 'in_progress' ? '启动' : '停机'}`)
    await refreshActivityAndRisk()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const inferMaterialModelFromRisk = (message: string) => {
  const match = message.match(/原料\[(.*?)\]/)
  return match?.[1] || ''
}

const locateInDependencyView = () => {
  if (!activityId.value) return
  router.push({
    name: 'Dependencies',
    query: {
      highlightDomain: localActivity.value.domain,
      focusActivity: activityId.value
    }
  })
}

const resolvePredecessorIds = async () => {
  const predecessorIdsFromActivity = Array.isArray(localActivity.value.predecessor_ids)
    ? localActivity.value.predecessor_ids.filter((id): id is string => typeof id === 'string' && id.length > 0)
    : (localActivity.value.predecessor_id ? [localActivity.value.predecessor_id] : [])

  if (predecessorIdsFromActivity.length > 0) return predecessorIdsFromActivity
  if (!activityId.value || !localActivity.value.domain) return []

  try {
    const dependencies = await getDependencies({
      domain: localActivity.value.domain,
      process_id: localActivity.value.process_id,
      activity_id: activityId.value
    })
    return dependencies
      .filter((dep) => dep.target_activity_id === activityId.value)
      .map((dep) => dep.source_activity_id)
      .filter((id, index, arr) => typeof id === 'string' && id.length > 0 && arr.indexOf(id) === index)
  } catch {
    return []
  }
}

const openEditDialog = async () => {
  await loadAllActivitiesForPredecessor()
  const predecessorIds = await resolvePredecessorIds()
  editForm.value = {
    name: localActivity.value.name,
    description: localActivity.value.description,
    status: localActivity.value.status,
    domain: localActivity.value.domain,
    process_id: localActivity.value.process_id,
    predecessor_ids: predecessorIds
  }
  editDialogVisible.value = true
}

const openSopEditDialog = () => {
  sopEditForm.value = {
    description: localActivity.value.description || '',
    sop_steps: localActivity.value.sop_steps ? JSON.parse(JSON.stringify(localActivity.value.sop_steps)) : []
  }
  sopDialogVisible.value = true
}

const addSopStep = () => {
  sopEditForm.value.sop_steps.push({ content: '', duration: 0 })
}

const removeSopStep = (index: number) => {
  sopEditForm.value.sop_steps.splice(index, 1)
}

const saveSopEdit = async () => {
  if (!activityId.value) return
  try {
    const payload = {
      description: sopEditForm.value.description,
      sop_steps: sopEditForm.value.sop_steps
    }
    await updateActivity(activityId.value, payload)
    ElMessage.success('SOP 已更新')
    sopDialogVisible.value = false
    await refreshActivityAndRisk()
  } catch (error) {
    ElMessage.error('更新 SOP 失败')
  }
}

const refreshActivityAndRisk = async () => {
  await Promise.all([loadLatestActivity(), loadActivityRisks(), loadResourceData()])
  emit('refreshed')
}

const loadLatestActivity = async () => {
  if (!activityId.value) return
  const latest = await getActivity(activityId.value)
  if ((latest as any)._id && !latest.id) latest.id = (latest as any)._id
  localActivity.value = latest
}

const loadActivityRisks = async () => {
  activityRisks.value = Array.isArray(localActivity.value.risks) ? localActivity.value.risks : []
}

const loadResourceDictionaries = async () => {
  const [personnelList, resourceList] = await Promise.all([
    getPersonnelList(),
    getResources()
  ])
  allPersonnel.value = (personnelList as any[]).map((p) => ({
    ...p,
    id: p._id || p.id || ''
  })) as PersonnelWithId[]
  allResources.value = (resourceList as any[]).map((r) => ({
    ...r,
    id: r._id || r.id || ''
  })) as ResourceWithId[]
}

const loadResourceData = async () => {
  if (!activityId.value) return
  try {
    const [data, occupied] = await Promise.all([
      getActivityResources(activityId.value),
      getOccupiedResources().catch(() => [])
    ])
    activityResourceState.value = {
      personnel_roles_required: data.personnel_roles_required || [],
      equipment_types_required: data.equipment_types_required || [],
      assigned_personnel: data.assigned_personnel || [],
      assigned_equipment: data.assigned_equipment || [],
      consumed_resources: data.consumed_resources || []
    }
    occupiedIds.value = occupied
  } catch {
    activityResourceState.value = {
      personnel_roles_required: [],
      equipment_types_required: [],
      assigned_personnel: [],
      assigned_equipment: [],
      consumed_resources: []
    }
  }
}

const saveResourceState = async (next: ActivityResourcesData) => {
  if (!activityId.value) return
  await updateActivityResources(activityId.value, {
    personnel_roles: next.personnel_roles_required || [],
    equipment_types: next.equipment_types_required || [],
    assigned_personnel_ids: next.assigned_personnel.map(p => p.id),
    assigned_equipment_ids: next.assigned_equipment.map(e => e.id),
    consumed_resources: next.consumed_resources.map(m => ({ resource_id: m.resource_id, rate: m.rate })
    )
  })
  await refreshActivityAndRisk()
}

const getFilteredPersonsByRole = (role: string) => {
  if (!role) return []
  return allPersonnel.value.filter((p) =>
    p.role === role &&
    !['resigned', 'inactive', 'busy', 'in_use'].includes((p.status || '').toLowerCase()) &&
    !occupiedIdSet.value.has(p.id) &&
    !assignedPersonnelIdSet.value.has(p.id)
  )
}

const getFilteredEquipmentBySpec = (specification: string) => {
  if (!specification) return []
  return availableEquipments.value.filter((e) =>
    e.specification === specification &&
    ['available', 'idle', '空闲'].includes((e.status || '').toLowerCase()) &&
    !occupiedIdSet.value.has(e.id) &&
    !assignedEquipmentIdSet.value.has(e.id)
  )
}

const addPersonnelRequirement = async () => {
  if (!selectedPersonnelRole.value) return
  const next: ActivityResourcesData = {
    ...activityResourceState.value,
    personnel_roles_required: [...(activityResourceState.value.personnel_roles_required || []), selectedPersonnelRole.value]
  }
  await saveResourceState(next)
  selectedPersonnelRole.value = ''
  ElMessage.success('岗位名额已增加')
}

const removePersonnelRequirement = async (slotIndex: number) => {
  const slot = personnelSlots.value.find(s => s.index === slotIndex)
  if (!slot) return
  const nextRoles = [...(activityResourceState.value.personnel_roles_required || [])]
  nextRoles.splice(slotIndex, 1)
  const nextAssigned = slot.assigned
    ? activityResourceState.value.assigned_personnel.filter(p => p.id !== slot.assigned!.id)
    : [...activityResourceState.value.assigned_personnel]
  const next: ActivityResourcesData = {
    ...activityResourceState.value,
    personnel_roles_required: nextRoles,
    assigned_personnel: nextAssigned
  }
  await saveResourceState(next)
  ElMessage.success('岗位名额已删除')
}

const startPersonnelAssign = (slotIndex: number) => {
  activePersonnelAssignIndex.value = slotIndex
}

const cancelPersonnelAssign = () => {
  activePersonnelAssignIndex.value = null
}

const confirmPersonnelAssign = async (slotIndex: number) => {
  const personId = personnelSlotSelection.value[slotIndex]
  if (!personId) return
  const person = allPersonnel.value.find((p) => p.id === personId)
  const slot = personnelSlots.value.find(s => s.index === slotIndex)
  if (!person || !slot) return
  const nextAssigned = [...activityResourceState.value.assigned_personnel]
  if (slot.assigned) {
    const oldIndex = nextAssigned.findIndex(item => item.id === slot.assigned!.id)
    if (oldIndex >= 0) nextAssigned.splice(oldIndex, 1)
  }
  nextAssigned.push({ id: person.id, name: person.name, role: slot.role })
  const next: ActivityResourcesData = {
    ...activityResourceState.value,
    assigned_personnel: nextAssigned
  }
  await saveResourceState(next)
  delete personnelSlotSelection.value[slotIndex]
  activePersonnelAssignIndex.value = null
  ElMessage.success('人员已分配')
}

const removePersonnel = async (id: string) => {
  const next: ActivityResourcesData = {
    ...activityResourceState.value,
    assigned_personnel: activityResourceState.value.assigned_personnel.filter(p => p.id !== id)
  }
  await saveResourceState(next)
  ElMessage.success('人员已移除')
}

const addEquipmentRequirement = async () => {
  if (!selectedEquipmentSpec.value) return
  const next: ActivityResourcesData = {
    ...activityResourceState.value,
    equipment_types_required: [...(activityResourceState.value.equipment_types_required || []), selectedEquipmentSpec.value]
  }
  await saveResourceState(next)
  selectedEquipmentSpec.value = ''
  ElMessage.success('设备名额已增加')
}

const removeEquipmentRequirement = async (slotIndex: number) => {
  const slot = equipmentSlots.value.find(s => s.index === slotIndex)
  if (!slot) return
  const nextTypes = [...(activityResourceState.value.equipment_types_required || [])]
  nextTypes.splice(slotIndex, 1)
  const nextAssigned = slot.assigned
    ? activityResourceState.value.assigned_equipment.filter(e => e.id !== slot.assigned!.id)
    : [...activityResourceState.value.assigned_equipment]
  const next: ActivityResourcesData = {
    ...activityResourceState.value,
    equipment_types_required: nextTypes,
    assigned_equipment: nextAssigned
  }
  await saveResourceState(next)
  ElMessage.success('设备名额已删除')
}

const startEquipmentAssign = (slotIndex: number) => {
  activeEquipmentAssignIndex.value = slotIndex
}

const cancelEquipmentAssign = () => {
  activeEquipmentAssignIndex.value = null
}

const confirmEquipmentAssign = async (slotIndex: number) => {
  const equipmentId = equipmentSlotSelection.value[slotIndex]
  if (!equipmentId) return
  const equipment = allResources.value.find((r) => r.id === equipmentId)
  const slot = equipmentSlots.value.find(s => s.index === slotIndex)
  if (!equipment || !slot) return
  const nextAssigned = [...activityResourceState.value.assigned_equipment]
  if (slot.assigned) {
    const oldIndex = nextAssigned.findIndex(item => item.id === slot.assigned!.id)
    if (oldIndex >= 0) nextAssigned.splice(oldIndex, 1)
  }
  nextAssigned.push({ id: equipment.id, name: equipment.name, specification: slot.specification })
  const next: ActivityResourcesData = {
    ...activityResourceState.value,
    assigned_equipment: nextAssigned
  }
  await saveResourceState(next)
  delete equipmentSlotSelection.value[slotIndex]
  activeEquipmentAssignIndex.value = null
  ElMessage.success('设备已分配')
}

const removeEquipment = async (id: string) => {
  const next: ActivityResourcesData = {
    ...activityResourceState.value,
    assigned_equipment: activityResourceState.value.assigned_equipment.filter(e => e.id !== id)
  }
  await saveResourceState(next)
  ElMessage.success('设备已移除')
}

const Package = Box
const Check = CheckIcon
const X = Close
const Edit2 = Edit
const Trash2 = Delete

const openMaterialAssignForm = () => {
  isMaterialAssigning.value = true
}

const cancelMaterialAssign = () => {
  isMaterialAssigning.value = false
  selectedMaterialId.value = ''
  selectedMaterialRate.value = 1
}

const getMaterialUnit = (resourceId: string) => materialUnitMap.value[resourceId] || ''

const assignMaterial = async () => {
  if (!selectedMaterialId.value) return
  const material = allResources.value.find((r) => r.id === selectedMaterialId.value)
  if (!material) return
  const existsIndex = activityResourceState.value.consumed_resources.findIndex(
    item => item.resource_id === selectedMaterialId.value
  )
  const nextConsumed = [...activityResourceState.value.consumed_resources]
  if (existsIndex >= 0) {
    nextConsumed[existsIndex] = {
      ...nextConsumed[existsIndex],
      rate: selectedMaterialRate.value,
      name: material.name
    }
  } else {
    nextConsumed.push({
      resource_id: material.id,
      name: material.name,
      rate: selectedMaterialRate.value
    })
  }
  const next: ActivityResourcesData = {
    ...activityResourceState.value,
    consumed_resources: nextConsumed
  }
  await saveResourceState(next)
  cancelMaterialAssign()
  ElMessage.success('原料分配成功')
}

const startEdit = (material: { resource_id: string; rate: number }) => {
  editingMaterialId.value = material.resource_id
  editQuantityValue.value = material.rate
}

const cancelEdit = () => {
  editingMaterialId.value = null
  editQuantityValue.value = ''
}

const saveEdit = async (materialId: string) => {
  const parsedRate = Number(editQuantityValue.value)
  if (!Number.isFinite(parsedRate) || parsedRate < 0) {
    ElMessage.warning('请输入有效的消耗数量')
    return
  }
  const nextConsumed = activityResourceState.value.consumed_resources.map((item) => {
    if (item.resource_id !== materialId) return item
    return { ...item, rate: parsedRate }
  })
  const next: ActivityResourcesData = {
    ...activityResourceState.value,
    consumed_resources: nextConsumed
  }
  await saveResourceState(next)
  cancelEdit()
  ElMessage.success('原料消耗量已更新')
}

const removeMaterial = async (resourceId: string) => {
  const next: ActivityResourcesData = {
    ...activityResourceState.value,
    consumed_resources: activityResourceState.value.consumed_resources.filter(m => m.resource_id !== resourceId)
  }
  await saveResourceState(next)
  ElMessage.success('原料已移除')
}

watch(
  () => props.activity,
  (next) => {
    localActivity.value = { ...next }
    if (props.forceExpand && collapseName.value) {
      expandedPanels.value = [collapseName.value]
    }
    void loadActivityRisks()
  },
  { deep: true, immediate: true }
)

watch(
  () => props.forceExpand,
  (shouldExpand) => {
    if (!collapseName.value) return
    expandedPanels.value = shouldExpand ? [collapseName.value] : []
  },
  { immediate: true }
)

watch(activeTab, async (tab) => {
  if (tab === 'risks') await loadActivityRisks()
  if (tab === 'resources') {
    await Promise.all([loadResourceDictionaries(), loadResourceData()])
  }
})

const saveActivityEdit = async () => {
  if (!activityId.value) return
  try {
    await updateActivity(activityId.value, editForm.value)
    ElMessage.success('活动已更新')
    editDialogVisible.value = false
    await refreshActivityAndRisk()
  } catch (error) {
    ElMessage.error('更新活动失败')
  }
}

const handleDeleteActivity = async () => {
  if (!activityId.value) return
  try {
    await ElMessageBox.confirm(
      '此操作将从数据库和图谱中永久删除该活动及其所有关联数据，是否继续？',
      '警告',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteActivity(activityId.value)
    ElMessage.success('活动已删除')
    editDialogVisible.value = false
    emit('refreshed')
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}
</script>

<style scoped>

.workflow-icon {
  color: #94a3b8;
}

.activity-highlight-flash {
  animation: activity-highlight-flash 1.8s ease;
}

@keyframes activity-highlight-flash {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0);
  }
  20%,
  60% {
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.35);
  }
}

:deep(.el-collapse-item.is-active .workflow-icon) {
  color: #2563eb;
}

:deep(.el-collapse-item__header) {
  border-bottom: none;
  height: auto;
  line-height: normal;
  padding: 16px 24px;
}

:deep(.el-collapse-item__wrap) {
  border-bottom: none;
  background-color: #f8fafc;
}

:deep(.el-collapse-item__content) {
  padding-bottom: 0;
}

:deep(.custom-tabs .el-tabs__nav-wrap::after) {
  height: 1px;
  background-color: #e2e8f0;
}

:deep(.custom-tabs .el-tabs__item) {
  font-weight: 500;
  color: #64748b;
}

:deep(.custom-tabs .el-tabs__item.is-active) {
  color: #2563eb;
}

:deep(.custom-tabs .el-tabs__active-bar) {
  background-color: #2563eb;
  height: 3px;
  border-radius: 3px 3px 0 0;
}

:deep(.sop-table th.el-table__cell) {
  background-color: #f8fafc;
  color: #475569;
  font-weight: 600;
}

/* 风险面板样式保持不变 */
.risk-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.risk-empty-state {
  border: 1px solid #dcfce7;
  background: #f0fdf4;
  border-radius: 10px;
}

.risk-empty-title {
  font-size: 14px;
  font-weight: 600;
  color: #166534;
}

.risk-empty-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #15803d;
}

.risk-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.risk-section-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.risk-header-icon.danger {
  color: #dc2626;
}

.risk-header-icon.warning {
  color: #d97706;
}

.risk-section-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.risk-card {
  border-radius: 8px;
}

.risk-card-shortage {
  border: 1px solid #fecaca;
  background: #fef2f2;
}

.risk-card-schedule {
  border: 1px solid #fed7aa;
  background: #fff7ed;
}

.risk-card-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.risk-main-line {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  flex: 1;
}

.risk-item-icon {
  margin-top: 2px;
  color: #606266;
}

.risk-item-text {
  color: #303133;
  line-height: 1.55;
  font-size: 13px;
  flex: 1;
}

.risk-segment-highlight {
  font-weight: 700;
  color: #dc2626;
}

.risk-action-btn {
  border: none;
  outline: none;
  white-space: nowrap;
  cursor: pointer;
  border-radius: 6px;
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.08);
}

.risk-action-alloc {
  color: #2563eb;
  border: 1px solid #bfdbfe;
}

.risk-action-alloc:hover {
  background: #eff6ff;
}

.risk-action-replenish {
  color: #dc2626;
  border: 1px solid #fecaca;
}

.risk-action-replenish:hover {
  background: #fef2f2;
}

:deep(.capsule-tabs.el-tabs--card > .el-tabs__header) {
  border-bottom: none;
  margin-bottom: 24px;
}

:deep(.capsule-tabs.el-tabs--card > .el-tabs__header .el-tabs__nav) {
  border: none;
  background: #f1f5f9;
  border-radius: 8px;
  padding: 4px;
}

:deep(.capsule-tabs.el-tabs--card > .el-tabs__header .el-tabs__item) {
  border: none;
  border-radius: 6px;
  height: 32px;
  line-height: 32px;
  color: #64748b;
  font-weight: 500;
  transition: all 0.2s;
}

:deep(.capsule-tabs.el-tabs--card > .el-tabs__header .el-tabs__item.is-active) {
  background: #ffffff;
  color: #1e293b;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.resource-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.resource-avatar {
  width: 40px;
  height: 40px;
  background: #e0e7ff;
  color: #4f46e5;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 16px;
}

.resource-icon-wrap {
  width: 40px;
  height: 40px;
  background: #f1f5f9;
  color: #64748b;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.resource-info {
  flex: 1;
}

.resource-name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 4px;
}

.resource-meta {
  font-size: 12px;
  color: #64748b;
}

.material-table {
  border-radius: 8px;
  border: 1px solid #f1f5f9;
}

.consume-amount {
  font-weight: 700;
  color: #2563eb;
}

.form-row {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  align-items: center;
}

.replenish-tip {
  margin-bottom: 12px;
}

:deep(.edit-activity-dialog.el-dialog) {
  border-radius: 16px;
  padding: 0;
  overflow: hidden;
}

:deep(.edit-activity-dialog .el-dialog__header) {
  padding: 0;
  margin: 0;
}

:deep(.custom-input-indigo .el-input__wrapper),
:deep(.custom-input-indigo .el-textarea__inner) {
  background-color: #f8fafc !important;
  border-radius: 0.75rem !important;
  box-shadow: 0 0 0 1px #e2e8f0 inset !important;
  padding-top: 0.25rem;
  padding-bottom: 0.25rem;
  transition: all 0.2s;
}

:deep(.custom-input-indigo .el-input__wrapper.is-focus),
:deep(.custom-input-indigo .el-textarea__inner:focus) {
  background-color: #ffffff !important;
  box-shadow: 0 0 0 1px #6366f1 inset, 0 0 0 4px #e0e7ff !important;
}

:deep(.custom-input-indigo .el-select .el-input__wrapper.is-focus) {
  background-color: #ffffff !important;
  box-shadow: 0 0 0 1px #6366f1 inset, 0 0 0 4px #e0e7ff !important;
}
</style>
