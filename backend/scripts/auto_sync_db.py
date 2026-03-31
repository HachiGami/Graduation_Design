import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from neo4j import GraphDatabase
from pymongo import MongoClient

# Add backend root to import path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings


DEFAULT_WORKING_HOURS = [
    {"start_time": "08:00", "end_time": "11:00"},
    {"start_time": "13:00", "end_time": "18:00"},
]

DEFAULT_ROLES = ["操作员", "清洁工", "质检员", "维修工"]
LEAVE_OR_MAINT_OPTIONS = [["1天后"], ["2天后"], ["1天后", "2天后"]]


def to_object_id(value: Optional[str]) -> Optional[ObjectId]:
    if value and ObjectId.is_valid(value):
        return ObjectId(value)
    return None


def mongo_filter_by_neo4j_id(neo4j_id: str) -> Dict[str, Any]:
    obj_id = to_object_id(neo4j_id)
    if obj_id:
        return {"_id": obj_id}
    return {"neo4j_id": neo4j_id}


def pick_sample(items: List[Dict[str, Any]], size: int) -> List[Dict[str, Any]]:
    if not items or size <= 0:
        return []
    return random.sample(items, k=min(size, len(items)))


class AutoSyncDB:
    def __init__(self) -> None:
        self.mongo_client = MongoClient(settings.mongodb_url)
        self.db = self.mongo_client[settings.database_name]
        self.neo4j_driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        self.stats: Dict[str, int] = {
            "activities_upserted": 0,
            "personnel_upserted": 0,
            "assets_upserted": 0,
            "personnel_allocations": 0,
            "equipment_allocations": 0,
            "risk_activities": 0,
        }

    def close(self) -> None:
        self.neo4j_driver.close()
        self.mongo_client.close()

    def fetch_activities(self) -> List[Dict[str, Any]]:
        query = """
        MATCH (a:Activity)
        RETURN COALESCE(a.id, elementId(a)) AS id,
               a.name AS name,
               a.domain AS domain,
               a.process_id AS process_id,
               a.activity_type AS activity_type,
               a.status AS status
        """
        with self.neo4j_driver.session() as session:
            result = session.run(query)
            return [dict(record) for record in result]

    def fetch_personnel(self) -> List[Dict[str, Any]]:
        query = """
        MATCH (p:Personnel)
        RETURN COALESCE(p.id, elementId(p)) AS id,
               p.name AS name,
               p.role AS role,
               p.status AS status
        """
        with self.neo4j_driver.session() as session:
            result = session.run(query)
            rows = [dict(record) for record in result]

        for row in rows:
            if not row.get("role"):
                row["role"] = random.choice(DEFAULT_ROLES)
        return rows

    def fetch_equipment(self) -> List[Dict[str, Any]]:
        query = """
        MATCH (e:Equipment)
        RETURN COALESCE(e.id, elementId(e)) AS id,
               e.name AS name,
               e.model AS model,
               e.status AS status
        """
        with self.neo4j_driver.session() as session:
            result = session.run(query)
            rows = [dict(record) for record in result]

        for row in rows:
            if not row.get("model"):
                row["model"] = row.get("name") or "通用设备"
        return rows

    def fetch_materials(self) -> List[Dict[str, Any]]:
        query = """
        MATCH (m:Material)
        RETURN COALESCE(m.id, elementId(m)) AS id,
               m.name AS name,
               m.model AS model,
               m.unit AS unit,
               m.quantity AS quantity
        """
        with self.neo4j_driver.session() as session:
            result = session.run(query)
            rows = [dict(record) for record in result]

        for row in rows:
            if not row.get("model"):
                row["model"] = row.get("name") or "通用原料"
            if not row.get("unit"):
                row["unit"] = "kg"
        return rows

    def bootstrap_personnel_from_mongo(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        with self.neo4j_driver.session() as session:
            mongo_people = list(self.db.personnel.find({}))
            if not mongo_people:
                now = datetime.utcnow()
                seed_people = [
                    {"name": "王强", "role": "操作员", "age": 28, "gender": "男", "native_place": "山东", "hire_date": "2020-05-12", "education": "大专", "salary": 6500.0},
                    {"name": "李敏", "role": "操作员", "age": 25, "gender": "女", "native_place": "江苏", "hire_date": "2021-08-20", "education": "本科", "salary": 7000.0},
                    {"name": "赵工", "role": "维修工", "age": 45, "gender": "男", "native_place": "河南", "hire_date": "2015-03-10", "education": "高中", "salary": 8500.0},
                    {"name": "陈洁", "role": "清洁工", "age": 50, "gender": "女", "native_place": "四川", "hire_date": "2018-11-05", "education": "初中", "salary": 4000.0},
                ]
                for seed in seed_people:
                    result = self.db.personnel.insert_one(
                        {
                            "name": seed["name"],
                            "role": seed["role"],
                            "responsibility": f"{seed['role']}职责执行",
                            "skills": [seed["role"]],
                            "work_hours": "08:00-18:00",
                            "assigned_tasks": [],
                            "status": "active",
                            "upcoming_leaves": [],
                            "age": seed["age"],
                            "gender": seed["gender"],
                            "native_place": seed["native_place"],
                            "hire_date": seed["hire_date"],
                            "education": seed["education"],
                            "salary": seed["salary"],
                            "created_at": now,
                            "updated_at": now,
                        }
                    )
                    mongo_people.append({"_id": result.inserted_id, **seed, "status": "active"})

            for person in mongo_people:
                pid = str(person.get("_id") or person.get("neo4j_id"))
                role = person.get("role") or random.choice(DEFAULT_ROLES)
                name = person.get("name") or f"人员-{pid[-4:]}"
                status = person.get("status") or "active"
                session.run(
                    """
                    MERGE (p:Personnel {id: $id})
                    SET p.name = $name,
                        p.role = $role,
                        p.status = $status
                    """,
                    {"id": pid, "name": name, "role": role, "status": status},
                )
                rows.append({"id": pid, "name": name, "role": role, "status": status})
        return rows

    def bootstrap_assets_from_mongo(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        materials: List[Dict[str, Any]] = []
        equipment: List[Dict[str, Any]] = []

        with self.neo4j_driver.session() as session:
            mongo_assets = list(self.db.assets.find({}))
            if not mongo_assets:
                now = datetime.utcnow()
                seed_assets = [
                    {"name": "鲜奶原料A", "model": "鲜奶原料A", "asset_type": "material", "unit": "kg", "quantity": 5000},
                    {"name": "包装盒B", "model": "包装盒B", "asset_type": "material", "unit": "箱", "quantity": 800},
                    {"name": "巴氏杀菌机-01", "model": "巴氏杀菌机", "asset_type": "equipment"},
                    {"name": "喷码机-01", "model": "喷码机", "asset_type": "equipment"},
                ]
                for seed in seed_assets:
                    result = self.db.assets.insert_one(
                        {
                            "name": seed["name"],
                            "model": seed["model"],
                            "asset_type": seed["asset_type"],
                            "status": "idle" if seed["asset_type"] == "equipment" else "available",
                            "specification": None,
                            "supplier": None,
                            "quantity": seed.get("quantity"),
                            "unit": seed.get("unit"),
                            "upcoming_maintenance": [],
                            "created_at": now,
                            "updated_at": now,
                        }
                    )
                    mongo_assets.append({"_id": result.inserted_id, **seed, "status": "idle"})

            for asset in mongo_assets:
                asset_id = str(asset.get("_id") or asset.get("neo4j_id"))
                asset_type = asset.get("asset_type")
                name = asset.get("name") or f"资产-{asset_id[-4:]}"
                model = asset.get("model") or name

                if asset_type == "equipment":
                    status = asset.get("status") or "idle"
                    session.run(
                        """
                        MERGE (e:Equipment {id: $id})
                        SET e.name = $name,
                            e.model = $model,
                            e.status = $status
                        """,
                        {"id": asset_id, "name": name, "model": model, "status": status},
                    )
                    equipment.append({"id": asset_id, "name": name, "model": model, "status": status})
                elif asset_type == "material":
                    unit = asset.get("unit") or "kg"
                    quantity = float(asset.get("quantity") or 0)
                    session.run(
                        """
                        MERGE (m:Material {id: $id})
                        SET m.name = $name,
                            m.model = $model,
                            m.unit = $unit,
                            m.quantity = $quantity
                        """,
                        {"id": asset_id, "name": name, "model": model, "unit": unit, "quantity": quantity},
                    )
                    materials.append(
                        {
                            "id": asset_id,
                            "name": name,
                            "model": model,
                            "unit": unit,
                            "quantity": quantity,
                        }
                    )
        return materials, equipment

    def build_requirements(
        self,
        activity: Dict[str, Any],
        materials: List[Dict[str, Any]],
        personnel: List[Dict[str, Any]],
        equipment: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        material_count = 1 if len(materials) < 2 else random.randint(1, min(2, len(materials)))
        selected_materials = pick_sample(materials, material_count)
        material_requirements = []
        for material in selected_materials:
            material_requirements.append(
                {
                    "material_model": material["model"],
                    "hourly_consumption_rate": round(random.uniform(5.0, 30.0), 2),
                    "unit": material.get("unit", "kg"),
                }
            )

        role_pool = sorted({p["role"] for p in personnel if p.get("role")}) or DEFAULT_ROLES
        selected_roles = random.sample(role_pool, k=min(len(role_pool), random.randint(1, 2)))
        personnel_requirements = [
            {
                "role": role,
                "count": random.randint(1, 3),
            }
            for role in selected_roles
        ]

        model_pool = [e["model"] for e in equipment if e.get("model")]
        if not model_pool:
            model_pool = ["巴氏杀菌机", "喷码机", "无菌灌装线"]
        selected_models = random.sample(model_pool, k=min(len(model_pool), random.randint(1, 2)))
        equipment_requirements = [
            {
                "equipment_model": model,
                "count": random.randint(1, 2),
            }
            for model in selected_models
        ]

        return material_requirements, personnel_requirements, equipment_requirements

    def clear_existing_allocation_relationships(self) -> None:
        with self.neo4j_driver.session() as session:
            session.run("MATCH (:Personnel)-[r:ASSIGNED_TO]->(:Activity) DELETE r")
            session.run("MATCH (:Equipment)-[r:USED_BY]->(:Activity) DELETE r")

    def create_allocations(
        self,
        activities_payload: List[Dict[str, Any]],
        personnel: List[Dict[str, Any]],
        equipment: List[Dict[str, Any]],
    ) -> None:
        activity_ids = [item["id"] for item in activities_payload]
        risk_count = max(1, len(activity_ids) // 4) if activity_ids else 0
        risk_activity_ids = set(random.sample(activity_ids, k=risk_count)) if risk_count else set()
        self.stats["risk_activities"] = len(risk_activity_ids)

        with self.neo4j_driver.session() as session:
            for item in activities_payload:
                activity_id = item["id"]
                is_risk_activity = activity_id in risk_activity_ids

                shortage_forced = False
                for req in item["personnel_requirements"]:
                    role = req["role"]
                    required_count = int(req["count"])
                    candidates = [p for p in personnel if p.get("role") == role]
                    if not candidates:
                        continue

                    if is_risk_activity and not shortage_forced:
                        assign_count = min(len(candidates), max(0, required_count - 1))
                        shortage_forced = True
                    else:
                        assign_count = min(len(candidates), required_count)

                    for selected in pick_sample(candidates, assign_count):
                        session.run(
                            """
                            MATCH (p:Personnel {id: $personnel_id})
                            MATCH (a:Activity {id: $activity_id})
                            MERGE (p)-[r:ASSIGNED_TO]->(a)
                            SET r.role = $role, r.assigned_at = datetime()
                            """,
                            {
                                "personnel_id": selected["id"],
                                "activity_id": activity_id,
                                "role": role,
                            },
                        )
                        self.stats["personnel_allocations"] += 1

                for req in item["equipment_requirements"]:
                    model = req["equipment_model"]
                    required_count = int(req["count"])
                    candidates = [e for e in equipment if e.get("model") == model]
                    if not candidates:
                        continue

                    if is_risk_activity and not shortage_forced:
                        assign_count = min(len(candidates), max(0, required_count - 1))
                        shortage_forced = True
                    else:
                        assign_count = min(len(candidates), required_count)

                    for selected in pick_sample(candidates, assign_count):
                        session.run(
                            """
                            MATCH (e:Equipment {id: $equipment_id})
                            MATCH (a:Activity {id: $activity_id})
                            MERGE (e)-[r:USED_BY]->(a)
                            SET r.model = $model, r.assigned_at = datetime()
                            """,
                            {
                                "equipment_id": selected["id"],
                                "activity_id": activity_id,
                                "model": model,
                            },
                        )
                        self.stats["equipment_allocations"] += 1

    def assign_upcoming_flags(
        self,
        personnel: List[Dict[str, Any]],
        equipment: List[Dict[str, Any]],
    ) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        personnel_flags: Dict[str, List[str]] = {p["id"]: [] for p in personnel}
        equipment_flags: Dict[str, List[str]] = {e["id"]: [] for e in equipment}

        if personnel:
            count = max(1, len(personnel) // 5)
            for person in random.sample(personnel, k=min(count, len(personnel))):
                personnel_flags[person["id"]] = random.choice(LEAVE_OR_MAINT_OPTIONS)

        if equipment:
            count = max(1, len(equipment) // 5)
            for asset in random.sample(equipment, k=min(count, len(equipment))):
                equipment_flags[asset["id"]] = random.choice(LEAVE_OR_MAINT_OPTIONS)

        return personnel_flags, equipment_flags

    def upsert_activities(self, activities_payload: List[Dict[str, Any]]) -> None:
        now = datetime.utcnow()
        for item in activities_payload:
            filter_query = mongo_filter_by_neo4j_id(item["id"])
            set_data = {
                "neo4j_id": item["id"],
                "name": item["name"],
                "description": f"{item['name']} 的生产活动，已自动生成风险预警测试数据。",
                "activity_type": item.get("activity_type") or "production",
                "sop_steps": [],
                "estimated_duration": random.randint(60, 240),
                "duration_minutes": None,
                "deadline": None,
                "required_resources": [],
                "required_personnel": [],
                "status": item.get("status") or "pending",
                "domain": item.get("domain") or "default",
                "process_id": item.get("process_id") or "auto-process",
                "version": 1,
                "is_active": True,
                "working_hours": DEFAULT_WORKING_HOURS,
                "material_requirements": item["material_requirements"],
                "personnel_requirements": item["personnel_requirements"],
                "equipment_requirements": item["equipment_requirements"],
                "updated_at": now,
            }
            self.db.activities.update_one(
                filter_query,
                {"$set": set_data, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
            self.stats["activities_upserted"] += 1

    def upsert_personnel(
        self,
        personnel: List[Dict[str, Any]],
        personnel_flags: Dict[str, List[str]],
    ) -> None:
        now = datetime.utcnow()
        with self.neo4j_driver.session() as session:
            for person in personnel:
                person_id = person["id"]
                role = person.get("role") or random.choice(DEFAULT_ROLES)
                upcoming_leaves = personnel_flags.get(person_id, [])

                session.run(
                    """
                    MATCH (p:Personnel {id: $personnel_id})
                    SET p.role = $role,
                        p.upcoming_leaves = $upcoming_leaves
                    """,
                    {
                        "personnel_id": person_id,
                        "role": role,
                        "upcoming_leaves": upcoming_leaves,
                    },
                )

                filter_query = mongo_filter_by_neo4j_id(person_id)
                set_data = {
                    "neo4j_id": person_id,
                    "name": person.get("name") or f"人员-{person_id[-4:]}",
                    "role": role,
                    "responsibility": f"{role}职责执行",
                    "skills": [role],
                    "work_hours": "08:00-18:00",
                    "assigned_tasks": [],
                    "status": person.get("status") or "active",
                    "upcoming_leaves": upcoming_leaves,
                    "age": person.get("age") or random.randint(20, 50),
                    "gender": person.get("gender") or random.choice(["男", "女"]),
                    "native_place": person.get("native_place") or random.choice(["北京", "上海", "广东", "江苏", "浙江", "四川", "湖北", "山东", "河南", "湖南"]),
                    "hire_date": person.get("hire_date") or f"{random.randint(2015, 2023)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
                    "education": person.get("education") or random.choice(["本科", "大专", "高中"]),
                    "salary": person.get("salary") or round(random.uniform(4000, 15000), 2),
                    "updated_at": now,
                }
                self.db.personnel.update_one(
                    filter_query,
                    {"$set": set_data, "$setOnInsert": {"created_at": now}},
                    upsert=True,
                )
                self.stats["personnel_upserted"] += 1

    def upsert_assets(
        self,
        materials: List[Dict[str, Any]],
        equipment: List[Dict[str, Any]],
        equipment_flags: Dict[str, List[str]],
    ) -> None:
        now = datetime.utcnow()
        with self.neo4j_driver.session() as session:
            for material in materials:
                material_id = material["id"]
                filter_query = mongo_filter_by_neo4j_id(material_id)
                set_data = {
                    "neo4j_id": material_id,
                    "name": material.get("name") or f"原料-{material_id[-4:]}",
                    "model": material.get("model") or material.get("name") or "通用原料",
                    "asset_type": "material",
                    "specification": None,
                    "supplier": None,
                    "status": "available",
                    "quantity": float(material.get("quantity") or 0),
                    "unit": material.get("unit") or "kg",
                    "upcoming_maintenance": [],
                    "updated_at": now,
                }
                self.db.assets.update_one(
                    filter_query,
                    {"$set": set_data, "$setOnInsert": {"created_at": now}},
                    upsert=True,
                )
                self.stats["assets_upserted"] += 1

            for asset in equipment:
                equipment_id = asset["id"]
                maintenance = equipment_flags.get(equipment_id, [])
                session.run(
                    """
                    MATCH (e:Equipment {id: $equipment_id})
                    SET e.model = $model,
                        e.upcoming_maintenance = $upcoming_maintenance
                    """,
                    {
                        "equipment_id": equipment_id,
                        "model": asset.get("model") or "通用设备",
                        "upcoming_maintenance": maintenance,
                    },
                )

                filter_query = mongo_filter_by_neo4j_id(equipment_id)
                set_data = {
                    "neo4j_id": equipment_id,
                    "name": asset.get("name") or f"设备-{equipment_id[-4:]}",
                    "model": asset.get("model") or asset.get("name") or "通用设备",
                    "asset_type": "equipment",
                    "specification": None,
                    "supplier": None,
                    "status": asset.get("status") or "idle",
                    "quantity": None,
                    "unit": None,
                    "upcoming_maintenance": maintenance,
                    "updated_at": now,
                }
                self.db.assets.update_one(
                    filter_query,
                    {"$set": set_data, "$setOnInsert": {"created_at": now}},
                    upsert=True,
                )
                self.stats["assets_upserted"] += 1

    def run(self) -> None:
        activities = self.fetch_activities()
        personnel = self.fetch_personnel()
        equipment = self.fetch_equipment()
        materials = self.fetch_materials()

        if not activities:
            raise RuntimeError("Neo4j 中未找到 Activity 节点，无法执行自动同步。")
        if not personnel:
            personnel = self.bootstrap_personnel_from_mongo()
        if not equipment or not materials:
            boot_materials, boot_equipment = self.bootstrap_assets_from_mongo()
            if not materials:
                materials = boot_materials
            if not equipment:
                equipment = boot_equipment

        if not personnel:
            raise RuntimeError("无法构建人员数据源：Neo4j 与 MongoDB 中均缺失 Personnel。")
        if not equipment:
            raise RuntimeError("无法构建设备数据源：Neo4j 与 MongoDB 中均缺失 Equipment。")
        if not materials:
            raise RuntimeError("无法构建原料数据源：Neo4j 与 MongoDB 中均缺失 Material。")

        activities_payload: List[Dict[str, Any]] = []
        for activity in activities:
            material_reqs, personnel_reqs, equipment_reqs = self.build_requirements(
                activity,
                materials,
                personnel,
                equipment,
            )
            activities_payload.append(
                {
                    "id": activity["id"],
                    "name": activity.get("name") or f"活动-{activity['id'][-4:]}",
                    "domain": activity.get("domain"),
                    "process_id": activity.get("process_id"),
                    "activity_type": activity.get("activity_type"),
                    "status": activity.get("status"),
                    "material_requirements": material_reqs,
                    "personnel_requirements": personnel_reqs,
                    "equipment_requirements": equipment_reqs,
                }
            )

        personnel_flags, equipment_flags = self.assign_upcoming_flags(personnel, equipment)
        self.clear_existing_allocation_relationships()
        self.create_allocations(activities_payload, personnel, equipment)

        self.upsert_activities(activities_payload)
        self.upsert_personnel(personnel, personnel_flags)
        self.upsert_assets(materials, equipment, equipment_flags)


def main() -> None:
    random.seed()
    syncer = AutoSyncDB()
    try:
        syncer.run()
    finally:
        syncer.close()


if __name__ == "__main__":
    main()
