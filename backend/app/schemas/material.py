from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

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

    daily_consumption: float = Field(0.0, description="每日总消耗量")
    remaining_days: float = Field(9999.0, description="预计可用天数")
    serving_activities_details: Optional[List[dict]] = Field(
        default=[],
        description="动态从Neo4j计算出的服务活动详情(含工作时长与消耗率)"
    )
    serving_processes: Optional[List[str]] = Field(
        default=[],
        description="动态从Neo4j计算出的所涉流程ID数组"
    )

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
