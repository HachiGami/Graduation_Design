from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from ..database import get_database, get_neo4j_driver
from ..schemas.resource import ResourceCreate, ResourceUpdate, ResourceResponse
from bson import ObjectId

router = APIRouter(prefix="/api/resources", tags=["资源管理"])

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
    
    # 同步到Neo4j：只存resource_id和name
    neo4j_query = """
    MERGE (r:Resource {id: $resource_id})
    SET r.name = $name, r.domain = $domain
    RETURN r
    """
    try:
        async with driver.session() as session:
            await session.run(neo4j_query, {
                "resource_id": resource_id,
                "name": resource.name,
                "domain": resource.domain
            })
    except Exception as e:
        print(f"Neo4j同步失败: {e}")
    
    return resource_dict

@router.get("", response_model=List[ResourceResponse])
async def get_resources(
    domain: Optional[str] = Query(None, description="按流程域筛选"),
    process_id: Optional[str] = Query(None, description="按流程实例ID筛选"),
    type: Optional[str] = Query(None, description="按资源类型筛选")
):
    db = get_database()
    driver = get_neo4j_driver()
    
    query_filter = {}
    if domain:
        query_filter["domain"] = domain
    if process_id:
        query_filter["process_id"] = process_id
    if type:
        query_filter["type"] = type
    
    resources = []
    resource_ids = []
    async for resource in db.resources.find(query_filter):
        resource["_id"] = str(resource["_id"])
        resource["serving_activities"] = []
        resources.append(resource)
        resource_ids.append(resource["_id"])
        
    if type == "设备" and resource_ids:
        # 查询 Neo4j 获取 serving_activities
        neo4j_query = """
        MATCH (e)-[:USED_BY|OCCUPIES]-(a:Activity)
        WHERE (e:Resource OR e:Equipment) AND e.id IN $resource_ids
        RETURN e.id AS resource_id, collect(a.name) AS activities
        """
        try:
            async with driver.session() as session:
                result = await session.run(neo4j_query, {"resource_ids": resource_ids})
                activities_map = {}
                async for record in result:
                    activities_map[record["resource_id"]] = record["activities"]
                
                for resource in resources:
                    if resource["_id"] in activities_map:
                        resource["serving_activities"] = activities_map[resource["_id"]]
        except Exception as e:
            print(f"Neo4j查询失败: {e}")
            
    return resources

@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(resource_id: str):
    db = get_database()
    resource = await db.resources.find_one({"_id": ObjectId(resource_id)})
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    resource["_id"] = str(resource["_id"])
    return resource

@router.put("/{resource_id}", response_model=ResourceResponse)
async def update_resource(resource_id: str, resource: ResourceUpdate):
    db = get_database()
    driver = get_neo4j_driver()
    
    update_data = {k: v for k, v in resource.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.resources.update_one(
        {"_id": ObjectId(resource_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="资源不存在")
    
    updated_resource = await db.resources.find_one({"_id": ObjectId(resource_id)})
    updated_resource["_id"] = str(updated_resource["_id"])
    
    # 同步到Neo4j：如果name更新了，同步更新
    if resource.name or resource.domain:
        neo4j_query = """
        MATCH (r:Resource {id: $resource_id})
        SET r.name = COALESCE($name, r.name),
            r.domain = COALESCE($domain, r.domain)
        RETURN r
        """
        try:
            async with driver.session() as session:
                await session.run(neo4j_query, {
                    "resource_id": resource_id,
                    "name": resource.name,
                    "domain": resource.domain
                })
        except Exception as e:
            print(f"Neo4j同步失败: {e}")
    
    return updated_resource

@router.delete("/{resource_id}")
async def delete_resource(resource_id: str):
    db = get_database()
    driver = get_neo4j_driver()
    
    result = await db.resources.delete_one({"_id": ObjectId(resource_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="资源不存在")
    
    # 同步到Neo4j：删除节点及其所有关系
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
