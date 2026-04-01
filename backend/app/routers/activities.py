from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from ..database import get_database, get_neo4j_driver
from ..schemas.activity import ActivityCreate, ActivityUpdate, ActivityResponse
from bson import ObjectId
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/activities", tags=["生产活动"])


class PersonnelRequirementPayload(BaseModel):
    role: str = Field(..., min_length=1, description="角色")
    count: int = Field(..., ge=1, description="需要人数")


class EquipmentRequirementPayload(BaseModel):
    equipment_model: str = Field(..., min_length=1, description="设备型号")
    count: int = Field(..., ge=1, description="需要数量")


class MaterialRequirementPayload(BaseModel):
    material_model: str = Field(..., min_length=1, description="原料型号")
    hourly_consumption_rate: float = Field(..., ge=0, description="每小时消耗")
    unit: Optional[str] = Field(default="", description="单位")


class ConsumedResourcePayload(BaseModel):
    resource_id: str = Field(..., min_length=1, description="原料资源ID")
    rate: float = Field(default=0.0, ge=0, description="消耗速率（单位/小时）")


class ActivityResourcesPayload(BaseModel):
    personnel_roles: List[str] = Field(default=[], description="职位需求列表（可重复）")
    equipment_types: List[str] = Field(default=[], description="设备种类需求列表（可重复）")
    assigned_personnel_ids: List[str] = Field(default=[], description="实际分配的人员ID列表")
    assigned_equipment_ids: List[str] = Field(default=[], description="实际分配的设备ID列表")
    consumed_resources: List[ConsumedResourcePayload] = Field(default=[], description="消耗原料及速率")


def _normalize_sop_steps(raw_steps):
    if not raw_steps:
        return []
    normalized = []
    for index, step in enumerate(raw_steps):
        if isinstance(step, dict):
            # 兼容旧格式 {step_number, description} 和新格式 {content}
            content = step.get("content") or step.get("description", "")
            normalized.append({
                "content": str(content),
                "duration": int(step.get("duration", 0)),
            })
        else:
            normalized.append({
                "content": str(step),
                "duration": 0,
            })
    return normalized


def _normalize_activity_for_response(activity: dict) -> dict:
    now = datetime.utcnow()
    activity.setdefault("name", "未命名活动")
    activity.setdefault("description", "")
    activity.setdefault("activity_type", "production")
    activity["sop_steps"] = _normalize_sop_steps(activity.get("sop_steps", []))
    activity.setdefault("estimated_duration", 0)
    activity.setdefault("duration_minutes", None)
    activity.setdefault("deadline", None)
    activity.setdefault("required_resources", [])
    activity.setdefault("required_personnel", [])
    activity.setdefault("status", "pending")
    activity.setdefault("domain", "production")
    activity.setdefault("process_id", "P001")
    activity.setdefault("version", 1)
    activity.setdefault("is_active", True)
    activity.setdefault(
        "working_hours",
        [
            {"start_time": "08:00", "end_time": "11:00"},
            {"start_time": "13:00", "end_time": "18:00"},
        ],
    )
    activity.setdefault("material_requirements", [])
    activity.setdefault("personnel_requirements", [])
    activity.setdefault("equipment_requirements", [])
    activity.setdefault("personnel_roles_required", [])
    activity.setdefault("equipment_types_required", [])
    activity.setdefault("created_at", activity.get("updated_at") or now)
    activity.setdefault("updated_at", activity.get("created_at") or now)
    return activity


def _parse_activity_object_id(activity_id: str) -> ObjectId:
    if not ObjectId.is_valid(activity_id):
        raise HTTPException(status_code=400, detail="无效的活动ID")
    return ObjectId(activity_id)

@router.post("", response_model=ActivityResponse)
async def create_activity(activity: ActivityCreate):
    db = get_database()
    driver = get_neo4j_driver()
    
    activity_dict = activity.model_dump()
    activity_dict["created_at"] = datetime.utcnow()
    activity_dict["updated_at"] = datetime.utcnow()
    
    result = await db.activities.insert_one(activity_dict)
    activity_id = str(result.inserted_id)
    activity_dict["_id"] = activity_id
    
    # 同步到Neo4j：只存activity_id和name
    neo4j_query = """
    MERGE (a:Activity {id: $activity_id})
    SET a.name = $name, a.domain = $domain, a.process_id = $process_id
    RETURN a
    """
    try:
        async with driver.session() as session:
            await session.run(neo4j_query, {
                "activity_id": activity_id,
                "name": activity.name,
                "domain": activity.domain,
                "process_id": activity.process_id
            })
    except Exception as e:
        print(f"Neo4j同步失败: {e}")
    
    return activity_dict

