from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from ..database import get_database, get_neo4j_driver
from ..schemas.dependency import DependencyCreate, DependencyUpdate, DependencyResponse

router = APIRouter(prefix="/api/dependencies", tags=["依赖关系"])

async def check_activity_exists(db, activity_id: str):
    if not ObjectId.is_valid(activity_id):
        raise HTTPException(status_code=400, detail=f"无效的活动ID: {activity_id}")
    activity = await db.activities.find_one({"_id": ObjectId(activity_id)})
    if not activity:
        raise HTTPException(status_code=404, detail=f"活动不存在: {activity_id}")
    return activity

@router.post("", response_model=DependencyResponse)
async def create_dependency(dependency: DependencyCreate):
    db = get_database()
    driver = get_neo4j_driver()
    
    # 1. Validate activities exist in MongoDB
    await check_activity_exists(db, dependency.source_activity_id)
    await check_activity_exists(db, dependency.target_activity_id)
    
    # 2. Create relationship in Neo4j
    query = """
    MERGE (a:Activity {id: $source_id})
    MERGE (b:Activity {id: $target_id})
    MERGE (a)-[r:DEPENDS_ON]->(b)
    SET r.type = $type,
        r.time_constraint = $time,
        r.status = $status,
        r.description = $desc,
        r.created_at = datetime()
    RETURN elementId(r) as id, r
    """
    
    try:
        async with driver.session() as session:
            result = await session.run(query, {
                "source_id": dependency.source_activity_id,
                "target_id": dependency.target_activity_id,
                "type": dependency.dependency_type,
                "time": dependency.time_constraint,
                "status": dependency.status or "active",
                "desc": dependency.description
            })
            record = await result.single()
            if not record:
                raise HTTPException(status_code=500, detail="创建依赖关系失败")
            
            rel_id = record["id"]
            # Construct response
            return DependencyResponse(
                id=rel_id,
                source_activity_id=dependency.source_activity_id,
                target_activity_id=dependency.target_activity_id,
                dependency_type=dependency.dependency_type,
                time_constraint=dependency.time_constraint,
                status=dependency.status or "active",
                description=dependency.description,
                created_at=datetime.utcnow() 
            )
    except Exception as e:
        print(f"Neo4j Error: {e}")
        raise HTTPException(status_code=500, detail=f"图数据库操作失败: {str(e)}")

@router.get("", response_model=List[DependencyResponse])
async def get_dependencies(activity_id: Optional[str] = Query(None, description="按活动ID筛选")):
    driver = get_neo4j_driver()
    
    if activity_id:
        # Check specific activity dependencies (both incoming and outgoing)
        query = """
        MATCH (s:Activity)-[r:DEPENDS_ON]->(t:Activity)
        WHERE s.id = $aid OR t.id = $aid
        RETURN elementId(r) as id, s.id as source, t.id as target, r
        """
        params = {"aid": activity_id}
    else:
        # Get all dependencies
        query = """
        MATCH (s:Activity)-[r:DEPENDS_ON]->(t:Activity)
        RETURN elementId(r) as id, s.id as source, t.id as target, r
        """
        params = {}

    try:
        dependencies = []
        async with driver.session() as session:
            result = await session.run(query, params)
            async for record in result:
                rel = record["r"]
                source_id = record["source"]
                target_id = record["target"]
                
                dependencies.append(DependencyResponse(
                    id=record["id"],
                    source_activity_id=source_id,
                    target_activity_id=target_id,
                    dependency_type=rel.get("type", rel.get("dependency_type")),
                    time_constraint=rel.get("time_constraint"),
                    status=rel.get("status", "active"),
                    description=rel.get("description"),
                    created_at=None 
                ))
        return dependencies
    except Exception as e:
        print(f"Neo4j Error: {e}")
        raise HTTPException(status_code=500, detail=f"图数据库查询失败: {str(e)}")

