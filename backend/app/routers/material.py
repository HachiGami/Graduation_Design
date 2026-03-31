from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional
from datetime import datetime
from ..database import get_database, get_neo4j_driver
from ..schemas.material import MaterialResponse, MaterialAddStock, MaterialUpdate
from bson import ObjectId

router = APIRouter(prefix="/api/materials", tags=["原料管理"])

def parse_working_hours(working_hours) -> float:
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
    elif isinstance(working_hours, str):
        periods = working_hours.split(",")
        for period in periods:
            parts = period.strip().split("-")
            if len(parts) == 2:
                try:
                    fmt = "%H:%M"
                    td = datetime.strptime(parts[1].strip(), fmt) - datetime.strptime(parts[0].strip(), fmt)
                    total_hours += td.total_seconds() / 3600
                except Exception:
                    pass
    return total_hours

@router.get("", response_model=List[MaterialResponse])
async def get_materials():
    db = get_database()
    driver = get_neo4j_driver()
    
    # 1. 查 Mongo 库存
    materials_cursor = db.resources.find({"type": "原料"})
    materials = []
    async for mat in materials_cursor:
        mat["_id"] = str(mat["_id"])
        materials.append(mat)
        
    # 2. 查 Mongo 活动时效
    activities_cursor = db.activities.find({"status": {"$in": ["运行中", "in_progress"]}})
    activities = {}
    async for act in activities_cursor:
        act_id = str(act["_id"])
        daily_hours = parse_working_hours(act.get("working_hours"))
        activities[act_id] = {
            "name": act.get("name", "未知活动"),
            "daily_hours": daily_hours
        }
        
    # 3. 查 Neo4j 消耗率
    # 查找所有运行中活动与原料的关联
    active_activity_ids = list(activities.keys())
    
    consumption_map = {} # material_id -> list of {activity_id, hourly_consumption}
    
    if active_activity_ids:
        try:
            async with driver.session() as session:
                result = await session.run("""
                    MATCH (a:Activity)-[r]->(m:Resource)
                    WHERE a.id IN $activity_ids AND (m.type = '原料' OR m.resource_type = 'RawMaterial')
                    RETURN a.id AS activity_id, m.id AS material_id, r.hourly_consumption AS hourly_consumption
                """, {"activity_ids": active_activity_ids})
                
                async for record in result:
                    mat_id = record["material_id"]
                    act_id = record["activity_id"]
                    hc = record["hourly_consumption"]
                    if hc is None:
                        hc = 0.0
                    else:
                        hc = float(hc)
                        
                    if mat_id not in consumption_map:
                        consumption_map[mat_id] = []
                    consumption_map[mat_id].append({
                        "activity_id": act_id,
                        "hourly_consumption": hc
                    })
        except Exception as e:
            print(f"Neo4j查询失败: {e}")

    # 4. 核心计算逻辑
    response_data = []
    for mat in materials:
        mat_id = mat["_id"]
        daily_consumption = 0.0
        serving_activities = []
        
        if mat_id in consumption_map:
            for usage in consumption_map[mat_id]:
                act_id = usage["activity_id"]
                hc = usage["hourly_consumption"]
                act_info = activities.get(act_id)
                if act_info:
                    daily_consumption += hc * act_info["daily_hours"]
                    serving_activities.append({
                        "activity_name": act_info["name"],
                        "hourly_consumption": hc
                    })
                    
        quantity = float(mat.get("quantity", 0))
        if daily_consumption > 0:
            remaining_days = quantity / daily_consumption
        else:
            remaining_days = -1.0 # 表示充足
            
        mat_response = MaterialResponse(
            _id=mat_id,
            name=mat.get("name", ""),
            type=mat.get("type", "原料"),
            specification=mat.get("specification"),
            supplier=mat.get("supplier"),
            manufacturer=mat.get("manufacturer"),
            quantity=quantity,
            unit=mat.get("unit", ""),
            status=mat.get("status"),
            domain=mat.get("domain"),
            process_id=mat.get("process_id"),
            daily_consumption=daily_consumption,
            remaining_days=remaining_days,
            serving_activities=serving_activities
        )
        response_data.append(mat_response)
        
    return response_data

@router.post("/{material_id}/add_stock", response_model=MaterialResponse)
async def add_stock(material_id: str, payload: MaterialAddStock):
    db = get_database()
    obj_id = ObjectId(material_id)
    
    material = await db.resources.find_one({"_id": obj_id, "type": "原料"})
    if not material:
        raise HTTPException(status_code=404, detail="原料不存在")
        
    new_quantity = float(material.get("quantity", 0)) + payload.add_amount
    
    await db.resources.update_one(
        {"_id": obj_id},
        {"$set": {"quantity": new_quantity, "updated_at": datetime.utcnow()}}
    )
    
    # 重新获取完整信息需要调用 get_materials 逻辑，但为了简化，这里只返回基础信息或重新计算
    # 简单起见，直接返回基础信息，前端重新拉取列表
    updated_material = await db.resources.find_one({"_id": obj_id})
    updated_material["_id"] = str(updated_material["_id"])
    
    return MaterialResponse(
        _id=updated_material["_id"],
        name=updated_material.get("name", ""),
        type=updated_material.get("type", "原料"),
        quantity=new_quantity,
        unit=updated_material.get("unit", ""),
        daily_consumption=0.0, # 简化返回
        remaining_days=-1.0,
        serving_activities=[]
    )

@router.put("/{material_id}", response_model=MaterialResponse)
async def update_material(material_id: str, payload: MaterialUpdate):
    db = get_database()
    obj_id = ObjectId(material_id)
    
    material = await db.resources.find_one({"_id": obj_id, "type": "原料"})
    if not material:
        raise HTTPException(status_code=404, detail="原料不存在")
        
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="没有提供更新数据")
        
    update_data["updated_at"] = datetime.utcnow()
    
    await db.resources.update_one(
        {"_id": obj_id},
        {"$set": update_data}
    )
    
    updated_material = await db.resources.find_one({"_id": obj_id})
    updated_material["_id"] = str(updated_material["_id"])
    
    return MaterialResponse(
        _id=updated_material["_id"],
        name=updated_material.get("name", ""),
        type=updated_material.get("type", "原料"),
        quantity=updated_material.get("quantity", 0),
        unit=updated_material.get("unit", ""),
        daily_consumption=0.0,
        remaining_days=-1.0,
        serving_activities=[]
    )
