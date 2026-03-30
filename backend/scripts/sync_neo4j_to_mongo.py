import random
from datetime import datetime, timedelta
from neo4j import GraphDatabase
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# --- 数据库配置 ---
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"  # 已根据用户反馈更新

MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB_NAME = "dairy_production"

# --- 业务常量定义 ---
DAIRY_SKILLS = {
    "生产员": ["无菌操作", "设备监控", "基础维修", "物料搬运"],
    "化验员": ["质量检测", "样本采集", "理化分析", "微生物培养"],
    "工程师": ["设备维护", "PLC编程", "系统优化", "预防性维修"],
    "班组长": ["生产调度", "人员管理", "安全审计", "报表汇总"]
}

DAIRY_SOP_TEMPLATES = [
    ["检查设备参数", "启动巴氏杀菌", "监控温度曲线", "记录产出数据"],
    ["清洗收奶管道", "开启离心净乳机", "调整标准化参数", "取样进行脂肪含量检测"],
    ["预热喷雾干燥塔", "开启高压泵进料", "调节进出风温度", "收集奶粉成品"],
    ["检查包装卷膜", "启动自动灌装机", "执行在线称重", "喷码并装箱"]
]

# --- 工具函数 ---
def generate_phone():
    return f"1{random.randint(3, 9)}{random.randint(100000000, 999999999)}"

def get_random_date(days_back=365):
    if days_back == 0:
        return datetime.now()
    if days_back > 0:
        return datetime.now() - timedelta(days=random.randint(0, days_back))
    else:
        # 处理负数情况，即未来日期
        return datetime.now() + timedelta(days=random.randint(0, abs(days_back)))

class DairyDataSyncer:
    def __init__(self):
        self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client[MONGO_DB_NAME]
        
        # 统计数据
        self.stats = {"Personnel": 0, "Activity": 0, "Resource": 0}

    def close(self):
        self.neo4j_driver.close()
        self.mongo_client.close()

    def sync_personnel(self):
        print("开始同步 Personnel (人员)...")
        with self.neo4j_driver.session() as session:
            result = session.run("MATCH (n:Personnel) RETURN n.id as id, n.name as name, n.role as role, n.department as department")
            for record in result:
                p_id = record["id"]
                # 检查 Mongo 是否存在
                if not self.db.personnel.find_one({"personnel_id": p_id}):
                    role = record["role"] or "生产员"
                    doc = {
                        "personnel_id": p_id,
                        "name": record["name"],
                        "role": role,
                        "department": record["department"] or "生产部",
                        "contact": generate_phone(),
                        "status": random.choice(["在岗", "休息", "请假"]),
                        "skills": random.sample(DAIRY_SKILLS.get(role, DAIRY_SKILLS["生产员"]), k=min(3, len(DAIRY_SKILLS.get(role, [])))),
                        "created_at": datetime.now()
                    }
                    self.db.personnel.insert_one(doc)
                    self.stats["Personnel"] += 1

    def sync_activities(self):
        print("开始同步 Activity (生产活动)...")
        with self.neo4j_driver.session() as session:
            result = session.run("MATCH (n:Activity) RETURN n.id as id, n.name as name, n.process_id as process_id, n.domain as domain")
            for record in result:
                a_id = record["id"]
                if not self.db.activities.find_one({"activity_id": a_id}):
                    sop = random.choice(DAIRY_SOP_TEMPLATES)
                    doc = {
                        "activity_id": a_id,
                        "name": record["name"],
                        "process_id": record["process_id"],
                        "domain": record["domain"],
                        "description": f"针对 {record['name']} 的标准化生产环节，确保乳品质量符合国标。",
                        "sop_steps": [f"步骤{i+1}: {step}" for i, step in enumerate(sop)],
                        "estimated_duration": random.randint(30, 240),
                        "status": random.choice(["pending", "in_progress", "completed"]),
                        "updated_at": datetime.now()
                    }
                    self.db.activities.insert_one(doc)
                    self.stats["Activity"] += 1

    def sync_resources(self):
        print("开始同步 Resource (资源)...")
        with self.neo4j_driver.session() as session:
            result = session.run("MATCH (n:Resource) RETURN n.id as id, n.name as name, n.resource_type as type")
            for record in result:
                r_id = record["id"]
                r_type = record["type"]
                if not self.db.resources.find_one({"resource_id": r_id}):
                    doc = {
                        "resource_id": r_id,
                        "name": record["name"],
                        "resource_type": r_type,
                    }
                    
                    if r_type == "RawMaterial":
                        doc.update({
                            "unit": random.choice(["升", "千克", "吨"]),
                            "inventory_level": round(random.uniform(100, 5000), 2),
                            "supplier": {
                                "name": f"蒙牛/伊利合作牧场_{random.randint(1, 10)}号",
                                "contact": generate_phone()
                            },
                            "expiration_date": get_random_date(days_back=-30)
                        })
                    elif r_type == "Equipment":
                        doc.update({
                            "status": random.choice(["运行中", "空闲", "需维保"]),
                            "last_maintenance_date": get_random_date(days_back=90),
                            "specifications": {
                                "capacity": f"{random.randint(5, 50)}T/h",
                                "power": f"{random.randint(10, 100)}kW",
                                "brand": random.choice(["利乐", "GEA", "SPX"])
                            }
                        })
                    
                    self.db.resources.insert_one(doc)
                    self.stats["Resource"] += 1

    def run(self):
        try:
            print("--- 开始数据库对齐同步任务 ---")
            self.sync_personnel()
            self.sync_activities()
            self.sync_resources()
            print("\n--- 同步任务完成 ---")
            print(f"成功补全 Personnel 集合: {self.stats['Personnel']} 条文档")
            print(f"成功补全 Activity 集合: {self.stats['Activity']} 条文档")
            print(f"成功补全 Resource 集合: {self.stats['Resource']} 条文档")
        except Exception as e:
            print(f"同步过程中发生错误: {e}")
        finally:
            self.close()

if __name__ == '__main__':
    syncer = DairyDataSyncer()
    syncer.run()
