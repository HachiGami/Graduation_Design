from fastapi import APIRouter
from datetime import datetime, timedelta
from ..database import get_database

router = APIRouter(prefix="/api/demo", tags=["演示数据"])

@router.post("/init")
async def init_demo_data():
    db = get_database()
    
    await db.resources.delete_many({})
    await db.personnel.delete_many({})
    await db.dependencies.delete_many({})
    await db.activities.delete_many({})
    
    resources = [
        {
            "name": "新鲜牛奶",
            "type": "原材料",
            "specification": "A级",
            "supplier": "本地牧场",
            "quantity": 5000,
            "unit": "升",
            "expiry_date": datetime.utcnow() + timedelta(days=2),
            "status": "available",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "消毒设备",
            "type": "设备",
            "specification": "UV-2000",
            "supplier": "工业设备公司",
            "quantity": 2,
            "unit": "台",
            "status": "available",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "包装盒",
            "type": "包装材料",
            "specification": "1L装",
            "supplier": "包装材料厂",
            "quantity": 10000,
            "unit": "个",
            "status": "available",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "冷藏柜",
            "type": "设备",
            "specification": "工业级",
            "supplier": "制冷设备公司",
            "quantity": 5,
            "unit": "台",
            "status": "available",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    personnel = [
        {
            "name": "张三",
            "role": "操作工",
            "responsibility": "负责消毒和加热操作",
            "skills": ["操作设备", "质检"],
            "work_hours": "8:00-17:00",
            "assigned_tasks": [],
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "李四",
            "role": "质检员",
            "responsibility": "负责产品质量检测",
            "skills": ["质检", "安全管理"],
            "work_hours": "8:00-17:00",
            "assigned_tasks": [],
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "王五",
            "role": "包装工",
            "responsibility": "负责产品包装",
            "skills": ["操作设备"],
            "work_hours": "9:00-18:00",
            "assigned_tasks": [],
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    dependencies = [
        {
            "name": "接收到消毒",
            "predecessor_stage": "牛奶接收",
            "successor_stage": "消毒处理",
            "dependency_type": "sequential",
            "time_constraint": 30,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "消毒到加热",
            "predecessor_stage": "消毒处理",
            "successor_stage": "加热",
            "dependency_type": "sequential",
            "time_constraint": 15,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "加热到冷却",
            "predecessor_stage": "加热",
            "successor_stage": "冷却",
            "dependency_type": "sequential",
            "time_constraint": 10,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "冷却到包装",
            "predecessor_stage": "冷却",
            "successor_stage": "包装",
            "dependency_type": "sequential",
            "time_constraint": 20,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    activities = [
        {
            "name": "牛奶消毒处理",
            "description": "对新鲜牛奶进行UV消毒处理",
            "activity_type": "消毒",
            "sop_steps": [
                {"step_number": 1, "description": "检查设备状态", "duration": 5},
                {"step_number": 2, "description": "启动UV消毒设备", "duration": 10},
                {"step_number": 3, "description": "牛奶通过消毒通道", "duration": 30},
                {"step_number": 4, "description": "检测消毒效果", "duration": 10}
            ],
            "estimated_duration": 55,
            "required_resources": [],
            "required_personnel": [],
            "status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "巴氏杀菌",
            "description": "对牛奶进行巴氏杀菌处理",
            "activity_type": "加热",
            "sop_steps": [
                {"step_number": 1, "description": "预热设备至63度", "duration": 10},
                {"step_number": 2, "description": "牛奶加热30分钟", "duration": 30},
                {"step_number": 3, "description": "温度监控", "duration": 5}
            ],
            "estimated_duration": 45,
            "required_resources": [],
            "required_personnel": [],
            "status": "in_progress",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "快速冷却",
            "description": "将牛奶快速冷却至4度",
            "activity_type": "冷却",
            "sop_steps": [
                {"step_number": 1, "description": "转移至冷却设备", "duration": 5},
                {"step_number": 2, "description": "冷却至4度", "duration": 20}
            ],
            "estimated_duration": 25,
            "required_resources": [],
            "required_personnel": [],
            "status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "产品包装",
            "description": "将牛奶装入包装盒",
            "activity_type": "包装",
            "sop_steps": [
                {"step_number": 1, "description": "准备包装材料", "duration": 10},
                {"step_number": 2, "description": "自动灌装", "duration": 40},
                {"step_number": 3, "description": "封口贴标", "duration": 20}
            ],
            "estimated_duration": 70,
            "required_resources": [],
            "required_personnel": [],
            "status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "质量检测",
            "description": "对成品进行质量检测",
            "activity_type": "质检",
            "sop_steps": [
                {"step_number": 1, "description": "抽样检测", "duration": 15},
                {"step_number": 2, "description": "记录数据", "duration": 10}
            ],
            "estimated_duration": 25,
            "required_resources": [],
            "required_personnel": [],
            "status": "completed",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    await db.resources.insert_many(resources)
    await db.personnel.insert_many(personnel)
    await db.dependencies.insert_many(dependencies)
    await db.activities.insert_many(activities)
    
    return {
        "message": "演示数据初始化成功",
        "counts": {
            "resources": len(resources),
            "personnel": len(personnel),
            "dependencies": len(dependencies),
            "activities": len(activities)
        }
    }

