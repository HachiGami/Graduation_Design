from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from ..database import get_database
from ..schemas.activity import ActivityCreate, ActivityUpdate, ActivityResponse
from bson import ObjectId

router = APIRouter(prefix="/api/activities", tags=["生产活动"])

@router.post("", response_model=ActivityResponse)
async def create_activity(activity: ActivityCreate):
    db = get_database()
    activity_dict = activity.model_dump()
    activity_dict["created_at"] = datetime.utcnow()
    activity_dict["updated_at"] = datetime.utcnow()
    
    result = await db.activities.insert_one(activity_dict)
    activity_dict["_id"] = str(result.inserted_id)
    return activity_dict

@router.get("", response_model=List[ActivityResponse])
async def get_activities():
    db = get_database()
    activities = []
    async for activity in db.activities.find():
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
    return updated_activity

@router.delete("/{activity_id}")
async def delete_activity(activity_id: str):
    db = get_database()
    result = await db.activities.delete_one({"_id": ObjectId(activity_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="生产活动不存在")
    return {"message": "删除成功"}