@router.get("", response_model=List[ActivityResponse])
async def get_activities(
    domain: str = Query(..., description="流程域（必填）"),
    process_id: Optional[str] = Query(None, description="流程实例ID")
):
    db = get_database()
    query_filter = {"domain": domain}
    if process_id:
        query_filter["process_id"] = process_id
    
    activities = []
    async for activity in db.activities.find(query_filter):
        activity["_id"] = str(activity["_id"])
        activities.append(_normalize_activity_for_response(activity))
    return activities


@router.get("/occupied-resources", response_model=List[str])
async def get_occupied_resources():
    """获取所有已被活动占用的资源ID（MongoDB ObjectId字符串）"""
    driver = get_neo4j_driver()

    occupied_ids: List[str] = []
    try:
        async with driver.session() as session:
            # 兼容历史关系方向：资源->活动 及 活动->资源
            result = await session.run(
                """
                MATCH (n)-[:ASSIGNED_TO|ASSIGNS|USES]->(:Activity)
                RETURN collect(distinct n.id) AS occupiedIds
                """
            )
            record = await result.single()
            if record and record.get("occupiedIds"):
                occupied_ids.extend([rid for rid in record["occupiedIds"] if isinstance(rid, str) and rid])

            result = await session.run(
                """
                MATCH (:Activity)-[:ASSIGNED_TO|ASSIGNS|USES]->(n)
                RETURN collect(distinct n.id) AS occupiedIds
                """
            )
            record = await result.single()
            if record and record.get("occupiedIds"):
                occupied_ids.extend([rid for rid in record["occupiedIds"] if isinstance(rid, str) and rid])
    except Exception as e:
        print(f"Neo4j查询失败: {e}")
        raise HTTPException(status_code=500, detail="查询已占用资源失败")

    return list(set(occupied_ids))


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(activity_id: str):
    db = get_database()
    activity = await db.activities.find_one({"_id": ObjectId(activity_id)})
    if not activity:
        raise HTTPException(status_code=404, detail="生产活动不存在")
    activity["_id"] = str(activity["_id"])
    return _normalize_activity_for_response(activity)

@router.get("/{activity_id}/details")
async def get_activity_details(activity_id: str):
    """获取活动详情（包含需求定义和实际分配）"""
    db = get_database()
    driver = get_neo4j_driver()
    
    # 步骤1: 从MongoDB获取活动基本信息和需求定义
    activity = await db.activities.find_one({"_id": ObjectId(activity_id)})
    if not activity:
        raise HTTPException(status_code=404, detail="生产活动不存在")
    
    activity["_id"] = str(activity["_id"])
    
    # 步骤2: 从Neo4j查询实际分配情况
    try:
        async with driver.session() as session:
            # 查询原料消耗
            result = await session.run("""
                MATCH (a:Activity {id: $activity_id})-[c:CONSUMES]->(m:Material)
                RETURN m.id as asset_id, m.name as name, 
                       c.consumption_rate_per_day as allocated_rate, 
                       c.unit as unit
            """, {"activity_id": activity_id})
            
            materials = []
            async for record in result:
                materials.append({
                    "asset_id": record["asset_id"],
                    "name": record["name"],
                    "allocated_rate": record["allocated_rate"],
                    "unit": record["unit"]
                })
            
            # 查询人员分配
            result = await session.run("""
                MATCH (a:Activity {id: $activity_id})-[as:ASSIGNS]->(p:Personnel)
                RETURN p.id as id, p.name as name, as.role as role
            """, {"activity_id": activity_id})
            
            personnel = []
            async for record in result:
                personnel.append({
                    "id": record["id"],
                    "name": record["name"],
                    "role": record["role"]
                })
            
            # 查询设备占用
            result = await session.run("""
                MATCH (a:Activity {id: $activity_id})-[o:OCCUPIES]->(e:Equipment)
                RETURN e.id as asset_id, e.name as name, e.model as model
            """, {"activity_id": activity_id})
            
            equipment = []
            async for record in result:
                equipment.append({
                    "asset_id": record["asset_id"],
                    "name": record["name"],
                    "model": record["model"]
                })
    except Exception as e:
        print(f"Neo4j查询失败: {e}")
        materials = []
        personnel = []
        equipment = []
    
    # 构建返回结果
    result = {
        # MongoDB 静态数据（需求定义）
        "id": activity["_id"],
        "name": activity.get("name"),
        "description": activity.get("description"),
        "status": activity.get("status"),
        "process_id": activity.get("process_id"),
        "domain": activity.get("domain"),
        "estimated_duration": activity.get("estimated_duration"),
        "material_requirements": activity.get("material_requirements", []),
        "personnel_requirements": activity.get("personnel_requirements", []),
        "equipment_requirements": activity.get("equipment_requirements", []),
        
        # Neo4j 实况数据（实际分配）
        "actual_allocations": {
            "materials": materials,
            "personnel": personnel,
            "equipment": equipment
        }
    }
    
    return result


