import asyncio
from app.database import connect_to_mongo, connect_to_neo4j, get_database, get_neo4j_driver, close_mongo_connection, close_neo4j_connection
from bson import ObjectId

async def clean_all_instances():
    await connect_to_mongo()
    await connect_to_neo4j()
    
    db = get_database()
    neo4j_driver = get_neo4j_driver()
    
    print("🧹 开启全局极简模式，开始双库清理所有实例快照...")

    # 定义克隆数据的特征查询字典
    # 特征说明：模板数据不会带有指向自己的 original_id，也不会带有特定执行批次的 activity_id 等外键
    queries = {
        "activities": {"$or": [{"original_id": {"$exists": True}}, {"activity_id": {"$exists": True}}]},
        "personnel": {"$or": [{"personnel_id": {"$exists": True}}, {"activity_id": {"$exists": True}}, {"original_id": {"$exists": True}}]},
        "resources": {"$or": [{"resource_id": {"$exists": True}}, {"equipment_id": {"$exists": True}}, {"material_id": {"$exists": True}}, {"activity_id": {"$exists": True}}, {"original_id": {"$exists": True}}]}
    }

    total_deleted_mongo = 0
    all_deleted_ids_str = []

    # 1. 扫描并记录需要删除的 Mongo ID
    for collection_name, query in queries.items():
        # 查找所有匹配的克隆文档
        clones = await db[collection_name].find(query).to_list(None)
        if not clones:
            print(f"✅ {collection_name}: 未发现克隆快照，无需清理。")
            continue
            
        clone_ids = [doc["_id"] for doc in clones]
        clone_ids_str = [str(doc["_id"]) for doc in clones]
        all_deleted_ids_str.extend(clone_ids_str)
        
        # 2. 从 MongoDB 中物理删除
        res = await db[collection_name].delete_many({"_id": {"$in": clone_ids}})
        total_deleted_mongo += res.deleted_count
        print(f"✅ {collection_name}: 成功从 MongoDB 删除了 {res.deleted_count} 条克隆快照。")

    # 3. 同步清理 Neo4j 中的图谱节点 (关键步骤)
    if all_deleted_ids_str:
        print(f"🔗 正在同步清理 Neo4j 中的 {len(all_deleted_ids_str)} 个幽灵节点...")
        async with neo4j_driver.session() as session:
            # 使用 UNWIND 批量删除关联的节点及其连线
            cypher_query = """
            UNWIND $ids AS target_id
            MATCH (n) WHERE n.id = target_id
            DETACH DELETE n
            """
            await session.run(cypher_query, ids=all_deleted_ids_str)
        print("✅ Neo4j 幽灵节点及关联连线清理完毕！")
    else:
        print("✅ Neo4j 无需清理。")

    # 4. 打印最终盘点结果
    print("-" * 30)
    print("📊 当前 MongoDB 剩余纯净【基础模板】数据盘点：")
    print(f" - Activities (活动): {await db['activities'].count_documents({})} 条")
    print(f" - Personnel (人员): {await db['personnel'].count_documents({})} 条")
    print(f" - Resources (机/料): {await db['resources'].count_documents({})} 条")
    print("✨ 系统已成功回归 1:1 极简状态！数据双库一致性已保障！")
    
    await close_mongo_connection()
    await close_neo4j_connection()

if __name__ == "__main__":
    asyncio.run(clean_all_instances())
