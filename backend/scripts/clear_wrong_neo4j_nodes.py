import asyncio
import os
import sys

# 将项目根目录添加到 sys.path 以确保能导入 app 模块
# 脚本在 backend/scripts/，app 在 backend/app/
# 所以需要将 backend/ 目录添加到 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from app.database import connect_to_neo4j, close_neo4j_connection, get_neo4j_driver

async def clear_wrong_nodes():
    print("Preparing to clear wrong label nodes (Asset and Resource) in Neo4j...")
    
    # 首先需要连接到 Neo4j
    await connect_to_neo4j()
    neo4j_driver = get_neo4j_driver()
    
    try:
        async with neo4j_driver.session() as session:
            # 使用 DETACH DELETE 彻底删除错误的节点，并自动销毁与它们相关的连线
            query = """
            MATCH (n)
            WHERE n:Asset OR n:Resource
            DETACH DELETE n
            """
            result = await session.run(query)
            summary = await result.consume()
            
            deleted_nodes = summary.counters.nodes_deleted
            deleted_relationships = summary.counters.relationships_deleted
            
            print(f"Cleanup completed!")
            print(f" - Deleted {deleted_nodes} wrong nodes (Asset/Resource).")
            print(f" - Cascadely deleted {deleted_relationships} associated relationships.")
    finally:
        # 确保关闭连接
        await close_neo4j_connection()

if __name__ == "__main__":
    asyncio.run(clear_wrong_nodes())
