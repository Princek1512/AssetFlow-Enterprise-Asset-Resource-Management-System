from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.auth import SignupRequest, TokenResponse, UserOut

<<<<<<< HEAD
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests

router = APIRouter(prefix="/auth", tags=["Authentication"])

class GoogleLoginRequest(BaseModel):
    token: str


=======
router = APIRouter(prefix="/auth", tags=["Authentication"])

>>>>>>> 0b21ee9da9c9fae9a687d8d219bb9ee4966c31b9

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)) -> User:
    """
    Public self-service signup. Always creates a base Employee account —
    role escalation is only possible via the Admin promotion endpoint.
    """
    normalized_email = payload.email.lower()

    existing = await db.execute(select(User).where(User.email == normalized_email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        full_name=payload.full_name.strip(),
        email=normalized_email,
        hashed_password=hash_password(payload.password),
        role=RoleEnum.EMPLOYEE,
    )
    db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        # Guards the race condition between the pre-check above and the insert
        # (e.g. two concurrent signups with the same email).
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    OAuth2-compatible password login. `form_data.username` carries the email
    (standard OAuth2 form field naming) so this endpoint works out of the box
    with Swagger UI's "Authorize" button and any OAuth2 client.
    """
    normalized_email = form_data.username.lower()

    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalar_one_or_none()

    generic_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise generic_error

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This account has been deactivated."
        )

    access_token = create_access_token(
        subject=str(user.id), extra_claims={"role": user.role.value, "email": user.email}
    )
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserOut)
async def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
<<<<<<< HEAD


@router.post("/google-login", response_model=TokenResponse)
async def google_login(payload: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Google OAuth2 login. Verify token, get or create user as Employee.
    """
    try:
        # Note: In production, specify the actual client ID, but here we mock verification
        # or use a relaxed verification for local dev per PRD.
        idinfo = id_token.verify_oauth2_token(payload.token, requests.Request(), clock_skew_in_seconds=10)
        
        email = idinfo["email"].lower()
        full_name = idinfo.get("name", email.split("@")[0])
        
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            # Create user on first Google login, MUST default to Employee
            user = User(
                full_name=full_name,
                email=email,
                hashed_password=hash_password("google_oauth_placeholder"),
                role=RoleEnum.EMPLOYEE,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        access_token = create_access_token(
            subject=str(user.id), extra_claims={"role": user.role.value, "email": user.email}
        )
        return TokenResponse(access_token=access_token)
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google Token",
        )
=======
>>>>>>> 0b21ee9da9c9fae9a687d8d219bb9ee4966c31b9
