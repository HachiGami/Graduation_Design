from pydantic import BaseModel, Field
from typing import Optional

class PersonnelAssignmentBase(BaseModel):
    activity_id: str = Field(..., description="活动ID (MongoDB ID)")
    personnel_id: str = Field(..., description="人员ID (MongoDB ID)")
    role: Optional[str] = Field(None, description="角色，如'负责人'/'操作员'")

class PersonnelAssignmentCreate(PersonnelAssignmentBase):
    pass

class PersonnelAssignmentUpdate(BaseModel):
    role: Optional[str] = None

class PersonnelAssignmentResponse(PersonnelAssignmentBase):
    id: Optional[str] = Field(None, description="关系唯一标识")
    
    class Config:
        populate_by_name = True

