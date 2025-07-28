#pragma once

#include <unordered_map>
#include <string>
#include <chrono>
#include <mutex>
#include <future>
#include <memory>

// Forward declaration
class HttpClient;

class RobotsTxtCache {
private:
    struct RobotsInfo {
        std::string content;
        std::chrono::steady_clock::time_point timestamp;
        bool is_valid;
        bool is_fetching = false; // Track if we're currently fetching
        std::shared_ptr<std::promise<void>> fetch_promise; // For blocking until fetch completes
    };
    
    mutable std::mutex mutex_;
    std::unordered_map<std::string, RobotsInfo> cache_;
    const std::chrono::hours cache_expiry_{24};
    HttpClient* http_client_; // For fetching robots.txt files
    
    // Internal async fetch method
    void fetch_and_cache_async(const std::string& domain);

public:
    explicit RobotsTxtCache(HttpClient* client);
    bool is_allowed(const std::string& domain, const std::string& path, const std::string& user_agent = "*");
    void add_robots_txt(const std::string& domain, const std::string& content);
    void fetch_and_cache(const std::string& domain);
    void clear_expired();
    size_t size() const;
};
