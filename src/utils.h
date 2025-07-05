#pragma once

#include <string>
#include <vector>
#include <mutex>
#include <unordered_map>
#include <chrono>
#include <functional>
#include <curl/curl.h>

class RobotsTxtCache {
private:
    std::mutex mutex_;
    std::unordered_map<std::string, std::string> rules_;

public:
    bool is_allowed(const std::string& domain);
    void parse(const std::string& domain, const std::string& content);
};

class RateLimiter {
private:
    std::mutex mutex_;
    std::unordered_map<std::string, std::chrono::steady_clock::time_point> last_fetch_;

public:
    void wait_for_domain(const std::string& domain);
};

std::string extract_domain(const std::string& url);
std::vector<std::string> canonicalize_urls(const std::string& base_url, const std::vector<std::string>& urls);
void save_batch_as_json(std::vector<std::pair<std::string, std::string>>& batch, const std::string& output_dir);
void log_error(const std::string& message);
std::string base64_encode(const std::string& in);