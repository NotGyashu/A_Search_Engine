#pragma once

#include <string>
#include <unordered_map>
#include <chrono>
#include <mutex>

/**
 * Phase 2: Conditional GET Support (ETag and Last-Modified headers)
 * Efficiently checks if content has changed before downloading
 */

namespace ConditionalGet {

struct HttpHeaders {
    std::string etag;
    std::string last_modified;
    std::chrono::system_clock::time_point response_time;
    
    HttpHeaders() : response_time(std::chrono::system_clock::now()) {}
    
    bool has_cache_info() const {
        return !etag.empty() || !last_modified.empty();
    }
};

class ConditionalGetManager {
private:
    // Store cache headers for each URL
    std::unordered_map<std::string, HttpHeaders> url_cache_;
    std::mutex cache_mutex_;

public:
    ConditionalGetManager() = default;
    
    // Check if we should download a URL based on cache headers
    bool should_download(const std::string& url);
    
    // Perform conditional GET request
    struct ConditionalGetResult {
        bool content_changed = true;
        std::string content;
        int http_status = 0;
        HttpHeaders headers;
    };
    
    ConditionalGetResult conditional_get(const std::string& url);
    
    // Update cache with new headers after successful download
    void update_cache(const std::string& url, const HttpHeaders& headers);
    
    // Get cache info for a URL
    HttpHeaders get_cache_info(const std::string& url);
    
    // Clear cache for a URL
    void clear_cache(const std::string& url);
    
    // Get cache statistics
    size_t get_cache_size() const;
    void print_cache_stats() const;
    
    // Load/save cache to disk (for persistence across restarts)
    bool save_cache_to_file(const std::string& cache_file_path);
    bool load_cache_from_file(const std::string& cache_file_path);
};

} // namespace ConditionalGet
