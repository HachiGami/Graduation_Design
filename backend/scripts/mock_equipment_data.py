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

MANUFACTURERS = ['西门子', 'ABB', '施耐德', '徐工机械', '本地供应商']
ACTIVITIES = ['喷码', '杀菌', '包装', '主生产线', '质检']

def get_random_date_past_10_years():
    end = datetime.now()
    start = end - timedelta(days=3650)
    random_date = start + timedelta(days=random.randint(0, 3650))
    return random_date.strftime("%Y-%m-%d")

def get_random_upcoming_maintenance():
    num_dates = random.randint(0, 2)
    dates = []
    for _ in range(num_dates):
        days_ahead = random.randint(1, 7)
        future_date = datetime.now() + timedelta(days=days_ahead)
        dates.append(future_date.strftime("%Y-%m-%d"))
    return sorted(list(set(dates)))

def get_random_serving_activities():
    num_activities = random.randint(0, 2)
    return random.sample(ACTIVITIES, num_activities)

async def main():
    print(f"Connecting to MongoDB at {MONGODB_URL}...")
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]
    
    # 查找所有设备
    equipments = await db.assets.find({"asset_type": "equipment"}).to_list(length=None)
    print(f"Found {len(equipments)} equipments.")
    
    updated_count = 0
    for eq in equipments:
        update_fields = {}
        
        if not eq.get("manufacturer"):
            update_fields["manufacturer"] = random.choice(MANUFACTURERS)
        if not eq.get("production_date"):
            update_fields["production_date"] = get_random_date_past_10_years()
        if not eq.get("upcoming_maintenance") or len(eq.get("upcoming_maintenance")) == 0:
            update_fields["upcoming_maintenance"] = get_random_upcoming_maintenance()
        if not eq.get("serving_activities") or len(eq.get("serving_activities")) == 0:
            update_fields["serving_activities"] = get_random_serving_activities()
        if not eq.get("process_id"):
            update_fields["process_id"] = random.choice(['P001', 'P002', 'P003'])
            
        if update_fields:
            await db.assets.update_one(
                {"_id": eq["_id"]},
                {"$set": update_fields}
            )
            updated_count += 1
            
    print(f"Successfully updated {updated_count} equipments.")
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
