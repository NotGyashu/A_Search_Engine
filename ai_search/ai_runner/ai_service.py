"""AI Service for AI Runner Microservice
Handles all AI-powered summarization with Google Gemini and other models
"""

import time
import re
import hashlib
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

class AIService:
    """AI-powered summarization service with multiple model support and caching"""
    
    def __init__(self):
        self.logger = logging.getLogger("ai_runner.ai_service")
        self.available_models = []
        self.summary_cache = {}  # Simple in-memory cache
        self.cache_ttl = 3600  # Cache TTL in seconds (1 hour)
        self._check_available_models()
        print("in ai_service.py")
    
    def _get_cache_key(self, query: str, results: List[Dict]) -> str:
        """Generate cache key for query and results"""
        # Create a hash based on query and top result titles
        content = query
        for result in results[:3]:  # Only top 3 for cache key
            content += result.get('title', '') + result.get('domain', '')
        print("getting cache key i ai_service.py")
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get summary from cache if available and not expired"""
        print(f"Checking cache for key: {cache_key[:8]} in ai_service.py...")  # Log first 8 chars for brevity
        if cache_key in self.summary_cache:
            cached_item = self.summary_cache[cache_key]
            if time.time() - cached_item['timestamp'] < self.cache_ttl:
                self.logger.info(f"Cache hit for key: {cache_key[:8]}...")
                return cached_item['result']
            else:
                # Remove expired cache entry
                del self.summary_cache[cache_key]
        return None
    
    def _store_in_cache(self, cache_key: str, result: Dict):
        """Store result in cache"""
        print(f"Storing result in cache for key: in ai_service.py...")
        self.summary_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
        
        # Simple cache cleanup - remove oldest entries if cache gets too large
        if len(self.summary_cache) > 100:
            oldest_key = min(self.summary_cache.keys(), 
                           key=lambda k: self.summary_cache[k]['timestamp'])
            del self.summary_cache[oldest_key]
    
    def _check_available_models(self):
        """Check which AI models are available"""
        self.available_models = []
        print("Checking available AI models in ai_service.py...")
        # Always available - smart template (no dependencies)
        self.available_models.append("smart_template")
        
        # Check Google Gemini
        try:
            import google.generativeai as genai
            if os.getenv("GOOGLE_API_KEY"):
                self.available_models.append("google_gemini")
                self.logger.info("Google Gemini available")
            else:
                self.logger.warning("Google API key not found")
        except ImportError:
            self.logger.info("Google Generative AI not installed")
        
        # Check OpenAI
        try:
            import openai
            if os.getenv("OPENAI_API_KEY"):
                self.available_models.append("openai_gpt")
                self.logger.info("OpenAI GPT available")
        except ImportError:
            self.logger.info("OpenAI not installed")
        
        # Check Transformers
        try:
            import transformers
            self.available_models.append("transformers")
            self.logger.info("Transformers available")
        except ImportError:
            self.logger.info("Transformers not installed")
        
        self.logger.info(f"Available AI models: {self.available_models}")
    
    def generate_summary(self, query: str, results: List[Dict], max_length: int = 300) -> Dict:
        """Generate AI summary of search results with caching"""
        print(f"Generating AI summary for query: '' with {len(results)} results in ai_service.py")
        if not results:
            return {
                'summary': "No results found for your query.",
                'model_used': "none",
                'generation_time_ms': 0,
                'error': None,
                'from_cache': False
            }
        
        # Check cache first
        cache_key = self._get_cache_key(query, results)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            cached_result['from_cache'] = True
            return cached_result
        
        start_time = time.time()
        
        # Try models in preference order
        model_preference = ["google_gemini", "openai_gpt", "transformers", "smart_template"]
            
        for model in model_preference:
            if model in self.available_models:
                try:
                    self.logger.info(f"Attempting summary with {model}")
                    
                    if model == "google_gemini":
                        summary = self._generate_gemini_summary(query, results, max_length)
                    elif model == "openai_gpt":
                        summary = self._generate_openai_summary(query, results, max_length)
                    elif model == "transformers":
                        summary = self._generate_transformers_summary(query, results, max_length)
                    elif model == "smart_template":
                        summary = self._generate_smart_template_summary(query, results, max_length)
                    else:
                        continue
                    
                    generation_time = round((time.time() - start_time) * 1000, 2)
                    
                    result = {
                        'summary': summary,
                        'model_used': model,
                        'generation_time_ms': generation_time,
                        'error': None,
                        'from_cache': False
                    }
                    
                    # Store in cache
                    self._store_in_cache(cache_key, result)
                    
                    return result
                    
                except Exception as e:
                    self.logger.warning(f"Model {model} failed: {e}")
                    continue
        
        # Fallback to smart template
        try:
            summary = self._generate_smart_template_summary(query, results, max_length)
            generation_time = round((time.time() - start_time) * 1000, 2)
            
            result = {
                'summary': summary,
                'model_used': "smart_template_fallback",
                'generation_time_ms': generation_time,
                'error': None,
                'from_cache': False
            }
            
            # Store in cache
            self._store_in_cache(cache_key, result)
            
            return result
        except Exception as e:
            self.logger.error(f"All AI models failed: {e}")
            return {
                'summary': f"Found {len(results)} results for '{query}'. AI summarization unavailable.",
                'model_used': "none",
                'generation_time_ms': round((time.time() - start_time) * 1000, 2),
                'error': str(e),
                'from_cache': False
            }
    
    def _generate_gemini_summary(self, query: str, results: List[Dict], max_length: int) -> str:
        """Generate summary using Google Gemini with optimized prompt and faster model"""
        import google.generativeai as genai
        print("Generating Gemini summary in ai_service.py...")
        # Configure Gemini with optimizations
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # Use faster model variant for better response time
        try:
            # Try the latest fast model first
            model = genai.GenerativeModel(
                'gemini-2.5-flash',  # Fastest experimental model
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Lower temperature for faster, more focused responses
                    max_output_tokens=max_length // 3,  # Limit output tokens for speed
                    candidate_count=1,  # Single candidate for speed
                    top_k=20,  # Limit vocabulary for faster generation
                    top_p=0.8,  # Focus on high-probability tokens
                ),
                # Add safety settings for faster processing
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ]
            )
        except Exception:
            # Fallback to stable model if experimental is unavailable
            model = genai.GenerativeModel(
                'gemini-1.5-flash',  # Stable fallback
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=max_length // 3,
                    candidate_count=1,
                )
            )
        
        # Prepare optimized context (limit to top 3 results for speed)
        context = self._prepare_optimized_context_for_ai(query, results[:3])
        
        # Optimized prompt for faster processing - shorter and more direct
        prompt = f"""Query: "{query}"
