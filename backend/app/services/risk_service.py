from typing import Any, Dict, List, Set
from collections import Counter
from bson import ObjectId


RUNNING_STATUSES = {"in_progress", "进行中"}


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _is_running(status: Any) -> bool:
    return isinstance(status, str) and status in RUNNING_STATUSES


def _parse_time_to_minutes(value: str) -> int:
    parts = str(value or "").split(":")
    if len(parts) != 2:
        return 0
    try:
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return 0


def _calc_daily_hours(working_hours: Any) -> float:
    windows = working_hours if isinstance(working_hours, list) else []
    if not windows:
        return 8.0
    total_minutes = 0
    for window in windows:
        if not isinstance(window, dict):
            continue
        start = _parse_time_to_minutes(window.get("start_time", "08:00"))
        end = _parse_time_to_minutes(window.get("end_time", "08:00"))
        if end > start:
            total_minutes += end - start
    return (total_minutes / 60.0) if total_minutes > 0 else 8.0


def _material_keys(material_id: str, material_name: str) -> List[str]:
    keys: List[str] = []
    if material_id:
        keys.append(f"id:{material_id}")
    if material_name:
        keys.append(f"name:{material_name.strip().lower()}")
    return keys


async def _load_assignments(
    neo4j_driver,
    activity_ids: List[str],
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    assignments: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        aid: {"personnel": [], "equipment": [], "materials": []} for aid in activity_ids
    }
    if not activity_ids:
        return assignments

    async with neo4j_driver.session() as session:
        # 人员：兼容历史关系方向
        personnel_queries = [
            """
            UNWIND $activity_ids AS aid
            MATCH (a:Activity {id: aid})-[:ASSIGNED_TO|ASSIGNS]->(p:Personnel)
            RETURN aid AS activity_id, p.id AS id, p.name AS name, p.role AS role, p.upcoming_leaves AS upcoming_leaves
            """,
            """
            UNWIND $activity_ids AS aid
            MATCH (p:Personnel)-[:ASSIGNED_TO|ASSIGNS]->(a:Activity {id: aid})
            RETURN aid AS activity_id, p.id AS id, p.name AS name, p.role AS role, p.upcoming_leaves AS upcoming_leaves
            """,
        ]
        seen_personnel: Set[str] = set()
        for query in personnel_queries:
            result = await session.run(query, {"activity_ids": activity_ids})
            async for row in result:
                aid = row.get("activity_id")
                pid = row.get("id")
                if not aid or not pid:
                    continue
                unique_key = f"{aid}::{pid}"
                if unique_key in seen_personnel:
                    continue
                seen_personnel.add(unique_key)
                assignments[aid]["personnel"].append(
                    {
                        "id": pid,
                        "name": row.get("name") or "未知人员",
                        "role": row.get("role"),
                        "upcoming_leaves": _as_list(row.get("upcoming_leaves")),
                    }
                )

        # 设备：兼容历史关系方向
        equipment_queries = [
            """
            UNWIND $activity_ids AS aid
            MATCH (a:Activity {id: aid})-[:USES|OCCUPIES]->(e:Equipment)
            RETURN aid AS activity_id, e.id AS id, e.name AS name, e.type AS type, e.specification AS specification, e.upcoming_maintenance AS upcoming_maintenance
            """,
            """
            UNWIND $activity_ids AS aid
            MATCH (e:Equipment)-[:USES|OCCUPIES|USED_BY]->(a:Activity {id: aid})
            RETURN aid AS activity_id, e.id AS id, e.name AS name, e.type AS type, e.specification AS specification, e.upcoming_maintenance AS upcoming_maintenance
            """,
        ]
        seen_equipment: Set[str] = set()
        for query in equipment_queries:
            result = await session.run(query, {"activity_ids": activity_ids})
            async for row in result:
                aid = row.get("activity_id")
                eid = row.get("id")
                if not aid or not eid:
                    continue
                unique_key = f"{aid}::{eid}"
                if unique_key in seen_equipment:
                    continue
                seen_equipment.add(unique_key)
                assignments[aid]["equipment"].append(
                    {
                        "id": eid,
                        "name": row.get("name") or "未知设备",
                        "type": row.get("type"),
                        "specification": row.get("specification"),
                        "upcoming_maintenance": _as_list(row.get("upcoming_maintenance")),
                    }
                )

        # 原料消耗：兼容关系方向
        material_queries = [
            """
            UNWIND $activity_ids AS aid
            MATCH (a:Activity {id: aid})-[c:CONSUMES]->(m)
            WHERE any(label IN labels(m) WHERE label IN ['Material', 'Resource'])
            RETURN aid AS activity_id, m.id AS id, m.name AS name, c.rate AS rate
            """,
            """
            UNWIND $activity_ids AS aid
            MATCH (m)-[c:CONSUMES]->(a:Activity {id: aid})
            WHERE any(label IN labels(m) WHERE label IN ['Material', 'Resource'])
            RETURN aid AS activity_id, m.id AS id, m.name AS name, c.rate AS rate
            """,
        ]
        for query in material_queries:
            result = await session.run(query, {"activity_ids": activity_ids})
            async for row in result:
                aid = row.get("activity_id")
                if not aid:
                    continue
                rate = float(row.get("rate") or 0.0)
                if rate <= 0:
                    continue
                assignments[aid]["materials"].append(
                    {
                        "id": row.get("id") or "",
                        "name": row.get("name") or "未知原料",
                        "rate": rate,  # 按天消耗速率
                    }
                )

    return assignments


