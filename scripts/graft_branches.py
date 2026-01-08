"""
分支嫁接脚本 - 为线性流程添加并行分支结构
将线性DAG改造为带有并行路径的DAG，用于演示CPM关键路径差异
"""
import asyncio
import sys
import os
import random
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from neo4j import AsyncGraphDatabase
from bson import ObjectId

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.app.config import settings

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# 并行活动规则：根据源节点和目标节点类型生成有业务逻辑的并行活动
PARALLEL_ACTIVITY_RULES = {
    # 生产流程相关
    "接收->检验": {"name": "检测设备预热", "type": "设备准备", "desc": "在原料接收的同时，提前预热检测设备以缩短检验时间"},
    "接收->消毒": {"name": "消毒设备预检", "type": "设备准备", "desc": "在原料接收时，同步对消毒设备进行状态检查"},
    "接收->包装": {"name": "包材准备与检验", "type": "材料准备", "desc": "在原料接收的同时，提前准备并检验包装材料，确保后续包装顺利"},
    "检验->消毒": {"name": "设备预热与清洗", "type": "设备准备", "desc": "在检验完成后，提前对消毒设备进行预热和清洗"},
    "检验->灌装": {"name": "灌装线清洁消毒", "type": "设备准备", "desc": "在产品检验的同时，对灌装生产线进行清洁和消毒"},
    "消毒->灌装": {"name": "容器清洗与消毒", "type": "预处理", "desc": "在消毒过程中，并行对灌装容器进行清洗和消毒"},
    "消毒->包装": {"name": "包材准备与标签打印", "type": "材料准备", "desc": "在消毒过程中，准备包装材料并预先打印产品标签"},
    "消毒->入库": {"name": "冷库预冷与货位准备", "type": "仓储准备", "desc": "在消毒过程中，提前对冷库进行预冷并准备存储货位"},
    "灌装->入库": {"name": "仓库标签打印与货位清理", "type": "仓储准备", "desc": "在灌装过程中，提前打印仓库标签并清理存储货位"},
    "灌装->包装": {"name": "质量抽检与记录", "type": "质检", "desc": "在灌装完成后，对产品进行快速抽检并记录数据"},
    "包装->入库": {"name": "库位预分配与清理", "type": "仓储准备", "desc": "在包装过程中，提前在仓库系统中分配存储位置并清理货位"},
    "预处理->发酵": {"name": "菌种培养与激活", "type": "材料准备", "desc": "在预处理时，同步培养和激活发酵所需的菌种"},
    "发酵->检验": {"name": "取样工具消毒", "type": "设备准备", "desc": "在发酵过程中，提前准备并消毒检验用的取样工具"},
    
    # 运输流程相关
    "装车->运输": {"name": "路线规划与优化", "type": "调度", "desc": "在装车时，同步进行最优运输路线规划"},
    "装车->卸货": {"name": "客户通知与确认", "type": "沟通", "desc": "在装车后，通知客户预计到达时间并确认接收准备"},
    "运输->卸货": {"name": "卸货区预备", "type": "现场准备", "desc": "在运输途中，提前联系目的地准备卸货区域"},
    "运输->签收": {"name": "单据准备与核对", "type": "文档准备", "desc": "在运输过程中，准备并预先核对签收单据"},
    "卸货->签收": {"name": "温度记录整理", "type": "质量记录", "desc": "在卸货时，同步整理运输全程的温度监控记录"},
    
    # 销售流程相关
    "订单->拣货": {"name": "库存预留与锁定", "type": "库存管理", "desc": "接收订单后，立即在系统中预留和锁定相应库存"},
    "拣货->配送": {"name": "配送单生成与打印", "type": "文档准备", "desc": "在拣货时，同步生成并打印配送单和地址标签"},
    "拣货->客户签收": {"name": "客户联系确认", "type": "沟通", "desc": "在拣货后，联系客户确认收货时间和地址"},
    "配送->签收": {"name": "配送轨迹记录", "type": "过程记录", "desc": "在配送途中，实时记录配送轨迹和状态"},
    "接单->打包": {"name": "冰袋准备与冷冻", "type": "材料准备", "desc": "接单后，立即准备并冷冻保温所需的冰袋"},
    
    # 质检流程相关
    "采集->检测": {"name": "检测设备校准", "type": "设备准备", "desc": "在样品采集时，同步对检测设备进行校准"},
    "检测->报告": {"name": "历史数据对比分析", "type": "数据分析", "desc": "在检测过程中，调取历史数据进行对比分析"},
    "抽检->检测": {"name": "标准样品准备", "type": "材料准备", "desc": "在抽检时，同步准备对照用的标准样品"},
    
    # 仓储流程相关
    "入库->上架": {"name": "货位清理与消毒", "type": "现场准备", "desc": "在入库登记时，同步清理和消毒货架位置"},
    "入库->盘点": {"name": "系统数据核对", "type": "数据核对", "desc": "在入库时，同步核对系统库存数据的准确性"},
    "上架->盘点": {"name": "库存预警检查", "type": "库存管理", "desc": "在上架过程中，检查库存预警设置和阈值"},
    
    # 通用规则
    "default": {"name": "并行准备工作", "type": "准备", "desc": "在流程执行过程中进行必要的准备工作"}
}


