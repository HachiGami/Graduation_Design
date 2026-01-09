import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from neo4j import AsyncGraphDatabase
import re

MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "dairy_production"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

# 领域知识：设备与操作的关联
EQUIPMENT_OPERATION_MAP = {
    '显微镜': ['检测', '观察', '分析', '微生物', '细胞'],
    '离心机': ['离心', '分离', '提取'],
    'pH计': ['pH', '酸碱', '检测', '测定'],
    '温度': ['温度', '加热', '冷却', '保温', '控温'],
    '泵': ['输送', '灌装', '抽取', '加料', '投料'],
    '罐': ['储存', '发酵', '反应', '搅拌', '加工'],
    '槽': ['储存', '发酵', '反应', '搅拌', '加工'],
    '打印': ['打印', '标签', '喷码'],
    '扫描': ['扫描', '识别', '录入', '检验'],
    'GPS': ['定位', '追踪', '导航', '路线'],
    '记录': ['记录', '监控', '数据'],
    '称': ['称重', '计量', '测重'],
    '秤': ['称重', '计量', '测重'],
    '传感': ['监控', '检测', '记录'],
    '清洗': ['清洗', '清洁', '消毒'],
    '输送': ['输送', '传送', '运输'],
    '包装': ['包装', '封装', '装箱'],
}

def semantic_match_score(resource_name, step_description):
    """
    改进的语义匹配算法
    """
    if not resource_name or not step_description:
        return 0.0
    
    resource_lower = resource_name.lower()
    step_lower = step_description.lower()
    
    score = 0.0
    
    # 1. 直接包含匹配（高权重）
    if resource_lower in step_lower or step_lower in resource_lower:
        score = max(score, 0.9)
    
    # 2. 基于领域知识的匹配
    for equipment_key, operations in EQUIPMENT_OPERATION_MAP.items():
        if equipment_key in resource_lower:
            for operation in operations:
                if operation in step_lower:
                    score = max(score, 0.8)
                    break
    
    # 3. 词级别的交集匹配
    # 简单分词（按常见分隔符）
    import re
    resource_words = set(re.findall(r'[\u4e00-\u9fa5]+', resource_lower))
    step_words = set(re.findall(r'[\u4e00-\u9fa5]+', step_lower))
    
    if resource_words and step_words:
        common_words = resource_words & step_words
        if common_words:
            overlap_ratio = len(common_words) / min(len(resource_words), len(step_words))
            score = max(score, overlap_ratio * 0.7)
    
    # 4. 字符级别的包含（弱匹配）
    for i in range(2, len(resource_lower)):
        substr = resource_lower[:i]
        if len(substr) >= 2 and substr in step_lower:
            score = max(score, 0.3)
    
    return score

def is_passive_step(step_description):
    """
    判断是否是被动步骤（无需人工干预）
    """
    passive_indicators = ['静置', '等待', '发酵', '冷藏', '冷却', '保温', '自然', '放置', '储存', '陈化', '发酵']
    step_lower = step_description.lower()
    return any(indicator in step_lower for indicator in passive_indicators)

def is_container_equipment(resource_name):
    """
    判断是否是容器类设备（占用整个活动周期）
    """
    container_indicators = ['罐', '槽', '池', '箱', '仓', '桶', '容器', 'tank', 'vessel', 'container']
    name_lower = resource_name.lower()
    return any(indicator in name_lower for indicator in container_indicators)

def is_monitoring_equipment(resource_name):
    """
    判断是否是监控类设备（通常全程占用）
    """
    monitoring_indicators = ['监控', '记录仪', '传感器', 'GPS', '追踪']
    name_lower = resource_name.lower()
    return any(indicator in name_lower for indicator in monitoring_indicators)

