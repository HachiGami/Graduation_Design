from pydantic import BaseModel, Field
from typing import Optional

class ResourceUsageBase(BaseModel):
    activity_id: str = Field(..., description="活动ID (MongoDB ID)")
    resource_id: str = Field(..., description="资源ID (MongoDB ID)")
    quantity: float = Field(..., description="使用数量")
    unit: str = Field(..., description="单位")
    stage: Optional[str] = Field(None, description="使用阶段，如'初期'/'中期'/'后期'")

class ResourceUsageCreate(ResourceUsageBase):
    pass

class ResourceUsageUpdate(BaseModel):
    quantity: Optional[float] = None
    unit: Optional[str] = None
    stage: Optional[str] = None

class ResourceUsageResponse(ResourceUsageBase):
    id: Optional[str] = Field(None, description="关系唯一标识")
    
    class Config:
        populate_by_name = True

