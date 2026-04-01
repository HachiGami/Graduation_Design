import asyncio
import sys
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient
from neo4j import AsyncGraphDatabase

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import settings  # noqa: E402


async def sync_resource_ids():
    mongo_client = AsyncIOMotorClient(settings.mongodb_url)
    neo4j_driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    mongo_updated = 0
    neo_created = 0
    total_processed = 0

    try:
        db = mongo_client[settings.database_name]
        resources = await db.resources.find({"type": {"$in": ["设备", "原料"]}}).to_list(None)

        async with neo4j_driver.session() as session:
            for doc in resources:
                total_processed += 1
                rid = str(doc["_id"])
                name = doc.get("name", "")
                rtype = doc.get("type", "")
                label = "Equipment" if rtype == "设备" else "Material"

                match_result = await session.run(
                    f"""
                    MATCH (n:{label} {{name: $name}})
                    RETURN count(n) AS cnt
                    """,
                    {"name": name},
                )
                match_record = await match_result.single()
                cnt = int(match_record["cnt"] or 0) if match_record else 0

                if cnt > 0:
                    update_result = await session.run(
                        f"""
                        MATCH (n:{label} {{name: $name}})
                        SET n.id = $id
                        RETURN count(n) AS touched
                        """,
                        {"name": name, "id": rid},
                    )
                    update_record = await update_result.single()
                    mongo_updated += int(update_record["touched"] or 0) if update_record else 0
                else:
                    create_result = await session.run(
                        f"""
                        CREATE (n:{label} {{id: $id, name: $name}})
                        RETURN count(n) AS created
                        """,
                        {"id": rid, "name": name},
                    )
                    create_record = await create_result.single()
                    neo_created += int(create_record["created"] or 0) if create_record else 0

        print("=== sync_resource_ids 完成 ===")
        print(f"处理资源总数: {total_processed}")
        print(f"按 name 命中并补齐 id 的节点数: {mongo_updated}")
        print(f"Neo4j 中未命中后新创建节点数: {neo_created}")
    finally:
        mongo_client.close()
        await neo4j_driver.close()


if __name__ == "__main__":
    asyncio.run(sync_resource_ids())
