from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.qa import router as qa_router
from app.api.agent import router as agent_router
from app.api.creator import router as creator_router
from app.api.debate import router as debate_router
from app.api.admin_ops import router as admin_ops_router
from app.api.admin_runtime_config import router as admin_runtime_config_router
from app.utils.logger import setup_logger

# 初始化日志
logger = setup_logger()

# 创建 FastAPI 应用
app = FastAPI(
    title="Agent Service API",
    description="LangGraph 自动问答服务 - 为 AgentTalk 平台提供智能问答生成",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(qa_router)
app.include_router(debate_router)
app.include_router(agent_router)
app.include_router(creator_router)
app.include_router(admin_ops_router)
app.include_router(admin_runtime_config_router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "Agent Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "agent-service"}


@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    logger.info("🚀 Agent Service 启动中...")
    logger.info("📖 API 文档: http://localhost:8001/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    logger.info("⏹️  Agent Service 已停止")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
