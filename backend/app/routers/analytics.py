from fastapi import APIRouter, Query
from typing import Optional, List
from pydantic import BaseModel

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

class DynamicRiskEvent(BaseModel):
    type: str
    time_window: str
    gap: float
    activity_ids: List[str]
    description: str

class DynamicRisksResponse(BaseModel):
    equipment_shortages: List[DynamicRiskEvent]
    personnel_overloads: List[DynamicRiskEvent]

@router.get("/dynamic-risks", response_model=DynamicRisksResponse)
async def get_dynamic_risks(
    process_id: Optional[str] = Query(None, description="流程ID")
):
    """
    获取动态风险数据（当前返回mock数据）
    """
    if process_id:
        return get_mock_data_for_process(process_id)
    
    return DynamicRisksResponse(
        equipment_shortages=[
            DynamicRiskEvent(
                type="equipment_shortage",
                time_window="T1-T5",
                gap=2.0,
                activity_ids=["mock-act-1", "mock-act-2"],
                description="生产设备并发需求超过容量2台"
            ),
            DynamicRiskEvent(
                type="equipment_shortage",
                time_window="T8-T12",
                gap=1.0,
                activity_ids=["mock-act-3"],
                description="包装设备峰值不足1台"
            )
        ],
        personnel_overloads=[
            DynamicRiskEvent(
                type="personnel_overload",
                time_window="T3-T7",
                gap=1.5,
                activity_ids=["mock-act-4", "mock-act-5"],
                description="操作人员超载1.5倍"
            )
        ]
    )

def get_mock_data_for_process(process_id: str) -> DynamicRisksResponse:
    """按流程返回mock数据"""
    mock_data = {
        "P001": DynamicRisksResponse(
            equipment_shortages=[
                DynamicRiskEvent(
                    type="equipment_shortage",
                    time_window="T2-T4",
                    gap=1.0,
                    activity_ids=["mock-p001-1"],
                    description="P001生产线设备不足1台"
                )
            ],
            personnel_overloads=[
                DynamicRiskEvent(
                    type="personnel_overload",
                    time_window="T1-T3",
                    gap=0.8,
                    activity_ids=["mock-p001-2"],
                    description="P001人员超载0.8倍"
                )
            ]
        ),
        "T001": DynamicRisksResponse(
            equipment_shortages=[
                DynamicRiskEvent(
                    type="equipment_shortage",
                    time_window="T5-T8",
                    gap=2.0,
                    activity_ids=["mock-t001-1"],
                    description="T001运输车辆不足2辆"
                )
            ],
            personnel_overloads=[]
        ),
        "S001": DynamicRisksResponse(
            equipment_shortages=[],
            personnel_overloads=[
                DynamicRiskEvent(
                    type="personnel_overload",
                    time_window="T10-T15",
                    gap=1.2,
                    activity_ids=["mock-s001-1", "mock-s001-2"],
                    description="S001销售人员超载1.2倍"
                )
            ]
        )
    }
    
    return mock_data.get(process_id, DynamicRisksResponse(
        equipment_shortages=[],
        personnel_overloads=[]
    ))

