<template>
  <div class="flex flex-col h-screen bg-slate-50 overflow-hidden p-4 gap-4 max-w-[1800px] mx-auto">
      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 flex justify-between items-center shrink-0">
        <div class="flex items-center space-x-3">
          <el-select
            v-model="currentProcessId"
            placeholder="选择流程ID"
            class="!w-48 shrink-0"
            clearable
          >
            <el-option
              v-for="process in processOptions"
              :key="process.id"
              :label="formatProcessLabel(process.id, process.name)"
              :value="process.id"
            />
          </el-select>
          <el-button
            type="primary"
            class="!bg-blue-600 !border-blue-600 !text-white hover:!bg-blue-700 hover:!border-blue-700"
            @click="applySelectedProcessHighlight"
          >
            定位并高亮
          </el-button>
          <el-button class="!bg-white !text-slate-600 !border-slate-300 hover:!text-slate-800 hover:!border-slate-400" @click="clearFlowHighlight">
            清除高亮
          </el-button>
          <!-- 路径分析按钮 (带状态切换) -->
          <button
            type="button"
            @click="togglePathSelectionMode"
            :class="[
              'ml-3 flex items-center px-4 py-2 font-bold border rounded-lg transition-all shadow-sm',
              isPathSelecting
                ? 'bg-indigo-600 text-white border-indigo-700 animate-pulse'
                : 'bg-indigo-50 text-indigo-600 border-indigo-200 hover:bg-indigo-100'
            ]"
            :title="isPathSelecting ? '右键点击图谱可退出选择' : '点击后，在图中依次左键选择起点和终点'"
          >
            <el-icon class="mr-1.5"><Guide /></el-icon>
            {{ isPathSelecting ? (pathStartNode ? '请点击终点...' : '请点击起点...') : '路径分析' }}
          </button>
        </div>

        <div class="flex items-center space-x-3">
          <div class="flex items-center bg-slate-100 rounded-lg p-1 border border-slate-200">
            <div class="flex items-center px-3 py-1 bg-white rounded shadow-sm text-indigo-700 cursor-pointer" @click="handleKpiClick('internalDependencies')">
              <span class="text-xs font-bold mr-1.5">内依赖</span><span class="text-sm font-black">{{ metrics.internalDependencyCount }}</span>
            </div>
            <div class="flex items-center px-3 py-1 text-indigo-700 hover:bg-white hover:shadow-sm rounded transition-all cursor-pointer" @click="handleKpiClick('externalDependencies')">
              <span class="text-xs font-bold mr-1.5">外依赖</span><span class="text-sm font-black">{{ metrics.externalDependencyCount }}</span>
            </div>
          </div>

          <div class="flex items-center px-3 py-1.5 rounded-lg border bg-blue-50 text-blue-700 border-blue-100 hover:bg-blue-100 cursor-pointer transition-colors" @click="handleKpiClick('activities')">
            <el-icon class="mr-2 opacity-80"><DataLine /></el-icon>
            <span class="text-xs font-bold mr-2 opacity-80">活动数</span>
            <span class="text-sm font-black">{{ metrics.activityCount }}</span>
          </div>
          <div class="flex items-center px-3 py-1.5 rounded-lg border bg-emerald-50 text-emerald-700 border-emerald-100 hover:bg-emerald-100 cursor-pointer transition-colors" @click="handleKpiClick('health')">
            <el-icon class="mr-2 opacity-80"><Odometer /></el-icon>
            <span class="text-xs font-bold mr-2 opacity-80">健康评分</span>
            <span class="text-sm font-black">{{ metrics.healthScore }}</span>
          </div>
          <div class="flex items-center px-3 py-1.5 rounded-lg border bg-amber-50 text-amber-700 border-amber-100 hover:bg-amber-100 cursor-pointer transition-colors" @click="handleKpiClick('resource')">
            <el-icon class="mr-2 opacity-80"><Clock /></el-icon>
            <span class="text-xs font-bold mr-2 opacity-80">可运行时间</span>
            <span class="text-sm font-black">{{ miniRunnableTimeText }}</span>
          </div>
          <div class="flex items-center px-3 py-1.5 rounded-lg border bg-red-50 text-red-700 border-red-100 hover:bg-red-100 cursor-pointer transition-colors" @click="handleKpiClick('dynamic')">
            <el-icon class="mr-2 opacity-80"><Warning /></el-icon>
            <span class="text-xs font-bold mr-2 opacity-80">异常风险</span>
            <span class="text-sm font-black">{{ riskList.length }}</span>
          </div>
        </div>
      </div>

      <div class="flex flex-1 gap-4 overflow-hidden">
        <div class="flex-1 bg-white rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden flex flex-col">
          <div class="flex-1 overflow-hidden">
            <DependencyGraph
              :data="graphData"
              :highlight-active="highlightActive"
              :highlight-set="highlightSet"
              :path-selection-mode="isPathSelecting"
              :path-start-activity-id="pathStartNode?.id ?? null"
              @node-click="handleNodeClick"
              @path-node-pick="handlePathNodePick"
              @path-selection-cancel="handlePathSelectionCancel"
              @edit-activity="handleEditActivityFromGraph"
              @edit-personnel="handleEditPersonnelFromGraph"
              @edit-resource="handleEditResourceFromGraph"
            />
          </div>
        </div>

        <aside class="w-[420px] bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col overflow-hidden shrink-0">
          <DashboardPanel
            mode="sidebar"
            :graph-data="graphData"
            :current-process-id="currentProcessId"
            :current-domain="currentDomain"
            :min-runnable-days="minRunnableDays"
            :risk-count="riskList.length"
            :risk-list="riskList"
            :path-analysis="currentCriticalPath"
            @highlight-request="handleDashboardHighlight"
            @process-select="handleProcessSelect"
          />
        </aside>
      </div>

    <!-- 依赖关系对话框 -->
    <el-dialog 
      v-model="dependencyDialogVisible" 
      :title="isEditDependency ? '编辑依赖关系' : '添加依赖关系'"
      width="600px"
    >
      <el-form :model="dependencyForm" label-width="120px">
        <el-form-item label="源活动">
          <el-select v-model="dependencyForm.source_activity_id" placeholder="选择源活动" filterable>
            <el-option 
              v-for="activity in activities" 
              :key="activity.id" 
              :label="activity.name" 
              :value="activity.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="目标活动">
          <el-select v-model="dependencyForm.target_activity_id" placeholder="选择目标活动" filterable>
            <el-option 
              v-for="activity in activities" 
              :key="activity.id" 
              :label="activity.name" 
              :value="activity.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="依赖类型">
          <el-select v-model="dependencyForm.dependency_type">
            <el-option label="顺序" value="sequential" />
            <el-option label="并行" value="parallel" />
            <el-option label="条件" value="conditional" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间约束">
          <el-input-number v-model="dependencyForm.time_constraint" :min="0" placeholder="分钟" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="dependencyForm.status">
            <el-option label="生效中" value="active" />
            <el-option label="未生效" value="inactive" />
            <el-option label="待确认" value="pending" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="dependencyForm.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dependencyDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleDependencySubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 活动详情对话框 -->
    <el-dialog 
      v-model="activityDialogVisible" 
      :title="isEditActivity ? '编辑活动' : (currentActivity?.id ? '活动详情' : '添加活动')"
      width="800px"
    >
      <!-- 详情展示模式 -->
      <div v-if="currentActivity?.id && !isEditActivity" class="flex flex-col gap-5 animate-in slide-in-from-right-4 duration-300">
        <div class="bg-slate-50 rounded-xl p-4 border border-slate-200 flex justify-between items-center shadow-sm">
          <div>
            <div class="text-[10px] font-bold text-slate-400 uppercase mb-1 tracking-wider">所属流程</div>
            <div class="text-sm font-black text-slate-800">{{ getProcessLabel(activityForm.process_id) }}</div>
          </div>
          <div class="h-8 w-px bg-slate-200"></div>
          <div>
            <div class="text-[10px] font-bold text-slate-400 uppercase mb-1 tracking-wider">SOP 合计</div>
            <div class="text-sm font-black text-blue-600">{{ sopTotalMinutesDetail }} <span class="text-[10px] font-bold text-slate-500">分钟</span></div>
          </div>
          <div class="h-8 w-px bg-slate-200"></div>
          <div class="text-right">
            <div class="text-[10px] font-bold text-slate-400 uppercase mb-1 tracking-wider">当前状态</div>
            <span v-if="activityForm.status === 'in_progress'" class="px-2 py-1 bg-blue-500 text-white rounded text-[10px] font-bold shadow-sm">进行中</span>
            <span v-else-if="activityForm.status === 'completed'" class="px-2 py-1 bg-emerald-500 text-white rounded text-[10px] font-bold shadow-sm">已完成</span>
            <span v-else class="px-2 py-1 bg-slate-400 text-white rounded text-[10px] font-bold shadow-sm">{{ activityForm.status }}</span>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="border border-slate-200 bg-white p-3.5 rounded-xl shadow-sm">
            <div class="text-[11px] font-bold text-slate-400 mb-1">活动名称</div>
            <div class="text-sm font-bold text-slate-700">{{ activityForm.name }}</div>
          </div>
          <div class="border border-slate-200 bg-white p-3.5 rounded-xl shadow-sm">
            <div class="text-[11px] font-bold text-slate-400 mb-1">运行时间段</div>
            <div class="text-xs font-bold text-slate-700 mt-1">
              <template v-if="Array.isArray(activityForm.working_hours)">
                {{ activityForm.working_hours.map(h => (h.start_time && h.end_time) ? `${h.start_time}-${h.end_time}` : '').filter(Boolean).join(', ') }}
              </template>
              <template v-else>
                {{ activityForm.working_hours || '未设置' }}
              </template>
            </div>
          </div>
          <div class="col-span-2 border border-slate-200 bg-white p-3.5 rounded-xl shadow-sm">
            <div class="text-[11px] font-bold text-slate-400 mb-1">活动描述</div>
            <div class="text-xs font-medium text-slate-600 leading-relaxed mt-1">{{ activityForm.description || '暂无描述' }}</div>
          </div>
        </div>

        <div class="mt-2">
          <div class="text-xs font-bold text-slate-800 mb-3 flex items-center">
            <div class="w-1.5 h-3 bg-blue-500 rounded-full mr-2"></div>SOP 执行步骤
          </div>
          <div v-if="activityForm.sop_steps?.length > 0" class="space-y-2.5 relative">
            <div class="absolute left-4 top-4 bottom-4 w-px bg-blue-100 z-0"></div>
            <div v-for="(step, index) in activityForm.sop_steps" :key="index" class="relative z-10 flex items-center p-3 bg-white border border-slate-200 rounded-xl shadow-sm hover:border-blue-300 hover:shadow-md transition-all">
              <div class="flex-shrink-0">
                <span class="inline-flex items-center justify-center bg-blue-50 text-blue-600 text-[11px] font-black px-2.5 py-1 rounded-md border border-blue-100 shadow-sm">
                  步骤 {{ (step as any).step_number || index + 1 }}
                </span>
              </div>
              <div class="ml-3 flex-1 text-sm font-bold text-slate-700 truncate">{{ (step as any).description || (step as any).name || step.content }}</div>
              <div class="ml-3 flex-shrink-0 flex items-center">
                <span class="text-[11px] font-black text-slate-600 bg-slate-50 px-2 py-1 rounded-md border border-slate-100">
                  {{ step.duration }} <span class="font-bold text-slate-400">分</span>
                </span>
              </div>
            </div>
          </div>
          <div v-else class="text-xs text-center py-4 text-slate-400 border-2 border-dashed border-slate-200 rounded-xl">无SOP配置</div>
        </div>
        <!-- 底部跳转按钮 -->
        <div class="mt-6">
          <button type="button" @click="goToActivityManagementFromDialog" class="w-full flex items-center justify-center py-3 bg-indigo-50 text-indigo-600 rounded-xl font-bold text-sm hover:bg-indigo-100 hover:shadow-sm transition-all border border-indigo-100">
            前往【生产活动管理】面板查看完整档案 <el-icon class="ml-2"><TopRight /></el-icon>
          </button>
        </div>
      </div>

      <!-- 编辑/添加模式 -->
      <el-form v-else :model="activityForm" label-width="120px">
        <el-form-item label="活动名称">
          <el-input v-model="activityForm.name" />
        </el-form-item>
        <el-form-item label="活动类型">
          <el-input v-model="activityForm.activity_type" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="activityForm.description" type="textarea" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="activityForm.status">
            <el-option label="待开始" value="pending" />
            <el-option label="进行中" value="in_progress" />
            <el-option label="已完成" value="completed" />
            <el-option label="已暂停" value="paused" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
      </el-form>

      <template v-if="!currentActivity?.id || isEditActivity" #footer>
        <div style="display: flex; justify-content: space-between;">
          <div>
            <el-button v-if="currentActivity?.id && isEditActivity" type="danger" @click="handleDeleteActivity">删除</el-button>
          </div>
          <div>
            <el-button @click="closeActivityDialog">取消</el-button>
            <el-button type="primary" @click="handleActivitySubmit">确定</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 资源详情对话框 -->
    <el-dialog 
      v-model="resourceDialogVisible" 
      :title="isEditResource ? '编辑资源' : (currentResource?.id ? '资源详情' : '添加资源')"
      width="600px"
    >
      <!-- 详情展示模式（设备 / 原料）；与下方编辑表单互斥，避免出现双轨 UI -->
      <template v-if="currentResource?.id && !isEditResource">
      <div v-if="currentResource?.type === '设备'" class="flex flex-col gap-4 animate-in slide-in-from-right-4 duration-300">
        <div class="bg-gradient-to-br from-slate-800 to-slate-900 p-5 rounded-2xl shadow-lg flex items-center mb-2">
          <div class="w-12 h-12 bg-white/10 rounded-xl flex items-center justify-center mr-4 border border-white/20">
            <el-icon :size="24" class="text-amber-400"><Monitor /></el-icon>
          </div>
          <div>
            <div class="text-lg font-black text-white">{{ resourceForm.name }}</div>
            <div class="text-xs font-bold text-amber-400 mt-1 uppercase tracking-widest">工业设备资产</div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="border border-slate-200 bg-white p-3.5 rounded-xl shadow-sm">
            <div class="text-[11px] font-bold text-slate-400 mb-1">设备类型</div><div class="text-sm font-bold text-slate-700">{{ resourceForm.specification || '未知' }}</div>
          </div>
          <div class="border border-slate-200 bg-white p-3.5 rounded-xl shadow-sm">
            <div class="text-[11px] font-bold text-slate-400 mb-1">生产时间</div><div class="text-sm font-bold text-slate-700">{{ (resourceForm as any).production_time || (resourceForm as any).manufacture_date || '未知' }}</div>
          </div>
          <div class="col-span-2 border border-slate-200 bg-white p-3.5 rounded-xl shadow-sm">
            <div class="text-[11px] font-bold text-slate-400 mb-1">供应商</div><div class="text-sm font-bold text-slate-700">{{ resourceForm.supplier || '未知' }}</div>
          </div>
        </div>
        <!-- 底部跳转按钮 -->
        <div class="mt-6">
          <button type="button" @click="goToEquipmentManagementFromDialog" class="w-full flex items-center justify-center py-3 bg-amber-50 text-amber-600 rounded-xl font-bold text-sm hover:bg-amber-100 hover:shadow-sm transition-all border border-amber-100">
            前往【生产设备资产】面板查看完整档案 <el-icon class="ml-2"><TopRight /></el-icon>
          </button>
        </div>
      </div>

      <div v-else-if="currentResource?.type === '原料'" class="flex flex-col gap-4 animate-in slide-in-from-right-4 duration-300">
        <div class="bg-white p-5 rounded-2xl border border-emerald-200 shadow-sm flex items-center justify-between">
          <div class="flex items-center">
            <div class="w-12 h-12 bg-emerald-50 rounded-xl flex items-center justify-center mr-4 border border-emerald-100">
              <el-icon :size="24" class="text-emerald-500"><Box /></el-icon>
            </div>
            <div>
              <div class="text-lg font-black text-slate-800">{{ resourceForm.name }}</div>
              <div class="text-xs font-bold text-emerald-600 mt-1 uppercase tracking-widest">生产流转原料</div>
            </div>
          </div>
          <div class="text-right">
            <div class="text-[10px] font-bold text-slate-400 uppercase mb-0.5">库存总量</div>
            <div class="text-xl font-black text-slate-700">{{ resourceForm.quantity }} <span class="text-[10px] font-bold text-slate-400">{{ resourceForm.unit }}</span></div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="border border-slate-200 bg-white p-4 rounded-xl shadow-sm flex flex-col justify-center">
            <div class="text-[11px] font-bold text-slate-400 mb-2">预估可用时长</div>
            <div>
              <span v-if="(resourceForm as any).remaining_days === -1 || (resourceForm as any).remaining_days > 999" class="inline-flex items-center text-sm font-black text-emerald-500">
                <el-icon class="mr-1"><Select /></el-icon> 充足
              </span>
              <span v-else class="inline-flex items-center px-2.5 py-1 bg-red-50 text-red-600 border border-red-200 rounded-lg text-xs font-bold shadow-sm">
                <div class="w-1.5 h-1.5 rounded-full bg-red-500 mr-1.5 animate-pulse"></div>
                仅剩 {{ Number((resourceForm as any).remaining_days).toFixed(1) }} 天
              </span>
            </div>
          </div>
          
          <div class="border border-blue-100 bg-blue-50/50 p-4 rounded-xl shadow-sm flex flex-col justify-center">
            <div class="text-[11px] font-bold text-slate-500 mb-1">当前活动消耗速率</div>
            <div class="text-lg font-black text-blue-700">
              {{ currentResourceEdgeRate }} <span class="text-[10px] font-bold text-blue-400 uppercase ml-0.5">/ Hour</span>
            </div>
          </div>
        </div>
        <!-- 底部跳转按钮 -->
        <div class="mt-6">
          <button type="button" @click="goToMaterialManagementFromDialog" class="w-full flex items-center justify-center py-3 bg-emerald-50 text-emerald-600 rounded-xl font-bold text-sm hover:bg-emerald-100 hover:shadow-sm transition-all border border-emerald-100">
            前往【原料库存调度】面板查看完整档案 <el-icon class="ml-2"><TopRight /></el-icon>
          </button>
        </div>
      </div>
      </template>

      <!-- 编辑/添加模式 -->
      <el-form v-else :model="resourceForm" label-width="120px">
        <el-form-item label="资源名称">
          <el-input v-model="resourceForm.name" />
        </el-form-item>
        <el-form-item label="资源类型">
          <el-input v-model="resourceForm.type" />
        </el-form-item>
        <el-form-item label="规格">
          <el-input v-model="resourceForm.specification" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="resourceForm.supplier" />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="resourceForm.quantity" :min="0" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="resourceForm.unit" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="resourceForm.status">
            <el-option label="可用" value="available" />
            <el-option label="使用中" value="in_use" />
            <el-option label="维护中" value="maintenance" />
            <el-option label="不可用" value="unavailable" />
          </el-select>
        </el-form-item>
      </el-form>

      <template v-if="!currentResource?.id || isEditResource" #footer>
        <div style="display: flex; justify-content: space-between;">
          <div>
            <el-button v-if="currentResource?.id && isEditResource" type="danger" @click="handleDeleteResource">删除</el-button>
          </div>
          <div>
            <el-button @click="closeResourceDialog">取消</el-button>
            <el-button type="primary" @click="handleResourceSubmit">确定</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 人员详情对话框 -->
    <el-dialog 
      v-model="personnelDialogVisible" 
      :title="isEditPersonnel ? '编辑人员' : (currentPersonnel?.id ? '人员详情' : '添加人员')"
      width="600px"
    >
      <!-- 详情展示模式 -->
      <div v-if="currentPersonnel?.id && !isEditPersonnel" class="flex flex-col gap-4 animate-in slide-in-from-right-4 duration-300">
        <div class="flex items-center p-5 bg-white rounded-2xl border border-slate-200 shadow-sm">
          <div class="w-14 h-14 bg-gradient-to-br from-blue-400 to-blue-600 text-white rounded-full flex items-center justify-center text-xl font-black shadow-md mr-4 ring-4 ring-blue-50">
            {{ personnelForm.name?.charAt(0) || 'P' }}
          </div>
          <div class="flex-1">
            <div class="text-xl font-black text-slate-800 flex items-center">
              {{ personnelForm.name }}
              <span class="ml-3 px-2.5 py-0.5 bg-slate-100 border border-slate-200 text-slate-600 text-[10px] font-bold rounded-md uppercase tracking-wider">{{ personnelForm.role }}</span>
            </div>
            <div class="text-xs font-bold text-slate-400 mt-1 flex items-center">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5"></span> 状态: {{ personnelForm.status === 'available' ? '活跃' : personnelForm.status }}
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="border border-slate-200 bg-white p-3.5 rounded-xl shadow-sm">
            <div class="text-[11px] font-bold text-slate-400 mb-1">性别</div><div class="text-sm font-bold text-slate-700">{{ personnelForm.gender || '未知' }}</div>
          </div>
          <div class="border border-slate-200 bg-white p-3.5 rounded-xl shadow-sm">
            <div class="text-[11px] font-bold text-slate-400 mb-1">年龄</div><div class="text-sm font-bold text-slate-700">{{ personnelForm.age ? personnelForm.age + ' 岁' : '未知' }}</div>
          </div>
          <div class="border border-slate-200 bg-white p-3.5 rounded-xl shadow-sm">
            <div class="text-[11px] font-bold text-slate-400 mb-1">学历</div><div class="text-sm font-bold text-slate-700">{{ personnelForm.education || '未知' }}</div>
          </div>
          <div class="border border-blue-100 bg-blue-50/50 p-3.5 rounded-xl shadow-sm">
            <div class="text-[11px] font-bold text-blue-500 mb-1">所属部门</div><div class="text-sm font-black text-blue-700">{{ personnelForm.department || '暂无部门' }}</div>
          </div>
          <div class="border border-slate-200 bg-white p-3.5 rounded-xl shadow-sm">
            <div class="text-[11px] font-bold text-slate-400 mb-1">薪资</div><div class="text-sm font-black text-emerald-600">{{ personnelForm.salary ? '¥ ' + personnelForm.salary + ' /月' : '保密' }}</div>
          </div>
          <div class="border border-slate-200 bg-white p-3.5 rounded-xl shadow-sm">
            <div class="text-[11px] font-bold text-slate-400 mb-1">入职日期</div><div class="text-sm font-bold text-slate-700">{{ personnelForm.hire_date || '未知' }}</div>
          </div>
          <div class="col-span-2 border border-slate-200 bg-white p-3.5 rounded-xl shadow-sm">
            <div class="text-[11px] font-bold text-slate-400 mb-1">籍贯</div><div class="text-sm font-bold text-slate-700">{{ personnelForm.native_place || '未知' }}</div>
          </div>
        </div>
        <!-- 底部跳转按钮 -->
        <div class="mt-6">
          <button type="button" @click="goToPersonnelManagementFromDialog" class="w-full flex items-center justify-center py-3 bg-blue-50 text-blue-600 rounded-xl font-bold text-sm hover:bg-blue-100 hover:shadow-sm transition-all border border-blue-100">
            前往【员工排班与分配】面板查看完整档案 <el-icon class="ml-2"><TopRight /></el-icon>
          </button>
        </div>
      </div>

      <!-- 编辑/添加模式 -->
      <el-form v-else :model="personnelForm" label-width="120px">
        <el-form-item label="姓名">
          <el-input v-model="personnelForm.name" />
        </el-form-item>
        <el-form-item label="角色">
          <el-input v-model="personnelForm.role" />
        </el-form-item>
        <el-form-item label="职责">
          <el-input v-model="personnelForm.responsibility" type="textarea" />
        </el-form-item>
        <el-form-item label="技能">
          <el-select v-model="personnelForm.skills" multiple filterable allow-create placeholder="输入技能">
            <el-option 
              v-for="skill in personnelForm.skills" 
              :key="skill" 
              :label="skill" 
              :value="skill" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="工作时间">
          <el-input v-model="personnelForm.work_hours" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="personnelForm.status">
            <el-option label="可用" value="available" />
            <el-option label="忙碌" value="busy" />
            <el-option label="休假" value="on_leave" />
            <el-option label="离职" value="resigned" />
          </el-select>
        </el-form-item>
      </el-form>

      <template v-if="!currentPersonnel?.id || isEditPersonnel" #footer>
        <div style="display: flex; justify-content: space-between;">
          <div>
            <el-button v-if="currentPersonnel?.id && isEditPersonnel" type="danger" @click="handleDeletePersonnel">删除</el-button>
          </div>
          <div>
            <el-button @click="closePersonnelDialog">取消</el-button>
            <el-button type="primary" @click="handlePersonnelSubmit">确定</el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { TopRight } from '@element-plus/icons-vue'
