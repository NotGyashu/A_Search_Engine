use std::collections::HashMap;
use tl::{Parser, HTMLTag, Node};
use regex::Regex;
use chrono::{DateTime, NaiveDateTime, Utc, TimeZone, NaiveDate};
use crate::types::*;
use crate::cleaner::FastCleaner;
use std::collections::HashSet;
use crate::extractor::metadata_extractor::MetadataExtractor;
use crate::extractor::main_content_extractor::MainContentExtractor;

pub struct OptimizedExtractor {
    // Precompiled regex patterns for performance
    api_pattern: Regex,
    function_pattern: Regex,
    tech_pattern: Regex,
    date_patterns: Vec<Regex>,
    url_pattern: Regex,
    email_pattern: Regex,
}

impl OptimizedExtractor {
    pub fn new() -> Self {
        // Technical content patterns (reduced for performance)
        let tech_keywords = [
            "api", "function", "class", "method", "algorithm", "code", "software", 
            "programming", "development", "technology", "technical", "system", 
            "framework", "library", "database", "server", "client", "frontend", "backend", 
            "fullstack", "compiler", "interpreter", "object", "variable", "loop", 
            "conditional", "array", "string", "boolean", "integer", "float", "pointer", 
            "recursion", "stack", "queue", "tree", "graph", "hash", "encryption", 
            "protocol", "network", "cloud", "virtualization", "container", "docker", 
            "kubernetes", "ci", "cd", "git", "version", "control", "repository", 
            "branch", "merge", "commit", "pull", "push", "debug", "exception", 
            "error", "log", "performance", "optimization", "testing", "unit", "integration", 
            "api-testing", "endpoint", "request", "response", "json", "xml", "yaml", 
            "html", "css", "javascript", "typescript", "python", "java", "c++", "c#", 
            "ruby", "php", "sql", "nosql", "mongodb", "postgresql", "mysql", "algorithmic", 
            "data", "datastructure", "machine-learning", "ai", "artificial-intelligence", 
            "deep-learning", "neural-network", "automation", "script", "shell", 
            "bash", "powershell", "devops", "security", "authentication", "authorization", 
            "token", "session", "cookie", "ssl", "tls", "http", "https", "rest", 
            "graphql", "websocket", "middleware", "architecture", "design-pattern", 
            "microservice", "singleton", "observer", "factory", "adapter", "decorator", 
            "strategy", "prototype", "thread", "process", "concurrency", "asynchronous", 
            "synchronous", "event-driven", "callback", "promise", "lambda", "api-gateway",
            "load-balancer", "cache", "cdn", "elastic", "scalability", "availability", 
            "redundancy", "backup", "replication", "cluster", "sharding", "indexing", 
            "query", "optimization", "latency", "throughput", "bandwidth", "iot", 
            "edge-computing", "serverless", "function-as-a-service", "infrastructure", 
            "monitoring", "logging", "tracing", "alerting", "incident", "sla", "slo", 
            "ci-cd-pipeline", "orchestration", "automation-script", "virtual-machine", 
            "hypervisor", "sandbox", "debugging-tool", "profiling", "refactoring", 
            "code-review", "linting", "formatter", "build-tool", "package-manager", 
            "dependency", "versioning", "semantic-versioning", "sdk", "ide", "terminal", 
            "cli", "restful", "crud", "orm", "mvc", "mvvm", "repository-pattern", 
            "event-sourcing", "queueing", "messaging", "pub-sub", "observer-pattern", 
            "factory-pattern", "adapter-pattern", "strategy-pattern", "singleton-pattern",
            "decorator-pattern", "proxy-pattern", "facade-pattern", "bridge-pattern", 
            "composite-pattern", "flyweight-pattern", "iterator-pattern", "state-pattern", 
            "chain-of-responsibility", "command-pattern", "mediator-pattern", "memento-pattern",
            "prototype-pattern", "visitor-pattern", "dependency-injection", "inversion-of-control",
            "oop", "functional-programming", "procedural", "imperative", "declarative", 
            "multi-threading", "parallel-processing", "gpu-computing", "tensor", 
            "backpropagation", "cnn", "rnn", "lstm", "gan", "transformer", 
            "nlp", "computer-vision", "reinforcement-learning", "data-pipeline", 
            "etl", "data-warehouse", "data-lake", "big-data", "hadoop", "spark", 
            "flink", "kafka", "streaming", "batch-processing", "map-reduce"
        ];

        
        let tech_pattern_str = tech_keywords.join("|");
        
        // Essential date patterns only
        let date_patterns = vec![
            Regex::new(r"\d{4}-\d{2}-\d{2}").unwrap(),       // YYYY-MM-DD
            Regex::new(r"\d{2}/\d{2}/\d{4}").unwrap(),       // MM/DD/YYYY
            Regex::new(r"\d{2}-\d{2}-\d{4}").unwrap(),       // MM-DD-YYYY
            Regex::new(r"\d{2}\.\d{2}\.\d{4}").unwrap(),     // DD.MM.YYYY
            Regex::new(r"\d{4}/\d{2}/\d{2}").unwrap(),       // YYYY/MM/DD
            Regex::new(r"\d{4}\.\d{2}\.\d{2}").unwrap(),     // YYYY.MM.DD
            Regex::new(r"\d{2} \w+ \d{4}").unwrap(),         // DD Month YYYY (e.g., 25 August 2025)
            Regex::new(r"\w+ \d{2}, \d{4}").unwrap(),        // Month DD, YYYY (e.g., August 25, 2025)
            Regex::new(r"\d{1,2}/\d{1,2}/\d{2}").unwrap(),   // M/D/YY or MM/DD/YY
            Regex::new(r"\d{1,2}-\d{1,2}-\d{2}").unwrap(),   // M-D-YY or MM-DD-YY
            Regex::new(r"\d{1,2} \w{3} \d{4}").unwrap(),     // DD Mon YYYY (e.g., 25 Aug 2025)
            Regex::new(r"\d{1,2}-\w{3}-\d{4}").unwrap(),     // DD-Mon-YYYY (e.g., 25-Aug-2025)
            Regex::new(r"\w{3} \d{1,2}, \d{4}").unwrap(),    // Mon DD, YYYY (e.g., Aug 25, 2025)
            Regex::new(r"\d{8}").unwrap(),                   // YYYYMMDD
            Regex::new(r"\d{2}\s?/\s?\d{2}\s?/\s?\d{4}").unwrap(), // MM / DD / YYYY with optional spaces
        ];

        Self {
            api_pattern: Regex::new(r"\b[A-Z][A-Za-z0-9_]*\.[A-Za-z0-9_]+\b").unwrap(),
            function_pattern: Regex::new(r"\b[a-z_][a-z0-9_]*\(.*?\)\b").unwrap(),
            tech_pattern: Regex::new(&format!(r"(?i)\b(?:{})\b", tech_pattern_str)).unwrap(),
            date_patterns,
            url_pattern: Regex::new(r"https?://[^\s]+").unwrap(),
            email_pattern: Regex::new(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b").unwrap(),
        }
    }

    pub fn extract_content(&self, html: &str, base_url: &str) -> ProcessedDocument {
        let dom = tl::parse(html, tl::ParserOptions::default()).unwrap();
        let parser = dom.parser();
        
        let mut document = ProcessedDocument::default();
        let metadata_extractor = MetadataExtractor::new(&dom, parser);
        let main_content_extractor = MainContentExtractor;
        
        // Extract all metadata using the cached extractor
        document.title = metadata_extractor.get_title().unwrap_or_default();
        document.description = metadata_extractor.get_description().unwrap_or_default();
        document.keywords = metadata_extractor.get_keywords();
        document.content_type = metadata_extractor.get_content_type().unwrap_or_default();
        document.primary_image = metadata_extractor.get_primary_image(|s| self.resolve_url(s, base_url));
        document.favicon = metadata_extractor.get_favicon(|s| self.resolve_url(s, base_url));
        document.author_name = metadata_extractor.get_author();
        (document.published_date, document.modified_date) = 
        metadata_extractor.get_dates(|s| self.parse_date_string(s));
        document.canonical_url = metadata_extractor.get_canonical_url(base_url);
        document.main_content = main_content_extractor.extract_main_content(&dom, parser);
        document.content_categories = MetadataExtractor::get_content_categories(&document.main_content);

        // Extract headings for content structure
        self.extract_headings(&dom, parser, &mut document);
        
        // Create optimized chunks with context
        document.text_chunks_with_context = self.create_chunks_with_context(&document.main_content, &document.headings);
        
        // Calculate essential metrics only
        self.calculate_essential_metrics(&mut document);
        
        // Detect technical content
        document.is_technical_content = self.is_technical_content(&document);
        if document.is_technical_content {
            document.content_categories.push("technology".into())
        }
        
        document
    }


    fn extract_headings(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument) {
        for level in 1..=6 {
            let selector = format!("h{}", level);
            if let Some(heading_nodes) = dom.query_selector(&selector) {
                for node_handle in heading_nodes {
                    if let Some(node) = node_handle.get(parser) {
                        let text = node.inner_text(parser).trim().to_string();
                        if !text.is_empty() && text.len() < 200 {
                            let heading = Heading {
                                level: level as u8,
                                text,
                            };
                            document.headings.push(heading);
                        }
                    }
                }
            }
        }
    }

    
fn create_chunks_with_context(&self, content: &str, headings: &[Heading]) -> Vec<ChunkWithContext> {
        if content.is_empty() {
            return Vec::new();
        }

        // 🧹 Use FastCleaner for proper chunking with comprehensive cleaning
        let cleaner = FastCleaner::new();
        
        // First, clean the content thoroughly to remove HTML entities and noise
        let cleaned_content = cleaner.clean_text(content);
        
        // Use FastCleaner's optimized chunking method (with less restrictive size requirements)
        let raw_chunks = cleaner.create_chunks(&cleaned_content, 2500, 50);  // Reduced from 100 to 50
        
        let mut chunks_with_context = Vec::new();
        
        for (index, chunk_text) in raw_chunks.into_iter().enumerate() {
            // Additional filtering for web-specific noise that might slip through
            if self.is_chunk_meaningful(&chunk_text) && !self.contains_web_noise(&chunk_text) {
                let relevant_headings = self.find_relevant_headings_for_chunk(&chunk_text, headings);
                
                chunks_with_context.push(ChunkWithContext {
                    text_chunk: chunk_text,
                    relevant_headings,
                    chunk_index: index,
                });
            }
        }

        chunks_with_context
    }
    
    fn contains_web_noise(&self, text: &str) -> bool {
        let text_lower = text.to_lowercase();
        
        // Check for HTML-encoded entities that might slip through
        if text.contains("\\u003c") || text.contains("\\u003e") || 
           text.contains("\\u0026") || text.contains("&nbsp;") ||
           text.contains("&amp;") || text.contains("&lt;") || text.contains("&gt;") {
            return true;
        }
        
        // CRITICAL: Check for CSS patterns that indicate stylesheet content
        if text.contains(".mw-parser-output") || text.contains("navbox") ||
           text.contains("display:inline") || text.contains("margin:0") ||
           text.contains("padding:0") || text.contains("font-weight:bold") ||
           text.contains("background-color:") || text.contains("border:") ||
           text.contains("content:") || text.contains("::after") ||
           text.contains("::before") || text.contains(".hlist") ||
           text.contains("box-sizing:") || text.contains("line-height:") ||
           text.contains("text-align:") || text.contains("white-space:") ||
           text.contains("border-color:") || text.contains("border-left:") ||
           text.contains("border-top:") || text.contains("float:") ||
           text.contains("max-width:") || text.contains("@media") ||
           text.contains("counter-reset:") || text.contains("counter-increment:") {
            return true;
        }
        
        // Check for MediaWiki-specific patterns
        if text.contains("vtePart of") || text.contains("vteReligions") ||
           text.contains("Retrieved from") || text.contains("Hidden categories:") ||
           text.contains("Articles with") || text.contains("Pages with") ||
           text.contains("Webarchive template") || text.contains("Commons category") {
            return true;
        }
        
        // Check for JSON remnants
        if text.contains("\"type\":") || text.contains("\"href\":") || 
           text.contains("\"title\":") || text.contains("\"class\":") ||
           text.contains("\"id\":") || text.contains("\"style\":") {
            return true;
        }
        
        // Enhanced interface/navigation noise detection
        let interface_noise = [
            "diffhist", "talk contribs", "mobile edit", "visual edit", "android app",
            "ios app", "hidden tag", "wikiedu", "dashboard", "assignment wizard",
            "wikiloop", "battlefield", "user creation", "account", "antivandal",
            "rollback", "manual revert", "tag filter", "namespace", "template",
            "category", "portal", "module", "invert selection", "recent changes",
            "options", "hide", "show", "edit filter", "cleanup", "vandalism",
            "deletion", "backlogs", "village pump", "mailing lists", "signpost"
        ];
        
        // Count interface noise indicators
        let noise_count = interface_noise.iter()
            .map(|&noise| text_lower.matches(noise).count())
            .sum::<usize>();
        
        // If more than 20% of the text is interface noise, reject it
        let word_count = text.split_whitespace().count();
        if word_count > 0 && (noise_count as f32 / word_count as f32) > 0.2 {
            return true;
        }
        
        // Check for excessive CSS-like patterns (lots of colons and semicolons)
        let css_chars = text.chars().filter(|c| *c == ':' || *c == ';').count();
        if css_chars > 20 && text.len() > 500 {
            let css_density = css_chars as f32 / text.len() as f32;
            if css_density > 0.01 { // More than 1% CSS characters
                return true;
            }
        }
        
        // Check for excessive version numbers and technical IDs (like [1.0], [2.1], etc.)
        let version_pattern_count = text.matches(|c: char| c == '[' || c == ']').count();
        if version_pattern_count > 10 {
            return true;
        }
        
        // Check for excessive technical abbreviations and acronyms
        let uppercase_sequences = text.chars()
            .collect::<Vec<_>>()
            .windows(3)
            .filter(|window| window.iter().all(|c| c.is_uppercase() || !c.is_alphabetic()))
            .count();
        
        if uppercase_sequences > word_count / 4 {
            return true;
        }
        
        // Check for excessive navigation/link text
        let link_indicators = ["click here", "read more", "learn more", "view all", 
                              "home page", "contact us", "about us", "privacy policy"];
        if link_indicators.iter().any(|&indicator| text_lower.contains(indicator)) {
            // Only reject if it's mostly navigation content
            let total_words = text.split_whitespace().count();
            let nav_words = link_indicators.iter()
                .map(|&indicator| text_lower.matches(indicator).count() * indicator.split_whitespace().count())
                .sum::<usize>();
            
            if total_words > 0 && (nav_words as f32 / total_words as f32) > 0.3 {
                return true;
            }
        }
        
        false
    }
    
    fn is_chunk_meaningful(&self, chunk: &str) -> bool {
        let chunk = chunk.trim();
        
        // Must have minimum length (reduced from 30 to 20)
        if chunk.len() < 20 {
            return false;
        }
        
        // Check for reasonable sentence structure (reduced from 5 to 3 words)
        let words: Vec<&str> = chunk.split_whitespace().collect();
        if words.len() < 3 {
            return false;
        }
        
        // Must contain some alphabetic content (made more lenient)
        let alpha_chars = chunk.chars().filter(|c| c.is_alphabetic()).count();
        if alpha_chars < chunk.len() / 5 { // Reduced from 1/4 to 1/5
            return false;
        }
        
        // Check for too much JSON-like content (made more lenient)
        let json_chars = chunk.chars().filter(|c| "{}[]\",:;".contains(*c)).count();
        if json_chars > chunk.len() / 3 { // Increased from 1/4 to 1/3
            return false;
        }
        
        // Must contain some readable English words (made more lenient)
        let common_words = ["the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "a", "an", "is", "are", "was", "were", "this", "that"];
        let word_count = common_words.iter().filter(|&word| {
            chunk.to_lowercase().contains(word)
        }).count();
        
        // Need at least 1 common word (was requiring any, now more explicit)
        word_count >= 1
    }

    fn find_relevant_headings_for_chunk(&self, chunk_text: &str, headings: &[Heading]) -> Vec<String> {
        // Simple relevance: headings that contain words from the chunk
        let chunk_words: std::collections::HashSet<String> = chunk_text
            .to_lowercase()
            .split_whitespace()
            .filter(|w| w.len() > 3)
            .take(20) // Only check first 20 words for performance
            .map(|w| w.to_string())
            .collect();

        headings
            .iter()
            .filter_map(|heading| {
                let heading_words: std::collections::HashSet<String> = heading.text
                    .to_lowercase()
                    .split_whitespace()
                    .map(|w| w.to_string())
                    .collect();

                // If heading shares words with chunk, it's relevant
                let intersection: Vec<_> = chunk_words.intersection(&heading_words).collect();
                if intersection.len() > 0 {
                    Some(heading.text.clone())
                } else {
                    None
                }
            })
            .take(3) // Max 3 relevant headings per chunk
            .collect()
    }


    fn resolve_url(&self, url: &str, base_url: &str) -> String {
        if url.starts_with("http") {
            url.to_string()
        } else if url.starts_with("//") {
            format!("https:{}", url)
        } else if url.starts_with("/") {
            // Extract domain from base_url
            if let Ok(parsed) = url::Url::parse(base_url) {
                format!("{}://{}{}", parsed.scheme(), parsed.host_str().unwrap_or(""), url)
            } else {
                url.to_string()
            }
        } else {
            format!("{}/{}", base_url.trim_end_matches('/'), url)
        }
    }

    fn clean_body_text(&self, text: &str) -> String {
        // Remove extra whitespace and clean up
        let cleaned = text
            .lines()
            .map(|line| line.trim())
            .filter(|line| !line.is_empty() && line.len() > 10)
            .collect::<Vec<_>>()
            .join(" ");
        
        // Remove excessive whitespace
        let regex = regex::Regex::new(r"\s+").unwrap();
        regex.replace_all(&cleaned, " ").trim().to_string()
    }

    fn extract_readable_content(&self, raw_content: &str) -> String {
        // Filter out common noise patterns found in modern web pages
        let lines: Vec<&str> = raw_content
            .lines()
            .map(|line| line.trim())
            .filter(|line| {
                // Skip empty lines
                if line.is_empty() || line.len() < 10 {
                    return false;
                }
                
                // Skip lines that look like JSON data
                if line.starts_with('{') || line.starts_with('[') || 
                   line.contains("\"props\"") || line.contains("\"pageProps\"") ||
                   line.contains("\"@type\"") || line.contains("\"contentType\"") ||
                   line.contains("\"href\"") || line.contains("\"metadata\"") {
                    return false;
                }
                
                // Skip navigation and UI elements
                if line.contains("Sign in") || line.contains("Register") ||
                   line.contains("Menu") || line.contains("Search") ||
                   line.contains("Subscribe") || line.contains("Follow") ||
                   line.contains("Share") || line.contains("Like") ||
                   line.contains("Tweet") || line.contains("Facebook") {
                    return false;
                }
                
                // Skip lines with excessive special characters (likely JSON/code)
                let special_char_count = line.chars().filter(|c| "{}[]\",:;".contains(*c)).count();
                if special_char_count > line.len() / 4 {
                    return false;
                }
                
                // Skip URLs and technical strings
                if line.starts_with("http") || line.starts_with("www.") ||
                   line.contains("javascript:") || line.contains("mailto:") ||
                   line.contains("tel:") {
                    return false;
                }
                
                // Skip lines that are mostly numbers or IDs
                let non_alphanumeric: usize = line.chars().filter(|c| !c.is_alphanumeric() && *c != ' ').count();
                if non_alphanumeric > line.len() / 3 {
                    return false;
                }
                
                true
            })
            .collect();
            
        let filtered_content = lines.join(" ");
        
        // Final cleanup
        self.clean_body_text(&filtered_content)
    }

 
    fn calculate_essential_metrics(&self, document: &mut ProcessedDocument) {
        let words: Vec<&str> = document.main_content
            .split_whitespace()
            .filter(|w| w.len() > 2)
            .collect();
        
        document.word_count = words.len();
        
        // Calculate semantic info with essential fields only
        document.semantic_info = SemanticInfo {
            word_count: document.word_count,
            sentence_count: document.main_content.matches('.').count(),
            paragraph_count: document.main_content.matches('\n').count().max(1),
            reading_time_minutes: (document.word_count as f32 / 200.0).max(1.0),
            content_quality_score: self.calculate_quality_score(&document.main_content, &document.headings),
            is_technical_content: self.calculate_technical_score(&document.main_content) > 0.3,
            headings_count: document.headings.len(),
            images_count: if document.primary_image.is_some() { 1 } else { 0 },
            links_count: 0, // We don't extract links in optimized version
            technical_score: self.calculate_technical_score(&document.main_content),
            avg_sentence_length: if document.semantic_info.sentence_count > 0 {
                document.word_count as f32 / document.semantic_info.sentence_count as f32
            } else { 0.0 },
            content_density: document.word_count as f32 / document.main_content.len().max(1) as f32,
        };
        
        document.content_quality_score = document.semantic_info.content_quality_score;
    }

    fn calculate_quality_score(&self, content: &str, headings: &[Heading]) -> f32 {
        let mut score = 0.0;
        
        // Length scoring
        let word_count = content.split_whitespace().count() as f32;
        if word_count > 100.0 {
            score += (word_count / 1000.0).min(3.0);
        }
        
        // Structure scoring
        if !headings.is_empty() {
            score += 1.0;
        }
        
        if headings.len() > 2 {
            score += 0.5;
        }
        
        score.min(5.0)
    }

    fn calculate_technical_score(&self, content: &str) -> f32 {
        let technical_count = self.tech_pattern.find_iter(content).count();
        (technical_count as f32 / content.len().max(1) as f32) * 1000.0
    }

    fn is_technical_content(&self, document: &ProcessedDocument) -> bool {
        document.semantic_info.technical_score > 0.3 || 
        document.semantic_info.is_technical_content
    }

    

    fn parse_date_string(&self, date_str: &str) -> Option<String> {
        // Simple date parsing - use chrono for proper parsing
        if let Ok(dt) = DateTime::parse_from_rfc3339(date_str) {
            return Some(dt.to_utc().to_rfc3339());
        }
        
        // Try other common formats
        for pattern in &self.date_patterns {
            if pattern.is_match(date_str) {
                // For now, return the original string if it matches a pattern
                return Some(date_str.to_string());
            }
        }
        
        None
    }
}
