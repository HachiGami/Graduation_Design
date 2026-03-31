import asyncio
import os
import sys
import random
from datetime import datetime, timedelta

# 添加项目根目录到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_mongo, get_database, close_mongo_connection

async def force_update_equipments():
    await connect_to_mongo()
    db = get_database()  # 获取 MongoDB 实例
    collection = db["resources"]
    
    # 查询所有设备
    cursor = collection.find({"type": "设备"})
    equipments = await cursor.to_list(length=None)
    
    if not equipments:
        print("❌ 未找到任何设备数据，请检查 resources 集合。")
        await close_mongo_connection()
        return

    updated_count = 0
    for eq in equipments:
        # 1. 生产厂家：优先使用原有的 supplier，否则随机生成
        manufacturer = eq.get("supplier")
        if not manufacturer or manufacturer == "":
            manufacturer = random.choice(["西门子", "ABB", "施耐德", "徐工机械", "本地设备厂"])
            
        # 2. 生产时间：过去 5-10 年内随机
        days_ago = random.randint(365 * 2, 365 * 10)
        prod_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        # 3. 未来检修日期：**所有设备必须生成该字段**。10%概率有具体日期，90%概率为空数组 []
        if random.random() < 0.15: # 15% 概率需要检修
            m_date = random.choice([["明天"], ["1天后"], ["3天后"], ["1天后", "5天后"]])
        else:
            m_date = [] # 必须初始化为空数组，不能是不存在
            
        # 强制更新 MongoDB
        await collection.update_one(
            {"_id": eq["_id"]},
            {"$set": {
                "manufacturer": manufacturer,
                "production_date": prod_date,
                "upcoming_maintenance": m_date
            }}
        )
        updated_count += 1
        
    print(f"Update Success: {updated_count} equipments updated with manufacturer, production_date and upcoming_maintenance.")
    await close_mongo_connection()

if __name__ == "__main__":
    # 设置标准输出编码为 UTF-8 避免 Windows 环境下的编码错误
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    asyncio.run(force_update_equipments())
