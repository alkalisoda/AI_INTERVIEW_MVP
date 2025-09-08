from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import uvicorn

from core.config import settings
from core.utils import ResponseFormatter
from api_gateway.routes import router as api_router, http_exception_handler
from ai_backend.coordinator import AICoordinator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Interviewer Backend",
    description="Modular AI-powered interview system with speech recognition, planning, and chatbot capabilities",
    version="2.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Global AI Coordinator instance
ai_coordinator = None

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    global ai_coordinator
    
    try:
        logger.info("Starting AI Interviewer Backend...")
        
        # Validate configuration
        settings.validate()
        logger.info("Configuration validated successfully")
        
        # Initialize AI Coordinator
        ai_coordinator = AICoordinator()
        logger.info("AI Coordinator initialized")
        
        # Store AI coordinator in app state for access in routes
        app.state.ai_coordinator = ai_coordinator
        
        # Perform health checks
        health_status = await ai_coordinator.health_check()
        if health_status["coordinator_status"] != "healthy":
            logger.warning(f"AI Coordinator health check warning: {health_status}")
        else:
            logger.info("AI Coordinator health check passed")
        
        logger.info("AI Interviewer Backend started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Shutting down AI Interviewer Backend...")
    
    # Cleanup resources if needed
    # Note: Current implementation doesn't require explicit cleanup
    # but this is where you would close database connections, etc.
    
    logger.info("AI Interviewer Backend shut down complete")

# Include API routes
app.include_router(
    api_router, 
    prefix="/api/v1",
    tags=["Interview API"]
)

# Register exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)

@app.get("/")
async def root():
    """Root path health check"""
    return ResponseFormatter.success_response({
        "service": "AI Interviewer Backend",
        "version": "2.0.0",
        "status": "running",
        "architecture": {
            "api_gateway": "Frontend communication layer",
            "ai_backend": {
                "coordinator": "AI module orchestration", 
                "speech_recognition": "Audio to text conversion",
                "planner": "Response analysis and planning",
                "chatbot": "Follow-up question generation"
            }
        },
        "endpoints": {
            "docs": "/docs" if settings.DEBUG else "disabled",
            "api": "/api/v1"
        }
    })

@app.get("/health")
async def detailed_health_check():
    """Detailed health check"""
    try:
        if ai_coordinator is None:
            return JSONResponse(
                status_code=503,
                content=ResponseFormatter.error_response(
                    "AI Coordinator not initialized",
                    code=503
                )
            )
        
        # Get detailed health status from AI coordinator
        health_status = await ai_coordinator.health_check()
        
        system_health = {
            "api_gateway": "healthy",
            "core_services": "healthy",
            "ai_backend": health_status
        }
        
        # Determine overall status
        overall_status = "healthy"
        if health_status["coordinator_status"] != "healthy":
            overall_status = "degraded"
        
        response_code = 200 if overall_status == "healthy" else 503
        
        return JSONResponse(
            status_code=response_code,
            content=ResponseFormatter.success_response({
                "overall_status": overall_status,
                "components": system_health,
                "configuration": {
                    "environment": settings.ENVIRONMENT,
                    "debug_mode": settings.DEBUG,
                    "max_audio_size": settings.MAX_AUDIO_SIZE,
                    "supported_audio_formats": settings.SUPPORTED_AUDIO_FORMATS
                }
            })
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content=ResponseFormatter.error_response(
                "Health check failed",
                code=500,
                details=str(e)
            )
        )

@app.get("/api/v1")
async def api_info():
    """API information endpoint"""
    return ResponseFormatter.success_response({
        "api_version": "v1",
        "available_endpoints": {
            "interview_management": {
                "start": "POST /api/v1/interview/start",
                "status": "GET /api/v1/interview/{session_id}/status",
                "current_question": "GET /api/v1/interview/{session_id}/question",
                "complete": "GET /api/v1/interview/{session_id}/complete"
            },
            "interaction": {
                "transcribe": "POST /api/v1/interview/{session_id}/transcribe",
                "submit_answer": "POST /api/v1/interview/{session_id}/submit-answer",
                "generate_followup": "POST /api/v1/interview/{session_id}/generate-followup",
                "next_question": "POST /api/v1/interview/{session_id}/next-question"
            },
            "system": {
                "health": "GET /api/v1/health",
                "root": "GET /"
            }
        },
        "supported_features": [
            "Speech-to-text transcription",
            "AI-powered response analysis",
            "Contextual follow-up generation", 
            "Multi-style interview support",
            "Real-time session management"
        ]
    })

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=ResponseFormatter.error_response(
            "Internal server error",
            code=500,
            details="An unexpected error occurred" if not settings.DEBUG else str(exc)
        )
    )

# Development server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        log_level="info"
    )