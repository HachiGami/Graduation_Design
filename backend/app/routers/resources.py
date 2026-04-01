from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional
from datetime import datetime
from ..database import get_database, get_neo4j_driver
from ..schemas.resource import ResourceCreate, ResourceUpdate, ResourceResponse
from bson import ObjectId

router = APIRouter(prefix="/api/resources", tags=["资源管理"])

# 旧种子数据的 resource_type 值 → 新 type 字段映射
_LEGACY_TYPE_MAP = {
    "Equipment": "设备",
    "RawMaterial": "原料",
    "Material": "原料",
    "equipment": "设备",
    "raw_material": "原料",
    "material": "原料",
}


def _normalize_resource_for_response(resource: dict) -> dict:
    """将旧格式文档归一化为 ResourceResponse 所需字段（向后兼容）。"""
    now = datetime.utcnow()

    # type 字段：兼容旧 resource_type 字段
    if not resource.get("type"):
        old_type = resource.get("resource_type", "")
        resource["type"] = _LEGACY_TYPE_MAP.get(old_type, old_type or "未知")

    # quantity：兼容旧 inventory_level 字段
    if resource.get("quantity") is None:
        resource["quantity"] = float(resource.get("inventory_level", 0) or 0)

    # unit：设备类型旧数据可能缺失
    resource.setdefault("unit", "")

    # supplier：旧数据可能是 {name, contact} 嵌套对象
    supplier = resource.get("supplier")
    if isinstance(supplier, dict):
        resource["supplier"] = supplier.get("name", "")
    elif not isinstance(supplier, str):
        resource["supplier"] = ""

    # specification：旧数据可能是 specifications: {capacity, power, brand} 嵌套对象
    if not resource.get("specification"):
        specs = resource.get("specifications", {})
        if isinstance(specs, dict):
            parts = [str(v) for k, v in specs.items() if v and k in ("brand", "capacity")]
            resource["specification"] = " / ".join(parts) if parts else ""
        elif isinstance(specs, str):
            resource["specification"] = specs
        else:
            resource["specification"] = ""

    resource.setdefault("status", "available")
    resource.setdefault("version", 1)
    resource.setdefault("is_active", True)
    resource.setdefault("manufacturer", None)
    resource.setdefault("production_date", None)
    resource.setdefault("upcoming_maintenance", [])
    resource.setdefault("serving_activities_details", [])
    resource.setdefault("serving_processes", [])
    resource.setdefault("created_at", resource.get("updated_at") or now)
    resource.setdefault("updated_at", resource.get("created_at") or now)
    return resource


def _parse_working_hours(working_hours) -> float:
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


async def _enrich_with_neo4j(resources: list, db, driver) -> None:
    """
    从 Neo4j 动态拉取每个实体关联的活动关系，并结合 MongoDB activities 获取工作时间和 process_id，
    将 serving_activities_details 和 serving_processes 注入到每个 resource dict 中（原地修改）。
    """
    names = [r.get("name") for r in resources if r.get("name")]
    if not names or not driver:
        for r in resources:
            r.setdefault("serving_activities_details", [])
            r.setdefault("serving_processes", [])
        return

    entity_activities_map: dict = {}

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
            total_hours = _parse_working_hours(working_hours)
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

    for r in resources:
        name = r.get("name", "")
        details = entity_activities_map.get(name, [])
        r["serving_activities_details"] = details
        r["serving_processes"] = list({d["process_id"] for d in details if d["process_id"]})


@router.post("", response_model=ResourceResponse)
async def create_resource(resource: ResourceCreate):
    db = get_database()
    driver = get_neo4j_driver()

    resource_dict = resource.model_dump()
    resource_dict["created_at"] = datetime.utcnow()
    resource_dict["updated_at"] = datetime.utcnow()

    result = await db.resources.insert_one(resource_dict)
    resource_id = str(result.inserted_id)
    resource_dict["_id"] = resource_id

    neo4j_query = """
    MERGE (r:Resource {id: $resource_id})
    SET r.name = $name
    RETURN r
    """
    try:
        async with driver.session() as session:
            await session.run(neo4j_query, {"resource_id": resource_id, "name": resource.name})
    except Exception as e:
        print(f"Neo4j同步失败: {e}")

    resource_dict.setdefault("serving_activities_details", [])
    resource_dict.setdefault("serving_processes", [])
    return resource_dict


