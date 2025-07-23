"""
Main FastAPI Server - Clean, modular backend server
Handles all API endpoints with proper error handling and logging
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
import uvicorn
import time
from datetime import datetime
import sys
from pathlib import Path
import traceback
from fastapi.encoders import jsonable_encoder


# Add common utilities
sys.path.append(str(Path(__file__).parent.parent.parent))
from common.utils import Logger
from common.config import *

from .routes import router
from .models import ErrorResponse


# Initialize logger
logger = Logger.setup_logger("backend.api.server")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    # Create FastAPI app
    app = FastAPI(
        title="AI Search Engine API",
        description="High-performance search engine with BM25 ranking and AI summarization",
        version="3.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOW_ORIGINS,
        allow_credentials=CORS_ALLOW_CREDENTIALS,
        allow_methods=CORS_ALLOW_METHODS,
        allow_headers=CORS_ALLOW_HEADERS,
    )
    
    # Add request logging middleware
    @app.middleware("http")
    async def websocket_cors_middleware(request: Request, call_next):
        if "upgrade" in request.headers.get("connection", "").lower() and \
        "websocket" in request.headers.get("upgrade", "").lower():
            # Allow WebSocket connections from any origin
            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = "*"
            return response
        return await call_next(request)

    async def log_requests(request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.url.path}")
        
        # Process request
        response = await call_next(request)
        
        # Log response
        process_time = round((time.time() - start_time) * 1000, 2)
        logger.info(f"Response: {response.status_code} in {process_time}ms")
        
        return response
    
    # Include API routes
    app.include_router(router, prefix="/api")
    
    # Root endpoint - serve basic info
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Root endpoint with basic information"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Search Engine</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                .container { max-width: 800px; margin: 0 auto; }
                .header { background: #f4f4f4; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .endpoint { background: #e8f4f8; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .method { background: #4CAF50; color: white; padding: 4px 8px; border-radius: 3px; font-size: 12px; }
                .method.get { background: #2196F3; }
                .method.post { background: #FF9800; }
                a { color: #2196F3; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔍 AI Search Engine API</h1>
                    <p>High-performance search with BM25 ranking and AI summarization</p>
                    <p><strong>Version:</strong> 3.0.0 | <strong>Status:</strong> Active</p>
                </div>
                
                <h2>🚀 API Endpoints</h2>
                
                <div class="endpoint">
                    <span class="method post">POST</span> 
                    <strong>/api/search</strong> - Search documents with AI summary
                    <br><small>Main search endpoint with full request body</small>
                </div>
                
                <div class="endpoint">
                    <span class="method get">GET</span> 
                    <strong>/api/search</strong> - Search documents (query parameters)
                    <br><small>Simple search: ?q=your+query&limit=10&ai_summary=true</small>
                </div>
                
                <div class="endpoint">
                    <span class="method get">GET</span> 
                    <strong>/api/stats</strong> - System statistics
                    <br><small>Database, search, and AI service statistics</small>
                </div>
                
                <div class="endpoint">
                    <span class="method get">GET</span> 
                    <strong>/api/health</strong> - Health check
                    <br><small>Check status of all services</small>
                </div>
                
                <div class="endpoint">
                    <span class="method get">GET</span> 
                    <strong>/api/config</strong> - Configuration
                    <br><small>Current system configuration</small>
                </div>
                
                <h2>📖 Documentation</h2>
                <p>
                    <a href="/api/docs">📋 Swagger UI</a> - Interactive API documentation<br>
                    <a href="/api/redoc">📚 ReDoc</a> - Alternative documentation view
                </p>
                
                <h2>🎯 Quick Test</h2>
                <p>Try a quick search: <a href="/api/search?q=python&limit=5">Search for "python"</a></p>
                
                <h2>💡 Frontend</h2>
                <p>React frontend available at: <a href="http://localhost:3000">http://localhost:3000</a></p>
            </div>
        </body>
        </html>
        """
    
    # Custom exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions"""
        logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
        
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(ErrorResponse(
                message=exc.detail,
                error_code=f"HTTP_{exc.status_code}",
                details={"path": str(request.url.path)}
            ).dict())
        )

    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors"""
        logger.warning(f"Validation Error: {exc.errors()}")
        
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(ErrorResponse(
                message="Request validation failed",
                error_code="VALIDATION_ERROR",
                details={"errors": exc.errors()}
            ).dict())
        )

    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions"""
        logger.error(f"Unexpected error: {exc}")
        logger.error(traceback.format_exc())
        
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(ErrorResponse(
                message="Internal server error",
                error_code="INTERNAL_ERROR",
                details={"path": str(request.url.path)}
            ).dict())
        )
    
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Application startup tasks"""
        logger.info("🚀 AI Search Engine API starting up...")
        logger.info(f"📊 Backend Port: {BACKEND_PORT}")
        logger.info(f"🌐 Frontend Port: {FRONTEND_PORT}")
        logger.info(f"🔧 CORS Origins: {CORS_ALLOW_ORIGINS}")
        
        # Warm up services (this initializes the search index)
        try:
            from .routes import get_services
            services = get_services()
            logger.info("✅ All services initialized successfully")
        except Exception as e:
            logger.error(f"❌ Service initialization failed: {e}")
    
    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown tasks"""
        logger.info("🛑 AI Search Engine API shutting down...")
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    # Run server
    logger.info(f"Starting server on {BACKEND_HOST}:{BACKEND_PORT}")
    
    uvicorn.run(
        "server:app",
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        reload=BACKEND_RELOAD,
        log_level=BACKEND_LOG_LEVEL.lower(),
        access_log=True
    )
