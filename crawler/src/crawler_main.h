#pragma once

/**
 * HYBRID SPEED CRAWLER - Header File
 * Production-Ready with Ultimate Performance
 * Target: 300+ pages/sec with full compliance and robustness
 */

#include "utils.h"
#include <curl/curl.h>
#include <string>
#include <vector>
#include <memory>
#include <atomic>

// Forward declarations for classes from utils.h and other dependencies
class RobotsTxtCache;
class RateLimiter;
class DomainBlacklist;
class ErrorTracker;

// Global variables (declared extern)
extern std::atomic<bool> stop_flag;
extern PerformanceMonitor global_monitor;
extern std::unique_ptr<UrlFrontier> url_frontier;
extern std::unique_ptr<CrawlLogger> crawl_logger;
extern std::unique_ptr<FileStorageManager> file_storage;

// CURL callback function
size_t hybrid_write_callback(void* contents, size_t size, size_t nmemb, void* userp);

// Worker thread functions
void multi_crawler_worker(int worker_id, RobotsTxtCache& robots, RateLimiter& limiter,
                         DomainBlacklist& blacklist, ErrorTracker& error_tracker);

void html_processing_worker(int worker_id, RobotsTxtCache& robots);

void enhanced_monitoring_thread();

// Signal handling
void signal_handler(int signal);

// Main function
int main(int argc, char* argv[]);
