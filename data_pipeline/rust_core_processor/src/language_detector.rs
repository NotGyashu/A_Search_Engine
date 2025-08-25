use whatlang::{detect, Lang};
use url::Url;
use std::collections::HashSet;
use once_cell::sync::Lazy;

// English domain TLDs and common English domains
static ENGLISH_DOMAINS: Lazy<HashSet<&'static str>> = Lazy::new(|| {
    [
        // Generic TLDs
        "com", "org", "net", "edu", "gov", "mil", "int",
        // Country TLDs that are primarily English
        "us", "uk", "ca", "au", "nz", "ie", "za",
        // Common subdomains
        "www", "en", "english"
    ].into_iter().collect()
});

static ENGLISH_DOMAIN_NAMES: Lazy<HashSet<&'static str>> = Lazy::new(|| {
    [
        "google", "facebook", "twitter", "youtube", "reddit", "stackoverflow",
        "github", "microsoft", "apple", "amazon", "wikipedia", "linkedin",
        "instagram", "netflix", "spotify", "dropbox", "slack", "zoom",
        "techcrunch", "engadget", "theverge", "wired", "ars-technica",
        "hacker-news", "medium", "substack", "wordpress", "blogspot"
    ].into_iter().collect()
});

pub struct FastLanguageDetector;

impl FastLanguageDetector {
    /// Ultra-fast language detection combining URL analysis and content detection
    pub fn detect_language(text: &str, url: &str) -> Option<String> {
        // Early filtering for empty content
        if text.trim().is_empty() {
            return None;
        }
        
        // 1. Check URL for English indicators (fastest)
        if !url.is_empty() {
            if let Some(lang) = Self::detect_from_url(url) {
                if lang == "en" {
                    return Some("en".to_string());
                }
            }
        }
        
        // 2. Check HTML lang attribute (very fast)
        if let Some(lang) = Self::extract_html_lang(text) {
            return Some(lang);
        }
        
        // 3. Use whatlang for content detection (still very fast)
        Self::detect_from_content(text)
    }
    
    /// Check if content is English using fast detection
    pub fn is_english(text: &str, url: &str) -> bool {
        Self::detect_language(text, url)
            .map(|lang| lang == "en")
            .unwrap_or(false)
    }
    
    /// Extract language from URL domain and path
    fn detect_from_url(url: &str) -> Option<String> {
        if let Ok(parsed_url) = Url::parse(url) {
            // Check domain for English indicators
            if let Some(domain) = parsed_url.domain() {
                let domain_lower = domain.to_lowercase();
                
                // Check for explicit English subdomains
                if domain_lower.starts_with("en.") || domain_lower.starts_with("english.") {
                    return Some("en".to_string());
                }
                
                // Check for known English domains
                for english_domain in ENGLISH_DOMAIN_NAMES.iter() {
                    if domain_lower.contains(english_domain) {
                        return Some("en".to_string());
                    }
                }
                
                // Check TLD
                let parts: Vec<&str> = domain_lower.split('.').collect();
                if let Some(tld) = parts.last() {
                    if ENGLISH_DOMAINS.contains(tld) {
                        return Some("en".to_string());
                    }
                }
            }
            
            // Check path for language indicators
            let path = parsed_url.path().to_lowercase();
            if path.contains("/en/") || path.contains("/english/") {
                return Some("en".to_string());
            }
            
            // Check for non-English path indicators
            let non_english_indicators = [
                "/de/", "/es/", "/fr/", "/it/", "/pt/", "/ru/", "/zh/", "/ja/", "/ko/",
                "/deutsch/", "/espanol/", "/francais/", "/italiano/", "/portuguese/"
            ];
            
            for indicator in non_english_indicators {
                if path.contains(indicator) {
                    return Some("non-en".to_string());
                }
            }
        }
        
        None
    }
    
    /// Extract language from HTML lang attribute
    fn extract_html_lang(html: &str) -> Option<String> {
        // Fast regex-free extraction for common patterns
        if let Some(start) = html.find("lang=") {
            let substr = &html[start + 5..];
            
            // Handle both quoted and unquoted attributes
            let lang_value = if substr.starts_with('"') {
                substr.get(1..)?.split('"').next()?
            } else if substr.starts_with('\'') {
                substr.get(1..)?.split('\'').next()?
            } else {
                substr.split_whitespace().next()?.split('>').next()?
            };
            
            // Extract language code (first 2 characters)
            if lang_value.len() >= 2 {
                let lang_code = &lang_value[..2].to_lowercase();
                return Some(lang_code.to_string());
            }
        }
        
        None
    }
    
    /// Detect language from content using whatlang
    fn detect_from_content(text: &str) -> Option<String> {
        // Clean text for better detection
        let clean_text = Self::clean_text_for_detection(text);
        
        // Use whatlang for ultra-fast detection
        if let Some(info) = detect(&clean_text) {
            let lang_code = match info.lang() {
                Lang::Eng => "en",
                Lang::Spa => "es", 
                Lang::Fra => "fr",
                Lang::Deu => "de",
                Lang::Ita => "it",
                Lang::Por => "pt",
                Lang::Rus => "ru",
                Lang::Jpn => "ja",
                Lang::Kor => "ko",
                Lang::Cmn => "zh",
                _ => return None, // Reject other languages
            };
            
            // Only return if confidence is reasonable
            if info.confidence() > 0.7 {
                Some(lang_code.to_string())
            } else {
                None
            }
        } else {
            None
        }
    }
    
    /// Clean text for better language detection
    fn clean_text_for_detection(text: &str) -> String {
        // Remove HTML tags, URLs, and other noise
        let mut clean = text.to_string();
        
        // Remove HTML tags (simple but fast)
        while let Some(start) = clean.find('<') {
            if let Some(end) = clean[start..].find('>') {
                clean.replace_range(start..start + end + 1, " ");
            } else {
                break;
            }
        }
        
        // Remove URLs
        clean = clean.split_whitespace()
            .filter(|word| !word.starts_with("http://") && !word.starts_with("https://"))
            .collect::<Vec<_>>()
            .join(" ");
        
        // Take first 1000 characters for fast detection
        if clean.len() > 1000 {
            clean.truncate(1000);
        }
        
        clean
    }
    
    /// Get detailed language detection info
    pub fn get_language_info(text: &str, url: &str) -> (Option<String>, f64, bool) {
        let detected_lang = Self::detect_language(text, url);
        let is_english_domain = !url.is_empty() && Self::detect_from_url(url) == Some("en".to_string());
        
        // Calculate confidence based on detection method
        let confidence = if detected_lang.is_some() {
            if is_english_domain { 0.95 } else { 0.8 }
        } else {
            0.0
        };
        
        (detected_lang, confidence, is_english_domain)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_english_detection() {
        let text = "This is a test of English language detection.";
        assert_eq!(FastLanguageDetector::detect_language(text, ""), Some("en".to_string()));
        assert!(FastLanguageDetector::is_english(text, ""));
    }
    
    #[test]
    fn test_url_detection() {
        assert!(FastLanguageDetector::is_english("", "https://techcrunch.com/article"));
        assert!(FastLanguageDetector::is_english("", "https://en.wikipedia.org/wiki/Test"));
        assert!(!FastLanguageDetector::is_english("", "https://es.wikipedia.org/wiki/Test"));
    }
    
    #[test]
    fn test_html_lang_extraction() {
        let html = r#"<html lang="en"><body>Test</body></html>"#;
        assert_eq!(FastLanguageDetector::extract_html_lang(html), Some("en".to_string()));
    }
}
