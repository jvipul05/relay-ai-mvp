from pydantic import BaseModel, Field

class ActionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)

class ActionApproval(BaseModel):
    approved_by: str = "Demo User"

class ActionVerification(BaseModel):
    verified_by: str = "Demo User"
