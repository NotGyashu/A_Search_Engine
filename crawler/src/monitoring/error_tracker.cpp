#include "error_tracker.h"
#include <iostream>
#include <iomanip>

void ErrorTracker::record_error(const std::string& domain, CURLcode error) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto& stats = domain_errors_[domain];
    stats.error_counts[error]++;
    stats.last_error = std::chrono::steady_clock::now();
    
    if (error == CURLE_OPERATION_TIMEDOUT) {
        stats.consecutive_timeouts++;
    } else {
        stats.consecutive_timeouts = 0;
    }
}

void ErrorTracker::record_success(const std::string& domain) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = domain_errors_.find(domain);
    if (it != domain_errors_.end()) {
        it->second.consecutive_timeouts = 0;
    }
}

bool ErrorTracker::should_blacklist_domain(const std::string& domain) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = domain_errors_.find(domain);
    if (it == domain_errors_.end()) {
        return false;
    }
    
    const auto& stats = it->second;
    
    // Blacklist if too many consecutive timeouts
    if (stats.consecutive_timeouts >= 5) {
        return true;
    }
    
    // Blacklist if too many total errors
    int total_errors = 0;
    for (const auto& error_pair : stats.error_counts) {
        total_errors += error_pair.second;
    }
    
    return total_errors >= 10;
}

void ErrorTracker::print_stats() const {
    std::lock_guard<std::mutex> lock(mutex_);
    
    std::cout << "\n================== ERROR STATISTICS ==================\n";
    for (const auto& domain_pair : domain_errors_) {
        const std::string& domain = domain_pair.first;
        const auto& stats = domain_pair.second;
        
        std::cout << "Domain: " << domain << "\n";
        std::cout << "  Consecutive timeouts: " << stats.consecutive_timeouts << "\n";
        
        for (const auto& error_pair : stats.error_counts) {
            std::cout << "  Error " << error_pair.first << ": " << error_pair.second << " times\n";
        }
    }
    std::cout << "========================================================\n\n";
}

void ErrorTracker::reset_stats() {
    std::lock_guard<std::mutex> lock(mutex_);
    domain_errors_.clear();
}
