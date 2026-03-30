import sys
import asyncio
import uuid
from pathlib import Path
from typing import Dict, List

from neo4j import AsyncGraphDatabase

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings


# activity_name 需与 Neo4j 中 Activity.name 完全一致
RESOURCE_MAPPINGS: List[Dict[str, str]] = [
    {"activity_name": "牛奶接收", "resource_name": "生鲜乳", "type": "RawMaterial", "relation": "CONSUMES"},
    {"activity_name": "牛奶接收", "resource_name": "储奶罐", "type": "Equipment", "relation": "USES"},
    {"activity_name": "原料检验", "resource_name": "快检试剂", "type": "RawMaterial", "relation": "CONSUMES"},
    {"activity_name": "牛奶消毒", "resource_name": "巴氏杀菌机", "type": "Equipment", "relation": "USES"},
    {"activity_name": "发酵处理", "resource_name": "发酵剂", "type": "RawMaterial", "relation": "CONSUMES"},
    {"activity_name": "发酵处理", "resource_name": "恒温发酵罐", "type": "Equipment", "relation": "USES"},
    {"activity_name": "灌装", "resource_name": "无菌包装盒", "type": "RawMaterial", "relation": "CONSUMES"},
    {"activity_name": "灌装", "resource_name": "无菌灌装线", "type": "Equipment", "relation": "USES"},
    {"activity_name": "实验室检测", "resource_name": "理化分析仪", "type": "Equipment", "relation": "USES"},
    {"activity_name": "出库装车", "resource_name": "液压叉车", "type": "Equipment", "relation": "USES"},
    {"activity_name": "冷链运输", "resource_name": "冷藏运输车", "type": "Equipment", "relation": "USES"},
    {"activity_name": "商品打包", "resource_name": "环保打包袋", "type": "RawMaterial", "relation": "CONSUMES"},
]


async def add_resources_to_neo4j() -> None:
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    created_or_matched = 0
    not_found_activities = 0
    skipped_invalid_relation = 0

    try:
        print("开始向 Neo4j 注入资源节点与关系...")

        async with driver.session() as session:
            for item in RESOURCE_MAPPINGS:
                relation = item["relation"].upper().strip()
                if relation not in {"USES", "CONSUMES"}:
                    skipped_invalid_relation += 1
                    print(f"[跳过] 非法关系类型: {relation} ({item})")
                    continue

                # 先确认活动存在，避免误创建孤立资源关系
                activity_check = await session.run(
                    "MATCH (a:Activity {name: $activity_name}) RETURN a.name AS name LIMIT 1",
                    {"activity_name": item["activity_name"]},
                )
                record = await activity_check.single()
                if not record:
                    not_found_activities += 1
                    print(f"[跳过] 未找到活动: {item['activity_name']}")
                    continue

                resource_id = str(uuid.uuid4())
                rel_query = f"""
                MATCH (a:Activity {{name: $activity_name}})
                MERGE (r:Resource {{name: $resource_name}})
                ON CREATE SET r.id = $resource_id, r.resource_type = $resource_type
                MERGE (a)-[rel:{relation}]->(r)
                RETURN a.name AS activity_name, type(rel) AS relation_type, r.name AS resource_name
                """

                result = await session.run(
                    rel_query,
                    {
                        "activity_name": item["activity_name"],
                        "resource_name": item["resource_name"],
                        "resource_type": item["type"],
                        "resource_id": resource_id,
                    },
                )
                linked = await result.single()
                if linked:
                    created_or_matched += 1
                    print(
                        f"成功建立连接: [活动] {linked['activity_name']} "
                        f"-({linked['relation_type']})-> [资源] {linked['resource_name']}"
                    )

        print("\n资源注入完成！")
        print(
            f"处理完成: 成功 {created_or_matched} 条, "
            f"活动缺失 {not_found_activities} 条, "
            f"非法关系 {skipped_invalid_relation} 条"
        )
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(add_resources_to_neo4j())
