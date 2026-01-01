from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

class SOPStep(BaseModel):
    step_number: int
    description: str
    duration: int

class ActivityBase(BaseModel):
    name: str = Field(..., description="活动名称")
    description: str = Field(..., description="活动描述")
    activity_type: str = Field(..., description="活动类型")
    sop_steps: List[SOPStep] = Field(default=[], description="SOP流程步骤")
    estimated_duration: int = Field(..., description="预计时长（分钟）")
    duration_minutes: Optional[int] = Field(None, description="实际耗时（分钟）")
    deadline: Optional[datetime] = Field(None, description="截止时间")
    required_resources: List[str] = Field(default=[], description="所需资源ID列表")
    required_personnel: List[str] = Field(default=[], description="所需人员ID列表")
    status: str = Field(default="pending", description="状态")
    domain: str = Field(..., description="流程域")
    process_id: str = Field(..., description="流程实例ID")
    version: Optional[int] = Field(1, description="流程版本号")
    is_active: Optional[bool] = Field(True, description="是否启用")

class ActivityCreate(ActivityBase):
    pass

class ActivityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    activity_type: Optional[str] = None
    sop_steps: Optional[List[SOPStep]] = None
    estimated_duration: Optional[int] = None
    duration_minutes: Optional[int] = None
    deadline: Optional[datetime] = None
    required_resources: Optional[List[str]] = None
    required_personnel: Optional[str] = None
    status: Optional[str] = None
    domain: Optional[str] = None
    process_id: Optional[str] = None
    version: Optional[int] = None
    is_active: Optional[bool] = None

class ActivityResponse(ActivityBase):
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
