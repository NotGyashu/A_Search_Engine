#include "performance_monitor.h"

void PerformanceMonitor::print_stats(size_t queue_size, int active_threads) const {
    auto now = std::chrono::steady_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - start_time_).count();
    
    if (elapsed > 0) {
        double crawl_rate = static_cast<double>(pages_crawled_) / elapsed;
        double discovery_rate = static_cast<double>(links_discovered_) / elapsed;
        double mb_per_sec = static_cast<double>(bytes_downloaded_) / (1024 * 1024 * elapsed);
             std::cout << "\n================== CRAWLER STATISTICS ==================\n";
    std::cout << "Runtime: " << elapsed << " seconds\n";
    std::cout << "Crawl rate: " << std::fixed << std::setprecision(2) << crawl_rate << " pages/sec\n";
    std::cout << "Discovery rate: " << std::fixed << std::setprecision(2) << discovery_rate << " links/sec\n";
    std::cout << "Download rate: " << std::fixed << std::setprecision(2) << mb_per_sec << " MB/sec\n";
    std::cout << "Total pages: " << pages_crawled_ << "\n";
    std::cout << "Total links: " << links_discovered_ << "\n";
    std::cout << "Network errors: " << network_errors_ << "\n";
    std::cout << "🌐 Filtered (non-English): " << pages_filtered_ << "\n";
    std::cout << "Queue size: " << queue_size << "\n";
    std::cout << "Active threads: " << active_threads << "\n";
    std::cout << "========================================================\n\n";
    }
}

double PerformanceMonitor::get_crawl_rate() const {
    auto now = std::chrono::steady_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - start_time_).count();
    return (elapsed > 0) ? static_cast<double>(pages_crawled_) / elapsed : 0.0;
}
