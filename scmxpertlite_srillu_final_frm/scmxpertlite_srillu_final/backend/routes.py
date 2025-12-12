from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
# Templates are mounted from the container working directory '/app'
# Use the relative 'templates' directory so Jinja finds files when running in Docker
templates = Jinja2Templates(directory="templates")

# ---------------- AUTH PAGES ---------------- #

@router.get("/login")
def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/signup")
def signup(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@router.get("/forget-password")
def forget_password(request: Request):
    return templates.TemplateResponse("forget-password.html", {"request": request})

@router.get("/verify-otp")
def verify_otp(request: Request):
    return templates.TemplateResponse("verify-otp.html", {"request": request})


# ---------------- MAIN APP PAGES ---------------- #

@router.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


# 👉 My Account Page (show user details)
@router.get("/account")
def account(request: Request):
    return templates.TemplateResponse("account.html", {"request": request})


# 👉 My Shipments Page (list all shipments)
@router.get("/shipments")
def shipments_page(request: Request):
    return templates.TemplateResponse("shipments.html", {"request": request})


# 👉 Create Shipment Page (form page)
@router.get("/shipment")
def shipment_create_page(request: Request):
    return templates.TemplateResponse("create_shipment.html", {"request": request})


# 👉 Device Stream Page
@router.get("/devicestream")
def devicestream(request: Request):
    return templates.TemplateResponse("device_stream.html", {"request": request})


# 👉 Logout Page
@router.get("/logout")
def logout(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# ---------------- ROOT DEFAULT ---------------- #

@router.get("/")
def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})
