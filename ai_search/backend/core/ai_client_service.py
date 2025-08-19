"""
AI Client Service - Enhanced Integration with AI Intelligence Hub
Handles communication with the AI Runner microservice with full Phase 1 & 2 capabilities
"""

import requests
import time
from typing import Dict, List, Optional
import logging
from pathlib import Path
import sys

# Add common utilities
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.helpers import Logger

class AIClientService:
    """Enhanced client for communicating with AI Intelligence Hub microservice"""
    
    def __init__(self, ai_runner_url: str = "http://127.0.0.1:8001"):
        self.ai_runner_url = ai_runner_url.rstrip('/')
        self.logger = Logger.setup_logger("backend.ai_client")
        self.timeout = 30  # 30 second timeout for AI operations
        self.fast_timeout = 5  # 5 second timeout for quick operations
        self.logger.info(f"� AI Intelligence Hub Client initialized with URL: {self.ai_runner_url}")
        
    def generate_summary(self, query: str, results: List[Dict], max_length: int = 300) -> Dict:
        """Generate AI summary by calling the AI Runner microservice"""
        self.logger.info(f"📝 Generating AI summary for query: '{query}' with {len(results)} results")
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
            
            self.logger.info(f"🚀 Calling AI Runner at {self.ai_runner_url}/summarize")
            response = requests.post(
                f"{self.ai_runner_url}/summarize",
                json=request_data,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            self.logger.info(f"📡 AI Runner response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"✅ AI summary generated using {result.get('model_used', 'unknown')}")
                return {
                    'summary': result['summary'],
                    'model_used': result['model_used'],
                    'generation_time_ms': result['generation_time_ms'],
                    'error': result.get('error')
                }
            else:
                error_msg = f"AI Runner returned status {response.status_code}: {response.text}"
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

    # === PHASE 1: QUERY INTELLIGENCE METHODS ===

    def enhance_query(self, query: str) -> Dict:
        """Enhance query with AI intelligence"""
        self.logger.info(f"🔍 Enhancing query: '{query}'")
        
        try:
            response = requests.post(
                f"{self.ai_runner_url}/enhance-query",
                json={"query": query},
                timeout=self.fast_timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"✅ Query enhanced with {len(result.get('expansions', []))} expansions")
                return result
            else:
                self.logger.warning(f"Query enhancement failed: {response.status_code}")
                return self._fallback_query_enhancement(query)
                
        except Exception as e:
            self.logger.warning(f"Query enhancement error: {e}")
            return self._fallback_query_enhancement(query)

    def classify_intent(self, query: str) -> Dict:
        """Classify search intent"""
        self.logger.info(f"🎯 Classifying intent for: '{query}'")
        
        try:
            response = requests.post(
                f"{self.ai_runner_url}/classify-intent",
                json={"query": query},
                timeout=self.fast_timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"✅ Intent classified: {result.get('primary_intent', 'unknown')}")
                return result
            else:
                self.logger.warning(f"Intent classification failed: {response.status_code}")
                return self._fallback_intent_classification(query)
                
        except Exception as e:
            self.logger.warning(f"Intent classification error: {e}")
            return self._fallback_intent_classification(query)

    def extract_entities(self, query: str) -> Dict:
        """Extract entities from query"""
        self.logger.info(f"🏷️ Extracting entities from: '{query}'")
        
        try:
            response = requests.post(
                f"{self.ai_runner_url}/extract-entities",
                json={"query": query},
                timeout=self.fast_timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"✅ Extracted {result.get('entity_count', 0)} entities")
                return result
            else:
                self.logger.warning(f"Entity extraction failed: {response.status_code}")
                return self._fallback_entity_extraction(query)
                
        except Exception as e:
            self.logger.warning(f"Entity extraction error: {e}")
            return self._fallback_entity_extraction(query)

    # === PHASE 2: CONTENT ANALYSIS METHODS ===

    def analyze_content(self, results: List[Dict]) -> Dict:
        """Analyze content of search results"""
        self.logger.info(f"📊 Analyzing content for {len(results)} results")
        
        try:
            response = requests.post(
                f"{self.ai_runner_url}/analyze-content",
                json={"results": results},
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"✅ Content analysis completed")
                return result
            else:
                self.logger.warning(f"Content analysis failed: {response.status_code}")
                return self._fallback_content_analysis(results)
                
        except Exception as e:
            self.logger.warning(f"Content analysis error: {e}")
            return self._fallback_content_analysis(results)

    def score_quality(self, content: str, title: str = "", domain: str = "") -> Dict:
        """Score content quality"""
        self.logger.info(f"⭐ Scoring quality for: '{title[:30]}'")
        
        try:
            response = requests.post(
                f"{self.ai_runner_url}/score-quality",
                json={"content": content, "title": title, "domain": domain},
                timeout=self.fast_timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"✅ Quality scored: {result.get('overall_score', 0):.3f}")
                return result
            else:
                self.logger.warning(f"Quality scoring failed: {response.status_code}")
                return self._fallback_quality_scoring()
                
        except Exception as e:
            self.logger.warning(f"Quality scoring error: {e}")
            return self._fallback_quality_scoring()

    def rerank_results(self, results: List[Dict], query: str) -> Dict:
        """Rerank results based on AI analysis"""
        self.logger.info(f"📈 Reranking {len(results)} results for query: '{query}'")
        
        try:
            response = requests.post(
                f"{self.ai_runner_url}/rerank-results",
                json={"results": results, "query": query},
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"✅ Results reranked")
                return result
            else:
                self.logger.warning(f"Result reranking failed: {response.status_code}")
                return self._fallback_reranking(results)
                
        except Exception as e:
            self.logger.warning(f"Result reranking error: {e}")
            return self._fallback_reranking(results)

    def generate_insights(self, query: str, results: List[Dict]) -> Dict:
        """Generate comprehensive insights"""
        self.logger.info(f"🧠 Generating comprehensive insights for: '{query}' with {len(results)} results")
        
        try:
            response = requests.post(
                f"{self.ai_runner_url}/generate-insights",
                json={"query": query, "results": results},
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"✅ Comprehensive insights generated")
                return result
            else:
                self.logger.warning(f"Insights generation failed: {response.status_code}")
                return self._fallback_insights(query, results)
                
        except Exception as e:
            self.logger.warning(f"Insights generation error: {e}")
            return self._fallback_insights(query, results)

    # === FALLBACK METHODS ===

    def _fallback_query_enhancement(self, query: str) -> Dict:
        """Fallback for query enhancement"""
        return {
            "original_query": query,
            "enhanced_query": query,
            "expansions": [],
            "suggestions": [],
            "corrections": [],
            "entities": {},
            "confidence": 0.0,
            "processing_time_ms": 0,
            "error": "AI enhancement unavailable"
        }

    def _fallback_intent_classification(self, query: str) -> Dict:
        """Fallback for intent classification"""
        return {
            "query": query,
            "primary_intent": "general",
            "confidence": 0.0,
            "all_intents": {"general": 0.0},
            "suggested_filters": [],
            "processing_time_ms": 0,
            "error": "AI classification unavailable"
        }

    def _fallback_entity_extraction(self, query: str) -> Dict:
        """Fallback for entity extraction"""
        return {
            "query": query,
            "entities": {},
            "entity_count": 0,
            "processing_time_ms": 0,
            "error": "AI extraction unavailable"
        }

    def _fallback_content_analysis(self, results: List[Dict]) -> Dict:
        """Fallback for content analysis"""
        return {
            "total_results": len(results),
            "quality_distribution": {"high": 0, "medium": 0, "low": len(results)},
            "content_types": {},
            "domain_analysis": {},
            "insights": ["AI analysis unavailable"],
            "processing_time_ms": 0,
            "error": "AI analysis unavailable"
        }

    def _fallback_quality_scoring(self) -> Dict:
        """Fallback for quality scoring"""
        return {
            "overall_score": 0.5,
            "factor_scores": {},
            "quality_tier": "medium",
            "domain_boost": 0.0,
            "processing_time_ms": 0,
            "error": "AI scoring unavailable"
        }

    def _fallback_reranking(self, results: List[Dict]) -> Dict:
        """Fallback for result reranking"""
        return {
            "reranked_results": results,
            "ranking_factors": {"results_reordered": 0},
            "processing_time_ms": 0,
            "error": "AI reranking unavailable"
        }

    def _fallback_insights(self, query: str, results: List[Dict]) -> Dict:
        """Fallback for comprehensive insights"""
        return {
            "query_analysis": {"intent": "general", "entities": []},
            "content_insights": ["AI insights unavailable"],
            "quality_overview": {"average_score": 0.5},
            "content_types": {},
            "authority_signals": {},
            "recommendations": ["Consider refining your search query"],
            "processing_time_ms": 0,
            "error": "AI insights unavailable"
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

    def batch_ai_operations(self, operations: List[Dict]) -> Dict:
        """Execute multiple AI operations in a single batch request for optimization"""
        self.logger.info(f"🚀 Executing batch AI operations: {len(operations)} operations")
        
        try:
            # Prepare batch request
            batch_request = {
                "operations": [
                    {"type": op["type"], "data": op["data"]} 
                    for op in operations
                ]
            }
            
            response = requests.post(
                f"{self.ai_runner_url}/batch-operations",
                json=batch_request,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"✅ Batch operations completed: {result.get('operations_count', 0)} ops in {result.get('total_processing_time_ms', 0)}ms")
                return result
            else:
                self.logger.warning(f"Batch operations failed: {response.status_code}")
                return self._fallback_batch_operations(operations)
                
        except Exception as e:
            self.logger.warning(f"Batch operations error: {e}")
            return self._fallback_batch_operations(operations)

    def _fallback_batch_operations(self, operations: List[Dict]) -> Dict:
        """Fallback for batch operations - execute individually"""
        self.logger.info("📦 Falling back to individual operations")
        
        results = {}
        individual_times = {}
        start_time = time.time()
        
        for op in operations:
            op_start = time.time()
            
            try:
                if op["type"] == "enhance_query":
                    result = self.enhance_query(op["data"].get("query", ""))
                elif op["type"] == "classify_intent":
                    result = self.classify_intent(op["data"].get("query", ""))
                elif op["type"] == "extract_entities":
                    result = self.extract_entities(op["data"].get("query", ""))
                elif op["type"] == "analyze_content":
                    result = self.analyze_content(op["data"].get("results", []))
                elif op["type"] == "score_quality":
                    result = self.score_quality(
                        op["data"].get("content", ""),
                        op["data"].get("title", ""),
                        op["data"].get("domain", "")
                    )
                elif op["type"] == "rerank_results":
                    result = self.rerank_results(
                        op["data"].get("results", []),
                        op["data"].get("query", "")
                    )
                elif op["type"] == "generate_insights":
                    result = self.generate_insights(
                        op["data"].get("query", ""),
                        op["data"].get("results", [])
                    )
                else:
                    result = {"error": f"Unknown operation type: {op['type']}"}
                
                results[op["type"]] = result
                individual_times[op["type"]] = round((time.time() - op_start) * 1000, 2)
                
            except Exception as e:
                results[op["type"]] = {"error": str(e)}
                individual_times[op["type"]] = round((time.time() - op_start) * 1000, 2)
        
        return {
            "results": results,
            "total_processing_time_ms": round((time.time() - start_time) * 1000, 2),
            "operations_count": len(operations),
            "individual_times": individual_times,
            "fallback_used": True
        }
