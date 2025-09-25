from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from . import schemas, crud
from .database import get_db
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from . import auth
from .config import settings
from .models import Role

app = FastAPI(title="Leave Management System")


@app.post("/auth/register",response_model=schemas.EmployeeOut, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.EmployeeSelfRegister, db: Session = Depends(get_db)):
    if crud.get_employee_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already exist")
    
    emp = crud.create_employee(
        db,
        name=payload.name,
        email=payload.email,
        department=payload.department,
        joining_date=payload.joining_date,
        password=payload.password,
        role=schemas.Role.employee
    )
    return emp

@app.post("/auth/token", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    emp = crud.get_employee_by_email(db, form_data.username)
    if not emp:
        raise HTTPException(status_code=401, detail="Invalid Credentials")
    
    if not auth.verify_password(form_data.password, emp.password_hash):
        raise HTTPException(status_code=401, detail="Invalid Credentials")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data = {"sub":emp.email, "role":emp.role},
        expires_delta= access_token_expires
        )
    
    refresh_token = auth.create_and_store_refresh_token(db, emp.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }

@app.post("/auth/refresh", response_model=schemas.Token)
def refresh_token(payload: schemas.RefreshRequest, db: Session = Depends(get_db)):
    user = auth.verify_refresh_token(db, payload.refresh_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # New access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires,
    )

    # Optionally: rotate refresh token here (invalidate old one, issue new one)
    new_refresh_token = auth.create_and_store_refresh_token(db, user.id)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }

@app.post("/auth/logout")
def logout(payload: schemas.RefreshRequest, db: Session = Depends(get_db)):
    revoked = auth.revoke_refresh_token(db, payload.refresh_token)
    if not revoked:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return {"message": "Logged out successfully"}


@app.post("/employees",response_model=schemas.EmployeeOut, status_code=status.HTTP_201_CREATED)
def add_employee(payload: schemas.EmployeeRegister, db: Session = Depends(get_db), current_user = Depends(auth.require_role([Role.manager]))):
    if crud.get_employee_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already exist")
    emp = crud.create_employee(
        db,
        name=payload.name,
        email=payload.email,
        department=payload.department,
        joining_date=payload.joining_date,
        password=payload.password,
        role=payload.role
    )
    return emp

@app.get("/employees/{employee_id}", response_model=schemas.EmployeeOut)
def get_employee(employee_id: int, db:Session = Depends(get_db), current_user = Depends(auth.get_current_user)):
    if current_user.role == Role.employee and current_user.id != employee_id:
        raise HTTPException(status_code=403, detail="You can only view your own details")
    
    emp = crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp

@app.get("/employees", response_model=List[schemas.EmployeeOut])
def list_employees(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user = Depends(auth.require_role([Role.manager]))):
    return crud.list_employees(db, skip, limit)

@app.get("/employees/{employee_id}/balance", response_model=schemas.BalanceOut)
def get_balance(employee_id: int, db:Session = Depends(get_db), current_user = Depends(auth.get_current_user)):
    if current_user.role == Role.employee and current_user.id != employee_id:
        raise HTTPException(status_code=403, detail="You can only view your own balance")
    
    emp = crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return schemas.BalanceOut(employee_id=emp.id, leave_balance=emp.leave_balance)


@app.post("/leave/apply", response_model=schemas.LeaveOut, status_code=status.HTTP_201_CREATED)
def apply_leave(payload: schemas.LeaveApply, db:Session = Depends(get_db), current_user = Depends(auth.require_role([Role.employee]))):
    if payload.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only apply leave for yourself")
    
    emp = crud.get_employee(db, payload.employee_id)
    
    try:
        leave = crud.apply_leave(db, employee=emp, start_date=payload.start_date, end_date=payload.end_date,)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return leave

@app.put("/leave/{leave_id}/approve")
def approve_leave(leave_id: int, db: Session = Depends(get_db), current_user = Depends(auth.require_role([Role.manager]))):
    leave = crud.get_leave(db, leave_id)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    emp = crud.get_employee(db, employee_id=leave.employee_id)
    try:
        leave, updated_balance = crud.approve_leave(db, leave=leave, employee=emp)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {
        "id": leave.id,
        "employee_id": emp.id,
        "status": leave.status,
        "updated_leave_balance": updated_balance
    }

@app.put("/leave/{leave_id}/reject", response_model=schemas.LeaveOut)
def reject_leave(leave_id: int, db: Session = Depends(get_db), current_user = Depends(auth.require_role([Role.manager]))):
    leave = crud.get_leave(db, leave_id)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    try:
        leave = crud.reject_leave(db, leave=leave)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return leave

@app.get("/leave/employee/{employee_id}", response_model=List[schemas.LeaveOut])
def list_employee_leaves(employee_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user = Depends(auth.get_current_user)):
    if current_user.role == Role.employee and current_user.id != employee_id:
        raise HTTPException(status_code=403, detail="You can only view your own leave records")
    
    emp = crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return crud.list_leaves_for_employee(db, employee_id, skip=skip, limit=limit)