Results: {context}
Task: Write a concise {max_length//4}-word summary focusing on the key information that answers the query. Be direct and factual."""
        
        try:
            response = model.generate_content(
                prompt,
                request_options={"timeout": 10}
            )
            
            # Add error handling for empty response
            if not response.text:
                raise ValueError("Gemini returned empty response")
            
            return response.text.strip()
        except Exception as e:
            # If fast model fails, try fallback
            self.logger.warning(f"Gemini 2.5 Flash failed, trying fallback: {e}")
            
            # Fallback to standard model
            fallback_model = genai.GenerativeModel(
                'gemini-1.5-flash',
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=max_length // 4,
                    candidate_count=1,
                )
            )
            
            response = fallback_model.generate_content(
                prompt,
                request_options={"timeout": 8}  # Even shorter timeout for fallback
            )
            return response.text.strip()
    
    def _generate_openai_summary(self, query: str, results: List[Dict], max_length: int) -> str:
        """Generate summary using OpenAI GPT"""
        import openai
        print("Generating OpenAI summary in ai_service.py...")
        # Prepare context
        context = self._prepare_context_for_ai(query, results)
        
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a helpful search assistant. Summarize the search results in {max_length} characters or less. Focus on the most relevant information for the query."
                },
                {
                    "role": "user",
                    "content": f"Query: {query}\n\nSearch Results:\n{context}"
                }
            ],
            max_tokens=max_length // 3,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
    
    def _generate_transformers_summary(self, query: str, results: List[Dict], max_length: int) -> str:
        """Generate summary using Hugging Face Transformers"""
        from transformers import pipeline
        print("Generating Transformers summary in ai_service.py...")
        # Use a lightweight summarization model
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        
        # Prepare context
        context = self._prepare_context_for_ai(query, results)
        
        # Limit input length
        if len(context) > 1000:
            context = context[:1000]
        
        summary = summarizer(context, max_length=max_length//4, min_length=50, do_sample=False)
        return summary[0]['summary_text']
    
    def _generate_smart_template_summary(self, query: str, results: List[Dict], max_length: int) -> str:
        """Generate summary using smart templates (no external dependencies)"""
        if not results:
            return "No results found."
        print("Generating smart template summary in ai_service.py...")
        # Extract key information
        num_results = len(results)
        top_domains = self._extract_top_domains(results)
        result_types = self._categorize_results(results)
        
        # Generate contextual summary
        summary_parts = []
        
        # Opening
        if num_results == 1:
            summary_parts.append(f"Found 1 relevant result for '{query}'.")
        else:
            summary_parts.append(f"Found {num_results} relevant results for '{query}'.")
        
        # Domain information
        if len(top_domains) > 1:
            domain_list = ", ".join(top_domains[:3])
            summary_parts.append(f"Results span multiple sources including {domain_list}.")
        elif top_domains:
            summary_parts.append(f"Results primarily from {top_domains[0]}.")
        
        # Content analysis
        if result_types:
            if 'tutorial' in result_types:
                summary_parts.append("Includes tutorial and guide content.")
            if 'documentation' in result_types:
                summary_parts.append("Features technical documentation.")
            if 'discussion' in result_types:
                summary_parts.append("Contains discussion and community content.")
        
        # Top result highlight
        if results:
            top_result = results[0]
            title = top_result.get('title', '').strip()
            if title:
                summary_parts.append(f"Top result: '{title}'.")
        
        # Combine and truncate
        full_summary = " ".join(summary_parts)
        
        if len(full_summary) > max_length:
            truncated = full_summary[:max_length].rsplit(' ', 1)[0]
            full_summary = truncated + "..."
        
        return full_summary
    
    def _prepare_context_for_ai(self, query: str, results: List[Dict]) -> str:
        """Prepare context from search results for AI processing"""
        context_parts = []
        print(f"Preparing context for AI with query: '{query}' in ai_service.py...")
        for i, result in enumerate(results[:5]):  # Limit to top 5 results
            title = result.get('title', '').strip()
            preview = result.get('content_preview', '').strip()
            domain = result.get('domain', '').strip()
            
            context_parts.append(f"{i+1}. {title}")
            if domain:
                context_parts.append(f"   Source: {domain}")
            if preview:
                context_parts.append(f"   Content: {preview}")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _prepare_optimized_context_for_ai(self, query: str, results: List[Dict]) -> str:
        """Prepare optimized, compact context for faster AI processing"""
        context_parts = []
        print(f"Preparing optimized context for AI with query: '{query}' in ai_service.py...")
        for i, result in enumerate(results[:3]):  # Only top 3 for speed
            title = result.get('title', '').strip()
            preview = result.get('content_preview', '').strip()[:150]  # Truncate preview
            
            # Create compact format
            context_parts.append(f"{i+1}. {title} - {preview}...")
        
        return " | ".join(context_parts)
    
    def _extract_top_domains(self, results: List[Dict]) -> List[str]:
        """Extract top domains from results"""
        domain_counts = {}
        print("Extracting top domains from results in ai_service.py...")
        for result in results:
            domain = result.get('domain', '').strip()
            if domain:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        # Sort by count
        sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)
        return [domain for domain, count in sorted_domains]
    
    def _categorize_results(self, results: List[Dict]) -> List[str]:
        """Categorize results based on content"""
        categories = []
        print("Categorizing results in ai_service.py...")
        for result in results:
            title = result.get('title', '').lower()
            content = result.get('content_preview', '').lower()
            
            combined_text = f"{title} {content}"
            
            if any(word in combined_text for word in ['tutorial', 'guide', 'how to', 'step by step']):
                categories.append('tutorial')
            
            if any(word in combined_text for word in ['documentation', 'api', 'reference', 'manual']):
                categories.append('documentation')
            
            if any(word in combined_text for word in ['discussion', 'forum', 'community', 'comment']):
                categories.append('discussion')
        
        return list(set(categories))
    
    def health_check(self) -> Dict:
        """Check AI service health"""
        try:
            # Test with a simple summarization
            test_results = [
                {
                    'title': 'Test Result',
                    'content_preview': 'This is a test result for health check.',
                    'domain': 'test.com'
                }
            ]
            
            summary_result = self.generate_summary("test query", test_results)
            
            return {
                'status': 'healthy',
                'available_models': self.available_models,
                'test_summary_working': summary_result.get('error') is None,
                'primary_model': self.available_models[0] if self.available_models else "none"
            }
            
        except Exception as e:
            self.logger.error(f"AI health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'available_models': self.available_models
            }