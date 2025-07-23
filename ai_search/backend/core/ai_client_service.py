"""
AI Client Service
Handles communication with the AI Runner microservice
"""

import requests
import time
from typing import Dict, List, Optional
import logging
from pathlib import Path
import sys

# Add common utilities
sys.path.append(str(Path(__file__).parent.parent.parent))
from common.utils import Logger

class AIClientService:
    """Client for communicating with AI Runner microservice"""
    
    def __init__(self, ai_runner_url: str = "http://127.0.0.1:8001"):
        self.ai_runner_url = ai_runner_url.rstrip('/')
        self.logger = Logger.setup_logger("backend.ai_client")
        self.timeout = 30  # 30 second timeout for AI operations
        print(f"AI Client initialized with URL: ")
        
    def generate_summary(self, query: str, results: List[Dict], max_length: int = 300) -> Dict:
        """Generate AI summary by calling the AI Runner microservice"""
        print(f"Generating AI summary for query: '' with  results in ai_search/backend/core/ai_client_service.py")
        if not results:
            return {
                'summary': "No results found for your query.",
                'model_used': "none",
                'generation_time_ms': 0,
                'error': None
            }
        
        start_time = time.time()
        
        try:
           
            # Prepare request
            request_data = {
                "query": query,
                "results": results,
                "max_length": max_length
            }
             # Add timeout to request
            response = requests.post(
                f"{self.ai_runner_url}/summarize",
                json=request_data,
                timeout=60,  # Increase timeout to 20 seconds
                headers={"Content-Type": "application/json"}
            )
            # Call AI Runner
            self.logger.info(f"Calling AI Runner for query: '{query}'")
            response = requests.post(
                f"{self.ai_runner_url}/summarize",
                json=request_data,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"AI summary generated using {result.get('model_used', 'unknown')}")
                return {
                    'summary': result['summary'],
                    'model_used': result['model_used'],
                    'generation_time_ms': result['generation_time_ms'],
                    'error': result.get('error')
                }
            else:
                error_msg = f"AI Runner returned status {response.status_code}"
                self.logger.error(error_msg)
                return self._fallback_summary(query, results, error_msg, start_time)
                
        except requests.exceptions.Timeout:
            error_msg = "AI Runner timeout"
            self.logger.warning(error_msg)
            return self._fallback_summary(query, results, error_msg, start_time)
            
        except requests.exceptions.ConnectionError:
            error_msg = "AI Runner unavailable"
            self.logger.warning(error_msg)
            return self._fallback_summary(query, results, error_msg, start_time)
            
        except Exception as e:
            error_msg = f"AI Runner error: {str(e)}"
            self.logger.error(error_msg)
            return self._fallback_summary(query, results, error_msg, start_time)
    
    def _fallback_summary(self, query: str, results: List[Dict], error: str, start_time: float) -> Dict:
        """Generate fallback summary when AI Runner is unavailable"""
        num_results = len(results)
        print(f"Fallback summary for query:  with  results in ai_search/backend/core/ai_client_service.py")
        if num_results == 1:
            summary = f"Found 1 relevant result for '{query}'."
        else:
            summary = f"Found {num_results} relevant results for '{query}'."
        
        if results:
            top_result = results[0]
            title = top_result.get('title', '').strip()
            if title:
                summary += f" Top result: '{title}'."
        
        summary += " (AI summarization unavailable)"
        
        generation_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            'summary': summary,
            'model_used': "fallback_template",
            'generation_time_ms': generation_time,
            'error': error
        }
    
    def health_check(self) -> Dict:
        """Check AI Runner health"""
        try:
            response = requests.get(
                f"{self.ai_runner_url}/health",
                timeout=5
            )
            
            if response.status_code == 200:
                return {
                    'status': 'healthy',
                    'ai_runner_available': True,
                    'ai_runner_data': response.json()
                }
            else:
                return {
                    'status': 'degraded',
                    'ai_runner_available': False,
                    'error': f"AI Runner returned status {response.status_code}"
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'ai_runner_available': False,
                'error': str(e)
            }
    
    def get_stats(self) -> Dict:
        """Get AI Runner statistics"""
        try:
            response = requests.get(
                f"{self.ai_runner_url}/stats",
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'available_models': [],
                    'primary_model': 'unavailable',
                    'service_status': 'error'
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get AI stats: {e}")
            return {
                'available_models': [],
                'primary_model': 'unavailable', 
                'service_status': 'unavailable'
            }
