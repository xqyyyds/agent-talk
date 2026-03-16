from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin_ops import router as admin_ops_router
from app.api.admin_runtime_config import router as admin_runtime_config_router
from app.api.admin_runtime_policy import router as admin_runtime_policy_router
from app.api.agent import router as agent_router
from app.api.creator import router as creator_router
from app.api.debate import router as debate_router
from app.api.qa import router as qa_router
from app.core.operations_engine import operations_engine
from app.utils.logger import setup_logger

logger = setup_logger()

app = FastAPI(
    title="Agent Service API",
    description="Agent orchestration service for AgentTalk",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(qa_router)
app.include_router(debate_router)
app.include_router(agent_router)
app.include_router(creator_router)
app.include_router(admin_ops_router)
app.include_router(admin_runtime_config_router)
app.include_router(admin_runtime_policy_router)


@app.get("/")
async def root():
    return {
        "service": "Agent Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "agent-service"}


@app.on_event("startup")
async def startup_event():
    logger.info("agent service starting")
    await operations_engine.start()


@app.on_event("shutdown")
async def shutdown_event():
    await operations_engine.stop()
    logger.info("agent service stopped")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
