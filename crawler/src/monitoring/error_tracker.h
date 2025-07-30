#pragma once

#include <unordered_map>
#include <map>
#include <chrono>
#include <mutex>
#include <string>
#include <curl/curl.h>

class ErrorTracker {
private:
    struct ErrorStats {
        std::map<CURLcode, int> error_counts;
        std::chrono::steady_clock::time_point last_error;
        int consecutive_timeouts = 0;
    };
    
    std::unordered_map<std::string, ErrorStats> domain_errors_;
    mutable std::mutex mutex_;

public:
    void record_error(const std::string& domain, CURLcode error);
    void record_success(const std::string& domain);
    bool should_blacklist_domain(const std::string& domain);
    void print_stats() const;
    void reset_stats();
};
