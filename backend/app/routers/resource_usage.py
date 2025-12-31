from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from bson import ObjectId

from ..database import get_database, get_neo4j_driver
from ..schemas.resource_usage import ResourceUsageCreate, ResourceUsageUpdate, ResourceUsageResponse

router = APIRouter(prefix="/api/resource-usage", tags=["资源使用关系"])

async def check_activity_exists(db, activity_id: str):
    if not ObjectId.is_valid(activity_id):
        raise HTTPException(status_code=400, detail=f"无效的活动ID: {activity_id}")
    activity = await db.activities.find_one({"_id": ObjectId(activity_id)})
    if not activity:
        raise HTTPException(status_code=404, detail=f"活动不存在: {activity_id}")
    return activity

async def check_resource_exists(db, resource_id: str):
    if not ObjectId.is_valid(resource_id):
        raise HTTPException(status_code=400, detail=f"无效的资源ID: {resource_id}")
    resource = await db.resources.find_one({"_id": ObjectId(resource_id)})
    if not resource:
        raise HTTPException(status_code=404, detail=f"资源不存在: {resource_id}")
    return resource

@router.post("", response_model=ResourceUsageResponse)
async def create_resource_usage(usage: ResourceUsageCreate):
    db = get_database()
    driver = get_neo4j_driver()
    
    # 验证活动和资源是否存在
    await check_activity_exists(db, usage.activity_id)
    await check_resource_exists(db, usage.resource_id)
    
    # 在Neo4j中创建USES关系
    query = """
    MERGE (a:Activity {id: $activity_id})
    MERGE (r:Resource {id: $resource_id})
    MERGE (a)-[u:USES]->(r)
    SET u.quantity = $quantity,
        u.unit = $unit,
        u.stage = $stage,
        u.created_at = datetime()
    RETURN elementId(u) as id, u
    """
    
    try:
        async with driver.session() as session:
            result = await session.run(query, {
                "activity_id": usage.activity_id,
                "resource_id": usage.resource_id,
                "quantity": usage.quantity,
                "unit": usage.unit,
                "stage": usage.stage
            })
            record = await result.single()
            if not record:
                raise HTTPException(status_code=500, detail="创建资源使用关系失败")
            
            rel_id = record["id"]
            return ResourceUsageResponse(
                id=rel_id,
                activity_id=usage.activity_id,
                resource_id=usage.resource_id,
                quantity=usage.quantity,
                unit=usage.unit,
                stage=usage.stage
            )
    except Exception as e:
        print(f"Neo4j Error: {e}")
        raise HTTPException(status_code=500, detail=f"图数据库操作失败: {str(e)}")

@router.get("", response_model=List[ResourceUsageResponse])
async def get_resource_usages(
    activity_id: Optional[str] = Query(None, description="按活动ID筛选"),
    resource_id: Optional[str] = Query(None, description="按资源ID筛选")
):
    driver = get_neo4j_driver()
    
    if activity_id and resource_id:
        query = """
        MATCH (a:Activity {id: $aid})-[u:USES]->(r:Resource {id: $rid})
        RETURN elementId(u) as id, a.id as activity_id, r.id as resource_id, u
        """
        params = {"aid": activity_id, "rid": resource_id}
    elif activity_id:
        query = """
        MATCH (a:Activity {id: $aid})-[u:USES]->(r:Resource)
        RETURN elementId(u) as id, a.id as activity_id, r.id as resource_id, u
        """
        params = {"aid": activity_id}
    elif resource_id:
        query = """
        MATCH (a:Activity)-[u:USES]->(r:Resource {id: $rid})
        RETURN elementId(u) as id, a.id as activity_id, r.id as resource_id, u
        """
        params = {"rid": resource_id}
    else:
        query = """
        MATCH (a:Activity)-[u:USES]->(r:Resource)
        RETURN elementId(u) as id, a.id as activity_id, r.id as resource_id, u
        """
        params = {}

    try:
        usages = []
        async with driver.session() as session:
            result = await session.run(query, params)
            async for record in result:
                rel = record["u"]
                usages.append(ResourceUsageResponse(
                    id=record["id"],
                    activity_id=record["activity_id"],
                    resource_id=record["resource_id"],
                    quantity=rel.get("quantity"),
                    unit=rel.get("unit"),
                    stage=rel.get("stage")
                ))
        return usages
    except Exception as e:
        print(f"Neo4j Error: {e}")
        raise HTTPException(status_code=500, detail=f"图数据库查询失败: {str(e)}")

@router.put("/{usage_id}", response_model=ResourceUsageResponse)
async def update_resource_usage(usage_id: str, usage: ResourceUsageUpdate):
    driver = get_neo4j_driver()
    
    query = """
    MATCH (a:Activity)-[u:USES]->(r:Resource)
    WHERE elementId(u) = $uid
    SET u += $props
    RETURN a.id as activity_id, r.id as resource_id, u
    """
    
    update_props = {k: v for k, v in usage.model_dump().items() if v is not None}
    if not update_props:
        raise HTTPException(status_code=400, detail="没有提供更新数据")

    try:
        async with driver.session() as session:
            result = await session.run(query, {"uid": usage_id, "props": update_props})
            record = await result.single()
            if not record:
                raise HTTPException(status_code=404, detail="资源使用关系不存在")
            
            rel = record["u"]
            return ResourceUsageResponse(
                id=usage_id,
                activity_id=record["activity_id"],
                resource_id=record["resource_id"],
                quantity=rel.get("quantity"),
                unit=rel.get("unit"),
                stage=rel.get("stage")
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

@router.delete("/{usage_id}")
async def delete_resource_usage(usage_id: str):
    driver = get_neo4j_driver()
    
    query = """
    MATCH ()-[u:USES]->()
    WHERE elementId(u) = $uid
    DELETE u
    RETURN count(u) as deleted_count
    """
    
    try:
        async with driver.session() as session:
            result = await session.run(query, {"uid": usage_id})
            record = await result.single()
            if record["deleted_count"] == 0:
                raise HTTPException(status_code=404, detail="资源使用关系不存在")
            return {"message": "删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

