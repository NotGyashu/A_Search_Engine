    use std::collections::{HashMap, HashSet};
    use regex::Regex;
    use rust_stemmers::{Algorithm, Stemmer};
    use crate::types::ImageInfo;
    use tl::parse;
    use tl::ParserOptions;   
    use once_cell::sync::Lazy;


    pub struct MetadataExtractor<'a> {
        dom: &'a tl::VDom<'a>,
        parser: &'a tl::Parser<'a>,
        meta_map: HashMap<String, String>,
        json_ld_blocks: Vec<serde_json::Value>,
        title: Option<String>,
        h1: Option<String>,
        meta_nodes: Vec<tl::NodeHandle>,
        link_nodes: Vec<tl::NodeHandle>,
        script_nodes: Vec<tl::NodeHandle>,
        img_nodes: Vec<tl::NodeHandle>,
        time_nodes: Vec<tl::NodeHandle>,
        author_nodes: Vec<tl::NodeHandle>,
        canonical_node: Option<tl::NodeHandle>,
    }
    


    impl<'a> MetadataExtractor<'a> {
    // Helper for recursive author extraction from JSON-LD
    fn extract_name_from_value(val: &serde_json::Value) -> Option<String> {
        match val {
            serde_json::Value::String(s) => Some(s.clone()),
            serde_json::Value::Object(sub_obj) => {
                sub_obj.get("name").and_then(|n| n.as_str()).map(|s| s.to_string())
            },
            serde_json::Value::Array(arr) => arr.get(0).and_then(Self::extract_name_from_value),
            _ => None,
        }
    }
        pub fn new(dom: &'a tl::VDom, parser: &'a tl::Parser) -> Self {
            let mut extractor = Self {
                dom,
                parser,
                meta_map: HashMap::new(),
                json_ld_blocks: Vec::new(),
                title: None,
                h1: None,
                meta_nodes: Vec::new(),
                link_nodes: Vec::new(),
                script_nodes: Vec::new(),
                img_nodes: Vec::new(),
                time_nodes: Vec::new(),
                author_nodes: Vec::new(),
                canonical_node: None,
            };
            extractor.collect_metadata();
            extractor
        }

        pub fn collect_structured_data_nodes(&self) -> Vec<tl::NodeHandle> {
            use std::collections::HashSet;

            let mut nodes = Vec::new();
            let mut seen = HashSet::new(); // track unique NodeHandles

            let mut add_nodes = |new_nodes: Vec<tl::NodeHandle>| {
                for node in new_nodes {
                    if seen.insert(node.clone()) {
                        nodes.push(node);
                    }
                }
            };

            // JSON-LD scripts
            if let Some(jsonld) = self.dom.query_selector("script[type*='ld+json'], script[type*='application/ld+json']") {
                add_nodes(jsonld.collect());
            }

            // Microdata: itemscope
            if let Some(microdata) = self.dom.query_selector("[itemscope]") {
                add_nodes(microdata.collect());
            }

            // RDFa: typeof, property, vocab
            if let Some(rdfa) = self.dom.query_selector("[typeof], [property], [vocab]") {
                add_nodes(rdfa.collect());
            }

            nodes
        }
        fn collect_metadata(&mut self) {
            // Collect all relevant nodes
        self.meta_nodes = self.dom.query_selector("meta").map(|iter| iter.collect::<Vec<_>>()).unwrap_or_default();
        self.link_nodes = self.dom.query_selector("link").map(|iter| iter.collect::<Vec<_>>()).unwrap_or_default();
            self.script_nodes = self.collect_structured_data_nodes();
            self.img_nodes = self.dom.query_selector("img").map(|iter| iter.collect())
        .unwrap_or_else(Vec::new);
            self.time_nodes = self.dom.query_selector("time").map(|iter| iter.collect())
        .unwrap_or_else(Vec::new);
            
            // Author-related selectors
            let author_selectors = [".author-name", ".author", "[data-author]", ".byline .name"];
            self.author_nodes = author_selectors.iter()
                .flat_map(|sel| self.dom.query_selector(sel).map(|iter| iter.collect::<Vec<_>>()).unwrap_or_default().into_iter())
                .collect();
                
            // Canonical URL
            self.canonical_node = self.dom.query_selector("link[rel='canonical']")
                .and_then(|mut iter| iter.next());

            // Parse meta tags into hashmap
            for node in &self.meta_nodes {
                if let Some(tag) = node.get(self.parser).and_then(|n| n.as_tag()) {
                    let attrs = tag.attributes();
                    let property = attrs.get("property").and_then(|p| p.map(|p| p.as_utf8_str()));
                    let name = attrs.get("name").and_then(|n| n.map(|n| n.as_utf8_str()));
                    let content = attrs.get("content").and_then(|c| c.map(|c| c.as_utf8_str()));

                    if let (Some(key), Some(content)) = (property.or(name), content) {
                        self.meta_map.insert(key.to_string(), content.to_string());
                    }
                }
            }

            // Parse JSON-LD blocks
            for node in &self.script_nodes {
                if let Some(node) = node.get(self.parser) {
                    let content = node.inner_text(self.parser);
                    if let Ok(json) = serde_json::from_str(&content) {
                        self.json_ld_blocks.push(json);
                    }
                }
            }

            // Get title and h1
            self.title = self.dom.query_selector("title")
                .and_then(|mut iter| iter.next())
                .and_then(|node| node.get(self.parser))
                .map(|node| node.inner_text(self.parser).trim().to_string());

            self.h1 = self.dom.query_selector("h1")
                .and_then(|mut iter| iter.next())
                .and_then(|node| node.get(self.parser))
                .map(|node| node.inner_text(self.parser).trim().to_string());
        }

        // Title extraction with priority: OG > Twitter > Title tag > H1
        pub fn get_title(&self) -> Option<String> {
            self.meta_map.get("og:title")
                .or_else(|| self.meta_map.get("twitter:title"))
                .cloned()
                .or_else(|| self.title.clone())
                .or_else(|| self.h1.clone())
                .map(|t| t.trim().to_string())
                .filter(|t| !t.is_empty())
        }

        pub fn get_description(&self) -> Option<String> {
        self.meta_map.get("og:description")
            .or_else(|| self.meta_map.get("twitter:description"))
            .or_else(|| self.meta_map.get("description"))
            .cloned()
            .map(|d| d.trim().to_string())
            .filter(|d| !d.is_empty())
        }


    pub fn get_keywords(&self) -> Vec<String> {
    let mut keywords = HashSet::new();

    // 1. Look for modern `article:tag` meta properties
    for node in &self.meta_nodes {
        if let Some(tag) = node.get(self.parser).and_then(|n| n.as_tag()) {
            if let Some(property) = tag
                .attributes()
                .get("property")
                .and_then(|p| p.map(|p_str| p_str.as_utf8_str()))
            {
                if property == "article:tag" {
                    if let Some(content) = tag
                        .attributes()
                        .get("content")
                        .and_then(|c| c.map(|c_str| c_str.as_utf8_str()))
                    {
                        let tag = content.trim().to_string();
                        if !tag.is_empty() && tag.len() >= 3
                            
                        {
                            keywords.insert(tag);
                        }
                    }
                }
            }
        }
    }

    // 2. Fallback to the old "keywords" meta tag
    if keywords.is_empty() {
        if let Some(kw_string) = self.meta_map.get("keywords") {
            for k in kw_string.split(',') {
                let keyword = k.trim().to_string();
                if !keyword.is_empty() && keyword.len() >= 3
                  
                {
                    keywords.insert(keyword);
                }
            }
        }
    }

    
    keywords.into_iter().take(15).collect()
}


        pub fn get_content_type(&self, url: &str) -> String {
    // 1. JSON-LD @type check
    for json in &self.json_ld_blocks {
        if let Some(obj) = json.as_object() {
            if let Some(type_val) = obj.get("@type").and_then(|v| v.as_str()) {
                return type_val.to_lowercase();
            }
        }
    }

    // 2. Gather candidate text
    let mut text = String::new();
    if let Some(desc) = self.get_description() {
        text.push_str(&desc.to_lowercase());
    }
    if let Some(title) = self.get_title() {
        text.push_str(" ");
        text.push_str(&title.to_lowercase());
    }

    let url_lc = url.to_lowercase();
    let mut content_type = "article".to_string();

    // 3. FAQ / Q&A
    if text.contains("faq") || text.contains("question") || text.contains("answer") || text.contains("help") {
        return "faq".to_string();
    }

    // 4. Product / e-commerce
    if text.contains("buy") || text.contains("price") || text.contains("product") ||
       text.contains("cart") || text.contains("shop") || text.contains("add to basket") {
        return "product".to_string();
    }

    // 5. Video
    if text.contains("video") || text.contains("watch") || text.contains("youtube") || url_lc.contains("video") {
        return "video".to_string();
    }

    // 6. Recipe
    if text.contains("recipe") || text.contains("ingredients") || text.contains("cook") || text.contains("servings") {
        return "recipe".to_string();
    }

    // 7. Reviews
    if text.contains("review") || text.contains("rating") || text.contains("stars") {
        return "review".to_string();
    }

    // 8. Blog / News (last fallback before "article")
    if url_lc.contains("blog") || url_lc.contains("news") || url_lc.contains("post") ||
       text.contains("blog") || text.contains("news") || text.contains("article") || text.contains("post") ||
       text.contains("journal") || text.contains("press") || text.contains("update") || text.contains("editorial") {
        return "blog".to_string();
    }

    content_type
}


        pub fn get_primary_image(&self, resolve_url: impl Fn(&str) -> String) -> Option<ImageInfo> {
            // 1. Check JSON-LD
            for json in &self.json_ld_blocks {
                if let Some(obj) = json.as_object() {
                    if let Some(image_val) = obj.get("image") {
                        let url = match image_val {
                            serde_json::Value::String(s) => Some(s.clone()),
                            serde_json::Value::Object(img_obj) => {
                                img_obj.get("url").and_then(|u| u.as_str()).map(|s| s.to_string())
                            }
                            _ => None,
                        };
                        if let Some(u) = url {
                            return Some(ImageInfo { 
                                src: resolve_url(&u), 
                                alt: "Featured image".to_string() 
                            });
                        }
                    }
                }
            }

            // 2. Check OG image
            if let Some(og_image) = self.meta_map.get("og:image") {
                return Some(ImageInfo { 
                    src: resolve_url(og_image), 
                    alt: "Featured image".to_string() 
                });
            }

            // 3. Check first meaningful image
            for node in &self.img_nodes {
                if let Some(tag) = node.get(self.parser).and_then(|n| n.as_tag()) {
                    let attrs = tag.attributes();
                    if let Some(src) = attrs.get("src").and_then(|s| s.map(|s| s.as_utf8_str())) {
                        let src_str = src.to_string();
                        // Skip small icons, logos, favicons
                        if !src_str.contains("icon") && !src_str.contains("logo") && !src_str.contains("favicon") {
                            let alt = attrs.get("alt")
                                .and_then(|a| a.map(|a| a.as_utf8_str().to_string()))
                                .unwrap_or_default();
                            return Some(ImageInfo { 
                                src: resolve_url(&src_str), 
                                alt 
                            });
                        }
                    }
                }
            }

            None
        }

        pub fn get_favicon(&self, resolve_url: impl Fn(&str) -> String) -> Option<String> {
            // Check for favicon links by examining rel attributes directly
            for node in &self.link_nodes {
                if let Some(tag) = node.get(self.parser).and_then(|n| n.as_tag()) {
                    let attrs = tag.attributes();
                    if let Some(rel) = attrs.get("rel").and_then(|r| r.map(|r| r.as_utf8_str())) {
                        let rel_str = rel.to_lowercase();
                        
                        // Check for common favicon rel values
                        if rel_str.contains("icon") || rel_str == "shortcut icon" {
                            if let Some(href) = attrs.get("href").and_then(|h| h.map(|h| h.as_utf8_str())) {
                                let url = resolve_url(&href.to_string());
                                if !url.is_empty() {
                                    return Some(url);
                                }
                            }
                        }
                    }
                }
            }
            
            None
        }


        pub fn get_dates(&self) -> (Option<String>, Option<String>) {
            let mut published_date: Option<String> = None;
            let mut modified_date: Option<String> = None;

            // --- 1. Check meta tags ---
            let pub_keys = ["article:published_time", "datePublished", "date"];
            for key in &pub_keys {
                if let Some(content) = self.meta_map.get(*key) {
                    published_date = Some(content.clone());
                    break;
                }
            }

            let mod_keys = ["article:modified_time", "dateModified", "lastmod"];
            for key in &mod_keys {
                if let Some(content) = self.meta_map.get(*key) {
                    modified_date = Some(content.clone());
                    break;
                }
            }

            // --- 2. Check JSON-LD ---
            for json in &self.json_ld_blocks {
                if let Some(obj) = json.as_object() {
                    if published_date.is_none() {
                        if let Some(date_pub) = obj.get("datePublished").and_then(|v| v.as_str()) {
                            published_date = Some(date_pub.to_string());
                        }
                    }
                    if modified_date.is_none() {
                        if let Some(date_mod) = obj.get("dateModified").and_then(|v| v.as_str()) {
                            modified_date = Some(date_mod.to_string());
                        }
                    }
                }
            }

            // --- 3. Fallback: <time> elements ---
            if published_date.is_none() {
                for node in &self.time_nodes {
                    if let Some(tag) = node.get(self.parser).and_then(|n| n.as_tag()) {
                        if let Some(datetime) = tag.attributes().get("datetime")
                            .and_then(|d| d.map(|d| d.as_utf8_str())) 
                        {
                            published_date = Some(datetime.to_string());
                            break;
                        }
                    }
                }
            }

            (published_date, modified_date)
        }


        pub fn get_author(&self) -> Option<String> {
            // 1. Check specific meta tags first
            if let Some(author) = self.meta_map.get("article:author").or_else(|| self.meta_map.get("author")) {
                let author = author.trim();
                if !author.is_empty() { return Some(author.to_string()); }
            }

            // 2. Check JSON-LD with a robust parser
            for json in &self.json_ld_blocks {
                if let Some(obj) = json.as_object() {
                    // Try author field, then publisher
                    if let Some(author_val) = obj.get("author") {
                        if let Some(name) = Self::extract_name_from_value(author_val) {
                            if !name.trim().is_empty() { return Some(name.trim().to_string()); }
                        }
                    }
                    if let Some(publisher_val) = obj.get("publisher") {
                        if let Some(name) = Self::extract_name_from_value(publisher_val) {
                            if !name.trim().is_empty() { return Some(name.trim().to_string()); }
                        }
                    }
                }
            }

            // 3. Fallback to CSS selectors
            for node in &self.author_nodes {
                if let Some(element) = node.get(self.parser) {
                    let author_text = element.inner_text(self.parser).trim().to_string();
                    if !author_text.is_empty() && author_text.len() < 100 {
                        return Some(author_text);
                    }
                }
            }

            None
        }


        pub fn get_canonical_url(&self, base_url: &str) -> Option<String> {
            if let Some(node) = self.canonical_node {
                if let Some(tag) = node.get(self.parser).and_then(|n| n.as_tag()) {
                    if let Some(href) = tag.attributes().get("href").and_then(|h| h.map(|h| h.as_utf8_str())) {
                        let canonical_url = href.to_string();
                        if canonical_url != base_url && !canonical_url.is_empty() {
                            return Some(canonical_url);
                        }
                    }
                }
            }
            None
        }


        
        // Helper function for content categorization (unchanged from original)
        pub fn get_content_categories(content: &str) -> Vec<String> {
            let mut categories = Vec::new();
        let re = Regex::new(r"\b\w+\b").unwrap();
            let tokens: Vec<String> = re
                .find_iter(content)
                .map(|m| m.as_str().to_lowercase())
                .collect();

            let stopwords = [
            "the", "and", "a", "an", "of", "to", "in", "for", "on", "with", "is", "it", "that", 
            "this", "at", "by", "from", "as", "are", "be", "or", "was", "were", "has", "had", "have"
        ];
            let stemmer = Stemmer::create(Algorithm::English);

            // Create stemmed ngrams (unigrams + bigrams)
            let mut ngrams = HashSet::new();
            for i in 0..tokens.len() {
                let word = &tokens[i];
                if stopwords.contains(&word.as_str()) {
                    continue;
                }
                let stemmed = stemmer.stem(word).to_string();
                ngrams.insert(stemmed.clone());

                if i + 1 < tokens.len() {
                    let next_word = &tokens[i + 1];
                    if !stopwords.contains(&next_word.as_str()) {
                        let next_stemmed = stemmer.stem(next_word).to_string();
                        let bigram = format!("{} {}", stemmed, next_stemmed);
                        ngrams.insert(bigram);

                    }
                }
            }

            let category_keywords: Vec<(&str, Vec<&str>)> = vec![
            ("news", vec![
                "news", "breaking", "update", "report", "headline", "journal", "media", "press",
                "announcement", "current", "daily news", "broadcast", "bulletin", "article", "coverage"
            ]),
            ("sports", vec![
                "football", "soccer", "basketball", "tennis", "cricket", "match", "tournament", "goal",
                "score", "league", "athlete", "olympics", "championship", "competition", "playoff",
                "coach", "team", "game", "sportsmanship", "player"
            ]),
            ("finance", vec![
                "stocks", "market", "investment", "finance", "economy", "bitcoin", "trading", "crypto",
                "banking", "fund", "portfolio", "mutual fund", "currency", "inflation", "deficit",
                "revenue", "capital", "dividend", "savings", "insurance"
            ]),
            ("health", vec![
                "health", "medicine", "wellness", "fitness", "disease", "nutrition", "exercise",
                "mental health", "medical", "therapy", "diet", "treatment", "hospital", "doctor",
                "clinic", "vaccine", "infection", "immune", "prevention", "rehabilitation"
            ]),
            ("entertainment", vec![
                "movie", "film", "tv", "music", "celebrity", "show", "concert", "series", "album",
                "entertainment", "theater", "drama", "comedy", "festival", "artist", "actor", "actress",
                "performance", "pop culture"
            ]),
            ("science", vec![
                "research", "experiment", "physics", "chemistry", "biology", "scientist", "study",
                "discovery", "laboratory", "experiment", "theory", "analysis", "observation",
                "scientific", "innovation", "space", "astronomy", "genetics", "geology", "climate"
            ]),
            ("travel", vec![
                "travel", "tourism", "destination", "flight", "hotel", "journey", "adventure", "trip",
                "vacation", "holiday", "explore", "sightseeing", "cruise", "itinerary", "backpacking",
                "resort", "beach", "mountain", "culture", "transportation"
            ]),
            ("food", vec![
                "food", "cuisine", "recipe", "dish", "restaurant", "meal", "dining", "chef",
                "ingredient", "gourmet", "taste", "baking", "cooking", "snack", "drink",
                "beverage", "dessert", "nutrition", "vegan", "organic"
            ]),
            ("fashion", vec![
                "fashion", "style", "clothing", "apparel", "designer", "trend", "runway",
                "collection", "brand", "outfit", "accessory", "model", "vogue", "couture",
                "textile", "footwear", "jewelry", "cosmetics", "hairstyle", "makeup"
            ]),
            ("education", vec![
                "education", "learning", "school", "college", "university", "course",
                "student", "teacher", "lecture", "curriculum", "study", "training",
                "knowledge", "academy", "classroom", "exam", "scholarship", "tutorial", "online course", "degree"
            ])
        ].iter().cloned().collect();

            // Count keyword matches
            let mut category_scores: Vec<(&str, usize)> = category_keywords.iter()
                .map(|(category, keywords)| {
                    let score = keywords.iter().filter(|kw| ngrams.contains(&kw.to_string())).count();
                    (*category, score)
                })
                .filter(|(_, score)| *score > 0)
                .collect();

            // Sort by match count descending
            category_scores.sort_by(|a, b| b.1.cmp(&a.1));

            // Add top categories until we reach max 3
            for (cat, _) in category_scores {
                if categories.len() >= 3 {
                    break;
                }
                if !categories.contains(&cat.to_string()) {
                    categories.push(cat.to_string());
                }
            }

            categories
        }
    }
