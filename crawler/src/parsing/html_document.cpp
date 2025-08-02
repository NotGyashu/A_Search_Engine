#include "html_document.h"
#include "ultra_parser.h"
#include <algorithm>
#include <sstream>
#include <unordered_set>
#include <iterator>
#include <cctype>

HtmlDocument::HtmlDocument(const std::string& html_content) : html_content_(html_content) {
    parse();
}

// === FAST UTILITY FUNCTIONS (NO REGEX) ===

size_t HtmlDocument::find_case_insensitive(std::string_view haystack, std::string_view needle, size_t start) {
    if (needle.empty() || haystack.size() < needle.size() || start > haystack.size())
        return std::string_view::npos;

    auto to_lower = [](char c) {
        return (c >= 'A' && c <= 'Z') ? (c + 32) : c;
    };

    for (size_t i = start; i <= haystack.size() - needle.size(); ++i) {
        bool match = true;
        for (size_t j = 0; j < needle.size(); ++j) {
            if (to_lower(haystack[i + j]) != to_lower(needle[j])) {
                match = false;
                break;
            }
        }
        if (match) return i;
    }
    return std::string_view::npos;
}

bool HtmlDocument::starts_with_case_insensitive(std::string_view str, std::string_view prefix) {
    if (prefix.size() > str.size()) return false;
    for (size_t i = 0; i < prefix.size(); ++i) {
        if (std::tolower(str[i]) != std::tolower(prefix[i])) return false;
    }
    return true;
}

std::string_view HtmlDocument::trim_whitespace(std::string_view str) {
    const char* whitespace = " \t\n\r\f\v";
    size_t start = str.find_first_not_of(whitespace);
    if (start == std::string_view::npos) return {};
    size_t end = str.find_last_not_of(whitespace);
    return str.substr(start, end - start + 1);
}

// === FAST TAG EXTRACTION (NO REGEX) ===

std::string HtmlDocument::extract_tag_content_fast(std::string_view html, std::string_view tag_name) const {
    std::string open_tag = "<" + std::string(tag_name);
    std::string close_tag = "</" + std::string(tag_name) + ">";
    
    size_t start = find_case_insensitive(html, open_tag);
    if (start == std::string_view::npos) return "";
    
    // Find end of opening tag
    size_t tag_end = html.find('>', start);
    if (tag_end == std::string_view::npos) return "";
    
    size_t content_start = tag_end + 1;
    size_t content_end = find_case_insensitive(html, close_tag, content_start);
    if (content_end == std::string_view::npos) return "";
    
    std::string_view content = html.substr(content_start, content_end - content_start);
    content = trim_whitespace(content);
    return std::string(content);
}

std::string HtmlDocument::extract_meta_content_fast(std::string_view html, std::string_view name) const {
    size_t pos = 0;
    while (pos < html.size()) {
        size_t meta_start = find_case_insensitive(html, "<meta", pos);
        if (meta_start == std::string_view::npos) break;
        
        size_t meta_end = html.find('>', meta_start);
        if (meta_end == std::string_view::npos) break;
        
        std::string_view meta_tag = html.substr(meta_start, meta_end - meta_start + 1);
        
        // Check if this meta tag has the name we want
        size_t name_pos = find_case_insensitive(meta_tag, "name=");
        if (name_pos != std::string_view::npos) {
            size_t name_start = name_pos + 5;
            char quote = meta_tag[name_start];
            if (quote == '"' || quote == '\'') {
                name_start++;
                size_t name_end = meta_tag.find(quote, name_start);
                if (name_end != std::string_view::npos) {
                    std::string_view meta_name = meta_tag.substr(name_start, name_end - name_start);
                    if (find_case_insensitive(meta_name, name) != std::string_view::npos) {
                        // Found the right meta tag, extract content
                        size_t content_pos = find_case_insensitive(meta_tag, "content=");
                        if (content_pos != std::string_view::npos) {
                            size_t content_start = content_pos + 8;
                            char content_quote = meta_tag[content_start];
                            if (content_quote == '"' || content_quote == '\'') {
                                content_start++;
                                size_t content_end = meta_tag.find(content_quote, content_start);
                                if (content_end != std::string_view::npos) {
                                    std::string_view content = meta_tag.substr(content_start, content_end - content_start);
                                    return std::string(trim_whitespace(content));
                                }
                            }
                        }
                    }
                }
            }
        }
        pos = meta_end + 1;
    }
    return "";
}

