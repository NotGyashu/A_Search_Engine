# ai_search/backend/api/routes.py
"""
API Routes - Simplified for the new Elasticsearch architecture.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Optional
import time
import asyncio
import json
import uuid
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.helpers import Logger

from .models import *
# Import the new, streamlined set of services
from ..core.enhanced_search_service import EnhancedSearchService
from ..core.ai_client_service import AIClientService

logger = Logger.setup_logger("backend.api.routes")
router = APIRouter()

# This global dictionary is required to track the status of background AI tasks.
ai_summary_tasks: Dict[str, Dict] = {}
websocket_connections: Dict[str, WebSocket] = {}

# --- Simplified Service Management ---

def get_services():
    """
    Initializes and returns the application's core services.
    This function now only creates the essential services needed.
    """
    # Using a simple singleton pattern to ensure services are created only once.
    if not hasattr(get_services, '_services'):
        logger.info("🚀 Initializing core services...")
        search_service = EnhancedSearchService()
        
        # Get AI Runner URL from environment variable
        ai_runner_url = os.getenv("AI_RUNNER_URL", "http://127.0.0.1:8001")
        logger.info(f"🤖 AI Runner URL: {ai_runner_url}")
        ai_service = AIClientService(ai_runner_url=ai_runner_url)
        
        get_services._services = {
            'search': search_service,
            'ai': ai_service
        }
        logger.info("✅ Core services initialized successfully.")
    
    return get_services._services

# --- API Endpoints ---

@router.get("/search")
async def parallel_search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    limit: Optional[int] = Query(10, ge=1, le=50, description="Maximum number of results"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Performs an instant search using Elasticsearch and starts a background task
    for AI summarization, returning a request ID for WebSocket streaming.
    """
    print("searching...")
    try:
        start_time = time.time()
        services = get_services()
        
        # 1. Perform instant search using the single, powerful search service
        search_result = services['search'].search(query=q, limit=limit)
        
        if search_result.get('error'):
            raise HTTPException(status_code=400, detail=f"Search failed: {search_result['error']}")
        
        # 2. Generate unique ID and start background AI task
        ai_request_id = str(uuid.uuid4())
        logger.info(f"🎯 Starting background AI task for query: '{q}' with ID: {ai_request_id[:8]}")
        
        background_tasks.add_task(
            generate_ai_summary_background,
            q,
            search_result['results'],
            ai_request_id,
            services['ai'] # Pass the AI service to the background task
        )
        
        # 3. Return instant search results
        search_result['ai_summary_request_id'] = ai_request_id
        search_result['total_time_ms'] = round((time.time() - start_time) * 1000, 2)
        
        logger.info(f"Parallel search for '{q}': {search_result['total_found']} results in {search_result['total_time_ms']}ms. AI task ID: {ai_request_id[:8]}")
        
        return search_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected search error for query '{q}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred during search.")

async def generate_ai_summary_background(query: str, results: list, request_id: str, ai_service: AIClientService):
    """Background task to generate AI summary via the AI Runner."""
    try:
        # Initialize the task status first
        ai_summary_tasks[request_id] = {
            'status': 'starting',
            'created_at': time.time()
        }
        
        logger.info(f"🤖 Starting AI summary generation for query: '{query}' with {len(results)} results")
        
        # Wait for WebSocket connection to be established (but don't block forever)
        start_wait = time.time()
        while request_id not in websocket_connections:
            if time.time() - start_wait > 10:  # 10-second timeout
                logger.warning(f"WebSocket connection for {request_id} not established - proceeding anyway")
                break  # Continue without WebSocket instead of returning
            await asyncio.sleep(0.1)
            
        # Update progress if WebSocket is connected
        if request_id in websocket_connections:
            ai_summary_tasks[request_id]['status'] = 'processing'
            ai_summary_tasks[request_id]['progress'] = 'Analyzing search results...'
            await notify_websocket_progress(request_id, 'Analyzing search results...')
        else:
            ai_summary_tasks[request_id]['status'] = 'processing'
        
        logger.info(f"🔄 Calling AI service for summary generation...")
        
        # Generate AI summary using the correct ai_service parameter
        ai_result = ai_service.generate_summary(query=query, results=results)
        
        logger.info(f"✅ AI service responded with result: {ai_result.get('model_used', 'unknown')}")
        
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

@router.get("/debug/ai-test")
async def debug_ai_test():
    """Debug endpoint to test AI service directly"""
    try:
        services = get_services()
        ai_service = services['ai']
        
        # Test with a simple query
        test_results = [
            {"title": "Test Article", "content_preview": "This is a test article about machine learning."},
            {"title": "Another Test", "content_preview": "Another test article about AI technology."}
        ]
        
        logger.info("🧪 Testing AI service directly...")
        result = ai_service.generate_summary(query="test", results=test_results)
        
        return {
            'ai_service_status': 'working',
            'test_result': result,
            'ai_runner_url': ai_service.ai_runner_url
        }
    except Exception as e:
        logger.error(f"❌ AI test failed: {e}")
        return {
            'ai_service_status': 'failed',
            'error': str(e)
        }
