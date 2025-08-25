use regex::Regex;
use once_cell::sync::Lazy;
use std::collections::{HashSet, HashMap};
use chrono::{DateTime, NaiveDateTime, NaiveDate, Utc, TimeZone};
use serde_json::Value;

// Pre-compiled regex patterns for ultra-fast text cleaning
static EXTRA_WHITESPACE: Lazy<Regex> = Lazy::new(|| Regex::new(r"\s+").unwrap());
static HTML_ENTITIES: Lazy<Regex> = Lazy::new(|| Regex::new(r"&[a-zA-Z0-9#]+;").unwrap());
static UNICODE_HTML_ENTITIES: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"\\u003[cC]|\\u003[eE]|\\u0026|\\u0022|\\u0027|\\u003[aA]|\\u003[dD]").unwrap()
});
static NAVIGATION_WORDS: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"\b(?:diffhist|contribs|mobile\s+edit|visual\s+edit|android\s+app|ios\s+app|hidden\s+tag|wikiedu|dashboard|assignment\s+wizard|wikiloop|battlefield|user\s+creation|antivandal|rollback|manual\s+revert|tag\s+filter|namespace|template\s+talk|category\s+talk|portal\s+talk|module\s+talk|invert\s+selection|recent\s+changes\s+options|hide\s+registered|hide\s+unregistered|show\s+bots|hide\s+minor|edit\s+filter\s+log|village\s+pump|mailing\s+lists|wikipedia\s+signpost)\b").unwrap()
});
static INTERFACE_PATTERNS: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"\b(?:diffhist|talk\s+contribs|Tags:|App\s+\w+|Mobile\s+edit|Visual\s+edit|Android\s+app|iOS\s+app|WikiEdu|WikiLoop|Dashboard|Wikifile|WINTR|User\s+creation|Account\s+\w+|AntiVandal|Rollback|Manual\s+revert|\+\d+|\-\d+|15:43|\[\d+\.\d+\]|\(testing\)|\(hidden\s+tag\))\b").unwrap()
});
static TECHNICAL_NOISE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"\b(?:wikiedu\.org|dashboard\.wikiedu\.org|wikiloop|battlefield|assignment\s+wizard|user\s+analysis\s+tool|citation\s+bot|content\s+translation|crop\s+tool|dab\s+mechanic|edit\s+check|hotcat|huggle|iabot|management\s+console|quickcategories|swviewer|takedown\s+tools|torproxy|twinkle)\b").unwrap()
});
static SOCIAL_SHARING: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"\b(?:facebook|twitter|linkedin|instagram|youtube|share|like|follow|tweet|pin)\b").unwrap()
});
static EXCESSIVE_PUNCT: Lazy<Regex> = Lazy::new(|| Regex::new(r"[.!?]{3,}").unwrap());
static URL_PATTERN: Lazy<Regex> = Lazy::new(|| Regex::new(r"https?://\S+").unwrap());
static EMAIL_PATTERN: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b").unwrap()
});

// Stop words for keyword filtering
static STOP_WORDS: Lazy<HashSet<&'static str>> = Lazy::new(|| {
    [
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
        "by", "from", "is", "are", "was", "were", "be", "been", "have", "has", "had",
        "do", "does", "did", "will", "would", "should", "could", "can", "may", "might",
        "must", "shall", "it", "its", "this", "that", "these", "those", "i", "you", "he",
        "she", "we", "they", "me", "him", "her", "us", "them", "my", "your", "his", "their",
        "one", "two", "three", "first", "second", "last", "next", "more", "most", "some",
        "all", "any", "each", "every", "no", "not", "only", "just", "also", "very", "much",
        "many", "now", "then", "here", "there", "when", "where", "how", "what", "who", "why"
    ].iter().copied().collect()
});

pub struct FastCleaner {
    max_chunk_size: usize,
    min_chunk_size: usize,
    overlap_size: usize,
}

impl FastCleaner {
    pub fn new() -> Self {
        Self {
            max_chunk_size: 2500,
            min_chunk_size: 100,
            overlap_size: 50,
        }
    }

