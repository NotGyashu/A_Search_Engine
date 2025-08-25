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
    
    // Content structure - OPTIMIZED: Only primary image and essential headings
    pub headings: Vec<Heading>,
    pub primary_image: Option<ImageInfo>,  // Only the main/featured image
    pub favicon: Option<String>,           // Only favicon URL
    
    // Content analysis
    pub word_count: usize,
    pub content_quality_score: f32,
    pub is_technical_content: bool,
    pub content_categories: Vec<String>,
    
    // Metadata - OPTIMIZED: Only essential fields
    pub canonical_url: Option<String>,     // Only if different from URL
    pub published_date: Option<String>,
    pub modified_date: Option<String>,
    pub author_name: Option<String>,       // Simplified author info
    
    // OPTIMIZED: Extracted essential structured data only
    pub structured_meta: Option<StructuredMeta>,
    
    // Chunking with context
    pub text_chunks_with_context: Vec<ChunkWithContext>,
    
    // Semantic analysis
    pub semantic_info: SemanticInfo,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Heading {
    pub level: u8,
    pub text: String,
    // Removed: id, class (not useful for search)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImageInfo {
    pub src: String,
    pub alt: String,
    // Removed: title, width, height (not essential for search)
}

// NEW: Optimized chunk with local context
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChunkWithContext {
    pub text_chunk: String,
    pub relevant_headings: Vec<String>,  // Only headings that apply to this chunk
    pub chunk_index: usize,
}

// NEW: Essential structured data only
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StructuredMeta {
    pub article_type: Option<String>,
    pub featured_image: Option<String>,
    pub date_published: Option<String>,
    pub date_modified: Option<String>,
    pub publisher_name: Option<String>,
}

// REMOVED: LinkInfo (not essential for search)
// REMOVED: AuthorInfo (simplified to author_name string)
// REMOVED: StructuredData (replaced with StructuredMeta)

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
            primary_image: None,
            favicon: None,
            word_count: 0,
            content_quality_score: 0.0,
            is_technical_content: false,
            content_categories: Vec::new(),
            canonical_url: None,
            published_date: None,
            modified_date: None,
            author_name: None,
            structured_meta: None,
            text_chunks_with_context: Vec::new(),
            semantic_info: SemanticInfo::default(),
        }
    }
}

// Removed old default implementations for deleted types

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
        dict.into()
    }
}

impl ToPyObject for ImageInfo {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        let dict = pyo3::types::PyDict::new_bound(py);
        dict.set_item("src", &self.src).unwrap();
        dict.set_item("alt", &self.alt).unwrap();
        dict.into()
    }
}

impl ToPyObject for ChunkWithContext {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        let dict = pyo3::types::PyDict::new_bound(py);
        dict.set_item("text_chunk", &self.text_chunk).unwrap();
        dict.set_item("relevant_headings", &self.relevant_headings).unwrap();
        dict.set_item("chunk_index", self.chunk_index).unwrap();
        dict.into()
    }
}

impl ToPyObject for StructuredMeta {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        let dict = pyo3::types::PyDict::new_bound(py);
        if let Some(ref article_type) = self.article_type {
            dict.set_item("article_type", article_type).unwrap();
        }
        if let Some(ref featured_image) = self.featured_image {
            dict.set_item("featured_image", featured_image).unwrap();
        }
        if let Some(ref date_published) = self.date_published {
            dict.set_item("date_published", date_published).unwrap();
        }
        if let Some(ref date_modified) = self.date_modified {
            dict.set_item("date_modified", date_modified).unwrap();
        }
        if let Some(ref publisher_name) = self.publisher_name {
            dict.set_item("publisher_name", publisher_name).unwrap();
        }
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
