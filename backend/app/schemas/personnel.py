from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class PersonnelBase(BaseModel):
    name: str = Field(..., description="姓名")
    role: str = Field(..., description="角色")
    department: Optional[str] = Field(None, description="所属部门")
    responsibility: str = Field(default="", description="职责（可与部门同步，兼容旧数据）")
    skills: List[str] = Field(default=[], description="技能列表")
    status: str = Field(default="active", description="状态")
    upcoming_leaves: List[str] = Field(
        default=[],
        description="未来7天内的请假日期列表，不需要具体几月几号，标记几天后请假就可以",
    )
    age: Optional[int] = Field(None, description="年龄")
    gender: Optional[str] = Field(None, description="性别")
    native_place: Optional[str] = Field(None, description="籍贯")
    hire_date: Optional[str] = Field(None, description="入职日期 (YYYY-MM-DD)")
    education: Optional[str] = Field(None, description="学历")
    salary: Optional[float] = Field(None, description="薪资(元/月)")

class PersonnelCreate(PersonnelBase):
    pass

class PersonnelUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    responsibility: Optional[str] = None
    skills: Optional[List[str]] = None
    status: Optional[str] = None
    upcoming_leaves: Optional[List[str]] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    native_place: Optional[str] = None
    hire_date: Optional[str] = None
    education: Optional[str] = None
    salary: Optional[float] = None

class PersonnelResponse(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    role: str
    department: Optional[str] = Field(None, description="所属部门")
    responsibility: Optional[str] = Field(None, description="职责")
    skills: Optional[List[str]] = Field(default=[], description="技能列表")
    assigned_tasks: Optional[List[str]] = Field(default=[], description="分配的任务")
    status: str = Field(default="active", description="状态")
    upcoming_leaves: Optional[List[str]] = Field(
        default=[],
        description="未来7天内的请假日期列表，不需要具体几月几号，标记几天后请假就可以",
    )
    age: Optional[int] = Field(None, description="年龄")
    gender: Optional[str] = Field(None, description="性别")
    native_place: Optional[str] = Field(None, description="籍贯")
    hire_date: Optional[str] = Field(None, description="入职日期 (YYYY-MM-DD)")
    education: Optional[str] = Field(None, description="学历")
    salary: Optional[float] = Field(None, description="薪资(元/月)")
    created_at: datetime
    updated_at: datetime
    serving_activities_details: Optional[List[dict]] = Field(
        default=[],
        description="动态从Neo4j计算出的服务活动详情"
    )
    serving_processes: Optional[List[str]] = Field(
        default=[],
        description="动态从Neo4j计算出的所涉流程ID数组"
    )

    class Config:
        populate_by_name = True
