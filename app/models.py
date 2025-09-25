from sqlalchemy import Integer, String, Date, ForeignKey, CheckConstraint, Enum as SAEnum, Boolean, DateTime, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .database import Base
import enum
from datetime import date, datetime

class LeaveStatus(str, enum.Enum):
    applied = "applied"
    approved = "approved"
    rejected = "rejected"

class Role(str, enum.Enum):
    employee = "employee"
    manager = "manager"


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    joining_date: Mapped[date] = mapped_column(Date, nullable=False)
    leave_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=20)

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(SAEnum(Role), nullable=False, default=Role.employee)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship: One employee can have many leave requests
    leaves: Mapped[list["LeaveRequest"]] = relationship("LeaveRequest", back_populates="employee", cascade="all, delete-orphan")

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date: Mapped["date"] = mapped_column(Date, nullable=False)
    end_date: Mapped["date"] = mapped_column(Date, nullable=False)
    num_days: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[LeaveStatus] = mapped_column(SAEnum(LeaveStatus), nullable=False, default = LeaveStatus.applied)

    # Relationship: Each leave belongs to one employee
    employee: Mapped["Employee"] = relationship("Employee", back_populates="leaves")

    # adding constraint 
    __table_args__ = (
        CheckConstraint("num_days > 0", name="ck_num_days_positive"),
        )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)

    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    user: Mapped["Employee"] = relationship("Employee", back_populates="refresh_tokens")