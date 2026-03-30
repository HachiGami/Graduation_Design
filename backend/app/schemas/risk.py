from pydantic import BaseModel
from typing import Literal, Optional


class RiskItem(BaseModel):
    risk_type: Literal["material_shortage", "allocation_shortage", "upcoming_absence"]
    level: Literal["high", "medium", "low"]
    activity_name: str
    message: str
    domain: Optional[str] = None
    process_id: Optional[str] = None
    runnable_days: Optional[float] = None
