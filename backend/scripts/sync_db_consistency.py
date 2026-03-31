import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to the Python path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_mongo, connect_to_neo4j, get_database, get_neo4j_driver, close_mongo_connection, close_neo4j_connection

async def sync_databases():
    await connect_to_mongo()
    await connect_to_neo4j()
    
    mongo_db = get_database()
    neo4j_driver = get_neo4j_driver()
    
    # 统一使用 name 作为跨库匹配的唯一键 (Primary Key)
    
    # ==========================================
    # 规则 1：活动 (Activity) - 以 Neo4j 为准
    # ==========================================
    print("开始同步 Activity (Neo4j -> MongoDB)...")
    async with neo4j_driver.session() as session:
        result = await session.run("MATCH (a:Activity) RETURN a.name AS name")
        records = await result.data()
        neo4j_activities = [record["name"] for record in records if record.get("name")]
        
    mongo_activities_cursor = mongo_db["activities"].find({})
    mongo_activities = await mongo_activities_cursor.to_list(length=None)
    mongo_activity_names = [a.get("name") for a in mongo_activities if a.get("name")]
    
    # Mongo 中缺少，需要插入
    missing_in_mongo = set(neo4j_activities) - set(mongo_activity_names)
    if missing_in_mongo:
        new_activities = []
        for name in missing_in_mongo:
            new_activities.append({
                "name": name,
                "description": f"{name}的生产活动 (自动同步生成)",
                "activity_type": "production",
                "status": "pending",
                "domain": "production",
                "process_id": "P001",
                "is_active": True,
                "working_hours": [{"start_time": "08:00", "end_time": "12:00"}, {"start_time": "13:00", "end_time": "17:00"}],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
        await mongo_db["activities"].insert_many(new_activities)
        print(f"MongoDB 补齐了 {len(new_activities)} 个 Activity。")
    else:
        print("MongoDB Activity 无需补齐。")
        
    # Mongo 中多余，需要删除
    extra_in_mongo = set(mongo_activity_names) - set(neo4j_activities)
    if extra_in_mongo:
        await mongo_db["activities"].delete_many({"name": {"$in": list(extra_in_mongo)}})
        print(f"MongoDB 删除了 {len(extra_in_mongo)} 个多余的 Activity。")
    else:
        print("MongoDB Activity 无需删除。")

    # ==========================================
    # 规则 2, 3, 4：人员、原料、设备 - 以 MongoDB 为准
    # ==========================================
    async def sync_entity_to_neo4j(mongo_collection, mongo_query, neo4j_label, entity_name):
        print(f"开始同步 {entity_name} (MongoDB -> Neo4j)...")
        # 拿 Mongo 数据
        cursor = mongo_db[mongo_collection].find(mongo_query)
        docs = await cursor.to_list(length=None)
        mongo_names = [doc.get("name") for doc in docs if doc.get("name")]
        
        async with neo4j_driver.session() as session:
            # Neo4j 缺少，需要插入
            if mongo_names:
                await session.run(f"""
                    UNWIND $names AS name
                    MERGE (n:{neo4j_label} {{name: name}})
                """, names=mongo_names)
            
            # Neo4j 多余，需要删除 (DETACH DELETE 连带关系一起删)
            result = await session.run(f"""
                MATCH (n:{neo4j_label})
                WHERE NOT n.name IN $names
                WITH n, n.name AS deleted_name
                DETACH DELETE n
                RETURN deleted_name
            """, names=mongo_names)
            deleted_records = await result.data()
            deleted_count = len(deleted_records)
            
        print(f"Neo4j 已同步 {entity_name} 数据。删除了 {deleted_count} 个多余节点。")

    # 执行规则 2：Personnel
    await sync_entity_to_neo4j("personnel", {}, "Personnel", "人员")
    
    # 执行规则 3：Material (原料)
    await sync_entity_to_neo4j("resources", {"type": "原料"}, "Material", "原料")
    
    # 执行规则 4：Equipment (设备)
    await sync_entity_to_neo4j("resources", {"type": "设备"}, "Equipment", "设备")

    # ==========================================
    # 规则 5：垃圾清理
    # ==========================================
    print("清理废弃的 Resource 节点...")
    async with neo4j_driver.session() as session:
        res = await session.run("MATCH (n:Resource) DETACH DELETE n RETURN count(n) AS c")
        record = await res.single()
        c = record["c"] if record else 0
        print(f"删除了 {c} 个旧的 Resource 节点。")

    await close_mongo_connection()
    await close_neo4j_connection()

if __name__ == "__main__":
    asyncio.run(sync_databases())
