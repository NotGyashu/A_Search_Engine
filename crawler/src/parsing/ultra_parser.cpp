/**
 * 🚀 SIMD HTML PARSER IMPLEMENTATION
 */

#include "ultra_parser.h"
#include "constants.h"
#include <algorithm>
#include <cstring>
#include <chrono>
#include <iostream>
#include <iomanip>
#include "tracy/Tracy.hpp"

namespace UltraParser {

// Thread-local storage
thread_local std::unique_ptr<UltraLinkExtractor> UltraHTMLParser::t_extractor_ = nullptr;
thread_local std::vector<char> UltraHTMLParser::t_filter_buffer_;
thread_local MemoryPool t_memory_pool;

// Global performance counters
static std::atomic<size_t> g_pages_processed{0};
static std::atomic<size_t> g_total_processing_time_us{0};
static std::atomic<size_t> g_simd_filtered{0};
static std::atomic<size_t> g_links_extracted{0};

// Configuration globals
static size_t g_max_html_size = CrawlerConstants::SIMD::MAX_HTML_SIZE;
static bool g_simd_enabled = true;

// ============= STAGE 1: SIMD PREFILTER IMPLEMENTATION =============

SIMDPrefilter::SIMDPrefilter() {
    RE2::Options opts;
    opts.set_case_sensitive(false); // Case-insensitive
    opts.set_dot_nl(true);          // '.' matches newlines
    opts.set_max_mem(1024 * 1024);  // Limit memory usage to 1MB per pattern

    // Optimized regex patterns - simpler and faster
    noise_patterns_.emplace_back(std::make_unique<re2::RE2>("<script[^>]*>.*?</script>", opts));
    noise_patterns_.emplace_back(std::make_unique<re2::RE2>("<style[^>]*>.*?</style>", opts));
    noise_patterns_.emplace_back(std::make_unique<re2::RE2>("<!--.*?-->", opts)); // ✅ Fixed comment pattern
    noise_patterns_.emplace_back(std::make_unique<re2::RE2>("<noscript[^>]*>.*?</noscript>", opts));
}




SIMDPrefilter::~SIMDPrefilter() {
}

bool SIMDPrefilter::is_html_content(const char* data, size_t len) const {
    if (!g_simd_enabled || len < CrawlerConstants::SIMD::MIN_SIMD_SIZE) {
        // Fallback for small content
        return std::string_view(data, std::min(len, size_t(100))).find('<') != std::string_view::npos;
    }
    
    // AVX2-accelerated HTML tag detection
    const __m256i html_mask = _mm256_set1_epi8('<');
    const size_t simd_end = (len / CrawlerConstants::SIMD::CHUNK_SIZE) * CrawlerConstants::SIMD::CHUNK_SIZE;
    
    for (size_t i = 0; i < simd_end; i += CrawlerConstants::SIMD::CHUNK_SIZE) {
        __m256i chunk = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(data + i));
        __m256i cmp = _mm256_cmpeq_epi8(chunk, html_mask);
        
        if (!_mm256_testz_si256(cmp, cmp)) {
            return true; // Found '<' character
        }
    }
    
    // Handle remaining bytes
    for (size_t i = simd_end; i < len; ++i) {
        if (data[i] == '<') return true;
    }
    
    return false;
}

bool SIMDPrefilter::is_quality_content(const char* data, size_t len) const {
    // Fast size checks first
    if (len < CrawlerConstants::ContentFilter::MIN_CONTENT_SIZE ) {
        return false;
    }
    if (len > CrawlerConstants::ContentFilter::MAX_CONTENT_SIZE){
        return false;
    }

    // Use SIMD-optimized search for HTML structure patterns
    const size_t check_size = std::min(len, (size_t)CrawlerConstants::ContentFilter::HTML_STRUCTURE_CHECK_SIZE);
    
    // Fast SIMD-based search for doctype and html tags
    bool has_doctype = false;
    bool has_html_tag = false;
    
    // Vectorized search for common HTML patterns
    if (check_size >= 9) {
        const char* end = data + check_size;
        
        // Look for <!DOCTYPE or <!doctype
        for (const char* p = data; p <= end - 9; ++p) {
            if (p[0] == '<' && p[1] == '!' && 
                ((p[2] == 'D' || p[2] == 'd') && 
                 (p[3] == 'O' || p[3] == 'o') && 
                 (p[4] == 'C' || p[4] == 'c'))) {
                has_doctype = true;
                break;
            }
        }
        
        // Look for <html or <HTML
        if (!has_doctype) {
            for (const char* p = data; p <= end - 5; ++p) {
                if (p[0] == '<' && 
                    ((p[1] == 'h' || p[1] == 'H') &&
                     (p[2] == 't' || p[2] == 'T') &&
                     (p[3] == 'm' || p[3] == 'M') &&
                     (p[4] == 'l' || p[4] == 'L'))) {
                    has_html_tag = true;
                    break;
                }
            }
        }
    }

    if (!has_doctype && !has_html_tag){
        return false;
    }

    // Optimized text content check using vectorized counting
    size_t text_chars = 0;
    bool in_tag = false;
    const char* end = data + std::min(len, (size_t)CrawlerConstants::ContentFilter::QUALITY_CHECK_SIZE);
    
    // Process in chunks for better cache performance
    const size_t chunk_size = 64;
    for (const char* chunk_start = data; chunk_start < end; chunk_start += chunk_size) {
        const char* chunk_end = std::min(chunk_start + chunk_size, end);
        
        for (const char* p = chunk_start; p < chunk_end; ++p) {
            if (*p == '<') in_tag = true;
            else if (*p == '>') in_tag = false;
            else if (!in_tag && std::isalnum(*p)) text_chars++;
        }
    }
    
    return text_chars > CrawlerConstants::ContentFilter::QUALITY_MIN_TEXT_CHARS;
}

