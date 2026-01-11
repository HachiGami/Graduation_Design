from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from ..database import get_database, get_neo4j_driver
from ..schemas.asset import AssetCreate, AssetUpdate, AssetResponse

router = APIRouter(prefix="/api/assets", tags=["资产管理"])

@router.post("", response_model=AssetResponse)
async def create_asset(asset: AssetCreate):
    """创建资产"""
    db = get_database()
    driver = get_neo4j_driver()
    
    asset_dict = asset.model_dump()
    asset_dict["created_at"] = datetime.utcnow()
    asset_dict["updated_at"] = datetime.utcnow()
    
    result = await db.assets.insert_one(asset_dict)
    asset_id = str(result.inserted_id)
    asset_dict["_id"] = asset_id
    
    # 同步到Neo4j
    try:
        async with driver.session() as session:
            if asset.asset_type == "equipment":
                await session.run("""
                    CREATE (e:Equipment {
                        id: $id,
                        name: $name,
                        model: $model,
                        status: $status
                    })
                """, {
                    "id": asset_id,
                    "name": asset.name,
                    "model": asset.model,
                    "status": asset.status
                })
            elif asset.asset_type == "material":
                await session.run("""
                    CREATE (m:Material {
                        id: $id,
                        name: $name,
                        quantity: $quantity,
                        unit: $unit
                    })
                """, {
                    "id": asset_id,
                    "name": asset.name,
                    "quantity": asset.quantity or 0,
                    "unit": asset.unit or ""
                })
    except Exception as e:
        print(f"Neo4j同步失败: {e}")
    
    return asset_dict

@router.get("", response_model=List[AssetResponse])
async def get_assets(
    asset_type: Optional[str] = Query(None, description="按类型筛选 (equipment/material)"),
    model: Optional[str] = Query(None, description="按型号筛选"),
    status: Optional[str] = Query(None, description="按状态筛选")
):
    """查询资产列表（全厂共享资源池）"""
    db = get_database()
    
    query_filter = {}
    if asset_type:
        query_filter["asset_type"] = asset_type
    if model:
        query_filter["model"] = model
    if status:
        query_filter["status"] = status
    
    assets = []
    async for asset in db.assets.find(query_filter):
        asset["_id"] = str(asset["_id"])
        assets.append(asset)
    
    return assets

@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(asset_id: str):
    """获取单个资产详情"""
    db = get_database()
    
    if not ObjectId.is_valid(asset_id):
        raise HTTPException(status_code=400, detail="无效的资产ID")
    
    asset = await db.assets.find_one({"_id": ObjectId(asset_id)})
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    asset["_id"] = str(asset["_id"])
    return asset

@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(asset_id: str, asset: AssetUpdate):
    """更新资产"""
    db = get_database()
    driver = get_neo4j_driver()
    
    if not ObjectId.is_valid(asset_id):
        raise HTTPException(status_code=400, detail="无效的资产ID")
    
    update_data = {k: v for k, v in asset.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.assets.update_one(
        {"_id": ObjectId(asset_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    updated_asset = await db.assets.find_one({"_id": ObjectId(asset_id)})
    updated_asset["_id"] = str(updated_asset["_id"])
    
    # 同步到Neo4j
    try:
        async with driver.session() as session:
            if updated_asset["asset_type"] == "equipment":
                await session.run("""
                    MATCH (e:Equipment {id: $id})
                    SET e.name = $name,
                        e.model = $model,
                        e.status = $status
                """, {
                    "id": asset_id,
                    "name": updated_asset["name"],
                    "model": updated_asset["model"],
                    "status": updated_asset["status"]
                })
            elif updated_asset["asset_type"] == "material":
                await session.run("""
                    MATCH (m:Material {id: $id})
                    SET m.name = $name,
                        m.quantity = $quantity,
                        m.unit = $unit
                """, {
                    "id": asset_id,
                    "name": updated_asset["name"],
                    "quantity": updated_asset.get("quantity", 0),
                    "unit": updated_asset.get("unit", "")
                })
    except Exception as e:
        print(f"Neo4j同步失败: {e}")
    
    return updated_asset

@router.delete("/{asset_id}")
async def delete_asset(asset_id: str):
    """删除资产"""
    db = get_database()
    driver = get_neo4j_driver()
    
    if not ObjectId.is_valid(asset_id):
        raise HTTPException(status_code=400, detail="无效的资产ID")
    
    result = await db.assets.delete_one({"_id": ObjectId(asset_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    # 同步到Neo4j
    try:
        async with driver.session() as session:
            await session.run("""
                MATCH (n {id: $id})
                WHERE n:Equipment OR n:Material
                DETACH DELETE n
            """, {"id": asset_id})
    except Exception as e:
        print(f"Neo4j同步失败: {e}")
    
    return {"message": "删除成功"}

@router.post("/allocate")
async def allocate_asset(
    activity_id: str = Query(..., description="活动ID"),
    asset_id: str = Query(..., description="资产ID"),
    rate: Optional[float] = Query(None, description="消耗速率（仅原料）")
):
    """分配资产给活动"""
    db = get_database()
    driver = get_neo4j_driver()
    
    if not ObjectId.is_valid(asset_id):
        raise HTTPException(status_code=400, detail="无效的资产ID")
    
    # 更新 MongoDB status
    result = await db.assets.update_one(
        {"_id": ObjectId(asset_id)},
        {"$set": {"status": "in_use", "updated_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    # 获取资产信息
    asset = await db.assets.find_one({"_id": ObjectId(asset_id)})
    
    # 创建 Neo4j 关系
    try:
        async with driver.session() as session:
            if asset["asset_type"] == "equipment":
                await session.run("""
                    MATCH (a:Activity {id: $activity_id})
                    MATCH (e:Equipment {id: $asset_id})
                    MERGE (a)-[o:OCCUPIES]->(e)
                """, {"activity_id": activity_id, "asset_id": asset_id})
            
            elif asset["asset_type"] == "material":
                await session.run("""
                    MATCH (a:Activity {id: $activity_id})
                    MATCH (m:Material {id: $asset_id})
                    MERGE (a)-[c:CONSUMES]->(m)
                    SET c.consumption_rate_per_day = $rate,
                        c.unit = $unit
                """, {
                    "activity_id": activity_id,
                    "asset_id": asset_id,
                    "rate": rate or 0,
                    "unit": asset.get("unit", "")
                })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建关系失败: {str(e)}")
    
    return {"message": "分配成功"}

@router.post("/release")
async def release_asset(
    activity_id: str = Query(..., description="活动ID"),
    asset_id: str = Query(..., description="资产ID")
):
    """释放资产（活动完成时调用）"""
    db = get_database()
    driver = get_neo4j_driver()
    
    if not ObjectId.is_valid(asset_id):
        raise HTTPException(status_code=400, detail="无效的资产ID")
    
    # 更新 MongoDB status
    result = await db.assets.update_one(
        {"_id": ObjectId(asset_id), "asset_type": "equipment"},
        {"$set": {"status": "idle", "updated_at": datetime.utcnow()}}
    )
    
    # 删除 Neo4j 关系
    try:
        async with driver.session() as session:
            await session.run("""
                MATCH (a:Activity {id: $activity_id})-[r]->(asset {id: $asset_id})
                WHERE type(r) IN ['OCCUPIES', 'CONSUMES']
                DELETE r
            """, {"activity_id": activity_id, "asset_id": asset_id})
    except Exception as e:
        print(f"Neo4j关系删除失败: {e}")
    
    return {"message": "释放成功"}
