"""
Content Cleaner and Text Processor

Handles text cleaning, normalization, chunking, and preparation for indexing.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional
from collections import Counter

logger = logging.getLogger(__name__)


class ContentCleaner:
    """Advanced text cleaning and processing for search optimization."""
    
    def __init__(self, max_chunk_size: int = 2000, min_chunk_size: int = 100):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size  # Increased from 100  for better chunks
        
        # Compile regex patterns for efficiency
        self.patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile frequently used regex patterns."""
        return {
            'extra_whitespace': re.compile(r'\s+'),
            'sentence_endings': re.compile(r'(?<=[.!?])\s+'),
            'code_blocks': re.compile(r'```[\s\S]*?```'),
            'inline_code': re.compile(r'`[^`]+`'),
            'urls': re.compile(r'https?://\S+'),
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'navigation_words': re.compile(r'\b(home|menu|navigation|footer|header|sidebar|breadcrumb)\b', re.IGNORECASE),
            'boilerplate': re.compile(r'\b(click here|read more|continue reading|share this|follow us)\b', re.IGNORECASE),
            'repetitive_phrases': re.compile(r'(.{10,}?)\1{2,}'),  # Remove 3+ repetitions
            'excessive_punctuation': re.compile(r'[.!?]{3,}'),
            'html_entities': re.compile(r'&[a-zA-Z0-9#]+;'),
            'social_sharing': re.compile(r'\b(facebook|twitter|linkedin|instagram|youtube|share|like|follow)\b', re.IGNORECASE)
        }
    
    def clean_text(self, text: str) -> str:
        """Comprehensive text cleaning pipeline."""
        if not text:
            return ""
        
        # Step 1: Remove navigation and boilerplate content
        text = self._remove_navigation_content(text)
        
        # Step 2: Clean HTML entities and special characters
        text = self._clean_html_entities(text)
        
        # Step 3: Remove repetitive content
        text = self._remove_repetitive_content(text)
        
        # Step 4: Normalize whitespace
        text = self._normalize_whitespace(text)
        
        # Step 5: Remove social sharing artifacts
        text = self._remove_social_artifacts(text)
        
        return text.strip()
    
    def _remove_navigation_content(self, text: str) -> str:
        """Remove navigation and UI-related content."""
        # Remove common navigation patterns
        text = self.patterns['navigation_words'].sub(' ', text)
        text = self.patterns['boilerplate'].sub(' ', text)
        
        # Remove lines that are likely navigation
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip short lines with only navigation words
            words = line.split()
            if len(words) <= 3 and any(word.lower() in ['home', 'menu', 'back', 'next', 'previous'] for word in words):
                continue
            
            # Skip lines that are mostly non-alphabetic (likely UI elements)
            alpha_ratio = sum(c.isalpha() for c in line) / len(line) if line else 0
            if alpha_ratio < 0.5 and len(line) < 50:
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _clean_html_entities(self, text: str) -> str:
        """Clean HTML entities and special characters."""
        # Common HTML entities
        entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&apos;': "'",
            '&nbsp;': ' ',
            '&#39;': "'",
            '&#8217;': "'",
            '&#8220;': '"',
            '&#8221;': '"',
            '&#8211;': '-',
            '&#8212;': '-'
        }

        for entity, replacement in entities.items():
            text = text.replace(entity, replacement)
        
        # Remove remaining HTML entities
        text = self.patterns['html_entities'].sub(' ', text)
        
        return text
    
    def _remove_repetitive_content(self, text: str) -> str:
        """Remove repetitive phrases and content."""
        # Remove exact repetitions
        text = self.patterns['repetitive_phrases'].sub(r'\1', text)
        
        # Remove excessive punctuation
        text = self.patterns['excessive_punctuation'].sub('...', text)
        
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize all whitespace to single spaces."""
        return self.patterns['extra_whitespace'].sub(' ', text)
    
    def _remove_social_artifacts(self, text: str) -> str:
        """Remove social media sharing artifacts."""
        text = self.patterns['social_sharing'].sub(' ', text)
        return text
    
    def create_text_snippet(self, content: str, max_length: int = 300) -> str:
        """Create a clean, representative snippet of the content."""
        if not content:
            return ""
        
        # Find the most meaningful paragraph
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        # Score paragraphs by information density
        best_paragraph = ""
        best_score = 0
        
        for paragraph in paragraphs:
            if len(paragraph) < 50:  # Too short
                continue
                
            # Calculate information density score
            words = paragraph.split()
            unique_words = set(word.lower() for word in words)
            
            score = (
                len(unique_words) * 2 +  # Vocabulary diversity
                (1 if any(c.isupper() for c in paragraph) else 0) * 5 +  # Has proper nouns
                (1 if '.' in paragraph else 0) * 3 +  # Has sentences
                (-1 if paragraph.lower().count('click') > 0 else 0) * 10  # Penalty for UI text
            )
            
            if score > best_score:
                best_score = score
                best_paragraph = paragraph
        
        # Fall back to first paragraph if no good one found
        if not best_paragraph and paragraphs:
            best_paragraph = paragraphs[0]
        
        # Truncate to max_length
        if len(best_paragraph) > max_length:
            # Try to end at a sentence boundary
            truncated = best_paragraph[:max_length]
            last_sentence_end = max(
                truncated.rfind('.'),
                truncated.rfind('!'),
                truncated.rfind('?')
            )
            
            if last_sentence_end > max_length * 0.7:  # If we can keep 70% and end at sentence
                best_paragraph = truncated[:last_sentence_end + 1]
            else:
                # Find last word boundary
                last_space = truncated.rfind(' ')
                if last_space > max_length * 0.8:
                    best_paragraph = truncated[:last_space] + "..."
                else:
                    best_paragraph = truncated + "..."
        
        return best_paragraph
    
    def intelligent_chunking(self, content: str, preserve_context: bool = True) -> List[str]:
        """Advanced content chunking that preserves semantic meaning."""
        if not content:
            return []
        
        # Split into sentences
        sentences = self.patterns['sentence_endings'].split(content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return []
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # Calculate the length if we add this sentence
            potential_length = len(current_chunk) + len(sentence) + 1
            
            if potential_length <= self.max_chunk_size:
                # Add sentence to current chunk
                current_chunk += (" " + sentence) if current_chunk else sentence
            else:
                # Save current chunk if it meets minimum size
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(current_chunk.strip())
                
                # Start new chunk with current sentence
                current_chunk = sentence
        
        # Add the final chunk
        if len(current_chunk) >= self.min_chunk_size:
            chunks.append(current_chunk.strip())
        elif chunks and current_chunk:
            # If final chunk is too small, append to last chunk
            chunks[-1] += " " + current_chunk
        
        # Apply overlap for better context (optional)
        if preserve_context and len(chunks) > 1:
            chunks = self._add_overlap(chunks)
        
        return chunks
    
    def _add_overlap(self, chunks: List[str], overlap_sentences: int = 1) -> List[str]:
        """Add sentence overlap between chunks for better context."""
        if len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = [chunks[0]]  # First chunk stays the same
        
        for i in range(1, len(chunks)):
            # Get last sentences from previous chunk
            prev_sentences = self.patterns['sentence_endings'].split(chunks[i-1])
            prev_sentences = [s.strip() for s in prev_sentences if s.strip()]
            
            # Take last N sentences for overlap
            overlap_text = ""
            if len(prev_sentences) > overlap_sentences:
                overlap_text = " ".join(prev_sentences[-overlap_sentences:]) + " "
            
            # Combine overlap with current chunk
            current_chunk = overlap_text + chunks[i]
            overlapped_chunks.append(current_chunk)
        
        return overlapped_chunks
    
    def extract_keywords(self, content: str, max_keywords: int = 20) -> List[str]:
        """Extract important keywords from content using advanced frequency analysis."""
        if not content:
            return []
        
        # Comprehensive stop words list
        stop_words = set([
            # Basic articles, prepositions, conjunctions
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'among', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
            
            # Common question words and pronouns
            'what', 'where', 'when', 'why', 'how', 'who', 'which', 'whose', 'whom',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs',
            
            # Common web/navigation words
            'get', 'make', 'use', 'take', 'give', 'see', 'know', 'think', 'come', 'go', 'want',
            'look', 'find', 'tell', 'ask', 'work', 'seem', 'feel', 'try', 'leave', 'put',
            'mean', 'keep', 'let', 'begin', 'help', 'talk', 'turn', 'start', 'show', 'hear',
            'play', 'run', 'move', 'live', 'believe', 'hold', 'bring', 'happen', 'write',
            'provide', 'sit', 'stand', 'lose', 'pay', 'meet', 'include', 'continue', 'set',
            'learn', 'change', 'lead', 'understand', 'watch', 'follow', 'stop', 'create',
            'speak', 'read', 'allow', 'add', 'spend', 'grow', 'open', 'walk', 'win', 'offer',
            'remember', 'love', 'consider', 'appear', 'buy', 'wait', 'serve', 'die', 'send',
            'expect', 'build', 'stay', 'fall', 'cut', 'reach', 'kill', 'remain', 'suggest',
            
            # Web/UI specific terms
            'click', 'here', 'link', 'page', 'site', 'website', 'home', 'menu', 'navigation',
            'footer', 'header', 'sidebar', 'breadcrumb', 'search', 'login', 'register',
            'submit', 'form', 'button', 'back', 'next', 'more', 'less', 'all', 'none',
            'contact', 'about', 'privacy', 'terms', 'copyright', 'share', 'like', 'follow',
            'subscribe', 'newsletter', 'email', 'download', 'upload', 'file', 'image',
            'video', 'audio', 'view', 'edit', 'delete', 'save', 'cancel', 'ok', 'yes', 'no',
            
            # Common filler words and determiners
            'very', 'really', 'quite', 'rather', 'just', 'only', 'even', 'still', 'also',
            'too', 'so', 'then', 'now', 'here', 'there', 'today', 'yesterday', 'tomorrow',
            'always', 'never', 'sometimes', 'often', 'usually', 'already', 'yet', 'again',
            'once', 'twice', 'first', 'second', 'third', 'last', 'next', 'previous',
            'another', 'other', 'same', 'different', 'new', 'old', 'good', 'bad', 'best',
            'worst', 'better', 'worse', 'much', 'many', 'little', 'few', 'most', 'least',
            'more', 'less', 'some', 'any', 'every', 'each', 'both', 'either', 'neither',
            
            # Additional problematic words found in analysis
            'their', 'them', 'they', 'than', 'then', 'there', 'these', 'those', 'thus',
            'such', 'said', 'says', 'say', 'way', 'ways', 'well', 'used', 'using', 'user',
            'users', 'one', 'two', 'three', 'within', 'without', 'while', 'where', 'when',
            'whether', 'which', 'who', 'whom', 'whose', 'why', 'how', 'however', 'though',
            'although', 'because', 'since', 'unless', 'until', 'while', 'whereas', 'whereby',
            'wherein', 'whereupon', 'wherever', 'whether', 'whichever', 'whoever', 'whomever',
            
            # Numbers and basic quantifiers
            'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
            'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 
            'eighteen', 'nineteen', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy',
            'eighty', 'ninety', 'hundred', 'thousand', 'million', 'billion', 'trillion',
            'first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth',
            'ninth', 'tenth', 'eleventh', 'twelfth'
        ])
        
        # Extract words (minimum 3 characters, exclude common patterns)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        
        # Filter out stop words and common meaningless patterns
        filtered_words = []
        for word in words:
            if (word not in stop_words and 
                len(word) >= 4 and  # Increased minimum length from 3 to 4
                not word.isdigit() and
                not re.match(r'^(www|http|html|css|js|php|com|org|net|amp|gt|lt)$', word) and
                not re.match(r'^(nbsp|quot|copy|reg|trade|hellip|ndash|mdash)$', word) and  # HTML entities
                not word.endswith(('ing', 'ed', 'er', 'est', 'ly', 's')) or len(word) >= 6):  # Allow suffixed words only if long enough
                filtered_words.append(word)
        
        # Count frequency and prioritize longer, more meaningful words
        word_freq = Counter(filtered_words)
        
        # Score words by frequency and length (prefer longer words)
        word_scores = {}
        for word, freq in word_freq.items():
            # Base score from frequency
            score = freq
            
            # Strong bonus for longer words (they're usually more meaningful)
            if len(word) >= 8:
                score *= 2.0  # Very strong bonus for long words
            elif len(word) >= 6:
                score *= 1.8  # Strong bonus
            elif len(word) >= 5:
                score *= 1.4  # Medium bonus
            elif len(word) >= 4:
                score *= 1.1  # Small bonus
            
            # Bonus for technical terms (contain numbers, capitals, or technical patterns)
            if re.search(r'[0-9]|[A-Z]', word):
                score *= 1.5
            
            # Bonus for domain-specific terms
            if any(term in word.lower() for term in ['tech', 'data', 'code', 'program', 'algorithm', 'system', 'network', 'software', 'hardware', 'computer']):
                score *= 1.3
            
            # Penalty for overly common patterns
            if word in ['said', 'says', 'like', 'just', 'back', 'part', 'time', 'year', 'years', 'people', 'things', 'thing']:
                score *= 0.5
            
            word_scores[word] = score
        
        # Get top keywords sorted by score, but ensure minimum quality
        keywords = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Filter for quality - only include words with sufficient score
        min_score = max(1.0, max(word_scores.values()) * 0.3) if word_scores else 1.0
        quality_keywords = [word for word, score in keywords if score >= min_score]
        
        # Return top keywords
        return quality_keywords[:max_keywords]
    
    def format_headings_for_index(self, headings: List[Dict[str, Any]]) -> str:
        """Format headings for OpenSearch indexing with proper truncation."""
        if not headings:
            return "[]"
        
        try:
            # Create a clean structure for indexing
            formatted_headings = []
            for heading in headings:
                if isinstance(heading, dict) and 'text' in heading:
                    # Ensure text is properly cleaned and not too long
                    text = str(heading['text']).strip()
                    if len(text) > 200:  # Reasonable limit for heading text
                        text = text[:197] + "..."
                    
                    formatted_headings.append({
                        'level': int(heading.get('level', 1)),
                        'text': text
                    })
                elif isinstance(heading, str):
                    text = heading.strip()
                    if len(text) > 200:
                        text = text[:197] + "..."
                    formatted_headings.append({'level': 1, 'text': text})
            
            # Limit number of headings to prevent oversized data
            if len(formatted_headings) > 10:
                formatted_headings = formatted_headings[:10]
            
            return json.dumps(formatted_headings, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Error formatting headings: {e}")
            return "[]"