std::string_view SIMDPrefilter::filter_noise(const char* data, size_t len, char* output_buffer) const {
    // Ultra-fast path: Skip filtering for small content that likely has no noise
    if (len < 512) {
        std::memcpy(output_buffer, data, len);
        return std::string_view(output_buffer, len);
    }
    
    // Quick heuristic: If no noise patterns detected, skip expensive regex entirely
    const char* script_pos = std::search(data, data + len, "<script", "<script" + 7);
    const char* style_pos = std::search(data, data + len, "<style", "<style" + 6);
    const char* comment_pos = std::search(data, data + len, "<!--", "<!--" + 4);
    
    bool has_script = (script_pos != data + len);
    bool has_style = (style_pos != data + len);
    bool has_comment = (comment_pos != data + len);
    
    // If no noise patterns found, return original content immediately
    if (!has_script && !has_style && !has_comment) {
        std::memcpy(output_buffer, data, len);
        return std::string_view(output_buffer, len);
    }
    
    // Manual fast removal for simple cases (avoid regex overhead)
    thread_local std::string temp_content;
    temp_content.clear();
    temp_content.reserve(len);
    temp_content.assign(data, len);
    
    size_t before_len = temp_content.size();
    size_t removals = 0;
    
    // Fast manual removal for script tags (most common)
    if (has_script) {
        size_t pos = 0;
        while ((pos = temp_content.find("<script", pos)) != std::string::npos) {
            size_t end_pos = temp_content.find("</script>", pos);
            if (end_pos != std::string::npos) {
                end_pos += 9; // Include closing tag
                temp_content.erase(pos, end_pos - pos);
                removals++;
                // Limit removals to prevent infinite loops
                if (removals > 50) break;
            } else {
                break;
            }
        }
    }
    
    // Fast manual removal for style tags
    if (has_style && removals < 50) {
        size_t pos = 0;
        while ((pos = temp_content.find("<style", pos)) != std::string::npos) {
            size_t end_pos = temp_content.find("</style>", pos);
            if (end_pos != std::string::npos) {
                end_pos += 8; // Include closing tag
                temp_content.erase(pos, end_pos - pos);
                removals++;
                if (removals > 50) break;
            } else {
                break;
            }
        }
    }
    
    // Fast manual removal for comments
    if (has_comment && removals < 50) {
        size_t pos = 0;
        while ((pos = temp_content.find("<!--", pos)) != std::string::npos) {
            size_t end_pos = temp_content.find("-->", pos);
            if (end_pos != std::string::npos) {
                end_pos += 3; // Include closing tag
                temp_content.erase(pos, end_pos - pos);
                removals++;
                if (removals > 50) break;
            } else {
                break;
            }
        }
    }
    
    size_t after_len = temp_content.size();
    
    // Safety check: revert if too much content removed
    if (before_len > 0 && after_len < before_len * 0.3) {
        std::memcpy(output_buffer, data, len);
        return std::string_view(output_buffer, len);
    }
    
    // Copy result to output buffer
    std::memcpy(output_buffer, temp_content.data(), after_len);
    return std::string_view(output_buffer, after_len);
}

// ============= STAGE 2: STREAMING TOKENIZER IMPLEMENTATION =============

