"""
多流程测试数据种子脚本
一键初始化 MongoDB + Neo4j 数据
"""
import asyncio
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from neo4j import AsyncGraphDatabase
from bson import ObjectId

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
            "domain": "production",
            "process_id": "P001",
            "version": 1,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "灌装机-自动01",
            "type": "设备",
            "specification": "自动灌装生产线",
            "supplier": "设备供应商B",
            "quantity": 1,
            "unit": "台",
            "status": "available",
            "domain": "production",
            "process_id": "P001",
            "version": 1,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "包装材料-1L纸盒",
            "type": "材料",
            "specification": "1升装纸盒",
            "supplier": "包装供应商C",
            "quantity": 10000,
            "unit": "个",
            "status": "available",
            "domain": "production",
            "process_id": "P001",
            "version": 1,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    result = await db.resources.insert_many(resources)
    resource_ids = [str(id) for id in result.inserted_ids]
    
    # 同步资源到 Neo4j
    for idx, resource in enumerate(resources):
        async with neo4j_driver.session() as session:
            await session.run(
                """
                MERGE (r:Resource {id: $id})
                SET r.name = $name
                """,
                id=resource_ids[idx],
                name=resource["name"]
            )
    
    # 创建活动-资源使用关系（USES）
    # 消毒设备 -> 牛奶消毒活动
    async with neo4j_driver.session() as session:
        await session.run(
            """
            MATCH (a:Activity {id: $activity_id})
            MATCH (r:Resource {id: $resource_id})
            MERGE (a)-[u:USES]->(r)
            SET u.quantity = 1, u.unit = '台', u.stage = 'production'
            """,
            activity_id=activity_ids[2],  # 牛奶消毒
            resource_id=resource_ids[0]   # 消毒设备
        )
    
    # 灌装机 -> 灌装活动
    async with neo4j_driver.session() as session:
        await session.run(
            """
            MATCH (a:Activity {id: $activity_id})
            MATCH (r:Resource {id: $resource_id})
            MERGE (a)-[u:USES]->(r)
            SET u.quantity = 1, u.unit = '台', u.stage = 'production'
            """,
            activity_id=activity_ids[3],  # 灌装
            resource_id=resource_ids[1]   # 灌装机
        )
    
    # 包装材料 -> 包装活动
    async with neo4j_driver.session() as session:
        await session.run(
            """
            MATCH (a:Activity {id: $activity_id})
            MATCH (r:Resource {id: $resource_id})
            MERGE (a)-[u:USES]->(r)
            SET u.quantity = 1000, u.unit = '个', u.stage = 'production'
            """,
            activity_id=activity_ids[4],  # 包装
            resource_id=resource_ids[2]   # 包装材料
        )
    
    print(f"[OK] 生产流程P001: {len(activities)}个活动, {len(dependencies)}条依赖, {len(resources)}个资源, 3条USES关系")
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
    
    print(f"[OK] 质检流程Q001: {len(activities)}个活动, {len(dependencies)}条依赖（独立流程）")


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
        
        print("\n" + "=" * 60)
        print("[OK] 所有数据初始化完成！")
        print("=" * 60)
        print("\n流程清单：")
        print("  - production/P001: 生产流程（6个活动）")
        print("  - transport/T001: 运输流程（4个活动）")
        print("  - sales/S001: 销售流程（4个活动）")
        print("  - quality/Q001: 质检流程（3个活动，独立）")
        print("\n跨流程关联：")
        print("  - 生产入库 → 运输出库装车")
        print("  - 运输入库签收 → 销售拣货")
        print("\n请使用前端流程选择器切换查看不同流程")
        
    finally:
        mongo_client.close()
        await neo4j_driver.close()


if __name__ == "__main__":
    asyncio.run(main())