@router.post("/{activity_id}/personnel", response_model=ActivityResponse)
async def add_personnel_requirement(activity_id: str, payload: PersonnelRequirementPayload):
    db = get_database()
    obj_id = _parse_activity_object_id(activity_id)
    activity = await db.activities.find_one({"_id": obj_id})
    if not activity:
        raise HTTPException(status_code=404, detail="生产活动不存在")

    requirements = activity.get("personnel_requirements", [])
    updated = False
    for req in requirements:
        if req.get("role") == payload.role:
            req["count"] = payload.count
            updated = True
            break
    if not updated:
        requirements.append({"role": payload.role, "count": payload.count})

    await db.activities.update_one(
        {"_id": obj_id},
        {"$set": {"personnel_requirements": requirements, "updated_at": datetime.utcnow()}},
    )
    latest = await db.activities.find_one({"_id": obj_id})
    latest["_id"] = str(latest["_id"])
    return _normalize_activity_for_response(latest)


@router.delete("/{activity_id}/personnel/{role}", response_model=ActivityResponse)
async def remove_personnel_requirement(activity_id: str, role: str):
    db = get_database()
    obj_id = _parse_activity_object_id(activity_id)
    activity = await db.activities.find_one({"_id": obj_id})
    if not activity:
        raise HTTPException(status_code=404, detail="生产活动不存在")

    requirements = activity.get("personnel_requirements", [])
    new_requirements = [req for req in requirements if req.get("role") != role]
    if len(new_requirements) == len(requirements):
        raise HTTPException(status_code=404, detail="人员需求不存在")

    await db.activities.update_one(
        {"_id": obj_id},
        {"$set": {"personnel_requirements": new_requirements, "updated_at": datetime.utcnow()}},
    )
    latest = await db.activities.find_one({"_id": obj_id})
    latest["_id"] = str(latest["_id"])
    return _normalize_activity_for_response(latest)


@router.post("/{activity_id}/equipment", response_model=ActivityResponse)
async def add_equipment_requirement(activity_id: str, payload: EquipmentRequirementPayload):
    db = get_database()
    obj_id = _parse_activity_object_id(activity_id)
    activity = await db.activities.find_one({"_id": obj_id})
    if not activity:
        raise HTTPException(status_code=404, detail="生产活动不存在")

    requirements = activity.get("equipment_requirements", [])
    updated = False
    for req in requirements:
        if req.get("equipment_model") == payload.equipment_model:
            req["count"] = payload.count
            updated = True
            break
    if not updated:
        requirements.append({"equipment_model": payload.equipment_model, "count": payload.count})

    await db.activities.update_one(
        {"_id": obj_id},
        {"$set": {"equipment_requirements": requirements, "updated_at": datetime.utcnow()}},
    )
    latest = await db.activities.find_one({"_id": obj_id})
    latest["_id"] = str(latest["_id"])
    return _normalize_activity_for_response(latest)