void StreamingTokenizer::feed(const char* data, size_t length) {
    // Optimize for bulk processing
    for (size_t i = 0; i < length; ++i) {
        position_ = i;
        const char c = data[i];
        
        // Fast path for TEXT state (most common)
        if (__builtin_expect(state_ == ParserState::TEXT, 1)) {
            if (__builtin_expect(c == '<', 0)) {
                state_ = ParserState::TAG_OPEN;
                tag_start_ = position_;
                current_tag_.is_closing = false;
            }
            continue;
        }
        
        // Handle other states
        process_byte(c, data);
    }
}

void StreamingTokenizer::process_byte(char c, const char* data) {
    switch (state_) {
        case ParserState::TAG_OPEN:
            if (__builtin_expect(c == '/', 0)) {
                current_tag_.is_closing = true;
            } else if (__builtin_expect(std::isalpha(c), 1)) {
                state_ = ParserState::TAG_NAME;
                current_tag_.start_pos = position_;
            } else if (__builtin_expect(c == '>', 0)) {
                state_ = ParserState::TEXT;
            }
            break;
            
        case ParserState::TAG_NAME:
            handle_tag_name_char(c, data);
            break;
            
        case ParserState::ATTR_NAME:
            handle_attribute_name_char(c, data);
            break;
            
        case ParserState::ATTR_VALUE_START:
        case ParserState::ATTR_VALUE:
            handle_attribute_value_char(c, data);
            break;
            
        case ParserState::TAG_CLOSE:
            if (__builtin_expect(c == '>', 1)) {
                state_ = ParserState::TEXT;
            }
            break;
            
        default:
            // TEXT state is handled in feed() for performance
            break;
    }
}

void StreamingTokenizer::handle_tag_name_char(char c, const char* data) {
    if (std::isspace(c)) {
        // End of tag name
        current_tag_.name = std::string_view(data + current_tag_.start_pos, 
                                           position_ - current_tag_.start_pos);
        if (current_tag_.is_closing) {
            on_tag_close(current_tag_);
            state_ = ParserState::TAG_CLOSE; // Skip to tag close for closing tags
        } else {
            on_tag_open(current_tag_);
            state_ = ParserState::ATTR_NAME;
            attr_name_start_ = 0; // Reset attribute parsing
        }
    } else if (c == '>') {
        // Self-closing tag or tag with no attributes
        current_tag_.name = std::string_view(data + current_tag_.start_pos, 
                                           position_ - current_tag_.start_pos);
        current_tag_.end_pos = position_;
        if (current_tag_.is_closing) {
            on_tag_close(current_tag_);
        } else {
            on_tag_open(current_tag_);
        }
        state_ = ParserState::TEXT;
    } else if (c == '/') {
        // Self-closing tag like <br/>
        current_tag_.name = std::string_view(data + current_tag_.start_pos, 
                                           position_ - current_tag_.start_pos);
        on_tag_open(current_tag_);
        state_ = ParserState::TAG_CLOSE;
    }
}

void StreamingTokenizer::handle_attribute_name_char(char c, const char* data) {
    if (std::isspace(c)) {
        // Skip whitespace between attributes
        if (attr_name_start_ > 0) {
            // We have an attribute name, move to value parsing
            current_attr_.name = std::string_view(data + attr_name_start_, 
                                                position_ - attr_name_start_);
            state_ = ParserState::ATTR_VALUE_START;
            attr_name_start_ = 0;
        }
        return;
    } else if (c == '=') {
        // End of attribute name
        if (attr_name_start_ > 0) {
            current_attr_.name = std::string_view(data + attr_name_start_, 
                                                position_ - attr_name_start_);
            state_ = ParserState::ATTR_VALUE_START;
            attr_name_start_ = 0;
        }
    } else if (c == '>') {
        // End of tag
        state_ = ParserState::TEXT;
        attr_name_start_ = 0;
    } else if (std::isalpha(c) && attr_name_start_ == 0) {
        // Start of new attribute name
        attr_name_start_ = position_;
    }
}

void StreamingTokenizer::handle_attribute_value_char(char c, const char* data) {
    if (state_ == ParserState::ATTR_VALUE_START) {
        if (c == '"' || c == '\'') {
            quote_char_ = c;
            attr_value_start_ = position_ + 1;
            state_ = ParserState::ATTR_VALUE;
        } else if (!std::isspace(c) && c != '>') {
            // Unquoted value
            quote_char_ = ' ';
            attr_value_start_ = position_;
            state_ = ParserState::ATTR_VALUE;
        } else if (c == '>') {
            // Tag ends without value
            state_ = ParserState::TEXT;
            attr_name_start_ = 0;
            attr_value_start_ = 0;
        }
    } else if (state_ == ParserState::ATTR_VALUE) {
        bool value_end = (quote_char_ == ' ') ? (std::isspace(c) || c == '>') 
                                             : (c == quote_char_);
        
        if (value_end) {
            current_attr_.value = std::string_view(data + attr_value_start_, 
                                                 position_ - attr_value_start_);
            on_attribute(current_attr_);
            
            // Reset for next attribute
            attr_name_start_ = 0;
            attr_value_start_ = 0;
            quote_char_ = 0;
            
            if (c == '>') {
                state_ = ParserState::TEXT;
            } else {
                state_ = ParserState::ATTR_NAME;
            }
        }
    }
}