    /// Main text cleaning function - REVISED for targeted cleaning
    pub fn clean_text(&self, text: &str) -> String {
        if text.is_empty() {
            return String::new();
        }

        let mut cleaned = text.to_string();

        // Step 1: Remove specific MediaWiki noise patterns that might slip through
        let vte_pattern = Regex::new(r"\s?vte\s").unwrap();
        cleaned = vte_pattern.replace_all(&cleaned, " ").to_string();
        
        // Step 2: Remove Wikipedia-specific interface remnants
        let wiki_noise = Regex::new(r"\b(?:diffhist|contribs|mobile\s+edit|visual\s+edit|android\s+app|ios\s+app|hidden\s+tag|wikiedu|dashboard|assignment\s+wizard|wikiloop|battlefield|user\s+creation|antivandal|rollback|manual\s+revert)\b").unwrap();
        cleaned = wiki_noise.replace_all(&cleaned, " ").to_string();

        // Step 3: Remove URLs and emails from text content
        cleaned = URL_PATTERN.replace_all(&cleaned, " ").to_string();
        cleaned = EMAIL_PATTERN.replace_all(&cleaned, " ").to_string();

        // Step 4: Clean HTML entities and Unicode-encoded HTML entities
        cleaned = HTML_ENTITIES.replace_all(&cleaned, " ").to_string();
        cleaned = UNICODE_HTML_ENTITIES.replace_all(&cleaned, " ").to_string();

        // Step 5: Normalize excessive punctuation
        cleaned = EXCESSIVE_PUNCT.replace_all(&cleaned, "...").to_string();

        // Step 6: Normalize all whitespace to single spaces (final step)
        cleaned = EXTRA_WHITESPACE.replace_all(&cleaned, " ").trim().to_string();

        // IMPORTANT: The old, aggressive line-by-line filtering is completely removed.
        // The DOM cleaning in lib.rs is a much safer and more effective replacement.

        cleaned
    }

    /// Clean description text specifically
    pub fn clean_description(&self, description: &str) -> String {
        if description.is_empty() {
            return String::new();
        }

        let mut cleaned = description.to_string();
        
        // Remove HTML entities
        cleaned = HTML_ENTITIES.replace_all(&cleaned, " ").to_string();
        
        // Normalize whitespace
        cleaned = EXTRA_WHITESPACE.replace_all(&cleaned, " ").to_string();
        
        // Trim and ensure reasonable length
        cleaned = cleaned.trim().to_string();
        if cleaned.len() > 300 {
            // Find a good breaking point
            if let Some(pos) = cleaned[..300].rfind('.') {
                cleaned = cleaned[..pos + 1].to_string();
            } else if let Some(pos) = cleaned[..300].rfind(' ') {
                cleaned = format!("{}...", &cleaned[..pos]);
            } else {
                cleaned = format!("{}...", &cleaned[..297]);
            }
        }

        cleaned
    }

    /// Create optimized text chunks for search indexing
    pub fn create_chunks(&self, text: &str, max_size: usize, min_size: usize) -> Vec<String> {
        if text.len() <= max_size {
            if text.len() >= min_size {
                return vec![text.to_string()];
            } else {
                return Vec::new();
            }
        }

        let mut chunks = Vec::new();
        let sentences: Vec<&str> = text.split(". ").collect();
        
        let mut current_chunk = String::new();
        
        for sentence in sentences {
            let sentence_with_period = if sentence.ends_with('.') {
                sentence.to_string()
            } else {
                format!("{}.", sentence)
            };

            // If adding this sentence would exceed max_size, finalize current chunk
            if current_chunk.len() + sentence_with_period.len() + 1 > max_size {
                if current_chunk.len() >= min_size {
                    chunks.push(current_chunk.trim().to_string());
                }
                current_chunk = sentence_with_period;
            } else {
                if !current_chunk.is_empty() {
                    current_chunk.push(' ');
                }
                current_chunk.push_str(&sentence_with_period);
            }
        }

        // Add the last chunk if it's large enough
        if current_chunk.len() >= min_size {
            chunks.push(current_chunk.trim().to_string());
        }

        // If we couldn't create proper sentence-based chunks, fall back to word-based
        if chunks.is_empty() && text.len() >= min_size {
            chunks = self.create_word_based_chunks(text, max_size, min_size);
        }

        chunks
    }

