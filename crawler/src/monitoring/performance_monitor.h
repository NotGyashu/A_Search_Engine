#pragma once

#include <atomic>
#include <chrono>
#include <mutex>
#include <iostream>
#include <iomanip>

// Performance monitor for detailed statistics
class PerformanceMonitor {
private:
    std::atomic<long> pages_crawled_{0};
    std::atomic<long> links_discovered_{0};
    std::atomic<long> network_errors_{0};
    std::atomic<long> bytes_downloaded_{0};
    std::atomic<long> pages_filtered_{0};  // Add filtered pages counter
    std::chrono::steady_clock::time_point start_time_;
    mutable std::mutex stats_mutex_;

public:
    PerformanceMonitor() : start_time_(std::chrono::steady_clock::now()) {}
    
    void increment_pages() { pages_crawled_++; }
    void increment_links(int count = 1) { links_discovered_ += count; }
    void increment_errors() { network_errors_++; }
    void increment_filtered() { pages_filtered_++; }  // Add filtered counter
    void add_bytes(long bytes) { bytes_downloaded_ += bytes; }
    
    void print_stats(size_t queue_size, int active_threads) const;
    double get_crawl_rate() const;
    long get_total_pages() const { return pages_crawled_; }
    long get_filtered_pages() const { return pages_filtered_; }  // Add getter
};
