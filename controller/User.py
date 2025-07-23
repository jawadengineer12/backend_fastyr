from models import User
from typing import Optional
from fastapi import  APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field 
from database import SessionLocal
from datetime import datetime, timedelta
from jose import jwt, JWTError
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string
import smtplib
import os



load_dotenv()


router = APIRouter(
    prefix="",
    tags=["Users"]
)

oauth_schema = OAuth2PasswordBearer(tokenUrl="token")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY")

ALGORITHM = os.getenv("ALGORITHM")

ACCESS_TOKEN_EXPIRE_HOURS = 3

reset_tokens = {}

email_code = {}

class UserCreate(BaseModel):
    userName: str
    email: str
    password: str

class UserUpdate(BaseModel):
    firstName: str
    lastName: str
    password: Optional[str] = None
    image: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    firstName: str
    lastName: str
    userEmail:str

class Password(BaseModel):
    password: str

class EmailRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str
    confirm_password: str

class PinVerification(BaseModel):
    email: EmailStr
    pin_code: str = Field(min_length=4, max_length=4)

class Credentials(BaseModel):
    credential:str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def generate_pin_code(length=4):
    return ''.join(random.choices(string.digits + string.ascii_letters, k=length))


def create_user(db: Session, user: UserCreate):
    hashed_password = pwd_context.hash(user.password)
    
    
    db_user = User(
        userName=user.userName, 
        email=user.email, 
        datetime = datetime.now(),
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return {"message": "SignUp successful"}

def authenticate_user(email: str, password: str, db: Session):
    user = get_user_by_email(db, email=email)
    if not user:
        return False
    if not pwd_context.verify(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.now() + expires_delta})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.get('/all_users')
def get_all(db: Session = Depends(get_db)):
    return db.query(User).all()


@router.post('/register')
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return create_user(db, user)

@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect Email or password")
    name = user.userName.split(" ")
    firstName = name[0]
    lastName = name[1] if len(name) > 1 else ""
    access_token_expires = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer", "firstName":firstName , "lastName":lastName , "userEmail": user.email} 


@router.get('/VerifyToken/{token}')
async def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=400, detail="Email not found")
        expire = payload.get("exp")
        # Convert the expire time from timestamp to datetime
        expire_time = datetime.fromtimestamp(expire)
        if expire_time < datetime.now():
            raise HTTPException(status_code=400, detail="Access Token Expired!")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")
    return {"Message": "Access Token Validated!"}

@router.get('/VerifyEmail')
async def verify_token(email: str,code: str):
    try:
        if email not in email_code and email_code[email] != code:
            raise HTTPException(status_code=400, detail="Email Not Verified!")
        elif email_code[email] == code:
            del email_code[email]
            return {"Message": "Email Verified!"}
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")


@router.put('/update/{email}')
def update(email: str, user: UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == email).first()
    image = user.image if user.image else None
    password = user.password if user.password else None
    if password is not None:
        db_user.hashed_password = pwd_context.hash(password.password)
    db_user.userName = user.firstName + " " + user.lastName
    db_user.image = image
    db.commit()
    db.refresh(db_user)

    name = db_user.userName.split(" ")
    firstName = name[0]
    lastName = name[1] if len(name) > 1 else ""
    
    userData = {"firstName": firstName, "lastName": lastName, "userEmail": db_user.email, "image":db_user.image}
    
    return userData


@router.get('/{email}')
def get_user(email: str, db: Session = Depends(get_db)):
    user = get_user_by_email(db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    name = user.userName.split(" ")
    firstName = name[0]
    lastName = name[1] if len(name) > 1 else ""
    
    userData = {"firstName": firstName, "lastName": lastName, "userEmail": user.email, "image":user.image}
    
    return userData 


@router.post('/VerifyPassword/{email}')
def verify_password(email: str, password: Password, db: Session = Depends(get_db)):
    user = get_user_by_email(db, email=email)
    if not user or not pwd_context.verify(password.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect Email or password")
    return {"Message": "Password is correct"}

@router.put('/updatePwd/{email}')
def update_password(email: str, password: Password, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == email).first()
    if (db_user):
        db_user.hashed_password = pwd_context.hash(password.password)
        db.commit()
        db.refresh(db_user)
        return db_user
    else:
        raise HTTPException(status_code=400, detail="User Not Found")


def send_email(email: str, pin_code: str, leadMessage: str, middleMessage: str, lastMessage: str):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = os.getenv("EMAIL_USERNAME")
    smtp_password = os.getenv("EMAIL_PASSWORD")

    msg = MIMEMultipart()
    msg["Subject"] = f"{leadMessage} pin code"
    msg["From"] = smtp_user
    msg["To"] = email

    body = f"""
    <html>
    <body>
        <p>Dear User,</p>
        <p>Your PIN code for {leadMessage} is: <strong>{pin_code}</strong></p>
        <p>Please use this code to {middleMessage}. If you did not request a {lastMessage}, please ignore this email.</p>
        <p>Best regards,<br>AI Avatar</p>
    </body>
    </html>
    """
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg,smtp_user, email)
        print(f"Email sent successfully to {email}")
    except smtplib.SMTPException as e:
        print(f"Failed to send email to {email}: {e}")


@router.post('/send_email_verification_code')
async def send_email_verification_code(request: EmailRequest):
    email = request.email

    if email not in email_code:
        verification_code = generate_pin_code(8)
        email_code[email] = verification_code
    else:
        verification_code = email_code[email]
    send_email(email, verification_code,"email verification", "verify your email", "code for email verification for AI Copilot") 

    return {"message": "Verification code sent to email"}

@router.post("/forgot-password")
async def forgot_password(request: EmailRequest, db: Session = Depends(get_db)):
    email = request.email
    db_user = get_user_by_email(db, email=email)
    if db_user is None:
        raise HTTPException(status_code=400, detail="Email Not Found")
    if email not in reset_tokens :
        pin_code = generate_pin_code(4)
        reset_tokens[email] = pin_code
    else:
        pin_code = reset_tokens[email]
    send_email(email, pin_code, "password reset","reset your password", "password reset")
    
    return email

@router.post("/pin-verification")
async def pin_verification(request: PinVerification ,db: Session = Depends(get_db)):
    email = request.email
    pin_code = request.pin_code

    if email not in reset_tokens or reset_tokens[email] != pin_code:
        raise HTTPException(status_code=400, detail="Invalid pin code")
    
    return {"message": "OTP Verified successfully"}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    email = request.email
    new_password = request.new_password
    confirm_password = request.confirm_password
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    db_user = get_user_by_email(db, email=email)
    if (db_user):
        if email in reset_tokens:
            db_user.hashed_password = pwd_context.hash(new_password)
            db.commit()
            db.refresh(db_user)
            del reset_tokens[email]
        else:
            raise HTTPException(status_code=400, detail="Passwords Not Be Updated")
        return {"message": "Password updated successfully"}
    else:
        raise HTTPException(status_code=400, detail="User Not Found")
    

    