// ============= STAGE 3: ULTRA LINK EXTRACTOR IMPLEMENTATION =============

std::vector<std::string> UltraLinkExtractor::extract_links(const char* html, size_t length) {
    links_.clear();
    links_found_ = 0;
    tags_processed_ = 0;
    in_anchor_tag_ = false;
    current_href_.clear();
    
    // Reset parsing state
    reset();
    
    // Truncate if too large
    size_t parse_length = std::min(length, g_max_html_size);
    
    // Parse HTML
    feed(html, parse_length);
    
    links_found_ = links_.size();
    return std::move(links_);
}

void UltraLinkExtractor::on_tag_open(const TagInfo& tag) {
    tags_processed_++;
    
    // Optimized case-insensitive anchor tag detection using bit manipulation
    if (__builtin_expect(tag.name.length() == 1, 0)) {
        const char c = tag.name[0] | 0x20; // Convert to lowercase using bit manipulation
        if (__builtin_expect(c == 'a', 0)) {
            in_anchor_tag_ = true;
            current_href_.clear();
        }
    }
}

void UltraLinkExtractor::on_tag_close(const TagInfo& tag) {
    // Optimized case-insensitive anchor tag detection
    if (__builtin_expect(tag.name.length() == 1 && in_anchor_tag_, 0)) {
        const char c = tag.name[0] | 0x20; // Convert to lowercase
        if (c == 'a') {
            in_anchor_tag_ = false;
            
            if (!current_href_.empty()) {
                process_href_value(current_href_);
                current_href_.clear();
            }
        }
    }
}

void UltraLinkExtractor::on_attribute(const AttributeInfo& attr) {
    if (__builtin_expect(in_anchor_tag_ && attr.name.length() == 4, 0)) {
        // Fast case-insensitive href detection using bit manipulation
        const char* name = attr.name.data();
        if (((name[0] | 0x20) == 'h') &&
            ((name[1] | 0x20) == 'r') &&
            ((name[2] | 0x20) == 'e') &&
            ((name[3] | 0x20) == 'f')) {
            current_href_ = std::string(attr.value);
        }
    }
}

void UltraLinkExtractor::process_href_value(std::string_view href) {
    if (href.empty() || href == "#") return;
    
    std::string url;
    if (href.find("://") != std::string_view::npos) {
        url = std::string(href);
    } else {
        url = resolve_url(href);
    }
    
    if (!url.empty() && url.length() < 2048) {
        links_.push_back(std::move(url));
    }
}

std::string UltraLinkExtractor::resolve_url(std::string_view relative_url) const {
    if (relative_url.empty()) return "";
    
    if (relative_url[0] == '/') {
        // Absolute path
        size_t protocol_end = base_url_.find("://");
        if (protocol_end == std::string::npos) return "";
        
        size_t domain_end = base_url_.find('/', protocol_end + 3);
        std::string base_domain = (domain_end == std::string::npos) 
            ? base_url_ : base_url_.substr(0, domain_end);
        
        return base_domain + std::string(relative_url);
    } else {
        // Relative path
        std::string base = base_url_;
        if (base.back() != '/') {
            size_t last_slash = base.find_last_of('/');
            if (last_slash != std::string::npos && last_slash > base.find("://") + 2) {
                base = base.substr(0, last_slash + 1);
            } else {
                base += "/";
            }
        }
        return base + std::string(relative_url);
    }
}

// ============= ULTRA PARSER FACADE IMPLEMENTATION =============

