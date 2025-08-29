use std::collections::{HashMap, HashSet};
use once_cell::sync::Lazy;
use regex::Regex;
use url::Url;
use crate::types::{ProcessedDocument, SemanticInfo};

// --- Static HashMaps and Vecs for keywords using Lazy ---

// Domain scores, converted from Python config
static DOMAIN_SCORES: Lazy<HashMap<&str, f32>> = Lazy::new(|| {
    let mut m = HashMap::new();
    // High authority
    m.insert("wikipedia.org", 0.9);
    m.insert("github.com", 0.85);
    m.insert("stackoverflow.com", 0.8);
    m.insert("arxiv.org", 0.85);
    m.insert("nature.com", 0.9);
    m.insert("science.org", 0.9);
    m.insert("pubmed.ncbi.nlm.nih.gov", 0.85);
    // Edu
    m.insert(".edu", 0.8);
    m.insert(".ac.uk", 0.8);
    // Gov
    m.insert(".gov", 0.75);
    m.insert(".mil", 0.7);
    // News
    m.insert("reuters.com", 0.8);
    m.insert("bbc.com", 0.8);
    m.insert("cnn.com", 0.7);
    m.insert("npr.org", 0.75);
    // Tech
    m.insert("techcrunch.com", 0.7);
    m.insert("arstechnica.com", 0.75);
    m.insert("wired.com", 0.7);
    // TLDs
    m.insert(".org", 0.6);
    m.insert(".com", 0.5);
    m.insert(".net", 0.45);
    m.insert(".info", 0.4);
    m.insert(".biz", 0.35);
    m
});

// Keyword-based indicators
static EDUCATIONAL_INDICATORS: Lazy<HashMap<&str, Vec<&str>>> = Lazy::new(|| {
    let mut m = HashMap::new();
    m.insert("strong", vec!["tutorial", "guide", "documentation", "manual", "reference", "api", "how-to"]);
    m.insert("medium", vec!["example", "demo", "introduction", "overview", "basics", "fundamentals"]);
    m.insert("weak", vec!["blog", "news", "announcement", "release"]);
    m
});

static QUALITY_INDICATORS: Lazy<HashMap<&str, Vec<&str>>> = Lazy::new(|| {
    let mut m = HashMap::new();
    m.insert("positive", vec!["detailed", "comprehensive", "complete", "thorough", "in-depth"]);
    m.insert("negative", vec!["broken", "outdated", "deprecated", "old", "legacy"]);
    m
});

static CITATION_PATTERNS: Lazy<Vec<Regex>> = Lazy::new(|| {
    vec![
        Regex::new(r"\[\d+\]").unwrap(),
        Regex::new(r"\(\d{4}\)").unwrap(),
        Regex::new(r"doi:").unwrap(),
        Regex::new(r"isbn:").unwrap(),
        Regex::new(r"arxiv:").unwrap(),
        Regex::new(r"according to").unwrap(),
        Regex::new(r"research shows").unwrap(),
        Regex::new(r"study found").unwrap(),
        Regex::new(r"published in").unwrap(),
    ]
});

static CREDENTIAL_INDICATORS: Lazy<Vec<&str>> = Lazy::new(|| {
    vec!["phd", "ph.d", "doctor", "professor", "researcher", "expert", "scientist", "engineer", "certified", "author:", "by:", "written by"]
});

static INSTITUTIONAL_INDICATORS: Lazy<Vec<&str>> = Lazy::new(|| {
    vec!["university", "institute", "research center", "official", "documentation", "specification", "standard", "rfc", "ieee", "acm"]
});

pub struct ContentScorer;

impl ContentScorer {
    pub fn new() -> Self {
        Self {}
    }

    pub fn calculate_domain_score(&self, url_str: &str) -> f32 {
        if url_str.is_empty() { return 0.3; }
        
        if let Ok(parsed_url) = Url::parse(url_str) {
            if let Some(domain) = parsed_url.domain() {
                let domain = domain.to_lowercase();
                // Check exact match
                if let Some(&score) = DOMAIN_SCORES.get(domain.as_str()) {
                    return score;
                }
                // Check TLD patterns
                for (pattern, &score) in DOMAIN_SCORES.iter() {
                    if pattern.starts_with('.') && domain.ends_with(pattern) {
                        return score;
                    }
                }
            }
        }
        0.3 // Default score
    }

    pub fn calculate_content_quality_score(&self, doc: &ProcessedDocument) -> f32 {
        if doc.main_content.is_empty() { return 0.1; }

        let weights: HashMap<&str, f32> = [
            ("length", 0.2),
            ("structure", 0.2),
            ("content_type", 0.15),
            ("language", 0.1),
            ("metadata", 0.1),
            ("technical", 0.1),
            ("authoritativeness", 0.1),
            ("completeness", 0.05),
        ].iter().cloned().collect();

        let scores: HashMap<&str, f32> = [
            ("length", self.calculate_length_score(doc.word_count)),
            ("structure", self.calculate_structure_score(doc)),
            ("content_type", self.calculate_content_type_score(&doc.main_content, &doc.title)),
            ("language", self.calculate_language_quality_score(&doc.main_content)),
            ("metadata", self.calculate_metadata_score(doc)),
            ("technical", self.calculate_technical_bonus(&doc.main_content)),
            ("authoritativeness", self.calculate_authoritativeness_score(&doc.main_content, &doc.title)),
            ("completeness", 1.0), // Placeholder, completeness is complex
        ].iter().cloned().collect();

        weights.keys().map(|&k| weights[k] * scores[k]).sum()
    }

