"""
Parallel Search API - Clean implementation with instant search + background AI
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Optional, List
import time
import asyncio
import json
import uuid
import sys
from pathlib import Path

# Add common utilities
sys.path.append(str(Path(__file__).parent.parent.parent))
from common.utils import Logger

from .models import *
from ..core.database_service import DatabaseService
from ..core.enhanced_search_service import EnhancedSearchService
from ..core.ai_client_service import AIClientService

# Initialize logger
logger = Logger.setup_logger("backend.api.parallel_routes")

# Create router
router = APIRouter()

# Global storage for AI summary tasks
ai_summary_tasks = {}

# Active WebSocket connections
websocket_connections = {}

def get_services():
    """Get all services"""
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

@router.get("/search")
async def parallel_search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    limit: Optional[int] = Query(10, ge=1, le=50, description="Maximum number of results"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Parallel search: Returns instant search results + starts background AI summarization
    """
    try:
        start_time = time.time()
        services = get_services()
        
        # 1. Perform instant search
        search_result = services['search'].search(query=q, limit=limit)
        
        if search_result.get('error'):
            raise HTTPException(status_code=400, detail=f"Search failed: {search_result['error']}")
        
        # 2. Generate unique request ID for AI tracking
        ai_request_id = str(uuid.uuid4())
        
        # 3. Start background AI summarization task
        ai_summary_tasks[ai_request_id] = {
            'status': 'generating',
            'progress': 'Initializing AI...',
            'created_at': time.time()
        }
        
        # Start background task
        background_tasks.add_task(
            generate_ai_summary_background,
            q,
            search_result['results'],
            ai_request_id,
            services
        )
        
        # 4. Return instant search results
        total_time = round((time.time() - start_time) * 1000, 2)
        
        response = {
            'query': q,
            'results': [
                {
                    'id': result['id'],
                    'url': result['url'], 
                    'title': result['title'],
                    'content_preview': result['content_preview'],
                    'domain': result['domain'],
                    'word_count': result['word_count'],
                    'relevance_score': result['relevance_score']
                }
                for result in search_result['results']
            ],
            'total_found': search_result['total_found'],
            'search_time_ms': search_result['search_time_ms'],
            'total_time_ms': total_time,
            'ai_summary_request_id': ai_request_id
        }
        
        logger.info(f"Parallel search: '{q}' -> {len(response['results'])} results in {total_time}ms, AI task started")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def generate_ai_summary_background(query: str, results: list, request_id: str, services: dict):
    """Background task to generate AI summary with streaming"""
    try:
         # Wait for WebSocket connection to be established
        start_wait = time.time()
        while request_id not in websocket_connections:
            if time.time() - start_wait > 10:  # 10-second timeout
                logger.warning(f"WebSocket connection for {request_id} not established")
                return
            await asyncio.sleep(0.1)
        # Update progress
        ai_summary_tasks[request_id]['progress'] = 'Analyzing search results...'
        await notify_websocket_progress(request_id, 'Analyzing search results...')
        
        # Generate AI summary
        ai_result = services['ai'].generate_summary(query=query, results=results)
        
        if not ai_result.get('error'):
            # Stream the summary in chunks for typing effect
            summary_text = ai_result['summary']
            await stream_summary_chunks(request_id, summary_text)
            
            # Mark as completed
            ai_summary_tasks[request_id] = {
                'status': 'completed',
                'summary': summary_text,
                'model_used': ai_result['model_used'],
                'generation_time_ms': ai_result['generation_time_ms'],
                'created_at': ai_summary_tasks[request_id]['created_at']
            }
            
            # Send completion notification and close WebSocket
            await notify_websocket_completion(request_id)
            await close_websocket_connection(request_id)
            
        else:
            ai_summary_tasks[request_id] = {
                'status': 'failed',
                'error': ai_result['error'],
                'created_at': ai_summary_tasks[request_id]['created_at']
            }
            await notify_websocket_error(request_id, ai_result['error'])
            await close_websocket_connection(request_id)
            
        logger.info(f"AI summary completed for: '{query}'")
        
    except Exception as e:
        ai_summary_tasks[request_id] = {
            'status': 'failed',
            'error': str(e),
            'created_at': ai_summary_tasks[request_id]['created_at']
        }
        await notify_websocket_error(request_id, str(e))
        await close_websocket_connection(request_id)
        logger.error(f"AI summary failed for '{query}': {e}")

