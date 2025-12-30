from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from ..database import get_database
from ..schemas.resource import ResourceCreate, ResourceUpdate, ResourceResponse
from bson import ObjectId

router = APIRouter(prefix="/api/resources", tags=["资源管理"])

@router.post("", response_model=ResourceResponse)
async def create_resource(resource: ResourceCreate):
    db = get_database()
    resource_dict = resource.model_dump()
    resource_dict["created_at"] = datetime.utcnow()
    resource_dict["updated_at"] = datetime.utcnow()
    
    result = await db.resources.insert_one(resource_dict)
    resource_dict["_id"] = str(result.inserted_id)
    return resource_dict

@router.get("", response_model=List[ResourceResponse])
async def get_resources():
    db = get_database()
    resources = []
    async for resource in db.resources.find():
        resource["_id"] = str(resource["_id"])
        resources.append(resource)
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
    return updated_resource

@router.delete("/{resource_id}")
async def delete_resource(resource_id: str):
    db = get_database()
    result = await db.resources.delete_one({"_id": ObjectId(resource_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="资源不存在")
    return {"message": "删除成功"}
