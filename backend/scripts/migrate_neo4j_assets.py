import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from neo4j import AsyncGraphDatabase
from app.config import settings

async def migrate_neo4j_to_assets():
    """
    清理 Neo4j 旧数据，与 MongoDB assets 集合同步
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
        print("Neo4j 资产节点重建开始")
        print("=" * 60)
        
        async with driver.session() as session:
            # 步骤1: 删除所有旧的 Resource 节点和关系
            print("\n删除旧的 Resource 节点...")
            result = await session.run("MATCH (r:Resource) DETACH DELETE r")
            await result.consume()
            
            print("删除旧的 USES 关系...")
            result = await session.run("MATCH ()-[u:USES]->() DELETE u")
            await result.consume()
            
            # 步骤2: 从 MongoDB 读取所有 assets，重建 Neo4j 节点
            equipment_count = 0
            async for asset in db.assets.find({"asset_type": "equipment"}):
                asset_id = str(asset["_id"])
                await session.run("""
                    CREATE (e:Equipment {
                        id: $id,
                        name: $name,
                        model: $model,
                        status: $status
                    })
                """, {
                    "id": asset_id,
                    "name": asset["name"],
                    "model": asset["model"],
                    "status": asset.get("status", "idle")
                })
                equipment_count += 1
                if equipment_count % 10 == 0:
                    print(f"  已创建 {equipment_count} 个Equipment节点...")
            
            material_count = 0
            async for asset in db.assets.find({"asset_type": "material"}):
                asset_id = str(asset["_id"])
                await session.run("""
                    CREATE (m:Material {
                        id: $id,
                        name: $name,
                        quantity: $quantity,
                        unit: $unit
                    })
                """, {
                    "id": asset_id,
                    "name": asset["name"],
                    "quantity": asset.get("quantity", 0),
                    "unit": asset.get("unit", "")
                })
                material_count += 1
                if material_count % 10 == 0:
                    print(f"  已创建 {material_count} 个Material节点...")
            
            # 验证结果
            print("\n验证迁移结果:")
            result = await session.run("MATCH (m:Material) RETURN count(m) as materials")
            record = await result.single()
            materials = record["materials"]
            
            result = await session.run("MATCH (e:Equipment) RETURN count(e) as equipments")
            record = await result.single()
            equipments = record["equipments"]
            
            result = await session.run("MATCH (r:Resource) RETURN count(r) as old_resources")
            record = await result.single()
            old_resources = record["old_resources"]
            
            result = await session.run("MATCH ()-[u:USES]->() RETURN count(u) as old_uses")
            record = await result.single()
            old_uses = record["old_uses"]
            
            print(f"  - Material 节点数: {materials}")
            print(f"  - Equipment 节点数: {equipments}")
            print(f"  - 旧 Resource 节点数 (应为0): {old_resources}")
            print(f"  - 旧 USES 关系数 (应为0): {old_uses}")
        
        print("\n" + "=" * 60)
        print("Neo4j 资产节点重建完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mongo_client.close()
        await driver.close()

if __name__ == "__main__":
    asyncio.run(migrate_neo4j_to_assets())
