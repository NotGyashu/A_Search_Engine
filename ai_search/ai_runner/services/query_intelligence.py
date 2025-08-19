"""
Query Intelligence Service
Handles query enhancement, intent detection, and entity extraction
"""

import re
import time
from typing import Dict, List, Optional, Tuple
import logging
from collections import Counter

class QueryIntelligenceService:
    """Service for intelligent query processing and enhancement"""
    
    def __init__(self):
        self.logger = logging.getLogger("ai_runner.query_intelligence")
        self.cache = {}  # Simple cache for query enhancements
        self.cache_ttl = 1800  # 30 minutes
        
        # Common query expansion patterns
        self.expansion_patterns = {
            'programming': {
                'python': ['python', 'python3', 'py', 'python programming'],
                'javascript': ['javascript', 'js', 'ecmascript', 'node.js', 'nodejs'],
                'react': ['react', 'reactjs', 'react.js', 'facebook react'],
                'vue': ['vue', 'vuejs', 'vue.js'],
                'angular': ['angular', 'angularjs', 'angular.js'],
                'machine learning': ['machine learning', 'ML', 'artificial intelligence', 'AI', 'deep learning'],
                'neural networks': ['neural networks', 'neural nets', 'deep learning', 'CNN', 'RNN'],
                'api': ['api', 'rest api', 'restful', 'web service', 'endpoint'],
                'database': ['database', 'db', 'sql', 'nosql', 'data storage'],
                'docker': ['docker', 'containerization', 'containers'],
                'kubernetes': ['kubernetes', 'k8s', 'container orchestration'],
                'git': ['git', 'version control', 'github', 'gitlab'],
                'testing': ['testing', 'unit tests', 'integration tests', 'TDD', 'test-driven'],
                'debugging': ['debugging', 'troubleshooting', 'error handling', 'bug fixing']
            },
            'content_types': {
                'tutorial': ['tutorial', 'guide', 'how to', 'step by step', 'walkthrough'],
                'documentation': ['documentation', 'docs', 'reference', 'manual', 'API docs'],
                'example': ['example', 'sample', 'demo', 'code example', 'snippet'],
                'troubleshooting': ['troubleshooting', 'error', 'fix', 'problem', 'issue', 'debug'],
                'best practices': ['best practices', 'patterns', 'conventions', 'standards']
            }
        }
        
        # Intent patterns
        self.intent_patterns = {
            'tutorial': [
                r'how\s+to\s+',
                r'tutorial\s+',
                r'guide\s+',
                r'step\s+by\s+step',
                r'learn\s+',
                r'getting\s+started',
                r'beginners?\s+',
                r'introduction\s+to'
            ],
            'troubleshooting': [
                r'error\s+',
                r'fix\s+',
                r'problem\s+',
                r'issue\s+',
                r'debug\s+',
                r'solve\s+',
                r'troubleshoot',
                r'not\s+working',
                r'broken\s+',
                r'failed\s+'
            ],
            'reference': [
                r'documentation\s+',
                r'reference\s+',
                r'api\s+',
                r'docs\s+',
                r'manual\s+',
                r'specification'
            ],
            'comparison': [
                r'vs\s+',
                r'versus\s+',
                r'compare\s+',
                r'difference\s+between',
                r'better\s+than',
                r'alternatives?\s+to'
            ],
            'example': [
                r'example\s+',
                r'sample\s+',
                r'demo\s+',
                r'code\s+example',
                r'snippet\s+'
            ]
        }
        
    def enhance_query(self, query: str) -> Dict:
        """
        Enhance query with expansions and suggestions
        
        Args:
            query: Original search query
            
        Returns:
            Dict with enhanced query and metadata
        """
        start_time = time.time()
        
        # Check cache
        cache_key = f"enhance_{query.lower()}"
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            if time.time() - cached_item['timestamp'] < self.cache_ttl:
                self.logger.info(f"Cache hit for query enhancement: {query[:30]}")
                return cached_item['result']
        
        try:
            original_query = query.strip()
            enhanced_query = original_query
            suggestions = []
            expansions = []
            
            # Detect and expand technical terms
            technical_expansions = self._expand_technical_terms(original_query)
            if technical_expansions:
                expansions.extend(technical_expansions)
                enhanced_query = self._build_enhanced_query(original_query, technical_expansions)
            
            # Generate query suggestions
            suggestions = self._generate_suggestions(original_query)
            
            # Detect spelling corrections
            corrections = self._detect_spelling_issues(original_query)
            
            # Extract key entities
            entities = self._extract_query_entities(original_query)
            
            processing_time = round((time.time() - start_time) * 1000, 2)
            
            result = {
                'original_query': original_query,
                'enhanced_query': enhanced_query,
                'expansions': expansions,
                'suggestions': suggestions,
                'corrections': corrections,
                'entities': entities,
                'confidence': self._calculate_enhancement_confidence(expansions, corrections),
                'processing_time_ms': processing_time
            }
            
            # Cache the result
            self.cache[cache_key] = {
                'result': result,
                'timestamp': time.time()
            }
            
            self.logger.info(f"Query enhanced: '{original_query}' -> found {len(expansions)} expansions")
            return result
            
        except Exception as e:
            self.logger.error(f"Query enhancement failed: {e}")
            return {
                'original_query': query,
                'enhanced_query': query,
                'expansions': [],
                'suggestions': [],
                'corrections': [],
                'entities': {},
                'confidence': 0.0,
                'processing_time_ms': round((time.time() - start_time) * 1000, 2),
                'error': str(e)
            }
    
    def classify_intent(self, query: str) -> Dict:
        """
        Classify the intent of a search query
        
        Args:
            query: Search query to classify
            
        Returns:
            Dict with intent classification and confidence
        """
        start_time = time.time()
        
        try:
            query_lower = query.lower()
            intent_scores = {}
            
            # Check each intent pattern
            for intent, patterns in self.intent_patterns.items():
                score = 0
                matched_patterns = []
                
                for pattern in patterns:
                    matches = re.findall(pattern, query_lower)
                    if matches:
                        score += len(matches)
                        matched_patterns.append(pattern)
                
                if score > 0:
                    intent_scores[intent] = {
                        'score': score,
                        'patterns': matched_patterns
                    }
            
            # Determine primary intent
            if intent_scores:
                primary_intent = max(intent_scores.keys(), key=lambda x: intent_scores[x]['score'])
                confidence = min(intent_scores[primary_intent]['score'] / 3.0, 1.0)  # Normalize to 0-1
            else:
                primary_intent = 'general'
                confidence = 0.5  # Default confidence for general queries
            
            # Generate suggested filters based on intent
            suggested_filters = self._generate_intent_filters(primary_intent, query_lower)
            
            processing_time = round((time.time() - start_time) * 1000, 2)
            
            result = {
                'query': query,
                'primary_intent': primary_intent,
                'confidence': round(confidence, 3),
                'all_intents': intent_scores,
                'suggested_filters': suggested_filters,
                'processing_time_ms': processing_time
            }
            
            self.logger.info(f"Intent classified: '{query[:30]}' -> {primary_intent} ({confidence:.2f})")
            return result
            
        except Exception as e:
            self.logger.error(f"Intent classification failed: {e}")
            return {
                'query': query,
                'primary_intent': 'general',
                'confidence': 0.0,
                'all_intents': {},
                'suggested_filters': [],
                'processing_time_ms': round((time.time() - start_time) * 1000, 2),
                'error': str(e)
            }
    
    def extract_entities(self, query: str) -> Dict:
        """
        Extract entities from query (technologies, topics, levels, etc.)
        
        Args:
            query: Search query to analyze
            
        Returns:
            Dict with extracted entities
        """
        start_time = time.time()
        
        try:
            query_lower = query.lower()
            entities = {
                'technologies': [],
                'topics': [],
                'levels': [],
                'content_types': [],
                'languages': [],
                'frameworks': []
            }
            
            # Technology detection
            tech_patterns = {
                'python': ['python', 'py', 'python3'],
                'javascript': ['javascript', 'js', 'node', 'nodejs'],
                'java': ['java', 'jvm'],
                'react': ['react', 'reactjs'],
                'vue': ['vue', 'vuejs'],
                'angular': ['angular', 'angularjs'],
                'docker': ['docker', 'container'],
                'kubernetes': ['kubernetes', 'k8s'],
                'aws': ['aws', 'amazon web services'],
                'azure': ['azure', 'microsoft azure'],
                'gcp': ['gcp', 'google cloud'],
                'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis'],
                'machine_learning': ['ml', 'ai', 'machine learning', 'neural network', 'tensorflow', 'pytorch']
            }
            
            for tech, patterns in tech_patterns.items():
                for pattern in patterns:
                    if pattern in query_lower:
                        entities['technologies'].append(tech)
                        break
            
            # Level detection
            level_patterns = {
                'beginner': ['beginner', 'basic', 'intro', 'getting started', 'fundamentals'],
                'intermediate': ['intermediate', 'advanced basics'],
                'advanced': ['advanced', 'expert', 'professional', 'production']
            }
            
            for level, patterns in level_patterns.items():
                for pattern in patterns:
                    if pattern in query_lower:
                        entities['levels'].append(level)
                        break
            
            # Content type detection
            content_patterns = {
                'tutorial': ['tutorial', 'guide', 'how to', 'walkthrough'],
                'documentation': ['docs', 'documentation', 'reference', 'manual'],
                'example': ['example', 'sample', 'demo'],
                'course': ['course', 'lesson', 'training'],
                'book': ['book', 'ebook', 'pdf'],
                'video': ['video', 'youtube', 'watch']
            }
            
            for content_type, patterns in content_patterns.items():
                for pattern in patterns:
                    if pattern in query_lower:
                        entities['content_types'].append(content_type)
                        break
            
            # Remove duplicates and empty lists
            for key in entities:
                entities[key] = list(set(entities[key]))
                if not entities[key]:
                    entities[key] = []
            
            processing_time = round((time.time() - start_time) * 1000, 2)
            
            result = {
                'query': query,
                'entities': entities,
                'entity_count': sum(len(v) for v in entities.values()),
                'processing_time_ms': processing_time
            }
            
            self.logger.info(f"Entities extracted from '{query[:30]}': {result['entity_count']} total")
            return result
            
        except Exception as e:
            self.logger.error(f"Entity extraction failed: {e}")
            return {
                'query': query,
                'entities': {
                    'technologies': [],
                    'topics': [],
                    'levels': [],
                    'content_types': [],
                    'languages': [],
                    'frameworks': []
                },
                'entity_count': 0,
                'processing_time_ms': round((time.time() - start_time) * 1000, 2),
                'error': str(e)
            }
    
    def _expand_technical_terms(self, query: str) -> List[str]:
        """Expand technical terms in the query"""
        query_lower = query.lower()
        expansions = []
        
        for category, terms in self.expansion_patterns.items():
            for term, alternatives in terms.items():
                if term in query_lower:
                    expansions.extend([alt for alt in alternatives if alt != term])
        
        return list(set(expansions))
    
    def _build_enhanced_query(self, original: str, expansions: List[str]) -> str:
        """Build enhanced query with expansions"""
        if not expansions:
            return original
        
        # Simple enhancement: add OR clauses for expansions
        expansion_clause = " OR ".join(f'"{exp}"' for exp in expansions[:3])  # Limit to top 3
        return f"{original} OR ({expansion_clause})"
    
    def _generate_suggestions(self, query: str) -> List[str]:
        """Generate query suggestions"""
        suggestions = []
        query_lower = query.lower()
        
        # Intent-based suggestions
        if any(word in query_lower for word in ['how', 'tutorial', 'guide']):
            suggestions.append(f"{query} for beginners")
            suggestions.append(f"{query} step by step")
        
        if any(word in query_lower for word in ['error', 'fix', 'problem']):
            suggestions.append(f"solve {query}")
            suggestions.append(f"debug {query}")
        
        # Add more specific suggestions based on detected technologies
        for tech in ['python', 'javascript', 'react', 'vue']:
            if tech in query_lower:
                suggestions.append(f"{query} best practices")
                suggestions.append(f"{query} examples")
                break
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def _detect_spelling_issues(self, query: str) -> List[Dict]:
        """Detect common spelling issues in technical queries"""
        corrections = []
        
        # Common technical misspellings
        common_mistakes = {
            'machien': 'machine',
            'javscript': 'javascript',
            'javascirpt': 'javascript',
            'pytohn': 'python',
            'databse': 'database',
            'algoritm': 'algorithm',
            'functon': 'function',
            'funciton': 'function'
        }
        
        words = query.lower().split()
        for word in words:
            if word in common_mistakes:
                corrections.append({
                    'original': word,
                    'suggestion': common_mistakes[word],
                    'confidence': 0.9
                })
        
        return corrections
    
    def _extract_query_entities(self, query: str) -> Dict:
        """Extract basic entities from query"""
        # This is a simplified version - could be enhanced with NLP libraries
        entities = {}
        
        # Extract quoted phrases
        quoted_phrases = re.findall(r'"([^"]*)"', query)
        if quoted_phrases:
            entities['exact_phrases'] = quoted_phrases
        
        # Extract words in ALL CAPS (might be acronyms)
        caps_words = re.findall(r'\b[A-Z]{2,}\b', query)
        if caps_words:
            entities['acronyms'] = caps_words
        
        return entities
    
    def _calculate_enhancement_confidence(self, expansions: List[str], corrections: List[Dict]) -> float:
        """Calculate confidence score for query enhancement"""
        score = 0.5  # Base confidence
        
        if expansions:
            score += min(len(expansions) * 0.1, 0.3)  # Up to 0.3 for expansions
        
        if corrections:
            score += min(len(corrections) * 0.2, 0.2)  # Up to 0.2 for corrections
        
        return min(round(score, 3), 1.0)
    
    def _generate_intent_filters(self, intent: str, query: str) -> List[str]:
        """Generate suggested filters based on detected intent"""
        filters = []
        
        if intent == 'tutorial':
            filters = ['guide', 'tutorial', 'beginner-friendly', 'step-by-step']
        elif intent == 'troubleshooting':
            filters = ['solution', 'fix', 'debugging', 'error-resolution']
        elif intent == 'reference':
            filters = ['documentation', 'api-reference', 'manual', 'specification']
        elif intent == 'comparison':
            filters = ['comparison', 'analysis', 'pros-cons', 'evaluation']
        elif intent == 'example':
            filters = ['code-example', 'sample', 'demo', 'implementation']
        else:
            filters = ['comprehensive', 'detailed', 'explanation']
        
        return filters[:4]  # Limit to 4 filters
    
    def health_check(self) -> Dict:
        """Check service health"""
        try:
            # Test with simple query
            test_result = self.enhance_query("python tutorial")
            
            return {
                'status': 'healthy',
                'cache_size': len(self.cache),
                'test_enhancement_working': 'error' not in test_result,
                'available_patterns': len(self.expansion_patterns),
                'available_intents': len(self.intent_patterns)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
