"""
多流程测试数据种子脚本
一键初始化 MongoDB + Neo4j 数据
"""
import asyncio
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from neo4j import AsyncGraphDatabase
from bson import ObjectId
import random

# 数据库配置
MONGODB_URL = "mongodb://localhost:27017"
MONGODB_DB = "dairy_production"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"


async def clear_all_data(mongo_client, neo4j_driver):
    """清空所有数据"""
    print("清空现有数据...")
    db = mongo_client[MONGODB_DB]
    
    # 清空MongoDB
    await db.activities.delete_many({})
    await db.resources.delete_many({})
    await db.personnel.delete_many({})
    
    # 清空Neo4j
    async with neo4j_driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")
    
    print("[OK] 数据清空完成")


async def create_and_link_personnel(db, neo4j_driver, personnel_list, activity_ids, process_id, domain):
    """创建人员并关联到活动"""
    if not personnel_list:
        return

    # MongoDB 插入
    for p in personnel_list:
        p.update({
            "process_id": process_id,
            "domain": domain,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
    
    result = await db.personnel.insert_many(personnel_list)
    personnel_ids = [str(id) for id in result.inserted_ids]
    
    # Neo4j 同步
    for idx, p in enumerate(personnel_list):
        async with neo4j_driver.session() as session:
            await session.run(
                """
                MERGE (p:Personnel {id: $id})
                SET p.name = $name, p.role = $role, p.department = $department
                """,
                id=personnel_ids[idx],
                name=p["name"],
                role=p["role"],
                department=p.get("department", "General")
            )
            
    # 确保每个活动都有人员，循环分配
    for i, activity_id in enumerate(activity_ids):
        # 每个活动至少分配 1-2 个人
        num_to_assign = 2 if len(personnel_ids) >= 2 else 1
        for j in range(num_to_assign):
            p_idx = (i + j) % len(personnel_ids)
            async with neo4j_driver.session() as session:
                await session.run(
                    """
                    MATCH (a:Activity {id: $activity_id})
                    MATCH (p:Personnel {id: $personnel_id})
                    MERGE (a)-[r:ASSIGNS]->(p)
                    SET r.role = 'operator', r.created_at = datetime()
                    """,
                    activity_id=activity_id,
                    personnel_id=personnel_ids[p_idx]
                )
    
    relation_count = len(activity_ids) * min(2, len(personnel_ids)) if len(personnel_ids) >= 2 else len(activity_ids)
    print(f"  - Created {len(personnel_list)} personnel, {relation_count} ASSIGNS relations")


async def create_and_link_resources(db, neo4j_driver, resource_list, activity_ids, process_id, domain):
    """创建资源（设备/材料）并关联到活动"""
    if not resource_list:
        return

    # MongoDB 插入
    for r in resource_list:
        r.update({
            "process_id": process_id,
            "domain": domain,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
    
    result = await db.resources.insert_many(resource_list)
    resource_ids = [str(id) for id in result.inserted_ids]
    
    # Neo4j 同步
    for idx, r in enumerate(resource_list):
        async with neo4j_driver.session() as session:
            await session.run(
                """
                MERGE (r:Resource {id: $id})
                SET r.name = $name, r.type = $type
                """,
                id=resource_ids[idx],
                name=r["name"],
                type=r["type"]
            )

    # 先按照指定的 target_activity_indices 分配
    uses_count = 0
    for i, r in enumerate(resource_list):
        target_indices = r.get("_target_activity_indices", [])
        if not target_indices:
            # 默认分配给某个活动，避免孤立
            target_indices = [i % len(activity_ids)]
            
        for act_idx in target_indices:
            if act_idx < len(activity_ids):
                async with neo4j_driver.session() as session:
                    await session.run(
                        """
                        MATCH (a:Activity {id: $activity_id})
                        MATCH (r:Resource {id: $resource_id})
                        MERGE (a)-[u:USES]->(r)
                        SET u.quantity = 1, u.unit = 'unit', u.stage = $domain
                        """,
                        activity_id=activity_ids[act_idx],
                        resource_id=resource_ids[i],
                        domain=domain
                    )
                    uses_count += 1
    
    # 确保每个活动都至少有一个资源，循环补充
    for i, activity_id in enumerate(activity_ids):
        r_idx = i % len(resource_ids)
        async with neo4j_driver.session() as session:
            # 使用 MERGE 避免重复
            await session.run(
                """
                MATCH (a:Activity {id: $activity_id})
                MATCH (r:Resource {id: $resource_id})
                MERGE (a)-[u:USES]->(r)
                ON CREATE SET u.quantity = 1, u.unit = 'unit', u.stage = $domain
                """,
                activity_id=activity_id,
                resource_id=resource_ids[r_idx],
                domain=domain
            )
    
    print(f"  - Created {len(resource_list)} resources, ensured all activities have resources")


async def create_production_p001(mongo_client, neo4j_driver):
    """生产流程 - P001"""
    print("\n创建生产流程 P001...")
    db = mongo_client[MONGODB_DB]
    
    activities = [
        {
            "name": "牛奶接收",
            "description": "接收新鲜牛奶并进行初步检查",
            "activity_type": "接收",
            "sop_steps": [
                {"step_number": 1, "description": "检查运输车辆", "duration": 10},
                {"step_number": 2, "description": "测量温度", "duration": 5},
                {"step_number": 3, "description": "卸货", "duration": 20}
            ],
            "estimated_duration": 35,
            "duration_minutes": 35,
            "status": "completed",
            "domain": "production",
            "process_id": "P001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "原料检验",
            "description": "对原料进行质量检验",
            "activity_type": "质检",
            "sop_steps": [
                {"step_number": 1, "description": "取样", "duration": 10},
                {"step_number": 2, "description": "化验", "duration": 30},
                {"step_number": 3, "description": "记录数据", "duration": 10}
            ],
            "estimated_duration": 50,
            "duration_minutes": 45,
            "status": "completed",
            "domain": "production",
            "process_id": "P001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "牛奶消毒",
            "description": "对牛奶进行巴氏消毒",
            "activity_type": "消毒",
            "sop_steps": [
                {"step_number": 1, "description": "预热设备", "duration": 15},
                {"step_number": 2, "description": "消毒处理", "duration": 30},
                {"step_number": 3, "description": "冷却", "duration": 20}
            ],
            "estimated_duration": 65,
            "duration_minutes": 60,
            "status": "in_progress",
            "domain": "production",
            "process_id": "P001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "灌装",
            "description": "将牛奶灌装到容器中",
            "activity_type": "灌装",
            "sop_steps": [
                {"step_number": 1, "description": "准备容器", "duration": 10},
                {"step_number": 2, "description": "自动灌装", "duration": 40}
            ],
            "estimated_duration": 50,
            "status": "pending",
            "domain": "production",
            "process_id": "P001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "包装",
            "description": "产品包装和贴标",
            "activity_type": "包装",
            "sop_steps": [
                {"step_number": 1, "description": "封口", "duration": 20},
                {"step_number": 2, "description": "贴标", "duration": 15},
                {"step_number": 3, "description": "装箱", "duration": 25}
            ],
            "estimated_duration": 60,
            "status": "pending",
            "domain": "production",
            "process_id": "P001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "入库",
            "description": "成品入库存储",
            "activity_type": "入库",
            "sop_steps": [
                {"step_number": 1, "description": "质检", "duration": 15},
                {"step_number": 2, "description": "入库登记", "duration": 10},
                {"step_number": 3, "description": "上架", "duration": 20}
            ],
            "estimated_duration": 45,
            "status": "pending",
            "domain": "production",
            "process_id": "P001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    result = await db.activities.insert_many(activities)
    activity_ids = [str(id) for id in result.inserted_ids]
    
    # 同步到Neo4j
    for idx, activity in enumerate(activities):
        async with neo4j_driver.session() as session:
            await session.run(
                """
                MERGE (a:Activity {id: $id})
                SET a.name = $name, a.domain = $domain, a.process_id = $process_id
                """,
                id=activity_ids[idx],
                name=activity["name"],
                domain=activity["domain"],
                process_id=activity["process_id"]
            )
    
    # 创建依赖关系
    dependencies = [
        (0, 1, "sequential", 10),  # 牛奶接收 -> 原料检验
        (1, 2, "sequential", 15),  # 原料检验 -> 牛奶消毒
        (2, 3, "sequential", 20),  # 牛奶消毒 -> 灌装
        (3, 4, "sequential", 10),  # 灌装 -> 包装
        (4, 5, "sequential", 15),  # 包装 -> 入库
    ]
    
    for source_idx, target_idx, dep_type, lag in dependencies:
        async with neo4j_driver.session() as session:
            await session.run(
                """
                MATCH (a:Activity {id: $source})
                MATCH (b:Activity {id: $target})
                MERGE (a)-[r:DEPENDS_ON]->(b)
                SET r.type = $type,
                    r.lag_minutes = $lag,
                    r.status = 'active',
                    r.domain = 'production',
                    r.process_id = 'P001'
                """,
                source=activity_ids[source_idx],
                target=activity_ids[target_idx],
                type=dep_type,
                lag=lag
            )
    
    # 创建资源
    resources = [
        {
            "name": "消毒设备-巴氏01",
            "type": "设备",
            "specification": "工业级巴氏消毒机",
            "supplier": "设备供应商A",
            "quantity": 1,
            "unit": "台",
            "status": "available",
            "_target_activity_indices": [2] # 消毒
        },
        {
            "name": "灌装机-自动01",
            "type": "设备",
            "specification": "自动灌装生产线",
            "supplier": "设备供应商B",
            "quantity": 1,
            "unit": "台",
            "status": "available",
            "_target_activity_indices": [3] # 灌装
        },
        {
            "name": "包装材料-1L纸盒",
            "type": "材料",
            "specification": "1升装纸盒",
            "supplier": "包装供应商C",
            "quantity": 10000,
            "unit": "个",
            "status": "available",
             "_target_activity_indices": [4] # 包装
        },
        {
            "name": "储奶罐-A",
            "type": "设备",
            "specification": "10吨级",
            "supplier": "设备供应商A",
            "quantity": 2,
            "unit": "个",
            "status": "available",
            "_target_activity_indices": [0] # 接收
        },
        {
            "name": "检测试剂盒",
            "type": "材料",
            "specification": "快速检测",
            "supplier": "检测耗材厂",
            "quantity": 100,
            "unit": "盒",
            "status": "available",
            "_target_activity_indices": [1] # 检验
        },
        {
            "name": "传送带",
            "type": "设备",
            "specification": "自动化",
            "supplier": "设备供应商C",
            "quantity": 3,
            "unit": "条",
            "status": "available",
            "_target_activity_indices": [3, 4] # 灌装、包装
        },
        {
            "name": "托盘",
            "type": "材料",
            "specification": "标准尺寸",
            "supplier": "仓储设备厂",
            "quantity": 50,
            "unit": "个",
            "status": "available",
            "_target_activity_indices": [5] # 入库
        }
    ]
    
    await create_and_link_resources(db, neo4j_driver, resources, activity_ids, "P001", "production")

    # 创建人员
    personnel = [
        {"name": "张三", "role": "生产主管", "department": "生产部"},
        {"name": "李四", "role": "操作工", "department": "生产部"},
        {"name": "王五", "role": "质检员", "department": "质检部"},
        {"name": "赵二", "role": "操作工", "department": "生产部"},
        {"name": "刘明", "role": "机械工", "department": "生产部"},
        {"name": "陈欣", "role": "仓管员", "department": "仓储部"}
    ]
    await create_and_link_personnel(db, neo4j_driver, personnel, activity_ids, "P001", "production")
    
    print(f"[OK] 生产流程P001: {len(activities)}个活动, {len(dependencies)}条依赖")
    return activity_ids


async def create_transport_t001(mongo_client, neo4j_driver, production_last_activity_id):
    """运输流程 - T001"""
    print("\n创建运输流程 T001...")
    db = mongo_client[MONGODB_DB]
    
    activities = [
        {
            "name": "出库装车",
            "description": "从仓库提取产品并装车",
            "activity_type": "装车",
            "sop_steps": [
                {"step_number": 1, "description": "核对订单", "duration": 15},
                {"step_number": 2, "description": "拣货", "duration": 30},
                {"step_number": 3, "description": "装车", "duration": 25}
            ],
            "estimated_duration": 70,
            "status": "pending",
            "domain": "transport",
            "process_id": "T001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "冷链运输",
            "description": "冷链车辆运输",
            "activity_type": "运输",
            "sop_steps": [
                {"step_number": 1, "description": "启动温控", "duration": 10},
                {"step_number": 2, "description": "运输途中", "duration": 180},
                {"step_number": 3, "description": "温度监控", "duration": 180}
            ],
            "estimated_duration": 180,
            "status": "pending",
            "domain": "transport",
            "process_id": "T001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "到站卸货",
            "description": "到达目的地卸货",
            "activity_type": "卸货",
            "sop_steps": [
                {"step_number": 1, "description": "验货", "duration": 20},
                {"step_number": 2, "description": "卸货", "duration": 30}
            ],
            "estimated_duration": 50,
            "status": "pending",
            "domain": "transport",
            "process_id": "T001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "入库签收",
            "description": "配送中心入库签收",
            "activity_type": "签收",
            "sop_steps": [
                {"step_number": 1, "description": "清点数量", "duration": 20},
                {"step_number": 2, "description": "质检", "duration": 15},
                {"step_number": 3, "description": "入库登记", "duration": 15}
            ],
            "estimated_duration": 50,
            "status": "pending",
            "domain": "transport",
            "process_id": "T001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    result = await db.activities.insert_many(activities)
    activity_ids = [str(id) for id in result.inserted_ids]
    
    # 同步到Neo4j
    for idx, activity in enumerate(activities):
        async with neo4j_driver.session() as session:
            await session.run(
                """
                MERGE (a:Activity {id: $id})
                SET a.name = $name, a.domain = $domain, a.process_id = $process_id
                """,
                id=activity_ids[idx],
                name=activity["name"],
                domain=activity["domain"],
                process_id=activity["process_id"]
            )
    
    # 流程内依赖
    dependencies = [
        (0, 1, "sequential", 15),  # 出库装车 -> 冷链运输
        (1, 2, "sequential", 10),  # 冷链运输 -> 到站卸货
        (2, 3, "sequential", 10),  # 到站卸货 -> 入库签收
    ]
    
    for source_idx, target_idx, dep_type, lag in dependencies:
        async with neo4j_driver.session() as session:
            await session.run(
                """
                MATCH (a:Activity {id: $source})
                MATCH (b:Activity {id: $target})
                MERGE (a)-[r:DEPENDS_ON]->(b)
                SET r.type = $type,
                    r.lag_minutes = $lag,
                    r.status = 'active',
                    r.domain = 'transport',
                    r.process_id = 'T001'
                """,
                source=activity_ids[source_idx],
                target=activity_ids[target_idx],
                type=dep_type,
                lag=lag
            )
    
    # 跨流程依赖：生产入库 -> 运输出库装车
    async with neo4j_driver.session() as session:
        await session.run(
            """
            MATCH (a:Activity {id: $source})
            MATCH (b:Activity {id: $target})
            MERGE (a)-[r:DEPENDS_ON]->(b)
            SET r.type = 'sequential',
                r.lag_minutes = 30,
                r.status = 'active',
                r.domain = NULL,
                r.process_id = NULL
            """,
            source=production_last_activity_id,
            target=activity_ids[0]
        )
        
    # 创建资源
    resources = [
        {
            "name": "冷链车-A001",
            "type": "设备",
            "specification": "5吨级冷链车",
            "supplier": "物流车队",
            "quantity": 1,
            "unit": "辆",
            "status": "available",
            "_target_activity_indices": [1] # 运输
        },
        {
            "name": "电动叉车",
            "type": "设备",
            "specification": "2吨",
            "supplier": "杭叉",
            "quantity": 2,
            "unit": "台",
            "status": "available",
            "_target_activity_indices": [0, 2] # 装车，卸货
        },
        {
            "name": "燃油",
            "type": "材料",
            "specification": "0号柴油",
            "supplier": "中石油",
            "quantity": 500,
            "unit": "升",
            "status": "available",
             "_target_activity_indices": [1] # 运输
        },
        {
            "name": "GPS定位设备",
            "type": "设备",
            "specification": "车载",
            "supplier": "物联网公司",
            "quantity": 5,
            "unit": "台",
            "status": "available",
            "_target_activity_indices": [1] # 运输
        },
        {
            "name": "温度记录仪",
            "type": "设备",
            "specification": "电子式",
            "supplier": "仪器厂",
            "quantity": 10,
            "unit": "个",
            "status": "available",
            "_target_activity_indices": [1] # 运输
        },
        {
            "name": "缠绕膜",
            "type": "材料",
            "specification": "工业级",
            "supplier": "包装材料厂",
            "quantity": 100,
            "unit": "卷",
            "status": "available",
            "_target_activity_indices": [0] # 装车
        },
        {
            "name": "手持扫码枪",
            "type": "设备",
            "specification": "无线",
            "supplier": "信息设备厂",
            "quantity": 8,
            "unit": "个",
            "status": "available",
            "_target_activity_indices": [3] # 签收
        }
    ]
    
    await create_and_link_resources(db, neo4j_driver, resources, activity_ids, "T001", "transport")

    # 创建人员
    personnel = [
        {"name": "孙七", "role": "司机", "department": "物流部"},
        {"name": "赵六", "role": "物流调度", "department": "物流部"},
        {"name": "搬运工甲", "role": "搬运工", "department": "物流部"},
        {"name": "搬运工乙", "role": "搬运工", "department": "物流部"},
        {"name": "押运员小李", "role": "押运员", "department": "物流部"}
    ]
    await create_and_link_personnel(db, neo4j_driver, personnel, activity_ids, "T001", "transport")
    
    print(f"[OK] 运输流程T001: {len(activities)}个活动, {len(dependencies)}条依赖 + 1条跨流程依赖")
    return activity_ids


async def create_sales_s001(mongo_client, neo4j_driver, transport_last_activity_id):
    """销售流程 - S001"""
    print("\n创建销售流程 S001...")
    db = mongo_client[MONGODB_DB]
    
    activities = [
        {
            "name": "订单生成",
            "description": "客户下单生成订单",
            "activity_type": "订单处理",
            "sop_steps": [
                {"step_number": 1, "description": "接收订单", "duration": 5},
                {"step_number": 2, "description": "库存核对", "duration": 10},
                {"step_number": 3, "description": "订单确认", "duration": 5}
            ],
            "estimated_duration": 20,
            "status": "completed",
            "domain": "sales",
            "process_id": "S001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "拣货",
            "description": "根据订单拣选商品",
            "activity_type": "拣货",
            "sop_steps": [
                {"step_number": 1, "description": "打印拣货单", "duration": 5},
                {"step_number": 2, "description": "拣货", "duration": 25},
                {"step_number": 3, "description": "复核", "duration": 10}
            ],
            "estimated_duration": 40,
            "status": "in_progress",
            "domain": "sales",
            "process_id": "S001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "出库配送",
            "description": "商品出库并配送",
            "activity_type": "配送",
            "sop_steps": [
                {"step_number": 1, "description": "包装", "duration": 15},
                {"step_number": 2, "description": "出库", "duration": 10},
                {"step_number": 3, "description": "配送", "duration": 120}
            ],
            "estimated_duration": 145,
            "status": "pending",
            "domain": "sales",
            "process_id": "S001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "客户签收",
            "description": "客户收货签收",
            "activity_type": "签收",
            "sop_steps": [
                {"step_number": 1, "description": "送达", "duration": 5},
                {"step_number": 2, "description": "客户验货", "duration": 10},
                {"step_number": 3, "description": "签收确认", "duration": 5}
            ],
            "estimated_duration": 20,
            "status": "pending",
            "domain": "sales",
            "process_id": "S001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    result = await db.activities.insert_many(activities)
    activity_ids = [str(id) for id in result.inserted_ids]
    
    # 同步到Neo4j
    for idx, activity in enumerate(activities):
        async with neo4j_driver.session() as session:
            await session.run(
                """
                MERGE (a:Activity {id: $id})
                SET a.name = $name, a.domain = $domain, a.process_id = $process_id
                """,
                id=activity_ids[idx],
                name=activity["name"],
                domain=activity["domain"],
                process_id=activity["process_id"]
            )
    
    # 流程内依赖
    dependencies = [
        (0, 1, "sequential", 10),  # 订单生成 -> 拣货
        (1, 2, "sequential", 15),  # 拣货 -> 出库配送
        (2, 3, "sequential", 5),   # 出库配送 -> 客户签收
    ]
    
    for source_idx, target_idx, dep_type, lag in dependencies:
        async with neo4j_driver.session() as session:
            await session.run(
                """
                MATCH (a:Activity {id: $source})
                MATCH (b:Activity {id: $target})
                MERGE (a)-[r:DEPENDS_ON]->(b)
                SET r.type = $type,
                    r.lag_minutes = $lag,
                    r.status = 'active',
                    r.domain = 'sales',
                    r.process_id = 'S001'
                """,
                source=activity_ids[source_idx],
                target=activity_ids[target_idx],
                type=dep_type,
                lag=lag
            )
    
    # 跨流程依赖：运输入库签收 -> 销售拣货
    async with neo4j_driver.session() as session:
        await session.run(
            """
            MATCH (a:Activity {id: $source})
            MATCH (b:Activity {id: $target})
            MERGE (a)-[r:DEPENDS_ON]->(b)
            SET r.type = 'sequential',
                r.lag_minutes = 20,
                r.status = 'active',
                r.domain = NULL,
                r.process_id = NULL
            """,
            source=transport_last_activity_id,
            target=activity_ids[1]
        )
        
    # 创建资源
    resources = [
        {
            "name": "PDA手持终端",
            "type": "设备",
            "specification": "型号X100",
            "supplier": "电子供应商",
            "quantity": 10,
            "unit": "台",
            "status": "available",
            "_target_activity_indices": [1] # 拣货
        },
        {
            "name": "快递箱",
            "type": "材料",
            "specification": "标准5号箱",
            "supplier": "包装厂",
            "quantity": 500,
            "unit": "个",
            "status": "available",
             "_target_activity_indices": [2] # 配送
        },
        {
            "name": "订单管理系统",
            "type": "设备",
            "specification": "软件系统",
            "supplier": "软件开发商",
            "quantity": 1,
            "unit": "套",
            "status": "available",
            "_target_activity_indices": [0] # 订单生成
        },
        {
            "name": "拣货车",
            "type": "设备",
            "specification": "手推式",
            "supplier": "仓储设备厂",
            "quantity": 15,
            "unit": "辆",
            "status": "available",
            "_target_activity_indices": [1] # 拣货
        },
        {
            "name": "泡沫箱",
            "type": "材料",
            "specification": "保温型",
            "supplier": "包装厂",
            "quantity": 300,
            "unit": "个",
            "status": "available",
            "_target_activity_indices": [2] # 配送
        },
        {
            "name": "冰袋",
            "type": "材料",
            "specification": "可重复使用",
            "supplier": "冷链耗材厂",
            "quantity": 1000,
            "unit": "个",
            "status": "available",
            "_target_activity_indices": [2] # 配送
        },
        {
            "name": "配送电动车",
            "type": "设备",
            "specification": "电动三轮",
            "supplier": "车辆厂",
            "quantity": 20,
            "unit": "辆",
            "status": "available",
            "_target_activity_indices": [2, 3] # 配送、签收
        }
    ]
    
    await create_and_link_resources(db, neo4j_driver, resources, activity_ids, "S001", "sales")

    # 创建人员
    personnel = [
        {"name": "周八", "role": "销售助理", "department": "销售部"},
        {"name": "吴九", "role": "拣货员", "department": "仓储部"},
        {"name": "快递员小王", "role": "配送员", "department": "物流部"},
        {"name": "拣货员小张", "role": "拣货员", "department": "仓储部"},
        {"name": "客服小刘", "role": "客服", "department": "销售部"}
    ]
    await create_and_link_personnel(db, neo4j_driver, personnel, activity_ids, "S001", "sales")
    
    print(f"[OK] 销售流程S001: {len(activities)}个活动, {len(dependencies)}条依赖 + 1条跨流程依赖")
    return activity_ids


async def create_quality_q001(mongo_client, neo4j_driver):
    """质检流程 - Q001（独立流程，无跨流程关联）"""
    print("\n创建质检流程 Q001（独立）...")
    db = mongo_client[MONGODB_DB]
    
    activities = [
        {
            "name": "样品采集",
            "description": "从批次中采集样品",
            "activity_type": "采样",
            "sop_steps": [
                {"step_number": 1, "description": "准备采样工具", "duration": 10},
                {"step_number": 2, "description": "采样", "duration": 20}
            ],
            "estimated_duration": 30,
            "status": "completed",
            "domain": "quality",
            "process_id": "Q001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "实验室检测",
            "description": "实验室进行各项指标检测",
            "activity_type": "检测",
            "sop_steps": [
                {"step_number": 1, "description": "微生物检测", "duration": 60},
                {"step_number": 2, "description": "理化指标检测", "duration": 40},
                {"step_number": 3, "description": "记录数据", "duration": 15}
            ],
            "estimated_duration": 115,
            "status": "in_progress",
            "domain": "quality",
            "process_id": "Q001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "出具报告",
            "description": "生成质检报告",
            "activity_type": "报告",
            "sop_steps": [
                {"step_number": 1, "description": "数据分析", "duration": 20},
                {"step_number": 2, "description": "编写报告", "duration": 30},
                {"step_number": 3, "description": "审核", "duration": 15}
            ],
            "estimated_duration": 65,
            "status": "pending",
            "domain": "quality",
            "process_id": "Q001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    result = await db.activities.insert_many(activities)
    activity_ids = [str(id) for id in result.inserted_ids]
    
    # 同步到Neo4j
    for idx, activity in enumerate(activities):
        async with neo4j_driver.session() as session:
            await session.run(
                """
                MERGE (a:Activity {id: $id})
                SET a.name = $name, a.domain = $domain, a.process_id = $process_id
                """,
                id=activity_ids[idx],
                name=activity["name"],
                domain=activity["domain"],
                process_id=activity["process_id"]
            )
    
    # 流程内依赖
    dependencies = [
        (0, 1, "sequential", 15),  # 样品采集 -> 实验室检测
        (1, 2, "sequential", 20),  # 实验室检测 -> 出具报告
    ]
    
    for source_idx, target_idx, dep_type, lag in dependencies:
        async with neo4j_driver.session() as session:
            await session.run(
                """
                MATCH (a:Activity {id: $source})
                MATCH (b:Activity {id: $target})
                MERGE (a)-[r:DEPENDS_ON]->(b)
                SET r.type = $type,
                    r.lag_minutes = $lag,
                    r.status = 'active',
                    r.domain = 'quality',
                    r.process_id = 'Q001'
                """,
                source=activity_ids[source_idx],
                target=activity_ids[target_idx],
                type=dep_type,
                lag=lag
            )
            
    # 创建资源
    resources = [
        {
            "name": "高倍显微镜",
            "type": "设备",
            "specification": "1600X",
            "supplier": "光学仪器厂",
            "quantity": 2,
            "unit": "台",
            "status": "available",
            "_target_activity_indices": [1] # 检测
        },
        {
            "name": "检测试剂A",
            "type": "材料",
            "specification": "500ml",
            "supplier": "化学试剂厂",
            "quantity": 20,
            "unit": "瓶",
            "status": "available",
             "_target_activity_indices": [1] # 检测
        },
        {
            "name": "采样工具箱",
            "type": "设备",
            "specification": "标准配置",
            "supplier": "实验器材厂",
            "quantity": 5,
            "unit": "套",
            "status": "available",
            "_target_activity_indices": [0] # 采样
        },
        {
            "name": "pH计",
            "type": "设备",
            "specification": "精密型",
            "supplier": "仪器厂",
            "quantity": 3,
            "unit": "台",
            "status": "available",
            "_target_activity_indices": [1] # 检测
        },
        {
            "name": "培养皿",
            "type": "材料",
            "specification": "无菌",
            "supplier": "实验耗材厂",
            "quantity": 200,
            "unit": "个",
            "status": "available",
            "_target_activity_indices": [1] # 检测
        },
        {
            "name": "报告打印机",
            "type": "设备",
            "specification": "激光打印",
            "supplier": "办公设备厂",
            "quantity": 2,
            "unit": "台",
            "status": "available",
            "_target_activity_indices": [2] # 报告
        }
    ]
    
    await create_and_link_resources(db, neo4j_driver, resources, activity_ids, "Q001", "quality")

    # 创建人员
    personnel = [
        {"name": "郑十", "role": "质检主任", "department": "质检部"},
        {"name": "钱十一", "role": "化验员", "department": "质检部"},
        {"name": "化验员小赵", "role": "化验员", "department": "质检部"},
        {"name": "采样员小孙", "role": "采样员", "department": "质检部"}
    ]
    await create_and_link_personnel(db, neo4j_driver, personnel, activity_ids, "Q001", "quality")
    
    print(f"[OK] 质检流程Q001: {len(activities)}个活动, {len(dependencies)}条依赖（独立流程）")


async def create_production_p002(mongo_client, neo4j_driver):
    """副生产线 - P002"""
    print("\n创建副生产线 P002...")
    db = mongo_client[MONGODB_DB]
    
    activities = [
        {
            "name": "原料预处理",
            "description": "对原料进行预处理",
            "activity_type": "预处理",
            "sop_steps": [
                {"step_number": 1, "description": "原料分类", "duration": 15},
                {"step_number": 2, "description": "清洗", "duration": 20}
            ],
            "estimated_duration": 35,
            "status": "completed",
            "domain": "production",
            "process_id": "P002",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "发酵处理",
            "description": "发酵工艺处理",
            "activity_type": "发酵",
            "sop_steps": [
                {"step_number": 1, "description": "投料", "duration": 10},
                {"step_number": 2, "description": "发酵控温", "duration": 120}
            ],
            "estimated_duration": 130,
            "status": "in_progress",
            "domain": "production",
            "process_id": "P002",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "成品检验",
            "description": "成品质量检验",
            "activity_type": "检验",
            "sop_steps": [
                {"step_number": 1, "description": "抽样", "duration": 10},
                {"step_number": 2, "description": "检验", "duration": 25}
            ],
            "estimated_duration": 35,
            "status": "pending",
            "domain": "production",
            "process_id": "P002",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    result = await db.activities.insert_many(activities)
    activity_ids = [str(id) for id in result.inserted_ids]
    
    for idx, activity in enumerate(activities):
        async with neo4j_driver.session() as session:
            await session.run(
                "MERGE (a:Activity {id: $id}) SET a.name = $name, a.domain = $domain, a.process_id = $process_id",
                id=activity_ids[idx], name=activity["name"], domain=activity["domain"], process_id=activity["process_id"]
            )
    
    dependencies = [(0, 1, "sequential", 10), (1, 2, "sequential", 15)]
    for source_idx, target_idx, dep_type, lag in dependencies:
        async with neo4j_driver.session() as session:
            await session.run(
                """MATCH (a:Activity {id: $source}) MATCH (b:Activity {id: $target})
                MERGE (a)-[r:DEPENDS_ON]->(b) SET r.type = $type, r.lag_minutes = $lag, r.status = 'active', r.domain = 'production', r.process_id = 'P002'""",
                source=activity_ids[source_idx], target=activity_ids[target_idx], type=dep_type, lag=lag
            )
    
    resources = [
        {"name": "发酵罐", "type": "设备", "specification": "5吨级", "supplier": "发酵设备厂", "quantity": 3, "unit": "个", "status": "available", "_target_activity_indices": [1]},
        {"name": "清洗设备", "type": "设备", "specification": "自动", "supplier": "清洗设备厂", "quantity": 2, "unit": "台", "status": "available", "_target_activity_indices": [0]},
        {"name": "发酵菌种", "type": "材料", "specification": "益生菌", "supplier": "菌种供应商", "quantity": 50, "unit": "包", "status": "available", "_target_activity_indices": [1]}
    ]
    await create_and_link_resources(db, neo4j_driver, resources, activity_ids, "P002", "production")
    
    personnel = [
        {"name": "发酵师傅老王", "role": "发酵技师", "department": "生产部"},
        {"name": "预处理工小李", "role": "操作工", "department": "生产部"},
        {"name": "检验员小陈", "role": "质检员", "department": "质检部"}
    ]
    await create_and_link_personnel(db, neo4j_driver, personnel, activity_ids, "P002", "production")
    
    print(f"[OK] 副生产线P002: {len(activities)}个活动, {len(dependencies)}条依赖")
    return activity_ids


async def create_transport_t002(mongo_client, neo4j_driver):
    """常温运输 - T002"""
    print("\n创建常温运输 T002...")
    db = mongo_client[MONGODB_DB]
    
    activities = [
        {
            "name": "常温装车",
            "description": "常温产品装车",
            "activity_type": "装车",
            "sop_steps": [
                {"step_number": 1, "description": "清点货物", "duration": 20},
                {"step_number": 2, "description": "装车", "duration": 30}
            ],
            "estimated_duration": 50,
            "status": "completed",
            "domain": "transport",
            "process_id": "T002",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "常温运输",
            "description": "常温车辆运输",
            "activity_type": "运输",
            "sop_steps": [
                {"step_number": 1, "description": "路线规划", "duration": 5},
                {"step_number": 2, "description": "运输", "duration": 150}
            ],
            "estimated_duration": 155,
            "status": "in_progress",
            "domain": "transport",
            "process_id": "T002",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "常温配送",
            "description": "到达目的地配送",
            "activity_type": "配送",
            "sop_steps": [
                {"step_number": 1, "description": "卸货", "duration": 25},
                {"step_number": 2, "description": "签收", "duration": 10}
            ],
            "estimated_duration": 35,
            "status": "pending",
            "domain": "transport",
            "process_id": "T002",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    result = await db.activities.insert_many(activities)
    activity_ids = [str(id) for id in result.inserted_ids]
    
    for idx, activity in enumerate(activities):
        async with neo4j_driver.session() as session:
            await session.run(
                "MERGE (a:Activity {id: $id}) SET a.name = $name, a.domain = $domain, a.process_id = $process_id",
                id=activity_ids[idx], name=activity["name"], domain=activity["domain"], process_id=activity["process_id"]
            )
    
    dependencies = [(0, 1, "sequential", 10), (1, 2, "sequential", 5)]
    for source_idx, target_idx, dep_type, lag in dependencies:
        async with neo4j_driver.session() as session:
            await session.run(
                """MATCH (a:Activity {id: $source}) MATCH (b:Activity {id: $target})
                MERGE (a)-[r:DEPENDS_ON]->(b) SET r.type = $type, r.lag_minutes = $lag, r.status = 'active', r.domain = 'transport', r.process_id = 'T002'""",
                source=activity_ids[source_idx], target=activity_ids[target_idx], type=dep_type, lag=lag
            )
    
    resources = [
        {"name": "普通货车", "type": "设备", "specification": "5吨级", "supplier": "车队", "quantity": 3, "unit": "辆", "status": "available", "_target_activity_indices": [1]},
        {"name": "手推车", "type": "设备", "specification": "标准", "supplier": "仓储设备", "quantity": 5, "unit": "辆", "status": "available", "_target_activity_indices": [0, 2]},
        {"name": "纸箱", "type": "材料", "specification": "标准", "supplier": "包装厂", "quantity": 1000, "unit": "个", "status": "available", "_target_activity_indices": [0]}
    ]
    await create_and_link_resources(db, neo4j_driver, resources, activity_ids, "T002", "transport")
    
    personnel = [
        {"name": "司机老张", "role": "司机", "department": "物流部"},
        {"name": "装卸工小刘", "role": "装卸工", "department": "物流部"},
        {"name": "调度员", "role": "调度", "department": "物流部"}
    ]
    await create_and_link_personnel(db, neo4j_driver, personnel, activity_ids, "T002", "transport")
    
    print(f"[OK] 常温运输T002: {len(activities)}个活动, {len(dependencies)}条依赖")
    return activity_ids


async def create_sales_s002(mongo_client, neo4j_driver):
    """线下销售 - S002"""
    print("\n创建线下销售 S002...")
    db = mongo_client[MONGODB_DB]
    
    activities = [
        {
            "name": "门店接单",
            "description": "门店收银接单",
            "activity_type": "接单",
            "sop_steps": [
                {"step_number": 1, "description": "客户选购", "duration": 10},
                {"step_number": 2, "description": "收银", "duration": 5}
            ],
            "estimated_duration": 15,
            "status": "completed",
            "domain": "sales",
            "process_id": "S002",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "商品打包",
            "description": "商品打包装袋",
            "activity_type": "打包",
            "sop_steps": [
                {"step_number": 1, "description": "装袋", "duration": 5},
                {"step_number": 2, "description": "密封", "duration": 3}
            ],
            "estimated_duration": 8,
            "status": "in_progress",
            "domain": "sales",
            "process_id": "S002",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "客户取货",
            "description": "客户取货完成",
            "activity_type": "交付",
            "sop_steps": [
                {"step_number": 1, "description": "验货", "duration": 3},
                {"step_number": 2, "description": "交付", "duration": 2}
            ],
            "estimated_duration": 5,
            "status": "pending",
            "domain": "sales",
            "process_id": "S002",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    result = await db.activities.insert_many(activities)
    activity_ids = [str(id) for id in result.inserted_ids]
    
    for idx, activity in enumerate(activities):
        async with neo4j_driver.session() as session:
            await session.run(
                "MERGE (a:Activity {id: $id}) SET a.name = $name, a.domain = $domain, a.process_id = $process_id",
                id=activity_ids[idx], name=activity["name"], domain=activity["domain"], process_id=activity["process_id"]
            )
    
    dependencies = [(0, 1, "sequential", 2), (1, 2, "sequential", 1)]
    for source_idx, target_idx, dep_type, lag in dependencies:
        async with neo4j_driver.session() as session:
            await session.run(
                """MATCH (a:Activity {id: $source}) MATCH (b:Activity {id: $target})
                MERGE (a)-[r:DEPENDS_ON]->(b) SET r.type = $type, r.lag_minutes = $lag, r.status = 'active', r.domain = 'sales', r.process_id = 'S002'""",
                source=activity_ids[source_idx], target=activity_ids[target_idx], type=dep_type, lag=lag
            )
    
    resources = [
        {"name": "收银机", "type": "设备", "specification": "POS机", "supplier": "收银设备商", "quantity": 5, "unit": "台", "status": "available", "_target_activity_indices": [0]},
        {"name": "购物袋", "type": "材料", "specification": "环保袋", "supplier": "包装厂", "quantity": 2000, "unit": "个", "status": "available", "_target_activity_indices": [1]},
        {"name": "保鲜袋", "type": "材料", "specification": "食品级", "supplier": "包装厂", "quantity": 1000, "unit": "卷", "status": "available", "_target_activity_indices": [1]}
    ]
    await create_and_link_resources(db, neo4j_driver, resources, activity_ids, "S002", "sales")
    
    personnel = [
        {"name": "收银员小美", "role": "收银员", "department": "销售部"},
        {"name": "店员小红", "role": "销售员", "department": "销售部"},
        {"name": "店长", "role": "店长", "department": "销售部"}
    ]
    await create_and_link_personnel(db, neo4j_driver, personnel, activity_ids, "S002", "sales")
    
    print(f"[OK] 线下销售S002: {len(activities)}个活动, {len(dependencies)}条依赖")
    return activity_ids


async def create_quality_q002(mongo_client, neo4j_driver):
    """专项质检 - Q002"""
    print("\n创建专项质检 Q002...")
    db = mongo_client[MONGODB_DB]
    
    activities = [
        {
            "name": "专项抽检",
            "description": "针对性专项抽检",
            "activity_type": "抽检",
            "sop_steps": [
                {"step_number": 1, "description": "确定抽检批次", "duration": 15},
                {"step_number": 2, "description": "抽样", "duration": 20}
            ],
            "estimated_duration": 35,
            "status": "completed",
            "domain": "quality",
            "process_id": "Q002",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "专项检测",
            "description": "进行专项检测分析",
            "activity_type": "检测",
            "sop_steps": [
                {"step_number": 1, "description": "样品准备", "duration": 20},
                {"step_number": 2, "description": "专项检测", "duration": 90}
            ],
            "estimated_duration": 110,
            "status": "in_progress",
            "domain": "quality",
            "process_id": "Q002",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "结果分析",
            "description": "检测结果分析评估",
            "activity_type": "分析",
            "sop_steps": [
                {"step_number": 1, "description": "数据统计", "duration": 25},
                {"step_number": 2, "description": "报告编制", "duration": 40}
            ],
            "estimated_duration": 65,
            "status": "pending",
            "domain": "quality",
            "process_id": "Q002",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    result = await db.activities.insert_many(activities)
    activity_ids = [str(id) for id in result.inserted_ids]
    
    for idx, activity in enumerate(activities):
        async with neo4j_driver.session() as session:
            await session.run(
                "MERGE (a:Activity {id: $id}) SET a.name = $name, a.domain = $domain, a.process_id = $process_id",
                id=activity_ids[idx], name=activity["name"], domain=activity["domain"], process_id=activity["process_id"]
            )
    
    dependencies = [(0, 1, "sequential", 10), (1, 2, "sequential", 15)]
    for source_idx, target_idx, dep_type, lag in dependencies:
        async with neo4j_driver.session() as session:
            await session.run(
                """MATCH (a:Activity {id: $source}) MATCH (b:Activity {id: $target})
                MERGE (a)-[r:DEPENDS_ON]->(b) SET r.type = $type, r.lag_minutes = $lag, r.status = 'active', r.domain = 'quality', r.process_id = 'Q002'""",
                source=activity_ids[source_idx], target=activity_ids[target_idx], type=dep_type, lag=lag
            )
    
    resources = [
        {"name": "光谱仪", "type": "设备", "specification": "高精度", "supplier": "精密仪器厂", "quantity": 1, "unit": "台", "status": "available", "_target_activity_indices": [1]},
        {"name": "专项试剂", "type": "材料", "specification": "专用", "supplier": "试剂供应商", "quantity": 30, "unit": "瓶", "status": "available", "_target_activity_indices": [1]},
        {"name": "分析软件", "type": "设备", "specification": "专业版", "supplier": "软件公司", "quantity": 2, "unit": "套", "status": "available", "_target_activity_indices": [2]}
    ]
    await create_and_link_resources(db, neo4j_driver, resources, activity_ids, "Q002", "quality")
    
    personnel = [
        {"name": "高级检测师", "role": "高级技师", "department": "质检部"},
        {"name": "质检分析员", "role": "分析员", "department": "质检部"},
        {"name": "抽检员", "role": "抽检员", "department": "质检部"}
    ]
    await create_and_link_personnel(db, neo4j_driver, personnel, activity_ids, "Q002", "quality")
    
    print(f"[OK] 专项质检Q002: {len(activities)}个活动, {len(dependencies)}条依赖")
    return activity_ids


async def create_warehouse_w001(mongo_client, neo4j_driver):
    """主仓库 - W001"""
    print("\n创建主仓库 W001...")
    db = mongo_client[MONGODB_DB]
    
    activities = [
        {
            "name": "入库登记",
            "description": "货物入库登记管理",
            "activity_type": "入库",
            "sop_steps": [
                {"step_number": 1, "description": "核对单据", "duration": 10},
                {"step_number": 2, "description": "系统登记", "duration": 8}
            ],
            "estimated_duration": 18,
            "status": "completed",
            "domain": "warehouse",
            "process_id": "W001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "货物上架",
            "description": "将货物摆放到货架",
            "activity_type": "上架",
            "sop_steps": [
                {"step_number": 1, "description": "分配货位", "duration": 5},
                {"step_number": 2, "description": "搬运上架", "duration": 20}
            ],
            "estimated_duration": 25,
            "status": "in_progress",
            "domain": "warehouse",
            "process_id": "W001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "库存盘点",
            "description": "定期库存盘点",
            "activity_type": "盘点",
            "sop_steps": [
                {"step_number": 1, "description": "清点数量", "duration": 40},
                {"step_number": 2, "description": "录入系统", "duration": 15}
            ],
            "estimated_duration": 55,
            "status": "pending",
            "domain": "warehouse",
            "process_id": "W001",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    result = await db.activities.insert_many(activities)
    activity_ids = [str(id) for id in result.inserted_ids]
    
    for idx, activity in enumerate(activities):
        async with neo4j_driver.session() as session:
            await session.run(
                "MERGE (a:Activity {id: $id}) SET a.name = $name, a.domain = $domain, a.process_id = $process_id",
                id=activity_ids[idx], name=activity["name"], domain=activity["domain"], process_id=activity["process_id"]
            )
    
    dependencies = [(0, 1, "sequential", 5), (1, 2, "sequential", 60)]
    for source_idx, target_idx, dep_type, lag in dependencies:
        async with neo4j_driver.session() as session:
            await session.run(
                """MATCH (a:Activity {id: $source}) MATCH (b:Activity {id: $target})
                MERGE (a)-[r:DEPENDS_ON]->(b) SET r.type = $type, r.lag_minutes = $lag, r.status = 'active', r.domain = 'warehouse', r.process_id = 'W001'""",
                source=activity_ids[source_idx], target=activity_ids[target_idx], type=dep_type, lag=lag
            )
    
    resources = [
        {"name": "货架系统", "type": "设备", "specification": "立体货架", "supplier": "仓储设备商", "quantity": 50, "unit": "组", "status": "available", "_target_activity_indices": [1]},
        {"name": "叉车", "type": "设备", "specification": "电动", "supplier": "叉车厂", "quantity": 4, "unit": "台", "status": "available", "_target_activity_indices": [1]},
        {"name": "盘点机", "type": "设备", "specification": "手持", "supplier": "信息设备商", "quantity": 10, "unit": "台", "status": "available", "_target_activity_indices": [2]},
        {"name": "托盘", "type": "材料", "specification": "塑料", "supplier": "仓储耗材", "quantity": 200, "unit": "个", "status": "available", "_target_activity_indices": [0, 1]}
    ]
    await create_and_link_resources(db, neo4j_driver, resources, activity_ids, "W001", "warehouse")
    
    personnel = [
        {"name": "主仓管理员", "role": "仓库主管", "department": "仓储部"},
        {"name": "叉车工老李", "role": "叉车工", "department": "仓储部"},
        {"name": "理货员", "role": "理货员", "department": "仓储部"},
        {"name": "录单员", "role": "文员", "department": "仓储部"}
    ]
    await create_and_link_personnel(db, neo4j_driver, personnel, activity_ids, "W001", "warehouse")
    
    print(f"[OK] 主仓库W001: {len(activities)}个活动, {len(dependencies)}条依赖")
    return activity_ids


async def create_warehouse_w002(mongo_client, neo4j_driver):
    """分仓库 - W002"""
    print("\n创建分仓库 W002...")
    db = mongo_client[MONGODB_DB]
    
    activities = [
        {
            "name": "分仓入库",
            "description": "分仓库收货入库",
            "activity_type": "入库",
            "sop_steps": [
                {"step_number": 1, "description": "验收", "duration": 15},
                {"step_number": 2, "description": "入库", "duration": 10}
            ],
            "estimated_duration": 25,
            "status": "completed",
            "domain": "warehouse",
            "process_id": "W002",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "分仓出库",
            "description": "分仓库提货出库",
            "activity_type": "出库",
            "sop_steps": [
                {"step_number": 1, "description": "拣货", "duration": 20},
                {"step_number": 2, "description": "出库", "duration": 10}
            ],
            "estimated_duration": 30,
            "status": "in_progress",
            "domain": "warehouse",
            "process_id": "W002",
            "version": 1,
            "is_active": True,
            "required_resources": [],
            "required_personnel": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    result = await db.activities.insert_many(activities)
    activity_ids = [str(id) for id in result.inserted_ids]
    
    for idx, activity in enumerate(activities):
        async with neo4j_driver.session() as session:
            await session.run(
                "MERGE (a:Activity {id: $id}) SET a.name = $name, a.domain = $domain, a.process_id = $process_id",
                id=activity_ids[idx], name=activity["name"], domain=activity["domain"], process_id=activity["process_id"]
            )
    
    dependencies = [(0, 1, "sequential", 30)]
    for source_idx, target_idx, dep_type, lag in dependencies:
        async with neo4j_driver.session() as session:
            await session.run(
                """MATCH (a:Activity {id: $source}) MATCH (b:Activity {id: $target})
                MERGE (a)-[r:DEPENDS_ON]->(b) SET r.type = $type, r.lag_minutes = $lag, r.status = 'active', r.domain = 'warehouse', r.process_id = 'W002'""",
                source=activity_ids[source_idx], target=activity_ids[target_idx], type=dep_type, lag=lag
            )
    
    resources = [
        {"name": "小型货架", "type": "设备", "specification": "标准", "supplier": "货架厂", "quantity": 20, "unit": "组", "status": "available", "_target_activity_indices": [0, 1]},
        {"name": "手推车", "type": "设备", "specification": "仓储用", "supplier": "设备商", "quantity": 6, "unit": "辆", "status": "available", "_target_activity_indices": [1]},
        {"name": "条码扫描枪", "type": "设备", "specification": "无线", "supplier": "信息设备", "quantity": 5, "unit": "个", "status": "available", "_target_activity_indices": [0, 1]}
    ]
    await create_and_link_resources(db, neo4j_driver, resources, activity_ids, "W002", "warehouse")
    
    personnel = [
        {"name": "分仓管理员", "role": "仓管", "department": "仓储部"},
        {"name": "拣货员小周", "role": "拣货员", "department": "仓储部"},
        {"name": "验收员", "role": "验收员", "department": "仓储部"}
    ]
    await create_and_link_personnel(db, neo4j_driver, personnel, activity_ids, "W002", "warehouse")
    
    print(f"[OK] 分仓库W002: {len(activities)}个活动, {len(dependencies)}条依赖")
    return activity_ids


async def main():
    print("=" * 60)
    print("多流程测试数据初始化")
    print("=" * 60)
    
    # 连接数据库
    mongo_client = AsyncIOMotorClient(MONGODB_URL)
    neo4j_driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        # 清空数据
        await clear_all_data(mongo_client, neo4j_driver)
        
        # 创建流程数据
        production_ids = await create_production_p001(mongo_client, neo4j_driver)
        transport_ids = await create_transport_t001(mongo_client, neo4j_driver, production_ids[-1])
        sales_ids = await create_sales_s001(mongo_client, neo4j_driver, transport_ids[-1])
        await create_quality_q001(mongo_client, neo4j_driver)
        
        # 新增流程
        await create_production_p002(mongo_client, neo4j_driver)
        await create_transport_t002(mongo_client, neo4j_driver)
        await create_sales_s002(mongo_client, neo4j_driver)
        await create_quality_q002(mongo_client, neo4j_driver)
        await create_warehouse_w001(mongo_client, neo4j_driver)
        await create_warehouse_w002(mongo_client, neo4j_driver)
        
        print("\n" + "=" * 60)
        print("[OK] 所有数据初始化完成！")
        print("=" * 60)
        print("\n流程清单：")
        print("  - production/P001: 主生产流程（6个活动）")
        print("  - production/P002: 副生产线（3个活动）")
        print("  - transport/T001: 冷链运输（4个活动）")
        print("  - transport/T002: 常温运输（3个活动）")
        print("  - sales/S001: 线上销售（4个活动）")
        print("  - sales/S002: 线下销售（3个活动）")
        print("  - quality/Q001: 常规质检（3个活动）")
        print("  - quality/Q002: 专项质检（3个活动）")
        print("  - warehouse/W001: 主仓库（3个活动）")
        print("  - warehouse/W002: 分仓库（2个活动）")
        print("\n跨流程关联：")
        print("  - 生产入库 → 运输出库装车")
        print("  - 运输入库签收 → 销售拣货")
        print("\n共10个流程，每个流程都包含活动、人员、资源节点")
        
    finally:
        mongo_client.close()
        await neo4j_driver.close()


if __name__ == "__main__":
    asyncio.run(main())
