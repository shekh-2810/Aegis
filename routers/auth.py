from fastapi import APIRouter, Depends, HTTPException, status

from auth_utils import create_access_token, get_current_user, hash_password, verify_password
from database import users_collection
from models import TokenResponse, UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(user: dict) -> UserOut:
    return UserOut(id=str(user["_id"]), name=user["name"], email=user["email"])


@router.post("/signup", response_model=TokenResponse)
def signup(request: UserCreate):
    email = request.email.lower().strip()

    if users_collection.find_one({"email": email}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")

    result = users_collection.insert_one(
        {
            "name": request.name.strip(),
            "email": email,
            "password_hash": hash_password(request.password),
        }
    )
    user = users_collection.find_one({"_id": result.inserted_id})

    token = create_access_token(str(user["_id"]))
    return TokenResponse(access_token=token, user=_user_out(user))


@router.post("/login", response_model=TokenResponse)
def login(request: UserLogin):
    email = request.email.lower().strip()
    user = users_collection.find_one({"email": email})

    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    token = create_access_token(str(user["_id"]))
    return TokenResponse(access_token=token, user=_user_out(user))


@router.get("/me", response_model=UserOut)
def me(current_user: dict = Depends(get_current_user)):
    return _user_out(current_user)
