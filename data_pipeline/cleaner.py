"""
Content Cleaner - Text Processing and Quality Enhancement

This module provides comprehensive text cleaning, intelligent chunking,
and keyword extraction capabilities for search content optimization.
"""

import re
import json
import logging
from collections import Counter
from typing import List, Dict, Set, Any
from pathlib import Path

from config import PipelineConfig

logger = logging.getLogger(__name__)

# OPTIMIZED: Load stop words once at module level to avoid repeated loading
_STOP_WORDS_CACHE = None

def _load_stop_words_once() -> Set[str]:
    """Load stop words once and cache them."""
    global _STOP_WORDS_CACHE
    if _STOP_WORDS_CACHE is not None:
        return _STOP_WORDS_CACHE
        
    stop_words = set()
    stop_words_file = Path(__file__).parent / "stop_words.txt"
    
    try:
        if stop_words_file.exists():
            with open(stop_words_file, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip().lower()
                    if word and not word.startswith('#'):  # Skip comments and empty lines
                        stop_words.add(word)
            logger.info(f"Loaded {len(stop_words)} stop words from {stop_words_file}")
        else:
            # Fallback to basic stop words if file doesn't exist
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
                'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had',
                'do', 'does', 'did', 'will', 'would', 'should', 'could', 'can', 'may', 'might',
                'must', 'shall', 'it', 'its', 'this', 'that', 'these', 'those', 'i', 'you', 'he',
                'she', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'their'
            }
            logger.warning(f"Stop words file not found, using {len(stop_words)} fallback words")
    except Exception as e:
        logger.error(f"Error loading stop words: {e}")
        stop_words = set()
    
    _STOP_WORDS_CACHE = stop_words
    return stop_words


