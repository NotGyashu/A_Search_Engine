"""
AI Runner Microservice
Handles all AI-powered operations with support for multiple AI models
Isolated from main backend to avoid dependency conflicts
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import time
import logging
from datetime import datetime
import uvicorn
from ai_service import AIService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ai_runner")

# Pydantic models
class SummarizeRequest(BaseModel):
    query: str
    results: List[Dict]
    max_length: Optional[int] = 300

class SummarizeResponse(BaseModel):
    summary: str
    model_used: str
    generation_time_ms: float
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    available_models: List[str]
    uptime_seconds: float

class AIStatsResponse(BaseModel):
    available_models: List[str]
    primary_model: str
    service_status: str

# Create FastAPI app
app = FastAPI(
    title="AI Runner Microservice",
    description="AI-powered summarization service with multi-model support",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global AI service instance
ai_service = None
start_time = time.time()

@app.on_event("startup")
async def startup_event():
    """Initialize AI service on startup"""
    global ai_service
    logger.info("🤖 Starting AI Runner Microservice...")
    ai_service = AIService()
    logger.info("✅ AI Runner ready")

@app.post("/summarize", response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest):
    """Generate AI summary of search results"""
    try:
        logger.info(f"📝 Summarization request: '{request.query}' with {len(request.results)} results")
        
        # Generate summary using AI service
        result = ai_service.generate_summary(
            query=request.query,
            results=request.results,
            max_length=request.max_length
        )
        
        response = SummarizeResponse(
            summary=result['summary'],
            model_used=result['model_used'],
            generation_time_ms=result['generation_time_ms'],
            error=result['error']
        )
        
        logger.info(f"✅ Summary generated using {result['model_used']} in {result['generation_time_ms']}ms")
        return response
        
    except Exception as e:
        logger.error(f"❌ Summarization failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI summarization failed: {str(e)}"
        )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check AI service health
        ai_health = ai_service.health_check() if ai_service else {"status": "not_initialized"}
        
        return HealthResponse(
            status="healthy" if ai_health.get("status") == "healthy" else "degraded",
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            available_models=ai_health.get("available_models", []),
            uptime_seconds=round(time.time() - start_time, 2)
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/stats", response_model=AIStatsResponse)
async def get_ai_stats():
    """Get AI service statistics"""
    try:
        if not ai_service:
            raise HTTPException(status_code=503, detail="AI service not initialized")
        
        health = ai_service.health_check()
        
        return AIStatsResponse(
            available_models=health.get("available_models", []),
            primary_model=health.get("primary_model", "none"),
            service_status=health.get("status", "unknown")
        )
    except Exception as e:
        logger.error(f"Stats request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stats unavailable: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "AI Runner Microservice",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "summarize": "/summarize",
            "health": "/health",
            "stats": "/stats",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    logger.info("🚀 Starting AI Runner server...")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001,  # Different port from main backend
        log_level="info"
    )
