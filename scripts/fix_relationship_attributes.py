import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from neo4j import AsyncGraphDatabase
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "dairy_production"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

async def fix_relationships():
    mongo_client = AsyncIOMotorClient(MONGODB_URL)
    mongo_db = mongo_client[DATABASE_NAME]
    neo4j_driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        print("=" * 60)
        print("开始修复关系属性...")
        print("=" * 60)
        
        # 先获取所有活动的时长
        activity_durations = {}
        async for mongo_activity in mongo_db.activities.find({}):
            if 'estimated_duration' in mongo_activity and 'name' in mongo_activity:
                activity_durations[mongo_activity['name']] = mongo_activity['estimated_duration']
        print(f"\n从 MongoDB 读取了 {len(activity_durations)} 个活动的时长")
        
        async with neo4j_driver.session() as session:
            # 获取所有 USES 关系并分类处理
            print("\n[1] 处理所有 USES 关系...")
            result = await session.run("""
                MATCH (a:Activity)-[r:USES]->(res:Resource)
                RETURN elementId(r) as rel_id, a.name as activity, res.name as resource, res.type as res_type
            """)
            uses_rels = await result.data()
            
            print(f"找到 {len(uses_rels)} 条 USES 关系")
            
            material_count = 0
            equipment_count = 0
            
            for rel in uses_rels:
                res_type = rel['res_type'] or ''
                activity_name = rel['activity']
                resource_name = (rel['resource'] or '').lower()
                
                # 判断是设备还是原料（通过 type 是否包含"设备"来判断）
                is_equipment = '设' in res_type or 'equipment' in res_type.lower()
                
                if is_equipment:
                    # 设备：只保留 duration
                    duration = activity_durations.get(activity_name, 60)
                    await session.run("""
                        MATCH ()-[r]->()
                        WHERE elementId(r) = $rel_id
                        SET r.duration = $duration
                        REMOVE r.quantity
                    """, rel_id=rel['rel_id'], duration=duration)
                    equipment_count += 1
                else:
                    # 原料：只保留 quantity
                    if '瓶' in resource_name or '盖' in resource_name or '容器' in resource_name or 'bottle' in resource_name or 'cap' in resource_name:
                        quantity = 2000
                    elif '牛奶' in resource_name or '水' in resource_name or '乳' in resource_name or 'milk' in resource_name or 'water' in resource_name:
                        quantity = 500
                    else:
                        quantity = 50
                    
                    await session.run("""
                        MATCH ()-[r]->()
                        WHERE elementId(r) = $rel_id
                        SET r.quantity = $quantity
                        REMOVE r.duration
                    """, rel_id=rel['rel_id'], quantity=quantity)
                    material_count += 1
            
            print(f"  [OK] 更新了 {equipment_count} 条设备关系")
            print(f"  [OK] 更新了 {material_count} 条原料关系")
            
            # 2. 人员逻辑：只保留 duration，移除 quantity
            print(f"\n[2] 处理人员关系 (ASSIGNS -> Personnel)")
            
            result = await session.run("""
                MATCH (a:Activity)-[r:ASSIGNS]->(p:Personnel)
                RETURN elementId(r) as rel_id, a.name as activity, p.name as personnel
            """)
            personnel_rels = await result.data()
            
            print(f"找到 {len(personnel_rels)} 条人员关系")
            
            for rel in personnel_rels:
                activity_name = rel['activity']
                duration = activity_durations.get(activity_name, 60)
                
                await session.run("""
                    MATCH ()-[r]->()
                    WHERE elementId(r) = $rel_id
                    SET r.duration = $duration
                    REMOVE r.quantity
                """, rel_id=rel['rel_id'], duration=duration)
            
            print(f"  [OK] 更新了 {len(personnel_rels)} 条人员关系")
            
            # 验证查询
            print("\n" + "=" * 60)
            print("验证结果:")
            print("=" * 60)
            
            print("\n[验证1] 原料关系 (应该只有 quantity):")
            result = await session.run("""
                MATCH (a)-[r:USES]->(res:Resource)
                WHERE NOT res.type CONTAINS '设'
                RETURN avg(r.quantity) as avg_quantity, avg(r.duration) as avg_duration,
                       count(r) as total_count
            """)
            record = await result.single()
            print(f"  avg(quantity) = {record['avg_quantity']}")
            print(f"  avg(duration) = {record['avg_duration']} (应为 None)")
            print(f"  总数 = {record['total_count']}")
            
            print("\n[验证2] 设备关系 (应该只有 duration):")
            result = await session.run("""
                MATCH (a)-[r:USES]->(res:Resource)
                WHERE res.type CONTAINS '设'
                RETURN avg(r.quantity) as avg_quantity, avg(r.duration) as avg_duration,
                       count(r) as total_count
            """)
            record = await result.single()
            print(f"  avg(quantity) = {record['avg_quantity']} (应为 None)")
            print(f"  avg(duration) = {record['avg_duration']}")
            print(f"  总数 = {record['total_count']}")
            
            print("\n[验证3] 人员关系 (应该只有 duration):")
            result = await session.run("""
                MATCH (a)-[r:ASSIGNS]->(p:Personnel)
                RETURN avg(r.quantity) as avg_quantity, avg(r.duration) as avg_duration,
                       count(r) as total_count
            """)
            record = await result.single()
            print(f"  avg(quantity) = {record['avg_quantity']} (应为 None)")
            print(f"  avg(duration) = {record['avg_duration']}")
            print(f"  总数 = {record['total_count']}")
        
        print("\n" + "=" * 60)
        print("[完成] 关系属性修复完成!")
        print("=" * 60)
        
    finally:
        await neo4j_driver.close()
        mongo_client.close()

if __name__ == "__main__":
    asyncio.run(fix_relationships())
