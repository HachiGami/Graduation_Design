from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import datetime

class AssetBase(BaseModel):
    model: str = Field(..., description="设备型号/规格（用于SOP匹配）")
    name: str = Field(..., description="资产个体名称（如'灌装机-01'）")
    asset_type: Literal["equipment", "material"] = Field(..., description="资产类型")
    specification: Optional[str] = Field(None, description="技术规格")
    supplier: Optional[str] = Field(None, description="供应商")
    status: Literal["idle", "in_use", "maintenance", "available"] = Field(default="idle", description="状态")
    
    # 仅用于 material 类型
    quantity: Optional[float] = Field(None, description="库存数量（仅原料）")
    unit: Optional[str] = Field(None, description="单位（仅原料）")
    upcoming_maintenance: Optional[List[str]] = Field(default=[], description="未来检修日期数组")
    manufacturer: Optional[str] = Field(None, description="生产厂家")
    production_date: Optional[str] = Field(None, description="生产时间 (YYYY-MM-DD)")
    serving_activities: Optional[List[str]] = Field(default=[], description="正在服务于哪项活动")
    process_id: Optional[str] = Field(None, description="流程ID")

class AssetCreate(AssetBase):
    pass

class AssetUpdate(BaseModel):
    model: Optional[str] = None
    name: Optional[str] = None
    asset_type: Optional[Literal["equipment", "material"]] = None
    specification: Optional[str] = None
    supplier: Optional[str] = None
    status: Optional[Literal["idle", "in_use", "maintenance", "available"]] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    upcoming_maintenance: Optional[List[str]] = None
    manufacturer: Optional[str] = None
    production_date: Optional[str] = None
    serving_activities: Optional[List[str]] = None
    process_id: Optional[str] = None

class AssetResponse(AssetBase):
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True
