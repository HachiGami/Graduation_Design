from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime

class ResourceBase(BaseModel):
    name: str = Field(..., description="资源名称")
    type: str = Field(..., description="资源类型")
    specification: Optional[str] = Field(None, description="规格")
    supplier: Optional[str] = Field(None, description="供应商")
    quantity: Optional[float] = Field(0, description="数量")
    unit: str = Field(..., description="单位")
    expiry_date: Optional[datetime] = Field(None, description="使用期限")
    status: str = Field(default="available", description="状态")
    version: Optional[int] = Field(1, description="版本号")
    is_active: Optional[bool] = Field(True, description="是否启用")
    manufacturer: Optional[str] = Field(None, description="生产厂家")
    production_date: Optional[str] = Field(None, description="生产时间 (YYYY-MM-DD)")
    upcoming_maintenance: Optional[list[str]] = Field(default=[], description="未来检修日期数组")

class ResourceCreate(ResourceBase):
    pass

class ResourceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    specification: Optional[str] = None
    supplier: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    expiry_date: Optional[datetime] = None
    status: Optional[str] = None
    version: Optional[int] = None
    is_active: Optional[bool] = None
    manufacturer: Optional[str] = None
    production_date: Optional[str] = None
    upcoming_maintenance: Optional[list[str]] = None
    equipment_activity_priority_order: Optional[List[str]] = Field(
        default=None,
        description="设备被多活动占用时的执行优先级（activity_id 顺序，靠前优先）",
    )

class ActivityConsumerResponse(BaseModel):
    activity_id: str = Field(default="", description="活动ID")
    activity_name: str = Field(..., description="活动名称")
    process_id: str = Field(default="", description="流程ID")
    status: str = Field(default="", description="活动状态")
    working_hours: List[Any] = Field(default=[], description="活动工作时间配置")
    rate: float = Field(0.0, description="原料消耗速率（单位/小时）")
    daily_consumption: float = Field(0.0, description="按工作时长计算的每日消耗量")


class ResourceResponse(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    type: str
    specification: Optional[str] = None
    supplier: Optional[str] = None
    quantity: float
    unit: str
    expiry_date: Optional[datetime] = None
    status: str = "available"
    version: Optional[int] = 1
    is_active: Optional[bool] = True
    manufacturer: Optional[str] = None
    production_date: Optional[str] = None
    upcoming_maintenance: Optional[List[str]] = Field(default=[])
    daily_consumption: float = Field(0.0, description="每日总消耗量")
    remaining_days: float = Field(-1.0, description="预计可用天数，-1 表示暂无消耗")
    created_at: datetime
    updated_at: datetime
    serving_activities_details: Optional[List[ActivityConsumerResponse]] = Field(
        default=[],
        description="动态从Neo4j计算出的服务活动详情(含工作时长与消耗率)"
    )
    serving_processes: Optional[List[str]] = Field(
        default=[],
        description="动态从Neo4j计算出的所涉流程ID数组"
    )
    equipment_activity_priority_order: Optional[List[str]] = Field(
        default=[],
        description="设备多活动占用时的优先级（activity_id，仅设备）",
    )

    class Config:
        populate_by_name = True
