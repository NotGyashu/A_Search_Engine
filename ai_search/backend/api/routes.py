"""
API Routes - Clean route definitions for the search engine
"""

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import time
from datetime import datetime
import sys
from pathlib import Path

# Add common utilities
sys.path.append(str(Path(__file__).parent.parent.parent))
from common.utils import Logger
from common.config import *

from .models import *
from ..core.database_service import DatabaseService
from ..core.search_service import SearchService
from ..core.ai_service import AIService


# Initialize logger
logger = Logger.setup_logger("backend.api.routes")

# Create router
router = APIRouter()

# Service dependencies
def get_services():
    """Get all services - this would be dependency injection in production"""
    if not hasattr(get_services, '_services'):
        db_service = DatabaseService()
        search_service = SearchService(db_service)
        ai_service = AIService()
        
        get_services._services = {
            'db': db_service,
            'search': search_service,
            'ai': ai_service
        }
    
    return get_services._services


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest, services=Depends(get_services)):
    """
    Search documents using BM25 algorithm with optional AI summarization
    """
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
    """
    Search documents using GET method (for easy testing)
    """
    # Convert to POST request format
    request = SearchRequest(
        query=q,
        limit=limit,
        include_ai_summary=ai_summary
    )
    
    # Use the POST handler
    return await search_documents(request, services)


@router.get("/stats", response_model=StatsResponse)
async def get_stats(services=Depends(get_services)):
    """
    Get comprehensive system statistics
    """
    try:
        # Get database stats
        db_stats = services['db'].get_database_stats()
        database_stats = DatabaseStats(**db_stats)
        
        # Get search stats
        search_stats_data = services['search'].get_stats()
        search_stats = SearchStats(**search_stats_data)
        
        # Get AI stats
        ai_stats_data = services['ai'].get_stats()
        ai_stats = AIStats(**ai_stats_data)
        
        # Create response
        response = StatsResponse(
            database=database_stats,
            search=search_stats,
            ai=ai_stats
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Stats API error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.get("/health", response_model=HealthCheck)
async def health_check(services=Depends(get_services)):
    """
    Comprehensive health check for all services
    """
    try:
        # Check database health
        db_health = services['db'].health_check()
        
        # Check search health
        search_health = services['search'].health_check()
        
        # Check AI health
        ai_health = services['ai'].health_check()
        
        # Determine overall status
        all_healthy = (
            db_health['status'] == 'healthy' and
            search_health['status'] == 'healthy' and
            ai_health['status'] == 'healthy'
        )
        
        status = 'healthy' if all_healthy else 'unhealthy'
        
        # Create detailed response
        health_response = HealthCheck(
            status=status,
            details={
                'database': db_health,
                'search': search_health,
                'ai': ai_health,
                'overall': {
                    'status': status,
                    'all_services_healthy': all_healthy
                }
            }
        )
        
        return health_response
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthCheck(
            status='unhealthy',
            details={
                'error': str(e),
                'message': 'Health check failed'
            }
        )


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """
    Get current system configuration
    """
    try:
        response = ConfigResponse(
            search_config={
                'BM25_K1': BM25_K1,
                'BM25_B': BM25_B,
                'BM25_MIN_TERM_LENGTH': BM25_MIN_TERM_LENGTH,
                'DEFAULT_SEARCH_LIMIT': DEFAULT_SEARCH_LIMIT,
                'MAX_SEARCH_LIMIT': MAX_SEARCH_LIMIT,
                'CONTENT_PREVIEW_LENGTH': CONTENT_PREVIEW_LENGTH,
                'TITLE_WEIGHT_MULTIPLIER': TITLE_WEIGHT_MULTIPLIER
            },
            ai_config={
                'AI_MODEL_PREFERENCE': AI_MODEL_PREFERENCE,
                'OPENAI_MODEL': OPENAI_MODEL,
                'AI_SUMMARY_MAX_LENGTH': AI_SUMMARY_MAX_LENGTH,
                'AI_FALLBACK_ENABLED': AI_FALLBACK_ENABLED
            },
            server_config={
                'BACKEND_HOST': BACKEND_HOST,
                'BACKEND_PORT': BACKEND_PORT,
                'FRONTEND_PORT': FRONTEND_PORT,
                'CORS_ENABLED': len(CORS_ALLOW_ORIGINS) > 0
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Config API error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get configuration: {str(e)}"
        )


@router.post("/search/rebuild")
async def rebuild_search_index(services=Depends(get_services)):
    """
    Rebuild the search index (admin endpoint)
    """
    try:
        logger.info("Rebuilding search index via API")
        
        # Rebuild index
        stats = services['search'].rebuild_index()
        
        return {
            'status': 'success',
            'message': 'Search index rebuilt successfully',
            'stats': stats,
            'timestamp': datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Index rebuild error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rebuild index: {str(e)}"
        )
