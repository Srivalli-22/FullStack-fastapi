from fastapi import APIRouter, Depends, HTTPException, status, Response
import schemas, utils
from fastapi.security import OAuth2PasswordRequestForm
from mongo_db import create_user_document, get_user_by_email

router = APIRouter(prefix='/auth', tags=['auth'])


# ---------------------------------------------------------
# SIGNUP
# ---------------------------------------------------------
@router.post('/signup', response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def signup(user: schemas.UserCreate):
    existing = get_user_by_email(user.email)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed = utils.get_password_hash(user.password)

    created = create_user_document(
        full_name=user.full_name,
        email=user.email,
        hashed_password=hashed,
        role="shipment_manager",
    )

    if not created:
        raise HTTPException(status_code=500, detail="Unable to create user")

    return created



# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------
@router.post('/login', response_model=schemas.Token)
def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"[auth.login] Attempting login for email: {form_data.username}")

    user = get_user_by_email(form_data.username)
    if not user:
        logger.warning(f"[auth.login] User not found: {form_data.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    logger.info(f"[auth.login] User found: {user['email']}, verifying password...")

    if not utils.verify_password(form_data.password, user["hashed_password"]):
        logger.warning(f"[auth.login] Wrong password for {user['email']}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    logger.info(f"[auth.login] Login successful for user: {user['email']}")

    # IMPORTANT FIX: use user["id"], NOT user["_id"]
    user_id = user.get("id")
    if not user_id:
        logger.error("[auth.login] ERROR → user has no 'id' field (after stringify)")
        raise HTTPException(status_code=500, detail="User ID missing in database")

    token = utils.create_access_token({
        "sub": user["email"],
        "id": user_id
    })

    # Set cookie
    response.set_cookie(
        key='access_token',
        value=token,
        httponly=True,
        samesite='Lax'
    )

    return {"access_token": token, "token_type": "bearer"}



# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------
@router.post('/logout')
def api_logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"status": "ok", "message": "Logged out"}