async def _load_material_stock_map(db, material_ids: Set[str], material_names: Set[str]) -> Dict[str, float]:
    stock_map: Dict[str, float] = {}

    async def _merge_from_collection(collection_name: str):
        collection = getattr(db, collection_name, None)
        if collection is None:
            return
        query = {"$or": []}  # type: ignore[var-annotated]
        object_ids = [ObjectId(mid) for mid in material_ids if ObjectId.is_valid(mid)]
        if object_ids:
            query["$or"].append({"_id": {"$in": object_ids}})
        if material_names:
            query["$or"].append({"name": {"$in": list(material_names)}})
        if not query["$or"]:
            return

        if collection_name == "resources":
            query = {"$and": [query, {"$or": [{"type": "原料"}, {"type": "material"}]}]}
        elif collection_name == "assets":
            query = {"$and": [query, {"asset_type": "material"}]}

        async for doc in collection.find(query):
            stock = float(doc.get("quantity") or 0.0)
            doc_id = str(doc.get("_id")) if doc.get("_id") is not None else ""
            doc_name = (doc.get("name") or "").strip().lower()
            for key in _material_keys(doc_id, doc_name):
                stock_map[key] = stock_map.get(key, 0.0) + stock

    await _merge_from_collection("resources")
    await _merge_from_collection("assets")
    return stock_map