    fn calculate_length_score(&self, word_count: usize) -> f32 {
        if word_count < 30 { 0.05 }
        else if word_count < 50 { 0.15 }
        else if word_count < 75 { 0.4 }
        else if word_count < 150 { 0.8 }
        else if word_count < 300 { 1.3 }
        else if word_count <= 1000 { 1.5 }
        else if word_count <= 3000 { 1.4 }
        else { 1.2 }
    }
    
    fn calculate_structure_score(&self, doc: &ProcessedDocument) -> f32 {
        let mut score = 1.0;
        if doc.main_content.contains("```") {
            score *= 1.2;
        }
        if doc.semantic_info.headings_count >= 3 { score *= 1.15; }
        else if doc.semantic_info.headings_count >= 1 { score *= 1.05; }
        
        score
    }

    fn calculate_content_type_score(&self, content: &str, title: &str) -> f32 {
        let content_lower = content.to_lowercase();
        let title_lower = title.to_lowercase();
        let combined_text = format!("{} {}", content_lower, title_lower);
        let mut score = 1.0;

        for (strength, indicators) in EDUCATIONAL_INDICATORS.iter() {
            if indicators.iter().any(|ind| combined_text.contains(ind)) {
                score *= match *strength {
                    "strong" => 1.4,
                    "medium" => 1.25,
                    _ => 1.1,
                };
                break;
            }
        }
        
        let positive_count = QUALITY_INDICATORS["positive"].iter().filter(|w| combined_text.contains(*w)).count();
        let negative_count = QUALITY_INDICATORS["negative"].iter().filter(|w| combined_text.contains(*w)).count();
        
        score *= 1.0 + (positive_count as f32 * 0.08);
        score *= 1.0 - (negative_count as f32 * 0.15);

        score.max(0.1)
    }

    fn calculate_language_quality_score(&self, content: &str) -> f32 {
        if content.is_empty() { return 0.1; }
        let mut score = 1.0;
        let len = content.len() as f32;

        let cap_ratio = content.chars().filter(|c| c.is_uppercase()).count() as f32 / len;
        if (0.02..=0.08).contains(&cap_ratio) { score *= 1.1; }
        else if cap_ratio > 0.15 { score *= 0.8; }
        
        let words: Vec<&str> = content.split_whitespace().collect();
        if !words.is_empty() {
            let unique_words: HashSet<_> = words.iter().map(|w| w.to_lowercase()).collect();
            let diversity = unique_words.len() as f32 / words.len() as f32;
            if diversity > 0.4 { score *= 1.1; }
        }

        score
    }
    
    fn calculate_metadata_score(&self, doc: &ProcessedDocument) -> f32 {
        let mut score = 1.0;
        if (10..=120).contains(&doc.title.len()) { score *= 1.1; }
        if doc.title.to_lowercase().split_whitespace().any(|w| ["how", "guide", "tutorial", "api"].contains(&w)) {
            score *= 1.05;
        }
        if doc.description.len() > 50 { score *= 1.05; }
        if doc.author_name.is_some() { score *= 1.02; }
        if doc.published_date.is_some() { score *= 1.02; }
        score
    }

    fn calculate_technical_bonus(&self, content: &str) -> f32 {
    let mut score: f32 = 1.0;
        let content_lower = content.to_lowercase();
        if content.contains("```") || content.contains("<code>") { score *= 1.25; }
        if content.contains("def ") || content.contains("function ") { score *= 1.15; }
        if content_lower.contains("class ") { score *= 1.1; }
        score.min(2.5)
    }
    
    fn calculate_authoritativeness_score(&self, content: &str, title: &str) -> f32 {
        let mut score = 1.0;
        let content_lower = content.to_lowercase();
        let title_lower = title.to_lowercase();

        let citation_count: usize = CITATION_PATTERNS.iter().map(|pat| pat.find_iter(&content_lower).count()).sum();
        if citation_count > 0 { score *= 1.0 + (citation_count as f32 * 0.1).min(0.5); }
        
        if CREDENTIAL_INDICATORS.iter().any(|ind| content_lower.contains(ind) || title_lower.contains(ind)) {
            score *= 1.1;
        }
        if INSTITUTIONAL_INDICATORS.iter().any(|ind| content_lower.contains(ind) || title_lower.contains(ind)) {
            score *= 1.15;
        }
        
        score.min(2.0)
    }
}