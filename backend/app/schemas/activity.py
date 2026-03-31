from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Literal
from datetime import datetime

class SopStep(BaseModel):
    content: str
    duration: int = 0  # 步骤耗时(分钟)

class MaterialRequirement(BaseModel):
    material_model: str = Field(..., description="原料型号（匹配Asset.model）")
    hourly_consumption_rate: float = Field(default=10.0, description="每小时消耗速率")
    unit: str = Field(..., description="单位（仅展示）")


class TimeWindow(BaseModel):
    start_time: str
    end_time: str

class PersonnelRequirement(BaseModel):
    role: str = Field(..., description="角色")
    count: int = Field(..., description="需要人数")

class EquipmentRequirement(BaseModel):
    equipment_model: str = Field(..., description="设备型号（匹配Asset.model）")
    count: int = Field(..., description="需要数量")

class ActivityBase(BaseModel):
    name: str = Field(..., description="活动名称")
    description: str = Field(..., description="活动描述")
    activity_type: str = Field(..., description="活动类型")
    sop_steps: Optional[List[SopStep]] = Field(default=[], description="SOP流程步骤")
    estimated_duration: int = Field(..., description="预计时长（分钟）")
    duration_minutes: Optional[int] = Field(None, description="实际耗时（分钟）")
    deadline: Optional[datetime] = Field(None, description="截止时间")
    status: Literal["pending", "in_progress"] = Field(default="pending", description="活动状态：pending(待机) 或 in_progress(进行中)")
    domain: str = Field(..., description="流程域")
    process_id: str = Field(..., description="流程实例ID")
    version: Optional[int] = Field(1, description="流程版本号")
    is_active: Optional[bool] = Field(True, description="是否启用")
    working_hours: List[TimeWindow] = Field(
        default_factory=lambda: [
            {"start_time": "08:00", "end_time": "11:00"},
            {"start_time": "13:00", "end_time": "18:00"},
        ],
        description="工作时间段",
    )
    
    # 资源需求定义
    material_requirements: List[MaterialRequirement] = Field(default=[], description="原料需求")
    personnel_requirements: List[PersonnelRequirement] = Field(default=[], description="人员需求")
    equipment_requirements: List[EquipmentRequirement] = Field(default=[], description="设备需求")

class ActivityCreate(ActivityBase):
    pass

class ActivityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    activity_type: Optional[str] = None
    sop_steps: Optional[List[SopStep]] = None
    estimated_duration: Optional[int] = None
    duration_minutes: Optional[int] = None
    deadline: Optional[datetime] = None
    status: Optional[Literal["pending", "in_progress"]] = None
    domain: Optional[str] = None
    process_id: Optional[str] = None
    version: Optional[int] = None
    is_active: Optional[bool] = None
    working_hours: Optional[List[TimeWindow]] = None
    material_requirements: Optional[List[MaterialRequirement]] = None
    personnel_requirements: Optional[List[PersonnelRequirement]] = None
    equipment_requirements: Optional[List[EquipmentRequirement]] = None

class ActivityResponse(ActivityBase):
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