import { DataLine, Odometer, Clock, Warning, VideoPlay, User, Monitor, Box, Select, Guide } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import { createDependency, updateDependency, getGraphData } from '@/api/dependency'
import { getActivities, getActivity, createActivity, updateActivity, deleteActivity } from '@/api/activity'
import { getResources, getResource, createResource, updateResource, deleteResource } from '@/api/resource'
import { getPersonnelList as getPersonnel, getPersonnelById, createPersonnel, updatePersonnel, deletePersonnel } from '@/api/personnel'
import type { Dependency, GraphData, Activity, Resource, Personnel } from '@/types'
import DependencyGraph from '@/components/DependencyGraph.vue'
import DashboardPanel from '@/components/DashboardPanel.vue'
import { analyzeGraph, type AnalysisScope } from '@/utils/graphAnalyzer'
import { checkResources } from '@/utils/resourceChecker'
import { getRisks, type RiskItem } from '@/api/analytics'
import { sumSopStepDurations } from '@/utils/sopDuration'
import { shortestDirectedPath } from '@/utils/graphPath'

type PathAnalysisDashboardPayload = {
  sourceId: string
  targetId: string
  sourceName: string
  targetName: string
  steps: number
  totalSopMinutes: number
  orderedActivities: Array<{
    id: string
    name: string
    process_id?: string
    duration: number
    stepIndex: number
  }>
}

