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

class PersonnelResponse(PersonnelBase):
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
