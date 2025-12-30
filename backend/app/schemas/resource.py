from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ResourceBase(BaseModel):
    name: str = Field(..., description="资源名称")
    type: str = Field(..., description="资源类型")
    specification: str = Field(..., description="规格")
    supplier: str = Field(..., description="供应商")
    quantity: float = Field(..., description="数量")
    unit: str = Field(..., description="单位")
    expiry_date: Optional[datetime] = Field(None, description="使用期限")
    status: str = Field(default="available", description="状态")

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

class ResourceResponse(ResourceBase):
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
