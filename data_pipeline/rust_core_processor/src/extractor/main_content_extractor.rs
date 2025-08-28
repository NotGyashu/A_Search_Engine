use tl::{VDom, Parser, Node};
use crate::ProcessedDocument;
use crate::extractor::metadata_extractor;

pub struct MainContentExtractor;

impl MainContentExtractor {
    pub fn extract_main_content(&self, dom: &VDom, parser: &Parser)-> String {
        // Priority selectors for main content
        let content_selectors = [
            "main", "article", ".content", ".post-content", ".entry-content",
            "#content", ".article-body", ".post-body", ".article-text",
            "[role='main']", ".main-content", ".page-content", ".content-wrapper",
            ".story-content", ".article-wrapper", ".text-content"
        ];

        // Try each selector and append all meaningful content
        let mut main_text = String::new();
        for selector in &content_selectors {
            if let Some(content_node) = dom.query_selector(selector).and_then(|mut iter| iter.next()) {
                if let Some(node) = content_node.get(parser) {
                    let content = self.extract_clean_text_from_node(node, parser);
                    if content.trim().len() > 50 {
                        main_text.push_str(&content);
                        main_text.push(' ');
                    }
                }
            }
        }

        // Fallback: entire body
        if main_text.trim().is_empty() {
            if let Some(body_node) = dom.query_selector("body").and_then(|mut iter| iter.next()) {
                if let Some(node) = body_node.get(parser) {
                    main_text.push_str(&self.extract_clean_text_from_node(node, parser));
                }
            }
        }

        main_text.trim().to_string()
    }

    fn extract_clean_text_from_node(&self, node: &Node, parser: &Parser) -> String {
        let mut clean_text = String::new();

        match node {
            Node::Tag(tag) => {
                let tag_name = tag.name().as_utf8_str().to_lowercase();
                if matches!(tag_name.as_str(), 
                    "script" | "style" | "noscript" | "nav" | "header" | "footer" |
                    "aside" | "menu" | "menuitem" | "figure" | "figcaption" |
                    "button" | "input" | "select" | "textarea" | "form" | "iframe"
                ) {
                    return String::new();
                }

                let attrs = tag.attributes();
                if let Some(class_val) = attrs.get("class").flatten() {
                    let class_str = class_val.as_utf8_str().to_lowercase();
                    if ["nav","menu","sidebar","footer","header","ad","popup","banner"].iter().any(|n| class_str.contains(n)) {
                        return String::new();
                    }
                }

                if let Some(id_val) = attrs.get("id").flatten() {
                    let id_str = id_val.as_utf8_str().to_lowercase();
                    if ["nav","menu","sidebar","footer","header","ad","popup","banner"].iter().any(|n| id_str.contains(n)) {
                        return String::new();
                    }
                }

                for child in tag.children().top().iter() {
                    if let Some(child_node) = child.get(parser) {
                        clean_text.push_str(&self.extract_clean_text_from_node(child_node, parser));
                        clean_text.push(' ');
                    }
                }
            }
            Node::Raw(text) => {
                let txt = text.as_utf8_str();
                let txt_cleaned = txt.replace("\u{200b}", "")
                                     .replace("&nbsp;", " ")
                                     .replace("\n", " ")
                                     .replace("\r", " ")
                                     .trim()
                                     .to_string();
                if !txt_cleaned.is_empty() && txt_cleaned.len() > 20 {
                    clean_text.push_str(&txt_cleaned);
                    clean_text.push(' ');
                }
            }
            Node::Comment(_) => {}
            // _ => {} // unreachable, all Node variants handled above
        }

        clean_text.split_whitespace().collect::<Vec<_>>().join(" ")
    }
}
