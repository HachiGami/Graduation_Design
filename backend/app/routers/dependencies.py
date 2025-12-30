from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from ..database import get_database
from ..schemas.dependency import DependencyCreate, DependencyUpdate, DependencyResponse
from bson import ObjectId

router = APIRouter(prefix="/api/dependencies", tags=["依赖关系"])

@router.post("", response_model=DependencyResponse)
async def create_dependency(dependency: DependencyCreate):
    db = get_database()
    dependency_dict = dependency.model_dump()
    dependency_dict["created_at"] = datetime.utcnow()
    dependency_dict["updated_at"] = datetime.utcnow()
    
    result = await db.dependencies.insert_one(dependency_dict)
    dependency_dict["_id"] = str(result.inserted_id)
    return dependency_dict

@router.get("", response_model=List[DependencyResponse])
async def get_dependencies():
    db = get_database()
    dependencies = []
    async for dependency in db.dependencies.find():
        dependency["_id"] = str(dependency["_id"])
        dependencies.append(dependency)
    return dependencies

@router.get("/{dependency_id}", response_model=DependencyResponse)
async def get_dependency(dependency_id: str):
    db = get_database()
    dependency = await db.dependencies.find_one({"_id": ObjectId(dependency_id)})
    if not dependency:
        raise HTTPException(status_code=404, detail="依赖关系不存在")
    dependency["_id"] = str(dependency["_id"])
    return dependency

@router.put("/{dependency_id}", response_model=DependencyResponse)
async def update_dependency(dependency_id: str, dependency: DependencyUpdate):
    db = get_database()
    update_data = {k: v for k, v in dependency.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.dependencies.update_one(
        {"_id": ObjectId(dependency_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="依赖关系不存在")
    
    updated_dependency = await db.dependencies.find_one({"_id": ObjectId(dependency_id)})
    updated_dependency["_id"] = str(updated_dependency["_id"])
    return updated_dependency

@router.delete("/{dependency_id}")
async def delete_dependency(dependency_id: str):
    db = get_database()
    result = await db.dependencies.delete_one({"_id": ObjectId(dependency_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="依赖关系不存在")
    return {"message": "删除成功"}