async def find_candidate_processes(driver):
    """查找节点数>3的流程（最多返回2个）"""
    print("\n[1] 查找候选流程...")
    
    query = """
    MATCH (a:Activity)
    WHERE a.process_id IS NOT NULL
    WITH a.process_id as pid, a.domain as domain, count(a) as node_count
    WHERE node_count > 3
    RETURN pid, domain, node_count
    ORDER BY node_count DESC
    LIMIT 2
    """
    
    candidates = []
    async with driver.session() as session:
        result = await session.run(query)
        async for record in result:
            candidates.append({
                "process_id": record["pid"],
                "domain": record["domain"],
                "node_count": record["node_count"]
            })
    
    print(f"   找到 {len(candidates)} 个候选流程:")
    for c in candidates:
        print(f"   - {c['domain']}/{c['process_id']}: {c['node_count']} 个节点")
    
    return candidates


async def find_graftable_nodes(driver, process_id):
    """在指定流程中找到可以嫁接的两个节点A和B（中间至少隔1跳）"""
    query = """
    MATCH (start:Activity {process_id: $pid})-[:DEPENDS_ON*2..]->(end:Activity {process_id: $pid})
    RETURN start.id as node_a_id, end.id as node_b_id, 
           start.name as node_a_name, end.name as node_b_name
    ORDER BY rand()
    LIMIT 1
    """
    
    async with driver.session() as session:
        result = await session.run(query, {"pid": process_id})
        record = await result.single()
        if not record:
            return None
        return {
            "node_a_id": record["node_a_id"],
            "node_b_id": record["node_b_id"],
            "node_a_name": record["node_a_name"],
            "node_b_name": record["node_b_name"]
        }


async def calculate_original_path_duration(driver, node_a_id, node_b_id, db):
    """计算A到B原路径的总时长"""
    query = """
    MATCH path = shortestPath((a:Activity {id: $a_id})-[:DEPENDS_ON*]->(b:Activity {id: $b_id}))
    RETURN [n in nodes(path) | n.id] as node_ids
    """
    
    async with driver.session() as session:
        result = await session.run(query, {"a_id": node_a_id, "b_id": node_b_id})
        record = await result.single()
        if not record:
            return 0
        
        node_ids = record["node_ids"]
        total_duration = 0
        for nid in node_ids:
            activity = await db.activities.find_one({"_id": ObjectId(nid)})
            if activity:
                total_duration += activity.get("estimated_duration", 0)
        
        return total_duration


