import asyncio
import sys
import os
import random

# 将项目根目录添加到 python 路径，以便导入 app 模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_neo4j, get_neo4j_driver, close_neo4j_connection

async def mock_material_consumption():
    await connect_to_neo4j()
    driver = get_neo4j_driver()
    
    if driver is None:
        print("❌ 无法连接到Neo4j，请检查配置。")
        return

    updated_count = 0
    try:
        async with driver.session() as session:
            # 查找活动与原料之间的依赖关系
            # 匹配 (a:Activity)-[r]->(m:Resource) WHERE m.type = '原料' OR m.resource_type = 'RawMaterial'
            result = await session.run("""
                MATCH (a:Activity)-[r]->(m:Resource)
                WHERE m.type = '原料' OR m.resource_type = 'RawMaterial'
                RETURN a.name AS activity_name, m.name AS material_name, id(r) AS rel_id, type(r) AS rel_type
            """)
            
            relationships = []
            async for record in result:
                relationships.append({
                    "rel_id": record["rel_id"],
                    "activity_name": record["activity_name"],
                    "material_name": record["material_name"],
                    "rel_type": record["rel_type"]
                })
            
            for rel in relationships:
                act_name = rel["activity_name"] or ""
                mat_name = rel["material_name"] or ""
                
                # 智能生成合理数值
                hourly_consumption = random.uniform(1.0, 50.0)
                if "包装" in act_name and "箱" in mat_name:
                    hourly_consumption = random.uniform(50.0, 200.0)
                elif "添加" in act_name and "香精" in mat_name:
                    hourly_consumption = random.uniform(0.1, 2.0)
                elif "奶" in mat_name:
                    hourly_consumption = random.uniform(100.0, 1000.0)
                    
                hourly_consumption = round(hourly_consumption, 2)
                
                # 更新关系属性
                await session.run("""
                    MATCH ()-[r]->()
                    WHERE id(r) = $rel_id
                    SET r.hourly_consumption = $hourly_consumption
                """, {
                    "rel_id": rel["rel_id"],
                    "hourly_consumption": hourly_consumption
                })
                updated_count += 1
                
    except Exception as e:
        print(f"Error: {e}")
        
    print(f"成功更新了 {updated_count} 个关系的 hourly_consumption 属性。")
    
    await close_neo4j_connection()

if __name__ == "__main__":
    asyncio.run(mock_material_consumption())
