from pydantic import BaseModel, EmailStr, field_validator
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

    class Config:
        from_attributes = True   # allows conversion from SQLAlchemy model

# ---------- LEAVE ----------

# Request: when applying for leave
class LeaveApply(BaseModel):
    employee_id: int
    start_date: date
    end_date: date

    # Validation → end_date should not be before start_date
    @field_validator("end_date")
    @classmethod
    def end_not_before_start(cls, v, info):
        values = info.data
        if "start_date" in values and v < values["start_date"]:
            raise ValueError("end_date cannot be before start_date")
        return v

# Response: when returning leave request info
class LeaveOut(BaseModel):
    id: int
    employee_id: int
    start_date: date
    end_date: date
    num_days: int
    status: LeaveStatus

    class Config:
        from_attributes = True

# Response: only leave balance
class BalanceOut(BaseModel):
    employee_id: int
    leave_balance: int