@router.delete("/{activity_id}/equipment/{model}", response_model=ActivityResponse)
async def remove_equipment_requirement(activity_id: str, model: str):
    db = get_database()
    obj_id = _parse_activity_object_id(activity_id)
    activity = await db.activities.find_one({"_id": obj_id})
    if not activity:
        raise HTTPException(status_code=404, detail="生产活动不存在")

    requirements = activity.get("equipment_requirements", [])
    new_requirements = [req for req in requirements if req.get("equipment_model") != model]
    if len(new_requirements) == len(requirements):
        raise HTTPException(status_code=404, detail="设备需求不存在")

    await db.activities.update_one(
        {"_id": obj_id},
        {"$set": {"equipment_requirements": new_requirements, "updated_at": datetime.utcnow()}},
    )
    latest = await db.activities.find_one({"_id": obj_id})
    latest["_id"] = str(latest["_id"])
    return _normalize_activity_for_response(latest)


@router.post("/{activity_id}/materials", response_model=ActivityResponse)
async def add_material_requirement(activity_id: str, payload: MaterialRequirementPayload):
    db = get_database()
    obj_id = _parse_activity_object_id(activity_id)
    activity = await db.activities.find_one({"_id": obj_id})
    if not activity:
        raise HTTPException(status_code=404, detail="生产活动不存在")

    requirements = activity.get("material_requirements", [])
    updated = False
    for req in requirements:
        if req.get("material_model") == payload.material_model:
            req["hourly_consumption_rate"] = payload.hourly_consumption_rate
            if payload.unit is not None:
                req["unit"] = payload.unit
            updated = True
            break
    if not updated:
        requirements.append(
            {
                "material_model": payload.material_model,
                "hourly_consumption_rate": payload.hourly_consumption_rate,
                "unit": payload.unit or "",
            }
        )

    await db.activities.update_one(
        {"_id": obj_id},
        {"$set": {"material_requirements": requirements, "updated_at": datetime.utcnow()}},
    )
    latest = await db.activities.find_one({"_id": obj_id})
    latest["_id"] = str(latest["_id"])
    return _normalize_activity_for_response(latest)


@router.delete("/{activity_id}/materials/{material_model}", response_model=ActivityResponse)
async def remove_material_requirement(activity_id: str, material_model: str):
    db = get_database()
    obj_id = _parse_activity_object_id(activity_id)
    activity = await db.activities.find_one({"_id": obj_id})
    if not activity:
        raise HTTPException(status_code=404, detail="生产活动不存在")

    requirements = activity.get("material_requirements", [])
    new_requirements = [req for req in requirements if req.get("material_model") != material_model]
    if len(new_requirements) == len(requirements):
        raise HTTPException(status_code=404, detail="原料需求不存在")

    await db.activities.update_one(
        {"_id": obj_id},
        {"$set": {"material_requirements": new_requirements, "updated_at": datetime.utcnow()}},
    )
    latest = await db.activities.find_one({"_id": obj_id})
    latest["_id"] = str(latest["_id"])
    return _normalize_activity_for_response(latest)

