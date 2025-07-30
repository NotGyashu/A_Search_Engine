#include "snippet_extractor.h"
#include <cctype>
#include <iostream>
#include <sstream>
#include <algorithm>
#include <unordered_map>


namespace SnippetExtraction {

namespace {

std::string extract_body_content(const std::string& html) {
    const std::string body_start_tag = "<body";
    const std::string body_end_tag = "</body>";

    size_t start_pos = html.find(body_start_tag);
    if (start_pos == std::string::npos) return "";

    start_pos = html.find('>', start_pos);
    if (start_pos == std::string::npos) return "";
    start_pos++;

    size_t end_pos = html.find(body_end_tag, start_pos);
    if (end_pos == std::string::npos) end_pos = html.size();

    return html.substr(start_pos, end_pos - start_pos);
}

// Fixed: Added extractor parameter and removed 'this->'

}  // namespace

BasicSnippetExtractor::BasicSnippetExtractor() {
    default_config_ = SnippetConfig{};
}

std::string BasicSnippetExtractor::extract_content_by_tag(const std::string& html, const std::string& tag) const {
    std::string result;
    const std::string open_tag = "<" + tag;
    const std::string close_tag = "</" + tag + ">";

    size_t pos = 0;
    while (pos < html.size()) {
        size_t start_pos = html.find(open_tag, pos);
        if (start_pos == std::string::npos) break;

        start_pos = html.find('>', start_pos);
        if (start_pos == std::string::npos) break;
        start_pos++;

        size_t end_pos = html.find(close_tag, start_pos);
        if (end_pos == std::string::npos) break;

        std::string content = html.substr(start_pos, end_pos - start_pos);
        content = strip_html_tags_simple(content);  // Now this works since it's a member function

        if (!content.empty()) {
            result += content + " ";
        }

        pos = end_pos + close_tag.size();
    }
    return result;
}

std::string BasicSnippetExtractor::strip_html_tags_simple(const std::string& html) const {
    std::string result;
    bool in_tag = false, in_script = false, in_style = false;

    for (size_t i = 0; i < html.size(); ++i) {
        if (!in_script && !in_style) {
            if (html.compare(i, 7, "<script") == 0) {
                in_script = true;
                i += 6;
                continue;
            } else if (html.compare(i, 6, "<style") == 0) {
                in_style = true;
                i += 5;
                continue;
            }
        }

        if (in_script && html.compare(i, 9, "</script>") == 0) {
            in_script = false;
            i += 8;
            continue;
        }
        if (in_style && html.compare(i, 8, "</style>") == 0) {
            in_style = false;
            i += 7;
            continue;
        }

        if (in_script || in_style) continue;

        if (html[i] == '<') in_tag = true;
        else if (html[i] == '>') in_tag = false;
        else if (!in_tag) result += html[i];
    }

    return result;
}

ExtractedSnippet BasicSnippetExtractor::extract_snippet(const std::string& html_content, 
                                                        const std::string& url,
                                                        const SnippetConfig& config) {
    ExtractedSnippet result;
    if (html_content.empty()) return result;

    try {
        std::string domain;
        if (!url.empty()) {
            size_t start = url.find("://");
            if (start != std::string::npos) {
                start += 3;
                size_t end = url.find('/', start);
                domain = url.substr(start, end - start);
            }
        }

        SnippetConfig effective_config = domain.empty() ? config : get_config_for_domain(domain);

        // Multi-strategy extraction with Google-like approach
        std::string extracted_text;
        result.extraction_method = "google_like";
        
        // Strategy 1: Try to extract first meaningful paragraph (Google-like)
        extracted_text = extract_first_meaningful_paragraph(html_content, effective_config);
        if (!extracted_text.empty() && contains_meaningful_information(extracted_text, effective_config)) {
            result.extraction_method = "first_meaningful_paragraph";
        } else {
            // Strategy 2: Try main content extraction
            extracted_text = extract_main_content(html_content, effective_config);
            if (!extracted_text.empty() && !is_boilerplate_content(extracted_text, effective_config)) {
                result.extraction_method = "main_content";
                result.has_main_content = true;
            } else {
                // Strategy 3: Try semantic content extraction
                extracted_text = extract_semantic_content(html_content, effective_config);
                if (!extracted_text.empty() && !is_boilerplate_content(extracted_text, effective_config)) {
                    result.extraction_method = "semantic_content";
                } else {
                    // Strategy 4: Fall back to priority tags but with stricter filtering
                    extracted_text = extract_text_from_priority_tags(html_content, effective_config);
                    result.extraction_method = "priority_tags_filtered";
                }
            }
        }

        // Apply Google-like processing
        extracted_text = remove_boilerplate_sentences(extracted_text, effective_config);
        extracted_text = remove_marketing_fluff(extracted_text, effective_config);
        extracted_text = fix_text_spacing(extracted_text);
        
        std::string final_snippet = create_google_like_snippet(extracted_text, effective_config);

        // Enhanced quality scoring with Google-like criteria
        float alphabetic_ratio = calculate_alphabetic_ratio(final_snippet);
        size_t word_count = count_meaningful_words(final_snippet);
        bool has_structure = has_proper_sentence_structure(final_snippet);
        bool link_heavy = is_link_heavy(final_snippet);
        bool marketing_heavy = is_marketing_heavy(final_snippet, effective_config);
        bool meaningful = contains_meaningful_information(final_snippet, effective_config);
        
        result.content_density = calculate_content_density(final_snippet);
        result.readability_score = calculate_readability_score(final_snippet);

        // Google-like quality scoring (more stringent)
        result.quality_score = 0.0f;
        if (alphabetic_ratio >= effective_config.min_alphabetic_ratio) result.quality_score += 0.2f;
        if (word_count >= effective_config.min_meaningful_words) result.quality_score += 0.2f;
        if (has_structure) result.quality_score += 0.2f;
        if (!link_heavy) result.quality_score += 0.1f;
        if (!marketing_heavy) result.quality_score += 0.15f;
        if (meaningful) result.quality_score += 0.1f;
        if (result.content_density > 0.6f) result.quality_score += 0.05f;

        // Only use high-quality snippets (Google standard)
        result.is_meaningful = (result.quality_score >= 0.7f && !final_snippet.empty());

        if (result.is_meaningful) {
            result.text_snippet = final_snippet;
            auto sentences = extract_sentences(final_snippet, effective_config);
            result.sentence_count = sentences.size();
            result.source_tag_count = sentences.size();
            result.primary_language = "en";
        }
    } catch (const std::exception& e) {
        std::cerr << "Error during snippet extraction: " << e.what() << std::endl;
    }

    return result;
}

// Fixed: Pass 'this' pointer to helper function
std::string BasicSnippetExtractor::extract_text_from_priority_tags(const std::string& html, const SnippetConfig& config) const {
    std::string result;
    for (const auto& tag : config.priority_tags) {
        result += extract_content_by_tag(html, tag);  // Call class method
    }

    if (result.empty()) {
        std::string body = extract_body_content(html);
        result = strip_html_tags_simple(body);
    }
    return result;
}

std::string BasicSnippetExtractor::normalize_text(const std::string& text, const SnippetConfig& config) const {
    std::string result = text;

    if (config.remove_html_entities) {
        replace_all(result, "&amp;", "&");
        replace_all(result, "&lt;", "<");
        replace_all(result, "&gt;", ">");
        replace_all(result, "&quot;", "\"");
        replace_all(result, "&apos;", "'");
        replace_all(result, "&nbsp;", " ");
    }

    if (config.normalize_whitespace) {
        std::string normalized;
        bool last_was_space = false;
        for (char c : result) {
            if (std::isspace(c)) {
                if (!last_was_space) {
                    normalized += ' ';
                    last_was_space = true;
                }
            } else {
                normalized += c;
                last_was_space = false;
            }
        }

        size_t start = normalized.find_first_not_of(" \t\n\r");
        if (start == std::string::npos) return "";
        size_t end = normalized.find_last_not_of(" \t\n\r");
        result = normalized.substr(start, end - start + 1);
    }

    return result;
}

float BasicSnippetExtractor::calculate_alphabetic_ratio(const std::string& text) const {
    if (text.empty()) return 0.0f;
    size_t alphabetic_count = 0, total_chars = 0;
    for (char c : text) {
        if (!std::isspace(c)) {
            ++total_chars;
            if (std::isalpha(c)) ++alphabetic_count;
        }
    }
    return total_chars > 0 ? static_cast<float>(alphabetic_count) / total_chars : 0.0f;
}

size_t BasicSnippetExtractor::count_meaningful_words(const std::string& text) const {
    std::istringstream iss(text);
    std::string word;
    size_t count = 0;
    while (iss >> word) {
        size_t alpha_count = 0;
        for (char c : word) {
            if (std::isalpha(c)) ++alpha_count;
        }
        if (alpha_count >= 2) ++count;
    }
    return count;
}

bool BasicSnippetExtractor::has_sentence_structure(const std::string& text) const {
    if (text.empty() || text.size() > 10000) return false;
    for (size_t i = 0; i + 2 < text.size(); ++i) {
        if ((text[i] == '.' || text[i] == '!' || text[i] == '?') &&
            std::isspace(text[i+1]) && std::isupper(text[i+2])) {
            return true;
        }
    }
    return false;
}

std::vector<std::string> BasicSnippetExtractor::extract_sentences(const std::string& text, const SnippetConfig& config) const {
    std::vector<std::string> sentences;
    std::string current;
    for (char c : text) {
        current += c;
        if (c == '.' || c == '!' || c == '?') {
            if (current.size() >= config.min_sentence_length) {
                size_t start = current.find_first_not_of(" \t\n\r");
                size_t end = current.find_last_not_of(" \t\n\r");
                if (start != std::string::npos && end != std::string::npos)
                    sentences.push_back(current.substr(start, end - start + 1));
            }
            current.clear();
            if (sentences.size() >= config.target_sentences) break;
        }
    }
    if (!current.empty() && sentences.size() < config.target_sentences) {
        size_t start = current.find_first_not_of(" \t\n\r");
        size_t end = current.find_last_not_of(" \t\n\r");
        if (start != std::string::npos && end != std::string::npos)
            sentences.push_back(current.substr(start, end - start + 1));
    }
    return sentences;
}

std::string BasicSnippetExtractor::build_snippet_from_sentences(const std::vector<std::string>& sentences, const SnippetConfig& config) const {
    std::string snippet;
    size_t current_length = 0;
    for (const auto& sentence : sentences) {
        if (current_length + sentence.size() > config.max_snippet_length) {
            size_t remaining = config.max_snippet_length - current_length;
            if (remaining > 20) snippet += sentence.substr(0, remaining - 3) + "...";
            break;
        }
        snippet += sentence;
        if (!sentence.empty() && sentence.back() != ' ') snippet += ' ';
        current_length = snippet.size();
    }
    if (!snippet.empty() && snippet.back() == ' ') snippet.pop_back();
    return snippet;
}

SnippetConfig BasicSnippetExtractor::get_config_for_domain(const std::string& domain) const {
    auto it = domain_configs_.find(domain);
    return it != domain_configs_.end() ? it->second : default_config_;
}

void BasicSnippetExtractor::set_domain_config(const std::string& domain, const SnippetConfig& config) {
    domain_configs_[domain] = config;
}

void BasicSnippetExtractor::replace_all(std::string& str, const std::string& from, const std::string& to) const {
    if (from.empty()) return;
    size_t start_pos = 0;
    while ((start_pos = str.find(from, start_pos)) != std::string::npos) {
        str.replace(start_pos, from.length(), to);
        start_pos += to.length();
    }
}

void BasicSnippetExtractor::print_extraction_stats() const {
    std::cout << "\n📊 Snippet Extraction Statistics:\n";
    std::cout << "   Domain-specific configs: " << domain_configs_.size() << "\n";
    std::cout << "   Default snippet length: " << default_config_.max_snippet_length << " chars\n";
    std::cout << "   Target sentences: " << default_config_.target_sentences << "\n";
}

// Enhanced content extraction methods

std::string BasicSnippetExtractor::extract_main_content(const std::string& html, const SnippetConfig& config) const {
    std::string result;
    
    // Try to find main content areas first
    std::vector<std::string> main_selectors = {"<main", "<article", "<div class=\"content\"", "<div id=\"content\"", 
                                               "<div class=\"post\"", "<div class=\"article\""};
    
    for (const auto& selector : main_selectors) {
        size_t pos = html.find(selector);
        if (pos != std::string::npos) {
            // Extract content from this main area
            size_t start = html.find('>', pos);
            if (start != std::string::npos) {
                start++;
                // Find the corresponding closing tag
                std::string tag_name = selector.substr(1, selector.find(' ') - 1);
                if (tag_name.empty()) tag_name = selector.substr(1);
                
                std::string close_tag = "</" + tag_name + ">";
                size_t end = html.find(close_tag, start);
                if (end != std::string::npos) {
                    std::string content = html.substr(start, end - start);
                    result = strip_html_tags_simple(content);
                    if (!result.empty()) break;
                }
            }
        }
    }
    
    return result;
}

std::string BasicSnippetExtractor::extract_semantic_content(const std::string& html, const SnippetConfig& config) const {
    // Extract paragraphs and rank them by quality
    auto paragraphs = extract_paragraphs(html, config);
    auto ranked_paragraphs = rank_paragraphs_by_quality(paragraphs, config);
    
    std::string result;
    size_t char_count = 0;
    
    for (const auto& paragraph : ranked_paragraphs) {
        if (char_count + paragraph.length() > config.max_snippet_length) break;
        if (!is_boilerplate_content(paragraph, config)) {
            result += paragraph + " ";
            char_count += paragraph.length() + 1;
        }
    }
    
    return result;
}

std::vector<std::string> BasicSnippetExtractor::extract_paragraphs(const std::string& html, const SnippetConfig& config) const {
    std::vector<std::string> paragraphs;
    
    // Extract content from paragraph-like tags
    for (const auto& tag : config.content_tags) {
        std::string content = extract_content_by_tag(html, tag);
        if (!content.empty() && content.length() >= config.min_paragraph_length) {
            paragraphs.push_back(content);
        }
    }
    
    return paragraphs;
}

std::vector<std::string> BasicSnippetExtractor::rank_paragraphs_by_quality(const std::vector<std::string>& paragraphs, 
                                                                           const SnippetConfig& config) const {
    std::vector<std::pair<std::string, float>> scored_paragraphs;
    
    for (const auto& paragraph : paragraphs) {
        float score = 0.0f;
        
        // Score based on length (prefer medium-length paragraphs)
        if (paragraph.length() >= 50 && paragraph.length() <= 300) score += 0.3f;
        
        // Score based on sentence structure
        if (has_sentence_structure(paragraph)) score += 0.2f;
        
        // Score based on alphabetic content
        if (calculate_alphabetic_ratio(paragraph) > 0.8f) score += 0.2f;
        
        // Penalize link-heavy content
        if (is_link_heavy(paragraph)) score -= 0.3f;
        
        // Penalize repetitive content
        if (is_repetitive_content(paragraph, config)) score -= 0.2f;
        
        scored_paragraphs.push_back({paragraph, score});
    }
    
    // Sort by score descending
    std::sort(scored_paragraphs.begin(), scored_paragraphs.end(), 
              [](const auto& a, const auto& b) { return a.second > b.second; });
    
    std::vector<std::string> result;
    for (const auto& scored : scored_paragraphs) {
        result.push_back(scored.first);
    }
    
    return result;
}

bool BasicSnippetExtractor::is_boilerplate_content(const std::string& text, const SnippetConfig& config) const {
    if (text.empty() || text.length() < 20) return true;
    
    // Check for navigation patterns
    if (contains_navigation_patterns(text)) return true;
    
    // Check for repetitive content
    if (is_repetitive_content(text, config)) return true;
    
    // Check for boilerplate selectors
    std::string lower_text = text;
    std::transform(lower_text.begin(), lower_text.end(), lower_text.begin(), ::tolower);
    
    for (const auto& selector : config.boilerplate_selectors) {
        if (lower_text.find(selector) != std::string::npos) return true;
    }
    
    return false;
}

bool BasicSnippetExtractor::contains_navigation_patterns(const std::string& text) const {
    std::vector<std::string> nav_patterns = {
        "home", "about", "contact", "login", "register", "search", "menu", "navigation",
        "skip to", "back to", "click here", "read more", "view all", "see more",
        "copyright", "privacy policy", "terms of service", "cookies"
    };
    
    std::string lower_text = text;
    std::transform(lower_text.begin(), lower_text.end(), lower_text.begin(), ::tolower);
    
    int nav_count = 0;
    for (const auto& pattern : nav_patterns) {
        if (lower_text.find(pattern) != std::string::npos) {
            nav_count++;
        }
    }
    
    // If more than 2 navigation patterns found, likely boilerplate
    return nav_count > 2;
}

bool BasicSnippetExtractor::is_repetitive_content(const std::string& text, const SnippetConfig& config) const {
    std::unordered_map<std::string, int> word_counts;
    std::stringstream ss(text);
    std::string word;
    
    while (ss >> word) {
        // Convert to lowercase and remove punctuation
        std::transform(word.begin(), word.end(), word.begin(), ::tolower);
        word.erase(std::remove_if(word.begin(), word.end(), ::ispunct), word.end());
        
        if (word.length() > 2) {  // Ignore very short words
            word_counts[word]++;
        }
    }
    
    // Check if any word appears too frequently
    int total_words = word_counts.size();
    for (const auto& pair : word_counts) {
        if (pair.second > static_cast<int>(config.max_repeated_words) && 
            total_words > 0 && 
            (static_cast<float>(pair.second) / total_words) > 0.1f) {
            return true;
        }
    }
    
    return false;
}

std::string BasicSnippetExtractor::remove_boilerplate_sentences(const std::string& text, const SnippetConfig& config) const {
    auto sentences = extract_sentences(text, config);
    std::string result;
    
    for (const auto& sentence : sentences) {
        if (!is_boilerplate_content(sentence, config) && 
            sentence.length() >= config.min_sentence_length) {
            result += sentence + " ";
        }
    }
    
    return result;
}

float BasicSnippetExtractor::calculate_content_density(const std::string& text) const {
    if (text.empty()) return 0.0f;
    
    size_t meaningful_chars = 0;
    size_t total_chars = text.length();
    
    for (char c : text) {
        if (std::isalnum(c) || c == '.' || c == ',' || c == '!' || c == '?') {
            meaningful_chars++;
        }
    }
    
    return static_cast<float>(meaningful_chars) / total_chars;
}

float BasicSnippetExtractor::calculate_readability_score(const std::string& text) const {
    if (text.empty()) return 0.0f;
    
    size_t sentence_count = 0;
    size_t word_count = 0;
    size_t char_count = 0;
    
    // Count sentences (rough approximation)
    for (char c : text) {
        if (c == '.' || c == '!' || c == '?') sentence_count++;
        if (std::isspace(c)) word_count++;
        if (std::isalnum(c)) char_count++;
    }
    
    if (sentence_count == 0 || word_count == 0) return 0.0f;
    
    // Simple readability score based on average sentence and word length
    float avg_sentence_length = static_cast<float>(word_count) / sentence_count;
    float avg_word_length = static_cast<float>(char_count) / word_count;
    
    // Prefer moderate sentence and word lengths
    float sentence_score = (avg_sentence_length > 5 && avg_sentence_length < 25) ? 0.5f : 0.2f;
    float word_score = (avg_word_length > 3 && avg_word_length < 8) ? 0.5f : 0.2f;
    
    return sentence_score + word_score;
}

bool BasicSnippetExtractor::is_link_heavy(const std::string& text) const {
    if (text.empty()) return false;
    
    // Count potential link indicators
    size_t link_indicators = 0;
    std::string lower_text = text;
    std::transform(lower_text.begin(), lower_text.end(), lower_text.begin(), ::tolower);
    
    std::vector<std::string> link_patterns = {"click", "here", "more", "read", "view", "see", "http", "www"};
    
    for (const auto& pattern : link_patterns) {
        size_t pos = 0;
        while ((pos = lower_text.find(pattern, pos)) != std::string::npos) {
            link_indicators++;
            pos += pattern.length();
        }
    }
    
    // If more than 20% of words are link-related, consider it link-heavy
    size_t word_count = std::count(text.begin(), text.end(), ' ') + 1;
    return word_count > 0 && (static_cast<float>(link_indicators) / word_count) > 0.2f;
}

// Google-like content extraction methods

std::string BasicSnippetExtractor::extract_first_meaningful_paragraph(const std::string& html, const SnippetConfig& config) const {
    // Look for the first substantial paragraph that isn't navigation/boilerplate
    std::string result;
    
    // Try to find first paragraph after title/header content
    size_t pos = 0;
    std::string p_tag = "<p";
    
    while (pos < html.length()) {
        size_t p_start = html.find(p_tag, pos);
        if (p_start == std::string::npos) break;
        
        size_t content_start = html.find('>', p_start);
        if (content_start == std::string::npos) break;
        content_start++;
        
        size_t content_end = html.find("</p>", content_start);
        if (content_end == std::string::npos) break;
        
        std::string paragraph = html.substr(content_start, content_end - content_start);
        paragraph = strip_html_tags_simple(paragraph);
        paragraph = fix_text_spacing(paragraph);
        
        // Check if this paragraph meets Google-like quality criteria
        if (paragraph.length() >= config.min_paragraph_length &&
            !is_boilerplate_content(paragraph, config) &&
            contains_meaningful_information(paragraph, config) &&
            has_proper_sentence_structure(paragraph)) {
            return paragraph;
        }
        
        pos = content_end + 4;
    }
    
    return result;
}

bool BasicSnippetExtractor::is_marketing_heavy(const std::string& text, const SnippetConfig& config) const {
    if (text.empty()) return false;
    
    std::vector<std::string> marketing_words = {
        "buy", "purchase", "sale", "discount", "offer", "deal", "shop", "order",
        "subscribe", "sign up", "register", "join", "get", "free", "best", "top",
        "amazing", "incredible", "ultimate", "perfect", "guaranteed", "limited",
        "exclusive", "premium", "professional", "expert", "solution", "service"
    };
    
    std::string lower_text = text;
    std::transform(lower_text.begin(), lower_text.end(), lower_text.begin(), ::tolower);
    
    size_t marketing_count = 0;
    for (const auto& word : marketing_words) {
        size_t pos = 0;
        while ((pos = lower_text.find(word, pos)) != std::string::npos) {
            // Check if it's a whole word
            bool is_whole_word = true;
            if (pos > 0 && std::isalnum(lower_text[pos - 1])) is_whole_word = false;
            if (pos + word.length() < lower_text.length() && std::isalnum(lower_text[pos + word.length()])) is_whole_word = false;
            
            if (is_whole_word) marketing_count++;
            pos += word.length();
        }
    }
    
    size_t total_words = std::count(text.begin(), text.end(), ' ') + 1;
    return total_words > 0 && marketing_count > config.max_marketing_words;
}

bool BasicSnippetExtractor::has_proper_sentence_structure(const std::string& text) const {
    if (text.empty() || text.length() < 20) return false;
    
    // Check for proper sentence endings
    bool has_sentence_ending = false;
    for (char c : text) {
        if (c == '.' || c == '!' || c == '?') {
            has_sentence_ending = true;
            break;
        }
    }
    
    // Check for reasonable word structure (not all caps, reasonable punctuation)
    size_t caps_count = 0;
    size_t letter_count = 0;
    for (char c : text) {
        if (std::isalpha(c)) {
            letter_count++;
            if (std::isupper(c)) caps_count++;
        }
    }
    
    // Avoid all-caps text
    float caps_ratio = letter_count > 0 ? static_cast<float>(caps_count) / letter_count : 0.0f;
    
    return has_sentence_ending && caps_ratio < 0.7f; // Max 70% caps
}

bool BasicSnippetExtractor::contains_meaningful_information(const std::string& text, const SnippetConfig& config) const {
    if (text.empty() || text.length() < config.min_meaningful_words * 4) return false;
    
    // Check for informational content indicators
    std::vector<std::string> info_indicators = {
        "about", "information", "description", "explain", "define", "what", "how", "why", "when", "where",
        "overview", "introduction", "background", "history", "purpose", "method", "process", "result",
        "according", "research", "study", "analysis", "report", "data", "evidence", "fact"
    };
    
    std::string lower_text = text;
    std::transform(lower_text.begin(), lower_text.end(), lower_text.begin(), ::tolower);
    
    size_t info_count = 0;
    for (const auto& indicator : info_indicators) {
        if (lower_text.find(indicator) != std::string::npos) {
            info_count++;
        }
    }
    
    // Avoid purely promotional content
    std::vector<std::string> promo_only = {
        "buy now", "click here", "learn more", "sign up", "get started", "contact us",
        "our services", "we offer", "we provide", "call us", "visit us"
    };
    
    size_t promo_count = 0;
    for (const auto& promo : promo_only) {
        if (lower_text.find(promo) != std::string::npos) {
            promo_count++;
        }
    }
    
    return info_count > 0 || promo_count <= 1;
}

std::string BasicSnippetExtractor::fix_text_spacing(const std::string& text) const {
    if (text.empty()) return text;
    
    std::string result = text;
    
    // Fix common spacing issues
    // 1. Add space after periods if missing
    for (size_t i = 0; i < result.length() - 1; ++i) {
        if (result[i] == '.' && std::isalpha(result[i + 1])) {
            result.insert(i + 1, " ");
        }
    }
    
    // 2. Fix "wordword" concatenations by looking for lowercase followed by uppercase
    for (size_t i = 0; i < result.length() - 1; ++i) {
        if (std::islower(result[i]) && std::isupper(result[i + 1])) {
            // Check if this looks like a word boundary (not an acronym)
            if (i > 0 && std::isalpha(result[i - 1])) {
                result.insert(i + 1, " ");
            }
        }
    }
    
    // 3. Normalize multiple spaces
    std::string normalized;
    bool last_was_space = false;
    for (char c : result) {
        if (std::isspace(c)) {
            if (!last_was_space) {
                normalized += ' ';
                last_was_space = true;
            }
        } else {
            normalized += c;
            last_was_space = false;
        }
    }
    
    // 4. Trim leading/trailing whitespace
    size_t start = normalized.find_first_not_of(" \t\n\r");
    if (start == std::string::npos) return "";
    size_t end = normalized.find_last_not_of(" \t\n\r");
    
    return normalized.substr(start, end - start + 1);
}

std::string BasicSnippetExtractor::create_google_like_snippet(const std::string& text, const SnippetConfig& config) const {
    if (text.empty()) return "";
    
    std::string fixed_text = fix_text_spacing(text);
    auto sentences = extract_sentences(fixed_text, config);
    
    std::string result;
    size_t char_count = 0;
    
    for (const auto& sentence : sentences) {
        if (sentence.length() < config.min_sentence_length) continue;
        if (!has_proper_sentence_structure(sentence)) continue;
        if (is_boilerplate_content(sentence, config)) continue;
        
        // Check if adding this sentence would exceed limit
        if (char_count + sentence.length() + 1 > config.max_snippet_length) {
            // If we haven't added any sentence yet, truncate this one
            if (result.empty() && sentence.length() > config.min_sentence_length) {
                std::string truncated = sentence.substr(0, config.max_snippet_length - 3) + "...";
                return truncated;
            }
            break;
        }
        
        if (!result.empty()) result += " ";
        result += sentence;
        char_count = result.length();
        
        // Stop after target sentences if we have enough content
        if (result.length() >= config.max_snippet_length / 2) break;
    }
    
    // Ensure proper ending
    if (!result.empty() && result.back() != '.' && result.back() != '!' && result.back() != '?') {
        // If it looks like it was cut off, add ellipsis
        if (result.length() > config.max_snippet_length * 0.8) {
            result += "...";
        }
    }
    
    return result;
}

std::string BasicSnippetExtractor::remove_marketing_fluff(const std::string& text, const SnippetConfig& config) const {
    if (text.empty()) return text;
    
    std::vector<std::string> fluff_phrases = {
        "click here", "learn more", "get started", "sign up now", "contact us today",
        "call now", "visit our", "check out", "don't miss", "limited time",
        "act now", "hurry", "exclusive offer", "special deal", "best price"
    };
    
    std::string result = text;
    std::string lower_result = result;
    std::transform(lower_result.begin(), lower_result.end(), lower_result.begin(), ::tolower);
    
    for (const auto& phrase : fluff_phrases) {
        size_t pos = 0;
        while ((pos = lower_result.find(phrase, pos)) != std::string::npos) {
            // Remove the phrase and surrounding context
            size_t start = pos;
            size_t end = pos + phrase.length();
            
            // Extend to remove surrounding sentence if it's mostly fluff
            while (start > 0 && result[start - 1] != '.' && result[start - 1] != '!' && result[start - 1] != '?') {
                start--;
            }
            while (end < result.length() && result[end] != '.' && result[end] != '!' && result[end] != '?') {
                end++;
            }
            if (end < result.length()) end++; // Include the punctuation
            
            result.erase(start, end - start);
            lower_result.erase(start, end - start);
            pos = start;
        }
    }
    
    return fix_text_spacing(result);
}

std::unique_ptr<SnippetExtractor> SnippetExtractorFactory::create_extractor(ExtractorType type) {
    switch (type) {
        case ExtractorType::BASIC:
        default:
            return std::make_unique<BasicSnippetExtractor>();
    }
}

}  // namespace SnippetExtraction