void VideoPlay
void User

const route = useRoute()
const router = useRouter()

const processOptions = computed(() => {
  const seen = new Set<string>()
  const list: Array<{ id: string; name: string }> = []
  ;(graphData.value.nodes || []).forEach((node: any) => {
    const pid = node?.process_id
    if (!pid || seen.has(pid)) return
    seen.add(pid)
    list.push({ id: pid, name: getProcessName(pid) })
  })
  return list.sort((a, b) => a.id.localeCompare(b.id))
})

const processNameMap: Record<string, string> = {
  P001: '主生产线',
  P002: '副生产线',
  T001: '冷链运输',
  T002: '常温运输',
  S001: '线上销售',
  S002: '线下销售',
  Q001: '常规质检',
  Q002: '专项质检',
  W001: '主仓库',
  W002: '分仓库'
}

const getProcessName = (processId: string) => processNameMap[processId] || '未知流程'

const formatProcessLabel = (processId: string, processName: string) => `${processId} - ${processName}`

/** 活动详情等场景：流程 ID →「ID - 名称」展示 */
const getProcessLabel = (processId: string | undefined) => {
  if (!processId) return '未知流程'
  const process = processOptions.value.find(p => p.id === processId)
  if (process) return formatProcessLabel(process.id, process.name)
  return formatProcessLabel(processId, getProcessName(processId))
}

