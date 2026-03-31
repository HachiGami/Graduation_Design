import asyncio
import sys
import os

# 将项目根目录添加到 python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_mongo, get_database

async def upgrade_sops():
    await connect_to_mongo()
    db = get_database()
    activities = await db["activities"].find({"sop_steps": {"$exists": True}}).to_list(None)
    
    updated_count = 0
    for act in activities:
        old_sops = act.get("sop_steps", [])
        new_sops = []
        
        # 如果旧数据是字符串列表，则进行转换
        if old_sops and isinstance(old_sops, list) and len(old_sops) > 0 and isinstance(old_sops[0], str):
            for step_str in old_sops:
                # 尝试去掉旧数据里可能包含的 "(0分钟)" 等字样
                clean_str = step_str.split(" (")[0] if " (" in step_str else step_str
                new_sops.append({"content": clean_str, "duration": 0})
            
            await db["activities"].update_one(
                {"_id": act["_id"]},
                {"$set": {"sop_steps": new_sops}}
            )
            updated_count += 1
            
    print(f"SOP structure upgrade completed! Migrated {updated_count} activity SOP data.")

if __name__ == "__main__":
    asyncio.run(upgrade_sops())
