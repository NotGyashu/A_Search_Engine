use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use pyo3::prelude::*;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessedDocument {
    // Core content
    pub main_content: String,
    pub title: String,
    pub description: String,
    pub language: String,
    pub keywords: Vec<String>,
    
    // Content structure
    pub headings: Vec<Heading>,
    pub images: Vec<ImageInfo>,
    pub links: Vec<LinkInfo>,
    pub table_of_contents: Vec<Heading>,
    
    // Content analysis
    pub word_count: usize,
    pub content_quality_score: f32,
    pub is_technical_content: bool,
    pub content_categories: Vec<String>,
    
    // Metadata and structured data
    pub canonical_url: String,
    pub published_date: Option<String>,
    pub modified_date: Option<String>,
    pub author_info: AuthorInfo,
    pub structured_data: StructuredData,
    pub meta_tags: HashMap<String, String>,
    pub open_graph: HashMap<String, String>,
    pub twitter_cards: HashMap<String, String>,
    
    // Icons and favicon
    pub icons: HashMap<String, String>,
    
    // Chunking
    pub text_chunks: Vec<String>,
    
    // Semantic analysis
    pub semantic_info: SemanticInfo,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Heading {
    pub level: u8,
    pub text: String,
    pub id: String,
    pub class: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImageInfo {
    pub src: String,
    pub alt: String,
    pub title: String,
    pub width: String,
    pub height: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LinkInfo {
    pub href: String,
    pub text: String,
    pub rel: Vec<String>,
    pub title: String,
    pub is_external: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthorInfo {
    pub name: String,
    pub url: String,
    pub bio: String,
    pub social_links: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StructuredData {
    pub json_ld: Vec<serde_json::Value>,
    pub microdata: Vec<HashMap<String, String>>,
    pub rdfa: Vec<HashMap<String, String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SemanticInfo {
    pub word_count: usize,
    pub sentence_count: usize,
    pub paragraph_count: usize,
    pub reading_time_minutes: f32,
    pub content_quality_score: f32,
    pub is_technical_content: bool,
    pub headings_count: usize,
    pub images_count: usize,
    pub links_count: usize,
    pub technical_score: f32,
    pub avg_sentence_length: f32,
    pub content_density: f32,
}

impl Default for ProcessedDocument {
    fn default() -> Self {
        Self {
            main_content: String::new(),
            title: String::new(),
            description: String::new(),
            language: String::new(),
            keywords: Vec::new(),
            headings: Vec::new(),
            images: Vec::new(),
            links: Vec::new(),
            table_of_contents: Vec::new(),
            word_count: 0,
            content_quality_score: 0.0,
            is_technical_content: false,
            content_categories: Vec::new(),
            canonical_url: String::new(),
            published_date: None,
            modified_date: None,
            author_info: AuthorInfo::default(),
            structured_data: StructuredData::default(),
            meta_tags: HashMap::new(),
            open_graph: HashMap::new(),
            twitter_cards: HashMap::new(),
            icons: HashMap::new(),
            text_chunks: Vec::new(),
            semantic_info: SemanticInfo::default(),
        }
    }
}

impl Default for AuthorInfo {
    fn default() -> Self {
        Self {
            name: String::new(),
            url: String::new(),
            bio: String::new(),
            social_links: Vec::new(),
        }
    }
}

impl Default for StructuredData {
    fn default() -> Self {
        Self {
            json_ld: Vec::new(),
            microdata: Vec::new(),
            rdfa: Vec::new(),
        }
    }
}

impl Default for SemanticInfo {
    fn default() -> Self {
        Self {
            word_count: 0,
            sentence_count: 0,
            paragraph_count: 0,
            reading_time_minutes: 0.0,
            content_quality_score: 0.0,
            is_technical_content: false,
            headings_count: 0,
            images_count: 0,
            links_count: 0,
            technical_score: 0.0,
            avg_sentence_length: 0.0,
            content_density: 0.0,
        }
    }
}

// Helper function to convert structs to Python objects
impl ToPyObject for Heading {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        let dict = pyo3::types::PyDict::new_bound(py);
        dict.set_item("level", self.level).unwrap();
        dict.set_item("text", &self.text).unwrap();
        dict.set_item("id", &self.id).unwrap();
        dict.set_item("class", &self.class).unwrap();
        dict.into()
    }
}

impl ToPyObject for ImageInfo {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        let dict = pyo3::types::PyDict::new_bound(py);
        dict.set_item("src", &self.src).unwrap();
        dict.set_item("alt", &self.alt).unwrap();
        dict.set_item("title", &self.title).unwrap();
        dict.set_item("width", &self.width).unwrap();
        dict.set_item("height", &self.height).unwrap();
        dict.into()
    }
}

impl ToPyObject for LinkInfo {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        let dict = pyo3::types::PyDict::new_bound(py);
        dict.set_item("href", &self.href).unwrap();
        dict.set_item("text", &self.text).unwrap();
        dict.set_item("rel", &self.rel).unwrap();
        dict.set_item("title", &self.title).unwrap();
        dict.set_item("is_external", self.is_external).unwrap();
        dict.into()
    }
}

impl ToPyObject for AuthorInfo {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        let dict = pyo3::types::PyDict::new_bound(py);
        dict.set_item("name", &self.name).unwrap();
        dict.set_item("url", &self.url).unwrap();
        dict.set_item("bio", &self.bio).unwrap();
        dict.set_item("social_links", &self.social_links).unwrap();
        dict.into()
    }
}

impl ToPyObject for StructuredData {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        let dict = pyo3::types::PyDict::new_bound(py);
        
        // Convert JSON values to strings for Python compatibility
        let json_ld_strs: Vec<String> = self.json_ld.iter()
            .map(|v| serde_json::to_string(v).unwrap_or_default())
            .collect();
        
        dict.set_item("json_ld", json_ld_strs).unwrap();
        dict.set_item("microdata", &self.microdata).unwrap();
        dict.set_item("rdfa", &self.rdfa).unwrap();
        dict.into()
    }
}

impl ToPyObject for SemanticInfo {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        let dict = pyo3::types::PyDict::new_bound(py);
        dict.set_item("word_count", self.word_count).unwrap();
        dict.set_item("sentence_count", self.sentence_count).unwrap();
        dict.set_item("paragraph_count", self.paragraph_count).unwrap();
        dict.set_item("reading_time_minutes", self.reading_time_minutes).unwrap();
        dict.set_item("content_quality_score", self.content_quality_score).unwrap();
        dict.set_item("is_technical_content", self.is_technical_content).unwrap();
        dict.set_item("headings_count", self.headings_count).unwrap();
        dict.set_item("images_count", self.images_count).unwrap();
        dict.set_item("links_count", self.links_count).unwrap();
        dict.set_item("technical_score", self.technical_score).unwrap();
        dict.set_item("avg_sentence_length", self.avg_sentence_length).unwrap();
        dict.set_item("content_density", self.content_density).unwrap();
        dict.into()
    }
}
