#pragma once

#include <string>
#include <chrono>
#include <mutex>
#include <memory>
#include <unordered_map>
#include <vector>
#include "rocksdb/db.h"

// The result of a non-blocking check against robots.txt rules.
enum class RobotsCheckResult {
    ALLOWED,
    DISALLOWED,
    DEFERRED_FETCH_STARTED
};

class RobotsTxtCache {
private:
    struct RobotsInfo {
        std::string content;
        std::chrono::steady_clock::time_point timestamp;
        bool is_valid = false;
        int last_http_status = 0; // Store the last HTTP status for re-fetch logic
        int crawl_delay = 0; // Crawl-delay in seconds
    };
    
    mutable std::mutex mutex_;
    // Fast in-memory cache for active crawling
    std::unordered_map<std::string, RobotsInfo> cache_;
    // Persistent disk cache
    std::unique_ptr<rocksdb::DB> db_; 

    // The default refresh interval is now 30 days.
    const std::chrono::hours cache_expiry_{30 * 24};
    
    // Helper methods for serialization to/from RocksDB
    std::string serialize(const RobotsInfo& info) const;
    RobotsInfo deserialize(const std::string& value) const;

    // Helper method for parsing rules
    bool parse_rules(const std::string& content, const std::string& user_agent, 
                     std::vector<std::string>& allowed, std::vector<std::string>& disallowed) const;

public:
    explicit RobotsTxtCache(const std::string& db_path);
    
    RobotsCheckResult is_allowed(const std::string& domain, const std::string& path, const std::string& user_agent = "*");
    
    // This function is called by the worker *after* a robots.txt is downloaded.
    void update_cache(const std::string& domain, const std::string& content, int http_status);
    
    /**
     * Call this method from the worker if a crawl is blocked by a cached rule
     * that you believe to be outdated. It will remove the entry from the cache,
     * forcing a fresh download on the next request to that domain.
     */
    void invalidate_for_domain(const std::string& domain);
};