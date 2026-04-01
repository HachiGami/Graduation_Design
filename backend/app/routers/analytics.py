from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from ..database import get_database, get_neo4j_driver
from ..services.scheduler_service import SchedulerService
from ..services.risk_service import calculate_activity_risks
from ..schemas.risk import RiskItem

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _parse_time_to_minutes(value: str) -> int:
    parts = value.split(":")
    if len(parts) != 2:
        return 0
    hour = int(parts[0])
    minute = int(parts[1])
    return hour * 60 + minute


def _calc_daily_hours(working_hours: List[Dict[str, str]]) -> float:
    if not working_hours:
        return 8.0

    total_minutes = 0
    for window in working_hours:
        try:
            start = _parse_time_to_minutes(window.get("start_time", "08:00"))
            end = _parse_time_to_minutes(window.get("end_time", "08:00"))
            if end > start:
                total_minutes += end - start
        except Exception:
            continue

    if total_minutes <= 0:
        return 8.0
    return total_minutes / 60.0

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


@router.get("/risks", response_model=List[RiskItem])
async def get_7day_risks(
    domain: Optional[str] = Query(None, description="流程域过滤，如：处理")
):
    db = get_database()
    neo4j_driver = get_neo4j_driver()

    query_filter: Dict[str, Any] = {}
    if domain:
        query_filter["domain"] = domain

    activities = []
    async for activity in db.activities.find(query_filter):
        activity["_id"] = str(activity["_id"])
        activities.append(activity)

    if not activities:
        return []

    risks_by_activity = await calculate_activity_risks(db, neo4j_driver, activities)
    results: List[RiskItem] = []
    for activity in activities:
        activity_name = activity.get("name", "未知活动")
        activity_domain = activity.get("domain")
        activity_process_id = activity.get("process_id")
        activity_id = str(activity.get("_id"))
        for message in risks_by_activity.get(activity_id, []):
            if "库存不足7天" in message:
                risk_type = "material_shortage"
                level = "high"
            elif "请假风险" in message or "检修风险" in message:
                risk_type = "upcoming_absence"
                level = "medium"
            else:
                risk_type = "allocation_shortage"
                level = "high"
            results.append(
                RiskItem(
                    risk_type=risk_type,
                    level=level,
                    activity_name=activity_name,
                    message=message,
                    domain=activity_domain,
                    process_id=activity_process_id,
                    runnable_days=None,
                )
            )

    return results
