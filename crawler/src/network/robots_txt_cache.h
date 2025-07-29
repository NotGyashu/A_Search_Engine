#pragma once

#include <unordered_map>
#include <string>
#include <chrono>
#include <mutex>
#include <memory>

// Forward declaration
class HttpClient;

// The result of a non-blocking check against robots.txt rules.
enum class RobotsCheckResult {
    ALLOWED,
    DISALLOWED,
    // The robots.txt for this domain is not cached; a fetch has been started.
    // The original URL should be deferred until the fetch is complete.
    DEFERRED_FETCH_STARTED
};

class RobotsTxtCache {
private:
    struct RobotsInfo {
        std::string content;
        std::chrono::steady_clock::time_point timestamp;
        bool is_valid = false; // Is the content valid or is this a placeholder?
    };
    
    mutable std::mutex mutex_;
    std::unordered_map<std::string, RobotsInfo> cache_;
    const std::chrono::hours cache_expiry_{24};
    // HttpClient is no longer needed here as fetching moves to the worker.
    
public:
    explicit RobotsTxtCache();
    
    // The non-blocking check function.
    RobotsCheckResult is_allowed(const std::string& domain, const std::string& path, const std::string& user_agent = "*");
    
    // This function is now called by the worker *after* a robots.txt is downloaded.
    void update_cache(const std::string& domain, const std::string& content, bool fetch_successful);
    
    void clear_expired();
    size_t size() const;
};