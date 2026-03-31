from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional
from datetime import datetime
from ..database import get_database, get_neo4j_driver
from ..schemas.material import MaterialResponse, MaterialAddStock, MaterialUpdate
from bson import ObjectId

router = APIRouter(prefix="/api/materials", tags=["原料管理"])


def parse_working_hours(working_hours) -> float:
    total_hours = 0.0
    if not working_hours:
        return total_hours

    if isinstance(working_hours, list):
        for period in working_hours:
            if isinstance(period, dict):
                start = period.get("start_time")
                end = period.get("end_time")
                if start and end:
                    try:
                        fmt = "%H:%M"
                        td = datetime.strptime(end, fmt) - datetime.strptime(start, fmt)
                        total_hours += td.total_seconds() / 3600
                    except Exception:
                        pass
    elif isinstance(working_hours, str):
        for period in working_hours.split(","):
            parts = period.strip().split("-")
            if len(parts) == 2:
                try:
                    fmt = "%H:%M"
                    td = datetime.strptime(parts[1].strip(), fmt) - datetime.strptime(parts[0].strip(), fmt)
                    total_hours += td.total_seconds() / 3600
                except Exception:
                    pass
    return total_hours


@router.get("", response_model=List[MaterialResponse])
async def get_materials():
    db = get_database()
    driver = get_neo4j_driver()

    # 1. 从 MongoDB 获取所有原料
    materials = []
    names = []
    async for mat in db.resources.find({"type": "原料"}):
        mat["_id"] = str(mat["_id"])
        materials.append(mat)
        if mat.get("name"):
            names.append(mat["name"])

    # 2. 从 Neo4j 动态查询关联活动（按实体名称匹配）
    entity_activities_map: dict = {}

    if names and driver:
        try:
            async with driver.session() as session:
                result = await session.run(
                    """
                    MATCH (a:Activity)-[r]-(e)
                    WHERE e.name IN $names
                    RETURN e.name AS entity_name,
                           a.name AS activity_name,
                           r.hourly_consumption AS hourly_consumption
                    """,
                    {"names": names},
                )
                neo4j_records = await result.data()

            activity_names = list({rec["activity_name"] for rec in neo4j_records if rec.get("activity_name")})

            activities_mongo_map: dict = {}
            if activity_names:
                async for act in db.activities.find({"name": {"$in": activity_names}}):
                    activities_mongo_map[act["name"]] = {
                        "process_id": act.get("process_id", ""),
                        "working_hours": act.get("working_hours", []),
                    }

            for rec in neo4j_records:
                entity_name = rec.get("entity_name")
                activity_name = rec.get("activity_name")
                if not entity_name or not activity_name:
                    continue

                act_info = activities_mongo_map.get(activity_name, {})
                process_id = act_info.get("process_id", "")
                working_hours = act_info.get("working_hours", [])
                hourly_consumption = float(rec.get("hourly_consumption") or 0.0)
                total_hours = parse_working_hours(working_hours)
                daily_consumption = round(hourly_consumption * total_hours, 4)

                entity_activities_map.setdefault(entity_name, []).append(
                    {
                        "activity_name": activity_name,
                        "process_id": process_id,
                        "working_hours": working_hours,
                        "hourly_consumption": hourly_consumption,
                        "daily_consumption": daily_consumption,
                    }
                )
        except Exception as e:
            print(f"Neo4j查询失败: {e}")

    # 3. 组装返回数据
    response_data = []
    for mat in materials:
        mat_name = mat.get("name", "")
        details = entity_activities_map.get(mat_name, [])
        serving_processes = list({d["process_id"] for d in details if d["process_id"]})

        total_daily_consumption = round(sum(d["daily_consumption"] for d in details), 4)
        quantity = float(mat.get("quantity", 0))
        remaining_days = round(quantity / total_daily_consumption, 2) if total_daily_consumption > 0 else -1.0

        mat_response = MaterialResponse(
            _id=mat["_id"],
            name=mat.get("name", ""),
            type=mat.get("type", "原料"),
            specification=mat.get("specification"),
            supplier=mat.get("supplier"),
            manufacturer=mat.get("manufacturer"),
            quantity=quantity,
            unit=mat.get("unit", ""),
            status=mat.get("status"),
            daily_consumption=total_daily_consumption,
            remaining_days=remaining_days,
            serving_activities_details=details,
            serving_processes=serving_processes,
        )
        response_data.append(mat_response)

    return response_data


@router.post("/{material_id}/add_stock", response_model=MaterialResponse)
async def add_stock(material_id: str, payload: MaterialAddStock):
    db = get_database()
    obj_id = ObjectId(material_id)

    material = await db.resources.find_one({"_id": obj_id, "type": "原料"})
    if not material:
        raise HTTPException(status_code=404, detail="原料不存在")

    new_quantity = float(material.get("quantity", 0)) + payload.add_amount

    await db.resources.update_one(
        {"_id": obj_id},
        {"$set": {"quantity": new_quantity, "updated_at": datetime.utcnow()}},
    )

    updated_material = await db.resources.find_one({"_id": obj_id})
    updated_material["_id"] = str(updated_material["_id"])

    return MaterialResponse(
        _id=updated_material["_id"],
        name=updated_material.get("name", ""),
        type=updated_material.get("type", "原料"),
        quantity=new_quantity,
        unit=updated_material.get("unit", ""),
        daily_consumption=0.0,
        remaining_days=-1.0,
        serving_activities_details=[],
        serving_processes=[],
    )


@router.put("/{material_id}", response_model=MaterialResponse)
async def update_material(material_id: str, payload: MaterialUpdate):
    db = get_database()
    obj_id = ObjectId(material_id)

    material = await db.resources.find_one({"_id": obj_id, "type": "原料"})
    if not material:
        raise HTTPException(status_code=404, detail="原料不存在")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="没有提供更新数据")

    update_data["updated_at"] = datetime.utcnow()
    await db.resources.update_one({"_id": obj_id}, {"$set": update_data})

    updated_material = await db.resources.find_one({"_id": obj_id})
    updated_material["_id"] = str(updated_material["_id"])

    return MaterialResponse(
        _id=updated_material["_id"],
        name=updated_material.get("name", ""),
        type=updated_material.get("type", "原料"),
        quantity=updated_material.get("quantity", 0),
        unit=updated_material.get("unit", ""),
        daily_consumption=0.0,
        remaining_days=-1.0,
        serving_activities_details=[],
        serving_processes=[],
    )