    /// Helper: Create word-based chunks when sentence splitting fails
    fn create_word_based_chunks(&self, text: &str, max_size: usize, min_size: usize) -> Vec<String> {
        let words: Vec<&str> = text.split_whitespace().collect();
        let mut chunks = Vec::new();
        let mut current_chunk = String::new();

        for word in words {
            if current_chunk.len() + word.len() + 1 > max_size {
                if current_chunk.len() >= min_size {
                    chunks.push(current_chunk.trim().to_string());
                }
                current_chunk = word.to_string();
            } else {
                if !current_chunk.is_empty() {
                    current_chunk.push(' ');
                }
                current_chunk.push_str(word);
            }
        }

        if current_chunk.len() >= min_size {
            chunks.push(current_chunk.trim().to_string());
        }

        chunks
    }

    /// Check if a line is navigation content
    fn is_navigation_line(&self, line: &str) -> bool {
        let line_lower = line.to_lowercase();
        
        // Enhanced navigation indicators for interface-heavy pages
        let nav_patterns = [
            "menu", "navigation", "nav", "breadcrumb", "skip to", "jump to",
            "home page", "main menu", "site map", "sitemap", "recent changes",
            "options", "filter", "hide", "show", "edit", "talk", "contribs",
            "diff", "hist", "tags:", "mobile edit", "visual edit", "app",
            "dashboard", "wizard", "tools", "list of", "invert selection"
        ];

        // Check for interface patterns
        let interface_patterns = [
            "diffhist", "+", "−", "15:43", "[1.", "talk contribs",
            "(hidden tag)", "android app", "ios app", "mobile web"
        ];

        nav_patterns.iter().any(|pattern| line_lower.contains(pattern)) ||
        interface_patterns.iter().any(|pattern| line_lower.contains(pattern))
    }

    /// Check if a line is low quality content
    fn is_low_quality_line(&self, line: &str) -> bool {
        let line_lower = line.to_lowercase();
        
        // CRITICAL: Target CSS and styling content first
        if line.contains(".mw-parser-output") || line.contains("navbox") ||
           line.contains("display:") || line.contains("margin:") ||
           line.contains("padding:") || line.contains("font-weight:") ||
           line.contains("background-color:") || line.contains("border:") ||
           line.contains("content:") || line.contains("::after") ||
           line.contains("::before") || line.contains(".hlist") ||
           line.contains("box-sizing:") || line.contains("line-height:") ||
           line.contains("text-align:") || line.contains("white-space:") ||
           line.contains("@media") || line.contains("counter-reset:") {
            return true;
        }
        
        // Target specific Wikipedia interface noise
        let interface_noise = [
            "wikiedu", "wikiloop", "dashboard", "assignment wizard", "battlefield",
            "user creation", "account", "tag filter", "namespace", "protection template",
            "edit summary", "citation bot", "content translation", "typos in one click",
            "diffhist", "talk contribs", "mobile edit", "visual edit", "android app",
            "ios app", "hidden tag", "antivandal", "rollback", "manual revert",
            "vtePart of", "vteReligions", "Retrieved from", "Hidden categories:",
            "Articles with", "Pages with", "Webarchive template", "Commons category"
        ];

        // Check for interface noise
        if interface_noise.iter().any(|&noise| line_lower.contains(noise)) {
            return true;
        }

        // Filter lines that are mostly version numbers and technical IDs
        if line.chars().filter(|c| c.is_numeric() || "[]().".contains(*c)).count() > line.len() / 2 {
            return true;
        }

        // Filter lines with excessive technical abbreviations (but be more lenient)
        let tech_abbrevs = line.matches(|c: char| c.is_uppercase()).count();
        if tech_abbrevs > 8 && line.len() < 150 {
            return true;
        }

        // Standard quality checks
        let quality_issues = [
            "loading...", "please wait", "javascript", "enable javascript", 
            "cookies", "privacy policy", "terms of service", "copyright", 
            "all rights reserved"
        ];

        if quality_issues.iter().any(|issue| line_lower.contains(issue)) {
            return true;
        }

        // For index pages, be much more permissive with punctuation
        // Only filter if it's VERY excessive (more than 60% punctuation)
        let punct_count = line.chars().filter(|c| !c.is_alphanumeric() && !c.is_whitespace()).count();
        let total_chars = line.len();
        
        if total_chars > 0 && (punct_count as f32 / total_chars as f32) > 0.6 {
            return true;
        }

        // Be more permissive with repeated characters for index pages
        // Only filter if there are more than 10 repeated characters
        let mut prev_char = '\0';
        let mut repeat_count = 0;
        let mut max_repeat = 0;
        
        for ch in line.chars() {
            if ch == prev_char {
                repeat_count += 1;
                max_repeat = max_repeat.max(repeat_count);
            } else {
                repeat_count = 1;
            }
            prev_char = ch;
        }
        
        max_repeat > 10  // Increased from 5 to 10
    }