// === FAST HTML CLEANING (NO REGEX) ===

std::string HtmlDocument::remove_scripts_and_styles_fast(std::string_view html) const {
    std::string result;
    result.reserve(html.size());
    
    size_t pos = 0;
    while (pos < html.size()) {
        // Look for script or style tags
        size_t script_start = find_case_insensitive(html, "<script", pos);
        size_t style_start = find_case_insensitive(html, "<style", pos);
        
        size_t next_tag = std::min(script_start, style_start);
        if (next_tag == std::string_view::npos) {
            // No more script/style tags, append rest
            result.append(html.substr(pos));
            break;
        }
        
        // Append everything before the tag
        result.append(html.substr(pos, next_tag - pos));
        
        // Determine which tag we found and find its closing tag
        std::string_view close_tag;
        if (next_tag == script_start) {
            close_tag = "</script>";
        } else {
            close_tag = "</style>";
        }
        
        size_t close_pos = find_case_insensitive(html, close_tag, next_tag);
        if (close_pos != std::string_view::npos) {
            pos = close_pos + close_tag.size();
        } else {
            // Malformed HTML, skip to next tag
            size_t tag_end = html.find('>', next_tag);
            pos = (tag_end != std::string_view::npos) ? tag_end + 1 : next_tag + 1;
        }
    }
    
    return result;
}

std::string HtmlDocument::strip_html_tags_fast(std::string_view html) const {
    std::string result;
    result.reserve(html.size());
    
    bool in_tag = false;
    for (char c : html) {
        if (c == '<') {
            in_tag = true;
            result += ' '; // Replace tag with space to preserve word boundaries
        } else if (c == '>') {
            in_tag = false;
        } else if (!in_tag) {
            result += c;
        }
    }
    
    return result;
}

std::string HtmlDocument::clean_extracted_text_fast(std::string_view text) const {
    std::string result;
    result.reserve(text.size());
    
    bool last_was_space = true; // Start as true to trim leading spaces
    
    for (char c : text) {
        if (std::isspace(c)) {
            if (!last_was_space) {
                result += ' ';
                last_was_space = true;
            }
        } else {
            result += c;
            last_was_space = false;
        }
    }
    
    // Trim trailing space
    if (!result.empty() && result.back() == ' ') {
        result.pop_back();
    }
    
    return result;
}

std::string HtmlDocument::normalize_whitespace_fast(std::string_view text) const {
    return clean_extracted_text_fast(text);
}

// === CENTRALIZED PARSING (NO REGEX) ===

void HtmlDocument::parse() {
    std::string_view html_view(html_content_);
    
    // 1. Extract and cache clean text
    std::string no_scripts = remove_scripts_and_styles_fast(html_view);
    std::string no_tags = strip_html_tags_fast(no_scripts);
    cached_clean_text_ = clean_extracted_text_fast(no_tags);
    
    // 2. Extract and cache title
    cached_title_ = extract_tag_content_fast(html_view, "title");
    cached_title_ = clean_extracted_text_fast(cached_title_);
    
    // 3. Extract and cache meta description
    cached_meta_description_ = extract_meta_content_fast(html_view, "description");
    cached_meta_description_ = clean_extracted_text_fast(cached_meta_description_);
}

// === GETTERS (RETURN CACHED VALUES) ===

const std::string& HtmlDocument::getTitle() const {
    return cached_title_;
}

const std::string& HtmlDocument::getMetaDescription() const {
    return cached_meta_description_;
}

const std::string& HtmlDocument::getCleanText() const {
    return cached_clean_text_;
}

const std::string& HtmlDocument::getRawHtml() const {
    return html_content_;
}

// === ADDITIONAL METHODS (REGEX-FREE) ===

std::string HtmlDocument::getMetaKeywords() const {
    return extract_meta_content_fast(html_content_, "keywords");
}

std::string HtmlDocument::getMainContent() const {
    return extract_main_content_heuristic_fast(html_content_);
}

std::string HtmlDocument::getFirstParagraph() const {
    return extract_paragraph_content_fast(html_content_);
}

std::string HtmlDocument::getSnippet(size_t max_length) const {
    std::string content = getMainContent();
    if (content.empty()) {
        content = getCleanText();
    }
    if (content.length() <= max_length) {
        return content;
    }
    size_t pos = max_length;
    while (pos > 0 && !std::isspace(content[pos])) {
        pos--;
    }
    return pos > 0 ? content.substr(0, pos) + "..." : content.substr(0, max_length) + "...";
}