@router.put("/{activity_id}", response_model=ActivityResponse)
async def update_activity(activity_id: str, activity: ActivityUpdate):
    db = get_database()
    driver = get_neo4j_driver()
    
    update_data = {k: v for k, v in activity.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.activities.update_one(
        {"_id": ObjectId(activity_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="生产活动不存在")
    
    updated_activity = await db.activities.find_one({"_id": ObjectId(activity_id)})
    updated_activity["_id"] = str(updated_activity["_id"])
    
    # 同步到Neo4j：如果name更新了，同步更新
    if activity.name or activity.domain or activity.process_id:
        neo4j_query = """
        MATCH (a:Activity {id: $activity_id})
        SET a.name = COALESCE($name, a.name),
            a.domain = COALESCE($domain, a.domain),
            a.process_id = COALESCE($process_id, a.process_id)
        RETURN a
        """
        try:
            async with driver.session() as session:
                await session.run(neo4j_query, {
                    "activity_id": activity_id,
                    "name": activity.name,
                    "domain": activity.domain,
                    "process_id": activity.process_id
                })
        except Exception as e:
            print(f"Neo4j同步失败: {e}")
    
    return updated_activity

@router.delete("/{activity_id}")
async def delete_activity(activity_id: str):
    db = get_database()
    driver = get_neo4j_driver()
    
    result = await db.activities.delete_one({"_id": ObjectId(activity_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="生产活动不存在")
    
    # 同步到Neo4j：删除节点及其所有关系
    neo4j_query = """
    MATCH (a:Activity {id: $activity_id})
    DETACH DELETE a
    """
    try:
        async with driver.session() as session:
            await session.run(neo4j_query, {"activity_id": activity_id})
    except Exception as e:
        print(f"Neo4j同步失败: {e}")
    
    return {"message": "删除成功"}

@router.post("/batch-status")
async def batch_update_status(
    domain: str = Query(..., description="流程域"),
    process_id: str = Query(..., description="流程实例ID"),
    new_status: str = Query(..., description="新状态")
):
    """批量更新流程所有活动的状态"""
    db = get_database()
    driver = get_neo4j_driver()
    
    # 更新MongoDB中的活动状态
    result = await db.activities.update_many(
        {"domain": domain, "process_id": process_id},
        {"$set": {"status": new_status, "updated_at": datetime.utcnow()}}
    )
    
    # 同步更新Neo4j
    try:
        async with driver.session() as session:
            await session.run("""
                MATCH (a:Activity)
                WHERE a.domain = $domain AND a.process_id = $process_id
                SET a.status = $status
            """, {"domain": domain, "process_id": process_id, "status": new_status})
            
            # 如果状态变为completed，释放所有资产
            if new_status == "completed":
                # 获取所有活动ID
                activities = []
                async for activity in db.activities.find({"domain": domain, "process_id": process_id}):
                    activities.append(str(activity["_id"]))
                
                # 释放所有设备资产
                for activity_id in activities:
                    # 查询占用的设备
                    result = await session.run("""
                        MATCH (a:Activity {id: $activity_id})-[:OCCUPIES]->(e:Equipment)
                        RETURN e.id as asset_id
                    """, {"activity_id": activity_id})
                    
                    equipment_ids = []
                    async for record in result:
                        equipment_ids.append(record["asset_id"])
                    
                    # 更新MongoDB中的设备状态为idle
                    for eq_id in equipment_ids:
                        await db.assets.update_one(
                            {"_id": ObjectId(eq_id)},
                            {"$set": {"status": "idle", "updated_at": datetime.utcnow()}}
                        )
                    
                    # 删除Neo4j关系
                    await session.run("""
                        MATCH (a:Activity {id: $activity_id})-[r]->(asset)
                        WHERE type(r) IN ['OCCUPIES', 'CONSUMES', 'ASSIGNS']
                        DELETE r
                    """, {"activity_id": activity_id})
    except Exception as e:
        print(f"Neo4j同步失败: {e}")
    
    return {
        "message": "批量更新成功",
        "updated_count": result.modified_count
    }


@router.get("/{activity_id}/resources")
async def get_activity_resources(activity_id: str):
    """获取活动的资源分配面板数据（含 MongoDB 需求定义 + Neo4j 实际分配）"""
    db = get_database()
    driver = get_neo4j_driver()

    obj_id = _parse_activity_object_id(activity_id)
    activity = await db.activities.find_one({"_id": obj_id})
    if not activity:
        raise HTTPException(status_code=404, detail="生产活动不存在")

    personnel_roles_required: List[str] = activity.get("personnel_roles_required", [])
    equipment_types_required: List[str] = activity.get("equipment_types_required", [])

    personnel_ids: List[str] = []
    equipment_ids: List[str] = []
    consumed_raw: List[dict] = []

    try:
        async with driver.session() as session:
            # 查询 ASSIGNED_TO 人员
            result = await session.run(
                "MATCH (a:Activity {id: $aid})-[:ASSIGNED_TO]->(p:Personnel) RETURN p.id AS id",
                {"aid": activity_id},
            )
            async for record in result:
                if record["id"]:
                    personnel_ids.append(record["id"])

            # 查询 USES 设备
            result = await session.run(
                "MATCH (a:Activity {id: $aid})-[:USES]->(r:Resource) RETURN r.id AS id",
                {"aid": activity_id},
            )
            async for record in result:
                if record["id"]:
                    equipment_ids.append(record["id"])

            # 查询 CONSUMES 原料及速率
            result = await session.run(
                "MATCH (a:Activity {id: $aid})-[c:CONSUMES]->(r:Resource) RETURN r.id AS id, c.rate AS rate",
                {"aid": activity_id},
            )
            async for record in result:
                if record["id"]:
                    consumed_raw.append({"id": record["id"], "rate": record["rate"] or 0.0})
    except Exception as e:
        print(f"Neo4j查询失败: {e}")

    # 从 MongoDB 丰富人员信息
    assigned_personnel = []
    for p_id in personnel_ids:
        if not ObjectId.is_valid(p_id):
            continue
        person = await db.personnel.find_one({"_id": ObjectId(p_id)})
        if person:
            assigned_personnel.append({
                "id": p_id,
                "name": person.get("name", ""),
                "role": person.get("role", ""),
            })

    # 从 MongoDB 丰富设备信息
    assigned_equipment = []
    for e_id in equipment_ids:
        if not ObjectId.is_valid(e_id):
            continue
        resource = await db.resources.find_one({"_id": ObjectId(e_id)})
        if resource:
            assigned_equipment.append({
                "id": e_id,
                "name": resource.get("name", ""),
                "specification": resource.get("specification", ""),
            })

    # 从 MongoDB 丰富原料信息
    consumed_resources = []
    for item in consumed_raw:
        r_id = item["id"]
        if not ObjectId.is_valid(r_id):
            continue
        resource = await db.resources.find_one({"_id": ObjectId(r_id)})
        if resource:
            consumed_resources.append({
                "resource_id": r_id,
                "name": resource.get("name", ""),
                "rate": item["rate"],
            })

    return {
        "personnel_roles_required": personnel_roles_required,
        "equipment_types_required": equipment_types_required,
        "assigned_personnel": assigned_personnel,
        "assigned_equipment": assigned_equipment,
        "consumed_resources": consumed_resources,
    }


@router.put("/{activity_id}/resources")
async def update_activity_resources(activity_id: str, payload: ActivityResourcesPayload):
    """综合更新活动资源分配（同时写 MongoDB 需求定义 + 原子化同步 Neo4j 关系）"""
    db = get_database()
    driver = get_neo4j_driver()

    obj_id = _parse_activity_object_id(activity_id)
    activity = await db.activities.find_one({"_id": obj_id})
    if not activity:
        raise HTTPException(status_code=404, detail="生产活动不存在")

    # ── 1. 更新 MongoDB 需求字段 ─────────────────────────────────────
    await db.activities.update_one(
        {"_id": obj_id},
        {
            "$set": {
                "personnel_roles_required": payload.personnel_roles,
                "equipment_types_required": payload.equipment_types,
                "updated_at": datetime.utcnow(),
            }
        },
    )

    # ── 2. 原子化同步 Neo4j ──────────────────────────────────────────
    try:
        async with driver.session() as session:
            # 步骤 2a：删除该活动所有旧的资源关系（兼容新旧命名）
            await session.run(
                """
                MATCH (a:Activity {id: $aid})-[r:ASSIGNED_TO|USES|CONSUMES|ASSIGNS|OCCUPIES]->()
                DELETE r
                """,
                {"aid": activity_id},
            )

            # 步骤 2b：批量创建 ASSIGNED_TO（人员）
            if payload.assigned_personnel_ids:
                await session.run(
                    """
                    UNWIND $ids AS pid
                    MATCH (a:Activity {id: $aid})
                    MATCH (p:Personnel {id: pid})
                    CREATE (a)-[:ASSIGNED_TO]->(p)
                    """,
                    {"aid": activity_id, "ids": payload.assigned_personnel_ids},
                )

            # 步骤 2c：批量创建 USES（设备，Resource 节点）
            if payload.assigned_equipment_ids:
                await session.run(
                    """
                    UNWIND $ids AS eid
                    MATCH (a:Activity {id: $aid})
                    MATCH (r:Resource {id: eid})
                    CREATE (a)-[:USES]->(r)
                    """,
                    {"aid": activity_id, "ids": payload.assigned_equipment_ids},
                )

            # 步骤 2d：批量创建 CONSUMES（原料，携带 rate 属性）
            if payload.consumed_resources:
                await session.run(
                    """
                    UNWIND $items AS item
                    MATCH (a:Activity {id: $aid})
                    MATCH (r:Resource {id: item.resource_id})
                    CREATE (a)-[:CONSUMES {rate: item.rate}]->(r)
                    """,
                    {
                        "aid": activity_id,
                        "items": [
                            {"resource_id": cr.resource_id, "rate": cr.rate}
                            for cr in payload.consumed_resources
                        ],
                    },
                )
    except Exception as e:
        print(f"Neo4j同步失败: {e}")
        raise HTTPException(status_code=500, detail=f"资源关系同步失败: {str(e)}")

    return {"message": "资源配置已更新", "activity_id": activity_id}