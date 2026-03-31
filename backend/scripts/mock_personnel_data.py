import random
import asyncio
import sys
import os
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

# 将项目根目录添加到 sys.path，以便导入 app.config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import settings

async def mock_personnel_data():
    # 连接 MongoDB
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.database_name]
    collection = db["personnel"]

    # 模拟数据选项
    provinces = ['北京', '上海', '广东', '江苏', '浙江', '山东', '四川', '河南', '湖北', '湖南', '河北', '安徽', '福建', '陕西']
    educations = ['高中', '大专', '本科', '硕士']
    education_weights = [0.1, 0.3, 0.5, 0.1]  # 权重：本科和大专较高

    # 获取所有员工
    cursor = collection.find({})
    count = 0

    async for person in cursor:
        update_fields = {}
        
        # 检查并生成 age
        if not person.get('age'):
            update_fields['age'] = random.randint(22, 55)
        
        # 检查并生成 gender
        if not person.get('gender'):
            update_fields['gender'] = random.choice(['男', '女'])
            
        # 检查并生成 native_place
        if not person.get('native_place'):
            update_fields['native_place'] = random.choice(provinces)
            
        # 检查并生成 hire_date (过去 5 年内)
        if not person.get('hire_date'):
            days_ago = random.randint(0, 365 * 5)
            hire_date = datetime.now() - timedelta(days=days_ago)
            update_fields['hire_date'] = hire_date.strftime('%Y-%m-%d')
            
        # 检查并生成 education
        if not person.get('education'):
            update_fields['education'] = random.choices(educations, weights=education_weights)[0]
            
        # 检查并生成 salary (4000-20000, 500的倍数)
        if not person.get('salary'):
            salary_base = random.randint(4000 // 500, 20000 // 500)
            update_fields['salary'] = salary_base * 500

        # 如果有需要更新的字段，执行更新
        if update_fields:
            await collection.update_one(
                {'_id': person['_id']},
                {'$set': update_fields}
            )
            count += 1

    print(f"成功更新 {count} 名员工")
    client.close()

if __name__ == "__main__":
    asyncio.run(mock_personnel_data())
