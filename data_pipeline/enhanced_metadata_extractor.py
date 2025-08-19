"""
Enhanced Metadata Extractor - Advanced HTML Data Extraction

Extracts structured data, canonical URLs, publication dates, images, 
table of contents, and author information from HTML content.
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
import dateutil.parser

logger = logging.getLogger(__name__)


class StructuredDataExtractor:
    """Extracts structured data from HTML using multiple formats."""
    
    def __init__(self):
        self.schema_types = {
            'Article': ['headline', 'datePublished', 'dateModified', 'author', 'description'],
            'BlogPosting': ['headline', 'datePublished', 'dateModified', 'author', 'description'],
            'NewsArticle': ['headline', 'datePublished', 'dateModified', 'author', 'description'],
            'Product': ['name', 'description', 'brand', 'price', 'rating'],
            'Event': ['name', 'startDate', 'endDate', 'location', 'description'],
            'Recipe': ['name', 'description', 'recipeIngredient', 'recipeInstructions', 'nutrition'],
            'Person': ['name', 'jobTitle', 'affiliation', 'email', 'url'],
            'Organization': ['name', 'description', 'url', 'contactPoint'],
            'SoftwareApplication': ['name', 'description', 'applicationCategory', 'operatingSystem']
        }
    
    def extract_json_ld(self, soup) -> List[Dict[str, Any]]:
        """Extract JSON-LD structured data."""
        json_ld_data = []
        
        try:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                if script.string:
                    try:
                        data = json.loads(script.string.strip())
                        if isinstance(data, list):
                            json_ld_data.extend(data)
                        else:
                            json_ld_data.append(data)
                    except json.JSONDecodeError as e:
                        logger.debug(f"Failed to parse JSON-LD: {e}")
        except Exception as e:
            logger.debug(f"JSON-LD extraction failed: {e}")
        
        return json_ld_data
    
    def extract_microdata(self, soup) -> List[Dict[str, Any]]:
        """Extract microdata from HTML."""
        microdata = []
        
        try:
            # Find elements with itemscope
            items = soup.find_all(attrs={'itemscope': True})
            for item in items:
                item_data = {}
                item_type = item.get('itemtype', '')
                if item_type:
                    item_data['@type'] = item_type.split('/')[-1]  # Get last part of URL
                
                # Extract properties
                properties = item.find_all(attrs={'itemprop': True})
                for prop in properties:
                    prop_name = prop.get('itemprop')
                    prop_value = self._extract_microdata_value(prop)
                    if prop_value:
                        item_data[prop_name] = prop_value
                
                if item_data:
                    microdata.append(item_data)
        except Exception as e:
            logger.debug(f"Microdata extraction failed: {e}")
        
        return microdata
    
    def _extract_microdata_value(self, element) -> Optional[str]:
        """Extract value from microdata property element."""
        if element.name in ['meta']:
            return element.get('content')
        elif element.name in ['time']:
            return element.get('datetime') or element.get_text(strip=True)
        elif element.name in ['img']:
            return element.get('src')
        elif element.name in ['a']:
            return element.get('href')
        else:
            return element.get_text(strip=True)
    
    def extract_rdfa(self, soup) -> List[Dict[str, Any]]:
        """Extract RDFa data from HTML."""
        rdfa_data = []
        
        try:
            # Find elements with RDFa properties
            elements = soup.find_all(attrs={'property': True})
            rdfa_item = {}
            
            for element in elements:
                prop = element.get('property')
                content = element.get('content') or element.get_text(strip=True)
                if prop and content:
                    rdfa_item[prop] = content
            
            if rdfa_item:
                rdfa_data.append(rdfa_item)
        except Exception as e:
            logger.debug(f"RDFa extraction failed: {e}")
        
        return rdfa_data


class EnhancedMetadataExtractor:
    """Enhanced metadata extraction with structured data support."""
    
    def __init__(self):
        self.structured_extractor = StructuredDataExtractor()
        
        # Date meta tag patterns
        self.date_meta_patterns = [
            'article:published_time',
            'article:modified_time',
            'og:updated_time',
            'datePublished',
            'dateModified',
            'pubdate',
            'publishdate',
            'date',
            'created',
            'modified',
            'updated'
        ]
    
    def extract_enhanced_metadata(self, html_content: str, base_url: str = None) -> Dict[str, Any]:
        """Extract comprehensive metadata from HTML content."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'lxml')
        except ImportError:
            logger.error("BeautifulSoup not available for enhanced metadata extraction")
            return {}
        
        metadata = {}
        
        # Store base URL for icon resolution
        self._base_url = base_url
        
        # FIXED: Extract basic page metadata first
        metadata['page_metadata'] = self._extract_basic_page_metadata(soup)
        
        # Extract structured data (needed for enhanced extraction)
        structured_data = self._extract_all_structured_data(soup)
        metadata['structured_data'] = structured_data
        
        # Extract canonical URL
        metadata['canonical_url'] = self._extract_canonical_url(soup, base_url)
        
        # ENHANCED: Extract publication and modification dates from multiple sources
        date_info = self._extract_publication_dates(soup, structured_data)
        metadata.update(date_info)
        
        # Extract image information
        metadata['images'] = self._extract_image_data(soup, base_url)
        
        # ENHANCED: Extract comprehensive table of contents
        metadata['table_of_contents'] = self._extract_table_of_contents(soup, base_url)
        
        # ENHANCED: Extract comprehensive author information
        metadata['author_info'] = self._extract_author_info(soup, structured_data)
        
        # Extract additional semantic information
        metadata['semantic_info'] = self._extract_semantic_info(soup)
        
        return metadata
    
    def _extract_all_structured_data(self, soup) -> Dict[str, List[Dict[str, Any]]]:
        """Extract all types of structured data."""
        return {
            'json_ld': self.structured_extractor.extract_json_ld(soup),
            'microdata': self.structured_extractor.extract_microdata(soup),
            'rdfa': self.structured_extractor.extract_rdfa(soup)
        }
    
    def _extract_basic_page_metadata(self, soup) -> Dict[str, str]:
        """Extract basic page metadata like title, description, etc. with enhanced preservation."""
        metadata = {}
        
        try:
            # Extract title from <title> tag
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
                if title:
                    metadata['title'] = title
            
            # ENHANCED: Extract description from multiple meta tag variations
            description_patterns = [
                {'name': 'description'},
                {'property': 'og:description'},
                {'name': 'twitter:description'},
                {'property': 'description'},
                {'name': 'DC.Description'},
                {'name': 'dc.description'},
                {'itemprop': 'description'}
            ]
            
            for pattern in description_patterns:
                meta_desc = soup.find('meta', attrs=pattern)
                if meta_desc and meta_desc.get('content'):
                    desc_content = meta_desc['content'].strip()
                    if desc_content and len(desc_content) > 10:  # Ensure substantial description
                        metadata['description'] = desc_content
                        break  # Use first substantial description found
            
            # ENHANCED: Extract keywords from multiple meta tag variations
            keyword_patterns = [
                {'name': 'keywords'},
                {'property': 'keywords'},
                {'name': 'news_keywords'},
                {'property': 'article:tag'},
                {'name': 'DC.Subject'},
                {'name': 'dc.subject'},
                {'itemprop': 'keywords'}
            ]
            
            all_keywords = []
            for pattern in keyword_patterns:
                meta_keywords = soup.find('meta', attrs=pattern)
                if meta_keywords and meta_keywords.get('content'):
                    keywords_text = meta_keywords['content'].strip()
                    if keywords_text:
                        # Handle both comma and semicolon separators
                        if ',' in keywords_text:
                            keywords_list = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]
                        elif ';' in keywords_text:
                            keywords_list = [kw.strip() for kw in keywords_text.split(';') if kw.strip()]
                        else:
                            # Single keyword or space-separated
                            keywords_list = [kw.strip() for kw in keywords_text.split() if kw.strip()]
                        
                        # Filter out very short or very long keywords
                        valid_keywords = [kw for kw in keywords_list if 2 <= len(kw) <= 50]
                        all_keywords.extend(valid_keywords)
            
            # Remove duplicates while preserving order
            if all_keywords:
                seen = set()
                unique_keywords = []
                for kw in all_keywords:
                    kw_lower = kw.lower()
                    if kw_lower not in seen:
                        seen.add(kw_lower)
                        unique_keywords.append(kw)
                metadata['keywords'] = unique_keywords[:20]  # Limit to 20 keywords
                
            # Extract language with multiple fallbacks
            lang_sources = [
                soup.find('html'),
                soup.find('meta', attrs={'name': 'language'}),
                soup.find('meta', attrs={'property': 'og:locale'}),
                soup.find('meta', attrs={'http-equiv': 'content-language'})
            ]
            
            for source in lang_sources:
                if source:
                    if source.name == 'html' and source.get('lang'):
                        metadata['language'] = source['lang']
                        break
                    elif source.name == 'meta' and source.get('content'):
                        metadata['language'] = source['content']
                        break
            
            # ENHANCED: Extract comprehensive icon information
            icons = {}
            
            # Standard icon selectors with better specificity
            icon_selectors = [
                ('favicon', 'link[rel="icon"]'),
                ('favicon-16x16', 'link[rel="icon"][sizes="16x16"]'),
                ('favicon-32x32', 'link[rel="icon"][sizes="32x32"]'),
                ('favicon-96x96', 'link[rel="icon"][sizes="96x96"]'),
                ('apple-touch-icon', 'link[rel="apple-touch-icon"]'),
                ('apple-touch-icon-57x57', 'link[rel="apple-touch-icon"][sizes="57x57"]'),
                ('apple-touch-icon-60x60', 'link[rel="apple-touch-icon"][sizes="60x60"]'),
                ('apple-touch-icon-72x72', 'link[rel="apple-touch-icon"][sizes="72x72"]'),
                ('apple-touch-icon-76x76', 'link[rel="apple-touch-icon"][sizes="76x76"]'),
                ('apple-touch-icon-114x114', 'link[rel="apple-touch-icon"][sizes="114x114"]'),
                ('apple-touch-icon-120x120', 'link[rel="apple-touch-icon"][sizes="120x120"]'),
                ('apple-touch-icon-144x144', 'link[rel="apple-touch-icon"][sizes="144x144"]'),
                ('apple-touch-icon-152x152', 'link[rel="apple-touch-icon"][sizes="152x152"]'),
                ('apple-touch-icon-180x180', 'link[rel="apple-touch-icon"][sizes="180x180"]'),
                ('apple-touch-icon-precomposed', 'link[rel="apple-touch-icon-precomposed"]'),
                ('shortcut-icon', 'link[rel="shortcut icon"]'),
                ('mask-icon', 'link[rel="mask-icon"]'),
                ('manifest', 'link[rel="manifest"]')
            ]
            
            for icon_type, selector in icon_selectors:
                icon_links = soup.select(selector)
                for link in icon_links:
                    href = link.get('href')
                    if href:
                        # Make absolute URL if needed
                        if hasattr(self, '_base_url') and self._base_url:
                            href = urljoin(self._base_url, href)
                        sizes = link.get('sizes', '')
                        key = f"{icon_type}-{sizes}" if sizes else icon_type
                        icons[key] = href
            
            # Also check for any other icon-related links with flexible rel attributes
            other_icon_links = soup.find_all('link', attrs={'rel': re.compile(r'icon', re.I)})
            for link in other_icon_links:
                rel_attr = link.get('rel')
                href = link.get('href')
                if rel_attr and href:
                    # Handle rel as both string and list
                    rel = rel_attr[0] if isinstance(rel_attr, list) else rel_attr
                    if rel not in icons:
                        if hasattr(self, '_base_url') and self._base_url:
                            href = urljoin(self._base_url, href)
                        icons[rel] = href
            
            if icons:
                metadata['icons'] = icons
                
        except Exception as e:
            logger.debug(f"Basic page metadata extraction failed: {e}")
        
        return metadata
    
    def _extract_canonical_url(self, soup, base_url: str = None) -> Optional[str]:
        """Extract canonical URL from link rel='canonical'."""
        try:
            canonical_link = soup.find('link', rel='canonical')
            if canonical_link and canonical_link.get('href'):
                canonical_url = canonical_link['href']
                
                # Make absolute URL if relative
                if base_url and not canonical_url.startswith(('http://', 'https://')):
                    canonical_url = urljoin(base_url, canonical_url)
                
                return canonical_url
        except Exception as e:
            logger.debug(f"Canonical URL extraction failed: {e}")
        
        return None
    
    def _extract_dates(self, soup) -> Dict[str, Optional[str]]:
        """Extract publication and modification dates."""
        dates = {
            'published_date': None,
            'modified_date': None,
            'extracted_dates': []
        }
        
        try:
            # Check meta tags
            for pattern in self.date_meta_patterns:
                meta_tag = soup.find('meta', attrs={'name': pattern}) or soup.find('meta', attrs={'property': pattern})
                if meta_tag and meta_tag.get('content'):
                    date_str = meta_tag['content']
                    parsed_date = self._parse_date(date_str)
                    if parsed_date:
                        dates['extracted_dates'].append({
                            'type': pattern,
                            'raw': date_str,
                            'parsed': parsed_date.isoformat()
                        })
                        
                        # Set primary dates
                        if 'published' in pattern.lower() and not dates['published_date']:
                            dates['published_date'] = parsed_date.isoformat()
                        elif 'modified' in pattern.lower() and not dates['modified_date']:
                            dates['modified_date'] = parsed_date.isoformat()
            
            # Check time elements
            time_elements = soup.find_all('time')
            for time_elem in time_elements:
                datetime_attr = time_elem.get('datetime')
                if datetime_attr:
                    parsed_date = self._parse_date(datetime_attr)
                    if parsed_date:
                        dates['extracted_dates'].append({
                            'type': 'time_element',
                            'raw': datetime_attr,
                            'parsed': parsed_date.isoformat()
                        })
                        
                        if not dates['published_date']:
                            dates['published_date'] = parsed_date.isoformat()
        
        except Exception as e:
            logger.debug(f"Date extraction failed: {e}")
        
        return dates
    
    def _parse_date(self, date_string: str) -> Optional[datetime]:
        """Parse date string into datetime object."""
        try:
            # Try dateutil parser first (handles most formats)
            return dateutil.parser.parse(date_string)
        except:
            try:
                # Try common ISO format
                return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            except:
                # Try basic patterns
                patterns = [
                    '%Y-%m-%d',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%d %H:%M:%S',
                    '%d/%m/%Y',
                    '%m/%d/%Y'
                ]
                
                for pattern in patterns:
                    try:
                        return datetime.strptime(date_string, pattern)
                    except:
                        continue
        
        return None
    
    def _extract_image_data(self, soup, base_url: str = None) -> List[Dict[str, Any]]:
        """Extract image information including alt text."""
        images = []
        
        try:
            img_tags = soup.find_all('img')
            for img in img_tags:
                img_data = {}
                
                # Extract basic attributes
                src = img.get('src')
                if src:
                    # Make absolute URL
                    if base_url and not src.startswith(('http://', 'https://', 'data:')):
                        src = urljoin(base_url, src)
                    img_data['src'] = src
                
                # Extract descriptive information
                alt_text = img.get('alt', '').strip()
                if alt_text:
                    img_data['alt'] = alt_text
                
                title = img.get('title', '').strip()
                if title:
                    img_data['title'] = title
                
                # Extract size information if available
                width = img.get('width')
                height = img.get('height')
                if width:
                    img_data['width'] = width
                if height:
                    img_data['height'] = height
                
                # Only include images with meaningful information
                if img_data and (img_data.get('alt') or img_data.get('title')):
                    images.append(img_data)
        
        except Exception as e:
            logger.debug(f"Image extraction failed: {e}")
        
        return images[:10]  # Limit to first 10 meaningful images
    
    def _extract_table_of_contents(self, soup, base_url: str = None) -> List[Dict[str, Any]]:
        """Extract comprehensive table of contents from navigation links and document structure."""
        toc = []
        
        try:
            # Method 1: Explicit TOC elements (enhanced patterns)
            toc_selectors = [
                'nav[class*="toc" i]',
                'div[class*="toc" i]',
                'div[class*="table-of-contents" i]',
                'nav[class*="contents" i]',
                'aside[class*="toc" i]',
                '.table-of-contents',
                '.toc',
                '#toc',
                '#table-of-contents',
                '[role="navigation"][aria-label*="contents" i]',
                '.content-navigation',
                '.page-navigation',
                '.in-page-nav'
            ]
            
            for selector in toc_selectors:
                try:
                    toc_elements = soup.select(selector)
                    for toc_elem in toc_elements:
                        links = toc_elem.find_all('a', href=True)
                        for link in links:
                            href = link['href']
                            text = link.get_text(strip=True)
                            
                            if text and href and len(text) <= 200:  # Reasonable heading length
                                # Make absolute URL for external links
                                if base_url and href.startswith('/'):
                                    href = urljoin(base_url, href)
                                
                                # Try to determine nesting level from HTML structure
                                level = self._determine_toc_level(link)
                                
                                toc.append({
                                    'text': text,
                                    'href': href,
                                    'level': level,
                                    'type': 'explicit_toc'
                                })
                        
                        if toc:  # If we found TOC items, don't check other selectors
                            break
                    
                    if toc:
                        break
                except Exception:
                    continue
            
            # Method 2: Enhanced heading structure with better semantic analysis
            if not toc:  # Only if we didn't find explicit TOC
                headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                for heading in headings:
                    heading_text = heading.get_text(strip=True)
                    
                    # Skip headings that are likely navigation or boilerplate
                    if not heading_text or len(heading_text) > 200:
                        continue
                    
                    # Skip common navigation headings
                    skip_patterns = [
                        'menu', 'navigation', 'search', 'login', 'register',
                        'footer', 'header', 'sidebar', 'share', 'related',
                        'comments', 'tags', 'categories', 'recent posts'
                    ]
                    
                    if any(pattern in heading_text.lower() for pattern in skip_patterns):
                        continue
                    
                    heading_id = heading.get('id')
                    
                    # Look for anchor links within or near the heading
                    anchor_link = heading.find('a', href=True)
                    if not anchor_link:
                        # Check if the heading itself is wrapped in a link
                        parent = heading.parent
                        if parent and parent.name == 'a' and parent.get('href'):
                            anchor_link = parent
                    
                    # Generate href
                    href = None
                    if heading_id:
                        href = f"#{heading_id}"
                        if base_url:
                            href = base_url + href
                    elif anchor_link and anchor_link.get('href'):
                        href = anchor_link['href']
                        if base_url and href.startswith('/'):
                            href = urljoin(base_url, href)
                    else:
                        # Generate an anchor from the heading text
                        anchor_id = re.sub(r'[^\w\s-]', '', heading_text.lower())
                        anchor_id = re.sub(r'[-\s]+', '-', anchor_id).strip('-')
                        if anchor_id:
                            href = f"#{anchor_id}"
                            if base_url:
                                href = base_url + href
                    
                    if href:
                        level = int(heading.name[1])  # h1 -> 1, h2 -> 2, etc.
                        
                        # Check if this heading has substantial content following it
                        content_score = self._calculate_heading_content_score(heading)
                        
                        toc.append({
                            'text': heading_text,
                            'href': href,
                            'level': level,
                            'type': 'heading_based',
                            'content_score': content_score
                        })
            
            # Method 3: Extract from structured navigation (e.g., Wikipedia-style)
            if not toc:
                nav_elements = soup.find_all(['nav', 'ul', 'ol'], class_=re.compile(r'nav|menu|contents', re.I))
                for nav_elem in nav_elements:
                    # Only consider navigation that seems like table of contents
                    nav_text = nav_elem.get_text(strip=True).lower()
                    if any(keyword in nav_text for keyword in ['contents', 'sections', 'chapters', 'topics']):
                        links = nav_elem.find_all('a', href=True)
                        for link in links:
                            href = link['href']
                            text = link.get_text(strip=True)
                            
                            if text and href and len(text) <= 200:
                                if base_url and href.startswith('/'):
                                    href = urljoin(base_url, href)
                                
                                level = self._determine_toc_level(link)
                                
                                toc.append({
                                    'text': text,
                                    'href': href,
                                    'level': level,
                                    'type': 'structured_nav'
                                })
            
            # Method 4: Extract from article sections (for long-form content)
            if not toc:
                sections = soup.find_all(['section', 'article'], id=True)
                for section in sections:
                    section_id = section.get('id')
                    # Look for a heading within the section
                    heading = section.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    if heading and section_id:
                        heading_text = heading.get_text(strip=True)
                        if heading_text and len(heading_text) <= 200:
                            href = f"#{section_id}"
                            if base_url:
                                href = base_url + href
                            
                            level = int(heading.name[1])
                            
                            toc.append({
                                'text': heading_text,
                                'href': href,
                                'level': level,
                                'type': 'section_based'
                            })
            
            # Sort TOC by document order and limit size
            if toc:
                # Remove duplicates while preserving order
                seen = set()
                unique_toc = []
                for item in toc:
                    key = (item['text'], item['href'])
                    if key not in seen:
                        seen.add(key)
                        unique_toc.append(item)
                
                # Limit to prevent oversized data
                toc = unique_toc[:30]
        
        except Exception as e:
            logger.debug(f"Table of contents extraction failed: {e}")
        
        return toc
    
    def _determine_toc_level(self, link_element) -> int:
        """Determine the nesting level of a TOC link based on HTML structure."""
        level = 1
        parent = link_element.parent
        
        # Count nested lists to determine level
        while parent:
            if parent.name in ['ul', 'ol', 'li']:
                # Check if this list is nested inside another list
                ancestor = parent.parent
                while ancestor:
                    if ancestor.name in ['ul', 'ol']:
                        level += 1
                        break
                    ancestor = ancestor.parent
                break
            parent = parent.parent
        
        return min(level, 6)  # Cap at h6 level
    
    def _calculate_heading_content_score(self, heading) -> float:
        """Calculate a score indicating how much content follows this heading."""
        score = 0.0
        current_level = int(heading.name[1])
        
        # Count content elements until next heading of same or higher level
        next_element = heading.next_sibling
        content_elements = 0
        text_length = 0
        
        while next_element and content_elements < 10:  # Limit search
            if hasattr(next_element, 'name'):
                # Stop at same or higher level heading
                if (next_element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] and
                    int(next_element.name[1]) <= current_level):
                    break
                
                # Count substantial content elements
                if next_element.name in ['p', 'div', 'section', 'article', 'ul', 'ol', 'table']:
                    content_elements += 1
                    text = next_element.get_text(strip=True)
                    text_length += len(text)
            
            next_element = next_element.next_sibling
        
        # Score based on content quantity and quality
        score = min(content_elements * 0.2 + text_length * 0.001, 1.0)
        return score
    
    def _extract_author_info(self, soup, structured_data: Dict = None) -> Dict[str, Any]:
        """Extract comprehensive author information from multiple sources."""
        author_info = {}
        
        try:
            # Method 1: Meta tags (multiple variations)
            meta_patterns = [
                {'name': 'author'},
                {'property': 'article:author'},
                {'name': 'twitter:creator'},
                {'property': 'og:article:author'},
                {'name': 'dc.creator'},
                {'name': 'DC.Creator'}
            ]
            
            for pattern in meta_patterns:
                author_meta = soup.find('meta', attrs=pattern)
                if author_meta and author_meta.get('content'):
                    author_info['meta_author'] = author_meta['content']
                    break
            
            # Method 2: Extract from structured data (JSON-LD, microdata)
            if structured_data:
                # JSON-LD author extraction
                json_ld = structured_data.get('json_ld', [])
                for item in json_ld:
                    if 'author' in item:
                        author_data = item['author']
                        if isinstance(author_data, dict):
                            if 'name' in author_data:
                                author_info['structured_author'] = author_data['name']
                            if 'url' in author_data:
                                author_info['author_url'] = author_data['url']
                            if '@type' in author_data:
                                author_info['author_type'] = author_data['@type']
                        elif isinstance(author_data, str):
                            author_info['structured_author'] = author_data
                        break
                
                # Microdata author extraction
                microdata = structured_data.get('microdata', [])
                for item in microdata:
                    if 'author' in item:
                        author_info['microdata_author'] = item['author']
                    if 'name' in item and item.get('@type') == 'Person':
                        author_info['person_name'] = item['name']
            
            # Method 3: Enhanced HTML patterns
            author_patterns = [
                {'class': re.compile(r'author|byline|writer|creator|contributor', re.I)},
                {'itemprop': 'author'},
                {'rel': 'author'},
                {'data-author': True},
                {'id': re.compile(r'author|byline', re.I)}
            ]
            
            for pattern in author_patterns:
                author_elem = soup.find(attrs=pattern)
                if author_elem:
                    author_text = author_elem.get_text(strip=True)
                    if author_text and len(author_text) <= 200:  # Reasonable author name length
                        author_info['html_author'] = author_text
                        
                        # Try to extract author URL if it's a link
                        if author_elem.name == 'a' and author_elem.get('href'):
                            author_info['author_url'] = author_elem['href']
                        
                        # Look for additional author info in parent elements
                        parent = author_elem.parent
                        if parent:
                            # Look for author bio or description
                            bio_elem = parent.find(attrs={'class': re.compile(r'bio|description', re.I)})
                            if bio_elem:
                                bio_text = bio_elem.get_text(strip=True)
                                if bio_text and len(bio_text) <= 500:
                                    author_info['author_bio'] = bio_text
                        break
            
            # Method 4: Look for author in common blog/CMS patterns
            cms_patterns = [
                '.author-name',
                '.post-author',
                '.entry-author',
                '.article-author', 
                '.byline-author',
                '[data-testid="author"]',
                '.writer-name'
            ]
            
            for pattern in cms_patterns:
                try:
                    author_elem = soup.select_one(pattern)
                    if author_elem:
                        author_text = author_elem.get_text(strip=True)
                        if author_text and len(author_text) <= 200:
                            author_info['cms_author'] = author_text
                            break
                except Exception:
                    continue
            
            # Method 5: Extract author from URL patterns (e.g., /author/username)
            # This would need URL context, so we'll add it as a placeholder
            
        except Exception as e:
            logger.debug(f"Author extraction failed: {e}")
        
        return author_info
    
    def _extract_semantic_info(self, soup) -> Dict[str, Any]:
        """Extract additional semantic information."""
        semantic_info = {}
        
        try:
            # Extract language
            html_tag = soup.find('html')
            if html_tag and html_tag.get('lang'):
                semantic_info['language'] = html_tag['lang']
            
            # Extract reading time indicators
            reading_time_elem = soup.find(attrs={'class': re.compile(r'reading.time|read.time', re.I)})
            if reading_time_elem:
                reading_time_text = reading_time_elem.get_text(strip=True)
                # Extract number from text like "5 min read"
                time_match = re.search(r'(\d+)', reading_time_text)
                if time_match:
                    semantic_info['estimated_reading_time'] = int(time_match.group(1))
            
            # Extract breadcrumbs
            breadcrumb_nav = soup.find(['nav', 'ol', 'ul'], attrs={'class': re.compile(r'breadcrumb', re.I)})
            if breadcrumb_nav:
                breadcrumb_links = breadcrumb_nav.find_all('a')
                breadcrumbs = []
                for link in breadcrumb_links:
                    text = link.get_text(strip=True)
                    href = link.get('href')
                    if text:
                        breadcrumbs.append({'text': text, 'href': href})
                semantic_info['breadcrumbs'] = breadcrumbs
        
        except Exception as e:
            logger.debug(f"Semantic info extraction failed: {e}")
        
        return semantic_info
    
    def _extract_publication_dates(self, soup, structured_data: Dict = None) -> Dict[str, Any]:
        """Extract publication and modification dates from multiple sources."""
        dates = {}
        
        try:
            # Method 1: Meta tags (multiple variations)
            meta_patterns = [
                # Published date patterns
                ({'name': 'publication_date'}, 'published_date'),
                ({'property': 'article:published_time'}, 'published_date'),
                ({'name': 'article:published_time'}, 'published_date'),
                ({'name': 'date'}, 'published_date'),
                ({'name': 'DC.Date'}, 'published_date'),
                ({'name': 'dc.date'}, 'published_date'),
                ({'name': 'pubdate'}, 'published_date'),
                ({'property': 'og:article:published_time'}, 'published_date'),
                ({'name': 'twitter:label1', 'content': 'Written by'}, None),  # Skip this one
                
                # Modified date patterns  
                ({'property': 'article:modified_time'}, 'modified_date'),
                ({'name': 'article:modified_time'}, 'modified_date'),
                ({'name': 'last-modified'}, 'modified_date'),
                ({'name': 'DC.Date.Modified'}, 'modified_date'),
                ({'property': 'og:article:modified_time'}, 'modified_date'),
            ]
            
            for pattern, date_type in meta_patterns:
                if date_type is None:
                    continue
                    
                meta_elem = soup.find('meta', attrs=pattern)
                if meta_elem and meta_elem.get('content'):
                    date_str = meta_elem['content']
                    parsed_date = self._parse_date_string(date_str)
                    if parsed_date:
                        dates[date_type] = parsed_date
            
            # Method 2: Extract from structured data (JSON-LD, microdata)
            if structured_data:
                # JSON-LD date extraction
                json_ld = structured_data.get('json_ld', [])
                for item in json_ld:
                    # Published dates
                    for pub_field in ['datePublished', 'publishedDate', 'dateCreated']:
                        if pub_field in item and not dates.get('published_date'):
                            parsed_date = self._parse_date_string(item[pub_field])
                            if parsed_date:
                                dates['published_date'] = parsed_date
                                break
                    
                    # Modified dates
                    for mod_field in ['dateModified', 'modifiedDate', 'dateUpdated']:
                        if mod_field in item and not dates.get('modified_date'):
                            parsed_date = self._parse_date_string(item[mod_field])
                            if parsed_date:
                                dates['modified_date'] = parsed_date
                                break
                
                # Microdata date extraction
                microdata = structured_data.get('microdata', [])
                for item in microdata:
                    for pub_field in ['datePublished', 'publishedDate', 'dateCreated']:
                        if pub_field in item and not dates.get('published_date'):
                            parsed_date = self._parse_date_string(item[pub_field])
                            if parsed_date:
                                dates['published_date'] = parsed_date
                                break
                    
                    for mod_field in ['dateModified', 'modifiedDate', 'dateUpdated']:
                        if mod_field in item and not dates.get('modified_date'):
                            parsed_date = self._parse_date_string(item[mod_field])
                            if parsed_date:
                                dates['modified_date'] = parsed_date
                                break
            
            # Method 3: HTML element patterns
            html_patterns = [
                # Time elements with datetime attribute
                ('time[datetime]', 'datetime'),
                ('time[pubdate]', 'datetime'),
                
                # Common date classes
                ('.published', 'text'),
                ('.post-date', 'text'),
                ('.entry-date', 'text'),
                ('.article-date', 'text'),
                ('.date-published', 'text'),
                ('.publish-date', 'text'),
                ('.creation-date', 'text'),
                ('.post-time', 'text'),
                
                # Microdata
                ('[itemprop="datePublished"]', 'datetime_or_text'),
                ('[itemprop="dateCreated"]', 'datetime_or_text'),
                ('[itemprop="dateModified"]', 'datetime_or_text'),
            ]
            
            for selector, attr_type in html_patterns:
                if dates.get('published_date') and dates.get('modified_date'):
                    break  # We have both dates
                
                try:
                    elements = soup.select(selector)
                    for elem in elements:
                        date_str = None
                        
                        if attr_type == 'datetime':
                            date_str = elem.get('datetime')
                        elif attr_type == 'text':
                            date_str = elem.get_text(strip=True)
                        elif attr_type == 'datetime_or_text':
                            date_str = elem.get('datetime') or elem.get_text(strip=True)
                        
                        if date_str:
                            parsed_date = self._parse_date_string(date_str)
                            if parsed_date:
                                # Determine if this is likely a published or modified date
                                elem_text = elem.get_text(strip=True).lower()
                                elem_class = ' '.join(elem.get('class', [])).lower()
                                elem_id = elem.get('id', '').lower()
                                combined_text = f"{elem_text} {elem_class} {elem_id}"
                                
                                if any(word in combined_text for word in ['modified', 'updated', 'edited', 'revised']):
                                    if not dates.get('modified_date'):
                                        dates['modified_date'] = parsed_date
                                elif not dates.get('published_date'):
                                    dates['published_date'] = parsed_date
                                break
                except Exception:
                    continue
            
            # Method 4: Extract from common blog/CMS patterns
            cms_date_patterns = [
                '.entry-meta .published',
                '.post-meta .date',
                '.article-meta time',
                '.byline time',
                '.post-header .date',
                '.content-meta .date'
            ]
            
            for pattern in cms_date_patterns:
                if dates.get('published_date'):
                    break
                    
                try:
                    elem = soup.select_one(pattern)
                    if elem:
                        date_str = elem.get('datetime') or elem.get_text(strip=True)
                        if date_str:
                            parsed_date = self._parse_date_string(date_str)
                            if parsed_date and not dates.get('published_date'):
                                dates['published_date'] = parsed_date
                                break
                except Exception:
                    continue
            
        except Exception as e:
            logger.debug(f"Date extraction failed: {e}")
        
        return dates
    
    def _parse_date_string(self, date_str: str) -> Optional[str]:
        """Parse various date string formats into ISO format."""
        if not date_str or not isinstance(date_str, str):
            return None
        
        try:
            # Clean the date string
            date_str = date_str.strip()
            
            # Handle relative dates
            relative_patterns = [
                (r'(\d+)\s*(minute|min)s?\s*ago', lambda m: datetime.now() - timedelta(minutes=int(m.group(1)))),
                (r'(\d+)\s*(hour|hr)s?\s*ago', lambda m: datetime.now() - timedelta(hours=int(m.group(1)))),
                (r'(\d+)\s*(day)s?\s*ago', lambda m: datetime.now() - timedelta(days=int(m.group(1)))),
                (r'(\d+)\s*(week)s?\s*ago', lambda m: datetime.now() - timedelta(weeks=int(m.group(1)))),
                (r'(\d+)\s*(month)s?\s*ago', lambda m: datetime.now() - timedelta(days=int(m.group(1)) * 30)),
                (r'(\d+)\s*(year)s?\s*ago', lambda m: datetime.now() - timedelta(days=int(m.group(1)) * 365)),
            ]
            
            for pattern, func in relative_patterns:
                match = re.search(pattern, date_str.lower())
                if match:
                    parsed_date = func(match)
                    return parsed_date.isoformat()
            
            # Handle "today", "yesterday" etc.
            if 'today' in date_str.lower():
                return datetime.now().isoformat()
            elif 'yesterday' in date_str.lower():
                return (datetime.now() - timedelta(days=1)).isoformat()
            
            # Try to parse with dateutil
            parsed_date = dateutil.parser.parse(date_str, fuzzy=True)
            
            # Validate that the date is reasonable (not too far in the future or past)
            now = datetime.now()
            if parsed_date.year < 1990 or parsed_date > now + timedelta(days=30):
                return None
            
            return parsed_date.isoformat()
            
        except Exception as e:
            logger.debug(f"Failed to parse date '{date_str}': {e}")
            return None
