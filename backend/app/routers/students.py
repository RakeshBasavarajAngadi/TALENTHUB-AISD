from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.student import Student
from app.schemas.student import StudentResponse, StudentUpdate, StudentCreate
from app.dependencies.auth import get_current_student, get_current_admin, get_password_hash

router = APIRouter(prefix="/api/students", tags=["Students"])

@router.get("/me", response_model=StudentResponse)
def get_student_profile(current_student: Student = Depends(get_current_student)):
    return current_student

@router.put("/me", response_model=StudentResponse)
def update_student_profile(
    data: StudentUpdate,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    if data.name is not None:
        current_student.name = data.name
    if data.email is not None:
        current_student.email = data.email
    if data.branch is not None:
        current_student.branch = data.branch
    if data.cgpa is not None:
        current_student.cgpa = data.cgpa
    if data.active_backlogs is not None:
        current_student.active_backlogs = data.active_backlogs
    if data.cleared_backlogs is not None:
        current_student.cleared_backlogs = data.cleared_backlogs

    db.commit()
    db.refresh(current_student)
    return current_student

@router.get("", response_model=List[StudentResponse])
def list_students(
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return db.query(Student).all()

@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    data: StudentCreate,
    db: Session = Depends(get_db)
):
    email_clean = data.email.strip().lower()
    usn_clean = data.usn.strip().upper()

    if db.query(Student).filter(Student.email.ilike(email_clean)).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student email already exists.")
    if db.query(Student).filter(Student.usn.ilike(usn_clean)).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student USN already exists.")

    student = Student(
        usn=usn_clean,
        name=data.name.strip(),
        email=email_clean,
        branch=data.branch.strip().upper(),
        cgpa=data.cgpa,
        active_backlogs=data.active_backlogs or 0,
        cleared_backlogs=data.cleared_backlogs or 0,
        has_accepted_offer=False,
        hashed_password=get_password_hash(data.password or "password123")
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student
