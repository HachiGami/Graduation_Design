from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class PersonnelBase(BaseModel):
    name: str = Field(..., description="姓名")
    role: str = Field(..., description="角色")
    responsibility: str = Field(..., description="职责")
    skills: List[str] = Field(default=[], description="技能列表")
    work_hours: str = Field(..., description="工作时间")
    assigned_tasks: List[str] = Field(default=[], description="分配的任务")
    status: str = Field(default="active", description="状态")
    upcoming_leaves: List[str] = Field(
        default=[],
        description="未来7天内的请假日期列表，不需要具体几月几号，标记几天后请假就可以",
    )

class PersonnelCreate(PersonnelBase):
    pass

class PersonnelUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    responsibility: Optional[str] = None
    skills: Optional[List[str]] = None
    work_hours: Optional[str] = None
    assigned_tasks: Optional[List[str]] = None
    status: Optional[str] = None
    upcoming_leaves: Optional[List[str]] = None

class PersonnelResponse(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    role: str
    responsibility: Optional[str] = Field(None, description="职责")
    skills: Optional[List[str]] = Field(default=[], description="技能列表")
    work_hours: Optional[str] = Field(None, description="工作时间")
    assigned_tasks: Optional[List[str]] = Field(default=[], description="分配的任务")
    status: str = Field(default="active", description="状态")
    upcoming_leaves: Optional[List[str]] = Field(
        default=[],
        description="未来7天内的请假日期列表，不需要具体几月几号，标记几天后请假就可以",
    )
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
