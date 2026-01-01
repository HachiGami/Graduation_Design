"""
数据迁移脚本：将MongoDB数据同步到Neo4j
根据"轻节点、重关系"原则，只在Neo4j中存储核心标识属性
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from neo4j import AsyncGraphDatabase
from app.config import settings

async def migrate_data():
    # 连接MongoDB
    mongo_client = AsyncIOMotorClient(settings.mongodb_url)
    db = mongo_client[settings.database_name]
    
    # 连接Neo4j
    neo4j_driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    
    try:
        await neo4j_driver.verify_connectivity()
        print("[OK] 成功连接到Neo4j")
        
        # 清空Neo4j中的现有数据（可选，根据需要决定是否执行）
        print("\n清空Neo4j现有数据...")
        async with neo4j_driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        print("[OK] 已清空Neo4j数据")
        
        # 1. 迁移活动节点
        print("\n开始迁移活动节点...")
        activity_count = 0
        async for activity in db.activities.find():
            activity_id = str(activity["_id"])
            activity_name = activity.get("name", "未命名活动")
            
            query = """
            MERGE (a:Activity {id: $activity_id})
            SET a.name = $name
            RETURN a
            """
            
            async with neo4j_driver.session() as session:
                await session.run(query, {
                    "activity_id": activity_id,
                    "name": activity_name
                })
            
            activity_count += 1
            print(f"  [OK] 迁移活动: {activity_name} ({activity_id})")
        
        print(f"[OK] 共迁移 {activity_count} 个活动节点")
        
        # 2. 迁移资源节点
        print("\n开始迁移资源节点...")
        resource_count = 0
        async for resource in db.resources.find():
            resource_id = str(resource["_id"])
            resource_name = resource.get("name", "未命名资源")
            
            query = """
            MERGE (r:Resource {id: $resource_id})
            SET r.name = $name
            RETURN r
            """
            
            async with neo4j_driver.session() as session:
                await session.run(query, {
                    "resource_id": resource_id,
                    "name": resource_name
                })
            
            resource_count += 1
            print(f"  [OK] 迁移资源: {resource_name} ({resource_id})")
        
        print(f"[OK] 共迁移 {resource_count} 个资源节点")
        
        # 3. 迁移人员节点
        print("\n开始迁移人员节点...")
        personnel_count = 0
        async for personnel in db.personnel.find():
            personnel_id = str(personnel["_id"])
            personnel_name = personnel.get("name", "未命名人员")
            
            query = """
            MERGE (p:Personnel {id: $personnel_id})
            SET p.name = $name
            RETURN p
            """
            
            async with neo4j_driver.session() as session:
                await session.run(query, {
                    "personnel_id": personnel_id,
                    "name": personnel_name
                })
            
            personnel_count += 1
            print(f"  [OK] 迁移人员: {personnel_name} ({personnel_id})")
        
        print(f"[OK] 共迁移 {personnel_count} 个人员节点")
        
        # 4. 根据活动的required_resources字段创建USES关系
        print("\n开始创建活动-资源使用关系...")
        usage_count = 0
        async for activity in db.activities.find():
            activity_id = str(activity["_id"])
            required_resources = activity.get("required_resources", [])
            
            for resource_ref in required_resources:
                # 处理不同格式的资源ID（字符串或ObjectId）
                if isinstance(resource_ref, str):
                    from bson import ObjectId
                    try:
                        resource_oid = ObjectId(resource_ref)
                    except:
                        resource_oid = resource_ref
                else:
                    resource_oid = resource_ref
                
                # 验证资源是否存在
                resource = await db.resources.find_one({"_id": resource_oid})
                if not resource:
                    print(f"  [WARN] 警告: 资源 {resource_ref} 不存在，跳过")
                    continue
                
                resource_id_str = str(resource["_id"])
                
                query = """
                MATCH (a:Activity {id: $activity_id})
                MATCH (r:Resource {id: $resource_id})
                MERGE (a)-[u:USES]->(r)
                SET u.quantity = 1,
                    u.unit = 'unit',
                    u.stage = 'production'
                RETURN u
                """
                
                async with neo4j_driver.session() as session:
                    await session.run(query, {
                        "activity_id": activity_id,
                        "resource_id": resource_id_str
                    })
                
                usage_count += 1
                print(f"  [OK] 创建关系: {activity.get('name')} -> {resource.get('name')}")
        
        print(f"[OK] 共创建 {usage_count} 个资源使用关系")
        
        # 5. 根据活动的required_personnel字段创建ASSIGNS关系
        print("\n开始创建活动-人员分配关系...")
        assignment_count = 0
        async for activity in db.activities.find():
            activity_id = str(activity["_id"])
            required_personnel = activity.get("required_personnel", [])
            
            for personnel_ref in required_personnel:
                # 处理不同格式的人员ID（字符串或ObjectId）
                if isinstance(personnel_ref, str):
                    from bson import ObjectId
                    try:
                        personnel_oid = ObjectId(personnel_ref)
                    except:
                        personnel_oid = personnel_ref
                else:
                    personnel_oid = personnel_ref
                
                # 验证人员是否存在
                personnel = await db.personnel.find_one({"_id": personnel_oid})
                if not personnel:
                    print(f"  [WARN] 警告: 人员 {personnel_ref} 不存在，跳过")
                    continue
                
                personnel_id_str = str(personnel["_id"])
                
                query = """
                MATCH (a:Activity {id: $activity_id})
                MATCH (p:Personnel {id: $personnel_id})
                MERGE (a)-[as:ASSIGNS]->(p)
                SET as.role = 'operator'
                RETURN as
                """
                
                async with neo4j_driver.session() as session:
                    await session.run(query, {
                        "activity_id": activity_id,
                        "personnel_id": personnel_id_str
                    })
                
                assignment_count += 1
                print(f"  [OK] 创建关系: {activity.get('name')} -> {personnel.get('name')}")
        
        print(f"[OK] 共创建 {assignment_count} 个人员分配关系")
        
        # 6. 统计Neo4j中的数据
        print("\n统计Neo4j数据...")
        async with neo4j_driver.session() as session:
            result = await session.run("""
                MATCH (a:Activity) 
                RETURN count(a) as activity_count
            """)
            record = await result.single()
            print(f"  Activity节点数: {record['activity_count']}")
            
            result = await session.run("""
                MATCH (r:Resource) 
                RETURN count(r) as resource_count
            """)
            record = await result.single()
            print(f"  Resource节点数: {record['resource_count']}")
            
            result = await session.run("""
                MATCH (p:Personnel) 
                RETURN count(p) as personnel_count
            """)
            record = await result.single()
            print(f"  Personnel节点数: {record['personnel_count']}")
            
            result = await session.run("""
                MATCH ()-[d:DEPENDS_ON]->() 
                RETURN count(d) as dep_count
            """)
            record = await result.single()
            print(f"  DEPENDS_ON关系数: {record['dep_count']}")
            
            result = await session.run("""
                MATCH ()-[u:USES]->() 
                RETURN count(u) as uses_count
            """)
            record = await result.single()
            print(f"  USES关系数: {record['uses_count']}")
            
            result = await session.run("""
                MATCH ()-[as:ASSIGNS]->() 
                RETURN count(as) as assigns_count
            """)
            record = await result.single()
            print(f"  ASSIGNS关系数: {record['assigns_count']}")
        
        print("\n[OK] 数据迁移完成！")
        
    except Exception as e:
        print(f"\n[ERROR] 迁移失败: {e}")
        raise
    finally:
        mongo_client.close()
        await neo4j_driver.close()

if __name__ == "__main__":
    asyncio.run(migrate_data())