size_t HtmlDocument::getContentLength() const {
    return cached_clean_text_.length();
}

size_t HtmlDocument::getWordCount() const {
    if (cached_clean_text_.empty()) return 0;
    std::istringstream stream(cached_clean_text_);
    return std::distance(std::istream_iterator<std::string>(stream), std::istream_iterator<std::string>());
}

float HtmlDocument::getTextDensity() const {
    if (html_content_.empty()) return 0.0f;
    return static_cast<float>(getContentLength()) / static_cast<float>(html_content_.length());
}

bool HtmlDocument::hasValidStructure() const {
    std::string_view html(html_content_);
    return (find_case_insensitive(html, "<html") != std::string_view::npos || 
            find_case_insensitive(html, "<!doctype") != std::string_view::npos) &&
           find_case_insensitive(html, "<head") != std::string_view::npos &&
           find_case_insensitive(html, "<body") != std::string_view::npos;
}

bool HtmlDocument::isContentRich() const {
    return getWordCount() > 50 && getTextDensity() > 0.1f && !getTitle().empty();
}

std::string HtmlDocument::detectLanguage() const {
    static const std::unordered_set<std::string> english_words = {
        "the", "and", "of", "to", "a", "in", "is", "it", "you", "that"
    };
    std::istringstream stream(cached_clean_text_);
    std::string word;
    size_t total_words = 0;
    size_t english_count = 0;
    while (stream >> word && total_words < 100) {
        total_words++;
        std::string lower_word;
        lower_word.reserve(word.size());
        for (char c : word) {
            lower_word += std::tolower(c);
        }
        if (english_words.count(lower_word)) {
            english_count++;
        }
    }
    if (total_words == 0) return "unknown";
    return (static_cast<float>(english_count) / total_words > 0.3f) ? "en" : "unknown";
}

bool HtmlDocument::isEnglishContent() const {
    return detectLanguage() == "en";
}

std::vector<std::string> HtmlDocument::extractLinks(const std::string& base_url) const {
    static UltraParser::UltraHTMLParser link_parser;
    return link_parser.extract_links_ultra(html_content_, base_url);
}

std::vector<std::string> HtmlDocument::extractInternalLinks(const std::string& domain) const {
    std::vector<std::string> all_links = extractLinks();
    std::vector<std::string> internal_links;
    for (const auto& link : all_links) {
        if (link.find(domain) != std::string::npos || (!link.empty() && link[0] == '/')) {
            internal_links.push_back(link);
        }
    }
    return internal_links;
}

bool HtmlDocument::isEmpty() const {
    return html_content_.empty() || cached_clean_text_.empty();
}

// === ADVANCED CONTENT EXTRACTION (REGEX-FREE) ===

std::string HtmlDocument::extract_main_content_heuristic_fast(std::string_view html) const {
    // Try to find main content containers in order of preference
    static const std::vector<std::string_view> content_tags = {
        "main", "article", "section"
    };
    
    static const std::vector<std::string_view> content_classes = {
        "content", "main", "article", "post", "entry"
    };
    
    // Try semantic tags first
    for (auto tag : content_tags) {
        std::string content = extract_tag_content_fast(html, tag);
        if (!content.empty()) {
            content = remove_scripts_and_styles_fast(content);
            content = strip_html_tags_fast(content);
            content = clean_extracted_text_fast(content);
            if (content.length() > 100 && !is_boilerplate_content_fast(content)) {
                return content;
            }
        }
    }
    
    // Try divs with content-related classes/IDs
    size_t pos = 0;
    while (pos < html.size()) {
        size_t div_start = find_case_insensitive(html, "<div", pos);
        if (div_start == std::string_view::npos) break;
        
        size_t div_end = html.find('>', div_start);
        if (div_end == std::string_view::npos) break;
        
        std::string_view div_tag = html.substr(div_start, div_end - div_start + 1);
        
        // Check if this div has content-related class or id
        bool is_content_div = false;
        for (auto cls : content_classes) {
            if (find_case_insensitive(div_tag, cls) != std::string_view::npos) {
                is_content_div = true;
                break;
            }
        }
        
        if (is_content_div) {
            // Find closing </div>
            size_t close_pos = find_case_insensitive(html, "</div>", div_end);
            if (close_pos != std::string_view::npos) {
                std::string_view content_area = html.substr(div_end + 1, close_pos - div_end - 1);
                std::string content = remove_scripts_and_styles_fast(content_area);
                content = strip_html_tags_fast(content);
                content = clean_extracted_text_fast(content);
                if (content.length() > 100 && !is_boilerplate_content_fast(content)) {
                    return content;
                }
            }
        }
        
        pos = div_end + 1;
    }
    
    // Fallback to paragraph extraction
    return extract_paragraph_content_fast(html);
}