const inferDomainFromProcessId = (processId: string) => {
  if (processId.startsWith('P')) return 'production'
  if (processId.startsWith('T')) return 'transport'
  if (processId.startsWith('S')) return 'sales'
  if (processId.startsWith('Q')) return 'quality'
  if (processId.startsWith('W')) return 'warehouse'
  return ''
}

const applySelectedProcessHighlight = () => {
  if (!currentProcessId.value) {
    ElMessage.warning('请先选择流程ID')
    return
  }
  const domain = inferDomainFromProcessId(currentProcessId.value)
  handleProcessChange(domain, currentProcessId.value)
}

// 当前选择的流程
const currentDomain = ref<string>('')
const currentProcessId = ref<string>('')
const highlightDomainFromQuery = ref<string>('')
const focusActivityFromQuery = ref<string>('')

// 从URL读取初始值
const initFromUrl = () => {
  const domain = route.query.domain as string
  const processId = route.query.process_id as string
  const highlightDomain = route.query.highlightDomain as string
  const focusActivity = route.query.focusActivity as string
  
  if (domain) {
    currentDomain.value = domain
  }
  if (processId) {
    currentProcessId.value = processId
  }
  highlightDomainFromQuery.value = highlightDomain || ''
  focusActivityFromQuery.value = focusActivity || ''
}

// 更新URL参数
const updateUrl = () => {
  router.replace({
    query: {
      domain: currentDomain.value,
      process_id: currentProcessId.value
    }
  })
}

// 处理流程切换
const handleProcessChange = (domain: string, processId: string) => {
  currentDomain.value = domain
  currentProcessId.value = processId
  updateUrl()
  
  loadActivities()
  loadResources()
  
  applyProcessHighlight()
}

const activities = ref<Activity[]>([])
const resources = ref<Resource[]>([])
const personnel = ref<Personnel[]>([])
const graphData = ref<GraphData>({ nodes: [], edges: [] })
const riskList = ref<RiskItem[]>([])

const minRunnableDays = computed<number | string>(() => {
  const list = riskList.value
    .map((risk) => risk.runnable_days)
    .filter((day): day is number => typeof day === 'number' && Number.isFinite(day))
  if (list.length === 0) return ''
  return Math.min(...list)
})

