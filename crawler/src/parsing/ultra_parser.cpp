/**
 * 🚀 ULTRA-FAST SIMD HTML PARSER IMPLEMENTATION
 * Targeting 300+ pages/sec with AVX2 acceleration
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
thread_local UltraLinkExtractor* UltraHTMLParser::t_extractor_ = nullptr;
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
#if HAVE_HYPERSCAN
    // Compile noise removal patterns
    const char* patterns[] = {
        "<script[^>]*>.*?</script>",  // Script tags
        "<style[^>]*>.*?</style>",    // Style tags  
        "<!--.*?-->",                 // Comments
        "<noscript[^>]*>.*?</noscript>" // NoScript tags
    };
    
    unsigned int flags[] = {
        HS_FLAG_CASELESS | HS_FLAG_DOTALL,
        HS_FLAG_CASELESS | HS_FLAG_DOTALL,
        HS_FLAG_DOTALL,
        HS_FLAG_CASELESS | HS_FLAG_DOTALL
    };
    
    hs_compile_error_t* compile_err;
    if (hs_compile_multi(patterns, flags, NULL, 4, HS_MODE_BLOCK, 
                        NULL, &noise_filter_db_, &compile_err) != HS_SUCCESS) {
        std::cerr << "Hyperscan compilation failed: " << compile_err->message << std::endl;
        hs_free_compile_error(compile_err);
        noise_filter_db_ = nullptr;
    }
    
    if (noise_filter_db_) {
        hs_alloc_scratch(noise_filter_db_, &scratch_);
    }
#endif
}

SIMDPrefilter::~SIMDPrefilter() {
#if HAVE_HYPERSCAN
    if (scratch_) hs_free_scratch(scratch_);
    if (noise_filter_db_) hs_free_database(noise_filter_db_);
#endif
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

size_t SIMDPrefilter::estimate_link_count(const char* data, size_t len) const {
    if (!g_simd_enabled || len < CrawlerConstants::SIMD::MIN_SIMD_SIZE) {
        // Simple fallback - look for <a href patterns
        size_t count = 0;
        const char* pos = data;
        const char* end = data + len - CrawlerConstants::SIMD::MIN_HREF_SIZE; // Need at least 6 chars for "<a href"
        
        while (pos < end) {
            pos = static_cast<const char*>(std::memchr(pos, '<', end - pos));
            if (!pos) break;
            
            if ((pos[1] == 'a' || pos[1] == 'A') && 
                (pos[2] == ' ' || pos[2] == '\t' || pos[2] == '\n' || pos[2] == '\r')) {
                // Found <a with whitespace, look for href
                const char* href_pos = pos + 2;
                const char* href_end = std::min(href_pos + CrawlerConstants::SIMD::HREF_SEARCH_WINDOW, end); // Search within configured window
                while (href_pos < href_end && (*href_pos == ' ' || *href_pos == '\t' || *href_pos == '\n' || *href_pos == '\r')) href_pos++;
                
                if (href_pos + CrawlerConstants::SIMD::HREF_PATTERN_SIZE < href_end && 
                    (std::strncmp(href_pos, "href", CrawlerConstants::SIMD::HREF_PATTERN_SIZE) == 0 || 
                     std::strncmp(href_pos, "HREF", CrawlerConstants::SIMD::HREF_PATTERN_SIZE) == 0)) {
                    count++;
                }
            }
            pos++;
        }
        return count;
    }
    
    // AVX2-accelerated <a href pattern detection
    const __m256i open_bracket = _mm256_set1_epi8('<');
    size_t count = 0;
    const size_t simd_end = (len >= CrawlerConstants::SIMD::SIMD_LOOKAHEAD) ? 
                           len - CrawlerConstants::SIMD::SIMD_LOOKAHEAD : 0;
    
    for (size_t i = 0; i < simd_end; i += CrawlerConstants::SIMD::CHUNK_SIZE) {
        __m256i chunk = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(data + i));
        __m256i cmp = _mm256_cmpeq_epi8(chunk, open_bracket);
        uint32_t mask = _mm256_movemask_epi8(cmp);
        
        // Check each potential < position
        while (mask) {
            int pos = __builtin_ctz(mask);
            size_t actual_pos = i + pos;
            
            // Check if it's <a href pattern
            if (actual_pos + 6 < len) {
                if ((data[actual_pos + 1] == 'a' || data[actual_pos + 1] == 'A') &&
                    (data[actual_pos + 2] == ' ' || data[actual_pos + 2] == '\t')) {
                    // Quick check for href in next few bytes
                    const char* check_pos = data + actual_pos + 2;
                    const char* check_end = std::min(check_pos + 20, data + len);
                    if (std::search(check_pos, check_end, "href", "href" + 4) != check_end ||
                        std::search(check_pos, check_end, "HREF", "HREF" + 4) != check_end) {
                        count++;
                    }
                }
            }
            
            mask &= mask - 1; // Clear the lowest set bit
        }
    }
    
    return count;
}

bool SIMDPrefilter::is_quality_content(const char* data, size_t len) const {
    if (len < CrawlerConstants::ContentFilter::MIN_CONTENT_SIZE || 
        len > CrawlerConstants::ContentFilter::MAX_CONTENT_SIZE) return false;
    
    // Check for basic HTML structure
    bool has_doctype = (std::search(data, data + std::min(len, (size_t)CrawlerConstants::ContentFilter::HTML_STRUCTURE_CHECK_SIZE), 
                                   "<!DOCTYPE", "<!DOCTYPE" + 9) != data + std::min(len, (size_t)CrawlerConstants::ContentFilter::HTML_STRUCTURE_CHECK_SIZE)) ||
                      (std::search(data, data + std::min(len, (size_t)CrawlerConstants::ContentFilter::HTML_STRUCTURE_CHECK_SIZE), 
                                   "<!doctype", "<!doctype" + 9) != data + std::min(len, (size_t)CrawlerConstants::ContentFilter::HTML_STRUCTURE_CHECK_SIZE));
    
    bool has_html_tag = (std::search(data, data + std::min(len, (size_t)CrawlerConstants::ContentFilter::HTML_STRUCTURE_CHECK_SIZE), 
                                    "<html", "<html" + 5) != data + std::min(len, (size_t)CrawlerConstants::ContentFilter::HTML_STRUCTURE_CHECK_SIZE)) ||
                       (std::search(data, data + std::min(len, (size_t)CrawlerConstants::ContentFilter::HTML_STRUCTURE_CHECK_SIZE), 
                                    "<HTML", "<HTML" + 5) != data + std::min(len, (size_t)CrawlerConstants::ContentFilter::HTML_STRUCTURE_CHECK_SIZE));
    
    if (!has_doctype && !has_html_tag) return false;
    
    // Estimate link count
    size_t link_count = estimate_link_count(data, len);
    if (link_count < CrawlerConstants::ContentFilter::QUALITY_MIN_LINKS) return false;
    
    // Quick text content check - look for reasonable amount of text
    size_t text_chars = 0;
    bool in_tag = false;
    const char* end = data + std::min(len, (size_t)CrawlerConstants::ContentFilter::QUALITY_CHECK_SIZE); // Check first configured KB for speed
    
    for (const char* p = data; p < end; ++p) {
        if (*p == '<') in_tag = true;
        else if (*p == '>') in_tag = false;
        else if (!in_tag && std::isalnum(*p)) text_chars++;
    }
    
    return text_chars > CrawlerConstants::ContentFilter::QUALITY_MIN_TEXT_CHARS; // At least configured text characters
}

std::string_view SIMDPrefilter::filter_noise(const char* data, size_t len, char* output_buffer) const {
#if HAVE_HYPERSCAN
    if (noise_filter_db_ && scratch_) {
        // Use Hyperscan to remove noise patterns
        std::vector<std::pair<size_t, size_t>> matches;
        
        auto match_handler = [](unsigned int id, unsigned long long from, 
                               unsigned long long to, unsigned int flags, void* context) -> int {
            auto* match_vec = static_cast<std::vector<std::pair<size_t, size_t>>*>(context);
            match_vec->emplace_back(from, to);
            return 0; // Continue matching
        };
        
        hs_scan(noise_filter_db_, data, len, 0, scratch_, match_handler, &matches);
        
        // Copy data excluding matched regions
        if (matches.empty()) {
            return std::string_view(data, len); // No noise found
        }
        
        // Sort matches by position
        std::sort(matches.begin(), matches.end());
        
        char* out_ptr = output_buffer;
        size_t pos = 0;
        
        for (const auto& [start, end] : matches) {
            // Copy content before match
            if (start > pos) {
                size_t copy_len = start - pos;
                std::memcpy(out_ptr, data + pos, copy_len);
                out_ptr += copy_len;
            }
            pos = end;
        }
        
        // Copy remaining content
        if (pos < len) {
            size_t copy_len = len - pos;
            std::memcpy(out_ptr, data + pos, copy_len);
            out_ptr += copy_len;
        }
        
        return std::string_view(output_buffer, out_ptr - output_buffer);
    }
#endif
    
    // Fallback - return original data
    return std::string_view(data, len);
}

// ============= STAGE 2: STREAMING TOKENIZER IMPLEMENTATION =============

void StreamingTokenizer::feed(const char* data, size_t length) {
    for (size_t i = 0; i < length; ++i) {
        position_ = i;
        process_byte(data[i], data);
    }
}

void StreamingTokenizer::process_byte(char c, const char* data) {
    switch (state_) {
        case ParserState::TEXT:
            if (c == '<') {
                state_ = ParserState::TAG_OPEN;
                tag_start_ = position_;
                current_tag_.is_closing = false; // Initialize as opening tag
            }
            break;
            
        case ParserState::TAG_OPEN:
            if (c == '/') {
                current_tag_.is_closing = true;
            } else if (std::isalpha(c)) {
                state_ = ParserState::TAG_NAME;
                // is_closing is already set correctly from above
                current_tag_.start_pos = position_;
            } else if (c == '>') {
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
            if (c == '>') {
                state_ = ParserState::TEXT;
            }
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
    
    // Check for anchor tags (case insensitive)
    if (tag.name.length() == 1 && (tag.name[0] == 'a' || tag.name[0] == 'A')) {
        in_anchor_tag_ = true;
        current_href_.clear();
    }
}

void UltraLinkExtractor::on_tag_close(const TagInfo& tag) {
    // Check for anchor tags (case insensitive)
    if (tag.name.length() == 1 && (tag.name[0] == 'a' || tag.name[0] == 'A') && in_anchor_tag_) {
        in_anchor_tag_ = false;
        
        if (!current_href_.empty()) {
            process_href_value(current_href_);
            current_href_.clear();
        }
    }
}

void UltraLinkExtractor::on_attribute(const AttributeInfo& attr) {
    if (in_anchor_tag_) {
        // Check for href attribute (case insensitive)
        bool is_href = (attr.name.length() == 4) && 
                      ((attr.name[0] == 'h' || attr.name[0] == 'H') &&
                       (attr.name[1] == 'r' || attr.name[1] == 'R') &&
                       (attr.name[2] == 'e' || attr.name[2] == 'E') &&
                       (attr.name[3] == 'f' || attr.name[3] == 'F'));
        
        if (is_href) {
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
    ZoneScopedN("UltraParser - extract_links_ultra"); // Parent zone for the whole function

    auto start_time = std::chrono::high_resolution_clock::now();
    
    if (!t_extractor_) {
        t_extractor_ = new UltraLinkExtractor(base_url);
    } else {
        t_extractor_->set_base_url(base_url);
    }
    
    // INSTRUMENTED: Profile each stage of the parser
    {
        ZoneScopedN("UltraParser - Prefilter Quality Check");
        if (!prefilter_.is_html_content(html.data(), html.length()) || !prefilter_.is_quality_content(html.data(), html.length())) {
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

void UltraHTMLParser::set_max_html_size(size_t size) {
    g_max_html_size = size;
}

void UltraHTMLParser::enable_simd_acceleration(bool enable) {
    g_simd_enabled = enable;
}

} // namespace UltraParser
