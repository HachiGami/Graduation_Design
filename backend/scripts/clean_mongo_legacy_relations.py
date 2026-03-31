import asyncio
import sys
import os

# Add the backend directory to the Python path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_database, connect_to_mongo, close_mongo_connection

async def clean_legacy_fields():
    await connect_to_mongo()
    db = get_database()
    
    # 1. 清理人员表残留的分配记录和旧索引
    res_p = await db["personnel"].update_many(
        {}, 
        {"$unset": {"assigned_tasks": "", "_target_activity_indices": ""}}
    )
    print(f"清理了 personnel 集合中 {res_p.modified_count} 条数据的遗留关系字段")

    # 2. 清理资源表 (设备/原料) 残留的分配记录和旧索引
    res_r = await db["resources"].update_many(
        {}, 
        {"$unset": {"serving_activities": "", "_target_activity_indices": ""}}
    )
    print(f"清理了 resources 集合中 {res_r.modified_count} 条数据的遗留关系字段")

    # 3. 清理活动表残留的旧索引 (保留 requirements 需求字段，只删 target 索引)
    res_a = await db["activities"].update_many(
        {},
        {"$unset": {"_target_activity_indices": "", "required_personnel": "", "required_resources": ""}}
    )
    print(f"清理了 activities 集合中 {res_a.modified_count} 条数据的遗留关系字段")

    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(clean_legacy_fields())
