"""
🌐 Language Detection for Data Pipeline
Ultra-fast English detection using pattern matching and statistical analysis
"""

import re
import logging
from typing import Optional, Dict, List
from collections import Counter

logger = logging.getLogger(__name__)

class LanguageDetector:
    """
    Fast language detection optimized for English content filtering
    Uses multiple techniques for high accuracy with minimal performance impact
    """
    
    # Most common English words (top 100 by frequency)
    COMMON_ENGLISH_WORDS = {
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
        'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his',
        'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy',
        'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'about', 'after',
        'again', 'also', 'been', 'before', 'being', 'between', 'both', 'called',
        'came', 'come', 'could', 'each', 'find', 'first', 'from', 'good', 'great',
        'have', 'here', 'into', 'just', 'know', 'like', 'long', 'look', 'make',
        'many', 'more', 'most', 'move', 'much', 'must', 'name', 'need', 'number',
        'only', 'other', 'over', 'part', 'place', 'right', 'same', 'should',
        'show', 'since', 'some', 'such', 'take', 'than', 'that', 'their', 'them',
        'there', 'these', 'they', 'thing', 'think', 'this', 'those', 'through',
        'time', 'under', 'very', 'want', 'water', 'well', 'were', 'what', 'where',
        'which', 'while', 'will', 'with', 'work', 'would', 'write', 'year', 'your'
    }
    
    # English-specific character patterns
    ENGLISH_PATTERNS = [
        r'\b(?:the|and|for|are|but|not|you|all|can|had|her|was|one|our|out|day)\b',
        r'\b(?:get|has|him|his|how|man|new|now|old|see|two|way|who|boy|did|its)\b',
        r'\b(?:let|put|say|she|too|use|about|after|again|also|been|before|being)\b',
        r'\b(?:between|both|called|came|come|could|each|find|first|from|good)\b',
        r'\b(?:great|have|here|into|just|know|like|long|look|make|many|more)\b'
    ]
    
    # Precompiled regex patterns for performance
    ENGLISH_REGEX = [re.compile(pattern, re.IGNORECASE) for pattern in ENGLISH_PATTERNS]
    
    # Non-English script detection (Unicode ranges)
    NON_ENGLISH_SCRIPTS = [
        (0x4E00, 0x9FFF, 'Chinese'),      # CJK Unified Ideographs
        (0x3040, 0x309F, 'Hiragana'),     # Japanese Hiragana
        (0x30A0, 0x30FF, 'Katakana'),     # Japanese Katakana
        (0x0600, 0x06FF, 'Arabic'),       # Arabic
        (0x0400, 0x04FF, 'Cyrillic'),     # Cyrillic (Russian, etc.)
        (0x0590, 0x05FF, 'Hebrew'),       # Hebrew
        (0x0E00, 0x0E7F, 'Thai'),         # Thai
        (0x0900, 0x097F, 'Devanagari'),   # Hindi
        (0x0980, 0x09FF, 'Bengali'),      # Bengali
        (0x0A00, 0x0A7F, 'Gurmukhi'),     # Punjabi
        (0x0A80, 0x0AFF, 'Gujarati'),     # Gujarati
        (0x0B00, 0x0B7F, 'Oriya'),        # Oriya
        (0x0B80, 0x0BFF, 'Tamil'),        # Tamil
        (0x0C00, 0x0C7F, 'Telugu'),       # Telugu
        (0x0C80, 0x0CFF, 'Kannada'),      # Kannada
        (0x0D00, 0x0D7F, 'Malayalam'),    # Malayalam
        (0x1100, 0x11FF, 'Hangul_Jamo'),  # Korean Hangul Jamo
        (0xAC00, 0xD7AF, 'Hangul_Syllables')  # Korean Hangul Syllables
    ]
    
    # HTML lang attribute regex
    HTML_LANG_REGEX = re.compile(r'<html[^>]*lang\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    
    # English-speaking domains
    ENGLISH_DOMAINS = {
        'wikipedia.org', 'en.wikipedia.org', 'github.com', 'stackoverflow.com',
        'medium.com', 'reddit.com', 'youtube.com', 'google.com', 'microsoft.com',
        'apple.com', 'amazon.com', 'facebook.com', 'twitter.com', 'linkedin.com',
        'geeksforgeeks.org', 'w3schools.com', 'mozilla.org', 'freecodecamp.org',
        'codecademy.com', 'tutorialspoint.com', 'programiz.com', 'baeldung.com'
    }
    
    @classmethod
    def extract_html_lang(cls, html: str) -> Optional[str]:
        """Extract language from HTML lang attribute"""
        match = cls.HTML_LANG_REGEX.search(html)
        if match:
            lang = match.group(1).lower()
            return lang[:2] if len(lang) >= 2 else lang
        return None
    
    @classmethod
    def is_english_domain(cls, url: str) -> bool:
        """Check if URL belongs to English-speaking domain"""
        url_lower = url.lower()
        
        # Check for English TLDs
        if any(tld in url_lower for tld in ['.com', '.org', '.net', '.edu', '.gov', '.uk', '.us', '.ca', '.au', '.nz']):
            return True
        
        # Check for known English domains
        for domain in cls.ENGLISH_DOMAINS:
            if domain in url_lower:
                return True
        
        return False
    
    @classmethod
    def has_non_english_script(cls, text: str) -> bool:
        """Check if text contains non-English scripts"""
        # Check first 1000 characters for performance
        sample = text[:1000]
        
        for char in sample:
            char_code = ord(char)
            for start, end, script in cls.NON_ENGLISH_SCRIPTS:
                if start <= char_code <= end:
                    return True
        
        return False
    
    @classmethod
    def calculate_english_word_ratio(cls, text: str, max_words: int = 100) -> float:
        """Calculate ratio of English words in text"""
        # Extract words (alphanumeric only)
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        if not words:
            return 0.0
        
        # Limit for performance
        words = words[:max_words]
        
        # Count English words
        english_count = sum(1 for word in words if word in cls.COMMON_ENGLISH_WORDS)
        
        return english_count / len(words)
    
    @classmethod
    def calculate_english_pattern_score(cls, text: str) -> float:
        """Calculate English pattern matching score"""
        text_sample = text[:2000]  # First 2000 chars for performance
        
        total_matches = 0
        for pattern in cls.ENGLISH_REGEX:
            matches = pattern.findall(text_sample)
            total_matches += len(matches)
        
        # Normalize by text length
        return min(total_matches / len(text_sample.split()), 1.0)
    
    @classmethod
    def detect_language(cls, text: str, url: str = "") -> Optional[str]:
        """
        Detect if text is English using multiple techniques
        Returns 'en' if English, None otherwise
        """
        if not text or len(text) < 50:
            return None
        
        # 1. Check HTML lang attribute (fastest)
        if '<html' in text:
            html_lang = cls.extract_html_lang(text)
            if html_lang:
                return 'en' if html_lang == 'en' else None
        
        # 2. Check domain (second fastest)
        if url and cls.is_english_domain(url):
            return 'en'
        
        # 3. Check for non-English scripts (immediate rejection)
        if cls.has_non_english_script(text):
            return None
        
        # 4. Calculate English word ratio
        english_ratio = cls.calculate_english_word_ratio(text)
        
        # 5. Calculate pattern matching score
        pattern_score = cls.calculate_english_pattern_score(text)
        
        # Combined scoring
        final_score = (english_ratio * 0.6) + (pattern_score * 0.4)
        
        # Threshold for English detection
        if final_score > 0.3:
            return 'en'
        
        return None
    
    @classmethod
    def is_english(cls, text: str, url: str = "") -> bool:
        """Simple boolean check for English content"""
        return cls.detect_language(text, url) == 'en'
    
    @classmethod
    def get_language_stats(cls, text: str, url: str = "") -> Dict:
        """Get detailed language detection statistics"""
        if not text:
            return {
                'detected_language': None,
                'confidence': 0.0,
                'english_word_ratio': 0.0,
                'pattern_score': 0.0,
                'has_non_english_script': False,
                'html_lang': None,
                'is_english_domain': False
            }
        
        # Calculate all metrics
        html_lang = cls.extract_html_lang(text) if '<html' in text else None
        is_english_domain = cls.is_english_domain(url) if url else False
        has_non_english = cls.has_non_english_script(text)
        english_ratio = cls.calculate_english_word_ratio(text)
        pattern_score = cls.calculate_english_pattern_score(text)
        
        # Final detection
        detected_lang = cls.detect_language(text, url)
        confidence = (english_ratio * 0.6) + (pattern_score * 0.4)
        
        return {
            'detected_language': detected_lang,
            'confidence': confidence,
            'english_word_ratio': english_ratio,
            'pattern_score': pattern_score,
            'has_non_english_script': has_non_english,
            'html_lang': html_lang,
            'is_english_domain': is_english_domain
        }
