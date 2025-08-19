"""
Content Analysis Service
Handles content analysis, quality scoring, and result enhancement
"""

import time
import re
from typing import Dict, List, Optional
from collections import Counter
import logging
import hashlib

class ContentAnalysisService:
    """Service for analyzing and enhancing search result content"""
    
    def __init__(self):
        self.logger = logging.getLogger("ai_runner.content_analysis")
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        
        # Content quality indicators
        self.quality_indicators = {
            'positive': {
                'technical_depth': [
                    'implementation', 'algorithm', 'architecture', 'design pattern',
                    'best practices', 'performance', 'optimization', 'scalability',
                    'security', 'testing', 'documentation', 'code example',
                    'step by step', 'detailed explanation', 'comprehensive'
                ],
                'authority_signals': [
                    'official documentation', 'api reference', 'specification',
                    'white paper', 'research', 'peer reviewed', 'academic',
                    'expert', 'maintainer', 'core team', 'official blog'
                ],
                'freshness': [
                    '2024', '2025', 'latest', 'updated', 'recent',
                    'new version', 'current', 'modern'
                ],
                'engagement': [
                    'comments', 'discussion', 'community', 'forum',
                    'stack overflow', 'github', 'popular', 'trending'
                ]
            },
            'negative': {
                'low_quality': [
                    'spam', 'duplicate', 'placeholder', 'lorem ipsum',
                    'under construction', 'coming soon', 'broken link',
                    'page not found', '404', 'error', 'unavailable'
                ],
                'outdated': [
                    'deprecated', 'legacy', 'old version', 'obsolete',
                    'no longer supported', 'archived', '2020', '2019', '2018'
                ],
                'unreliable': [
                    'unverified', 'rumor', 'speculation', 'personal opinion',
                    'biased', 'advertisement', 'promotional', 'sponsored'
                ]
            }
        }
        
        # Content type patterns
        self.content_type_patterns = {
            'tutorial': [
                r'tutorial', r'guide', r'how\s+to', r'step\s+by\s+step',
                r'walkthrough', r'getting\s+started', r'introduction\s+to'
            ],
            'documentation': [
                r'documentation', r'docs', r'api\s+reference', r'manual',
                r'specification', r'official\s+guide', r'reference'
            ],
            'blog_post': [
                r'blog', r'article', r'post', r'published', r'author',
                r'opinion', r'thoughts', r'experience'
            ],
            'forum_discussion': [
                r'forum', r'discussion', r'thread', r'question',
                r'answer', r'community', r'stack\s+overflow'
            ],
            'code_example': [
                r'example', r'sample', r'demo', r'snippet',
                r'code', r'implementation', r'source'
            ],
            'news': [
                r'news', r'announcement', r'release', r'update',
                r'breaking', r'latest', r'today'
            ],
            'academic': [
                r'paper', r'research', r'study', r'journal',
                r'academic', r'university', r'publication'
            ]
        }
        
    def analyze_content(self, results: List[Dict]) -> Dict:
        """
        Analyze content of search results for quality, type, and insights
        
        Args:
            results: List of search results to analyze
            
        Returns:
            Dict with content analysis insights
        """
        start_time = time.time()
        
        try:
            if not results:
                return self._empty_analysis()
            
            # Generate cache key
            cache_key = self._generate_cache_key(results)
            if cache_key in self.cache:
                cached_item = self.cache[cache_key]
                if time.time() - cached_item['timestamp'] < self.cache_ttl:
                    return cached_item['result']
            
            analysis = {
                'total_results': len(results),
                'quality_distribution': self._analyze_quality_distribution(results),
                'content_types': self._classify_content_types(results),
                'domain_analysis': self._analyze_domains(results),
                'freshness_analysis': self._analyze_freshness(results),
                'topic_clusters': self._extract_topic_clusters(results),
                'authority_signals': self._detect_authority_signals(results),
                'duplicate_detection': self._detect_duplicates(results),
                'processing_time_ms': 0
            }
            
            # Calculate overall insights
            analysis['insights'] = self._generate_insights(analysis)
            analysis['processing_time_ms'] = round((time.time() - start_time) * 1000, 2)
            
            # Cache the result
            self.cache[cache_key] = {
                'result': analysis,
                'timestamp': time.time()
            }
            
            self.logger.info(f"Content analysis completed for {len(results)} results")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Content analysis failed: {e}")
            return self._empty_analysis(error=str(e))
    
    def score_quality(self, content: str, title: str = "", domain: str = "") -> Dict:
        """
        Score the quality of individual content
        
        Args:
            content: Content text to analyze
            title: Title of the content
            domain: Domain of the source
            
        Returns:
            Dict with quality score and factors
        """
        start_time = time.time()
        
        try:
            combined_text = f"{title} {content}".lower()
            
            scores = {
                'technical_depth': self._score_technical_depth(combined_text),
                'authority': self._score_authority(combined_text, domain),
                'freshness': self._score_freshness(combined_text),
                'engagement': self._score_engagement(combined_text),
                'readability': self._score_readability(content),
                'completeness': self._score_completeness(content)
            }
            
            # Calculate weighted overall score
            weights = {
                'technical_depth': 0.25,
                'authority': 0.20,
                'freshness': 0.15,
                'engagement': 0.10,
                'readability': 0.15,
                'completeness': 0.15
            }
            
            overall_score = sum(scores[factor] * weights[factor] for factor in scores)
            
            # Apply domain boost
            domain_boost = self._get_domain_authority_boost(domain)
            overall_score = min(overall_score + domain_boost, 1.0)
            
            result = {
                'overall_score': round(overall_score, 3),
                'factor_scores': scores,
                'quality_tier': self._get_quality_tier(overall_score),
                'domain_boost': domain_boost,
                'processing_time_ms': round((time.time() - start_time) * 1000, 2)
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Quality scoring failed: {e}")
            return {
                'overall_score': 0.5,
                'factor_scores': {},
                'quality_tier': 'unknown',
                'domain_boost': 0.0,
                'processing_time_ms': round((time.time() - start_time) * 1000, 2),
                'error': str(e)
            }
    
    def rerank_results(self, results: List[Dict], query: str) -> Dict:
        """
        Rerank results based on content analysis and query relevance
        
        Args:
            results: Original search results
            query: Search query for relevance scoring
            
        Returns:
            Dict with reranked results and ranking factors
        """
        start_time = time.time()
        
        try:
            if not results:
                return {
                    'reranked_results': [],
                    'ranking_factors': {},
                    'processing_time_ms': 0
                }
            
            # Score each result
            scored_results = []
            for i, result in enumerate(results):
                content = result.get('content_preview', '') or result.get('description', '')
                title = result.get('title', '')
                domain = result.get('domain', '')
                
                # Content quality score
                quality_score = self.score_quality(content, title, domain)
                
                # Query relevance score
                relevance_score = self._calculate_relevance_score(
                    query, title, content
                )
                
                # Position bias (earlier results get slight boost)
                position_bias = max(0, 1 - (i * 0.1))
                
                # Combined ranking score
                combined_score = (
                    quality_score['overall_score'] * 0.4 +
                    relevance_score * 0.5 +
                    position_bias * 0.1
                )
                
                scored_results.append({
                    'result': result,
                    'original_position': i,
                    'quality_score': quality_score['overall_score'],
                    'relevance_score': relevance_score,
                    'position_bias': position_bias,
                    'combined_score': combined_score,
                    'quality_tier': quality_score['quality_tier']
                })
            
            # Sort by combined score
            scored_results.sort(key=lambda x: x['combined_score'], reverse=True)
            
            # Extract reranked results
            reranked = [item['result'] for item in scored_results]
            
            # Calculate ranking changes
            ranking_changes = []
            for i, scored_item in enumerate(scored_results):
                original_pos = scored_item['original_position']
                new_pos = i
                if original_pos != new_pos:
                    ranking_changes.append({
                        'title': scored_item['result'].get('title', 'Unknown'),
                        'original_position': original_pos,
                        'new_position': new_pos,
                        'change': original_pos - new_pos,
                        'reason': f"Quality: {scored_item['quality_tier']}, "
                                f"Score: {scored_item['combined_score']:.3f}"
                    })
            
            result = {
                'reranked_results': reranked,
                'ranking_factors': {
                    'total_results': len(results),
                    'results_reordered': len(ranking_changes),
                    'ranking_changes': ranking_changes[:5],  # Top 5 changes
                    'average_quality_score': round(
                        sum(item['quality_score'] for item in scored_results) / len(scored_results), 3
                    ),
                    'score_distribution': self._get_score_distribution(scored_results)
                },
                'processing_time_ms': round((time.time() - start_time) * 1000, 2)
            }
            
            self.logger.info(f"Reranked {len(results)} results, {len(ranking_changes)} position changes")
            return result
            
        except Exception as e:
            self.logger.error(f"Result reranking failed: {e}")
            return {
                'reranked_results': results,  # Return original order on error
                'ranking_factors': {},
                'processing_time_ms': round((time.time() - start_time) * 1000, 2),
                'error': str(e)
            }
    
    def detect_duplicates(self, results: List[Dict]) -> Dict:
        """
        Detect duplicate or near-duplicate results
        
        Args:
            results: List of results to check for duplicates
            
        Returns:
            Dict with duplicate detection results
        """
        start_time = time.time()
        
        try:
            duplicates = []
            seen_content = {}
            
            for i, result in enumerate(results):
                content = result.get('content_preview', '') or result.get('description', '')
                title = result.get('title', '')
                
                # Create content signature
                signature = self._create_content_signature(content, title)
                
                if signature in seen_content:
                    duplicates.append({
                        'original_index': seen_content[signature],
                        'duplicate_index': i,
                        'original_title': results[seen_content[signature]].get('title', ''),
                        'duplicate_title': title,
                        'similarity_type': 'exact_content'
                    })
                else:
                    seen_content[signature] = i
            
            # Check for near-duplicates (title similarity)
            near_duplicates = self._find_near_duplicates(results)
            
            result = {
                'exact_duplicates': duplicates,
                'near_duplicates': near_duplicates,
                'total_duplicates': len(duplicates) + len(near_duplicates),
                'unique_results': len(results) - len(duplicates),
                'processing_time_ms': round((time.time() - start_time) * 1000, 2)
            }
            
            self.logger.info(f"Duplicate detection: {len(duplicates)} exact, {len(near_duplicates)} near")
            return result
            
        except Exception as e:
            self.logger.error(f"Duplicate detection failed: {e}")
            return {
                'exact_duplicates': [],
                'near_duplicates': [],
                'total_duplicates': 0,
                'unique_results': len(results),
                'processing_time_ms': round((time.time() - start_time) * 1000, 2),
                'error': str(e)
            }
    
    # Helper methods
    
    def _empty_analysis(self, error: str = None) -> Dict:
        """Return empty analysis structure"""
        result = {
            'total_results': 0,
            'quality_distribution': {},
            'content_types': {},
            'domain_analysis': {},
            'freshness_analysis': {},
            'topic_clusters': [],
            'authority_signals': {},
            'duplicate_detection': {},
            'insights': [],
            'processing_time_ms': 0
        }
        if error:
            result['error'] = error
        return result
    
    def _generate_cache_key(self, results: List[Dict]) -> str:
        """Generate cache key for results"""
        content_hash = hashlib.md5()
        for result in results[:5]:  # Use top 5 for cache key
            title = result.get('title', '')
            content = result.get('content_preview', '')[:100]  # First 100 chars
            content_hash.update(f"{title}{content}".encode())
        return content_hash.hexdigest()
    
    def _analyze_quality_distribution(self, results: List[Dict]) -> Dict:
        """Analyze quality distribution across results"""
        quality_scores = []
        for result in results:
            content = result.get('content_preview', '') or result.get('description', '')
            title = result.get('title', '')
            domain = result.get('domain', '')
            
            quality = self.score_quality(content, title, domain)
            quality_scores.append(quality['overall_score'])
        
        if not quality_scores:
            return {}
        
        return {
            'average': round(sum(quality_scores) / len(quality_scores), 3),
            'highest': round(max(quality_scores), 3),
            'lowest': round(min(quality_scores), 3),
            'high_quality_count': len([s for s in quality_scores if s >= 0.8]),
            'medium_quality_count': len([s for s in quality_scores if 0.5 <= s < 0.8]),
            'low_quality_count': len([s for s in quality_scores if s < 0.5])
        }
    
    def _classify_content_types(self, results: List[Dict]) -> Dict:
        """Classify content types of results"""
        type_counts = Counter()
        
        for result in results:
            content = f"{result.get('title', '')} {result.get('content_preview', '')}".lower()
            
            detected_types = []
            for content_type, patterns in self.content_type_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, content):
                        detected_types.append(content_type)
                        break
            
            if not detected_types:
                detected_types = ['general']
            
            for ctype in detected_types:
                type_counts[ctype] += 1
        
        return dict(type_counts)
    
    def _analyze_domains(self, results: List[Dict]) -> Dict:
        """Analyze domain distribution and authority"""
        domain_counts = Counter()
        domain_authority = {}
        
        authority_domains = {
            'github.com': 0.9,
            'stackoverflow.com': 0.95,
            'docs.python.org': 0.98,
            'developer.mozilla.org': 0.95,
            'reactjs.org': 0.9,
            'nodejs.org': 0.9,
            'microsoft.com': 0.85,
            'google.com': 0.85,
            'w3.org': 0.9,
            'ieee.org': 0.95
        }
        
        for result in results:
            domain = result.get('domain', '')
            if domain:
                domain_counts[domain] += 1
                domain_authority[domain] = authority_domains.get(domain, 0.5)
        
        return {
            'domain_distribution': dict(domain_counts.most_common(10)),
            'high_authority_domains': {
                domain: score for domain, score in domain_authority.items() 
                if score >= 0.8
            },
            'total_unique_domains': len(domain_counts)
        }
    
    def _analyze_freshness(self, results: List[Dict]) -> Dict:
        """Analyze content freshness"""
        freshness_indicators = {
            'very_recent': 0,  # 2024-2025
            'recent': 0,       # 2022-2023
            'older': 0,        # 2020-2021
            'outdated': 0      # before 2020
        }
        
        current_year = 2025
        
        for result in results:
            content = f"{result.get('title', '')} {result.get('content_preview', '')}".lower()
            
            # Look for year indicators
            year_matches = re.findall(r'20\d{2}', content)
            if year_matches:
                latest_year = max(int(year) for year in year_matches)
                
                if latest_year >= current_year - 1:
                    freshness_indicators['very_recent'] += 1
                elif latest_year >= current_year - 3:
                    freshness_indicators['recent'] += 1
                elif latest_year >= current_year - 5:
                    freshness_indicators['older'] += 1
                else:
                    freshness_indicators['outdated'] += 1
            
            # Check for freshness keywords
            elif any(word in content for word in ['latest', 'new', 'updated', 'current', '2025']):
                freshness_indicators['very_recent'] += 1
            else:
                freshness_indicators['recent'] += 1  # Default assumption
        
        return freshness_indicators
    
    def _extract_topic_clusters(self, results: List[Dict]) -> List[Dict]:
        """Extract topic clusters from results"""
        # Simple keyword-based clustering
        word_freq = Counter()
        
        for result in results:
            content = f"{result.get('title', '')} {result.get('content_preview', '')}".lower()
            words = re.findall(r'\b[a-zA-Z]{4,}\b', content)  # Words 4+ chars
            word_freq.update(words)
        
        # Get top topics
        top_topics = word_freq.most_common(10)
        
        clusters = []
        for topic, count in top_topics:
            if count >= 2:  # Only topics appearing in 2+ results
                clusters.append({
                    'topic': topic,
                    'frequency': count,
                    'relevance': min(count / len(results), 1.0)
                })
        
        return clusters[:5]  # Top 5 clusters
    
    def _detect_authority_signals(self, results: List[Dict]) -> Dict:
        """Detect authority signals in results"""
        signals = {
            'official_docs': 0,
            'expert_content': 0,
            'community_validated': 0,
            'academic_sources': 0
        }
        
        for result in results:
            content = f"{result.get('title', '')} {result.get('content_preview', '')}".lower()
            domain = result.get('domain', '').lower()
            
            # Official documentation
            if any(term in content or term in domain for term in [
                'official', 'documentation', 'docs', 'api reference'
            ]):
                signals['official_docs'] += 1
            
            # Expert content
            if any(term in content for term in [
                'expert', 'maintainer', 'core team', 'lead developer'
            ]):
                signals['expert_content'] += 1
            
            # Community validated
            if any(term in domain for term in [
                'stackoverflow', 'github', 'reddit'
            ]):
                signals['community_validated'] += 1
            
            # Academic sources
            if any(term in content or term in domain for term in [
                'research', 'academic', 'university', 'paper', 'journal'
            ]):
                signals['academic_sources'] += 1
        
        return signals
    
    def _detect_duplicates(self, results: List[Dict]) -> Dict:
        """Simple duplicate detection"""
        return self.detect_duplicates(results)
    
    def _generate_insights(self, analysis: Dict) -> List[str]:
        """Generate insights from analysis"""
        insights = []
        
        # Quality insights
        quality_dist = analysis.get('quality_distribution', {})
        if quality_dist.get('high_quality_count', 0) > 0:
            insights.append(f"Found {quality_dist['high_quality_count']} high-quality results")
        
        # Content type insights
        content_types = analysis.get('content_types', {})
        if content_types:
            top_type = max(content_types.items(), key=lambda x: x[1])
            insights.append(f"Primarily {top_type[0]} content ({top_type[1]} results)")
        
        # Authority insights
        authority = analysis.get('authority_signals', {})
        if authority.get('official_docs', 0) > 0:
            insights.append(f"Includes {authority['official_docs']} official documentation sources")
        
        # Freshness insights
        freshness = analysis.get('freshness_analysis', {})
        if freshness.get('very_recent', 0) > 0:
            insights.append(f"{freshness['very_recent']} results contain recent/updated content")
        
        return insights[:3]  # Top 3 insights
    
    def _score_technical_depth(self, content: str) -> float:
        """Score technical depth of content"""
        depth_indicators = self.quality_indicators['positive']['technical_depth']
        matches = sum(1 for indicator in depth_indicators if indicator in content)
        return min(matches / 5.0, 1.0)  # Normalize to 0-1
    
    def _score_authority(self, content: str, domain: str) -> float:
        """Score authority of content"""
        authority_indicators = self.quality_indicators['positive']['authority_signals']
        matches = sum(1 for indicator in authority_indicators if indicator in content)
        
        # Domain authority boost
        domain_score = self._get_domain_authority_boost(domain)
        
        content_score = min(matches / 3.0, 1.0)
        return min(content_score + domain_score, 1.0)
    
    def _score_freshness(self, content: str) -> float:
        """Score content freshness"""
        freshness_indicators = self.quality_indicators['positive']['freshness']
        matches = sum(1 for indicator in freshness_indicators if indicator in content)
        return min(matches / 3.0, 1.0)
    
    def _score_engagement(self, content: str) -> float:
        """Score content engagement"""
        engagement_indicators = self.quality_indicators['positive']['engagement']
        matches = sum(1 for indicator in engagement_indicators if indicator in content)
        return min(matches / 2.0, 1.0)
    
    def _score_readability(self, content: str) -> float:
        """Score content readability (simplified)"""
        if not content:
            return 0.0
        
        # Simple readability metrics
        sentences = len(re.split(r'[.!?]+', content))
        words = len(content.split())
        
        if sentences == 0:
            return 0.0
        
        avg_sentence_length = words / sentences
        
        # Prefer moderate sentence length (10-20 words)
        if 10 <= avg_sentence_length <= 20:
            return 1.0
        elif 5 <= avg_sentence_length < 10 or 20 < avg_sentence_length <= 30:
            return 0.7
        else:
            return 0.4
    
    def _score_completeness(self, content: str) -> float:
        """Score content completeness"""
        if not content:
            return 0.0
        
        # Simple completeness indicators
        word_count = len(content.split())
        
        if word_count >= 200:
            return 1.0
        elif word_count >= 100:
            return 0.8
        elif word_count >= 50:
            return 0.6
        else:
            return 0.3
    
    def _get_domain_authority_boost(self, domain: str) -> float:
        """Get authority boost based on domain"""
        authority_domains = {
            'github.com': 0.15,
            'stackoverflow.com': 0.2,
            'docs.python.org': 0.25,
            'developer.mozilla.org': 0.2,
            'reactjs.org': 0.15,
            'nodejs.org': 0.15,
            'microsoft.com': 0.1,
            'google.com': 0.1,
            'w3.org': 0.15,
            'ieee.org': 0.2
        }
        
        return authority_domains.get(domain.lower(), 0.0)
    
    def _get_quality_tier(self, score: float) -> str:
        """Get quality tier based on score"""
        if score >= 0.8:
            return 'high'
        elif score >= 0.6:
            return 'medium-high'
        elif score >= 0.4:
            return 'medium'
        elif score >= 0.2:
            return 'low-medium'
        else:
            return 'low'
    
    def _calculate_relevance_score(self, query: str, title: str, content: str) -> float:
        """Calculate relevance score between query and content"""
        query_terms = query.lower().split()
        combined_text = f"{title} {content}".lower()
        
        matches = sum(1 for term in query_terms if term in combined_text)
        return matches / len(query_terms) if query_terms else 0.0
    
    def _get_score_distribution(self, scored_results: List[Dict]) -> Dict:
        """Get distribution of scores"""
        scores = [item['combined_score'] for item in scored_results]
        
        return {
            'high_score': len([s for s in scores if s >= 0.8]),
            'medium_score': len([s for s in scores if 0.5 <= s < 0.8]),
            'low_score': len([s for s in scores if s < 0.5]),
            'average': round(sum(scores) / len(scores), 3) if scores else 0
        }
    
    def _create_content_signature(self, content: str, title: str) -> str:
        """Create signature for duplicate detection"""
        # Normalize and create hash
        normalized = re.sub(r'\s+', ' ', f"{title} {content}".lower().strip())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _find_near_duplicates(self, results: List[Dict]) -> List[Dict]:
        """Find near-duplicate results based on title similarity"""
        near_duplicates = []
        
        for i, result1 in enumerate(results):
            for j, result2 in enumerate(results[i+1:], i+1):
                title1 = result1.get('title', '').lower()
                title2 = result2.get('title', '').lower()
                
                if title1 and title2:
                    similarity = self._calculate_title_similarity(title1, title2)
                    if similarity >= 0.8:  # 80% similarity threshold
                        near_duplicates.append({
                            'index1': i,
                            'index2': j,
                            'title1': result1.get('title', ''),
                            'title2': result2.get('title', ''),
                            'similarity': round(similarity, 3)
                        })
        
        return near_duplicates
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles"""
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def health_check(self) -> Dict:
        """Check service health"""
        try:
            # Test with sample content
            test_result = self.score_quality(
                "This is a comprehensive tutorial about Python programming with examples",
                "Python Programming Tutorial",
                "python.org"
            )
            
            return {
                'status': 'healthy',
                'cache_size': len(self.cache),
                'test_scoring_working': 'error' not in test_result,
                'quality_indicators_loaded': len(self.quality_indicators),
                'content_patterns_loaded': len(self.content_type_patterns)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
