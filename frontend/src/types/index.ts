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
}