def match_parallel_activity(node_a_name, node_b_name):
    """根据源节点和目标节点匹配合适的并行活动"""
    # 提取关键词进行匹配
    keywords_a = node_a_name.replace("牛奶", "").replace("产品", "").strip()
    keywords_b = node_b_name.replace("牛奶", "").replace("产品", "").strip()
    
    # 尝试精确匹配规则
    for rule_key, activity_info in PARALLEL_ACTIVITY_RULES.items():
        if rule_key == "default":
            continue
        key_parts = rule_key.split("->")
        if len(key_parts) == 2:
            key_a, key_b = key_parts[0], key_parts[1]
            # 精确匹配
            if key_a in keywords_a and key_b in keywords_b:
                print(f"   匹配规则: [{rule_key}] -> {activity_info['name']}")
                return activity_info
            # 完整名称匹配
            if key_a in node_a_name and key_b in node_b_name:
                print(f"   匹配规则: [{rule_key}] -> {activity_info['name']}")
                return activity_info
    
    # 如果没有匹配到，生成动态规则
    print(f"   使用默认规则生成并行活动")
    return PARALLEL_ACTIVITY_RULES["default"]


async def create_bypass_activity(db, driver, process_id, domain, node_a, node_b, original_duration):
    """创建旁路活动节点并建立关系"""
    
    # 根据节点类型匹配合适的并行活动
    parallel_activity = match_parallel_activity(node_a["node_a_name"], node_b["node_b_name"])
    new_activity_name = parallel_activity["name"]
    activity_type = parallel_activity["type"]
    activity_desc = parallel_activity["desc"]
    
    # 根据活动类型决定耗时策略
    # 准备类、沟通类活动通常比主流程短
    if activity_type in ["设备准备", "材料准备", "文档准备", "沟通", "现场准备"]:
        is_critical = False
        new_duration = int(original_duration * 0.6)  # 短40%
        print(f"   策略：{activity_type}活动设计为非关键路径（耗时 {new_duration} 分钟 < 原路径 {original_duration} 分钟）")
    # 质检类、数据分析类可能成为瓶颈
    elif activity_type in ["质检", "数据分析", "质量记录"]:
        is_critical = random.choice([True, False])
        if is_critical:
            new_duration = int(original_duration * 1.3)  # 长30%
            print(f"   策略：{activity_type}活动可能成为关键路径（耗时 {new_duration} 分钟 > 原路径 {original_duration} 分钟）")
        else:
            new_duration = int(original_duration * 0.8)  # 短20%
            print(f"   策略：{activity_type}活动设计为非关键路径（耗时 {new_duration} 分钟 < 原路径 {original_duration} 分钟）")
    else:
        is_critical = False
        new_duration = int(original_duration * 0.7)  # 短30%
        print(f"   策略：{activity_type}活动设计为非关键路径（耗时 {new_duration} 分钟 < 原路径 {original_duration} 分钟）")
    
    # 构造新Activity文档
    new_activity_doc = {
        "name": new_activity_name,
        "description": activity_desc,
        "activity_type": activity_type,
        "sop_steps": [
            {"step_number": 1, "description": "启动旁路", "duration": new_duration // 2},
            {"step_number": 2, "description": "完成旁路", "duration": new_duration // 2}
        ],
        "estimated_duration": new_duration,
        "duration_minutes": new_duration,
        "status": "pending",
        "domain": domain,
        "process_id": process_id,
        "version": 1,
        "is_active": True,
        "required_resources": [],
        "required_personnel": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    if DRY_RUN:
        print(f"   [DRY RUN] 将创建新节点: {new_activity_name} (耗时 {new_duration} 分钟)")
        return None
    
    # MongoDB插入
    result = await db.activities.insert_one(new_activity_doc)
    new_activity_id = str(result.inserted_id)
    print(f"   [OK] MongoDB插入成功: {new_activity_id}")
    
    # Neo4j同步节点
    neo4j_node_query = """
    MERGE (a:Activity {id: $activity_id})
    SET a.name = $name, a.domain = $domain, a.process_id = $process_id
    RETURN a
    """
    async with driver.session() as session:
        await session.run(neo4j_node_query, {
            "activity_id": new_activity_id,
            "name": new_activity_name,
            "domain": domain,
            "process_id": process_id
        })
    print(f"   [OK] Neo4j节点同步成功")
    
    # 创建两条新边：A -> New, New -> B
    edge_query = """
    MATCH (a:Activity {id: $source_id})
    MATCH (b:Activity {id: $target_id})
    MERGE (a)-[r:DEPENDS_ON]->(b)
    SET r.type = 'parallel',
        r.lag_minutes = 0,
        r.status = 'active',
        r.domain = $domain,
        r.process_id = $process_id,
        r.description = $desc
    """
    
    async with driver.session() as session:
        # A -> New
        await session.run(edge_query, {
            "source_id": node_a["node_a_id"],
            "target_id": new_activity_id,
            "domain": domain,
            "process_id": process_id,
            "desc": "旁路分支起点"
        })
        # New -> B
        await session.run(edge_query, {
            "source_id": new_activity_id,
            "target_id": node_b["node_b_id"],
            "domain": domain,
            "process_id": process_id,
            "desc": "旁路分支终点"
        })
    
    print(f"   [OK] Neo4j关系创建成功: {node_a['node_a_name']} -> {new_activity_name} -> {node_b['node_b_name']}")
    
    return {
        "new_node_id": new_activity_id,
        "new_node_name": new_activity_name,
        "duration": new_duration,
        "is_critical": is_critical
    }


async def graft_branches():
    """主函数：执行嫁接操作"""
    print("=" * 70)
    print("分支嫁接脚本 - 为线性流程添加并行分支")
    print("=" * 70)
    
    if DRY_RUN:
        print("\n[!] DRY RUN 模式（不会实际修改数据）")
    
    # 连接数据库
    mongo_client = AsyncIOMotorClient(settings.mongodb_url)
    db = mongo_client[settings.database_name]
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    
    try:
        await driver.verify_connectivity()
        print("[OK] 数据库连接成功\n")
        
        # 查找候选流程
        candidates = await find_candidate_processes(driver)
        
        if not candidates:
            print("\n[ERROR] 未找到符合条件的流程（节点数 > 3）")
            return
        
        grafted_results = []
        
        # 对每个候选流程执行嫁接
        for idx, candidate in enumerate(candidates, 1):
            process_id = candidate["process_id"]
            domain = candidate["domain"]
            
            print(f"\n[2.{idx}] 处理流程: {domain}/{process_id}")
            
            # 找到可嫁接的节点对
            nodes = await find_graftable_nodes(driver, process_id)
            if not nodes:
                print(f"   [WARN] 该流程无法找到合适的嫁接点（可能是纯线性且节点太少）")
                continue
            
            print(f"   选中嫁接点: {nodes['node_a_name']} (A) -> ... -> {nodes['node_b_name']} (B)")
            
            # 计算原路径时长
            original_duration = await calculate_original_path_duration(
                driver, nodes["node_a_id"], nodes["node_b_id"], db
            )
            print(f"   原路径总时长: {original_duration} 分钟")
            
            # 创建旁路节点
            result = await create_bypass_activity(
                db, driver, process_id, domain, nodes, nodes, original_duration
            )
            
            if result:
                grafted_results.append({
                    "process_id": process_id,
                    "domain": domain,
                    "new_node_id": result["new_node_id"],
                    "new_node_name": result["new_node_name"],
                    "duration": result["duration"],
                    "is_critical": result["is_critical"],
                    "from_node": nodes["node_a_name"],
                    "to_node": nodes["node_b_name"]
                })
        
        # 输出结果总结
        print("\n" + "=" * 70)
        print("嫁接操作完成")
        print("=" * 70)
        
        if not grafted_results:
            print("\n没有成功嫁接任何分支")
        else:
            print(f"\n成功嫁接 {len(grafted_results)} 个分支:\n")
            for r in grafted_results:
                critical_mark = "[关键路径]" if r["is_critical"] else "[非关键路径]"
                print(f"  * 流程: {r['domain']}/{r['process_id']}")
                print(f"    分支: {r['from_node']} -> [{r['new_node_name']}] -> {r['to_node']}")
                print(f"    节点ID: {r['new_node_id']}")
                print(f"    耗时: {r['duration']} 分钟 {critical_mark}")
                print()
        
        print("提示：刷新前端页面查看新增的并行分支和CPM关键路径变化")
    
    except Exception as e:
        print(f"\n[ERROR] 执行失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        mongo_client.close()
        await driver.close()


if __name__ == "__main__":
    asyncio.run(graft_branches())
