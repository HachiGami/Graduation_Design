import asyncio
import os
import sys

# 将项目根目录添加到 python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_database, connect_to_mongo, close_mongo_connection

async def migrate_activity_statuses():
    # 确保已连接到 MongoDB
    await connect_to_mongo()
    db = get_database()
    
    if db is None:
        print("❌ 无法连接到数据库，请检查配置。")
        return

    # 将所有旧的 completed 状态以及其他非法状态，统一重置为 pending (待机)
    result = await db["activities"].update_many(
        {"status": {"$nin": ["in_progress", "pending"]}},
        {"$set": {"status": "pending"}}
    )
    
    # 额外兼容：如果之前有叫 "待开始" "待处理" 的中文状态，也强行洗回 "pending"
    result_cn = await db["activities"].update_many(
        {"status": {"$in": ["待处理", "待开始", "已完成"]}},
        {"$set": {"status": "pending"}}
    )
    
    print(f"Status migration completed! Reset {result.modified_count + result_cn.modified_count} activity records to pending.")
    
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(migrate_activity_statuses())