std::string HtmlDocument::extract_paragraph_content_fast(std::string_view html) const {
    std::string result;
    result.reserve(1000); // Reserve space for performance
    
    size_t pos = 0;
    while (pos < html.size() && result.length() < 500) {
        size_t p_start = find_case_insensitive(html, "<p", pos);
        if (p_start == std::string_view::npos) break;
        
        size_t p_tag_end = html.find('>', p_start);
        if (p_tag_end == std::string_view::npos) break;
        
        size_t p_close = find_case_insensitive(html, "</p>", p_tag_end);
        if (p_close == std::string_view::npos) {
            pos = p_tag_end + 1;
            continue;
        }
        
        std::string_view p_content = html.substr(p_tag_end + 1, p_close - p_tag_end - 1);
        std::string paragraph = strip_html_tags_fast(p_content);
        paragraph = clean_extracted_text_fast(paragraph);
        
        if (paragraph.length() > 30 && !is_boilerplate_content_fast(paragraph)) {
            if (!result.empty()) result += " ";
            result += paragraph;
        }
        
        pos = p_close + 4; // Skip "</p>"
    }
    
    return result;
}

bool HtmlDocument::is_boilerplate_content_fast(std::string_view text) const {
    static const std::vector<std::string_view> boilerplate_patterns = {
        "cookie", "privacy", "terms", "subscribe", "newsletter", "advertisement",
        "click here", "read more", "learn more", "copyright", "all rights reserved",
        "contact us", "about us", "follow us", "social media", "navigation"
    };
    
    // Convert to lowercase for comparison
    std::string lower_text;
    lower_text.reserve(text.size());
    for (char c : text) {
        lower_text += std::tolower(c);
    }
    
    for (auto pattern : boilerplate_patterns) {
        if (lower_text.find(pattern) != std::string::npos) return true;
    }
    return false;
}

bool HtmlDocument::is_navigation_content_fast(std::string_view text) const {
    static const std::vector<std::string_view> nav_keywords = {
        "home", "about", "contact", "services", "products", "blog", "news",
        "login", "register", "search", "menu", "navigation", "sitemap"
    };
    
    std::string lower_text;
    lower_text.reserve(text.size());
    for (char c : text) {
        lower_text += std::tolower(c);
    }
    
    for (auto keyword : nav_keywords) {
        if (lower_text.find(keyword) != std::string::npos) {
            return true;
        }
    }
    return false;
}

// === STATIC UTILITY METHODS (REGEX-FREE) ===

std::string HtmlDocument::resolveRelativeUrl(const std::string& base_url, const std::string& relative_url) {
    if (relative_url.empty() || relative_url.find("://") != std::string::npos) return relative_url;
    
    if (relative_url[0] == '/') {
        size_t protocol_end = base_url.find("://");
        if (protocol_end == std::string::npos) return relative_url;
        size_t domain_end = base_url.find('/', protocol_end + 3);
        return base_url.substr(0, domain_end) + relative_url;
    }
    
    size_t last_slash = base_url.find_last_of('/');
    return base_url.substr(0, last_slash + 1) + relative_url;
}

std::string HtmlDocument::extractDomain(const std::string& url) {
    size_t start = url.find("://");
    if (start == std::string::npos) return "";
    start += 3;
    size_t end = url.find('/', start);
    if (end == std::string::npos) end = url.size();
    
    std::string domain = url.substr(start, end - start);
    // Convert to lowercase
    std::transform(domain.begin(), domain.end(), domain.begin(), ::tolower);
    return domain;
}

bool HtmlDocument::isValidHtml(const std::string& content) {
    if (content.length() < 20) return false;
    
    std::string_view html(content.substr(0, std::min(content.size(), size_t(1000))));
    return find_case_insensitive(html, "<html") != std::string_view::npos ||
           find_case_insensitive(html, "<!doctype html") != std::string_view::npos ||
           find_case_insensitive(html, "<head") != std::string_view::npos ||
           find_case_insensitive(html, "<body") != std::string_view::npos;
}