@router.put("/{dependency_id}", response_model=DependencyResponse)
async def update_dependency(dependency_id: str, dependency: DependencyUpdate):
    driver = get_neo4j_driver()
    
    query = """
    MATCH (s:Activity)-[r:DEPENDS_ON]->(t:Activity)
    WHERE elementId(r) = $did
    SET r += $props
    RETURN s.id as source, t.id as target, r
    """
    
    # Filter None values
    update_props = {k: v for k, v in dependency.model_dump().items() if v is not None}
    if not update_props:
        raise HTTPException(status_code=400, detail="没有提供更新数据")

    try:
        async with driver.session() as session:
            result = await session.run(query, {"did": dependency_id, "props": update_props})
            record = await result.single()
            if not record:
                raise HTTPException(status_code=404, detail="依赖关系不存在")
            
            rel = record["r"]
            return DependencyResponse(
                id=dependency_id,
                source_activity_id=record["source"],
                target_activity_id=record["target"],
                dependency_type=rel.get("type", rel.get("dependency_type")),
                time_constraint=rel.get("time_constraint"),
                status=rel.get("status", "active"),
                description=rel.get("description")
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

@router.delete("/{dependency_id}")
async def delete_dependency(dependency_id: str):
    driver = get_neo4j_driver()
    
    query = """
    MATCH ()-[r:DEPENDS_ON]->()
    WHERE elementId(r) = $did
    DELETE r
    RETURN count(r) as deleted_count
    """
    
    try:
        async with driver.session() as session:
            result = await session.run(query, {"did": dependency_id})
            record = await result.single()
            if record["deleted_count"] == 0:
                raise HTTPException(status_code=404, detail="依赖关系不存在")
            return {"message": "删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.get("/graph/data")
async def get_graph_data():
    driver = get_neo4j_driver()
    db = get_database()
    
    try:
        edges = []
        node_ids = set()
        resource_ids = set()
        
        # 获取活动依赖关系
        dependency_query = """
        MATCH (s:Activity)-[r:DEPENDS_ON]->(t:Activity)
        RETURN s.id as source_id, t.id as target_id, 'DEPENDS_ON' as rel_type, r
        """
        
        async with driver.session() as session:
            result = await session.run(dependency_query)
            async for record in result:
                source_id = record["source_id"]
                target_id = record["target_id"]
                rel = record["r"]
                
                node_ids.add(source_id)
                node_ids.add(target_id)
                
                edges.append({
                    "source": source_id,
                    "target": target_id,
                    "relation": "DEPENDS_ON",
                    "type": rel.get("type", rel.get("dependency_type")),
                    "time_constraint": rel.get("time_constraint"),
                    "status": rel.get("status"),
                    "description": rel.get("description")
                })
        
        # 获取活动-资源使用关系
        usage_query = """
        MATCH (a:Activity)-[u:USES]->(r:Resource)
        RETURN a.id as activity_id, r.id as resource_id, u
        """
        
        async with driver.session() as session:
            result = await session.run(usage_query)
            async for record in result:
                activity_id = record["activity_id"]
                resource_id = record["resource_id"]
                rel = record["u"]
                
                node_ids.add(activity_id)
                resource_ids.add(resource_id)
                
                edges.append({
                    "source": activity_id,
                    "target": resource_id,
                    "relation": "USES",
                    "quantity": rel.get("quantity"),
                    "unit": rel.get("unit"),
                    "stage": rel.get("stage")
                })
        
        # 构建节点列表
        nodes = []
        
        # 添加活动节点
        for node_id in node_ids:
            activity = await db.activities.find_one({"_id": ObjectId(node_id)})
            if activity:
                nodes.append({
                    "id": node_id,
                    "name": activity.get("name", "未知活动"),
                    "category": "Activity",
                    "type": activity.get("activity_type", "unknown"),
                    "status": activity.get("status", "pending")
                })
        
        # 添加资源节点
        for resource_id in resource_ids:
            resource = await db.resources.find_one({"_id": ObjectId(resource_id)})
            if resource:
                nodes.append({
                    "id": resource_id,
                    "name": resource.get("name", "未知资源"),
                    "category": "Resource",
                    "type": resource.get("type", "unknown"),
                    "status": resource.get("status", "available")
                })
        
        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        print(f"Neo4j Error: {e}")
        raise HTTPException(status_code=500, detail=f"获取图数据失败: {str(e)}")
