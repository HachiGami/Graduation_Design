from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from datetime import datetime


class SchedulerService:
    """
    调度服务：基于资源约束的自动排程与风险检测
    实现 CPM + 贪心资源分配算法
    """
    
    def __init__(self, db, neo4j_driver):
        self.db = db
        self.neo4j_driver = neo4j_driver
    
    async def calculate_schedule(
        self, 
        process_id: Optional[str] = None
    ) -> Dict:
        """
        计算排程并检测动态风险
        
        Returns:
            {
                "equipment_shortages": [...],
                "personnel_overloads": [...]
            }
        """
        try:
            # 1. 加载活动和依赖
            activities = await self._load_activities(process_id)
            if not activities:
                return {
                    "equipment_shortages": [],
                    "personnel_overloads": []
                }
            
            dependencies = await self._load_dependencies(process_id)
            
            # 2. 拓扑排序 + CPM 计算
            sorted_activities = self._topological_sort(activities, dependencies)
            if not sorted_activities:
                # 存在环或无法排序
                return {
                    "equipment_shortages": [],
                    "personnel_overloads": []
                }
            
            self._calculate_es_ef(sorted_activities, dependencies)
            
            # 3. 构建时间轴并检测冲突
            equipment_shortages = await self._detect_equipment_shortages(
                sorted_activities, process_id
            )
            personnel_overloads = await self._detect_personnel_overloads(
                sorted_activities, process_id
            )
            
            return {
                "equipment_shortages": equipment_shortages,
                "personnel_overloads": personnel_overloads
            }
            
        except Exception as e:
            print(f"Error in calculate_schedule: {e}")
            return {
                "equipment_shortages": [],
                "personnel_overloads": []
            }
    
    async def _load_activities(self, process_id: Optional[str]) -> List[Dict]:
        """从 MongoDB 加载活动"""
        collection = self.db["activities"]
        query = {"is_active": True}
        if process_id:
            query["process_id"] = process_id
        
        activities = []
        async for activity in collection.find(query):
            activity["id"] = str(activity["_id"])
            activities.append(activity)
        
        return activities
    
    async def _load_dependencies(self, process_id: Optional[str]) -> List[Dict]:
        """从 Neo4j 加载依赖关系"""
        async with self.neo4j_driver.session() as session:
            query = """
            MATCH (source:Activity)-[dep:DEPENDS_ON]->(target:Activity)
            WHERE source.status = 'active' AND target.status = 'active'
            """
            if process_id:
                query += " AND source.process_id = $process_id AND target.process_id = $process_id"
            
            query += """
            RETURN source.mongo_id as source_id, 
                   target.mongo_id as target_id, 
                   COALESCE(dep.lag_minutes, 0) as lag_minutes
            """
            
            params = {"process_id": process_id} if process_id else {}
            result = await session.run(query, params)
            
            dependencies = []
            async for record in result:
                dependencies.append({
                    "source_id": record["source_id"],
                    "target_id": record["target_id"],
                    "lag_minutes": record["lag_minutes"]
                })
            
            return dependencies
    
    def _topological_sort(
        self, 
        activities: List[Dict], 
        dependencies: List[Dict]
    ) -> List[Dict]:
        """
        拓扑排序（Kahn算法）
        检测环并返回排序后的活动列表
        """
        # 构建邻接表和入度表
        activity_map = {act["id"]: act for act in activities}
        adj_list = defaultdict(list)
        in_degree = {act["id"]: 0 for act in activities}
        
        for dep in dependencies:
            source_id = dep["source_id"]
            target_id = dep["target_id"]
            if source_id in activity_map and target_id in activity_map:
                adj_list[source_id].append(dep)
                in_degree[target_id] += 1
        
        # Kahn算法
        queue = [act_id for act_id, degree in in_degree.items() if degree == 0]
        sorted_acts = []
        
        while queue:
            current_id = queue.pop(0)
            sorted_acts.append(activity_map[current_id])
            
            for dep in adj_list[current_id]:
                target_id = dep["target_id"]
                in_degree[target_id] -= 1
                if in_degree[target_id] == 0:
                    queue.append(target_id)
        
        # 检测环
        if len(sorted_acts) != len(activities):
            print(f"Warning: Cycle detected in dependencies")
            return []
        
        return sorted_acts
    
    def _calculate_es_ef(
        self, 
        sorted_activities: List[Dict], 
        dependencies: List[Dict]
    ):
        """
        CPM 正推：计算每个活动的 ES (最早开始) 和 EF (最早结束)
        直接修改 activities 对象，添加 es 和 ef 字段
        """
        # 构建前驱映射
        predecessors = defaultdict(list)
        for dep in dependencies:
            predecessors[dep["target_id"]].append(dep)
        
        # 初始化
        for act in sorted_activities:
            act["es"] = 0
            act["ef"] = 0
        
        # 正推计算
        activity_map = {act["id"]: act for act in sorted_activities}
        
        for act in sorted_activities:
            # 计算 ES = max(前驱的EF + lag)
            if act["id"] in predecessors:
                max_pred_ef = 0
                for dep in predecessors[act["id"]]:
                    source_id = dep["source_id"]
                    if source_id in activity_map:
                        pred_ef = activity_map[source_id]["ef"]
                        lag = dep.get("lag_minutes", 0)
                        max_pred_ef = max(max_pred_ef, pred_ef + lag)
                act["es"] = max_pred_ef
            
            # 计算 EF = ES + duration
            duration = act.get("estimated_duration", 0)
            act["ef"] = act["es"] + duration
    
    async def _detect_equipment_shortages(
        self, 
        activities: List[Dict], 
        process_id: Optional[str]
    ) -> List[Dict]:
        """
        检测设备资源短缺
        """
        # 1. 构建时间轴：每分钟的资源需求
        timeline = defaultdict(lambda: defaultdict(list))  # {minute: {resource_id: [activity_ids]}}
        
        for act in activities:
            es = act.get("es", 0)
            ef = act.get("ef", 0)
            required_resources = act.get("required_resources", [])
            
            for res_id in required_resources:
                for minute in range(int(es), int(ef)):
                    timeline[minute][res_id].append(act["id"])
        
        # 2. 加载资源库存
        resource_map = await self._load_resource_quantities(process_id)
        
        # 3. 检测冲突
        shortages = []
        checked_windows = set()  # 避免重复报告相同时间窗口
        
        for minute in sorted(timeline.keys()):
            for resource_id, activity_ids in timeline[minute].items():
                demand = len(activity_ids)  # 假设每个活动需要1个资源
                available = resource_map.get(resource_id, 0)
                
                if demand > available:
                    gap = demand - available
                    time_key = (minute, resource_id)
                    
                    if time_key not in checked_windows:
                        checked_windows.add(time_key)
                        
                        # 获取资源名称
                        resource_name = await self._get_resource_name(resource_id)
                        
                        shortages.append({
                            "type": "equipment_shortage",
                            "time_window": self._format_time_window(minute),
                            "gap": float(gap),
                            "activity_ids": activity_ids[:10],  # 限制数量
                            "description": f"{resource_name}在此时段需求{demand}个，库存仅{available}个，缺口{gap}个"
                        })
        
        return shortages
    
    async def _detect_personnel_overloads(
        self, 
        activities: List[Dict], 
        process_id: Optional[str]
    ) -> List[Dict]:
        """
        检测人力超载
        """
        # 1. 构建时间轴：每分钟的人员需求
        timeline = defaultdict(lambda: defaultdict(list))  # {minute: {skill: [activity_ids]}}
        
        for act in activities:
            es = act.get("es", 0)
            ef = act.get("ef", 0)
            required_personnel = act.get("required_personnel", [])
            
            # 获取人员技能
            for person_id in required_personnel:
                person = await self._get_personnel(person_id)
                if person:
                    skills = person.get("skills", [])
                    for skill in skills:
                        for minute in range(int(es), int(ef)):
                            timeline[minute][skill].append(act["id"])
        
        # 2. 统计可用人员数量（按技能）
        skill_personnel_count = await self._count_personnel_by_skill(process_id)
        
        # 3. 检测超载
        overloads = []
        checked_windows = set()
        
        for minute in sorted(timeline.keys()):
            for skill, activity_ids in timeline[minute].items():
                demand = len(activity_ids)
                available = skill_personnel_count.get(skill, 0)
                
                if available > 0 and demand > available:
                    overload_ratio = demand / available
                    time_key = (minute, skill)
                    
                    if time_key not in checked_windows:
                        checked_windows.add(time_key)
                        
                        overloads.append({
                            "type": "personnel_overload",
                            "time_window": self._format_time_window(minute),
                            "gap": round(overload_ratio - 1, 2),
                            "activity_ids": activity_ids[:10],
                            "description": f"{skill}技能在此时段需求{demand}人，可用{available}人，超载{overload_ratio:.1f}倍"
                        })
        
        return overloads
    
    async def _load_resource_quantities(self, process_id: Optional[str]) -> Dict[str, float]:
        """加载资源库存映射"""
        collection = self.db["resources"]
        query = {"is_active": True, "status": "available"}
        if process_id:
            query["process_id"] = process_id
        
        resource_map = {}
        async for resource in collection.find(query):
            resource_id = str(resource["_id"])
            resource_map[resource_id] = resource.get("quantity", 0)
        
        return resource_map
    
    async def _get_resource_name(self, resource_id: str) -> str:
        """获取资源名称"""
        from bson import ObjectId
        collection = self.db["resources"]
        try:
            resource = await collection.find_one({"_id": ObjectId(resource_id)})
            return resource.get("name", "未知资源") if resource else "未知资源"
        except:
            return "未知资源"
    
    async def _get_personnel(self, person_id: str) -> Optional[Dict]:
        """获取人员信息"""
        from bson import ObjectId
        collection = self.db["personnel"]
        try:
            return await collection.find_one({"_id": ObjectId(person_id)})
        except:
            return None
    
    async def _count_personnel_by_skill(self, process_id: Optional[str]) -> Dict[str, int]:
        """统计每种技能的可用人员数量"""
        collection = self.db["personnel"]
        query = {"status": {"$in": ["available", "active"]}}
        
        skill_count = defaultdict(int)
        async for person in collection.find(query):
            skills = person.get("skills", [])
            for skill in skills:
                skill_count[skill] += 1
        
        return dict(skill_count)
    
    def _format_time_window(self, minute: int) -> str:
        """格式化时间窗口"""
        start = minute
        end = minute + 60  # 假设时间窗口为1小时
        return f"T+{start}~T+{end}"
