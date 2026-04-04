from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field

from app.core.auth import create_access_token, hash_password, verify_password, decode_token
from app.core.config import get_settings
from app.services.user_store import UserStore

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_user_store() -> UserStore:
    return UserStore(get_settings().users_path)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    email: str = Field(min_length=5, max_length=128)
    password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, store: UserStore = Depends(get_user_store)) -> TokenResponse:
    if store.get_by_username(req.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    if store.get_by_email(req.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    store.create(req.username, req.email, hash_password(req.password))
    token = create_access_token(req.username)
    return TokenResponse(access_token=token, username=req.username)


@router.post("/login", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    store: UserStore = Depends(get_user_store),
) -> TokenResponse:
    user = store.get_by_username(form.username)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token(user.username)
    return TokenResponse(access_token=token, username=user.username)


@router.get("/me")
def me(token: str = Depends(oauth2_scheme), store: UserStore = Depends(get_user_store)) -> dict:
    username = decode_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = store.get_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"username": user.username, "email": user.email}
