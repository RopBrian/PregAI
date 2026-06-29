from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from backend.api.routes import chat, analysis, auth, admin
from backend.config.settings import settings
from backend.chatbot.orchestrator import get_orchestrator
from sqlalchemy.exc import SQLAlchemyError
import os
import uuid
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for preloading models and resources"""
    logger.info("Preloading AI models and orchestrator...")
    try:
        # This triggers IntentClassifier load_model and LLMClient init
        get_orchestrator()
        logger.info("AI models and orchestrator preloaded successfully")
    except Exception as e:
        logger.error(f"Failed to preload models: {e}")
    
    yield
    logger.info("Shutting down PregnancyAI Backend")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Hybrid AI Chatbot and Fetal Brain Ultrasound Classification System",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_request_id_header(request: Request, call_next):
        request_id = str(uuid.uuid4())
        # Attach request ID to the request state so routes can access it
        request.state.request_id = request_id
        
        # Add to logs using loguru contextual logging
        with logger.contextualize(request_id=request_id):
            logger.info(f"Incoming request: {request.method} {request.url.path}")
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            logger.info(f"Completed request: {request.method} {request.url.path} with status {response.status_code}")
            return response

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        """Handle database errors and return JSON instead of HTML"""
        logger.error(f"Database error: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Database error. Please try again later."}
        )

    for api_prefix in ("/api/v1", "/v1"):
        app.include_router(chat.router, prefix=api_prefix)
        app.include_router(analysis.router, prefix=api_prefix)
        app.include_router(auth.router, prefix=api_prefix)
        app.include_router(admin.router, prefix=api_prefix)

    static_path = os.path.join("backend", "static")
    os.makedirs(static_path, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_path), name="static")

    @app.get("/")
    async def root():
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "status": "online",
            "documentation": "/docs"
        }

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    logger.info(f"{settings.app_name} API started successfully")
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.main:app", host="0.0.0.0", port=8000, reload=True)
