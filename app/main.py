from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from . import schemas, crud
from .database import Base, engine, get_db

app = FastAPI(title="Leave Management System")

Base.metadata.create_all(bind=engine)

@app.post("/employees",response_model=schemas.EmployeeOut, status_code=status.HTTP_201_CREATED)
def add_employee(payload: schemas.EmployeeCreate, db: Session = Depends(get_db)):
    if crud.get_employee_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already exist")
    emp = crud.create_employee(
        db,
        name=payload.name,
        email=payload.email,
        department=payload.department,
        joining_date=payload.joining_date
    )
    return emp

@app.get("/employees/{employee_id}", response_model=schemas.EmployeeOut)
def get_employee(employee_id: int, db:Session = Depends(get_db)):
    emp = crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp

@app.get("/employees", response_model=List[schemas.EmployeeOut])
def list_employees(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.list_employees(db, skip, limit)

@app.get("/employees/{employee_id}/balance", response_model=schemas.BalanceOut)
def get_balance(employee_id: int, db:Session = Depends(get_db)):
    emp = crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return schemas.BalanceOut(employee_id=emp.id, leave_balance=emp.leave_balance)


@app.post("/leave/apply", response_model=schemas.LeaveOut, status_code=status.HTTP_201_CREATED)
def apply_leave(payload: schemas.LeaveApply, db:Session = Depends(get_db)):
    emp = crud.get_employee(db, payload.employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    try:
        leave = crud.apply_leave(db, employee=emp, start_date=payload.start_date, end_date=payload.end_date,)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return leave

@app.put("/leave/{leave_id}/approve")
def approve_leave(leave_id: int, db: Session = Depends(get_db)):
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
def reject_leave(leave_id: int, db: Session = Depends(get_db)):
    leave = crud.get_leave(db, leave_id)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    try:
        leave = crud.reject_leave(db, leave=leave)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return leave

@app.get("/leave/employee/{employee_id}", response_model=List[schemas.LeaveOut])
def list_employee_leaves(employee_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    emp = crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return crud.list_leaves_for_employee(db, employee_id, skip=skip, limit=limit)
