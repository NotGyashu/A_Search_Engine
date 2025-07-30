#include "html_document.h"
#include <algorithm>
#include <sstream>
#include <unordered_set>
#include <cctype>
#include <functional>
#include "ultra_parser.h"

// Initialize static regex patterns
std::regex HtmlDocument::title_regex_(R"(<title[^>]*>([^<]*)</title>)", std::regex::icase);
std::regex HtmlDocument::meta_description_regex_(R"(<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\'])", std::regex::icase);
std::regex HtmlDocument::meta_keywords_regex_(R"(<meta[^>]*name=["\']keywords["\'][^>]*content=["\']([^"\']*)["\'])", std::regex::icase);
std::regex HtmlDocument::script_style_regex_(R"(<(script|style)[^>]*>[\s\S]*?</\1>)", std::regex::icase);
std::regex HtmlDocument::tag_regex_(R"(<[^>]*>)");
std::regex HtmlDocument::whitespace_regex_(R"(\s+)");
std::regex HtmlDocument::multiple_spaces_regex_(R"( {2,})");

HtmlDocument::HtmlDocument(const std::string& html_content) : html_content_(html_content) {}

std::string HtmlDocument::getTitle() const {
    if (!title_extracted_) {
        std::smatch match;
        if (std::regex_search(html_content_, match, title_regex_) && match.size() > 1) {
            cached_title_ = clean_extracted_text(match[1].str());
        }
        title_extracted_ = true;
    }
    return cached_title_;
}

std::string HtmlDocument::getMetaDescription() const {
    if (!meta_description_extracted_) {
        std::smatch match;
        if (std::regex_search(html_content_, match, meta_description_regex_) && match.size() > 1) {
            cached_meta_description_ = clean_extracted_text(match[1].str());
        }
        meta_description_extracted_ = true;
    }
    return cached_meta_description_;
}

std::string HtmlDocument::getMetaKeywords() const {
    std::smatch match;
    if (std::regex_search(html_content_, match, meta_keywords_regex_) && match.size() > 1) {
        return clean_extracted_text(match[1].str());
    }
    return "";
}

std::string HtmlDocument::getCleanText() const {
    if (!clean_text_extracted_) {
        std::string content = remove_scripts_and_styles(html_content_);
        content = strip_html_tags(content);
        cached_clean_text_ = clean_extracted_text(content);
        clean_text_extracted_ = true;
    }
    return cached_clean_text_;
}

std::string HtmlDocument::getMainContent() const {
    return extract_main_content_heuristic(html_content_);
}

std::string HtmlDocument::getFirstParagraph() const {
    return extract_paragraph_content(html_content_);
}

std::string HtmlDocument::getSnippet(size_t max_length) const {
    std::string content = getMainContent();
    if (content.empty()) {
        content = getCleanText();
    }
    
    if (content.length() <= max_length) {
        return content;
    }
    
    // Find a good breaking point (end of sentence or word)
    size_t pos = max_length;
    while (pos > max_length / 2 && pos < content.length()) {
        if (content[pos] == '.' || content[pos] == '!' || content[pos] == '?') {
            return content.substr(0, pos + 1);
        }
        if (content[pos] == ' ') {
            size_t good_break = pos;
            // Look ahead for sentence end
            for (size_t i = pos; i < std::min(pos + 20, content.length()); ++i) {
                if (content[i] == '.' || content[i] == '!' || content[i] == '?') {
                    return content.substr(0, i + 1);
                }
            }
            return content.substr(0, good_break) + "...";
        }
        pos++;
    }
    
    // Fallback: cut at word boundary
    pos = max_length;
    while (pos > 0 && content[pos] != ' ') pos--;
    return content.substr(0, pos) + "...";
}

std::string HtmlDocument::remove_scripts_and_styles(const std::string& html) const {
    return std::regex_replace(html, script_style_regex_, "");
}

std::string HtmlDocument::strip_html_tags(const std::string& html) const {
    return std::regex_replace(html, tag_regex_, " ");
}

std::string HtmlDocument::clean_extracted_text(const std::string& text) const {
    std::string result = text;
    
    // Normalize whitespace
    result = std::regex_replace(result, whitespace_regex_, " ");
    result = std::regex_replace(result, multiple_spaces_regex_, " ");
    
    // Trim leading and trailing whitespace
    result.erase(0, result.find_first_not_of(" \t\n\r\f\v"));
    result.erase(result.find_last_not_of(" \t\n\r\f\v") + 1);
    
    return result;
}

std::string HtmlDocument::normalize_whitespace(const std::string& text) const {
    return clean_extracted_text(text);
}

std::string HtmlDocument::extract_main_content_heuristic(const std::string& html) const {
    // Priority order for content containers
    static const std::vector<std::string> content_selectors = {
        "<main[^>]*>",
        "<article[^>]*>",
        "<div[^>]*class=['\"][^'\"]*content[^'\"]*['\"][^>]*>",
        "<div[^>]*id=['\"][^'\"]*content[^'\"]*['\"][^>]*>",
        "<div[^>]*class=['\"][^'\"]*main[^'\"]*['\"][^>]*>",
        "<div[^>]*id=['\"][^'\"]*main[^'\"]*['\"][^>]*>",
        "<section[^>]*>"
    };
    
    for (const auto& selector : content_selectors) {
        std::regex pattern(selector, std::regex::icase);
        std::smatch match;
        
        if (std::regex_search(html, match, pattern)) {
            size_t start_pos = match.position() + match.length();
            
            // Find the closing tag
            std::string tag_name = selector.substr(1, selector.find_first_of(" [") - 1);
            std::string closing_tag = "</" + tag_name + ">";
            
            size_t end_pos = html.find(closing_tag, start_pos);
            if (end_pos != std::string::npos) {
                std::string content = html.substr(start_pos, end_pos - start_pos);
                content = remove_scripts_and_styles(content);
                content = strip_html_tags(content);
                content = clean_extracted_text(content);
                
                if (content.length() > 100 && !is_boilerplate_content(content)) {
                    return content;
                }
            }
        }
    }
    
    // Fallback: extract paragraph content
    return extract_paragraph_content(html);
}

std::string HtmlDocument::extract_paragraph_content(const std::string& html) const {
    std::regex p_regex(R"(<p[^>]*>([\s\S]*?)</p>)", std::regex::icase);
    std::sregex_iterator iter(html.begin(), html.end(), p_regex);
    std::sregex_iterator end;
    
    std::string result;
    for (; iter != end; ++iter) {
        std::string paragraph = (*iter)[1].str();
        paragraph = strip_html_tags(paragraph);
        paragraph = clean_extracted_text(paragraph);
        
        if (paragraph.length() > 30 && !is_boilerplate_content(paragraph)) {
            if (!result.empty()) result += " ";
            result += paragraph;
            
            // Stop after we have enough content
            if (result.length() > 500) break;
        }
    }
    
    return result;
}

bool HtmlDocument::is_boilerplate_content(const std::string& text) const {
    static const std::unordered_set<std::string> boilerplate_patterns = {
        "cookie", "privacy", "terms", "subscribe", "newsletter", "advertisement",
        "click here", "read more", "learn more", "copyright", "all rights reserved",
        "contact us", "about us", "follow us", "social media", "navigation"
    };
    
    std::string lower_text = text;
    std::transform(lower_text.begin(), lower_text.end(), lower_text.begin(), ::tolower);
    
    for (const auto& pattern : boilerplate_patterns) {
        if (lower_text.find(pattern) != std::string::npos) {
            return true;
        }
    }
    
    // Check for repetitive content
    if (text.length() < 50) return true;
    
    // Check for excessive punctuation or special characters
    size_t special_chars = 0;
    for (char c : text) {
        if (!std::isalnum(c) && !std::isspace(c)) {
            special_chars++;
        }
    }
    
    return (special_chars > text.length() / 3);
}

bool HtmlDocument::is_navigation_content(const std::string& text) const {
    static const std::unordered_set<std::string> nav_keywords = {
        "home", "about", "contact", "services", "products", "blog", "news",
        "login", "register", "search", "menu", "navigation", "sitemap"
    };
    
    std::string lower_text = text;
    std::transform(lower_text.begin(), lower_text.end(), lower_text.begin(), ::tolower);
    
    for (const auto& keyword : nav_keywords) {
        if (lower_text.find(keyword) != std::string::npos) {
            return true;
        }
    }
    
    return false;
}

size_t HtmlDocument::getContentLength() const {
    return getCleanText().length();
}

size_t HtmlDocument::getWordCount() const {
    std::string text = getCleanText();
    if (text.empty()) return 0;
    
    std::istringstream stream(text);
    std::string word;
    size_t count = 0;
    
    while (stream >> word) {
        if (word.length() > 2) { // Only count meaningful words
            count++;
        }
    }
    
    return count;
}

float HtmlDocument::getTextDensity() const {
    if (html_content_.empty()) return 0.0f;
    
    size_t text_length = getContentLength();
    size_t html_length = html_content_.length();
    
    return static_cast<float>(text_length) / static_cast<float>(html_length);
}

bool HtmlDocument::hasValidStructure() const {
    std::string lower_html = html_content_;
    std::transform(lower_html.begin(), lower_html.end(), lower_html.begin(), ::tolower);
    
    return (lower_html.find("<html") != std::string::npos ||
            lower_html.find("<!doctype") != std::string::npos) &&
           lower_html.find("<head") != std::string::npos &&
           lower_html.find("<body") != std::string::npos;
}

bool HtmlDocument::isContentRich() const {
    return getWordCount() > 50 && getTextDensity() > 0.1f && !getTitle().empty();
}

std::string HtmlDocument::detectLanguage() const {
    // Simple language detection based on common English words
    std::string text = getCleanText();
    std::transform(text.begin(), text.end(), text.begin(), ::tolower);
    
    static const std::unordered_set<std::string> english_words = {
        "the", "and", "of", "to", "a", "in", "is", "it", "you", "that",
        "he", "was", "for", "on", "are", "as", "with", "his", "they", "at"
    };
    
    std::istringstream stream(text);
    std::string word;
    size_t total_words = 0;
    size_t english_count = 0;
    
    while (stream >> word && total_words < 100) {
        total_words++;
        if (english_words.count(word)) {
            english_count++;
        }
    }
    
    if (total_words == 0) return "unknown";
    
    float english_ratio = static_cast<float>(english_count) / static_cast<float>(total_words);
    return (english_ratio > 0.3f) ? "en" : "unknown";
}

bool HtmlDocument::isEnglishContent() const {
    return detectLanguage() == "en";
}

// Use the UltraHTMLParser for links
std::vector<std::string> HtmlDocument::extractLinks(const std::string& base_url) const {
    // Replace the regex logic with a call to the high-performance engine
    static UltraParser::UltraHTMLParser link_parser;
    return link_parser.extract_links_ultra(html_content_, base_url);
}

std::vector<std::string> HtmlDocument::extractInternalLinks(const std::string& domain) const {
    std::vector<std::string> all_links = extractLinks();
    std::vector<std::string> internal_links;
    
    for (const auto& link : all_links) {
        if (link.find(domain) != std::string::npos || link[0] == '/') {
            internal_links.push_back(link);
        }
    }
    
    return internal_links;
}

bool HtmlDocument::isEmpty() const {
    return html_content_.empty() || getContentLength() == 0;
}

std::string HtmlDocument::getRawHtml() const {
    return html_content_;
}

std::string HtmlDocument::resolveRelativeUrl(const std::string& base_url, const std::string& relative_url) {
    if (relative_url.empty()) return "";
    if (relative_url.find("://") != std::string::npos) return relative_url; // Already absolute
    
    if (relative_url[0] == '/') {
        // Absolute path
        size_t protocol_end = base_url.find("://");
        if (protocol_end == std::string::npos) return "";
        
        size_t domain_end = base_url.find('/', protocol_end + 3);
        std::string base_domain = (domain_end == std::string::npos) 
            ? base_url : base_url.substr(0, domain_end);
        
        return base_domain + relative_url;
    } else {
        // Relative path
        std::string base = base_url;
        if (base.back() != '/') {
            size_t last_slash = base.find_last_of('/');
            if (last_slash != std::string::npos && last_slash > base.find("://") + 2) {
                base = base.substr(0, last_slash + 1);
            } else {
                base += "/";
            }
        }
        return base + relative_url;
    }
}

std::string HtmlDocument::extractDomain(const std::string& url) {
    size_t start = url.find("://");
    if (start == std::string::npos) return "";
    
    start += 3;
    size_t end = url.find('/', start);
    return url.substr(start, end == std::string::npos ? std::string::npos : end - start);
}

bool HtmlDocument::isValidHtml(const std::string& content) {
    if (content.length() < 20) return false;
    
    std::string lower_content = content.substr(0, 1000);
    std::transform(lower_content.begin(), lower_content.end(), lower_content.begin(), ::tolower);
    
    return lower_content.find("<html") != std::string::npos ||
           lower_content.find("<!doctype html") != std::string::npos ||
           lower_content.find("<head") != std::string::npos ||
           lower_content.find("<body") != std::string::npos;
}
