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
}

export interface Personnel {
  id?: string
  name: string
  role: string
  responsibility: string
  skills: string[]
  work_hours: string
  assigned_tasks: string[]
  status: string
  created_at?: string
  updated_at?: string
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
  step_number: number
  description: string
  duration: number
}

export interface Activity {
  id?: string
  name: string
  description: string
  activity_type: string
  sop_steps: SOPStep[]
  estimated_duration: number
  duration_minutes?: number
  deadline?: string
  required_resources: string[]
  required_personnel: string[]
  status: string
  domain: string
  process_id: string
  version?: number
  is_active?: boolean
  created_at?: string
  updated_at?: string
  material_requirements?: MaterialRequirement[]
  personnel_requirements?: PersonnelRequirement[]
  equipment_requirements?: EquipmentRequirement[]
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
  consumption_rate_per_day: number
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
  estimated_duration: number
  material_requirements: MaterialRequirement[]
  personnel_requirements: PersonnelRequirement[]
  equipment_requirements: EquipmentRequirement[]
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

