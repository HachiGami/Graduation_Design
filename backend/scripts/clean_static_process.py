import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_mongo, get_database, close_mongo_connection

async def clean_redundant_fields():
    await connect_to_mongo()
    db = get_database()
    res_p = await db["personnel"].update_many({}, {"$unset": {"process_id": "", "domain": ""}})
    res_r = await db["resources"].update_many({}, {"$unset": {"process_id": "", "domain": ""}})
    print(f"[OK] Clean done! Personnel: {res_p.modified_count}, Resources: {res_r.modified_count}")
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(clean_redundant_fields())
