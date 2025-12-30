from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DependencyBase(BaseModel):
    name: str = Field(..., description="依赖关系名称")
    predecessor_stage: str = Field(..., description="前置环节")
    successor_stage: str = Field(..., description="后置环节")
    dependency_type: str = Field(..., description="依赖类型：sequential/parallel/conditional")
    time_constraint: Optional[int] = Field(None, description="时间约束（分钟）")
    condition: Optional[str] = Field(None, description="条件描述")

class DependencyCreate(DependencyBase):
    pass

class DependencyUpdate(BaseModel):
    name: Optional[str] = None
    predecessor_stage: Optional[str] = None
    successor_stage: Optional[str] = None
    dependency_type: Optional[str] = None
    time_constraint: Optional[int] = None
    condition: Optional[str] = None

class DependencyResponse(DependencyBase):
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
