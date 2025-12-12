from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException as FastAPIHTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from routers import auth_router, shipments_router, device_router
import routes
import utils
import os
from starlette.middleware.sessions import SessionMiddleware
from mongo_db import (
    connect_to_mongo,
    disconnect_from_mongo,
    ensure_demo_user,
    get_user_by_email,
)
from kafkamod.producer import test_connection as test_kafka_connection
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title='SCMXPertLite - Real-Time Shipment & Device Streaming (srillu)')


# Global exception handlers to ensure JSON responses for errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={
        "detail": exc.errors()
    })


@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Log the full exception and return a generic 500 JSON response
    logger.exception("Unhandled exception in request: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# CORS Middleware (Must be added BEFORE SessionMiddleware for proper order)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (change to specific URLs in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session Middleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv('JWT_SECRET','supersecret_jwt_key_change_this'))

# MongoDB connection on startup
@app.on_event("startup")
async def startup_event():
    print("\n" + "="*60)
    print("[SCMXPertLite] 🚀 Starting up backend services...")
    print("="*60)
    
    # Connect to MongoDB
    print("[startup] Connecting to MongoDB Atlas...")
    try:
        mongo_db_conn = connect_to_mongo()
        if mongo_db_conn:
            print("[startup] ✅ MongoDB connected")
            try:
                ensure_demo_user(
                    full_name="Demo User",
                    email="demo@demo.com",
                    hashed_password=utils.get_password_hash("Demo@123"),
                )
            except Exception as ensure_exc:
                print(f"[startup] ⚠️ Demo user seed warning: {ensure_exc}")
        else:
            print("[startup] ⚠️ MongoDB not connected (continuing without persistence)")
    except Exception as e:
        print(f"[startup] ⚠️ MongoDB connection warning: {e}")
    
    # Test Kafka connection
    print("[startup] Testing Kafka connection...")
    try:
        if test_kafka_connection():
            print("[startup] ✅ Kafka connected")
        else:
            print("[startup] ⚠️ Kafka not available (will retry when publishing)")
    except Exception as e:
        print(f"[startup] ⚠️ Kafka connection warning: {e}")
    
    print("="*60)
    print("[SCMXPertLite] ✅ Startup complete!\n")

@app.on_event("shutdown")
async def shutdown_event():
    print("\n" + "="*60)
    print("[SCMXPertLite] 🛑 Shutting down backend services...")
    print("="*60)
    
    # Disconnect from MongoDB
    print("[shutdown] Disconnecting from MongoDB...")
    try:
        disconnect_from_mongo()
        print("[shutdown] ✅ MongoDB disconnected")
    except Exception as e:
        print(f"[shutdown] ⚠️ MongoDB shutdown warning: {e}")
    
    print("="*60)
    print("[SCMXPertLite] ✅ Shutdown complete!\n")

# FIXED TEMPLATE & STATIC PATHS
templates = Jinja2Templates(directory='templates')
app.mount('/static', StaticFiles(directory='static'), name='static')

# Include your routers
app.include_router(auth_router)
app.include_router(shipments_router)
app.include_router(device_router)
app.include_router(routes.router)


# --------------------------
#         ROUTES
# --------------------------

@app.get('/health')
def health():
    return JSONResponse({'status': 'ok', 'message': 'Backend is healthy'}, status_code=200)


@app.get('/seed')
def seed_endpoint():
    """Quick seed endpoint to create demo data"""
    try:
        ensure_demo_user(
            full_name="Demo User",
            email="demo@demo.com",
            hashed_password=utils.get_password_hash("Demo@123"),
        )
        return JSONResponse({'status': 'ok', 'message': 'Demo user ensured'}, status_code=200)
    except Exception as e:
        return JSONResponse({'status': 'error', 'message': str(e)}, status_code=500)


@app.get('/', response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})


@app.get('/login', response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})


@app.get('/signup', response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse('signup.html', {'request': request})


@app.get('/dashboard', response_class=HTMLResponse)
def dashboard(request: Request):
    user = request.session.get('user') or 'Guest'
    return templates.TemplateResponse('dashboard.html', {'request': request, 'user': user})


# Login POST -> Dashboard
@app.post('/form-login')
def form_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    user = get_user_by_email(email)

    if not user or not utils.verify_password(password, user["hashed_password"]):
        return RedirectResponse('/login', status_code=303)

    request.session['user'] = {
        'id': user['id'],
        'email': user['email'],
        'full_name': user.get('full_name'),
    }
    return RedirectResponse('/dashboard', status_code=303)


# Logout
@app.get('/logout')
def logout(request: Request):
    # Clear server-side session and browser cookie if present
    request.session.clear()
    resp = RedirectResponse('/login')
    resp.delete_cookie('access_token')
    return resp
#   FRONTEND PAGES FIX
# --------------------------

@app.get('/shipment', response_class=HTMLResponse, include_in_schema=False)
def create_shipment_page(request: Request):
    return templates.TemplateResponse("create_shipment.html", {"request": request})

@app.get('/shipments', response_class=HTMLResponse, include_in_schema=False)
def shipments_page(request: Request):
    return templates.TemplateResponse("shipments.html", {"request": request})


@app.get('/devicestream', response_class=HTMLResponse, include_in_schema=False)
def device_stream_page(request: Request):
    return templates.TemplateResponse("device_stream.html", {"request": request})


@app.get('/account', response_class=HTMLResponse)
def account_page(request: Request):
    """Render account page showing signed-in user details via session or token."""
    user_safe = None

    sess_user = request.session.get('user')
    if isinstance(sess_user, dict):
        user_safe = sess_user
    elif isinstance(sess_user, str):
        user_doc = get_user_by_email(sess_user)
        if user_doc:
            user_safe = {
                'id': user_doc['id'],
                'email': user_doc.get('email'),
                'full_name': user_doc.get('full_name'),
            }

    if not user_safe:
        auth_header = request.headers.get('authorization') or request.headers.get('Authorization')
        if auth_header and auth_header.lower().startswith('bearer '):
            token = auth_header.split(' ', 1)[1]
            payload = utils.decode_access_token(token)
            if payload:
                user_doc = get_user_by_email(payload.get('sub', ''))
                if user_doc:
                    user_safe = {
                        'id': user_doc['id'],
                        'email': user_doc.get('email'),
                        'full_name': user_doc.get('full_name'),
                    }

    return templates.TemplateResponse('account.html', {'request': request, 'user': user_safe})
