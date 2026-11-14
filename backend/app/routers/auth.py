from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.student import Student
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.student import StudentCreate
from app.dependencies.auth import verify_password, get_password_hash, create_access_token, get_current_user_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(request: StudentCreate, db: Session = Depends(get_db)):
    email_clean = request.email.strip().lower()
    usn_clean = request.usn.strip().upper()

    # Check if email is already taken
    existing_email = db.query(Student).filter(Student.email.ilike(email_clean)).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A student with this email address already exists."
        )

    # Check if USN is already taken
    existing_usn = db.query(Student).filter(Student.usn.ilike(usn_clean)).first()
    if existing_usn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A student with this USN already exists."
        )

    # Hash password securely
    raw_pwd = request.password if request.password else "password123"
    hashed_pwd = get_password_hash(raw_pwd)

    # Create new student profile
    student = Student(
        usn=usn_clean,
        name=request.name.strip(),
        email=email_clean,
        branch=request.branch.strip().upper(),
        cgpa=request.cgpa,
        active_backlogs=request.active_backlogs if request.active_backlogs is not None else 0,
        cleared_backlogs=request.cleared_backlogs if request.cleared_backlogs is not None else 0,
        has_accepted_offer=False,
        hashed_password=hashed_pwd
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    # Generate JWT token for immediate authenticated session
    access_token = create_access_token({
        "sub": student.email,
        "user_id": student.student_id,
        "role": "STUDENT",
        "name": student.name
    })

    return TokenResponse(
        access_token=access_token,
        role="STUDENT",
        user_id=student.student_id,
        name=student.name,
        email=student.email
    )

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    email = request.email.strip().lower()
    role = request.role.upper()
    password = request.password

    if role == "ADMIN":
        # Admin credentials: admin@talenthub.edu / adminpass
        if email == "admin@talenthub.edu" and password in ["adminpass", "admin123", "password123"]:
            access_token = create_access_token({
                "sub": email,
                "user_id": 999,
                "role": "ADMIN",
                "name": "Placement Director (Admin)"
            })
            return TokenResponse(
                access_token=access_token,
                role="ADMIN",
                user_id=999,
                name="Placement Director",
                email=email
            )
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials.")

    elif role == "STUDENT":
        student = db.query(Student).filter(Student.email.ilike(email)).first()
        if not student:
            # Try by USN if entered as USN
            student = db.query(Student).filter(Student.usn.ilike(email)).first()

        if not student:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Student account not found.")

        if not verify_password(password, student.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password.")

        access_token = create_access_token({
            "sub": student.email,
            "user_id": student.student_id,
            "role": "STUDENT",
            "name": student.name
        })

        return TokenResponse(
            access_token=access_token,
            role="STUDENT",
            user_id=student.student_id,
            name=student.name,
            email=student.email
        )
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role specified.")

@router.get("/me")
def get_me(user: dict = Depends(get_current_user_token)):
    return user
