"""
AI Service - Handle AI-powered summarization and enhancement
Supports multiple AI models with intelligent fallback
"""

import time
import re
from typing import Dict, List, Optional
from pathlib import Path
import sys

# Add common utilities
sys.path.append(str(Path(__file__).parent.parent.parent))
from common.utils import Logger, PerformanceMonitor
from common.config import AI_MODEL_PREFERENCE, OPENAI_MODEL


class AIService:
    """AI-powered summarization and enhancement service"""
    
    def __init__(self):
        self.logger = Logger.setup_logger("backend.ai")
        self.model_preference = AI_MODEL_PREFERENCE.copy()
        self.available_models = []
        
        # Check available models
        self._check_available_models()
    
    def _check_available_models(self):
        """Check which AI models are available"""
        self.available_models = []
        
        # Always available - smart template (no dependencies)
        self.available_models.append("smart_template")
        
        # Check OpenAI
        try:
            import openai
            import os
            if os.getenv("OPENAI_API_KEY"):
                self.available_models.append("openai_gpt")
                self.logger.info("OpenAI GPT models available")
            else:
                self.logger.warning("OpenAI API key not found")
        except ImportError:
            self.logger.info("OpenAI not installed")
        
        # Check Transformers
        try:
            import transformers
            self.available_models.append("transformers")
            self.logger.info("Transformers models available")
        except ImportError:
            self.logger.info("Transformers not installed")
        
        # Check Ollama
        try:
            import requests
            # Simple check - could be improved
            self.available_models.append("ollama")
            self.logger.info("Ollama models potentially available")
        except ImportError:
            self.logger.info("Ollama not available")
        
        self.logger.info(f"Available AI models: {self.available_models}")
    
    def generate_summary(self, query: str, results: List[Dict], max_length: int = 300) -> Dict:
        """Generate AI summary of search results"""
        if not results:
            return {
                'summary': "No results found for your query.",
                'model_used': "none",
                'generation_time_ms': 0,
                'error': None
            }
        
        start_time = time.time()
        
        # Try each available model in preference order
        for model in self.model_preference:
            if model in self.available_models:
                try:
                    self.logger.info(f"Attempting summary with {model}")
                    
                    if model == "smart_template":
                        summary = self._generate_smart_template_summary(query, results, max_length)
                    elif model == "openai_gpt":
                        summary = self._generate_openai_summary(query, results, max_length)
                    elif model == "transformers":
                        summary = self._generate_transformers_summary(query, results, max_length)
                    elif model == "ollama":
                        summary = self._generate_ollama_summary(query, results, max_length)
                    else:
                        continue
                    
                    generation_time = round((time.time() - start_time) * 1000, 2)
                    
                    return {
                        'summary': summary,
                        'model_used': model,
                        'generation_time_ms': generation_time,
                        'error': None
                    }
                    
                except Exception as e:
                    self.logger.warning(f"Model {model} failed: {e}")
                    continue
        
        # Fallback to smart template if all else fails
        try:
            summary = self._generate_smart_template_summary(query, results, max_length)
            generation_time = round((time.time() - start_time) * 1000, 2)
            
            return {
                'summary': summary,
                'model_used': "smart_template_fallback",
                'generation_time_ms': generation_time,
                'error': None
            }
        except Exception as e:
            self.logger.error(f"All AI models failed: {e}")
            return {
                'summary': f"Found {len(results)} results for '{query}'. AI summarization unavailable.",
                'model_used': "none",
                'generation_time_ms': round((time.time() - start_time) * 1000, 2),
                'error': str(e)
            }
    
    def _generate_smart_template_summary(self, query: str, results: List[Dict], max_length: int) -> str:
        """Generate summary using smart templates (no external dependencies)"""
        if not results:
            return "No results found."
        
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
    
    def _generate_openai_summary(self, query: str, results: List[Dict], max_length: int) -> str:
        """Generate summary using OpenAI GPT"""
        import openai
        import os
        
        # Prepare context
        context = self._prepare_context_for_ai(query, results)
        
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
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
            max_tokens=max_length // 3,  # Rough estimate
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
    
    def _generate_transformers_summary(self, query: str, results: List[Dict], max_length: int) -> str:
        """Generate summary using Hugging Face Transformers"""
        from transformers import pipeline
        
        # Use a lightweight summarization model
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        
        # Prepare context
        context = self._prepare_context_for_ai(query, results)
        
        # Limit input length for the model
        if len(context) > 1000:
            context = context[:1000]
        
        summary = summarizer(context, max_length=max_length//4, min_length=50, do_sample=False)
        return summary[0]['summary_text']
    
    def _generate_ollama_summary(self, query: str, results: List[Dict], max_length: int) -> str:
        """Generate summary using Ollama (local LLM)"""
        import requests
        
        # Prepare context
        context = self._prepare_context_for_ai(query, results)
        
        prompt = f"""Based on these search results for "{query}", provide a concise summary:

{context}

Summary:"""
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama2",  # Default model
                "prompt": prompt,
                "stream": False
            }
        )
        
        if response.status_code == 200:
            return response.json()['response'].strip()
        else:
            raise Exception(f"Ollama API error: {response.status_code}")
    
    def _prepare_context_for_ai(self, query: str, results: List[Dict]) -> str:
        """Prepare context from search results for AI processing"""
        context_parts = []
        
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
    
    def _extract_top_domains(self, results: List[Dict]) -> List[str]:
        """Extract top domains from results"""
        domain_counts = {}
        
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
    
    def get_stats(self) -> Dict:
        """Get AI service statistics"""
        return {
            'available_models': self.available_models,
            'model_preference': self.model_preference,
            'default_model': self.model_preference[0] if self.model_preference else "none"
        }
    
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
