from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from ..database import get_database, get_neo4j_driver
from ..schemas.personnel import PersonnelCreate, PersonnelUpdate, PersonnelResponse
from bson import ObjectId

router = APIRouter(prefix="/api/personnel", tags=["人员管理"])


def _normalize_personnel_for_response(personnel: dict) -> dict:
    now = datetime.utcnow()
    personnel.setdefault("name", "未知人员")
    personnel.setdefault("role", "操作员")
    personnel.setdefault("department", None)
    personnel.setdefault("responsibility", personnel.get("department") or "")
    personnel.setdefault("skills", [])
    personnel.setdefault("work_hours", "")
    personnel.setdefault("assigned_tasks", [])
    personnel.setdefault("status", "active")
    personnel.setdefault("upcoming_leaves", [])
    personnel.setdefault("age", None)
    personnel.setdefault("gender", None)
    personnel.setdefault("native_place", None)
    personnel.setdefault("hire_date", None)
    personnel.setdefault("education", None)
    personnel.setdefault("salary", None)
    personnel.setdefault("created_at", personnel.get("updated_at") or now)
    personnel.setdefault("updated_at", personnel.get("created_at") or now)
    return personnel

@router.post("", response_model=PersonnelResponse)
async def create_personnel(personnel: PersonnelCreate):
    db = get_database()
    driver = get_neo4j_driver()
    
    personnel_dict = personnel.model_dump()
    personnel_dict["created_at"] = datetime.utcnow()
    personnel_dict["updated_at"] = datetime.utcnow()
    
    result = await db.personnel.insert_one(personnel_dict)
    personnel_id = str(result.inserted_id)
    personnel_dict["_id"] = personnel_id
    
    # 同步到Neo4j：只存personnel_id和name
    neo4j_query = """
    MERGE (p:Personnel {id: $personnel_id})
    SET p.name = $name
    RETURN p
    """
    try:
        async with driver.session() as session:
            await session.run(neo4j_query, {
                "personnel_id": personnel_id,
                "name": personnel.name
            })
    except Exception as e:
        print(f"Neo4j同步失败: {e}")
    
    return personnel_dict

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
    return total_hours


@router.get("", response_model=List[PersonnelResponse])
async def get_personnel():
    db = get_database()
    driver = get_neo4j_driver()

    personnel_list = []
    names = []
    try:
        cursor = db.personnel.find()
        async for personnel in cursor:
            personnel["_id"] = str(personnel["_id"])
            _normalize_personnel_for_response(personnel)
            personnel_list.append(personnel)
            if personnel.get("name"):
                names.append(personnel["name"])
    except Exception:
        raise

    # 从 Neo4j 动态查询关联活动
    entity_activities_map: dict = {}
    if names and driver:
        try:
            async with driver.session() as session:
                result = await session.run(
                    """
                    MATCH (a:Activity)-[]-(p:Personnel)
                    WHERE p.name IN $names
                    RETURN p.name AS entity_name,
                           a.name AS activity_name,
                           a.process_id AS process_id
                    """,
                    {"names": names},
                )
                neo4j_records = await result.data()

            for rec in neo4j_records:
                entity_name = rec.get("entity_name")
                activity_name = rec.get("activity_name")
                process_id = rec.get("process_id")
                if not entity_name or not activity_name:
                    continue

                entity_activities_map.setdefault(entity_name, []).append(
                    {
                        "activity_name": activity_name,
                        "process_id": process_id,
                    }
                )
        except Exception as e:
            print(f"Neo4j查询失败: {e}")

    for person in personnel_list:
        name = person.get("name", "")
        details = entity_activities_map.get(name, [])
        person["serving_activities_details"] = details
        person["serving_processes"] = list({d["process_id"] for d in details if d["process_id"]})

    return personnel_list

@router.get("/{personnel_id}", response_model=PersonnelResponse)
async def get_personnel_by_id(personnel_id: str):
    db = get_database()
    personnel = await db.personnel.find_one({"_id": ObjectId(personnel_id)})
    if not personnel:
        raise HTTPException(status_code=404, detail="人员不存在")
    personnel["_id"] = str(personnel["_id"])
    _normalize_personnel_for_response(personnel)
    personnel.setdefault("serving_activities_details", [])
    personnel.setdefault("serving_processes", [])
    return personnel

@router.put("/{personnel_id}", response_model=PersonnelResponse)
async def update_personnel(personnel_id: str, personnel: PersonnelUpdate):
    db = get_database()
    driver = get_neo4j_driver()
    
    update_data = {k: v for k, v in personnel.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.personnel.update_one(
        {"_id": ObjectId(personnel_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="人员不存在")
    
    updated_personnel = await db.personnel.find_one({"_id": ObjectId(personnel_id)})
    updated_personnel["_id"] = str(updated_personnel["_id"])
    updated_personnel.setdefault("serving_activities_details", [])
    updated_personnel.setdefault("serving_processes", [])

    # 同步到Neo4j：如果name更新了，同步更新；如果status变为resigned，删除分配关系
    if personnel.name or personnel.status == "resigned":
        try:
            async with driver.session() as session:
                if personnel.name:
                    neo4j_query_name = """
                    MATCH (p:Personnel {id: $personnel_id})
                    SET p.name = $name
                    RETURN p
                    """
                    await session.run(neo4j_query_name, {
                        "personnel_id": personnel_id,
                        "name": personnel.name
                    })
                
                if personnel.status == "resigned":
                    neo4j_query_resign = """
                    MATCH (p:Personnel {id: $personnel_id})-[r:ASSIGNED_TO]->()
                    DELETE r
                    """
                    await session.run(neo4j_query_resign, {
                        "personnel_id": personnel_id
                    })
        except Exception as e:
            print(f"Neo4j同步失败: {e}")
    
    return updated_personnel

@router.delete("/{personnel_id}")
async def delete_personnel(personnel_id: str):
    db = get_database()
    driver = get_neo4j_driver()
    
    result = await db.personnel.delete_one({"_id": ObjectId(personnel_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="人员不存在")
    
    # 同步到Neo4j：删除节点及其所有关系
    neo4j_query = """
    MATCH (p:Personnel {id: $personnel_id})
    DETACH DELETE p
    """
    try:
        async with driver.session() as session:
            await session.run(neo4j_query, {"personnel_id": personnel_id})
    except Exception as e:
        print(f"Neo4j同步失败: {e}")
    
    return {"message": "删除成功"}
