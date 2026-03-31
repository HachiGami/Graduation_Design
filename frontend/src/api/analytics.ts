import request from './request'

export interface DynamicRiskEvent {
  type: 'equipment_shortage' | 'personnel_overload'
  timeWindow: string
  gap: number
  activityIds: string[]
  description: string
}

export interface DynamicRisksResponse {
  equipmentShortages: DynamicRiskEvent[]
  personnelOverloads: DynamicRiskEvent[]
}

export interface RiskItem {
  risk_type: 'material_shortage' | 'allocation_shortage' | 'upcoming_absence'
  level: 'high' | 'medium' | 'low'
  activity_name: string
  message: string
  domain?: string | null
  process_id?: string | null
  runnable_days?: number | null
}

export const getRisks = (domain?: string) => {
  return request.get('/analytics/risks', { params: { domain } })
}

/**
 * 获取动态风险数据（当前返回mock数据）
 */
export async function getDynamicRisks(processId?: string): Promise<DynamicRisksResponse> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(getMockDynamicRisks(processId))
    }, 300)
  })
}

/**
 * Mock动态风险数据
 */
function getMockDynamicRisks(processId?: string): DynamicRisksResponse {
  if (processId) {
    return getMockDataForProcess(processId)
  }
  
  return {
    equipmentShortages: [
      {
        type: 'equipment_shortage',
        timeWindow: 'T1-T5',
        gap: 2,
        activityIds: ['mock-act-1', 'mock-act-2'],
        description: '生产设备并发需求超过容量2台'
      },
      {
        type: 'equipment_shortage',
        timeWindow: 'T8-T12',
        gap: 1,
        activityIds: ['mock-act-3'],
        description: '包装设备峰值不足1台'
      }
    ],
    personnelOverloads: [
      {
        type: 'personnel_overload',
        timeWindow: 'T3-T7',
        gap: 1.5,
        activityIds: ['mock-act-4', 'mock-act-5'],
        description: '操作人员超载1.5倍'
      }
    ]
  }
}

/**
 * 按流程返回mock数据
 */
function getMockDataForProcess(processId: string): DynamicRisksResponse {
  const mockData: Record<string, DynamicRisksResponse> = {
    'P001': {
      equipmentShortages: [
        {
          type: 'equipment_shortage',
          timeWindow: 'T2-T4',
          gap: 1,
          activityIds: ['mock-p001-1'],
          description: 'P001生产线设备不足1台'
        }
      ],
      personnelOverloads: [
        {
          type: 'personnel_overload',
          timeWindow: 'T1-T3',
          gap: 0.8,
          activityIds: ['mock-p001-2'],
          description: 'P001人员超载0.8倍'
        }
      ]
    },
    'T001': {
      equipmentShortages: [
        {
          type: 'equipment_shortage',
          timeWindow: 'T5-T8',
          gap: 2,
          activityIds: ['mock-t001-1'],
          description: 'T001运输车辆不足2辆'
        }
      ],
      personnelOverloads: []
    },
    'S001': {
      equipmentShortages: [],
      personnelOverloads: [
        {
          type: 'personnel_overload',
          timeWindow: 'T10-T15',
          gap: 1.2,
          activityIds: ['mock-s001-1', 'mock-s001-2'],
          description: 'S001销售人员超载1.2倍'
        }
      ]
    }
  }
  
  return mockData[processId] || {
    equipmentShortages: [],
    personnelOverloads: []
  }
}

/**
 * 按流程汇总动态风险统计
 */
export function summarizeDynamicRisksByProcess(): Array<{
  processId: string
  processName: string
  equipmentShortageCount: number
  personnelOverloadCount: number
  totalRiskCount: number
}> {
  const processes = ['P001', 'P002', 'T001', 'T002', 'S001', 'S002', 'W001', 'W002']
  
  return processes.map(processId => {
    const risks = getMockDataForProcess(processId)
    const equipmentShortageCount = risks.equipmentShortages.length
    const personnelOverloadCount = risks.personnelOverloads.length
    
    return {
      processId,
      processName: getProcessName(processId),
      equipmentShortageCount,
      personnelOverloadCount,
      totalRiskCount: equipmentShortageCount + personnelOverloadCount
    }
  }).filter(p => p.totalRiskCount > 0)
    .sort((a, b) => b.totalRiskCount - a.totalRiskCount)
}

function getProcessName(processId: string): string {
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
  return processMap[processId] ? `${processId} - ${processMap[processId]}` : processId
}


