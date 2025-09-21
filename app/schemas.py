from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from datetime import date
from enum import Enum

class LeaveStatus(str, Enum):
    applied = "applied"
    approved = "approved"
    rejected = "rejected"


# ---------- EMPLOYEE ----------

# Request: when creating an employee
class EmployeeCreate(BaseModel):
    name: str
    email: EmailStr
    department: str
    joining_date: date

# Response: when sending employee data back
class EmployeeOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    department: str
    joining_date: date
    leave_balance: int

    model_config = ConfigDict(from_attributes=True)   # allows conversion from SQLAlchemy model

# ---------- LEAVE ----------

# Request: when applying for leave
class LeaveApply(BaseModel):
    employee_id: int
    start_date: date
    end_date: date

# Response: when returning leave request info
class LeaveOut(BaseModel):
    id: int
    employee_id: int
    start_date: date
    end_date: date
    num_days: int
    status: LeaveStatus

    model_config = ConfigDict(from_attributes=True)

# Response: only leave balance
class BalanceOut(BaseModel):
    employee_id: int
    leave_balance: int