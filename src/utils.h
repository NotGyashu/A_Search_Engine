#pragma once
#include <string>
#include <unordered_map>
#include <mutex>
#include <chrono>
#include <vector>

// Function declarations
std::string extract_domain(const std::string& url);
std::vector<std::string> canonicalize_urls(const std::string& base_url, const std::vector<std::string>& urls);
void save_as_json(const std::string& url, const std::string& html, const std::string& output_dir);
void log_error(const std::string& message);

class RobotsTxtCache {
public:
    bool is_allowed(const std::string& url, const std::string& user_agent);
    void parse(const std::string& domain, const std::string& content);
    
private:
    std::unordered_map<std::string, std::string> rules_;
    std::mutex mutex_;
};

class RateLimiter {
public:
    void wait_for_domain(const std::string& domain);
private:
    std::unordered_map<std::string, std::chrono::steady_clock::time_point> last_fetch_;
    std::mutex mutex_;
};