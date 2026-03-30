from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from ..database import get_database, get_neo4j_driver
from ..schemas.activity import ActivityCreate, ActivityUpdate, ActivityResponse
from bson import ObjectId

router = APIRouter(prefix="/api/activities", tags=["生产活动"])


def _normalize_sop_steps(raw_steps):
    if not raw_steps:
        return []
    normalized = []
    for index, step in enumerate(raw_steps):
        if isinstance(step, dict):
            normalized.append({
                "step_number": int(step.get("step_number", index + 1)),
                "description": str(step.get("description", "")),
                "duration": int(step.get("duration", 0)),
            })
        else:
            normalized.append({
                "step_number": index + 1,
                "description": str(step),
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
    activity.setdefault("created_at", activity.get("updated_at") or now)
    activity.setdefault("updated_at", activity.get("created_at") or now)
    return activity

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