const miniRunnableTimeText = computed(() => {
  const runningStatuses = new Set(['in_progress', '进行中'])
  const activityNodes = (graphData.value.nodes || []).filter((node: any) =>
    (node?.type === 'activity' || node?.category === 'Activity') &&
    runningStatuses.has(node?.status) &&
    (!currentProcessId.value || node?.process_id === currentProcessId.value)
  )

  const runningActivityIds = new Set(activityNodes.map((node: any) => node.id))
  const usageEdges = ((graphData.value as any).resource_edges || []) as any[]
  const consumedRateByOriginalResourceId = new Map<string, number>()

  for (const edge of usageEdges) {
    const relation = String(edge?.relation || edge?.type || '').toUpperCase()
    if (relation !== 'CONSUMES') continue
    if (!runningActivityIds.has(edge?.source)) continue

    const resourceNode = ((graphData.value as any).resource_nodes || []).find((n: any) => n?.id === edge?.target)
    const originalId = resourceNode?.original_id || edge?.target
    const rate = Number(edge?.rate ?? edge?.quantity ?? edge?.value ?? edge?.weight)
    if (!originalId || !Number.isFinite(rate) || rate <= 0) continue
    consumedRateByOriginalResourceId.set(originalId, (consumedRateByOriginalResourceId.get(originalId) || 0) + rate)
  }

  const candidateDays: number[] = []
  for (const [resourceId, rate] of consumedRateByOriginalResourceId) {
    const resourceInfo = resources.value.find((r: any) => r?.id === resourceId || r?._id === resourceId)
    const remainingDays = Number((resourceInfo as any)?.remaining_days)
    if (Number.isFinite(remainingDays) && remainingDays >= 0) {
      candidateDays.push(remainingDays)
      continue
    }
    const quantity = Number((resourceInfo as any)?.quantity)
    if (Number.isFinite(quantity) && quantity >= 0 && rate > 0) {
      candidateDays.push(quantity / rate)
    }
  }

  const minDays = candidateDays.length > 0 ? Math.min(...candidateDays) : null
  const text = minDays === null || !Number.isFinite(minDays) || minDays < 0
    ? '充足'
    : (minDays > 999 ? '无限制' : `${minDays.toFixed(1)}天`)


  return text
})

// 高亮状态：FlowHighlightSet（流程选择器）和 DashboardHighlightSet（仪表盘）
const flowHighlightSet = ref<{nodeIds: Set<string>, edgeIds: Set<string>}>({
  nodeIds: new Set(),
  edgeIds: new Set()
})

const dashboardHighlightSet = ref<{nodeIds: Set<string>, edgeIds: Set<string>}>({
  nodeIds: new Set(),
  edgeIds: new Set()
})

// 最终高亮集合（并集）
const highlightActive = ref(false)
const highlightSet = ref<{nodeIds: Set<string>, edgeIds: Set<string>}>({
  nodeIds: new Set(),
  edgeIds: new Set()
})

// 两点路径分析专用高亮（优先级最高）
const pathHighlightSet = ref<{ nodeIds: Set<string>; edgeIds: Set<string> }>({
  nodeIds: new Set(),
  edgeIds: new Set()
})

// 路径分析状态机
const isPathSelecting = ref(false)
const pathStartNode = ref<any>(null)
const pathEndNode = ref<any>(null)
const currentCriticalPath = ref<PathAnalysisDashboardPayload | null>(null)

const togglePathSelectionMode = () => {
  isPathSelecting.value = !isPathSelecting.value
  if (!isPathSelecting.value) {
    resetPathSelection()
  } else {
    pathStartNode.value = null
    pathEndNode.value = null
    currentCriticalPath.value = null
    pathHighlightSet.value = { nodeIds: new Set(), edgeIds: new Set() }
    updateHighlightUnion()
    ElMessage.info('已进入路径分析模式：请左键点击一个节点作为【起点】')
  }
}

const resetPathSelection = () => {
  isPathSelecting.value = false
  pathStartNode.value = null
  pathEndNode.value = null
  currentCriticalPath.value = null
  pathHighlightSet.value = { nodeIds: new Set(), edgeIds: new Set() }
  updateHighlightUnion()
}

const runPathAnalysisHighlight = (sourceId: string, targetId: string) => {
  const edges = graphData.value.edges || []
  const res = shortestDirectedPath(
    edges.map((e: any) => ({ source: e.source, target: e.target })),
    sourceId,
    targetId
  )
  if (!res) {
    ElMessage.error('该起点和终点之间不存在直接连通的生产链路！')
    resetPathSelection()
    return
  }
  const nodeMap = new Map<string, any>((graphData.value.nodes || []).map((n: any) => [n.id, n]))
  const orderedActivities = res.nodeIds.map((id, idx) => {
    const n = nodeMap.get(id)
    const duration = n ? sumSopStepDurations(n.sop_steps) : 0
    return {
      id,
      name: n?.name || id,
      process_id: n?.process_id,
      duration,
      stepIndex: idx + 1
    }
  })
  const totalSopMinutes = orderedActivities.reduce((s, a) => s + a.duration, 0)

  const anchorNode =
    nodeMap.get(sourceId) ||
    orderedActivities.map(a => nodeMap.get(a.id)).find((n: any) => n?.process_id)
  const anchorPid = anchorNode?.process_id
  const anchorDomain = anchorNode?.domain
  if (anchorPid) {
    if (anchorDomain) currentDomain.value = anchorDomain
    if (currentProcessId.value !== anchorPid) {
      currentProcessId.value = anchorPid
      updateUrl()
    }
  }

  pathHighlightSet.value = {
    nodeIds: new Set(res.nodeIds),
    edgeIds: new Set(res.edgeIds)
  }
  currentCriticalPath.value = {
    sourceId,
    targetId,
    sourceName: orderedActivities[0]?.name || sourceId,
    targetName: orderedActivities[orderedActivities.length - 1]?.name || targetId,
    steps: res.nodeIds.length,
    totalSopMinutes,
    orderedActivities
  }
  pathStartNode.value = null
  pathEndNode.value = null
  updateHighlightUnion()
  ElMessage.success(`已高亮最短路径（${res.nodeIds.length} 个活动）`)
}

const handlePathNodePick = (payload: { id: string; rawData: any }) => {
  const { id, rawData } = payload
  if (!pathStartNode.value) {
    pathStartNode.value = rawData
    ElMessage.success(`已设置起点: ${rawData.name || id}，请继续点击终点`)
    return
  }
  if (id === pathStartNode.value.id) {
    ElMessage.warning('请选择另一个活动作为终点')
    return
  }
  pathEndNode.value = rawData
  ElMessage.success(`已设置终点: ${rawData.name || id}，正在计算路径...`)
  isPathSelecting.value = false
  runPathAnalysisHighlight(pathStartNode.value.id, id)
}

const handlePathSelectionCancel = () => {
  if (!isPathSelecting.value) return
  resetPathSelection()
  ElMessage.warning('已取消路径分析')
}

// 计算并集并更新最终高亮集合
// 策略：路径分析 > 仪表盘 > 流程
const updateHighlightUnion = () => {
  const hasPathHighlight =
    pathHighlightSet.value.nodeIds.size > 0 || pathHighlightSet.value.edgeIds.size > 0
  const hasDashboardHighlight =
    dashboardHighlightSet.value.nodeIds.size > 0 || dashboardHighlightSet.value.edgeIds.size > 0

  let nodeIds: Set<string>
  let edgeIds: Set<string>

  if (hasPathHighlight) {
    nodeIds = new Set(pathHighlightSet.value.nodeIds)
    edgeIds = new Set(pathHighlightSet.value.edgeIds)
  } else if (hasDashboardHighlight) {
    nodeIds = new Set(dashboardHighlightSet.value.nodeIds)
    edgeIds = new Set(dashboardHighlightSet.value.edgeIds)
  } else {
    nodeIds = new Set(flowHighlightSet.value.nodeIds)
    edgeIds = new Set(flowHighlightSet.value.edgeIds)
  }
  highlightSet.value = { nodeIds, edgeIds }
  highlightActive.value = nodeIds.size > 0 || edgeIds.size > 0
}

