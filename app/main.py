from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.sql_database import Base, engine
from fastapi.staticfiles import StaticFiles
from app.config import Settings
from app.router.logs_router import log_router
from app.router.auth_router import auth_router
from app.router.users_router import users_router
from app.router.institute_supervisor import institute_supervisor_router

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="PTI e-SIWES API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(Settings.ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/images", StaticFiles(directory="images"), name="images")


# ===========================================
#   ROUTES
# ===========================================
   
app.include_router(auth_router, prefix="/api/auth/user", tags=["Role Based Users Auth"])
app.include_router(users_router, prefix="/api/user", tags=["Users & Profiles"])
app.include_router(log_router, prefix="/api/log", tags=["Logbook Management"])
app.include_router(institute_supervisor_router, prefix="/api/institution", tags=["Institution Dashboard"])
