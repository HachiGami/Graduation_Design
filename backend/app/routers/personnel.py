from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from ..database import get_database, get_neo4j_driver
from ..schemas.personnel import PersonnelCreate, PersonnelUpdate, PersonnelResponse
from bson import ObjectId

router = APIRouter(prefix="/api/personnel", tags=["人员管理"])

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

@router.get("", response_model=List[PersonnelResponse])
async def get_personnel():
    db = get_database()
    personnel_list = []
    try:
        cursor = db.personnel.find()
        async for personnel in cursor:
            personnel["_id"] = str(personnel["_id"])
            personnel_list.append(personnel)
    except Exception as e:
        raise
    
    return personnel_list

@router.get("/{personnel_id}", response_model=PersonnelResponse)
async def get_personnel_by_id(personnel_id: str):
    db = get_database()
    personnel = await db.personnel.find_one({"_id": ObjectId(personnel_id)})
    if not personnel:
        raise HTTPException(status_code=404, detail="人员不存在")
    personnel["_id"] = str(personnel["_id"])
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
    
    # 同步到Neo4j：如果name更新了，同步更新
    if personnel.name:
        neo4j_query = """
        MATCH (p:Personnel {id: $personnel_id})
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
