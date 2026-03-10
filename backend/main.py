"""FastAPI应用入口点"""

import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 导入配置管理
from .core.config import settings, get_logging_config, get_api_key

# 配置日志
logging_config = get_logging_config()
logging.basicConfig(
    level=getattr(logging, logging_config["level"]),
    format=logging_config["format"],
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler(logging_config["file"])  # 输出到文件
    ]
)

logger = logging.getLogger(__name__)


def _parse_cors_origins() -> list[str]:
    """Parse CORS origins from env with safe local defaults."""
    raw = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
    if not raw:
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]

# 使用统一的API路由注册
from .api.v1 import api_router
from .core.database import engine
from .models.base import Base

# Create FastAPI app
app = FastAPI(
    title="AutoClip API",
    description="AI视频切片处理API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Create database tables
@app.on_event("startup")
async def startup_event():
    logger.info("启动AutoClip API服务...")
    # 导入所有模型以确保表被创建
    from .models.bilibili import BilibiliAccount, UploadRecord
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表创建完成")
    
    # 加载API密钥到环境变量
    api_key = get_api_key()
    if api_key:
        os.environ["DASHSCOPE_API_KEY"] = api_key
        logger.info("API密钥已加载到环境变量")
    else:
        logger.warning("未找到API密钥配置")
    
    # 启动WebSocket网关服务 - 已禁用，使用新的简化进度系统
    # from .services.websocket_gateway_service import websocket_gateway_service
    # await websocket_gateway_service.start()
    # logger.info("WebSocket网关服务已启动")
    logger.info("WebSocket网关服务已禁用，使用新的简化进度系统")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("正在关闭AutoClip API服务...")
    # WebSocket网关服务已禁用
    # from .services.websocket_gateway_service import websocket_gateway_service
    # await websocket_gateway_service.stop()
    # logger.info("WebSocket网关服务已停止")
    logger.info("WebSocket网关服务已禁用")

# Add CORS middleware
cors_origins = _parse_cors_origins()
cors_allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
if "*" in cors_origins and cors_allow_credentials:
    cors_allow_credentials = False
    logger.warning("CORS_ALLOW_ORIGINS incluye '*': se desactiva allow_credentials por seguridad.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include unified API routes
app.include_router(api_router, prefix="/api/v1")

# 添加独立的video-categories端点
@app.get("/api/v1/video-categories")
async def get_video_categories():
    """获取视频分类配置."""
    return {
        "categories": [
            {
                "value": "default",
                "name": "General",
                "description": "Procesamiento de contenido de video general",
                "icon": "🎬",
                "color": "#4facfe"
            },
            {
                "value": "knowledge",
                "name": "Conocimiento",
                "description": "Contenido educativo: ciencia, tecnologia, historia y cultura",
                "icon": "📚",
                "color": "#52c41a"
            },
            {
                "value": "entertainment",
                "name": "Entretenimiento",
                "description": "Contenido de entretenimiento: juegos, musica, cine y similares",
                "icon": "🎮",
                "color": "#722ed1"
            },
            {
                "value": "business",
                "name": "Negocios",
                "description": "Contenido de negocios, emprendimiento e inversion",
                "icon": "💼",
                "color": "#fa8c16"
            },
            {
                "value": "experience",
                "name": "Experiencias",
                "description": "Historias personales y aprendizajes de vida",
                "icon": "🌟",
                "color": "#eb2f96"
            },
            {
                "value": "opinion",
                "name": "Opinion y analisis",
                "description": "Comentarios de actualidad y analisis de puntos de vista",
                "icon": "💭",
                "color": "#13c2c2"
            },
            {
                "value": "speech",
                "name": "Conferencias",
                "description": "Charlas, conferencias y presentaciones publicas",
                "icon": "🎤",
                "color": "#f5222d"
            }
        ]
    }

# 导入统一错误处理中间件
from .core.error_middleware import global_exception_handler

# 注册全局异常处理器
app.add_exception_handler(Exception, global_exception_handler)

if __name__ == "__main__":
    import uvicorn
    import sys
    
    # 默认端口
    port = 8000
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                try:
                    port = int(sys.argv[i + 1])
                except ValueError:
                    logger.error(f"无效的端口号: {sys.argv[i + 1]}")
                    port = 8000
    
    logger.info(f"启动服务器，端口: {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