@router.websocket("/ws/summary/{request_id}")
async def websocket_ai_summary(websocket: WebSocket, request_id: str):
    """WebSocket endpoint for real-time AI summary streaming"""
   
    
    try:
        await websocket.accept()
        websocket_connections[request_id] = websocket
        # Send initial status
        if request_id in ai_summary_tasks:
            task = ai_summary_tasks[request_id]
            await websocket.send_text(json.dumps({
                'type': 'status',
                'status': task['status'],
                'progress': task.get('progress', '')
            }))
        
        # Keep connection alive with periodic pings until task is complete
        last_ping = time.time()
        while True:
            try:
                # Check if task is completed or failed - if so, break the loop
                if request_id in ai_summary_tasks:
                    task_status = ai_summary_tasks[request_id].get('status')
                    if task_status in ['completed', 'failed']:
                        logger.info(f"Task {request_id} finished with status: {task_status}, stopping ping loop")
                        break
                
                # Check if we need to send a keep-alive
                if time.time() - last_ping > 10:  # Every 10 seconds
                    await websocket.send_text(json.dumps({'type': 'ping'}))
                    last_ping = time.time()
                
                # Try to receive a message (with timeout)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1)
                # Process pong messages if needed
                try:
                    parsed_data = json.loads(data)
                    if parsed_data.get('type') == 'pong':
                        logger.debug(f"Received pong from {request_id}")
                except json.JSONDecodeError:
                    pass  # Ignore non-JSON messages
                
            except asyncio.TimeoutError:
                # Timeout is normal, just continue
                continue
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for request_id: {request_id}")
    except Exception as e:
        logger.error(f"WebSocket error for request_id {request_id}: {e}")
    finally:
        if request_id in websocket_connections:
            del websocket_connections[request_id]

async def stream_summary_chunks(request_id: str, summary_text: str):
    """Stream summary text in chunks for typing effect"""
    if request_id not in websocket_connections:
        return
    
    websocket = websocket_connections[request_id]
    
    # Split into words for smooth streaming
    words = summary_text.split(' ')
    chunk_size = 3  # Send 3 words at a time
    
    try:
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            if i + chunk_size < len(words):
                chunk += ' '
            
            await websocket.send_text(json.dumps({
                'type': 'summary_chunk',
                'text': chunk
            }))
            
            # Small delay for typing effect
            await asyncio.sleep(0.1)
            
    except Exception as e:
        logger.error(f"Error streaming summary chunks: {e}")

async def notify_websocket_progress(request_id: str, progress: str):
    """Notify WebSocket of progress update"""
    if request_id not in websocket_connections:
        return
    
    try:
        await websocket_connections[request_id].send_text(json.dumps({
            'type': 'progress',
            'progress': progress
        }))
    except Exception as e:
        logger.error(f"Error sending progress update: {e}")

async def notify_websocket_completion(request_id: str):
    """Notify WebSocket of completion"""
    if request_id not in websocket_connections:
        return
    
    try:
        await websocket_connections[request_id].send_text(json.dumps({
            'type': 'summary_done'
        }))
    except Exception as e:
        logger.error(f"Error sending completion notification: {e}")

async def notify_websocket_error(request_id: str, error: str):
    """Notify WebSocket of error"""
    if request_id not in websocket_connections:
        return
    
    try:
        await websocket_connections[request_id].send_text(json.dumps({
            'type': 'error',
            'error': error
        }))
    except Exception as e:
        logger.error(f"Error sending error notification: {e}")

async def close_websocket_connection(request_id: str):
    """Close WebSocket connection and cleanup"""
    if request_id not in websocket_connections:
        return
    
    try:
        websocket = websocket_connections[request_id]
        await websocket.close(code=1000, reason="AI processing completed")
        logger.info(f"WebSocket connection closed for request_id: {request_id}")
    except Exception as e:
        logger.error(f"Error closing WebSocket connection: {e}")
    finally:
        # Cleanup connection from dict
        if request_id in websocket_connections:
            del websocket_connections[request_id]

# Health, Config, Stats endpoints
@router.get("/health")
async def health_check():
    """Simple health check"""
    services = get_services()
    try:
        # Test database connection
        db_stats = services['db'].get_stats()
        
        return {
            'status': 'healthy',
            'timestamp': time.time(),
            'database': 'connected',
            'documents': db_stats.get('total_documents', 0),
            'ai_tasks_active': len([t for t in ai_summary_tasks.values() if t['status'] == 'generating']),
            'websocket_connections': len(websocket_connections)
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }

@router.get("/stats")
async def get_stats():
    """Get system statistics"""
    services = get_services()
    try:
        db_stats = services['db'].get_stats()
        search_stats = services['search'].get_search_stats() if hasattr(services['search'], 'get_search_stats') else {}
        
        # AI task statistics
        total_tasks = len(ai_summary_tasks)
        completed_tasks = len([t for t in ai_summary_tasks.values() if t['status'] == 'completed'])
        failed_tasks = len([t for t in ai_summary_tasks.values() if t['status'] == 'failed'])
        generating_tasks = len([t for t in ai_summary_tasks.values() if t['status'] == 'generating'])
        
        return {
            'database': db_stats,
            'search': search_stats,
            'ai_summary_tasks': {
                'total': total_tasks,
                'completed': completed_tasks,
                'failed': failed_tasks,
                'generating': generating_tasks
            },
            'websockets': {
                'active_connections': len(websocket_connections)
            },
            'timestamp': time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")

@router.get("/config")
async def get_config():
    """Get configuration"""
    return {
        'search_limit_max': 50,
        'search_limit_default': 10,
        'ai_summary_enabled': True,
        'websocket_enabled': True,
        'parallel_processing': True,
        'version': '1.0.0'
    }