@router.get("", response_model=List[ResourceResponse])
async def get_resources(
    type: Optional[str] = Query(None, description="按资源类型筛选"),
):
    db = get_database()
    driver = get_neo4j_driver()

    query_filter = {}
    if type:
        query_filter["type"] = type

    resources = []
    async for resource in db.resources.find(query_filter):
        resource["_id"] = str(resource["_id"])
        _normalize_resource_for_response(resource)
        resources.append(resource)

    await _enrich_with_neo4j(resources, db, driver)
    return resources


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(resource_id: str):
    db = get_database()
    driver = get_neo4j_driver()
    resource = await db.resources.find_one({"_id": ObjectId(resource_id)})
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    resource["_id"] = str(resource["_id"])
    _normalize_resource_for_response(resource)
    await _enrich_with_neo4j([resource], db, driver)
    return resource


@router.put("/{resource_id}", response_model=ResourceResponse)
async def update_resource(resource_id: str, resource: ResourceUpdate):
    db = get_database()
    driver = get_neo4j_driver()

    update_data = {k: v for k, v in resource.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()

    if "quantity" in update_data and float(update_data["quantity"]) < 0:
        raise HTTPException(status_code=400, detail="库存余额不足")

    result = await db.resources.update_one(
        {"_id": ObjectId(resource_id)},
        {"$set": update_data},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="资源不存在")

    updated_resource = await db.resources.find_one({"_id": ObjectId(resource_id)})
    updated_resource["_id"] = str(updated_resource["_id"])
    _normalize_resource_for_response(updated_resource)

    if resource.name:
        neo4j_query = """
        MATCH (r:Resource {id: $resource_id})
        SET r.name = COALESCE($name, r.name)
        RETURN r
        """
        try:
            async with driver.session() as session:
                await session.run(neo4j_query, {"resource_id": resource_id, "name": resource.name})
        except Exception as e:
            print(f"Neo4j同步失败: {e}")

    await _enrich_with_neo4j([updated_resource], db, driver)
    return updated_resource


@router.patch("/{resource_id}/stock", response_model=ResourceResponse)
async def update_resource_stock(resource_id: str, change_amount: float = Body(..., embed=True)):
    db = get_database()
    driver = get_neo4j_driver()

    resource = await db.resources.find_one({"_id": ObjectId(resource_id)})
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")

    current_quantity = float(resource.get("quantity", 0) or 0)
    new_quantity = current_quantity + float(change_amount)
    if new_quantity < 0:
        raise HTTPException(status_code=400, detail="库存余额不足")

    await db.resources.update_one(
        {"_id": ObjectId(resource_id)},
        {"$set": {"quantity": new_quantity, "updated_at": datetime.utcnow()}},
    )

    updated_resource = await db.resources.find_one({"_id": ObjectId(resource_id)})
    updated_resource["_id"] = str(updated_resource["_id"])
    _normalize_resource_for_response(updated_resource)
    await _enrich_with_neo4j([updated_resource], db, driver)
    return updated_resource


@router.delete("/{resource_id}")
async def delete_resource(resource_id: str):
    db = get_database()
    driver = get_neo4j_driver()

    result = await db.resources.delete_one({"_id": ObjectId(resource_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="资源不存在")

    neo4j_query = """
    MATCH (r:Resource {id: $resource_id})
    DETACH DELETE r
    """
    try:
        async with driver.session() as session:
            await session.run(neo4j_query, {"resource_id": resource_id})
    except Exception as e:
        print(f"Neo4j同步失败: {e}")

    return {"message": "删除成功"}
