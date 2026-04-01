import asyncio
import sys
import os

# Add backend directory to sys.path to allow importing from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_mongo, connect_to_neo4j, close_mongo_connection, close_neo4j_connection, get_database, get_neo4j_driver

async def sync_entity_to_neo4j(session, label: str, mongo_data: list, properties_mapping: list):
    """
    通用同步函数：将 Mongo 数据以 Merge 方式写入 Neo4j，并删除多余的图节点
    """
    if not mongo_data:
        print(f"⚠️ MongoDB 中没有 {label} 的数据，将清空 Neo4j 中对应的所有节点...")
        await session.run(f"MATCH (n:{label}) DETACH DELETE n")
        return

    # 1. 组装 Neo4j 需要的数据批次
    batch = []
    valid_ids = []
    for doc in mongo_data:
        doc_id = str(doc["_id"])
        valid_ids.append(doc_id)
        
        node_props = {"id": doc_id}
        for prop in properties_mapping:
            node_props[prop] = doc.get(prop, "")
        batch.append(node_props)

    # 2. 动态构建 SET 语句以更新属性
    set_clauses = ", ".join([f"n.{prop} = data.{prop}" for prop in properties_mapping])
    
    # 3. MERGE 节点 (存在则更新，不存在则创建)
    merge_query = f"""
    UNWIND $batch AS data
    MERGE (n:{label} {{id: data.id}})
    SET {set_clauses}
    """
    await session.run(merge_query, batch=batch)

    # 4. 删除孤儿节点 (Neo4j 中有，但 Mongo 中没有的数据)
    delete_query = f"""
    MATCH (n:{label})
    WHERE NOT n.id IN $valid_ids
    DETACH DELETE n
    """
    delete_result = await session.run(delete_query, valid_ids=valid_ids)
    summary = await delete_result.consume()
    deleted_nodes = summary.counters.nodes_deleted
    
    print(f"✅ {label}: 成功同步 {len(batch)} 个节点，清理了 {deleted_nodes} 个孤儿/幽灵节点。")


async def run_sync():
    await connect_to_mongo()
    await connect_to_neo4j()
    
    db = get_database()
    neo4j_driver = get_neo4j_driver()
    
    print("🔄 开始执行 MongoDB -> Neo4j 强制基准对齐同步...")

    # 从 MongoDB 拉取全量真实数据
    equipments = await db["resources"].find({"type": "设备"}).to_list(None)
    materials = await db["resources"].find({"type": "原料"}).to_list(None)
    personnel = await db["personnel"].find({}).to_list(None)
    activities = await db["activities"].find({}).to_list(None)

    async with neo4j_driver.session() as session:
        # 同步设备 (Asset)
        await sync_entity_to_neo4j(session, "Asset", equipments, ["name"])
        
        # 同步原料 (Resource)
        await sync_entity_to_neo4j(session, "Resource", materials, ["name"])
        
        # 同步人员 (Personnel)
        await sync_entity_to_neo4j(session, "Personnel", personnel, ["name", "department", "role"])
        
        # 同步活动 (Activity)
        await sync_entity_to_neo4j(session, "Activity", activities, ["name", "domain", "process_id"])

    print("✨ 所有实体强同步完成，Neo4j 图谱已与 MongoDB 完美一致！")
    
    await close_mongo_connection()
    await close_neo4j_connection()

if __name__ == "__main__":
    asyncio.run(run_sync())
