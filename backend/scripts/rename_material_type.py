import asyncio
import sys
import os

# 将项目根目录添加到 python 路径，以便导入 app 模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_mongo, get_database, close_mongo_connection

async def rename_material_to_raw():
    # 初始化数据库连接
    await connect_to_mongo()
    db = get_database()
    
    if db is None:
        print("❌ 无法连接到数据库，请检查配置。")
        return

    collection = db["resources"]
    
    # 查找目前存在的“材料”数量
    count_before = await collection.count_documents({"type": "材料"})
    if count_before == 0:
        print("No items with type '材料' found, maybe already updated.")
        await close_mongo_connection()
        return

    print(f"Find {count_before} items with type '材料', starting migration...")
    
    # 执行高效的批量更新
    result = await collection.update_many(
        {"type": "材料"},
        {"$set": {"type": "原料"}}
    )
    
    print(f"Migration completed! Successfully updated {result.modified_count} items from '材料' to '原料'.")
    
    # 关闭数据库连接
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(rename_material_to_raw())