async def calculate_smart_durations():
    mongo_client = AsyncIOMotorClient(MONGODB_URL)
    mongo_db = mongo_client[DATABASE_NAME]
    neo4j_driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        print("=" * 80)
        print("智能资源占用时长计算")
        print("=" * 80)
        
        # 读取所有活动的 SOP
        activities_sop = {}
        async for activity in mongo_db.activities.find({}):
            if 'name' in activity and 'sop_steps' in activity:
                activities_sop[activity['name']] = {
                    'sop_steps': activity['sop_steps'],
                    'total_duration': activity.get('estimated_duration', 60)
                }
        
        print(f"\n加载了 {len(activities_sop)} 个活动的 SOP 数据")
        
        async with neo4j_driver.session() as session:
            # 处理设备（USES -> Resource with type='设备'）
            print("\n" + "=" * 80)
            print("[1] 处理设备占用时长")
            print("=" * 80)
            
            result = await session.run("""
                MATCH (a:Activity)-[r:USES]->(res:Resource)
                WHERE res.type CONTAINS '设'
                RETURN elementId(r) as rel_id, a.name as activity, res.name as resource
            """)
            equipment_rels = await result.data()
            
            print(f"\n找到 {len(equipment_rels)} 条设备关系\n")
            
            for rel in equipment_rels:
                activity_name = rel['activity']
                resource_name = rel['resource']
                
                if activity_name not in activities_sop:
                    continue
                
                sop_data = activities_sop[activity_name]
                sop_steps = sop_data['sop_steps']
                total_duration = sop_data['total_duration']
                
                print(f"> Activity: [{activity_name}] | Equipment: [{resource_name}]")
                
                # 计算每个步骤的匹配度
                matched_steps = []
                total_matched_duration = 0
                
                for step in sop_steps:
                    step_desc = step.get('description', '')
                    step_duration = step.get('duration', 0)
                    
                    score = semantic_match_score(resource_name, step_desc)
                    
                    if score > 0.25:  # 降低匹配阈值
                        matched_steps.append(step)
                        total_matched_duration += step_duration
                        print(f"  - Step '{step_desc}'({step_duration}m): MATCH (score={score:.2f})")
                    else:
                        print(f"  - Step '{step_desc}'({step_duration}m): NO MATCH (score={score:.2f})")
                
                # 决策逻辑
                match_ratio = len(matched_steps) / max(len(sop_steps), 1)
                
                if is_container_equipment(resource_name):
                    # 容器类设备：全程占用
                    final_duration = total_duration
                    print(f"  >> 判定：容器类设备 -> 全程占用")
                elif is_monitoring_equipment(resource_name):
                    # 监控类设备：全程占用
                    final_duration = total_duration
                    print(f"  >> 判定：监控类设备 -> 全程占用")
                elif match_ratio > 0.6:
                    # 大部分步骤匹配：全程占用
                    final_duration = total_duration
                    print(f"  >> 判定：核心设备 (匹配率={match_ratio:.1%}) -> 全程占用")
                elif total_matched_duration > 0:
                    # 工具类设备：累加匹配步骤
                    final_duration = total_matched_duration
                    print(f"  >> 判定：工具类设备 -> 累加匹配步骤")
                else:
                    # 没有匹配到任何步骤，使用默认值（可能是辅助设备）
                    final_duration = max(1, int(total_duration * 0.3))  # 默认占用30%时间
                    print(f"  >> 判定：辅助设备 -> 默认占用30%")
                
                print(f"  = Final Duration: {final_duration}m\n")
                
                # 更新数据库
                await session.run("""
                    MATCH ()-[r]->()
                    WHERE elementId(r) = $rel_id
                    SET r.duration = $duration
                """, rel_id=rel['rel_id'], duration=final_duration)
            
            # 处理人员（ASSIGNS -> Personnel）
            print("=" * 80)
            print("[2] 处理人员占用时长")
            print("=" * 80)
            
            result = await session.run("""
                MATCH (a:Activity)-[r:ASSIGNS]->(p:Personnel)
                RETURN elementId(r) as rel_id, a.name as activity, p.name as personnel
            """)
            personnel_rels = await result.data()
            
            print(f"\n找到 {len(personnel_rels)} 条人员关系\n")
            
            for rel in personnel_rels:
                activity_name = rel['activity']
                personnel_name = rel['personnel']
                
                if activity_name not in activities_sop:
                    continue
                
                sop_data = activities_sop[activity_name]
                sop_steps = sop_data['sop_steps']
                
                print(f"> Activity: [{activity_name}] | Personnel: [{personnel_name}]")
                
                # 人员只累加主动操作步骤
                active_duration = 0
                
                for step in sop_steps:
                    step_desc = step.get('description', '')
                    step_duration = step.get('duration', 0)
                    
                    if is_passive_step(step_desc):
                        print(f"  - Step '{step_desc}'({step_duration}m): SKIP (被动步骤)")
                    else:
                        active_duration += step_duration
                        print(f"  - Step '{step_desc}'({step_duration}m): INCLUDE (主动步骤)")
                
                final_duration = active_duration if active_duration > 0 else sop_data['total_duration']
                print(f"  = Final Duration: {final_duration}m\n")
                
                # 更新数据库
                await session.run("""
                    MATCH ()-[r]->()
                    WHERE elementId(r) = $rel_id
                    SET r.duration = $duration
                """, rel_id=rel['rel_id'], duration=final_duration)
            
            # 验证结果
            print("=" * 80)
            print("验证结果")
            print("=" * 80)
            
            print("\n[设备占用时长统计 - 前20条]")
            result = await session.run("""
                MATCH (a:Activity)-[r:USES]->(res:Resource)
                WHERE res.type CONTAINS '设'
                RETURN a.name as activity, res.name as resource, r.duration as duration
                ORDER BY a.name, res.name
                LIMIT 20
            """)
            async for record in result:
                print(f"  {record['activity']} -> {record['resource']}: {record['duration']}m")
            
            print("\n[人员占用时长统计 - 前20条]")
            result = await session.run("""
                MATCH (a:Activity)-[r:ASSIGNS]->(p:Personnel)
                RETURN a.name as activity, p.name as personnel, r.duration as duration
                ORDER BY a.name, p.name
                LIMIT 20
            """)
            async for record in result:
                print(f"  {record['activity']} -> {record['personnel']}: {record['duration']}m")
            
            print("\n[统计分析]")
            result = await session.run("""
                MATCH (a:Activity)-[r:USES]->(res:Resource)
                WHERE res.type CONTAINS '设'
                RETURN min(r.duration) as min_dur, max(r.duration) as max_dur, avg(r.duration) as avg_dur
            """)
            record = await result.single()
            print(f"  设备占用时长: 最小={record['min_dur']}m, 最大={record['max_dur']}m, 平均={record['avg_dur']:.1f}m")
        
        print("\n" + "=" * 80)
        print("[完成] 智能资源占用时长计算完成!")
        print("=" * 80)
        
    finally:
        await neo4j_driver.close()
        mongo_client.close()

if __name__ == "__main__":
    asyncio.run(calculate_smart_durations())
