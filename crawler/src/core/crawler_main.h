#pragma once

/**
 * HYBRID SPEED CRAWLER - Header File
 */

#include "robots_txt_cache.h"
#include "rate_limiter.h" 
#include "domain_blacklist.h"
#include "error_tracker.h"
#include "performance_monitor.h"
#include "crawl_logger.h"
#include "connection_pool.h" // Include ConnectionPool header
#include <curl/curl.h>
#include <string>
#include <vector>
#include <memory>
#include <atomic>

// Forward declarations
class HtmlProcessingQueue;
class WorkStealingQueue;

// Global variables
extern std::atomic<bool> stop_flag;
extern PerformanceMonitor global_monitor;
extern std::unique_ptr<CrawlLogger> crawl_logger;
extern std::unique_ptr<HtmlProcessingQueue> html_processing_queue;
extern std::unique_ptr<WorkStealingQueue> work_stealing_queue;

// CURL callback function
size_t hybrid_write_callback(void* contents, size_t size, size_t nmemb, void* userp);

// Worker thread functions
// FIX: The function signature is updated to accept the ConnectionPool reference.
void multi_crawler_worker(int worker_id, RobotsTxtCache& robots, RateLimiter& limiter,
                         DomainBlacklist& blacklist, ErrorTracker& error_tracker,
                         ConnectionPool& connection_pool);

void html_processing_worker(int worker_id, RobotsTxtCache& robots);
void enhanced_monitoring_thread();

// Signal handling
void signal_handler(int signal);

// Main function
int main(int argc, char* argv[]);