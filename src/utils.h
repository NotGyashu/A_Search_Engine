#pragma once

#include <string>
#include <vector>
#include <mutex>
#include <unordered_map>
#include <chrono>
#include <functional>
#include <curl/curl.h>
#include <iostream>
#include <map>

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

class DomainBlacklist {
private:
    mutable std::mutex mutex_;
    std::unordered_map<std::string, std::chrono::steady_clock::time_point> blacklist_;
    const std::chrono::minutes cooldown{30};

public:
    bool is_blacklisted(const std::string& domain) const {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = blacklist_.find(domain);
        if (it != blacklist_.end()) {
            return (std::chrono::steady_clock::now() - it->second) < cooldown;
        }
        return false;
    }

    void add(const std::string& domain) {
        std::lock_guard<std::mutex> lock(mutex_);
        blacklist_[domain] = std::chrono::steady_clock::now();
    }

    size_t size() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return blacklist_.size();
    }
};

class ErrorTracker {
public:
    void record_error(const std::string& domain, CURLcode error) {
        std::lock_guard<std::mutex> lock(mutex_);
        error_counts_[domain][error]++;
    }

    void print_stats() const {
        std::lock_guard<std::mutex> lock(mutex_);
        for (const auto& [domain, errors] : error_counts_) {
            std::cerr << "Domain: " << domain << "\n";
            for (const auto& [err, count] : errors) {
                std::cerr << "  " << curl_easy_strerror(err) << ": " << count << "\n";
            }
        }
    }

private:
    std::unordered_map<std::string, std::map<CURLcode, int>> error_counts_;
    mutable std::mutex mutex_;
};

std::string extract_domain(const std::string& url);
std::vector<std::string> canonicalize_urls(const std::string& base_url, const std::vector<std::string>& urls);
void save_batch_as_json(std::vector<std::pair<std::string, std::string>>& batch, const std::string& output_dir);
void log_error(const std::string& message);
std::string base64_encode(const std::string& in);
bool is_useful_url(const std::string& url);  // Added declaration