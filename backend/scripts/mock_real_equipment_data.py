import asyncio
import os
import sys
import random
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# 加载环境变量
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "graduation_design")

MANUFACTURERS = ['西门子', 'ABB', '施耐德', '徐工机械', '三一重工', '中联重科', '通用电气']
MAINTENANCE_OPTIONS = [["明天"], ["1天后"], ["3天后"], ["1天后", "4天后"]]

def get_random_date_past_10_years():
    end = datetime.now()
    start = end - timedelta(days=3650)
    random_date = start + timedelta(days=random.randint(0, 3650))
    return random_date.strftime("%Y-%m-%d")

async def main():
    print(f"Connecting to MongoDB at {MONGODB_URL}...")
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]
    
    # 查找 resources 集合中 type 为 "设备" 的数据
    equipments = await db.resources.find({"type": "设备"}).to_list(length=None)
    print(f"Found {len(equipments)} equipments in resources collection.")
    
    updated_count = 0
    for eq in equipments:
        update_fields = {}
        
        # 补充 manufacturer
        if not eq.get("manufacturer"):
            update_fields["manufacturer"] = random.choice(MANUFACTURERS)
            
        # 补充 production_date
        if not eq.get("production_date"):
            update_fields["production_date"] = get_random_date_past_10_years()
            
        # 清理可能错误生成的 serving_activities
        if "serving_activities" in eq:
            update_fields["serving_activities"] = []
            
        # 10% 的设备生成 upcoming_maintenance
        if random.random() < 0.1:
            update_fields["upcoming_maintenance"] = random.choice(MAINTENANCE_OPTIONS)
        else:
            update_fields["upcoming_maintenance"] = []
            
        if update_fields:
            # 使用 $unset 移除 serving_activities，因为它由 API 动态计算
            unset_fields = {}
            if "serving_activities" in update_fields:
                unset_fields["serving_activities"] = ""
                del update_fields["serving_activities"]
                
            update_query = {}
            if update_fields:
                update_query["$set"] = update_fields
            if unset_fields:
                update_query["$unset"] = unset_fields
                
            if update_query:
                await db.resources.update_one(
                    {"_id": eq["_id"]},
                    update_query
                )
                updated_count += 1
            
    print(f"Successfully updated {updated_count} equipments.")
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
