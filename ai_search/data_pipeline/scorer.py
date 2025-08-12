"""
Content Scorer - Quality and Domain Scoring

Provides comprehensive scoring mechanisms for content quality,
domain authority, and content categorization to improve search relevance.
"""

import re
import logging
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class DomainRanker:
    """Simple domain ranking based on predefined scores and TLD patterns."""
    
    def __init__(self):
        self.domain_scores = {
            # High authority domains
            'wikipedia.org': 0.9,
            'github.com': 0.85,
            'stackoverflow.com': 0.8,
            'arxiv.org': 0.85,
            'nature.com': 0.9,
            'science.org': 0.9,
            'pubmed.ncbi.nlm.nih.gov': 0.85,
            
            # Educational domains
            '.edu': 0.8,
            '.ac.uk': 0.8,
            
            # Government domains
            '.gov': 0.75,
            '.mil': 0.7,
            
            # News domains
            'reuters.com': 0.8,
            'bbc.com': 0.8,
            'cnn.com': 0.7,
            'npr.org': 0.75,
            
            # Tech domains
            'techcrunch.com': 0.7,
            'arstechnica.com': 0.75,
            'wired.com': 0.7,
            
            # Default scores by TLD
            '.org': 0.6,
            '.com': 0.5,
            '.net': 0.45,
            '.info': 0.4,
            '.biz': 0.35
        }
    
    def get_domain_score(self, url: str) -> float:
        """Get domain score for a URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Check exact domain matches first
            if domain in self.domain_scores:
                return self.domain_scores[domain]
            
            # Check TLD patterns
            for pattern, score in self.domain_scores.items():
                if pattern.startswith('.') and domain.endswith(pattern):
                    return score
            
            # Default score for unknown domains
            return 0.3
            
        except Exception as e:
            logger.warning(f"Could not parse domain from URL {url}: {e}")
            return 0.3


class ContentScorer:
    """Provides content quality scoring and categorization."""
    
    def __init__(self):
        self.domain_ranker = DomainRanker()

class ContentScorer:
    """Advanced content scoring system for search optimization."""
    
    def __init__(self):
        self.domain_ranker = DomainRanker()
        
        # Educational content indicators
        self.educational_indicators = {
            'strong': ['tutorial', 'guide', 'documentation', 'manual', 'reference', 'api', 'how-to'],
            'medium': ['example', 'demo', 'introduction', 'overview', 'basics', 'fundamentals'],
            'weak': ['blog', 'news', 'announcement', 'release']
        }
        
        # Quality indicators
        self.quality_indicators = {
            'positive': ['detailed', 'comprehensive', 'complete', 'thorough', 'in-depth'],
            'negative': ['broken', 'outdated', 'deprecated', 'old', 'legacy']
        }
    
    def calculate_domain_score(self, url: str) -> float:
        """Calculate domain authority score."""
        try:
            return self.domain_ranker.get_domain_score(url)
        except Exception as e:
            logger.warning(f"Domain scoring failed for {url}: {e}")
            return 1.0
    
    def calculate_content_quality_score(self, content: str, metadata: Dict[str, Any], 
                                      content_metrics: Dict[str, Any]) -> float:
        """Calculate comprehensive content quality score."""
        if not content:
            return 0.1
        
        weights = {
        'length': 0.3,
        'structure': 0.2,
        'content_type': 0.15,
        'language': 0.15,
        'metadata': 0.1,
        'technical': 0.1
        }
        
        
        # Length-based scoring
        word_count = content_metrics.get('word_count', 0)
        scores = {
        'length': self._calculate_length_score(word_count),
        'structure': self._calculate_structure_score(content_metrics),
        'content_type': self._calculate_content_type_score(content, metadata),
        'language': self._calculate_language_quality_score(content),
        'metadata': self._calculate_metadata_score(metadata),
        'technical': self._calculate_technical_content_bonus(content)
        
        }
        return sum(weights[k] * scores[k] for k in weights)
       
            
    def _calculate_length_score(self, word_count: int) -> float:
        """Score based on content length - ultra quality standards."""
        if word_count < 30:
            return 0.05  # Extremely poor for tiny fragments
        elif word_count < 50:
            return 0.15  # Very poor score for tiny content
        elif word_count < 75:
            return 0.4   # Poor for content below our minimum
        elif word_count < 150:
            return 0.8   # Acceptable for moderate content
        elif word_count < 300:
            return 1.3   # Excellent score for substantial content
        elif word_count <= 1000:
            return 1.5   # Outstanding score for comprehensive content
        elif word_count <= 3000:
            return 1.4   # Still excellent for long content
        else:
            return 1.2   # Good but slightly penalize extremely long content
           
    def _calculate_structure_score(self, content_metrics: Dict[str, Any]) -> float:
        """Score based on content structure indicators."""
        score = 1.0
        
        # Bonus for code blocks (technical content)
        if content_metrics.get('has_code_blocks', False):
            score *= 1.2
        
        # Bonus for lists (well-structured content)
        if content_metrics.get('has_lists', False):
            score *= 1.1
        
        # Sentence length analysis
        avg_sentence_length = content_metrics.get('avg_sentence_length', 0)
        if 10 <= avg_sentence_length <= 25:  # Good readability range
            score *= 1.1
        
        return score
    
    def _calculate_content_type_score(self, content: str, metadata: Dict[str, Any]) -> float:
        """Score based on detected content type and educational value - ultra quality standards."""
        content_lower = content.lower()
        title_lower = (metadata.get('title', '') or '').lower()
        
        score = 1.0
        
        # Educational content indicators
        for strength, indicators in self.educational_indicators.items():
            for indicator in indicators:
                if indicator in content_lower or indicator in title_lower:
                    if strength == 'strong':
                        score *= 1.4   # Increased bonus for strong educational indicators
                    elif strength == 'medium':
                        score *= 1.25  # Increased bonus for medium indicators
                    else:  # weak
                        score *= 1.1   # Increased bonus for weak indicators
                    break  # Only apply bonus once per strength level
        
        # Quality indicators
        positive_count = sum(1 for word in self.quality_indicators['positive'] 
                           if word in content_lower)
        negative_count = sum(1 for word in self.quality_indicators['negative'] 
                           if word in content_lower)
        
        score *= (1 + positive_count * 0.08)  # Better bonus for quality indicators
        score *= (1 - negative_count * 0.15)  # Stronger penalty for negative indicators
        
        return max(score, 0.1)  # Ensure minimum score
    
    def _calculate_language_quality_score(self, content: str) -> float:
        """Score based on language quality indicators."""
        if not content:
            return 0.1
        
        score = 1.0
        
        # Capitalization ratio (proper nouns, titles, etc.)
        cap_ratio = sum(1 for c in content if c.isupper()) / len(content) if content else 0
        if 0.02 <= cap_ratio <= 0.08:  # Good range for proper capitalization
            score *= 1.1
        elif cap_ratio > 0.15:  # Too much capitalization (spam-like)
            score *= 0.8
        
        # Punctuation analysis
        punct_ratio = sum(1 for c in content if c in '.,!?;:') / len(content) if content else 0
        if 0.03 <= punct_ratio <= 0.12:  # Good punctuation usage
            score *= 1.05
        
        # Word variety (lexical diversity)
        words = content.lower().split()
        if words:
            unique_words = set(words)
            diversity_ratio = len(unique_words) / len(words)
            if diversity_ratio > 0.4:  # Good vocabulary diversity
                score *= 1.1
        
        return score
    
    def _calculate_metadata_score(self, metadata: Dict[str, Any]) -> float:
        """Score based on metadata completeness and quality."""
        score = 1.0
        
        # Title quality
        title = metadata.get('title', '')
        if title:
            if 10 <= len(title) <= 120:  # Good title length
                score *= 1.1
            if any(word in title.lower() for word in ['how', 'guide', 'tutorial', 'api']):
                score *= 1.05
        
        # Description quality
        description = metadata.get('description', '')
        if description and len(description) > 50:
            score *= 1.05
        
        # Author information
        if metadata.get('author'):
            score *= 1.02
        
        # Date information (recent content bonus)
        if metadata.get('date'):
            score *= 1.02
        
        return score
    
    def _calculate_technical_content_bonus(self, content: str) -> float:
        """Bonus scoring for technical/programming content - ultra quality standards."""
        content_lower = content.lower()
        score = 1.0
        
        # Programming language indicators
        prog_languages = [
            'python', 'javascript', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'swift',
            'kotlin', 'typescript', 'scala', 'haskell', 'clojure', 'erlang', 'elixir'
        ]
        
        lang_mentions = sum(1 for lang in prog_languages if lang in content_lower)
        if lang_mentions > 0:
            score *= (1 + lang_mentions * 0.05)  # Better bonus per language mentioned
        
        # Technical frameworks and tools
        tech_terms = [
            'api', 'rest', 'graphql', 'database', 'sql', 'nosql', 'mongodb', 'redis',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'react', 'vue', 'angular',
            'node.js', 'express', 'django', 'flask', 'spring', 'laravel', 'algorithm',
            'optimization', 'performance', 'architecture', 'design', 'pattern', 'framework'
        ]
        
        tech_mentions = sum(1 for term in tech_terms if term in content_lower)
        if tech_mentions > 0:
            score *= (1 + tech_mentions * 0.03)  # Better bonus per tech term
        
        # Advanced programming concepts
        advanced_concepts = [
            'decorator', 'metaclass', 'coroutine', 'async', 'await', 'closure', 'lambda',
            'generator', 'iterator', 'inheritance', 'polymorphism', 'encapsulation',
            'abstraction', 'interface', 'middleware', 'microservice', 'testing', 'unittest'
        ]
        
        concept_mentions = sum(1 for concept in advanced_concepts if concept in content_lower)
        if concept_mentions > 0:
            score *= (1 + concept_mentions * 0.04)  # Significant bonus for advanced concepts
        
        # Code patterns
        if '```' in content or '<code>' in content:
            score *= 1.25  # Excellent bonus for code examples
        
        if content.count('def ') > 0 or content.count('function ') > 0:
            score *= 1.15  # Function definitions
        
        # Class definitions and object-oriented concepts
        if 'class ' in content_lower:
            score *= 1.1
        
        return min(score, 2.5)  # Higher cap for technical bonus
    
    def calculate_freshness_score(self, metadata: Dict[str, Any]) -> float:
        """Calculate content freshness score based on publication date."""
        # This could be enhanced with actual date parsing
        # For now, return neutral score
        return 1.0
    
    def calculate_engagement_score(self, content_metrics: Dict[str, Any]) -> float:
        """Calculate potential engagement score based on content characteristics."""
        score = 1.0
        
        # Reading time sweet spot (3-8 minutes)
        reading_time = content_metrics.get('reading_time_minutes', 0)
        if 3 <= reading_time <= 8:
            score *= 1.2
        elif reading_time > 15:
            score *= 0.9  # Penalty for very long reads
        
        return score
    
    def get_content_categories(self, content: str, metadata: Dict[str, Any]) -> list:
        """Categorize content for better search filtering."""
        categories = []
        content_lower = content.lower()
        title_lower = (metadata.get('title', '') or '').lower()
        
        # Technical categories
        if any(term in content_lower for term in ['api', 'code', 'function', 'class', 'method']):
            categories.append('technical')
        
        # Educational categories
        if any(term in content_lower + title_lower for term in ['tutorial', 'guide', 'how-to']):
            categories.append('educational')
        
        # Documentation
        if any(term in content_lower + title_lower for term in ['documentation', 'docs', 'reference']):
            categories.append('documentation')
        
        # Q&A content
        if any(term in content_lower for term in ['question', 'answer', 'ask', 'solve']):
            categories.append('qa')
        
        # Blog/article
        if any(term in content_lower + title_lower for term in ['blog', 'article', 'post']):
            categories.append('blog')
        
        return categories if categories else ['general']