const loadActivities = async () => {
  try {
    activities.value = await getActivities({ 
      domain: currentDomain.value, 
      process_id: currentProcessId.value 
    })
  } catch (error) {
    ElMessage.error('加载活动失败')
  }
}

const loadResources = async () => {
  try {
    resources.value = await getResources({
      domain: currentDomain.value,
      process_id: currentProcessId.value
    })
  } catch (error) {
    ElMessage.error('加载资源失败')
  }
}

const loadPersonnel = async () => {
  try {
    personnel.value = await getPersonnel()
  } catch (error) {
    ElMessage.error('加载人员失败')
  }
}

// 加载全局图数据
const loadGlobalGraphData = async () => {
  try {
    graphData.value = await getGraphData({ scope: 'global' })
  } catch (error) {
    ElMessage.error('加载图数据失败')
  }
}

// 应用流程高亮
const applyProcessHighlight = () => {
  if (!currentDomain.value || !currentProcessId.value) {
    ElMessage.warning('请先选择流程域和流程ID')
    return
  }
  
  const nodeIds = new Set<string>()
  const edgeIds = new Set<string>()
  
  graphData.value.nodes?.forEach((node: any) => {
    if (node.domain === currentDomain.value && node.process_id === currentProcessId.value) {
      nodeIds.add(node.id)
    }
  })
  
  graphData.value.edges?.forEach((edge: any) => {
    if (edge.domain === currentDomain.value && edge.process_id === currentProcessId.value) {
      edgeIds.add(`${edge.source}-${edge.target}`)
    }
  })
  
  if (nodeIds.size === 0) {
    ElMessage.warning(`未找到 ${currentDomain.value}/${currentProcessId.value} 相关节点`)
    return
  }
  
  // 清除仪表盘高亮（如导航带来的 focusActivity），让流程高亮生效
  dashboardHighlightSet.value = { nodeIds: new Set(), edgeIds: new Set() }
  pathHighlightSet.value = { nodeIds: new Set(), edgeIds: new Set() }
  currentCriticalPath.value = null
  isPathSelecting.value = false
  pathStartNode.value = null
  pathEndNode.value = null
  flowHighlightSet.value = { nodeIds, edgeIds }
  updateHighlightUnion()
  
  ElMessage.success(`已定位到 ${currentDomain.value}/${currentProcessId.value}（${nodeIds.size}个节点）`)
}

// 清除流程高亮
const clearFlowHighlight = () => {
  currentDomain.value = ''
  currentProcessId.value = ''
  flowHighlightSet.value = { nodeIds: new Set(), edgeIds: new Set() }
  // 同时清除仪表盘高亮，确保完全恢复全局视图
  dashboardHighlightSet.value = { nodeIds: new Set(), edgeIds: new Set() }
  pathHighlightSet.value = { nodeIds: new Set(), edgeIds: new Set() }
  currentCriticalPath.value = null
  isPathSelecting.value = false
  pathStartNode.value = null
  pathEndNode.value = null
  updateHighlightUnion()
  updateUrl()
  ElMessage.success('已恢复全局视图')
}

const applyRouteFocusHighlight = () => {
  const focusId = focusActivityFromQuery.value
  const domain = highlightDomainFromQuery.value
  if (!focusId && !domain) return

  if (domain) {
    currentDomain.value = domain
  }

  if (!focusId) return
  const node = graphData.value.nodes.find((item: any) => item.id === focusId)
  if (node) {
    if (node.domain) currentDomain.value = node.domain
    if (node.process_id) currentProcessId.value = node.process_id
  }

  pathHighlightSet.value = { nodeIds: new Set(), edgeIds: new Set() }
  currentCriticalPath.value = null
  dashboardHighlightSet.value = {
    nodeIds: new Set([focusId]),
    edgeIds: new Set()
  }
  updateHighlightUnion()
}

// 计算 KPI 指标
const metrics = computed(() => {
  const scope: AnalysisScope = currentProcessId.value 
    ? { type: 'process', processId: currentProcessId.value }
    : { type: 'global' }
  
  const analysis = analyzeGraph(graphData.value, scope)

  const nodeMap = new Map<string, any>(
    (graphData.value.nodes || []).map((node: any) => [node.id, node])
  )
  let internalDependencyCount = 0
  let externalDependencyCount = 0

  ;(graphData.value.edges || []).forEach((edge: any) => {
    const sourceNode = nodeMap.get(edge.source)
    const targetNode = nodeMap.get(edge.target)
    if (!sourceNode || !targetNode) return

    if (sourceNode.process_id === targetNode.process_id) {
      internalDependencyCount += 1
    } else {
      externalDependencyCount += 1
    }
  })

  const resourceCheck = checkResources(graphData.value, currentProcessId.value)
  
  return {
    activityCount: analysis.scale.activityCount,
    internalDependencyCount,
    externalDependencyCount,
    healthScore: analysis.health.score,
    issueCount: analysis.health.issueCount,
    resourceShortageCount: resourceCheck.dataLevel === 'level1' ? resourceCheck.shortageCount : resourceCheck.riskList?.length || 0,
    dynamicRiskCount: 0
  }
})

// KPI 点击处理
const handleKpiClick = (type: string) => {
  if (type === 'activities') {
    const activityIds = graphData.value.nodes.filter((n: any) => n.type === 'activity' || n.category === 'Activity').map((n: any) => n.id)
    handleDashboardHighlight({ nodeIds: activityIds, edgeIds: [] })
  } else if (type === 'internalDependencies' || type === 'externalDependencies') {
    const nodeMap = new Map<string, any>(
      (graphData.value.nodes || []).map((node: any) => [node.id, node])
    )
    const edgeIds = (graphData.value.edges || [])
      .filter((edge: any) => {
        const sourceNode = nodeMap.get(edge.source)
        const targetNode = nodeMap.get(edge.target)
        if (!sourceNode || !targetNode) return false
        const isInternal = sourceNode.process_id === targetNode.process_id
        return type === 'internalDependencies' ? isInternal : !isInternal
      })
      .map((e: any) => `${e.source}-${e.target}`)
    handleDashboardHighlight({ nodeIds: [], edgeIds })
  }
}

// 处理仪表盘高亮请求
const handleDashboardHighlight = (payload: { nodeIds: string[], edgeIds: string[] }) => {
  pathHighlightSet.value = { nodeIds: new Set(), edgeIds: new Set() }
  currentCriticalPath.value = null
  dashboardHighlightSet.value = {
    nodeIds: new Set(payload.nodeIds),
    edgeIds: new Set(payload.edgeIds)
  }
  updateHighlightUnion()
}

// 处理流程选择请求（来自仪表盘全局排行点击）
const handleProcessSelect = (payload: { processId: string }) => {
  const node = graphData.value.nodes?.find((n: any) => n.process_id === payload.processId)
  if (node) {
    currentDomain.value = node.domain || ''
    currentProcessId.value = payload.processId
    updateUrl()
    applyProcessHighlight()
  }
}

// 刷新图数据
const loadGraphData = async () => {
  await loadGlobalGraphData()
  if (highlightActive.value && currentDomain.value && currentProcessId.value) {
    applyProcessHighlight()
  }
}

const loadRiskList = async () => {
  try {
    riskList.value = await getRisks(currentDomain.value || undefined)
  } catch (error) {
    riskList.value = []
    ElMessage.error('加载风险数据失败')
  }
}

// 依赖关系对话框
const dependencyDialogVisible = ref(false)
const isEditDependency = ref(false)
const dependencyForm = ref<Dependency>({
  source_activity_id: '',
  target_activity_id: '',
  dependency_type: 'sequential',
  status: 'active',
  domain: 'production',
  process_id: 'P001'
})

