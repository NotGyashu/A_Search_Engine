"""API Routes - Clean route definitions for the search engine
"""

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import time
from datetime import datetime
import sys
from pathlib import Path
from fastapi.encoders import jsonable_encoder

# Add common utilities
sys.path.append(str(Path(__file__).parent.parent.parent))
from common.utils import Logger

from .models import *
from ..core.database_service import DatabaseService
from ..core.enhanced_search_service import EnhancedSearchService
from ..core.ai_client_service import AIClientService

# Initialize logger 
logger = Logger.setup_logger("backend.api.routes")

# Create router
router = APIRouter()

def get_services():
    """Get all services - this would be dependency injection in production"""
    if not hasattr(get_services, '_services'):
        db_service = DatabaseService()
        search_service = EnhancedSearchService(db_service)
        ai_service = AIClientService()

        get_services._services = {
            'db': db_service,
            'search': search_service,
            'ai': ai_service
        }

    return get_services._services

@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest, services=Depends(get_services)):
    """Search documents using BM25 algorithm with optional AI summarization"""
    try:
        start_time = time.time()

        # Perform search
        search_result = services['search'].search(
            query=request.query,
            limit=request.limit
        )

        # Handle search errors
        if search_result.get('error'):
            raise HTTPException(
                status_code=400,
                detail=f"Search failed: {search_result['error']}"
            )

        # Convert results to response format
        results = [
            SearchResult(
                id=result['id'],
                url=result['url'],
                title=result['title'],
                content_preview=result['content_preview'],
                domain=result['domain'],
                word_count=result['word_count'],
                relevance_score=result['relevance_score']
            )
            for result in search_result['results']
        ]

        # Generate AI summary if requested
        ai_summary = None
        ai_model_used = None
        ai_generation_time = None

        if request.include_ai_summary and results:
            ai_result = services['ai'].generate_summary(
                query=request.query,
                results=search_result['results']
            )

            if not ai_result.get('error'):
                ai_summary = ai_result['summary']
                ai_model_used = ai_result['model_used']
                ai_generation_time = ai_result['generation_time_ms']

        # Create response
        response = SearchResponse(
            query=request.query,
            results=results,
            total_found=search_result['total_found'],
            search_time_ms=search_result['search_time_ms'],
            search_method=search_result['search_method'],
            ai_summary=ai_summary,
            ai_model_used=ai_model_used,
            ai_generation_time_ms=ai_generation_time
        )

        # Log successful search
        total_time = round((time.time() - start_time) * 1000, 2)
        logger.info(f"Search API: '{request.query}' -> {len(results)} results in {total_time}ms")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search API error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/search", response_model=SearchResponse)
async def search_documents_get(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    limit: Optional[int] = Query(10, ge=1, le=50, description="Maximum number of results"),
    ai_summary: Optional[bool] = Query(True, description="Include AI summary"),
    services=Depends(get_services)
):
    """Search documents using GET method (for easy testing)"""
    request = SearchRequest(
        query=q,
        limit=limit,
        include_ai_summary=ai_summary
    )
    return await search_documents(request, services)

@router.get("/health")
async def health_check(services=Depends(get_services)):
    """Simple health check"""
    try:
        # Basic health checks
        db_health = services['db'].health_check()
        search_health = services['search'].health_check()
        ai_health = services['ai'].health_check()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "database": db_health.get('status', 'unknown'),
                "search": search_health.get('status', 'unknown'),
                "ai_runner": ai_health.get('status', 'unknown')
            }
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/stats")
async def get_stats(services=Depends(get_services)):
    """Get system statistics"""
    try:
        # Get basic stats
        db_stats = services['db'].get_database_stats()
        search_stats = services['search'].get_stats()
        ai_stats = services['ai'].get_stats()

        return {
            "database": {
                "total_documents": db_stats.get('total_documents', 0),
                "database_size_mb": db_stats.get('database_size_mb', 0)
            },
            "search": {
                "indexed_documents": search_stats.get('indexed_documents', 0),
                "vocabulary_size": search_stats.get('vocabulary_size', 0)
            },
            "ai": {
                "available_models": ai_stats.get('available_models', []),
                "service_status": ai_stats.get('service_status', 'unknown')
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/config")
async def get_config():
    """Get configuration"""
    try:
        return {
            "backend_port": 8000,
            "ai_runner_port": 8001,
            "frontend_port": 3000,
            "search_method": "Enhanced BM25",
            "ai_enabled": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Config error: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