std::vector<std::string> UltraHTMLParser::extract_links_ultra(const std::string& html, const std::string& base_url) {
    ZoneScopedN("UltraParser - extract_links_ultra");

    auto start_time = std::chrono::high_resolution_clock::now();
    
    // Early exit for small/empty content
    if (__builtin_expect(html.empty() || html.length() < 100, 0)) {
        return {};
    }
    
    // Early exit for extremely large content that might cause performance issues
    if (__builtin_expect(html.length() > 5 * 1024 * 1024, 0)) { // Skip files > 5MB
        g_simd_filtered.fetch_add(1);
        return {};
    }
    
    if (!t_extractor_) {
        t_extractor_ = std::make_unique<UltraLinkExtractor>(base_url);
    } else {
        t_extractor_->set_base_url(base_url);
    }
    
    // Combine quality and HTML checks for better cache locality
    {
        ZoneScopedN("UltraParser - Prefilter Quality & HTML Check");
        
        // Fast heuristic: check for HTML tags first (cheapest check)
        bool has_angle_bracket = html.find('<') != std::string::npos;
        if (__builtin_expect(!has_angle_bracket, 0)) {
            g_simd_filtered.fetch_add(1);
            return {};
        }
        
        // Then check content quality
        bool is_quality = prefilter_.is_quality_content(html.data(), html.length());
        if (__builtin_expect(!is_quality, 0)) {
            g_simd_filtered.fetch_add(1);
            return {};
        }
        
        // Finally do the more expensive HTML content check
        bool is_html = prefilter_.is_html_content(html.data(), html.length());
        if (__builtin_expect(!is_html, 0)) {
            g_simd_filtered.fetch_add(1);
            return {};
        }
    }
    
    std::string_view filtered_view;
    {
        ZoneScopedN("UltraParser - Prefilter Noise Filter");
        if (t_filter_buffer_.size() < html.length()) {
            t_filter_buffer_.resize(html.length() * 2);
        }
        filtered_view = prefilter_.filter_noise(html.data(), html.length(), t_filter_buffer_.data());
    }
    
    // Early exit if no anchor tags after filtering
    if (__builtin_expect(filtered_view.find("<a") == std::string_view::npos && 
                         filtered_view.find("<A") == std::string_view::npos, 0)) {
        return {};
    }

    std::vector<std::string> links;
    {
        ZoneScopedN("UltraParser - Streaming Extraction");
        links = t_extractor_->extract_links(filtered_view.data(), filtered_view.length());
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
    
    g_pages_processed.fetch_add(1);
    g_total_processing_time_us.fetch_add(duration.count());
    g_links_extracted.fetch_add(links.size());
    
    return links;
}

void UltraHTMLParser::print_performance_stats() const {
    size_t pages = g_pages_processed.load();
    if (pages == 0) return;
    
    double avg_time_ms = g_total_processing_time_us.load() / 1000.0 / pages;
    double pages_per_sec = 1000.0 / avg_time_ms;
    
    std::cout << "\n🚀 ULTRA PARSER PERFORMANCE STATS 🚀\n";
    std::cout << "=====================================\n";
    std::cout << "Pages processed: " << pages << "\n";
    std::cout << "Average time per page: " << std::fixed << std::setprecision(2) << avg_time_ms << " ms\n";
    std::cout << "Theoretical max speed: " << std::fixed << std::setprecision(0) << pages_per_sec << " pages/sec\n";
    std::cout << "SIMD filtered pages: " << g_simd_filtered.load() << " (" 
              << (g_simd_filtered.load() * 100 / pages) << "%)\n";
    std::cout << "Total links extracted: " << g_links_extracted.load() << "\n";
    std::cout << "Avg links per page: " << (g_links_extracted.load() / pages) << "\n";
    std::cout << "=====================================\n\n";
}

double UltraHTMLParser::get_avg_processing_time_ms() const {
    size_t pages = g_pages_processed.load();
    return pages > 0 ? (g_total_processing_time_us.load() / 1000.0 / pages) : 0.0;
}

size_t UltraHTMLParser::get_pages_processed() const {
    return g_pages_processed.load();
}

UltraHTMLParser::BatchResult UltraHTMLParser::extract_links_batch(const std::vector<std::pair<std::string, std::string>>& html_pages) {
    ZoneScopedN("UltraParser - extract_links_batch");
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    BatchResult result;
    result.all_links.reserve(html_pages.size());
    result.total_links = 0;
    
    // Process pages in batch with reduced per-page overhead
    for (const auto& [html, base_url] : html_pages) {
        // Use the optimized single-page extraction
        auto links = extract_links_ultra(html, base_url);
        result.total_links += links.size();
        result.all_links.emplace_back(std::move(links));
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
    result.processing_time_ms = duration.count() / 1000.0;
    
    return result;
}

void UltraHTMLParser::set_max_html_size(size_t size) {
    g_max_html_size = size;
}

void UltraHTMLParser::enable_simd_acceleration(bool enable) {
    g_simd_enabled = enable;
}

} // namespace UltraParser