// 活动对话框
const activityDialogVisible = ref(false)
const isEditActivity = ref(false)
const currentActivity = ref<Activity | null>(null)
const activityForm = ref<Activity>({
  name: '',
  description: '',
  activity_type: '',
  sop_steps: [],
  required_resources: [],
  required_personnel: [],
  status: 'pending',
  domain: 'production',
  process_id: 'P001'
})

const sopTotalMinutesDetail = computed(() => sumSopStepDurations(activityForm.value.sop_steps))

// 资源对话框
const resourceDialogVisible = ref(false)
const isEditResource = ref(false)
const currentResource = ref<Resource | null>(null)
const currentResourceEdgeRate = ref<number | string>(0)
const resourceForm = ref<Resource>({
  name: '',
  type: '',
  specification: '',
  supplier: '',
  quantity: 0,
  unit: '',
  status: 'available'
})

// 人员对话框
const personnelDialogVisible = ref(false)
const isEditPersonnel = ref(false)
const currentPersonnel = ref<Personnel | null>(null)
const personnelForm = ref<Personnel>({
  name: '',
  role: '',
  responsibility: '',
  skills: [],
  work_hours: '',
  assigned_tasks: [],
  status: 'available'
})

const closeEntityDetailDialogs = () => {
  activityDialogVisible.value = false
  resourceDialogVisible.value = false
  personnelDialogVisible.value = false
  isEditActivity.value = false
  isEditResource.value = false
  isEditPersonnel.value = false
}

const resolveActivityIdForNavigation = () =>
  currentActivity.value?.id ||
  activityForm.value.id ||
  (activityForm.value as any)._id

const resolveResourceIdForNavigation = () =>
  currentResource.value?.id ||
  resourceForm.value.id ||
  (resourceForm.value as any)._id

const resolvePersonnelIdForNavigation = () =>
  currentPersonnel.value?.id ||
  personnelForm.value.id ||
  (personnelForm.value as any)._id

const goToActivityManagementFromDialog = () => {
  const id = resolveActivityIdForNavigation()
  if (!id) {
    ElMessage.warning('缺少活动 ID，无法跳转到生产活动管理')
    return
  }
  closeEntityDetailDialogs()
  router.push({ name: 'Dashboard', query: { highlightId: String(id) } })
}

const goToEquipmentManagementFromDialog = () => {
  if (currentResource.value?.type !== '设备') {
    ElMessage.warning('当前不是设备资源')
    return
  }
  const id = resolveResourceIdForNavigation()
  if (!id) {
    ElMessage.warning('缺少设备 ID，无法跳转')
    return
  }
  closeEntityDetailDialogs()
  router.push({ name: 'Equipment', query: { highlightId: String(id) } })
}

const goToMaterialManagementFromDialog = () => {
  const t = currentResource.value?.type || resourceForm.value.type
  const isMaterial =
    t === '原料' || String(t || '').toLowerCase() === 'material'
  if (!isMaterial) {
    ElMessage.warning('当前不是原料资源')
    return
  }
  const id = resolveResourceIdForNavigation()
  if (!id) {
    ElMessage.warning('缺少原料 ID，无法跳转')
    return
  }
  closeEntityDetailDialogs()
  router.push({ name: 'Material', query: { highlightId: String(id) } })
}

const goToPersonnelManagementFromDialog = () => {
  const id = resolvePersonnelIdForNavigation()
  if (!id) {
    ElMessage.warning('缺少人员 ID，无法跳转')
    return
  }
  closeEntityDetailDialogs()
  router.push({ name: 'Personnel', query: { highlightId: String(id) } })
}

// 节点点击处理
const handleNodeClick = async (node: any) => {
  if (node.category === 'Activity') {
    try {
      const activity = await getActivity(node.id)
      if ((activity as any)._id && !activity.id) {
        activity.id = (activity as any)._id
      }
      currentActivity.value = activity
      activityForm.value = { ...activity }
      isEditActivity.value = false
      activityDialogVisible.value = true
    } catch (error) {
      ElMessage.error('加载活动详情失败')
    }
  } else if (node.category === 'Resource') {
    try {
      // 优先从 rawData 获取原始ID，否则使用节点ID
      // 注意：节点ID可能是组合ID（如 id_inst_parent），需要解析或使用 rawData.original_id
      const resourceId = node.rawData?.original_id || node.id
      
      // 如果依然是组合ID，尝试从字符串解析
      let finalResourceId = resourceId;
      if (finalResourceId && finalResourceId.includes('_inst_')) {
          finalResourceId = finalResourceId.split('_inst_')[0];
      }

      const resource = await getResource(finalResourceId)
      if ((resource as any)._id && !resource.id) {
        resource.id = (resource as any)._id
      }

      // ================== 强化：消耗速率地毯式提取逻辑 ==================
      const allEdges = [
        ...(graphData.value.edges || []),
        ...((graphData.value as GraphData & { resource_edges?: any[] }).resource_edges || [])
      ]

      const targetIds = [node.id, node.rawData?.original_id, node.rawData?._id, finalResourceId].filter(Boolean)
      const relatedEdges = allEdges.filter((e: any) =>
        targetIds.includes(e.source) || targetIds.includes(e.target)
      )

      const relUpper = (e: any) => String(e.relation || e.type || '').toUpperCase()
      const isMaterial =
        resource.type === '原料' ||
        String(resource.type || '').toLowerCase() === 'material'
      const consumesEdges = relatedEdges.filter((e: any) => relUpper(e) === 'CONSUMES')
      const edgesToScan = isMaterial
        ? (consumesEdges.length > 0 ? consumesEdges : [])
        : relatedEdges

      let foundRate = 0

      for (const edge of edgesToScan) {
        const rateVal =
          (edge as any).rate ??
          (edge as any).quantity ??
          (edge as any).value ??
          (edge as any).rawData?.rate ??
          (edge as any).rawData?.properties?.rate ??
          (edge as any).data?.rate ??
          (edge as any).data?.properties?.rate

        const numRate = Number(rateVal)
        if (!isNaN(numRate) && numRate > 0) {
          if (numRate !== 1 || foundRate === 0) {
            foundRate = numRate
          }
        }
      }

      currentResourceEdgeRate.value = foundRate
      // =================================================================

      currentResource.value = resource
      resourceForm.value = { ...resource }
      isEditResource.value = false
      resourceDialogVisible.value = true
    } catch (error) {
      ElMessage.error('加载资源详情失败')
    }
  } else if (node.category === 'Personnel') {
    try {
      const personnelId = node.rawData?.original_id || node.id
      
      // 如果依然是组合ID，尝试从字符串解析
      let finalPersonnelId = personnelId;
      if (finalPersonnelId && finalPersonnelId.includes('_inst_')) {
          finalPersonnelId = finalPersonnelId.split('_inst_')[0];
      }

      const person = await getPersonnelById(finalPersonnelId)
      if ((person as any)._id && !person.id) {
        person.id = (person as any)._id
      }
      currentPersonnel.value = person
      personnelForm.value = { ...person }
      isEditPersonnel.value = false
      personnelDialogVisible.value = true
    } catch (error) {
      ElMessage.error('加载人员详情失败')
    }
  }
}

// 从图表编辑活动
const handleEditActivityFromGraph = async (activity: any) => {
  try {
    const fullActivity = await getActivity(activity.id)
    if ((fullActivity as any)._id && !fullActivity.id) {
      fullActivity.id = (fullActivity as any)._id
    }
    currentActivity.value = fullActivity
    activityForm.value = { ...fullActivity }
    isEditActivity.value = true
    activityDialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载活动详情失败')
  }
}