    /// Extract and filter keywords from text
    pub fn extract_keywords(&self, text: &str, max_keywords: usize) -> Vec<String> {
        if text.is_empty() {
            return Vec::new();
        }

        // Simple but effective keyword extraction
        let text_lower = text.to_lowercase();
        let words: Vec<&str> = text_lower
            .split_whitespace()
            .filter(|word| {
                word.len() > 3 
                && word.chars().all(|c| c.is_alphabetic())
                && !STOP_WORDS.contains(word)
            })
            .collect();

        // Count word frequencies
        let mut word_counts = std::collections::HashMap::new();
        for word in words {
            *word_counts.entry(word).or_insert(0) += 1;
        }

        // Sort by frequency and take top keywords
        let mut sorted_words: Vec<_> = word_counts.into_iter().collect();
        sorted_words.sort_by(|a, b| b.1.cmp(&a.1));

        sorted_words
            .into_iter()
            .take(max_keywords)
            .filter(|(_, count)| *count >= 2) // Must appear at least twice
            .map(|(word, _)| word.to_string())
            .collect()
    }

    /// Normalize a date string to ISO 8601 format with Z suffix for OpenSearch compatibility
    pub fn normalize_date(&self, date_str: &str) -> Option<String> {
        if date_str.is_empty() {
            return None;
        }

        let trimmed = date_str.trim();
        if trimmed.is_empty() || trimmed == "null" {
            return None;
        }

        // 1. ISO 8601 formats (already correct)
        if let Ok(dt) = DateTime::parse_from_rfc3339(trimmed) {
            let utc_dt = dt.with_timezone(&Utc);
            return Some(utc_dt.format("%Y-%m-%dT%H:%M:%SZ").to_string());
        }

        // 2. RFC 2822 format (e.g., "Fri, 22 Aug 2025 15:05:20 GMT")
        if let Ok(dt) = DateTime::parse_from_rfc2822(trimmed) {
            let utc_dt = dt.with_timezone(&Utc);
            return Some(utc_dt.format("%Y-%m-%dT%H:%M:%SZ").to_string());
        }

        // 3. Common web formats with timezone
        let web_formats_with_tz = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S %z",
            "%d %b %Y %H:%M:%S %z",
            "%b %d, %Y %H:%M:%S %z",
        ];

        for format in &web_formats_with_tz {
            if let Ok(dt) = DateTime::parse_from_str(trimmed, format) {
                let utc_dt = dt.with_timezone(&Utc);
                return Some(utc_dt.format("%Y-%m-%dT%H:%M:%SZ").to_string());
            }
        }

