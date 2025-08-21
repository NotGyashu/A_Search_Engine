"""
Document Processor - Main Processing Orchestrator

Coordinates all processing modules to transform raw HTML documents
into optimized, searchable content for OpenSearch indexing.
"""

import hashlib
import time
import logging
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
from extractor import ContentExtractor
from cleaner import ContentCleaner
from scorer import ContentScorer
from language_detector import LanguageDetector
from enhanced_metadata_extractor import EnhancedMetadataExtractor

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Document:
    """Represents the metadata for a single document (optimized)."""
   
    document_id: str
    url: str
    title: str
    domain: str
    description: str
    content_type: str
    categories: List[str]
    keywords: List[str]
    canonical_url: Optional[str] = None
    published_date: Optional[str] = None
    modified_date: Optional[str] = None
    author_info: Optional[Dict[str, Any]] = None
    structured_data: Optional[Dict[str, Any]] = None
    images: Optional[List[Dict[str, Any]]] = None
    table_of_contents: Optional[List[Dict[str, Any]]] = None
    semantic_info: Optional[Dict[str, Any]] = None
    icons: Optional[Dict[str, str]] = None


@dataclass(slots=True)
class DocumentChunk:
    """Represents an indexable chunk of a document (optimized)."""

    chunk_id: str
    document_id: str
    text_chunk: str
    headings: str
    domain_score: float
    quality_score: float
    word_count: int
    content_categories: List[str]
    keywords: List[str]


