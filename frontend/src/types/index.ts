export interface Resource {
  id?: string
  name: string
  type: string
  specification: string
  supplier: string
  quantity: number
  unit: string
  expiry_date?: string
  status: string
  domain?: string
  process_id?: string
  version?: number
  is_active?: boolean
  created_at?: string
  updated_at?: string
  /** 设备多活动占用时拖拽排序持久化（activity_id 列表，靠前优先） */
  equipment_activity_priority_order?: string[]
}

/** 列表接口从 Neo4j 聚合的当前服务活动（见后端 PersonnelResponse） */
export interface PersonnelServingActivityDetail {
  activity_name: string
  activity_id?: string
  process_id?: string
  status?: string
  working_hours?: Array<{ start_time?: string; end_time?: string }>
}

export interface Personnel {
  id?: string
  name: string
  role: string
  department?: string
  responsibility: string
  skills: string[]
  work_hours: string
  assigned_tasks: string[]
  status: string
  upcoming_leaves?: string[]
  age?: number
  gender?: string
  native_place?: string
  hire_date?: string
  education?: string
  salary?: number
  created_at?: string
  updated_at?: string
  serving_activities_details?: PersonnelServingActivityDetail[]
  serving_processes?: string[]
}

export interface Dependency {
  id?: string
  source_activity_id: string
  target_activity_id: string
  dependency_type: string
  time_constraint?: number
  lag_minutes?: number
  status?: string
  description?: string
  domain: string
  process_id: string
  created_at?: string
}

export interface ResourceUsage {
  id?: string
  activity_id: string
  resource_id: string
  quantity: number
  unit: string
  stage?: string
  domain?: string
  process_id?: string
}

export interface GraphNode {
  id: string
  name: string
  type: string
  status: string
  risks?: string[]
  domain?: string
  process_id?: string
  parent_activity?: string
  estimated_duration?: number
  description?: string
}

export interface GraphEdge {
  source: string
  target: string
  type: string
  time_constraint?: number
  description?: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  resource_nodes?: GraphNode[]
  resource_edges?: GraphEdge[]
  personnel_nodes?: GraphNode[]
  personnel_edges?: GraphEdge[]
}

export interface SOPStep {
  content: string
  duration: number
}

export interface TimeWindow {
  start_time: string
  end_time: string
}

export interface Activity {
  id?: string
  name: string
  description: string
  activity_type?: string
  sop_steps: SOPStep[]
  /** @deprecated 由后端根据 SOP 计算，前端不再手动维护或提交 */
  estimated_duration?: number
  duration_minutes?: number
  deadline?: string
  required_resources: string[]
  required_personnel: string[]
  status: string
  domain: string
  process_id: string
  predecessor_ids?: string[]
  predecessor_id?: string | null
  version?: number
  is_active?: boolean
  working_hours?: TimeWindow[]
  created_at?: string
  updated_at?: string
  material_requirements?: MaterialRequirement[]
  personnel_requirements?: PersonnelRequirement[]
  equipment_requirements?: EquipmentRequirement[]
  personnel_roles_required?: string[]
  equipment_types_required?: string[]
  risks?: string[]
}

// ── 活动资源分配面板专用类型 ───────────────────────────────────────

export interface ActivityResourcesPersonnel {
  id: string
  name: string
  role: string
}

export interface ActivityResourcesEquipment {
  id: string
  name: string
  specification: string
}

export interface ActivityResourcesConsumed {
  resource_id: string
  name: string
  rate: number
}

export interface ActivityResourcesData {
  personnel_roles_required: string[]
  equipment_types_required: string[]
  assigned_personnel: ActivityResourcesPersonnel[]
  assigned_equipment: ActivityResourcesEquipment[]
  consumed_resources: ActivityResourcesConsumed[]
}

export interface UpdateActivityResourcesPayload {
  personnel_roles: string[]
  equipment_types: string[]
  assigned_personnel_ids: string[]
  assigned_equipment_ids: string[]
  consumed_resources: { resource_id: string; rate: number }[]
}

// Asset (资产) 相关类型
export interface Asset {
  id?: string
  model: string
  name: string
  asset_type: 'equipment' | 'material'
  specification?: string
  supplier?: string
  status: 'idle' | 'in_use' | 'maintenance' | 'available'
  quantity?: number
  unit?: string
  created_at?: string
  updated_at?: string
}

// 资源需求类型
export interface MaterialRequirement {
  material_model: string
  hourly_consumption_rate: number
  consumption_rate_per_day?: number
  unit: string
}

export interface PersonnelRequirement {
  role: string
  count: number
}

export interface EquipmentRequirement {
  equipment_model: string
  count: number
}

// 实际分配类型
export interface MaterialAllocation {
  asset_id: string
  name: string
  allocated_rate: number
  unit: string
}

export interface PersonnelAllocation {
  id: string
  name: string
  role: string
}

export interface EquipmentAllocation {
  asset_id: string
  name: string
  model: string
}

export interface ActualAllocations {
  materials: MaterialAllocation[]
  personnel: PersonnelAllocation[]
  equipment: EquipmentAllocation[]
}

// 活动详情（包含需求和分配）
export interface ActivityDetails {
  id: string
  name: string
  description: string
  status: string
  process_id: string
  domain: string
  /** @deprecated 由后端根据 SOP 计算 */
  estimated_duration?: number
  material_requirements: MaterialRequirement[]
  personnel_requirements: PersonnelRequirement[]
  equipment_requirements: EquipmentRequirement[]
  personnel_roles_required?: string[]
  equipment_types_required?: string[]
  risks?: string[]
  actual_allocations: ActualAllocations
}

// 合规性检查结果
export interface ComplianceCheckResult {
  is_compliant: boolean
  missing_resources: {
    type: 'material' | 'personnel' | 'equipment'
    resource: string
    required: number | string
    actual: number | string
    available?: string[]
  }[]
}

