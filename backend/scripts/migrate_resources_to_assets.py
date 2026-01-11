import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from neo4j import AsyncGraphDatabase
from app.config import settings

async def migrate_resources_to_assets():
    """
    将现有 resources 集合按 quantity 拆分为独立的 asset 文档
    """
    # 连接数据库
    mongo_client = AsyncIOMotorClient(settings.mongodb_url)
    db = mongo_client[settings.database_name]
    
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    
    try:
        print("=" * 60)
        print("MongoDB 资产实例化迁移开始")
        print("=" * 60)
        
        # 步骤1: 读取所有设备类型的资源
        equipment_resources = []
        async for res in db.resources.find({"type": "equipment"}):
            equipment_resources.append(res)
        
        print(f"\n找到 {len(equipment_resources)} 个设备类型资源")
        
        migrated_assets = []
        
        # 步骤2: 处理设备资源
        for resource in equipment_resources:
            resource_id = str(resource["_id"])
            model = resource["name"]  # 原 name 变为 model
            quantity = int(resource.get("quantity", 1))
            
            print(f"\n处理设备: {model} (数量: {quantity})")
            
            # 根据 quantity 生成独立文档
            for i in range(quantity):
                asset_doc = {
                    "model": model,
                    "name": f"{model}-{i+1:02d}",  # 生成个体名称，如"泵-01"
                    "asset_type": "equipment",
                    "specification": resource.get("specification", ""),
                    "supplier": resource.get("supplier", ""),
                    "status": "idle",
                    "quantity": 1,  # 设备固定为 1
                    "unit": resource.get("unit", "台"),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                # 插入 MongoDB
                result = await db.assets.insert_one(asset_doc)
                asset_id = str(result.inserted_id)
                
                # 同步到 Neo4j
                neo4j_query = """
                MERGE (e:Equipment {id: $asset_id})
                SET e.name = $name, 
                    e.model = $model,
                    e.status = $status
                """
                async with driver.session() as session:
                    await session.run(neo4j_query, {
                        "asset_id": asset_id,
                        "name": asset_doc["name"],
                        "model": asset_doc["model"],
                        "status": "idle"
                    })
                
                migrated_assets.append(asset_id)
                print(f"  创建资产实例: {asset_doc['name']} (ID: {asset_id})")
            
            # 删除原资源文档
            await db.resources.delete_one({"_id": resource["_id"]})
            print(f"  删除原资源文档: {resource_id}")
        
        # 步骤3: 原料类型保持不变（无需拆分）
        material_resources = []
        async for material in db.resources.find({"type": "material"}):
            material_resources.append(material)
        
        print(f"\n找到 {len(material_resources)} 个原料类型资源")
        
        for material in material_resources:
            material_id = str(material["_id"])
            asset_doc = {
                "model": material["name"],
                "name": material["name"],  # 原料不需要个体编号
                "asset_type": "material",
                "specification": material.get("specification", ""),
                "supplier": material.get("supplier", ""),
                "status": "available",
                "quantity": material.get("quantity", 0),
                "unit": material.get("unit", ""),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await db.assets.insert_one(asset_doc)
            asset_id = str(result.inserted_id)
            
            # 同步到 Neo4j
            neo4j_query = """
            MERGE (m:Material {id: $asset_id})
            SET m.name = $name, m.quantity = $quantity, m.unit = $unit
            """
            async with driver.session() as session:
                await session.run(neo4j_query, {
                    "asset_id": asset_id,
                    "name": asset_doc["name"],
                    "quantity": asset_doc["quantity"],
                    "unit": asset_doc["unit"]
                })
            
            await db.resources.delete_one({"_id": material["_id"]})
            print(f"  迁移原料: {asset_doc['name']} (ID: {asset_id})")
        
        print("\n" + "=" * 60)
        print(f"迁移完成统计:")
        print(f"  - 生成设备资产实例: {len(migrated_assets)} 个")
        print(f"  - 迁移原料资产: {len(material_resources)} 个")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mongo_client.close()
        await driver.close()

if __name__ == "__main__":
    asyncio.run(migrate_resources_to_assets())
