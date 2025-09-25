from sqlalchemy.orm import Session
from sqlalchemy import select, and_
import hashlib
from datetime import datetime, timedelta

from . import models
from .config import settings
from . import auth
from .models import RefreshToken


# ---------- Helper ----------
def daterange_inclusive_days(start_date,end_date):
    return (end_date - start_date).days + 1


def create_refresh_token(db: Session, user_id: int, token_hash: str, expires_at: datetime):
    rt = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt

def get_refresh_token_by_hash(db: Session, token_hash: str):
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    return db.execute(stmt).scalar_one_or_none()

def revoke_refresh_token(db: Session, token_hash: str):
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).one_or_none()
    if rt:
        db.delete(rt)
        db.commit()
        return True
    return False

def delete_expired_refresh_tokens(db: Session):
    now = datetime.utcnow()
    stmt = select(RefreshToken).where(RefreshToken.expires_at < now)
    results = db.execute(stmt).scalars().all()
    for rt in results:
        db.delete(rt)
    db.commit()

# ---------- EMPLOYEE ----------
def create_employee(db:Session, *, name:str, email:str, department:str, joining_date, password:str, role: models.Role = models.Role.employee):
    employee = models.Employee(
        name = name,
        email = email, 
        department = department,
        joining_date = joining_date,
        leave_balance = settings.DEFAULT_LEAVE_BALANCE,
        password_hash = auth.hash_password(password),
        role=role
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee

def get_employee(db:Session, employee_id:int):
    return db.get(models.Employee, employee_id)

def get_employee_by_email(db:Session, email:str):
    stmt = select(models.Employee).where(models.Employee.email == email)
    return db.execute(stmt).scalar_one_or_none()

def list_employees(db:Session, skip:int =0, limit:int = 100):
    stmt = select(models.Employee).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


# ---------- LEAVES ----------
def has_overlapping_leave(db:Session, employee_id:int, start_date, end_date):
    stmt = select(models.LeaveRequest).where(
        models.LeaveRequest.employee_id == employee_id,
        models.LeaveRequest.status.in_([models.LeaveStatus.applied, models.LeaveStatus.approved]),
        and_(models.LeaveRequest.start_date <= end_date,
             models.LeaveRequest.end_date >= start_date)
    )
    return db.execute(stmt).first() is not None

def apply_leave(db:Session, employee:models.Employee, start_date, end_date):

    if start_date < employee.joining_date:
        raise ValueError("Cannot apply for leave before joining date")
    if has_overlapping_leave(db, employee.id, start_date, end_date):
        raise ValueError("Overlapping leave request exists")

    num_days = daterange_inclusive_days(start_date, end_date)
    if num_days <= 0:
        raise ValueError("Invalid date range")
    if employee.leave_balance < num_days:
        raise ValueError("Requested days exceed leave balance")

    leave = models.LeaveRequest(
        employee_id = employee.id,
        start_date = start_date,
        end_date = end_date,
        num_days = num_days,
        status = models.LeaveStatus.applied
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave

def get_leave(db: Session, leave_id: int):
    return db.get(models.LeaveRequest, leave_id)

def list_leaves_for_employee(db: Session, employee_id: int, skip: int = 0, limit: int = 100):
    stmt = select(models.LeaveRequest).where(models.LeaveRequest.employee_id == employee_id).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()

def approve_leave(db:Session, leave:models.LeaveRequest, employee:models.Employee):
    if leave.status == models.LeaveStatus.rejected:
        raise ValueError("Cannot approve an already rejected leave")
    if leave.status == models.LeaveStatus.approved:
        raise ValueError("Cannot approve an already approved leave")
    
    employee.leave_balance -= leave.num_days
    leave.status = models.LeaveStatus.approved

    db.commit()
    db.refresh(leave)
    db.refresh(employee)
    return leave, employee.leave_balance

def reject_leave(db:Session, leave:models.LeaveRequest):
    if leave.status == models.LeaveStatus.rejected:
        raise ValueError("Cannot reject an already rejected leave")
    if leave.status == models.LeaveStatus.approved:
        raise ValueError("Cannot reject an already approved leave")
    
    leave.status = models.LeaveStatus.rejected
    db.commit()
    db.refresh(leave)
    return leave