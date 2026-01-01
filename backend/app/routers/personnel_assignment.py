from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from bson import ObjectId

from ..database import get_database, get_neo4j_driver
from ..schemas.personnel_assignment import PersonnelAssignmentCreate, PersonnelAssignmentUpdate, PersonnelAssignmentResponse

router = APIRouter(prefix="/api/personnel-assignment", tags=["人员分配关系"])

async def check_activity_exists(db, activity_id: str):
    if not ObjectId.is_valid(activity_id):
        raise HTTPException(status_code=400, detail=f"无效的活动ID: {activity_id}")
    activity = await db.activities.find_one({"_id": ObjectId(activity_id)})
    if not activity:
        raise HTTPException(status_code=404, detail=f"活动不存在: {activity_id}")
    return activity

async def check_personnel_exists(db, personnel_id: str):
    if not ObjectId.is_valid(personnel_id):
        raise HTTPException(status_code=400, detail=f"无效的人员ID: {personnel_id}")
    personnel = await db.personnel.find_one({"_id": ObjectId(personnel_id)})
    if not personnel:
        raise HTTPException(status_code=404, detail=f"人员不存在: {personnel_id}")
    return personnel

@router.post("", response_model=PersonnelAssignmentResponse)
async def create_personnel_assignment(assignment: PersonnelAssignmentCreate):
    db = get_database()
    driver = get_neo4j_driver()
    
    # 验证活动和人员是否存在
    await check_activity_exists(db, assignment.activity_id)
    await check_personnel_exists(db, assignment.personnel_id)
    
    # 在Neo4j中创建ASSIGNS关系
    query = """
    MERGE (a:Activity {id: $activity_id})
    MERGE (p:Personnel {id: $personnel_id})
    MERGE (a)-[as:ASSIGNS]->(p)
    SET as.role = $role,
        as.created_at = datetime()
    RETURN elementId(as) as id, as
    """
    
    try:
        async with driver.session() as session:
            result = await session.run(query, {
                "activity_id": assignment.activity_id,
                "personnel_id": assignment.personnel_id,
                "role": assignment.role
            })
            record = await result.single()
            if not record:
                raise HTTPException(status_code=500, detail="创建人员分配关系失败")
            
            rel_id = record["id"]
            return PersonnelAssignmentResponse(
                id=rel_id,
                activity_id=assignment.activity_id,
                personnel_id=assignment.personnel_id,
                role=assignment.role
            )
    except Exception as e:
        print(f"Neo4j Error: {e}")
        raise HTTPException(status_code=500, detail=f"图数据库操作失败: {str(e)}")

@router.get("", response_model=List[PersonnelAssignmentResponse])
async def get_personnel_assignments(
    activity_id: Optional[str] = Query(None, description="按活动ID筛选"),
    personnel_id: Optional[str] = Query(None, description="按人员ID筛选")
):
    driver = get_neo4j_driver()
    
    if activity_id and personnel_id:
        query = """
        MATCH (a:Activity {id: $aid})-[as:ASSIGNS]->(p:Personnel {id: $pid})
        RETURN elementId(as) as id, a.id as activity_id, p.id as personnel_id, as
        """
        params = {"aid": activity_id, "pid": personnel_id}
    elif activity_id:
        query = """
        MATCH (a:Activity {id: $aid})-[as:ASSIGNS]->(p:Personnel)
        RETURN elementId(as) as id, a.id as activity_id, p.id as personnel_id, as
        """
        params = {"aid": activity_id}
    elif personnel_id:
        query = """
        MATCH (a:Activity)-[as:ASSIGNS]->(p:Personnel {id: $pid})
        RETURN elementId(as) as id, a.id as activity_id, p.id as personnel_id, as
        """
        params = {"pid": personnel_id}
    else:
        query = """
        MATCH (a:Activity)-[as:ASSIGNS]->(p:Personnel)
        RETURN elementId(as) as id, a.id as activity_id, p.id as personnel_id, as
        """
        params = {}

    try:
        assignments = []
        async with driver.session() as session:
            result = await session.run(query, params)
            async for record in result:
                rel = record["as"]
                assignments.append(PersonnelAssignmentResponse(
                    id=record["id"],
                    activity_id=record["activity_id"],
                    personnel_id=record["personnel_id"],
                    role=rel.get("role")
                ))
        return assignments
    except Exception as e:
        print(f"Neo4j Error: {e}")
        raise HTTPException(status_code=500, detail=f"图数据库查询失败: {str(e)}")

@router.put("/{assignment_id}", response_model=PersonnelAssignmentResponse)
async def update_personnel_assignment(assignment_id: str, assignment: PersonnelAssignmentUpdate):
    driver = get_neo4j_driver()
    
    query = """
    MATCH (a:Activity)-[as:ASSIGNS]->(p:Personnel)
    WHERE elementId(as) = $aid
    SET as += $props
    RETURN a.id as activity_id, p.id as personnel_id, as
    """
    
    update_props = {k: v for k, v in assignment.model_dump().items() if v is not None}
    if not update_props:
        raise HTTPException(status_code=400, detail="没有提供更新数据")

    try:
        async with driver.session() as session:
            result = await session.run(query, {"aid": assignment_id, "props": update_props})
            record = await result.single()
            if not record:
                raise HTTPException(status_code=404, detail="人员分配关系不存在")
            
            rel = record["as"]
            return PersonnelAssignmentResponse(
                id=assignment_id,
                activity_id=record["activity_id"],
                personnel_id=record["personnel_id"],
                role=rel.get("role")
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

@router.delete("/{assignment_id}")
async def delete_personnel_assignment(assignment_id: str):
    driver = get_neo4j_driver()
    
    query = """
    MATCH ()-[as:ASSIGNS]->()
    WHERE elementId(as) = $aid
    DELETE as
    RETURN count(as) as deleted_count
    """
    
    try:
        async with driver.session() as session:
            result = await session.run(query, {"aid": assignment_id})
            record = await result.single()
            if record["deleted_count"] == 0:
                raise HTTPException(status_code=404, detail="人员分配关系不存在")
            return {"message": "删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

