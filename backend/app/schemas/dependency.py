from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DependencyBase(BaseModel):
    source_activity_id: str = Field(..., description="前置活动ID (MongoDB ID)")
    target_activity_id: str = Field(..., description="后置活动ID (MongoDB ID)")
    dependency_type: str = Field(..., description="依赖类型：sequential/parallel/conditional")
    time_constraint: Optional[int] = Field(0, description="时间约束（分钟），例如FS+lag")
    status: Optional[str] = Field("active", description="依赖状态：active/inactive/pending")
    description: Optional[str] = Field(None, description="依赖关系描述")

class DependencyCreate(DependencyBase):
    pass

class DependencyUpdate(BaseModel):
    dependency_type: Optional[str] = None
    time_constraint: Optional[int] = None
    status: Optional[str] = None
    description: Optional[str] = None

class DependencyResponse(DependencyBase):
    id: Optional[str] = Field(None, description="关系唯一标识（如有）")
    created_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
