from datetime import datetime, timedelta
import hashlib
import random
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import Session
from app.model.users_model import User, UserRole

# Adjust this import to match how your configurations are instantiated 
# (e.g., from app.config import settings)
from app.config import settings 
from app.db.sql_database import Base, get_db
# from app.model.client_model import Client
# from app.model.builder_model import Builder

class OTP(Base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    otp = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)

    def is_expired(self):
        return datetime.utcnow() > self.expires_at


# --- JWT CONFIG ---
# Assumes Settings attributes are accessible or an instantiated config instance is used
SECRET_KEY = settings.SECRET_KEY  
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

# --- PASSWORD CONFIG ---
MAX_BCRYPT_BYTES = settings.MAX_BCRYPT_BYTES 
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
security = HTTPBearer()


def hash_password(password: str) -> str:
    # First hash with SHA256
    sha256_hash = hashlib.sha256(password.encode()).hexdigest()
    # Then hash using the argon2 context
    return pwd_context.hash(sha256_hash)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    sha256_hash = hashlib.sha256(plain_password.encode()).hexdigest()
    return pwd_context.verify(sha256_hash, hashed_password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    
def generate_otp(db: Session, email: str, expiry_minutes: int = 10):
    """Generate and store OTP in database"""
    otp_value = str(random.randint(100000, 999999))  # 6-digit OTP
    expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)

    # Delete any existing OTP for this email
    db.query(OTP).filter(OTP.email == email, OTP.is_used == False).delete()

    # Store new OTP
    otp_record = OTP(email=email, otp=otp_value, expires_at=expires_at)
    db.add(otp_record)
    db.commit()
    db.refresh(otp_record)

    return otp_value

def verify_otp(email: str, otp: str, db: Session):
    """Verify OTP stored in database and update user verification status"""
    otp_record = (
        db.query(OTP)
        .filter(OTP.email == email, OTP.is_used == False)
        .order_by(OTP.created_at.desc())
        .first()
    )

    if not otp_record:
        return False, "No OTP found for this email"

    # Check if expired
    if otp_record.is_expired():
        return False, "OTP expired"

    # Check validity
    if otp_record.otp != otp:
        return False, "Invalid OTP"

    # Mark OTP as used
    otp_record.is_used = True
    db.commit()

    return True, "OTP verified and email confirmed successfully"


# jwt token Auth check section
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    email = payload.get("sub")
    role = payload.get("role")
    
    if not email or not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    
    if role not in [UserRole.student, UserRole.industry_supervisor, UserRole.institution_supervisor, UserRole.admin]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user role in token")

    # Fetch user based on token role claim to minimize unnecessary DB queries
   
    user = db.query(User).filter(User.email == email, User.role == role).first()
   

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found in database")
    
    # Attach the role directly to the DB object dynamically so routes can check it if needed
    user.user_role = role 
    return user

def require_any_user(current_user=Depends(get_current_user)):
    """
    Dependency that allows access if the user is either a Client or a Builder.
    """
    if current_user.user_role not in ["client", "builder"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Client or Builder permissions required"
        )
    return current_user