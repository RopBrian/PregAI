from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional
from pydantic import BaseModel, EmailStr
from backend.database.database import get_db
from backend.database import crud, models
from backend.config.settings import settings

router = APIRouter(prefix='/auth', tags=['auth'])
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='api/v1/auth/login')

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class UserBase(BaseModel):
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = 'pregnant_mother'

class UserCreate(UserBase):
    password: str
    date_of_birth: Optional[datetime] = None
    terms_accepted: bool

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class User(UserBase):
    user_id: int
    registration_date: datetime
    terms_accepted: Optional[bool] = False
    terms_accepted_at: Optional[datetime]

    class Config:
        from_attributes = True

@router.post('/register', response_model=User)
async def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Create a new user (defaults to pregnant_mother role)"""
    if not user_in.terms_accepted:
        raise HTTPException(status_code=400, detail='You must accept the Terms and Conditions to register.')

    db_user = crud.get_user_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(status_code=400, detail='Email already registered')
    
    db_user = crud.get_user_by_username(db, username=user_in.username)
    if db_user:
        raise HTTPException(status_code=400, detail='Username already taken')
    
    hashed_password = get_password_hash(user_in.password)
    new_user = crud.create_user(
        db=db,
        username=user_in.username,
        email=user_in.email,
        password_hash=hashed_password,
        role='pregnant_mother', # Hardcoded for public registration
        terms_accepted=user_in.terms_accepted
    )
    
    crud.create_system_log(
        db=db,
        log_type='AUTH',
        log_message=f"New user registered: {new_user.username}",
        severity='info',
        user_id=new_user.user_id,
        endpoint='/auth/register',
        http_method='POST',
        status_code=200
    )
    
    # Update optional fields if provided
    if user_in.first_name: new_user.first_name = user_in.first_name
    if user_in.last_name: new_user.last_name = user_in.last_name
    if user_in.date_of_birth: new_user.date_of_birth = user_in.date_of_birth
    
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post('/login', response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail='Incorrect username or password', 
            headers={'WWW-Authenticate': 'Bearer'}
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={'sub': user.username, 'role': user.role}, 
        expires_delta=access_token_expires
    )
    crud.create_system_log(
        db=db,
        log_type='AUTH',
        log_message=f"User login successful: {user.username}",
        severity='info',
        user_id=user.user_id,
        endpoint='/auth/login',
        http_method='POST',
        status_code=200
    )
    
    return {
        'access_token': access_token, 
        'token_type': 'bearer',
        'role': user.role
    }

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, 
        detail='Could not validate credentials', 
        headers={'WWW-Authenticate': 'Bearer'}
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: Optional[str] = payload.get('sub')
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = crud.get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user

@router.get('/me', response_model=User)
async def get_me(current_user: models.User = Depends(get_current_user)):
    """Get current authenticated user information"""
    return current_user

@router.post('/change-password')
async def change_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Change the current user's password after verifying the old password"""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail='Current password is incorrect.')

    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail='New password must be at least 8 characters long.')

    if verify_password(payload.new_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail='New password must be different from your current password.')

    current_user.password_hash = get_password_hash(payload.new_password)
    db.commit()

    crud.create_system_log(
        db=db,
        log_type='AUTH',
        log_message=f"Password changed for user: {current_user.username}",
        severity='info',
        user_id=current_user.user_id,
        endpoint='/auth/change-password',
        http_method='POST',
        status_code=200
    )

    return {'message': 'Password changed successfully.'}

@router.delete('/profile')
async def delete_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Permanently delete user account and all associated data"""
    if not current_user:
        raise HTTPException(status_code=401, detail='Authentication required.')

    username = current_user.username
    user_id = current_user.user_id
    
    # 1. Physical file cleanup for all user scans
    try:
        import os
        for img in current_user.images:
            if os.path.exists(img.file_path):
                os.remove(img.file_path)
            if img.prediction and img.prediction.gradcam_path:
                if os.path.exists(img.prediction.gradcam_path):
                    os.remove(img.prediction.gradcam_path)
    except Exception as e:
        # We don't want to block account deletion if file removal fails
        pass

    # 2. Database cleanup (cascades handle related records)
    db.delete(current_user)
    db.commit()
    
    crud.create_system_log(
        db=db,
        log_type='AUTH',
        log_message=f"User account deleted: {username} (ID: {user_id})",
        severity='warning',
        endpoint='/auth/profile',
        http_method='DELETE',
        status_code=200
    )
    
    return {'message': 'Account and all associated data deleted successfully.'}
