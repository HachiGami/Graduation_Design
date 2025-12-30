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
  name: string
  predecessor_stage: string
  successor_stage: string
  dependency_type: string
  time_constraint?: number
  condition?: string
  created_at?: string
  updated_at?: string
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
  deadline?: string
  required_resources: string[]
  required_personnel: string[]
  status: string
  created_at?: string
  updated_at?: string
}

