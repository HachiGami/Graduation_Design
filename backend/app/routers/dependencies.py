from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from bson import ObjectId

from ..database import get_database, get_neo4j_driver
from ..schemas.dependency import DependencyCreate, DependencyUpdate, DependencyResponse
from ..services.risk_service import calculate_activity_risks

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
        r.lag_minutes = $lag,
        r.status = $status,
        r.description = $desc,
        r.domain = $domain,
        r.process_id = $process_id,
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
                "lag": dependency.lag_minutes or 0,
                "status": dependency.status or "active",
                "desc": dependency.description,
                "domain": dependency.domain,
                "process_id": dependency.process_id
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
async def get_dependencies(
    domain: str = Query(..., description="流程域（必填）"),
    process_id: Optional[str] = Query(None, description="流程实例ID"),
    activity_id: Optional[str] = Query(None, description="按活动ID筛选")
):
    driver = get_neo4j_driver()
    
    where_clauses = ["r.domain = $domain"]
    params = {"domain": domain}
    
    if process_id:
        where_clauses.append("r.process_id = $process_id")
        params["process_id"] = process_id
    
    if activity_id:
        where_clauses.append("(s.id = $aid OR t.id = $aid)")
        params["aid"] = activity_id
    
    where_clause = " AND ".join(where_clauses)
    
    query = f"""
    MATCH (s:Activity)-[r:DEPENDS_ON]->(t:Activity)
    WHERE {where_clause}
    RETURN elementId(r) as id, s.id as source, t.id as target, r
    """

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
                    domain=rel.get("domain"),
                    process_id=rel.get("process_id"),
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
@router.get("/graph/data")
async def get_graph_data(
    scope: str = Query("global", description="查询范围: global/domain/process"),
    domain: Optional[str] = Query(None, description="流程域（scope=domain或process时必填）"),
    process_id: Optional[str] = Query(None, description="流程实例ID（scope=process时必填）"),
    include_cross: bool = Query(False, description="是否包含跨流程关联")
):
    """
    获取图数据
    - scope=global: 返回全部数据（默认）
    - scope=domain: 返回指定domain的所有process
    - scope=process: 返回指定domain+process_id的数据
    """
    driver = get_neo4j_driver()
    db = get_database()
    try:
        edges = []
        activity_ids = set()
        
        # 根据scope构建查询
        if scope == "global":
            # 全局：返回所有数据
            dependency_query = """
            MATCH (s:Activity)-[r:DEPENDS_ON]->(t:Activity)
            RETURN DISTINCT s.id as source_id, t.id as target_id, r,
                   s.domain as s_domain, s.process_id as s_pid,
                   t.domain as t_domain, t.process_id as t_pid
            ORDER BY s.id, t.id
            """
            params = {}
        elif scope == "domain":
            # 域级：返回某个domain的所有process
            if not domain:
                raise HTTPException(status_code=400, detail="scope=domain时必须提供domain参数")
            dependency_query = """
            MATCH (s:Activity)-[r:DEPENDS_ON]->(t:Activity)
            WHERE s.domain = $domain OR t.domain = $domain
            RETURN DISTINCT s.id as source_id, t.id as target_id, r,
                   s.domain as s_domain, s.process_id as s_pid,
                   t.domain as t_domain, t.process_id as t_pid
            ORDER BY s.id, t.id
            """
            params = {"domain": domain}
        else:  # scope == "process"
            # 流程级：返回指定domain+process_id的数据
            if not domain or not process_id:
                raise HTTPException(status_code=400, detail="scope=process时必须提供domain和process_id参数")
            
            if include_cross:
                dependency_query = """
                MATCH (s:Activity)-[r:DEPENDS_ON]->(t:Activity)
                WHERE (s.domain = $domain AND s.process_id = $process_id) 
                   OR (t.domain = $domain AND t.process_id = $process_id)
                RETURN DISTINCT s.id as source_id, t.id as target_id, r,
                       s.domain as s_domain, s.process_id as s_pid,
                       t.domain as t_domain, t.process_id as t_pid
                ORDER BY s.id, t.id
                """
            else:
                dependency_query = """
                MATCH (s:Activity)-[r:DEPENDS_ON]->(t:Activity)
                WHERE r.domain = $domain AND r.process_id = $process_id
                RETURN DISTINCT s.id as source_id, t.id as target_id, r,
                       s.domain as s_domain, s.process_id as s_pid,
                       t.domain as t_domain, t.process_id as t_pid
                ORDER BY s.id, t.id
                """
            params = {"domain": domain, "process_id": process_id}
        
        async with driver.session() as session:
            result = await session.run(dependency_query, params)
            async for record in result:
                source_id = record["source_id"]
                target_id = record["target_id"]
                rel = record["r"]
                
                # 获取source和target的domain/process_id
                s_domain = record.get("s_domain")
                s_pid = record.get("s_pid")
                t_domain = record.get("t_domain")
                t_pid = record.get("t_pid")
                
                activity_ids.add(source_id)
                activity_ids.add(target_id)
                
                edges.append({
                    "source": source_id,
                    "target": target_id,
                    "relation": "DEPENDS_ON",
                    "type": rel.get("type", rel.get("dependency_type", "sequential")),
                    "time_constraint": rel.get("time_constraint"),
                    "status": rel.get("status", "active"),
                    "description": rel.get("description"),
                    "domain": rel.get("domain", s_domain),  # 边的domain（优先用关系属性，否则用源节点）
                    "process_id": rel.get("process_id", s_pid)  # 边的process_id
                })
        
        # 获取活动-资源使用关系（每个活动的资源单独一个节点）
        usage_query = """
        MATCH (a:Activity)-[u:ASSIGNED_TO|ASSIGNS|USES|CONSUMES]->(r)
        WHERE any(label IN labels(r) WHERE label IN ['Resource', 'Equipment', 'Material'])
        RETURN a.id as activity_id, r.id as resource_id, r.name as resource_name,
               coalesce(r.resource_type, head(labels(r))) as resource_type,
               type(u) as relation_type, labels(r) as node_labels, u
        ORDER BY a.id, r.id
        """
        
        resource_nodes = []
        resource_edges = []
        resource_instance_counter = {}
        
        async with driver.session() as session:
            result = await session.run(usage_query)
            async for record in result:
                activity_id = record["activity_id"]
                resource_id = record["resource_id"]
                relation_type = record["relation_type"]
                rel = record["u"]
                
                activity_ids.add(activity_id)
                
                # 为每个活动-资源组合创建唯一的资源实例ID
                key = f"{activity_id}_{resource_id}"
                if key not in resource_instance_counter:
                    resource_instance_counter[key] = 0
                resource_instance_counter[key] += 1
                
                resource_instance_id = f"{resource_id}_inst_{activity_id}"
                
                # 优先从 MongoDB 取资源详情；若 resource_id 不是 ObjectId（例如 UUID），回退到 Neo4j 属性
                resource = None
                if resource_id and ObjectId.is_valid(resource_id):
                    resource = await db.resources.find_one({"_id": ObjectId(resource_id)})

                if resource:
                    resource_nodes.append({
                        "id": resource_instance_id,
                        "original_id": resource_id,
                        "name": resource.get("name", "未知资源"),
                        "category": "Resource",
                        "type": resource.get("type", "material"),
                        "status": resource.get("status", "available"),
                        "parent_activity": activity_id,
                        "specification": resource.get("specification", ""),
                        "supplier": resource.get("supplier", ""),
                        "quantity": resource.get("quantity", 0),
                        "unit": resource.get("unit", ""),
                        "expiry_date": resource.get("expiry_date")
                    })
                else:
                    resource_nodes.append({
                        "id": resource_instance_id,
                        "original_id": resource_id,
                        "name": record.get("resource_name", "未知资源"),
                        "category": "Resource",
                        "type": (record.get("resource_type") or "material").lower(),
                        "status": "available",
                        "parent_activity": activity_id,
                        "specification": "",
                        "supplier": "",
                        "quantity": 0,
                        "unit": rel.get("unit", ""),
                        "expiry_date": None
                    })
                
                resource_edges.append({
                    "source": activity_id,
                    "target": resource_instance_id,
                    "relation": relation_type,
                    "quantity": rel.get("quantity", 1),
                    "unit": rel.get("unit", "unit"),
                    "stage": rel.get("stage")
                })
        
        # 获取活动-人员分配关系（每个活动的人员单独一个节点）
        personnel_query = """
        MATCH (a:Activity)-[as:ASSIGNED_TO|ASSIGNS]->(p:Personnel)
        RETURN a.id as activity_id, p.id as personnel_id, as
        ORDER BY a.id, p.id
        """
        
        personnel_nodes = []
        personnel_edges = []
        
        async with driver.session() as session:
            result = await session.run(personnel_query)
            async for record in result:
                activity_id = record["activity_id"]
                personnel_id = record["personnel_id"]
                rel = record["as"]
                
                activity_ids.add(activity_id)
                
                # 为每个活动-人员组合创建唯一的人员实例ID
                personnel_instance_id = f"{personnel_id}_inst_{activity_id}"
                
                # 获取人员详情
                try:
                    personnel = await db.personnel.find_one({"_id": ObjectId(personnel_id)})
                    if personnel:
                        personnel_nodes.append({
                            "id": personnel_instance_id,
                            "original_id": personnel_id,
                            "name": personnel.get("name", "未知人员"),
                            "category": "Personnel",
                            "role": rel.get("role", "操作员"),
                            "status": personnel.get("status", "available"),
                            "parent_activity": activity_id,
                            "responsibility": personnel.get("responsibility", ""),
                            "skills": personnel.get("skills", []),
                            "work_hours": personnel.get("work_hours", ""),
                            "assigned_tasks": personnel.get("assigned_tasks", [])
                        })
                except Exception as e:
                    pass
                
                personnel_edges.append({
                    "source": activity_id,
                    "target": personnel_instance_id,
                    "relation": "ASSIGNS",
                    "role": rel.get("role")
                })
        
        # 构建活动节点列表
        nodes = []
        activity_docs = []
        seen_activity_ids = set()
        
        for node_id in activity_ids:
            if node_id not in seen_activity_ids:
                activity = await db.activities.find_one({"_id": ObjectId(node_id)})
                
                if activity:
                    activity["_id"] = str(activity["_id"])
                    activity_docs.append(activity)
                    nodes.append({
                        "id": node_id,
                        "name": activity.get("name", "未知活动"),
                        "category": "Activity",
                        "type": activity.get("activity_type", "processing"),
                        "status": activity.get("status", "pending"),
                        "description": activity.get("description", ""),
                        "estimated_duration": activity.get("estimated_duration", 0),
                        "domain": activity.get("domain", "unknown"),
                        "process_id": activity.get("process_id", "unknown"),
                        "risks": [],
                    })
                    seen_activity_ids.add(node_id)

        try:
            risks_by_activity = await calculate_activity_risks(db, driver, activity_docs)
            for node in nodes:
                node["risks"] = risks_by_activity.get(node["id"], [])
        except Exception as e:
            print(f"图谱节点风险计算失败: {e}")
        
        return {
            "nodes": nodes,
            "edges": edges,
            "resource_nodes": resource_nodes,
            "resource_edges": resource_edges,
            "personnel_nodes": personnel_nodes,
            "personnel_edges": personnel_edges
        }
    except Exception as e:
        print(f"Neo4j Error: {e}")
        raise HTTPException(status_code=500, detail=f"获取图数据失败: {str(e)}")