class ContentCleaner:
    """Advanced text cleaning and processing for search optimization."""
    
    def __init__(self, max_chunk_size: int = 3000, min_chunk_size: int = 150):  # INCREASED sizes
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        
        # Compile regex patterns for efficiency
        self.patterns = self._compile_patterns()
        
        # OPTIMIZED: Use cached stop words instead of loading each time
        self.stop_words = _load_stop_words_once()
    
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
            
            # Enhanced UI element detection
            line_lower = line.lower()
            
            # Skip lines with common UI patterns
            ui_patterns = [
                'vote up', 'vote down', 'upvote', 'downvote', 'points', 'karma',
                'reply', 'comment', 'share', 'like', 'follow', 'subscribe',
                'posted by', 'submitted by', 'author:', 'ago', 'minutes ago',
                'hours ago', 'days ago', 'permalink', 'source', 'edit', 'delete',
                'report', 'flag', 'hide', 'login', 'register', 'sign up', 'sign in'
            ]
            
            if any(pattern in line_lower for pattern in ui_patterns):
                continue
                
            # Skip short lines with only navigation words
            words = line.split()
            if len(words) <= 3 and any(word.lower() in ['home', 'menu', 'back', 'next', 'previous'] for word in words):
                continue
            
            # Skip lines that are mostly numbers (like vote counts)
            if len(words) > 0:
                numeric_words = sum(1 for word in words if word.isdigit())
                if numeric_words / len(words) > 0.6:  # More than 60% numbers
                    continue
            
            # Skip lines that are mostly non-alphabetic (likely UI elements)
            alpha_ratio = sum(c.isalpha() for c in line) / len(line) if line else 0
            if alpha_ratio < 0.5 and len(line) < 50:
                continue
            
            # Skip lines with repetitive words
            if len(words) > 2:
                word_counts = {}
                for word in words:
                    word_lower = word.lower()
                    word_counts[word_lower] = word_counts.get(word_lower, 0) + 1
                max_count = max(word_counts.values())
                if max_count > len(words) * 0.4:  # More than 40% repetition
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
    
    def create_description(self, content: str, max_length: int = 300) -> str:
        """Create a clean, representative description of the content."""
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
            
            # Skip paragraphs that are clearly navigation/UI elements
            if self._is_low_quality_paragraph(paragraph):
                continue
                
            # Calculate information density score
            words = paragraph.split()
            unique_words = set(word.lower() for word in words)
            
            score = (
                len(unique_words) * 2 +  # Vocabulary diversity
                (1 if any(c.isupper() for c in paragraph) else 0) * 5 +  # Has proper nouns
                (1 if '.' in paragraph else 0) * 3 +  # Has sentences
                (-1 if paragraph.lower().count('click') > 0 else 0) * 10 +  # Penalty for UI text
                (-1 if self._contains_repetitive_patterns(paragraph) else 0) * 15  # Penalty for repetitive content
            )
            
            if score > best_score:
                best_score = score
                best_paragraph = paragraph
        
        # Fall back to first non-low-quality paragraph if no good one found
        if not best_paragraph and paragraphs:
            for paragraph in paragraphs:
                if not self._is_low_quality_paragraph(paragraph):
                    best_paragraph = paragraph
                    break
            
            # Final fallback to first paragraph
            if not best_paragraph:
                best_paragraph = paragraphs[0]
        
        # Clean up the selected paragraph
        best_paragraph = self._clean_snippet_text(best_paragraph)
        
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

    def _is_low_quality_paragraph(self, paragraph: str) -> bool:
        """Check if a paragraph is likely to be navigation, UI, or low-quality content."""
        paragraph_lower = paragraph.lower()
        
        # Common UI/navigation patterns
        ui_indicators = [
            'click', 'menu', 'navigation', 'sidebar', 'footer', 'header',
            'subscribe', 'follow', 'share', 'like', 'comment', 'reply',
            'login', 'register', 'sign up', 'sign in', 'logout',
            'search', 'filter', 'sort', 'view all', 'load more',
            'privacy policy', 'terms of service', 'cookie policy',
            'advertisement', 'sponsored', 'ad', 'promo',
            'vote up', 'vote down', 'upvote', 'downvote',
            'points', 'karma', 'reputation', 'score',
            'posted by', 'submitted by', 'author:', 'by:',
            'ago', 'minutes ago', 'hours ago', 'days ago',
            'permalink', 'source', 'link', 'url',
            'edit', 'delete', 'report', 'flag', 'hide'
        ]
        
        # Check for UI indicators
        if any(indicator in paragraph_lower for indicator in ui_indicators):
            return True
        
        # Check for repetitive patterns (like vote counters)
        if self._contains_repetitive_patterns(paragraph):
            return True
        
        # Check for mostly numbers or symbols
        words = paragraph.split()
        if len(words) > 0:
            non_alpha_words = sum(1 for word in words if not any(c.isalpha() for c in word))
            if non_alpha_words / len(words) > 0.5:  # More than 50% non-alphabetic words
                return True
        
        # Check for very short sentences with common patterns
        if len(paragraph) < 100 and ('reply' in paragraph_lower or 'posted' in paragraph_lower):
            return True
            
        return False

    def _contains_repetitive_patterns(self, text: str) -> bool:
        """Check if text contains repetitive patterns like vote counters."""
        words = text.split()
        if len(words) < 3:
            return False
        
        # Check for repeated words (like "1 1 1" or "vote vote vote")
        word_counts = {}
        for word in words:
            word_lower = word.lower()
            word_counts[word_lower] = word_counts.get(word_lower, 0) + 1
        
        # If any word appears more than 30% of the time, it's repetitive
        max_count = max(word_counts.values())
        if max_count > len(words) * 0.3:
            return True
        
        # Check for numeric patterns (like vote counts)
        numeric_words = [word for word in words if word.isdigit()]
        if len(numeric_words) > len(words) * 0.4:  # More than 40% numbers
            return True
        
        return False

    def _clean_snippet_text(self, text: str) -> str:
        """Final cleanup of snippet text."""
        # Remove HTML entities
        import html
        text = html.unescape(text)
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        # Remove leading/trailing punctuation that might be artifacts
        text = text.strip('.,;:-()[]{}"\' ')
        
        # Fix common encoding issues
        text = text.replace('â€™', "'").replace('â€œ', '"').replace('â€', '"')
        text = text.replace('Ã¢â‚¬â„¢', "'").replace('Ã¢â‚¬Å"', '"').replace('Ã¢â‚¬', '"')
        
        return text
    
    def intelligent_chunking(self, content: str, preserve_context: bool = True, html_content: str = None, content_importance_threshold: float = 0.3) -> List[str]:
        """
        Enhanced content chunking that preserves semantic meaning and handles long-form content better.
        
        Args:
            content: Clean text content to chunk
            preserve_context: Whether to add overlap between chunks
            html_content: Original HTML content for structure analysis
            content_importance_threshold: Minimum importance score for content preservation
        
        Returns:
            List of content chunks with improved semantic preservation
        """
        if not content:
            return []
        
        # For very long content, use domain-specific strategies
        content_length = len(content)
        
        # Try HTML structure-based chunking first if HTML is available
        if html_content:
            html_chunks = self._enhanced_chunk_by_html_structure(content, html_content, content_importance_threshold)
            if html_chunks:
                return html_chunks
        
        # For long-form content, use enhanced sentence-based chunking
        if content_length > 5000:  # Long-form content
            return self._chunk_long_form_content(content, preserve_context)
        else:
            # Standard chunking for shorter content
            return self._chunk_by_sentences(content, preserve_context)
    
    def _enhanced_chunk_by_html_structure(self, content: str, html_content: str, importance_threshold: float = 0.3) -> List[str]:
        """
        Enhanced HTML structure-based chunking with content importance analysis.
        
        Args:
            content: Clean text content
            html_content: Original HTML content
            importance_threshold: Minimum importance score for inclusion
            
        Returns:
            List of structurally-aware chunks with better content preservation
        """
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'lxml')
            chunks = []
            
            # Enhanced element analysis for content importance
            important_elements = soup.find_all([
                'article', 'main', 'section', 'div', 'p', 
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'blockquote', 'pre', 'code', 'ul', 'ol', 'li',
                'table', 'th', 'td', 'figure', 'figcaption'
            ])
            
            # Find all heading tags and analyze document structure
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            
            if headings:
                # Structure-based chunking with enhanced content preservation
                for i, heading in enumerate(headings):
                    chunk_content = []
                    
                    # Add the heading text
                    heading_text = heading.get_text(strip=True)
                    if heading_text:
                        chunk_content.append(heading_text)
                    
                    # Get content until next heading of same or higher level
                    current_level = int(heading.name[1])  # h1 -> 1, h2 -> 2, etc.
                    
                    # Enhanced content collection with importance scoring
                    content_elements = self._collect_section_content(heading, current_level, importance_threshold)
                    chunk_content.extend(content_elements)
                    
                    # Create chunk from collected content
                    if chunk_content:
                        chunk_text = ' '.join(chunk_content)
                        
                        # Enhanced chunk size management
                        if len(chunk_text) > self.max_chunk_size:
                            # Split intelligently preserving important content
                            sub_chunks = self._split_large_chunk_intelligently(chunk_text, heading_text)
                            chunks.extend(sub_chunks)
                        elif len(chunk_text) >= self.min_chunk_size:
                            chunks.append(chunk_text)
                        else:
                            # Merge small chunks with previous if possible
                            if chunks and len(chunks[-1]) + len(chunk_text) <= self.max_chunk_size:
                                chunks[-1] += '\n\n' + chunk_text
                            elif len(chunk_text) >= 50:  # Still include if not too small
                                chunks.append(chunk_text)
            else:
                # No clear heading structure, use enhanced paragraph-based chunking
                paragraphs = soup.find_all(['p', 'div', 'section', 'article'])
                current_chunk = []
                current_length = 0
                
                for para in paragraphs:
                    para_text = para.get_text(strip=True)
                    if not para_text or len(para_text) < 20:  # Skip very short paragraphs
                        continue
                    
                    # Calculate content importance
                    importance_score = self._calculate_content_importance(para, para_text)
                    
                    if importance_score >= importance_threshold:
                        para_length = len(para_text)
                        
                        if current_length + para_length <= self.max_chunk_size:
                            current_chunk.append(para_text)
                            current_length += para_length
                        else:
                            # Save current chunk
                            if current_chunk and current_length >= self.min_chunk_size:
                                chunks.append(' '.join(current_chunk))
                            
                            # Start new chunk
                            current_chunk = [para_text]
                            current_length = para_length
                
                # Add final chunk
                if current_chunk and current_length >= self.min_chunk_size:
                    chunks.append(' '.join(current_chunk))
            
            # Filter and validate chunks
            valid_chunks = [chunk for chunk in chunks if len(chunk) >= self.min_chunk_size]
            
            return valid_chunks if valid_chunks else []
            
        except Exception as e:
            logger.warning(f"Enhanced HTML structure chunking failed: {e}, falling back to sentence chunking")
            return []
    
    def _collect_section_content(self, heading, current_level: int, importance_threshold: float) -> List[str]:
        """Collect content elements for a section with importance scoring."""
        content_elements = []
        
        # Find all elements between this heading and the next relevant heading
        next_element = heading.next_sibling
        while next_element:
            if hasattr(next_element, 'name'):
                # Check if it's a heading of same or higher level
                if (next_element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] and
                    int(next_element.name[1]) <= current_level):
                    break
                
                # Extract text from content elements with importance scoring
                if next_element.name in ['p', 'div', 'section', 'article', 'li', 'td', 'blockquote', 'pre']:
                    text = next_element.get_text(strip=True)
                    if text and len(text) > 15:  # Minimum content length
                        importance_score = self._calculate_content_importance(next_element, text)
                        if importance_score >= importance_threshold:
                            content_elements.append(text)
                
                # Handle lists specially to preserve structure
                elif next_element.name in ['ul', 'ol']:
                    list_items = next_element.find_all('li')
                    list_content = []
                    for item in list_items:
                        item_text = item.get_text(strip=True)
                        if item_text:
                            list_content.append(f"• {item_text}")
                    
                    if list_content:
                        list_text = '\n'.join(list_content)
                        importance_score = self._calculate_content_importance(next_element, list_text)
                        if importance_score >= importance_threshold:
                            content_elements.append(list_text)
                
                # Handle tables
                elif next_element.name == 'table':
                    table_text = self._extract_table_content(next_element)
                    if table_text:
                        importance_score = self._calculate_content_importance(next_element, table_text)
                        if importance_score >= importance_threshold:
                            content_elements.append(table_text)
            
            next_element = next_element.next_sibling
        
        return content_elements
    
    def _calculate_content_importance(self, element, text: str) -> float:
        """Calculate importance score for content based on various factors."""
        score = 0.0
        
        # Base score from text length and quality
        word_count = len(text.split())
        if word_count >= 10:
            score += 0.3
        if word_count >= 25:
            score += 0.2
        if word_count >= 50:
            score += 0.1
        
        # Bonus for diverse vocabulary
        unique_words = len(set(word.lower() for word in text.split()))
        if unique_words > word_count * 0.7:  # High vocabulary diversity
            score += 0.2
        
        # Element-based scoring
        if hasattr(element, 'name'):
            if element.name in ['article', 'main', 'section']:
                score += 0.3
            elif element.name in ['p', 'blockquote']:
                score += 0.2
            elif element.name in ['li', 'td']:
                score += 0.1
        
        # Class and ID analysis for content detection
        classes = ' '.join(element.get('class', [])).lower() if hasattr(element, 'get') else ''
        element_id = element.get('id', '').lower() if hasattr(element, 'get') else ''
        
        content_indicators = ['content', 'article', 'main', 'body', 'text', 'post', 'entry']
        nav_indicators = ['nav', 'menu', 'sidebar', 'footer', 'header', 'ad', 'advertisement']
        
        if any(indicator in classes or indicator in element_id for indicator in content_indicators):
            score += 0.2
        
        if any(indicator in classes or indicator in element_id for indicator in nav_indicators):
            score -= 0.3
        
        # Content quality indicators
        if any(char in text for char in '.!?'):  # Has sentence structure
            score += 0.1
        
        if text.count('.') >= 2:  # Multiple sentences
            score += 0.1
        
        # Penalty for repetitive or low-quality content
        if len(set(text.lower().split())) < len(text.split()) * 0.5:  # High repetition
            score -= 0.2
        
        return max(0.0, min(1.0, score))  # Clamp between 0 and 1
    
    def _extract_table_content(self, table_element) -> str:
        """Extract meaningful content from table elements."""
        try:
            rows = table_element.find_all('tr')
            table_content = []
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if cells:
                    row_text = ' | '.join(cell.get_text(strip=True) for cell in cells if cell.get_text(strip=True))
                    if row_text:
                        table_content.append(row_text)
            
            return '\n'.join(table_content) if table_content else ''
        except Exception:
            return ''
    
    def _chunk_long_form_content(self, content: str, preserve_context: bool = True) -> List[str]:
        """Enhanced chunking strategy for long-form content."""
        # First, try to identify natural break points (double newlines, section breaks)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        if not paragraphs:
            # Fallback to sentence-based chunking
            return self._chunk_by_sentences(content, preserve_context)
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph_length = len(paragraph)
            current_length = len(current_chunk)
            
            # If adding this paragraph would exceed max size
            if current_length + paragraph_length > self.max_chunk_size:
                # Save current chunk if it's substantial
                if current_length >= self.min_chunk_size:
                    chunks.append(current_chunk.strip())
                
                # Handle oversized paragraphs
                if paragraph_length > self.max_chunk_size:
                    # Split the paragraph by sentences
                    para_chunks = self._split_large_chunk_intelligently(paragraph, "")
                    chunks.extend(para_chunks)
                    current_chunk = ""
                else:
                    current_chunk = paragraph
            else:
                # Add paragraph to current chunk
                current_chunk += ("\n\n" + paragraph) if current_chunk else paragraph
        
        # Add final chunk
        if len(current_chunk) >= self.min_chunk_size:
            chunks.append(current_chunk.strip())
        elif chunks and current_chunk:
            # Merge small final chunk with previous
            chunks[-1] += "\n\n" + current_chunk
        
        # Apply context overlap for long-form content
        if preserve_context and len(chunks) > 1:
            chunks = self._add_enhanced_overlap(chunks)
        
        return chunks
    
    def _split_large_chunk_intelligently(self, chunk_text: str, heading_context: str = "") -> List[str]:
        """Split a large chunk intelligently while preserving context and meaning."""
        sentences = self.patterns['sentence_endings'].split(chunk_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return [chunk_text] if len(chunk_text) >= self.min_chunk_size else []
        
        sub_chunks = []
        current_chunk = heading_context if heading_context else ""
        
        for sentence in sentences:
            sentence_length = len(sentence)
            current_length = len(current_chunk)
            
            # Calculate potential length with sentence separator
            potential_length = current_length + sentence_length + (2 if current_chunk else 0)
            
            if potential_length <= self.max_chunk_size:
                current_chunk += (". " + sentence) if current_chunk and not current_chunk.endswith(heading_context) else sentence
            else:
                # Save current chunk if substantial
                if current_length >= self.min_chunk_size:
                    sub_chunks.append(current_chunk.strip())
                
                # Start new chunk
                if sentence_length > self.max_chunk_size:
                    # Handle extremely long sentences (rare but possible)
                    words = sentence.split()
                    word_chunks = []
                    current_words = []
                    current_word_length = 0
                    
                    for word in words:
                        word_length = len(word) + 1  # +1 for space
                        if current_word_length + word_length <= self.max_chunk_size:
                            current_words.append(word)
                            current_word_length += word_length
                        else:
                            if current_words:
                                word_chunks.append(' '.join(current_words))
                            current_words = [word]
                            current_word_length = word_length
                    
                    if current_words:
                        word_chunks.append(' '.join(current_words))
                    
                    sub_chunks.extend([chunk for chunk in word_chunks if len(chunk) >= self.min_chunk_size])
                    current_chunk = ""
                else:
                    # Include heading context in new chunk if available
                    current_chunk = (heading_context + ". " + sentence) if heading_context else sentence
        
        # Add final chunk
        if len(current_chunk) >= self.min_chunk_size:
            sub_chunks.append(current_chunk.strip())
        elif sub_chunks and current_chunk and len(current_chunk) > 20:
            # Merge small final chunk with previous if not too small
            sub_chunks[-1] += ". " + current_chunk
        
        return sub_chunks
    
    def _add_enhanced_overlap(self, chunks: List[str], overlap_sentences: int = 2) -> List[str]:
        """Add enhanced sentence overlap between chunks for better context preservation."""
        if len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = [chunks[0]]  # First chunk stays the same
        
        for i in range(1, len(chunks)):
            # Get last sentences from previous chunk for context
            prev_sentences = self.patterns['sentence_endings'].split(chunks[i-1])
            prev_sentences = [s.strip() for s in prev_sentences if s.strip()]
            
            # Take last N sentences for overlap
            overlap_text = ""
            if len(prev_sentences) > overlap_sentences:
                overlap_text = ". ".join(prev_sentences[-overlap_sentences:]) + ". "
            elif prev_sentences:
                # Use all available sentences if fewer than desired overlap
                overlap_text = ". ".join(prev_sentences) + ". "
            
            # Combine overlap with current chunk, ensuring we don't exceed max size
            current_chunk = chunks[i]
            if overlap_text:
                combined = overlap_text + current_chunk
                if len(combined) <= self.max_chunk_size * 1.1:  # Allow slight overflow for context
                    current_chunk = combined
            
            overlapped_chunks.append(current_chunk)
        
        return overlapped_chunks
    
    def _split_large_chunk(self, chunk_text: str) -> List[str]:
        """Split a large chunk into smaller pieces while preserving meaning."""
        sentences = self.patterns['sentence_endings'].split(chunk_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        sub_chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            potential_length = len(current_chunk) + len(sentence) + 1
            
            if potential_length <= self.max_chunk_size:
                current_chunk += (" " + sentence) if current_chunk else sentence
            else:
                if len(current_chunk) >= self.min_chunk_size:
                    sub_chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if len(current_chunk) >= self.min_chunk_size:
            sub_chunks.append(current_chunk.strip())
        elif sub_chunks and current_chunk:
            sub_chunks[-1] += " " + current_chunk
        
        return sub_chunks
    
    def _chunk_by_sentences(self, content: str, preserve_context: bool = True) -> List[str]:
        """Original sentence-based chunking method."""
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
    
    def combine_keywords(self, original_keywords: List[str], generated_keywords: List[str], max_keywords: int = 10) -> List[str]:
        """
        Combine original and generated keywords with priority to original ones.
        
        Args:
            original_keywords: Keywords from HTML meta tags (author-provided)
            generated_keywords: Keywords extracted from content
            max_keywords: Maximum number of keywords to return
            
        Returns:
            Combined list of keywords with original keywords prioritized
        """
        combined = []
        
        # Normalize inputs
        if isinstance(original_keywords, str):
            original_keywords = [kw.strip() for kw in original_keywords.split(',') if kw.strip()]
        if isinstance(generated_keywords, str):
            generated_keywords = [kw.strip() for kw in generated_keywords.split(',') if kw.strip()]
        
        # Clean and normalize keywords
        def clean_keyword(kw):
            return kw.lower().strip()
        
        # Add original keywords first (highest priority)
        seen = set()
        for kw in original_keywords or []:
            cleaned = clean_keyword(kw)
            if cleaned and len(cleaned) > 2 and cleaned not in seen:
                combined.append(kw.strip())  # Keep original case
                seen.add(cleaned)
                if len(combined) >= max_keywords:
                    return combined
        
        # Add generated keywords to fill remaining slots
        for kw in generated_keywords or []:
            cleaned = clean_keyword(kw)
            if cleaned and len(cleaned) > 2 and cleaned not in seen:
                combined.append(kw.strip())
                seen.add(cleaned)
                if len(combined) >= max_keywords:
                    return combined
        
        return combined
    
    def extract_keywords(self, content: str, max_keywords: int = 20, use_advanced_nlp: bool = True) -> List[str]:
        """Extract important keywords using multiple techniques including NER and topic modeling."""
        if not content:
            return []
        
        keywords = set()
        
        # Method 1: Enhanced frequency-based extraction
        freq_keywords = self._extract_frequency_keywords(content, max_keywords // 2)
        keywords.update(freq_keywords)
        
        # Method 2: Named Entity Recognition (if available)
        if use_advanced_nlp:
            ner_keywords = self._extract_ner_keywords(content)
            keywords.update(ner_keywords)
            
            # Method 3: Topic modeling keywords
            topic_keywords = self._extract_topic_keywords(content)
            keywords.update(topic_keywords)
        
        # Convert to list and return top keywords by relevance
        return list(keywords)[:max_keywords]
    
    def _extract_frequency_keywords(self, content: str, max_keywords: int = 10) -> List[str]:
        """Enhanced frequency-based keyword extraction."""
        # Extract words (minimum 3 characters, exclude common patterns)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        
        # Filter out stop words and common meaningless patterns
        filtered_words = []
        for word in words:
            if (word not in self.stop_words and 
                len(word) >= 4 and
                not word.isdigit() and
                not re.match(r'^(www|http|html|css|js|php|com|org|net|amp|gt|lt)$', word) and
                not re.match(r'^(nbsp|quot|copy|reg|trade|hellip|ndash|mdash)$', word) and
                not word.endswith(('ing', 'ed', 'er', 'est', 'ly', 's')) or len(word) >= 6):
                filtered_words.append(word)
        
        # Count frequency and prioritize longer, more meaningful words
        word_freq = Counter(filtered_words)
        
        # Score words by frequency and length
        word_scores = {}
        for word, freq in word_freq.items():
            score = freq
            
            # Bonus for longer words
            if len(word) >= 8:
                score *= 2.0
            elif len(word) >= 6:
                score *= 1.8
            elif len(word) >= 5:
                score *= 1.4
            elif len(word) >= 4:
                score *= 1.1
            
            # Bonus for technical terms
            if re.search(r'[0-9]|[A-Z]', word):
                score *= 1.3
            
            word_scores[word] = score
        
        # Return top scored words
        sorted_words = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
        return [word for word, score in sorted_words[:max_keywords]]
    
    def _extract_ner_keywords(self, content: str) -> List[str]:
        """Extract named entities as keywords using spaCy (if available)."""
        try:
            import spacy
            
            # Try to load English model
            try:
                nlp = spacy.load("en_core_web_sm")
            except OSError:
                # Fallback to basic model or skip NER
                logger.debug("spaCy English model not available, skipping NER")
                return []
            
            # Process content
            doc = nlp(content[:1000])  # Limit to first 1000 chars for performance
            
            # Extract entities
            entities = []
            for ent in doc.ents:
                if (ent.label_ in ['PERSON', 'ORG', 'PRODUCT', 'EVENT', 'WORK_OF_ART', 'LAW'] and
                    len(ent.text) >= 3 and
                    not ent.text.lower() in self.stop_words):
                    entities.append(ent.text.lower().strip())
            
            return list(set(entities))[:5]  # Return top 5 unique entities
            
        except ImportError:
            logger.debug("spaCy not available, skipping NER extraction")
            return []
        except Exception as e:
            logger.debug(f"NER extraction failed: {e}")
            return []
    
    def _extract_topic_keywords(self, content: str) -> List[str]:
        """Extract topic-based keywords using centralized configuration."""
        try:
            content_lower = content.lower()
            topic_keywords = []
            
            # Use centralized topic patterns from config
            topic_patterns = PipelineConfig.CATEGORY_KEYWORDS
            
            for topic, keywords in topic_patterns.items():
                matches = sum(1 for keyword in keywords if keyword in content_lower)
                if matches >= 2:  # Topic is relevant if at least 2 keywords match
                    # Add the most specific keywords from this topic
                    for keyword in keywords:
                        if keyword in content_lower and len(keyword) >= 5:
                            topic_keywords.append(keyword)
                            if len(topic_keywords) >= 5:
                                break
                    if len(topic_keywords) >= 5:
                        break
            
            return topic_keywords[:5]
            
        except Exception as e:
            logger.debug(f"Topic keyword extraction failed: {e}")
            return []
    
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
