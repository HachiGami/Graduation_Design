from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from ..database import get_database, get_neo4j_driver
from ..services.scheduler_service import SchedulerService
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

    risks: List[RiskItem] = []

    if not activities:
        return risks

    async with neo4j_driver.session() as session:
        for activity in activities:
            activity_name = activity.get("name", "未知活动")
            activity_graph_id = activity.get("neo4j_id") or activity["_id"]
            activity_domain = activity.get("domain")
            activity_process_id = activity.get("process_id")

            # 1) 物料断供风险（不足7天）
            daily_hours = _calc_daily_hours(activity.get("working_hours", []))
            for req in activity.get("material_requirements", []):
                material_model = req.get("material_model")
                if not material_model:
                    continue

                hourly_rate = req.get("hourly_consumption_rate")
                if hourly_rate is None:
                    per_day = req.get("consumption_rate_per_day")
                    if per_day is None:
                        hourly_rate = 10.0
                    else:
                        hourly_rate = float(per_day) / max(daily_hours, 1.0)

                daily_consumption = float(hourly_rate) * daily_hours
                if daily_consumption <= 0:
                    continue

                total_quantity = 0.0
                async for material in db.assets.find(
                    {"asset_type": "material", "model": material_model}
                ):
                    total_quantity += float(material.get("quantity") or 0)

                # 兼容按名称匹配的历史数据
                if total_quantity <= 0:
                    async for material in db.assets.find(
                        {"asset_type": "material", "name": material_model}
                    ):
                        total_quantity += float(material.get("quantity") or 0)

                runnable_days = total_quantity / daily_consumption if daily_consumption > 0 else 0.0
                if runnable_days < 7:
                    risks.append(
                        RiskItem(
                            risk_type="material_shortage",
                            level="high",
                            activity_name=activity_name,
                            message=f"【警告】活动[{activity_name}]的原料[{material_model}]仅够运行 {runnable_days:.1f} 天！",
                            domain=activity_domain,
                            process_id=activity_process_id,
                            runnable_days=round(runnable_days, 2),
                        )
                    )

            # 查询活动已分配的人员（兼容 ASSIGNED_TO 与 ASSIGNS）
            assigned_personnel_result_1 = await session.run(
                """
                MATCH (a:Activity {id: $activity_id})
                MATCH (p:Personnel)-[:ASSIGNED_TO]->(a)
                RETURN DISTINCT p.id AS id, p.name AS name, p.role AS role, p.upcoming_leaves AS upcoming_leaves
                """,
                {"activity_id": activity_graph_id},
            )
            assigned_personnel_result_2 = await session.run(
                """
                MATCH (a:Activity {id: $activity_id})-[:ASSIGNS]->(p:Personnel)
                RETURN DISTINCT p.id AS id, p.name AS name, p.role AS role, p.upcoming_leaves AS upcoming_leaves
                """,
                {"activity_id": activity_graph_id},
            )
            assigned_personnel = []
            seen_personnel_ids = set()
            for result_cursor in [assigned_personnel_result_1, assigned_personnel_result_2]:
                async for record in result_cursor:
                    pid = record.get("id")
                    if not pid or pid in seen_personnel_ids:
                        continue
                    seen_personnel_ids.add(pid)
                    assigned_personnel.append(
                        {
                            "id": pid,
                            "name": record.get("name") or "未知人员",
                            "role": record.get("role") or "未知角色",
                            "upcoming_leaves": record.get("upcoming_leaves") or [],
                        }
                    )

            # 查询活动已分配的设备（兼容 USED_BY 与 OCCUPIES）
            assigned_equipment_result_1 = await session.run(
                """
                MATCH (a:Activity {id: $activity_id})
                MATCH (e:Equipment)-[:USED_BY]->(a)
                RETURN DISTINCT e.id AS id, e.name AS name, e.model AS model, e.upcoming_maintenance AS upcoming_maintenance
                """,
                {"activity_id": activity_graph_id},
            )
            assigned_equipment_result_2 = await session.run(
                """
                MATCH (a:Activity {id: $activity_id})-[:OCCUPIES]->(e:Equipment)
                RETURN DISTINCT e.id AS id, e.name AS name, e.model AS model, e.upcoming_maintenance AS upcoming_maintenance
                """,
                {"activity_id": activity_graph_id},
            )
            assigned_equipment = []
            seen_equipment_ids = set()
            for result_cursor in [assigned_equipment_result_1, assigned_equipment_result_2]:
                async for record in result_cursor:
                    eid = record.get("id")
                    if not eid or eid in seen_equipment_ids:
                        continue
                    seen_equipment_ids.add(eid)
                    assigned_equipment.append(
                        {
                            "id": eid,
                            "name": record.get("name") or "未知设备",
                            "model": record.get("model") or "未知型号",
                            "upcoming_maintenance": record.get("upcoming_maintenance") or [],
                        }
                    )

            # 2) 资源分配不满足风险（供不应求）
            personnel_count_by_role: Dict[str, int] = {}
            for p in assigned_personnel:
                role = p.get("role") or "未知角色"
                personnel_count_by_role[role] = personnel_count_by_role.get(role, 0) + 1

            equipment_count_by_model: Dict[str, int] = {}
            for e in assigned_equipment:
                model = e.get("model") or "未知型号"
                equipment_count_by_model[model] = equipment_count_by_model.get(model, 0) + 1

            for req in activity.get("personnel_requirements", []):
                required_role = req.get("role")
                required_count = int(req.get("count", 0))
                if not required_role or required_count <= 0:
                    continue
                allocated_count = personnel_count_by_role.get(required_role, 0)
                if allocated_count < required_count:
                    risks.append(
                        RiskItem(
                            risk_type="allocation_shortage",
                            level="high",
                            activity_name=activity_name,
                            message=f"【警告】活动[{activity_name}]需要 {required_count} 名{required_role}，当前仅分配 {allocated_count} 名！",
                            domain=activity_domain,
                            process_id=activity_process_id,
                        )
                    )

            for req in activity.get("equipment_requirements", []):
                required_model = req.get("equipment_model")
                required_count = int(req.get("count", 0))
                if not required_model or required_count <= 0:
                    continue
                allocated_count = equipment_count_by_model.get(required_model, 0)
                if allocated_count < required_count:
                    risks.append(
                        RiskItem(
                            risk_type="allocation_shortage",
                            level="high",
                            activity_name=activity_name,
                            message=f"【警告】活动[{activity_name}]需要 {required_count} 台[{required_model}]，当前仅分配 {allocated_count} 台！",
                            domain=activity_domain,
                            process_id=activity_process_id,
                        )
                    )

            # 3) 突发缺勤/检修风险（未来7天）
            for p in assigned_personnel:
                leave_days = p.get("upcoming_leaves", [])
                if leave_days:
                    risks.append(
                        RiskItem(
                            risk_type="upcoming_absence",
                            level="medium",
                            activity_name=activity_name,
                            message=f"【风险】分配给活动[{activity_name}]的{p['name']}将在[{', '.join(leave_days)}]请假，请重新调配！",
                            domain=activity_domain,
                            process_id=activity_process_id,
                        )
                    )

            for e in assigned_equipment:
                maintenance_days = e.get("upcoming_maintenance", [])
                if maintenance_days:
                    risks.append(
                        RiskItem(
                            risk_type="upcoming_absence",
                            level="medium",
                            activity_name=activity_name,
                            message=f"【风险】分配给活动[{activity_name}]的设备[{e['name']}]将在[{', '.join(maintenance_days)}]检修，请提前切换备用设备！",
                            domain=activity_domain,
                            process_id=activity_process_id,
                        )
                    )

    return risks