class DocumentProcessor:
    """Advanced document processing with modular components and optimized extraction."""
    
    def __init__(self, min_content_length: int = 400, max_chunk_size: int = 2000):
        self.min_content_length = min_content_length
        self.max_chunk_size = max_chunk_size
        
        # Initialize processing modules with improved settings
        self.extractor = ContentExtractor()
        self.cleaner = ContentCleaner(max_chunk_size=max_chunk_size, min_chunk_size=400)
        self.scorer = ContentScorer()
        self.enhanced_extractor = EnhancedMetadataExtractor()
        
        # Processing statistics
        self.stats = {
            'processed_count': 0,
            'successful_count': 0,
            'failed_count': 0,
            'skipped_count': 0,
            'total_processing_time': 0,
            'content_too_short': 0,
            'language_filtered': 0,
            'extraction_failed': 0
        }
    
    def _extract_all_from_soup(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """
        ULTRA-OPTIMIZED: Single-pass HTML extraction
        Extract ALL data in one traversal, then process without soup
        """
        if not soup:
            return {}

        try:
            # SINGLE-PASS RAW EXTRACTION
            raw_data = self._single_pass_raw_extraction(soup, base_url)
            
            # PROCESS RAW DATA (NO MORE SOUP OPERATIONS)
            processed_data = self._process_raw_data(raw_data, base_url)
            
            return processed_data
            
        except Exception as e:
            logger.warning(f"Error in ultra-optimized extraction for {base_url}: {e}")
            return {}
    
    def _single_pass_raw_extraction(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """Extract all raw data in a single HTML traversal."""
        raw_data = {
            'meta_tags': {},
            'script_tags': [],
            'links': [],
            'headings': [],
            'images': [],
            'tables': [],
            'text_content': '',
            'title': '',
            'lang': '',
            'author_elements': [],
            'date_elements': [],
            'structured_data': {'json_ld': [], 'microdata': [], 'rdfa': []}
        }
        
        # Extract title and language at document level
        if soup.title:
            raw_data['title'] = soup.title.get_text(strip=True)
        
        html_tag = soup.find('html')
        if html_tag:
            raw_data['lang'] = html_tag.get('lang', '')
        
        # Single traversal to extract ALL data
        for element in soup.find_all():
            tag_name = element.name.lower()
            
            # Meta tags
            if tag_name == 'meta':
                attrs = element.attrs
                content = attrs.get('content', '')
                if content:
                    # Store all meta attributes for later processing
                    key = None
                    if 'name' in attrs:
                        key = f"name:{attrs['name']}"
                    elif 'property' in attrs:
                        key = f"property:{attrs['property']}"
                    elif 'http-equiv' in attrs:
                        key = f"http-equiv:{attrs['http-equiv']}"
                    
                    if key:
                        raw_data['meta_tags'][key] = content
            
            # JSON-LD and scripts
            elif tag_name == 'script':
                script_type = element.get('type', '').lower()
                if 'json' in script_type or 'ld' in script_type:
                    try:
                        script_content = element.get_text(strip=True)
                        if script_content:
                            import json
                            parsed = json.loads(script_content)
                            raw_data['structured_data']['json_ld'].append(parsed)
                    except:
                        pass
            
            # Links (canonical, etc.)
            elif tag_name == 'link':
                rel = element.get('rel', [])
                if isinstance(rel, str):
                    rel = [rel]
                href = element.get('href', '')
                if href:
                    raw_data['links'].append({
                        'rel': rel,
                        'href': href,
                        'type': element.get('type', ''),
                        'title': element.get('title', '')
                    })
            
            # Headings for TOC
            elif tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                raw_data['headings'].append({
                    'level': int(tag_name[1]),
                    'text': element.get_text(strip=True),
                    'id': element.get('id', '')
                })
            
            # Images
            elif tag_name == 'img':
                src = element.get('src', '')
                if src:
                    raw_data['images'].append({
                        'src': src,
                        'alt': element.get('alt', ''),
                        'title': element.get('title', ''),
                        'width': element.get('width', ''),
                        'height': element.get('height', '')
                    })
            
            # Author-related elements
            elif any(cls in element.get('class', []) for cls in ['author', 'byline', 'writer']) or \
                 element.get('rel') == 'author' or \
                 element.get('itemprop') in ['author', 'creator']:
                raw_data['author_elements'].append({
                    'tag': tag_name,
                    'text': element.get_text(strip=True),
                    'class': element.get('class', []),
                    'itemprop': element.get('itemprop', ''),
                    'href': element.get('href', '')
                })
            
            # Date-related elements
            elif 'time' in tag_name or \
                 any(cls in element.get('class', []) for cls in ['date', 'published', 'updated']) or \
                 element.get('itemprop') in ['datePublished', 'dateModified', 'dateCreated']:
                raw_data['date_elements'].append({
                    'tag': tag_name,
                    'text': element.get_text(strip=True),
                    'datetime': element.get('datetime', ''),
                    'class': element.get('class', []),
                    'itemprop': element.get('itemprop', '')
                })
        
        # Extract clean text content
        raw_data['text_content'] = soup.get_text(separator=' ', strip=True)
        
        return raw_data
    
    def _process_raw_data(self, raw_data: Dict[str, Any], base_url: str) -> Dict[str, Any]:
        """Process raw extracted data without any soup operations."""
        processed = {
            'page_metadata': self._process_page_metadata(raw_data),
            'structured_data': raw_data['structured_data'],
            'canonical_url': self._process_canonical_url(raw_data, base_url),
            'images': self._process_image_data(raw_data, base_url),
            'table_of_contents': self._process_table_of_contents(raw_data),
            'author_info': self._process_author_info(raw_data),
            'semantic_info': self._process_semantic_info(raw_data),
        }
        
        # Process dates
        date_info = self._process_publication_dates(raw_data)
        processed['published_date'] = date_info.get('published_date')
        processed['modified_date'] = date_info.get('modified_date')
        
        return processed
    
    def _process_page_metadata(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process basic page metadata from raw data."""
        meta_tags = raw_data['meta_tags']
        
        # Description priority order
        description = (
            meta_tags.get('property:og:description') or
            meta_tags.get('name:description') or
            meta_tags.get('name:twitter:description') or
            ''
        )
        
        # Keywords
        keywords = meta_tags.get('name:keywords', '')
        
        # Other metadata
        return {
            'title': raw_data['title'],
            'description': description,
            'keywords': keywords.split(',') if keywords else [],
            'language': raw_data['lang'],
            'og_title': meta_tags.get('property:og:title', ''),
            'og_type': meta_tags.get('property:og:type', ''),
            'twitter_card': meta_tags.get('name:twitter:card', ''),
            'robots': meta_tags.get('name:robots', ''),
            'viewport': meta_tags.get('name:viewport', '')
        }
    
    def _process_publication_dates(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process publication dates from raw meta data."""
        meta_tags = raw_data['meta_tags']
        dates = {}
        
        # Publication date patterns (highest priority first)
        pub_patterns = [
            'property:article:published_time',
            'name:article:published_time', 
            'name:publication_date',
            'name:date',
            'name:pubdate',
            'name:DC.Date'
        ]
        
        for pattern in pub_patterns:
            if pattern in meta_tags and not dates.get('published_date'):
                date_str = meta_tags[pattern]
                parsed_date = self._parse_date_string(date_str)
                if parsed_date:
                    dates['published_date'] = parsed_date
                    break
        
        # Modified date patterns
        mod_patterns = [
            'property:article:modified_time',
            'name:article:modified_time',
            'name:last-modified',
            'name:DC.Date.Modified'
        ]
        
        for pattern in mod_patterns:
            if pattern in meta_tags and not dates.get('modified_date'):
                date_str = meta_tags[pattern]
                parsed_date = self._parse_date_string(date_str)
                if parsed_date:
                    dates['modified_date'] = parsed_date
                    break
        
        # Also check structured data
        for json_ld in raw_data['structured_data']['json_ld']:
            if not dates.get('published_date'):
                for field in ['datePublished', 'publishedDate', 'dateCreated']:
                    if field in json_ld:
                        parsed_date = self._parse_date_string(json_ld[field])
                        if parsed_date:
                            dates['published_date'] = parsed_date
                            break
            
            if not dates.get('modified_date'):
                for field in ['dateModified', 'modifiedDate', 'dateUpdated']:
                    if field in json_ld:
                        parsed_date = self._parse_date_string(json_ld[field])
                        if parsed_date:
                            dates['modified_date'] = parsed_date
                            break
        
        return dates
    
    def _process_canonical_url(self, raw_data: Dict[str, Any], base_url: str) -> str:
        """Extract canonical URL from raw link data."""
        for link in raw_data['links']:
            if 'canonical' in link['rel']:
                href = link['href']
                if href.startswith('http'):
                    return href
                else:
                    from urllib.parse import urljoin
                    return urljoin(base_url, href)
        return base_url
    
    def _process_image_data(self, raw_data: Dict[str, Any], base_url: str) -> List[Dict[str, Any]]:
        """Process image data from raw extraction."""
        images = []
        from urllib.parse import urljoin
        
        for img in raw_data['images'][:10]:  # Limit to first 10 images
            src = img['src']
            if not src.startswith('http'):
                src = urljoin(base_url, src)
            
            images.append({
                'src': src,
                'alt': img['alt'],
                'title': img['title']
            })
        
        return images
    
    def _process_table_of_contents(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate table of contents from headings."""
        toc = []
        for heading in raw_data['headings']:
            if heading['text']:  # Only include headings with text
                toc.append({
                    'level': heading['level'],
                    'text': heading['text'],
                    'anchor': heading['id'] or heading['text'].lower().replace(' ', '-')
                })
        return toc
    
    def _process_author_info(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process author information from raw data."""
        author_info = {'name': '', 'url': '', 'bio': ''}
        
        # Check meta tags first
        meta_tags = raw_data['meta_tags']
        author_name = (
            meta_tags.get('name:author') or
            meta_tags.get('property:article:author') or
            meta_tags.get('name:twitter:creator') or
            ''
        )
        
        if author_name:
            author_info['name'] = author_name
        
        # Check author elements
        for elem in raw_data['author_elements']:
            if elem['text'] and not author_info['name']:
                author_info['name'] = elem['text']
            if elem['href'] and not author_info['url']:
                author_info['url'] = elem['href']
        
        return author_info
    
    def _process_semantic_info(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process semantic information from raw data."""
        return {
            'headings_count': len(raw_data['headings']),
            'images_count': len(raw_data['images']),
            'has_structured_data': len(raw_data['structured_data']['json_ld']) > 0,
            'word_count': len(raw_data['text_content'].split()) if raw_data['text_content'] else 0
        }
    
    def _parse_date_string(self, date_str: str) -> str:
        """Parse date string and return ISO format."""
        if not date_str:
            return ''
        
        try:
            from dateutil.parser import parse
            parsed = parse(date_str)
            return parsed.isoformat()
        except:
            return date_str  # Return original if parsing fails
    
    def _score_description_quality(self, description: str, source_type: str) -> float:
        """Score description quality based on content and source."""
        score = 0.0
        
        # Length scoring (optimal 120-300 characters)
        length = len(description)
        if 120 <= length <= 300:
            score += 3.0
        elif 80 <= length <= 400:
            score += 2.0
        elif 50 <= length <= 500:
            score += 1.0
        
        # Source type scoring (prefer authored content)
        source_scores = {
            'og_description': 2.5,  # Open Graph is usually well-crafted
            'meta_description': 2.0,  # Standard meta description
            'json_ld_description': 1.5,  # Structured data description
            'microdata_description': 1.0   # Microdata description
        }
        score += source_scores.get(source_type, 0.0)
        
        # Content quality indicators
        if description.count('.') >= 1:  # Has sentence structure
            score += 0.5
        
        if any(word in description.lower() for word in ['and', 'or', 'with', 'about', 'the']):
            score += 0.3  # Natural language indicators
        
        # Penalties for low-quality descriptions
        if description.lower().startswith(('click', 'welcome', 'home', 'menu')):
            score -= 1.0  # Navigation text
        
        if len(description.split()) < 5:
            score -= 1.0  # Too short
        
        if description.count(description.split()[0]) > 3:  # Repetitive
            score -= 0.5
        
        return max(0.0, score)
    
    def _determine_content_type(self, url: str, metadata: Dict) -> str:
        """Determine the content type based on URL and metadata."""
        content_type = "article"  # default
        
        # Use pre-extracted metadata instead of searching again
        page_metadata = metadata.get('page_metadata', {})
        description = page_metadata.get('description', '').lower()
        
        # Check for blog indicators
        if (any(indicator in url.lower() for indicator in ['blog', 'news', 'post']) or
            any(indicator in description for indicator in ['blog', 'post', 'article'])):
            content_type = "blog"
        
        # Check for technical content
        elif any(keyword in description for keyword in 
                ['tutorial', 'guide', 'documentation', 'api', 'code', 'programming']):
            content_type = "documentation"
        
        return content_type
    
    def process_document(self, raw_doc: Dict[str, Any]) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """
        Process a single raw document through the complete pipeline.
        REFACTORED for performance - Extract-Once, Transform-Later strategy.
        """
        start_time = time.time()
        self.stats['processed_count'] += 1
        
        try:
            # Step 1: Basic validation (fast early exits)
            url = str(raw_doc.get("url", "")).strip()
            if not url:
                logger.debug("Skipping document: No URL")
                self.stats['skipped_count'] += 1
                return None
            
            html_content = raw_doc.get("content", "")
            if not html_content or len(html_content) < 500:
                logger.debug(f"Skipping {url}: HTML too short ({len(html_content)} chars)")
                self.stats['content_too_short'] += 1
                return None
                
            # Step 2: Language filtering (optimized early exit)
            if not LanguageDetector.is_english(html_content, url):
                self.stats['language_filtered'] += 1
                return None
            
            # Step 3: Single-pass HTML parsing
            soup = None
            try:
                soup = BeautifulSoup(html_content, "lxml")
            except Exception as e:
                logger.warning(f"Failed to parse HTML for {url}: {e}")
                self.stats['failed_count'] += 1
                return None

            # Step 4: ONE-TIME Coordinated Extraction
            # This is the core optimization. All data is pulled from `soup` here.
            all_extracted_data = self._extract_all_from_soup(soup, url)
            
            # Use extractor for main content but pass soup to avoid re-parsing
            main_content_data = self.extractor.extract_content(
                html_content, url, raw_doc, soup=soup
            )
            
            main_content = main_content_data.get('main_content', '')
            if not main_content or len(main_content) < self.min_content_length:
                logger.debug(f"Skipping {url}: Content too short ({len(main_content)} chars)")
                self.stats['content_too_short'] += 1
                return None

            # --- From this point on, we NO LONGER touch the `soup` object ---
            # All subsequent operations work with extracted strings and dictionaries

            # Step 5: Metadata Consolidation (working with extracted dictionaries)
            page_meta = all_extracted_data.get('page_metadata', {})
            structured_data = all_extracted_data.get('structured_data', {})
            json_ld_data = structured_data.get('json_ld', [])
            
            # Title selection with simplified logic
            crawler_title = raw_doc.get('title', '') if raw_doc.get('title') not in ['N/A', 'n/a', 'None', 'null', ''] else ''
            title = (
                page_meta.get('og_title') or 
                (json_ld_data[0].get('headline') if json_ld_data else None) or
                page_meta.get('title') or 
                crawler_title or 
                "Untitled Document"
            )
            
            # Clean and validate title
            if title and title.strip() and not self._is_generic_title(title) and len(title) >= 3:
                title = title.strip()
            else:
                title = "Untitled Document"
                
            domain = raw_doc.get('domain', '') or self._extract_domain(url)
            headings = all_extracted_data.get('table_of_contents', [])

            # Step 6: Content Cleaning (on extracted string only)
            cleaned_content = self.cleaner.clean_text(main_content)
            if not cleaned_content:
                logger.debug(f"Skipping {url}: Content cleaning resulted in empty text")
                self.stats['content_too_short'] += 1
                return None
            
            # Step 7: Description Selection (from pre-extracted metadata)
            og_description = page_meta.get('og_description')
            meta_description = page_meta.get('description')
            json_ld_description = json_ld_data[0].get('description') if json_ld_data else None
            
            description = None
            if og_description and len(og_description.strip()) > 10:
                description = self.cleaner._clean_snippet_text(og_description.strip())
            elif meta_description and len(meta_description.strip()) > 10:
                description = self.cleaner._clean_snippet_text(meta_description.strip())
            elif json_ld_description and len(json_ld_description.strip()) > 10:
                description = self.cleaner._clean_snippet_text(json_ld_description.strip())
            
            if not description:
                description = self.cleaner.create_description(cleaned_content)
            
            # Step 8: Keyword and Category Extraction (simplified)
            original_keywords = page_meta.get('keywords', [])
            generated_keywords = self.cleaner.extract_keywords(cleaned_content)
            combined_keywords = self.cleaner.combine_keywords(original_keywords, generated_keywords, max_keywords=10)
            
            # Use simplified metadata for categories
            metadata_for_categories = {
                'title': title,
                'description': description,
                'author_info': all_extracted_data.get('author_info', {}),
                'structured_data': structured_data
            }
            categories = self.scorer.get_content_categories(cleaned_content, metadata_for_categories)
            
            # Step 9: Scoring (optimized)
            content_type = self._determine_content_type(url, all_extracted_data)
            domain_score = self.scorer.calculate_domain_score(url)
            quality_score = self.scorer.calculate_content_quality_score(
                cleaned_content, metadata_for_categories, {}, html_content=None  # Pass None to avoid re-parsing
            )

            # Step 10: Create Document Record
            document_id = hashlib.md5(url.encode()).hexdigest()
            document = Document(
                document_id=document_id,
                url=url,
                title=title,
                domain=domain,
                description=description,
                content_type=content_type,
                categories=categories[:3],
                keywords=combined_keywords,
                canonical_url=all_extracted_data.get('canonical_url'),
                published_date=all_extracted_data.get('published_date'),
                modified_date=all_extracted_data.get('modified_date'),
                author_info=all_extracted_data.get('author_info'),
                structured_data=structured_data,
                images=all_extracted_data.get('images'),
                table_of_contents=headings,
                semantic_info=all_extracted_data.get('semantic_info'),
                icons=page_meta.get('icons')
            )

            # Step 11: Chunking (on cleaned string only)
            text_chunks = self.cleaner.intelligent_chunking(
                cleaned_content, 
                preserve_context=True
            )
            if not text_chunks:
                self.stats['content_too_short'] += 1
                return None

            # Enhanced chunk quality filtering with size validation
            quality_chunks = []
            max_chunk_chars = 8000  # Limit chunk size to prevent indexing issues
            
            for chunk in text_chunks:
                # Validate chunk size and quality
                word_count = len(chunk.split())
                char_count = len(chunk)
                min_words = 50 if content_type in ['article', 'blog', 'documentation'] else 30
                
                # Apply both word count and character count limits
                if word_count >= min_words and char_count <= max_chunk_chars:
                    quality_chunks.append(chunk)
                elif char_count > max_chunk_chars:
                    # If chunk is too large, try to split it further
                    sentences = chunk.split('. ')
                    current_chunk = ""
                    
                    for sentence in sentences:
                        test_chunk = current_chunk + sentence + ". "
                        if len(test_chunk) <= max_chunk_chars:
                            current_chunk = test_chunk
                        else:
                            if current_chunk.strip() and len(current_chunk.split()) >= min_words:
                                quality_chunks.append(current_chunk.strip())
                            current_chunk = sentence + ". "
                    
                    # Add remaining content if it meets criteria
                    if current_chunk.strip() and len(current_chunk.split()) >= min_words:
                        quality_chunks.append(current_chunk.strip())
            
            if not quality_chunks:
                self.stats['content_too_short'] += 1
                return None

            # Step 12: Create Chunk Records (optimized)
            document_chunks = []
            formatted_headings = self.cleaner.format_headings_for_index(headings)
            
            for i, chunk in enumerate(quality_chunks):
                chunk_id = hashlib.md5(f"{document_id}_chunk_{i}".encode()).hexdigest()
                chunk_keywords = self.cleaner.extract_keywords(chunk, max_keywords=8)
                
                # Combine chunk-specific keywords with document keywords
                chunk_combined_keywords = list(dict.fromkeys(
                    chunk_keywords + combined_keywords[:5]
                ))[:10]
                
                chunk_word_count = len(chunk.split())
                
                # Use document-level quality score for performance (avoids re-calculation)
                chunk_quality_score = quality_score
                
                doc_chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    text_chunk=chunk,
                    headings=formatted_headings,
                    domain_score=domain_score,
                    quality_score=chunk_quality_score,
                    word_count=chunk_word_count,
                    content_categories=categories,
                    keywords=chunk_combined_keywords
                )
                document_chunks.append(doc_chunk)
            
            # Step 13: Performance logging (reduced frequency)
            processing_time = time.time() - start_time
            self.stats['successful_count'] += 1
            self.stats['total_processing_time'] += processing_time
            
            # Only log significant documents to reduce I/O overhead
            if len(quality_chunks) > 5 or processing_time > 1.0:
                raw_size_kb = len(html_content.encode("utf-8")) / 1024
                clean_size_kb = len(cleaned_content.encode("utf-8")) / 1024
                logger.info(
                    f"[PROCESSED] {url} | "
                    f"Raw: {raw_size_kb:.1f}KB → Clean: {clean_size_kb:.1f}KB → "
                    f"Chunks: {len(quality_chunks)} | Time: {processing_time:.2f}s"
                )
            
            return {
                "documents": [asdict(document)],
                "chunks": [asdict(chunk) for chunk in document_chunks]
            }
            
        except Exception as e:
            self.stats['failed_count'] += 1
            processing_time = time.time() - start_time
            self.stats['total_processing_time'] += processing_time
            logger.error(f"Error processing document {url}: {e}")
            return None
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL as fallback."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return "unknown.domain"
    
    def _is_generic_title(self, title: str) -> bool:
        """Check if title is too generic or templated."""
        generic_patterns = [
            'untitled', 'home', 'index', 'main', 'welcome',
            'page not found', '404', 'error', 'loading'
        ]
        
        title_lower = title.lower()
        return any(pattern in title_lower for pattern in generic_patterns)
    
    def process_batch(self, documents: List[Dict[str, Any]], 
                     write_output: bool = True, 
                     output_dir: str = "processed_output",
                     batch_name: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """Process a batch of documents efficiently."""
        logger.info(f"Processing batch of {len(documents)} documents")
        
        all_documents = []
        all_chunks = []
        
        for raw_doc in documents:
            result = self.process_document(raw_doc)
            if result:
                all_documents.extend(result["documents"])
                all_chunks.extend(result["chunks"])
        
        logger.info(
            f"Batch processing complete: "
            f"{len(all_documents)} documents, {len(all_chunks)} chunks created"
        )
        
        # Write processed data for quality inspection
        if write_output and (all_documents or all_chunks):
            self.write_processed_documents(
                all_documents, 
                all_chunks, 
                output_dir=output_dir,
                batch_name=batch_name
            )
        
        return {
            "documents": all_documents,
            "chunks": all_chunks
        }
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get detailed processing statistics."""
        total_processed = self.stats['processed_count']
        avg_processing_time = (
            self.stats['total_processing_time'] / max(total_processed, 1)
        )
        
        return {
            **self.stats,
            'success_rate': (self.stats['successful_count'] / max(total_processed, 1)) * 100,
            'avg_processing_time_seconds': avg_processing_time,
            'documents_per_second': 1 / max(avg_processing_time, 0.001)
        }
    
    def reset_stats(self):
        """Reset processing statistics."""
        self.stats = {
            'processed_count': 0,
            'successful_count': 0,
            'failed_count': 0,
            'skipped_count': 0,
            'total_processing_time': 0,
            'language_filtered': 0,
            'content_too_short': 0,
            'extraction_failed': 0
        }

    def write_processed_documents(self, 
                                documents: List[Dict[str, Any]], 
                                chunks: List[Dict[str, Any]], 
                                output_dir: str = "processed_output",
                                batch_name: str = None) -> Dict[str, str]:
        """
        Write processed documents and chunks to files for quality inspection.
        
        Args:
            documents: List of processed document records
            chunks: List of processed chunk records  
            output_dir: Directory to write files to
            batch_name: Optional batch identifier for filename
            
        Returns:
            Dict with paths to written files
        """
        try:
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate timestamp for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            batch_suffix = f"_{batch_name}" if batch_name else ""
            
            # Prepare output data with quality metrics
            output_data = {
                "processing_metadata": {
                    "timestamp": timestamp,
                    "total_documents": len(documents),
                    "total_chunks": len(chunks),
                    "batch_name": batch_name,
                    "processing_stats": self.get_processing_stats()
                },
                "documents": documents,
                "chunks": chunks,
                "quality_summary": self._generate_quality_summary(documents, chunks)
            }
            
            # Write comprehensive output file
            # COMMENTED OUT: JSON writing to save disk space and improve performance
            main_file = output_path / f"processed_data_{timestamp}{batch_suffix}.json"
            with open(main_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
            
            # Write human-readable summary
            summary_file = output_path / f"quality_report_{timestamp}{batch_suffix}.txt"
            self._write_quality_report(summary_file, output_data)
            
            # Write sample documents for manual inspection (increased to 500 samples)
            sample_file = output_path / f"sample_documents_{timestamp}{batch_suffix}.txt"
            self._write_sample_documents(sample_file, documents, chunks, sample_size=500)
            
            file_paths = {
                # "main_file": str(main_file),  # COMMENTED OUT
                "summary_file": str(summary_file), 
                "sample_file": str(sample_file)
            }
            
            logger.info(f"📁 Processed documents written to:")
            # logger.info(f"   📄 Main data: {main_file}")  # COMMENTED OUT
            logger.info(f"   📊 Quality report: {summary_file}")
            logger.info(f"   🔍 Sample documents: {sample_file}")
            
            return file_paths
            
        except Exception as e:
            logger.error(f"Failed to write processed documents: {e}")
            return {}
    
    def _generate_quality_summary(self, documents: List[Dict[str, Any]], 
                                chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate quality metrics summary for the processed data."""
        if not documents:
            return {"error": "No documents to analyze"}
        
        # Document quality metrics
        doc_metrics = {
            "avg_title_length": sum(len(d.get('title', '')) for d in documents) / len(documents),
            "domains": list(set(d.get('domain', '') for d in documents)),
            "content_types": list(set(d.get('content_type', '') for d in documents)),
            "avg_keywords_per_doc": sum(len(d.get('keywords', [])) for d in documents) / len(documents),
            "documents_with_categories": sum(1 for d in documents if d.get('categories')),
        }
        
        # Chunk quality metrics
        if chunks:
            chunk_metrics = {
                "avg_chunk_length": sum(len(c.get('text_chunk', '')) for c in chunks) / len(chunks),
                "avg_word_count": sum(c.get('word_count', 0) for c in chunks) / len(chunks),
                "avg_quality_score": sum(c.get('quality_score', 0) for c in chunks) / len(chunks),
                "avg_domain_score": sum(c.get('domain_score', 0) for c in chunks) / len(chunks),
                "chunks_per_document": len(chunks) / len(documents)
            }
        else:
            chunk_metrics = {"error": "No chunks to analyze"}
        
        return {
            "document_metrics": doc_metrics,
            "chunk_metrics": chunk_metrics
        }
    
    def _write_quality_report(self, file_path: Path, data: Dict[str, Any]):
        """Write a human-readable quality report."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("🔍 DOCUMENT PROCESSING QUALITY REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            # Processing metadata
            meta = data["processing_metadata"]
            f.write(f"📊 Processing Summary:\n")
            f.write(f"   Timestamp: {meta['timestamp']}\n")
            f.write(f"   Documents: {meta['total_documents']}\n")
            f.write(f"   Chunks: {meta['total_chunks']}\n")
            f.write(f"   Batch: {meta.get('batch_name', 'N/A')}\n\n")
            
            # Processing stats
            stats = meta["processing_stats"]
            f.write(f"⚡ Performance Metrics:\n")
            f.write(f"   Success Rate: {stats.get('success_rate', 0):.1f}%\n")
            f.write(f"   Avg Processing Time: {stats.get('avg_processing_time_seconds', 0):.2f}s\n")
            f.write(f"   Documents/Second: {stats.get('documents_per_second', 0):.1f}\n\n")
            
            # Quality summary
            quality = data["quality_summary"]
            if "document_metrics" in quality:
                doc_m = quality["document_metrics"]
                f.write(f"📄 Document Quality:\n")
                f.write(f"   Avg Title Length: {doc_m.get('avg_title_length', 0):.1f} chars\n")
                f.write(f"   Unique Domains: {len(doc_m.get('domains', []))}\n")
                f.write(f"   Content Types: {', '.join(doc_m.get('content_types', []))}\n")
                f.write(f"   Avg Keywords/Doc: {doc_m.get('avg_keywords_per_doc', 0):.1f}\n")
                f.write(f"   Docs with Categories: {doc_m.get('documents_with_categories', 0)}\n\n")
            
            if "chunk_metrics" in quality:
                chunk_m = quality["chunk_metrics"]
                if "error" not in chunk_m:
                    f.write(f"📝 Chunk Quality:\n")
                    f.write(f"   Avg Chunk Length: {chunk_m.get('avg_chunk_length', 0):.0f} chars\n")
                    f.write(f"   Avg Word Count: {chunk_m.get('avg_word_count', 0):.0f} words\n")
                    f.write(f"   Avg Quality Score: {chunk_m.get('avg_quality_score', 0):.2f}\n")
                    f.write(f"   Avg Domain Score: {chunk_m.get('avg_domain_score', 0):.2f}\n")
                    f.write(f"   Chunks per Document: {chunk_m.get('chunks_per_document', 0):.1f}\n\n")
            
            # Domain breakdown
            if "document_metrics" in quality and quality["document_metrics"].get("domains"):
                f.write(f"🌐 Domain Breakdown:\n")
                domains = quality["document_metrics"]["domains"]
                for domain in sorted(domains):
                    if domain:
                        f.write(f"   - {domain}\n")
                f.write("\n")
    
    def _write_sample_documents(self, file_path: Path, documents: List[Dict[str, Any]], 
                              chunks: List[Dict[str, Any]], sample_size: int = 500):
        """Write sample documents for manual inspection."""
        with open(file_path, 'w', encoding='utf-8') as f:
            total_docs = len(documents)
            actual_sample_size = min(sample_size, total_docs)
            
            f.write("🔍 SAMPLE PROCESSED DOCUMENTS\n")
            f.write("=" * 40 + "\n")
            f.write(f"Showing {actual_sample_size} out of {total_docs} total documents\n")
            f.write("=" * 40 + "\n\n")
            
            # Sample documents
            for i, doc in enumerate(documents[:actual_sample_size]):
                f.write(f"📄 DOCUMENT {i+1}\n")
                f.write("-" * 20 + "\n")
                f.write(f"URL: {doc.get('url', 'N/A')}\n")
                f.write(f"Title: {doc.get('title', 'N/A')}\n")
                f.write(f"Domain: {doc.get('domain', 'N/A')}\n")
                f.write(f"Content Type: {doc.get('content_type', 'N/A')}\n")
                f.write(f"Categories: {', '.join(doc.get('categories', []))}\n")
                f.write(f"Keywords: {', '.join(doc.get('keywords', []))}\n")
                f.write(f"Snippet: {doc.get('description', 'N/A')[:200]}...\n")
                f.write("\n")
                
                # Related chunks
                doc_chunks = [c for c in chunks if c.get('document_id') == doc.get('document_id')]
                f.write(f"📝 CHUNKS ({len(doc_chunks)} total):\n")
                for j, chunk in enumerate(doc_chunks[:2]):  # Show first 2 chunks
                    f.write(f"  Chunk {j+1}:\n")
                    f.write(f"    Quality: {chunk.get('quality_score', 0):.2f}\n")
                    f.write(f"    Domain Score: {chunk.get('domain_score', 0):.2f}\n")
                    f.write(f"    Words: {chunk.get('word_count', 0)}\n")
                    f.write(f"    Text: {chunk.get('text_chunk', 'N/A')[:150]}...\n")
                    
                    # Parse and display headings properly
                    headings_str = chunk.get('headings', '[]')
                    try:
                        import json
                        headings_list = json.loads(headings_str) if isinstance(headings_str, str) else headings_str
                        if headings_list and isinstance(headings_list, list):
                            f.write(f"    Headings:\n")
                            for heading in headings_list[:3]:  # Show first 3 headings
                                level = heading.get('level', 1)
                                text = heading.get('text', '')
                                f.write(f"      H{level}: {text}\n")
                        else:
                            f.write(f"    Headings: None\n")
                    except:
                        f.write(f"    Headings: {headings_str[:200]}...\n")
                    f.write("\n")
                
                f.write("\n" + "="*40 + "\n\n")

    def _extract_headings_from_content(self, content: str) -> List[dict]:
        """Extract headings from content as fallback when enhanced metadata doesn't provide them."""
        import re
        headings = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for markdown-style headings
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                text = line.lstrip('#').strip()
                if text:
                    headings.append({'level': level, 'text': text})
            # Look for common heading patterns
            elif re.match(r'^[A-Z][^.]*:$', line) and len(line) < 100:
                headings.append({'level': 2, 'text': line.rstrip(':')})
                
        return headings[:10]  # Limit to 10 headings
