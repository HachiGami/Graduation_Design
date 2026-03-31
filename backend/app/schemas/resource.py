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
    domain: Optional[str] = Field(None, description="流程域")
    process_id: Optional[str] = Field(None, description="流程实例ID")
    version: Optional[int] = Field(1, description="版本号")
    is_active: Optional[bool] = Field(True, description="是否启用")
    manufacturer: Optional[str] = Field(None, description="生产厂家")
    production_date: Optional[str] = Field(None, description="生产时间 (YYYY-MM-DD)")
    upcoming_maintenance: Optional[list[str]] = Field(default=[], description="未来检修日期数组，格式如 ['1天后', '2天后']")
    serving_activities: Optional[list[str]] = Field(default=[], description="该字段不在 Mongo 存储，而由 API 动态从 Neo4j 查询得出")

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
    domain: Optional[str] = None
    process_id: Optional[str] = None
    version: Optional[int] = None
    is_active: Optional[bool] = None
    manufacturer: Optional[str] = None
    production_date: Optional[str] = None
    upcoming_maintenance: Optional[list[str]] = None
class ResourceResponse(ResourceBase):
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
