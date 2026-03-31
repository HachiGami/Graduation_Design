from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ActivityUsage(BaseModel):
    activity_name: str
    hourly_consumption: float

class MaterialResponse(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    type: str
    specification: Optional[str] = None
    supplier: Optional[str] = None
    manufacturer: Optional[str] = None
    quantity: float
    unit: str
    status: Optional[str] = None
    domain: Optional[str] = None
    process_id: Optional[str] = None
    
    daily_consumption: float = Field(0.0, description="每日总消耗量")
    remaining_days: float = Field(9999.0, description="预计可用天数")
    serving_activities: List[ActivityUsage] = Field(default_factory=list, description="正在使用该原料的活动")

    class Config:
        populate_by_name = True

class MaterialAddStock(BaseModel):
    add_amount: float = Field(..., gt=0, description="增加的数量")

class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    specification: Optional[str] = None
    supplier: Optional[str] = None
    manufacturer: Optional[str] = None
    unit: Optional[str] = None
    status: Optional[str] = None
    domain: Optional[str] = None
    process_id: Optional[str] = None
