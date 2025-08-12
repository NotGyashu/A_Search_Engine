#pragma once

/**
 * 🚀 ULTRA-FAST SIMD HTML PARSER
 * 3-Stage Hybrid Architecture for 300+ pages/sec
 * Stage 1: SIMD Prefilter (AVX2)
 * Stage 2: Streaming Tokenizer (Zero-allocation FSM)
 * Stage 3: Targeted DOM Extraction (Links only)
 */

#include "constants.h"
#include <immintrin.h>
#include <string_view>
#include <string>
#include <vector>
#include <unordered_map>
#include <atomic>
#include <thread>
#include <chrono>
#include <functional>
#include <memory>
#include <re2/re2.h>


namespace UltraParser {

// ============= STAGE 1: SIMD PREFILTER =============

class SIMDPrefilter {
private:
    static constexpr size_t CHUNK_SIZE = CrawlerConstants::SIMD::CHUNK_SIZE; // AVX2 256-bit chunks
    
public:
    SIMDPrefilter();
    ~SIMDPrefilter();
    
    // AVX2-accelerated HTML detection
    bool is_html_content(const char* data, size_t len) const;
    
    // Remove <script>, <style>, comments using SIMD + Hyperscan
    std::string_view filter_noise(const char* data, size_t len, char* output_buffer) const;
    std::vector<std::unique_ptr<re2::RE2>> noise_patterns_;
    // Quick link density check
    size_t estimate_link_count(const char* data, size_t len) const;
    
    // Quick quality assessment
    bool is_quality_content(const char* data, size_t len) const;
};

// ============= STAGE 2: STREAMING TOKENIZER =============

enum class ParserState : uint8_t {
    TEXT = 0,
    TAG_OPEN,
    TAG_NAME,
    ATTR_NAME,
    ATTR_VALUE_START,
    ATTR_VALUE,
    TAG_CLOSE
};

struct TagInfo {
    std::string_view name;
    size_t start_pos;
    size_t end_pos;
    bool is_closing;
};

struct AttributeInfo {
    std::string_view name;
    std::string_view value;
};

class StreamingTokenizer {
private:
    ParserState state_ = ParserState::TEXT;
    size_t position_ = 0;
    size_t tag_start_ = 0;
    size_t attr_name_start_ = 0;
    size_t attr_value_start_ = 0;
    char quote_char_ = 0;
    
    // Buffers for current parsing
    TagInfo current_tag_;
    AttributeInfo current_attr_;
    
public:
    virtual ~StreamingTokenizer() = default;
    
    // Reset parser state
    void reset() {
        state_ = ParserState::TEXT;
        position_ = 0;
        tag_start_ = 0;
        attr_name_start_ = 0;
        attr_value_start_ = 0;
        quote_char_ = 0;
        current_tag_ = TagInfo{};
        current_attr_ = AttributeInfo{};
    }
    
    // Main parsing entry point
    void feed(const char* data, size_t length);
    
    // Override these in derived classes
    virtual void on_tag_open(const TagInfo& tag) {}
    virtual void on_tag_close(const TagInfo& tag) {}
    virtual void on_attribute(const AttributeInfo& attr) {}
    virtual void on_text(std::string_view text) {}
    
private:
    void process_byte(char c, const char* data);
    void handle_tag_name_char(char c, const char* data);
    void handle_attribute_name_char(char c, const char* data);
    void handle_attribute_value_char(char c, const char* data);
};

// ============= STAGE 3: TARGETED EXTRACTION =============

class UltraLinkExtractor : public StreamingTokenizer {
private:
    std::vector<std::string> links_;
    std::string base_url_;
    
    // State for link extraction
    bool in_anchor_tag_ = false;
    std::string current_href_;
    
    // Performance counters
    mutable size_t links_found_ = 0;
    mutable size_t tags_processed_ = 0;

public:
    explicit UltraLinkExtractor(const std::string& base_url) : base_url_(base_url) {
        links_.reserve(50); // Pre-allocate for typical page
    }
    
    // Extract all links from HTML
    std::vector<std::string> extract_links(const char* html, size_t length);
    std::vector<std::string> extract_links(const std::string& html) {
        return extract_links(html.data(), html.length());
    }
    
    // Update base URL for link resolution
    void set_base_url(const std::string& base_url) {
        base_url_ = base_url;
    }
    
    // Performance metrics
    size_t get_links_found() const { return links_found_; }
    size_t get_tags_processed() const { return tags_processed_; }
    
protected:
    void on_tag_open(const TagInfo& tag) override;
    void on_tag_close(const TagInfo& tag) override;
    void on_attribute(const AttributeInfo& attr) override;

private:
    void process_href_value(std::string_view href);
    std::string resolve_url(std::string_view relative_url) const;
};

// ============= ULTRA PARSER FACADE =============

class UltraHTMLParser {
private:
    SIMDPrefilter prefilter_;
    thread_local static std::unique_ptr<UltraLinkExtractor> t_extractor_;
    thread_local static std::vector<char> t_filter_buffer_;

public:
    UltraHTMLParser() = default;
    
    // Main parsing interface - optimized for 300+ pages/sec
    std::vector<std::string> extract_links_ultra(const std::string& html, const std::string& base_url);
    
    // Batch processing for even better performance
    struct BatchResult {
        std::vector<std::vector<std::string>> all_links;
        size_t total_links;
        double processing_time_ms;
    };
    
    BatchResult extract_links_batch(const std::vector<std::pair<std::string, std::string>>& html_pages);
    
    // Performance monitoring (using static globals to avoid threading issues)
    void print_performance_stats() const;
    double get_avg_processing_time_ms() const;
    size_t get_pages_processed() const;
    
    // Configuration
    static void set_max_html_size(size_t size);
    static void enable_simd_acceleration(bool enable);
};

// ============= MEMORY OPTIMIZATION HELPERS =============

class MemoryPool {
private:
    std::vector<char> buffer_;
    size_t position_ = 0;
    
public:
    explicit MemoryPool(size_t size = CrawlerConstants::SIMD::MEMORY_POOL_SIZE) : buffer_(size) {} // Configurable memory pool
    
    char* allocate(size_t size) {
        if (position_ + size > buffer_.size()) {
            position_ = 0; // Reset pool (circular)
        }
        char* ptr = buffer_.data() + position_;
        position_ += size;
        return ptr;
    }
    
    void reset() { position_ = 0; }
};

// Thread-local memory pools for zero-allocation parsing
extern thread_local MemoryPool t_memory_pool;

} // namespace UltraParser
