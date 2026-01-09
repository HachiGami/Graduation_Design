from fastapi import APIRouter, Query, Depends
from typing import Optional, List
from pydantic import BaseModel
from ..database import get_database, get_neo4j_driver
from ..services.scheduler_service import SchedulerService

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
    获取动态风险数据（基于真实调度计算）
    """
    try:
        db = get_database()
        neo4j_driver = get_neo4j_driver()
        
        if not db or not neo4j_driver:
            # 数据库未连接，返回空结果
            return DynamicRisksResponse(
                equipment_shortages=[],
                personnel_overloads=[]
            )
        
        # 使用调度服务计算真实风险
        scheduler = SchedulerService(db, neo4j_driver)
        result = await scheduler.calculate_schedule(process_id)
        
        # 转换为响应模型
        equipment_shortages = [
            DynamicRiskEvent(**event) for event in result.get("equipment_shortages", [])
        ]
        personnel_overloads = [
            DynamicRiskEvent(**event) for event in result.get("personnel_overloads", [])
        ]
        
        return DynamicRisksResponse(
            equipment_shortages=equipment_shortages,
            personnel_overloads=personnel_overloads
        )
        
    except Exception as e:
        print(f"Error in get_dynamic_risks: {e}")
        # 发生错误时返回空结果
        return DynamicRisksResponse(
            equipment_shortages=[],
            personnel_overloads=[]
        )