async def calculate_activity_risks(
    db,
    neo4j_driver,
    activities: List[Dict[str, Any]],
) -> Dict[str, List[str]]:
    activity_ids = [str(item.get("_id")) for item in activities if item.get("_id")]
    risks_by_activity: Dict[str, List[str]] = {aid: [] for aid in activity_ids}
    if not activity_ids:
        return risks_by_activity

    assignments = await _load_assignments(neo4j_driver, activity_ids)

    # 聚合所有运行中活动的原料总日消耗
    total_daily_consumption: Dict[str, float] = {}
    material_ids: Set[str] = set()
    material_names: Set[str] = set()
    running_activity_ids = {str(item.get("_id")) for item in activities if _is_running(item.get("status"))}
    activity_hours_map = {
        str(item.get("_id")): _calc_daily_hours(item.get("working_hours"))
        for item in activities
        if item.get("_id")
    }
    for aid in running_activity_ids:
        for consumed in assignments.get(aid, {}).get("materials", []):
            mid = consumed.get("id") or ""
            mname = (consumed.get("name") or "").strip()
            hourly_rate = float(consumed.get("rate") or 0.0)
            if hourly_rate <= 0:
                continue
            daily_rate = hourly_rate * activity_hours_map.get(aid, 8.0)
            for key in _material_keys(mid, mname):
                total_daily_consumption[key] = total_daily_consumption.get(key, 0.0) + daily_rate
            if mid:
                material_ids.add(mid)
            if mname:
                material_names.add(mname)

    stock_map = await _load_material_stock_map(db, material_ids, material_names)

    for activity in activities:
        aid = str(activity.get("_id"))
        if aid not in risks_by_activity:
            continue
        activity_name = activity.get("name") or "未知活动"
        assigned = assignments.get(aid, {"personnel": [], "equipment": [], "materials": []})
        assigned_personnel = assigned["personnel"]
        assigned_equipment = assigned["equipment"]

        required_equipment = _as_list(activity.get("equipment_types_required"))
        required_personnel = _as_list(activity.get("personnel_roles_required"))

        # 1) 分类短缺风险（按职业/设备类型统计）
        req_roles = Counter(required_personnel)
        assigned_roles = Counter(
            person.get("role")
            for person in assigned_personnel
            if isinstance(person.get("role"), str) and person.get("role")
        )
        for role, count in req_roles.items():
            shortage = count - assigned_roles.get(role, 0)
            if shortage > 0:
                risks_by_activity[aid].append(f"缺 {shortage} 名 {role}")

        req_equips = Counter(required_equipment)
        assigned_equips = Counter(
            equipment_type
            for equipment in assigned_equipment
            for equipment_type in [equipment.get("type") or equipment.get("specification")]
            if isinstance(equipment_type, str) and equipment_type
        )
        for equipment_type, count in req_equips.items():
            shortage = count - assigned_equips.get(equipment_type, 0)
            if shortage > 0:
                risks_by_activity[aid].append(f"缺 {shortage} 台 {equipment_type}")

        # 2) 原料短缺风险（库存 / 所有运行中活动总消耗）
        for consumed in assigned["materials"]:
            material_name = consumed.get("name") or "未知原料"
            material_id = consumed.get("id") or ""
            keys = _material_keys(material_id, material_name)
            total_rate = 0.0
            for key in keys:
                total_rate = max(total_rate, total_daily_consumption.get(key, 0.0))
            if total_rate <= 0:
                continue

            stock = 0.0
            for key in keys:
                stock = max(stock, stock_map.get(key, 0.0))

            runnable_days = stock / total_rate if total_rate > 0 else 0.0
            if runnable_days < 7:
                risks_by_activity[aid].append(
                    f"消耗的原料[{material_name}]库存不足7天（预计{runnable_days:.1f}天）"
                )

        # 3) 人员请假风险（字段非空即风险）
        for person in assigned_personnel:
            leave_values = _as_list(person.get("upcoming_leaves"))
            pid = person.get("id")
            if not leave_values and pid and ObjectId.is_valid(pid):
                mongo_person = await db.personnel.find_one({"_id": ObjectId(pid)})
                leave_values = _as_list((mongo_person or {}).get("upcoming_leaves"))
            if leave_values:
                risks_by_activity[aid].append(
                    f"人员请假风险：{person.get('name') or '未知人员'}未来7天内有请假计划"
                )

        # 4) 设备检修风险（字段非空即风险）
        for equipment in assigned_equipment:
            maintenance_values = _as_list(equipment.get("upcoming_maintenance"))
            eid = equipment.get("id")
            if not maintenance_values and eid and ObjectId.is_valid(eid):
                mongo_equipment = await db.resources.find_one({"_id": ObjectId(eid)})
                maintenance_values = _as_list((mongo_equipment or {}).get("upcoming_maintenance"))
            if maintenance_values:
                risks_by_activity[aid].append(
                    f"设备检修风险：{equipment.get('name') or '未知设备'}未来7天内有检修计划"
                )

    return risks_by_activity
