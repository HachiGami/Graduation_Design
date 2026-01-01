from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from ..database import get_database, get_neo4j_driver
from ..schemas.activity import ActivityCreate, ActivityUpdate, ActivityResponse
from bson import ObjectId

router = APIRouter(prefix="/api/activities", tags=["生产活动"])

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
        activities.append(activity)
    return activities

@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(activity_id: str):
    db = get_database()
    activity = await db.activities.find_one({"_id": ObjectId(activity_id)})
    if not activity:
        raise HTTPException(status_code=404, detail="生产活动不存在")
    activity["_id"] = str(activity["_id"])
    return activity

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