        // 4. Naive datetime formats (assume UTC)
        let naive_formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%m-%d-%Y %H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
            "%b %d, %Y %H:%M:%S",
            "%d %b %Y %H:%M:%S",
            "%B %d, %Y %H:%M:%S",
            "%d %B %Y %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%d.%m.%Y %H:%M:%S",
        ];

        for format in &naive_formats {
            if let Ok(ndt) = NaiveDateTime::parse_from_str(trimmed, format) {
                let utc_dt = Utc.from_utc_datetime(&ndt);
                return Some(utc_dt.format("%Y-%m-%dT%H:%M:%SZ").to_string());
            }
        }

        // 5. US format with AM/PM (e.g., "7/29/2025, 9:28:40 AM")
        let am_pm_formats = [
            "%m/%d/%Y, %I:%M:%S %p",
            "%m/%d/%Y %I:%M:%S %p",
            "%d/%m/%Y, %I:%M:%S %p",
            "%d/%m/%Y %I:%M:%S %p",
            "%m-%d-%Y, %I:%M:%S %p",
            "%m-%d-%Y %I:%M:%S %p",
            "%b %d, %Y, %I:%M:%S %p",
            "%B %d, %Y, %I:%M:%S %p",
        ];

        for format in &am_pm_formats {
            if let Ok(ndt) = NaiveDateTime::parse_from_str(trimmed, format) {
                let utc_dt = Utc.from_utc_datetime(&ndt);
                return Some(utc_dt.format("%Y-%m-%dT%H:%M:%SZ").to_string());
            }
        }

        // 6. Date-only formats (set time to 00:00:00 UTC)
        let date_only_formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y", 
            "%m-%d-%Y",
            "%d-%m-%Y",
            "%b %d, %Y",
            "%d %b %Y",
            "%B %d, %Y",
            "%d %B %Y",
            "%Y/%m/%d",
            "%d.%m.%Y",
            "%Y.%m.%d",
        ];

        for format in &date_only_formats {
            if let Ok(nd) = NaiveDate::parse_from_str(trimmed, format) {
                if let Some(ndt) = nd.and_hms_opt(0, 0, 0) {
                    let utc_dt = Utc.from_utc_datetime(&ndt);
                    return Some(utc_dt.format("%Y-%m-%dT%H:%M:%SZ").to_string());
                }
            }
        }

        // If no format matches, return None to remove the field
        None
    }

    /// Clean all date fields in structured data recursively
    pub fn clean_structured_data_dates(&self, value: &mut Value) {
        match value {
            Value::Object(map) => {
                let mut to_remove = Vec::new();
                let mut to_update = Vec::new();

                for (key, val) in map.iter() {
                    // Check if this field name suggests it contains a date
                    let is_date_field = key.to_lowercase().contains("date") ||
                                       key.to_lowercase().contains("time") ||
                                       key.to_lowercase().contains("published") ||
                                       key.to_lowercase().contains("modified") ||
                                       key.to_lowercase().contains("created") ||
                                       key.to_lowercase().contains("updated") ||
                                       key.to_lowercase().contains("buildtime");

                    if is_date_field {
                        if let Value::String(date_str) = val {
                            if let Some(normalized) = self.normalize_date(date_str) {
                                to_update.push((key.clone(), Value::String(normalized)));
                            } else {
                                to_remove.push(key.clone());
                            }
                        }
                    } else {
                        // Recursively clean nested objects/arrays
                        match val {
                            Value::Object(_) | Value::Array(_) => {
                                // We'll handle this in the recursive call below
                            }
                            _ => {}
                        }
                    }
                }

                // Remove invalid date fields
                for key in to_remove {
                    map.remove(&key);
                }

                // Update valid date fields
                for (key, new_value) in to_update {
                    map.insert(key, new_value);
                }

                // Recursively clean nested objects
                for val in map.values_mut() {
                    self.clean_structured_data_dates(val);
                }
            }
            Value::Array(arr) => {
                for item in arr.iter_mut() {
                    self.clean_structured_data_dates(item);
                }
            }
            _ => {}
        }
    }

    /// Clean all date fields in a JSON string and return cleaned JSON
    pub fn clean_json_dates(&self, json_str: &str) -> Option<String> {
        if let Ok(mut value) = serde_json::from_str::<Value>(json_str) {
            self.clean_structured_data_dates(&mut value);
            serde_json::to_string(&value).ok()
        } else {
            None
        }
    }

    /// Clean date fields in a HashMap<String, String>
    pub fn clean_hashmap_dates(&self, map: &mut HashMap<String, String>) {
        let mut to_remove = Vec::new();
        let mut to_update = Vec::new();

        for (key, value) in map.iter() {
            // Check if this field name suggests it contains a date
            let is_date_field = key.to_lowercase().contains("date") ||
                               key.to_lowercase().contains("time") ||
                               key.to_lowercase().contains("published") ||
                               key.to_lowercase().contains("modified") ||
                               key.to_lowercase().contains("created") ||
                               key.to_lowercase().contains("updated") ||
                               key.to_lowercase().contains("buildtime");

            if is_date_field {
                if let Some(normalized) = self.normalize_date(value) {
                    to_update.push((key.clone(), normalized));
                } else {
                    to_remove.push(key.clone());
                }
            }
        }

        // Remove invalid date fields
        for key in to_remove {
            map.remove(&key);
        }

        // Update valid date fields
        for (key, new_value) in to_update {
            map.insert(key, new_value);
        }
    }
}
