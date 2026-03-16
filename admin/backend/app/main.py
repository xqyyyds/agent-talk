from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine
from app.models import AdminUser
from app.routers import auth, admins, dashboard, users, agents, content, ops
from app.security import hash_password


app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    if (
        settings.app_env == "production"
        and settings.jwt_secret == "admin-secret-change-me"
    ):
        raise RuntimeError("JWT_SECRET is using unsafe default value in production")
    if (
        settings.app_env == "production"
        and settings.admin_init_password == "ChangeMe123!"
    ):
        print(
            "[admin_backend] WARNING: ADMIN_INIT_PASSWORD is using unsafe default value"
        )
    if (
        settings.app_env == "production"
        and settings.agent_service_runtime_token == "change-this-runtime-token"
    ):
        raise RuntimeError(
            "AGENT_SERVICE_RUNTIME_TOKEN is using unsafe default value in production"
        )

    Base.metadata.create_all(bind=engine)

    db = Session(engine)
    try:
        first_admin = db.query(AdminUser).first()
        if not first_admin:
            db.add(
                AdminUser(
                    username=settings.admin_init_username,
                    password_hash=hash_password(settings.admin_init_password),
                    status="active",
                )
            )
            db.commit()
            print("[admin_backend] initialized default admin user")
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "service": "admin_backend"}


app.include_router(auth.router)
app.include_router(admins.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(agents.router)
app.include_router(content.router)
app.include_router(ops.router)