// 从图表编辑人员
const handleEditPersonnelFromGraph = async (personnel: any) => {
  try {
    const personnelId = personnel.rawData?.original_id || personnel.id
    let finalPersonnelId = personnelId
    if (finalPersonnelId && finalPersonnelId.includes('_inst_')) {
      finalPersonnelId = finalPersonnelId.split('_inst_')[0]
    }
    const person = await getPersonnelById(finalPersonnelId)
    if ((person as any)._id && !person.id) {
      person.id = (person as any)._id
    }
    currentPersonnel.value = person
    personnelForm.value = { ...person }
    isEditPersonnel.value = true
    personnelDialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载人员详情失败')
  }
}

// 从图表编辑资源
const handleEditResourceFromGraph = async (resource: any) => {
  try {
    const resourceId = resource.rawData?.original_id || resource.id
    let finalResourceId = resourceId
    if (finalResourceId && finalResourceId.includes('_inst_')) {
      finalResourceId = finalResourceId.split('_inst_')[0]
    }
    const fullResource = await getResource(finalResourceId)
    if ((fullResource as any)._id && !fullResource.id) {
      fullResource.id = (fullResource as any)._id
    }
    currentResource.value = fullResource
    resourceForm.value = { ...fullResource }
    isEditResource.value = true
    resourceDialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载资源详情失败')
  }
}

const handleDependencySubmit = async () => {
  try {
    if (isEditDependency.value && dependencyForm.value.id) {
      await updateDependency(dependencyForm.value.id, dependencyForm.value)
      ElMessage.success('更新成功')
    } else {
      await createDependency(dependencyForm.value)
      ElMessage.success('创建成功')
    }
    dependencyDialogVisible.value = false
    await loadGraphData()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

// 活动操作
const handleActivitySubmit = async () => {
  try {
    const { estimated_duration: _omit, ...payload } = activityForm.value
    if (currentActivity.value?.id) {
      await updateActivity(currentActivity.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await createActivity(payload as Activity)
      ElMessage.success('创建成功')
    }
    activityDialogVisible.value = false
    isEditActivity.value = false
    await loadActivities()
    await loadGraphData()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const closeActivityDialog = () => {
  activityDialogVisible.value = false
  isEditActivity.value = false
}

const handleDeleteActivity = async () => {
  try {
    await ElMessageBox.confirm('确定删除该活动?', '提示', {
      type: 'warning'
    })
    if (currentActivity.value?.id) {
      await deleteActivity(currentActivity.value.id)
      ElMessage.success('删除成功')
      activityDialogVisible.value = false
      await loadActivities()
      await loadGraphData()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 资源操作
const handleResourceSubmit = async () => {
  try {
    if (currentResource.value?.id) {
      await updateResource(currentResource.value.id, resourceForm.value)
      ElMessage.success('更新成功')
    } else {
      await createResource(resourceForm.value)
      ElMessage.success('创建成功')
    }
    resourceDialogVisible.value = false
    isEditResource.value = false
    await loadResources()
    await loadGraphData()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const closeResourceDialog = () => {
  resourceDialogVisible.value = false
  isEditResource.value = false
}

const handleDeleteResource = async () => {
  try {
    await ElMessageBox.confirm('确定删除该资源?', '提示', {
      type: 'warning'
    })
    if (currentResource.value?.id) {
      await deleteResource(currentResource.value.id)
      ElMessage.success('删除成功')
      resourceDialogVisible.value = false
      await loadResources()
      await loadGraphData()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 人员操作
const isPersonnelResigningStatus = (s: string | undefined) => {
  const v = String(s || '').toLowerCase()
  return v === 'resigned' || v === '离职'
}

const handlePersonnelSubmit = async () => {
  if (!personnelForm.value.name?.trim() || !personnelForm.value.role?.trim() || !personnelForm.value.responsibility?.trim()) {
    console.error('表单校验失败')
    ElMessage.warning('请检查表单填写是否有误')
    return
  }
  const prevStatus = currentPersonnel.value?.status
  const nextStatus = personnelForm.value.status
  if (
    currentPersonnel.value?.id &&
    !isPersonnelResigningStatus(prevStatus) &&
    isPersonnelResigningStatus(nextStatus)
  ) {
    try {
      await ElMessageBox.confirm(
        '将员工状态设为「离职」将自动解除其当前在图谱中关联的所有生产活动分配，是否继续？',
        '高危操作确认',
        {
          confirmButtonText: '确定离职并解绑',
          cancelButtonText: '取消',
          type: 'warning',
          confirmButtonClass: 'el-button--danger'
        }
      )
    } catch {
      return
    }
  }
  const { id, work_hours, assigned_tasks, created_at, updated_at, department, ...restPersonnel } = personnelForm.value as Personnel
  const payload = {
    ...restPersonnel,
    name: restPersonnel.name,
    role: restPersonnel.role,
    responsibility: restPersonnel.responsibility,
    skills: restPersonnel.skills,
    status: restPersonnel.status,
    upcoming_leaves: restPersonnel.upcoming_leaves,
    age: restPersonnel.age,
    gender: restPersonnel.gender,
    native_place: restPersonnel.native_place,
    hire_date: restPersonnel.hire_date,
    education: restPersonnel.education,
    salary: restPersonnel.salary
  }
  try {
    if (currentPersonnel.value?.id) {
      await updatePersonnel(currentPersonnel.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await createPersonnel(payload as Personnel)
      ElMessage.success('创建成功')
    }
    personnelDialogVisible.value = false
    isEditPersonnel.value = false
    await loadPersonnel()
    await loadGraphData()
  } catch (error) {
    ElMessage.error(`保存失败: ${error instanceof Error ? error.message : String(error)}`)
  }
}

const closePersonnelDialog = () => {
  personnelDialogVisible.value = false
  isEditPersonnel.value = false
}

const handleDeletePersonnel = async () => {
  try {
    await ElMessageBox.confirm('确定删除该人员?', '提示', {
      type: 'warning'
    })
    if (currentPersonnel.value?.id) {
      await deletePersonnel(currentPersonnel.value.id)
      ElMessage.success('删除成功')
      personnelDialogVisible.value = false
      await loadPersonnel()
      await loadGraphData()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const onPersonnelNeo4jAssignmentsChanged = () => {
  void loadPersonnel()
  void loadGraphData()
}

onMounted(async () => {
  window.addEventListener('personnel-neo4j-assignments-changed', onPersonnelNeo4jAssignmentsChanged)
  initFromUrl()
  await loadGlobalGraphData()
  applyRouteFocusHighlight()
  
  if (currentDomain.value && currentProcessId.value) {
    await loadActivities()
  }
  // 全局首屏也需要加载资源，否则 mini 可运行时间会长期停留在“充足”
  await loadResources()
  await loadPersonnel()
  await loadRiskList()
})

onUnmounted(() => {
  window.removeEventListener('personnel-neo4j-assignments-changed', onPersonnelNeo4jAssignmentsChanged)
})

watch([currentDomain, currentProcessId], async () => {
  await loadRiskList()
})

watch(
  () => [route.query.highlightDomain, route.query.focusActivity],
  async () => {
    const newHighlightDomain = (route.query.highlightDomain as string) || ''
    const newFocusActivity = (route.query.focusActivity as string) || ''
    highlightDomainFromQuery.value = newHighlightDomain
    focusActivityFromQuery.value = newFocusActivity
    // 只有在新参数非空时（真正从外部导航过来）才重载图，
    // 避免 updateUrl() 清除参数时触发不必要的图重建并导致高亮丢失
    if (newHighlightDomain || newFocusActivity) {
      await loadGlobalGraphData()
      applyRouteFocusHighlight()
    }
  }
)
</script>

<style scoped>
.tooltip {
  cursor: pointer;
}
</style>
