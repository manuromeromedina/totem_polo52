from pydantic import BaseModel

class UserBase(BaseModel):
    email: str
    role: str  # 'totem', 'company_admin', 'polo_admin'

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    company_id: int

    class Config:
        orm_mode = True

class CompanyBase(BaseModel):
    name: str

class CompanyResponse(CompanyBase):
    id: int

    class Config:
        orm_mode = True
