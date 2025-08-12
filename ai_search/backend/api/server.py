# ai_search/backend/api/server.py
"""
Main FastAPI Server - Clean, modular backend server for the OpenSearch-powered search engine.
Handles all API endpoints with proper error handling and logging.
"""

import os
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from dotenv import load_dotenv

# --- Configuration & Setup ---

# Load environment variables from .env file at the project root
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Add project root to Python path for clean imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.helpers import Logger
from .routes import router
from .models import ErrorResponse

# Get values from .env with sensible defaults
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))
BACKEND_LOG_LEVEL = os.getenv("BACKEND_LOG_LEVEL", "info").lower()
BACKEND_RELOAD = os.getenv("BACKEND_RELOAD", "true").lower() == "true"

# CORS Settings
CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
CORS_ALLOW_METHODS = os.getenv("CORS_ALLOW_METHODS", "*").split(",")
CORS_ALLOW_HEADERS = os.getenv("CORS_ALLOW_HEADERS", "*").split(",")

# Frontend port for development info
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", 3000))

# Initialize logger
logger = Logger.setup_logger("backend.api.server")

# --- FastAPI Application Factory ---

def create_app() -> FastAPI:
    """Create and configure the main FastAPI application."""
    
    # Updated description to reflect the new architecture
    app = FastAPI(
        title="AI Search Engine API",
        description="High-performance search engine powered by OpenSearch with AI summarization",
        version="4.0.0", # Version bump for new architecture
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    # Add CORS middleware for frontend communication
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOW_ORIGINS,
        allow_credentials=CORS_ALLOW_CREDENTIALS,
        allow_methods=CORS_ALLOW_METHODS,
        allow_headers=CORS_ALLOW_HEADERS,
    )
    
    # Add request logging and WebSocket middleware
    @app.middleware("http")
    async def request_middleware(request: Request, call_next):
        # Handle WebSocket CORS headers
        if "upgrade" in request.headers.get("connection", "").lower() and \
           "websocket" in request.headers.get("upgrade", "").lower():
            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = request.headers.get("origin") or "*"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response

        # Log standard HTTP requests
        start_time = time.time()
        logger.info(f"Request: {request.method} {request.url.path}")
        response = await call_next(request)
        process_time = round((time.time() - start_time) * 1000, 2)
        logger.info(f"Response: {response.status_code} in {process_time}ms")
        return response
    
    # Include the API router from routes.py
    app.include_router(router, prefix="/api")
    
    # --- Root Endpoint & Exception Handlers ---

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def root():
        """Provides a simple HTML page with API info and links."""
        # Updated HTML to remove "BM25" and mention OpenSearch
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Search Engine API</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; line-height: 1.6; background-color: #f7f7f7; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; background: #fff; padding: 20px 40px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
                .header {{ text-align: center; border-bottom: 1px solid #eee; padding-bottom: 20px; margin-bottom: 20px; }}
                .header h1 {{ color: #1a73e8; }}
                .endpoint {{ background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #1a73e8; }}
                a {{ color: #1a73e8; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 AI Search Engine API</h1>
                    <p>High-performance search powered by <strong>OpenSearch</strong> with AI summarization.</p>
                    <p><strong>Version:</strong> 4.0.0 | <strong>Status:</strong> Active</p>
                </div>
                <h2>API Endpoints</h2>
                <div class="endpoint"><strong>GET /api/search</strong> - Perform a search query.</div>
                <div class="endpoint"><strong>GET /api/health</strong> - Check the health of all services.</div>
                
                <h2>Documentation</h2>
                <p>
                    <a href="/api/docs">📋 Swagger UI</a> - Interactive API documentation<br>
                    <a href="/api/redoc">📚 ReDoc</a> - Alternative documentation view
                </p>
                
                <h2>Frontend</h2>
                <p>React frontend available at: <a href="http://localhost:{FRONTEND_PORT}">http://localhost:{FRONTEND_PORT}</a></p>
            </div>
        </body>
        </html>
        """
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail} for {request.url.path}")
        return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(ErrorResponse(message=exc.detail, error_code=f"HTTP_{exc.status_code}")))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation Error: {exc.errors()}")
        return JSONResponse(status_code=422, content=jsonable_encoder(ErrorResponse(message="Request validation failed", error_code="VALIDATION_ERROR", details={"errors": exc.errors()})))

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        return JSONResponse(status_code=500, content=jsonable_encoder(ErrorResponse(message="Internal server error", error_code="INTERNAL_ERROR")))
    
    # --- Startup & Shutdown Events ---

    @app.on_event("startup")
    async def startup_event():
        """Initializes all necessary services when the application starts."""
        logger.info("🚀 AI Search Engine API starting up...")
        logger.info(f"Host: {BACKEND_HOST}, Port: {BACKEND_PORT}")
        logger.info(f"Allowed CORS Origins: {CORS_ALLOW_ORIGINS}")
        
        try:
            # This call initializes the singleton services (Search, AI)
            from .routes import get_services
            get_services()
            logger.info("✅ Core services initialized successfully.")
        except Exception as e:
            logger.critical(f"❌ CRITICAL: Service initialization failed: {e}", exc_info=True)
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("🛑 AI Search Engine API shutting down...")
    
    return app

# --- Application Instance ---
app = create_app()

if __name__ == "__main__":
    logger.info(f"Starting server with uvicorn on http://{BACKEND_HOST}:{BACKEND_PORT}")
    uvicorn.run(
        "server:app",
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        reload=BACKEND_RELOAD,
        log_level=BACKEND_LOG_LEVEL,
        access_log=True
    )
