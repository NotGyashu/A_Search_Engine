"""🎯 Domain-Based Ranking Service
Provides educational domain prioritization and content type detection
"""

import re
from typing import Dict, List, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

class DomainRanker:
    """
    Zero-runtime-cost domain ranking with precomputed scores
    """
    
    # Tier 1: Highest quality educational domains
    TIER_1_EDUCATIONAL = {
        'wikipedia.org': 2.0,
        'en.wikipedia.org': 2.0,
        'geeksforgeeks.org': 1.9,
        'stackoverflow.com': 1.8,
        'github.com': 1.7,
        'arxiv.org': 1.8,
        'nature.com': 1.7,
        'science.org': 1.7,
        'mit.edu': 1.8,
        'stanford.edu': 1.8,
        'harvard.edu': 1.8,
        'w3schools.com': 1.6,
        'mozilla.org': 1.6,
        'freecodecamp.org': 1.6,
        'codecademy.com': 1.5,
        'khanacademy.org': 1.7,
        'coursera.org': 1.5,
        'edx.org': 1.5,
        'udacity.com': 1.4,
        'udemy.com': 1.3,
        'tutorialspoint.com': 1.4,
        'javatpoint.com': 1.3,
        'programiz.com': 1.4,
        'leetcode.com': 1.5,
        'hackerrank.com': 1.4,
        'topcoder.com': 1.3,
        'codeforces.com': 1.3,
        'codechef.com': 1.3,
        'guru99.com': 1.2,
        'baeldung.com': 1.3,
        'spring.io': 1.4,
        'docs.python.org': 1.7,
        'docs.oracle.com': 1.6,
        'docs.microsoft.com': 1.5,
        'developer.mozilla.org': 1.8,
        'developer.android.com': 1.6,
        'developer.apple.com': 1.6,
        'aws.amazon.com': 1.5,
        'cloud.google.com': 1.5,
        'docs.aws.amazon.com': 1.5,
        'firebase.google.com': 1.4,
        'nodejs.org': 1.5,
        'reactjs.org': 1.5,
        'vuejs.org': 1.5,
        'angular.io': 1.5
    }
    
    # Tier 2: Quality content domains
    TIER_2_EDUCATIONAL = {
        'medium.com': 1.4,
        'dev.to': 1.3,
        'towardsdatascience.com': 1.5,
        'hackernoon.com': 1.3,
        'scotch.io': 1.2,
        'css-tricks.com': 1.3,
        'smashingmagazine.com': 1.3,
        'alistapart.com': 1.3,
        'sitepoint.com': 1.2,
        'digitalocean.com': 1.3,
        'netlify.com': 1.2,
        'heroku.com': 1.2,
        'blog.google': 1.2,
        'engineering.fb.com': 1.3,
        'netflixtechblog.com': 1.3,
        'eng.uber.com': 1.3,
        'blog.twitter.com': 1.2,
        'blog.linkedin.com': 1.2,
        'blog.github.com': 1.2,
        'auth0.com': 1.2,
        'okta.com': 1.2,
        'twilio.com': 1.2,
        'stripe.com': 1.2,
        'segment.com': 1.2
    }
    
    # Educational TLDs (precomputed for speed)
    EDUCATIONAL_TLDS = {
        '.edu': 1.6,
        '.ac.uk': 1.5,
        '.ac.in': 1.4,
        '.edu.au': 1.4,
        '.edu.ca': 1.4,
        '.gov': 1.4,
        '.org': 1.2
    }
    
    # Definition indicators (precompiled regex for speed)
    DEFINITION_PATTERNS = [
        re.compile(r'\b(?:what\s+is|definition|meaning|explain|introduction|overview)\b', re.IGNORECASE),
        re.compile(r'\b(?:tutorial|guide|how\s+to|learn|course|lesson)\b', re.IGNORECASE),
        re.compile(r'\b(?:reference|documentation|docs|manual|api)\b', re.IGNORECASE),
        re.compile(r'\b(?:example|sample|demo|code|implementation)\b', re.IGNORECASE)
    ]
    
    # Domain cache for performance
    _domain_cache = {}
    
    def __init__(self):
        # Merge all domain rankings for fast lookup
        self.all_domains = {**self.TIER_1_EDUCATIONAL, **self.TIER_2_EDUCATIONAL}
        print("DomainRanker initialized with precomputed domain scores.")
        # Precompile domain patterns for TLD matching
        self.tld_patterns = [(tld, score) for tld, score in self.EDUCATIONAL_TLDS.items()]
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL with caching"""
        if url in self._domain_cache:
            return self._domain_cache[url]
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            self._domain_cache[url] = domain
            return domain
        except:
            return ""
    
    def get_domain_score(self, url: str) -> float:
        """Get domain authority score (zero-cost lookup)"""
        domain = self.extract_domain(url)
        # Direct domain lookup (fastest)
        if domain in self.all_domains:
            return self.all_domains[domain]
        
        # TLD-based scoring
        for tld, score in self.tld_patterns:
            if domain.endswith(tld):
                return score
        
        return 1.0  # Default score
    
    def get_content_type_boost(self, title: str, content: str, query_terms: List[str]) -> float:
        """Calculate content type boost based on query and content"""
        boost = 1.0
        
        # Combine title and first part of content for analysis
        text_to_analyze = f"{title} {content[:500]}".lower()
        
        # Query-specific boosts
        query_text = " ".join(query_terms).lower()
        
        # Definition queries get boost for definition content
        if any(term in query_text for term in ['what', 'define', 'definition', 'meaning', 'explain']):
            if self.DEFINITION_PATTERNS[0].search(text_to_analyze):
                boost *= 1.5
        
        # Tutorial queries get boost for tutorial content
        if any(term in query_text for term in ['tutorial', 'guide', 'how', 'learn', 'course']):
            if self.DEFINITION_PATTERNS[1].search(text_to_analyze):
                boost *= 1.4
        
        # Reference queries get boost for documentation
        if any(term in query_text for term in ['reference', 'documentation', 'docs', 'api']):
            if self.DEFINITION_PATTERNS[2].search(text_to_analyze):
                boost *= 1.3
        
        # Example queries get boost for examples
        if any(term in query_text for term in ['example', 'sample', 'demo', 'code']):
            if self.DEFINITION_PATTERNS[3].search(text_to_analyze):
                boost *= 1.2
        print(f"Content type boost calculated: {boost:.2f} for query terms: {query_terms}")
        return boost
    
    def calculate_domain_boost(self, url: str, title: str, content: str, query_terms: List[str] = None) -> float:
        """Calculate total domain and content boost"""
        # Get base domain score
        domain_score = self.get_domain_score(url)
        
        # Get content type boost if query terms provided
        content_boost = 1.0
        if query_terms:
            content_boost = self.get_content_type_boost(title, content, query_terms)
        
        # Combined boost (capped at 3.0 to prevent extreme scores)
        total_boost = min(domain_score * content_boost, 3.0)
        print(f"Total domain boost calculated: {total_boost:.2f} for URL: {url}")
        return total_boost
    
    def is_educational_domain(self, url: str) -> bool:
        """Check if domain is educational (fast lookup)"""
        domain = self.extract_domain(url)
        print(f"Domain educational?")
        
        # Check direct educational domains
        if domain in self.all_domains:
            return True
        
        # Check educational TLDs
        for tld, _ in self.tld_patterns:
            if domain.endswith(tld):
                return True
        
        return False
    
    def get_domain_stats(self) -> Dict:
        """Get domain ranking statistics"""
        print("Gathering domain ranking statistics...")
         # Return counts of educational domains and TLDs
         # This is a zero-cost operation since we use precomputed data
        return {
            'tier_1_domains': len(self.TIER_1_EDUCATIONAL),
            'tier_2_domains': len(self.TIER_2_EDUCATIONAL),
            'educational_tlds': len(self.EDUCATIONAL_TLDS),
            'total_domains': len(self.all_domains),
            'cache_size': len(self._domain_cache)
        }