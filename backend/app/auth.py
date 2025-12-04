from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from connectors.mongo_connector import MongoConnector
import os

# --- Configuration ---
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# --- Password Hashing ---
# Using bcrypt directly instead of passlib to avoid compatibility issues
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# --- Security ---
security = HTTPBearer()

# --- Pydantic Models ---
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str

class PasswordReset(BaseModel):
    new_password: str

# --- Helper Functions ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

# --- User CRUD ---
def get_user_by_username(username: str) -> Optional[dict]:
    mongo = MongoConnector()
    try:
        pipeline = [{"$match": {"username": username}}, {"$limit": 1}]
        df = mongo.aggregate("users", pipeline)
        if df.empty:
            return None
        user = df.to_dict(orient="records")[0]
        user["id"] = str(user.get("_id", ""))
        return user
    finally:
        mongo.close()

def get_user_by_id(user_id: str) -> Optional[dict]:
    from bson import ObjectId
    mongo = MongoConnector()
    try:
        pipeline = [{"$match": {"_id": ObjectId(user_id)}}, {"$limit": 1}]
        df = mongo.aggregate("users", pipeline)
        if df.empty:
            return None
        user = df.to_dict(orient="records")[0]
        user["id"] = str(user.get("_id", ""))
        return user
    except:
        return None
    finally:
        mongo.close()

def create_user(username: str, email: str, password: str, role: str = "user") -> dict:
    mongo = MongoConnector()
    try:
        # Check if user exists
        existing = get_user_by_username(username)
        if existing:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        user_doc = {
            "username": username,
            "email": email,
            "password_hash": hash_password(password),
            "role": role,
            "created_at": datetime.utcnow()
        }
        mongo.insert_one("users", user_doc)
        return {"username": username, "email": email, "role": role}
    finally:
        mongo.close()

def get_all_users() -> list:
    mongo = MongoConnector()
    try:
        pipeline = [{"$project": {"password_hash": 0}}]  # Exclude password
        df = mongo.aggregate("users", pipeline)
        if df.empty:
            return []
        users = df.to_dict(orient="records")
        for user in users:
            user["id"] = str(user.get("_id", ""))
            if "_id" in user:
                del user["_id"]
        return users
    finally:
        mongo.close()

def update_user_password(user_id: str, new_password: str) -> bool:
    from bson import ObjectId
    mongo = MongoConnector()
    try:
        if not mongo.client:
            mongo.connect()
        result = mongo.db["users"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"password_hash": hash_password(new_password)}}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating password: {e}")
        return False
    finally:
        mongo.close()

# --- Dependencies ---
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
