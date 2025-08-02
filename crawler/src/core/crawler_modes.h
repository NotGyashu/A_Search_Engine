#pragma once

#include "crawler_core.h"
#include <memory>

// Forward declarations
class RobotsTxtCache;
class RateLimiter;
class DomainBlacklist;
class ErrorTracker;
class ConnectionPool;
class HttpClient;

/**
 * Mode-specific crawler logic declarations
 */
void run_regular_mode(int max_threads, int max_depth, int max_queue_size, int max_runtime_minutes);
void run_fresh_mode(int max_runtime_minutes);

// Helper functions for mode initialization
void initialize_regular_mode_components(int max_depth, int max_queue_size);
void initialize_fresh_mode_components();
void setup_rss_poller(CrawlerMode mode, HttpClient* http_client, int network_workers);
void setup_sitemap_parser(HttpClient* http_client);
void start_worker_threads(int network_workers, int html_workers, CrawlerMode mode,
                         RobotsTxtCache& robots, RateLimiter& limiter,
                         DomainBlacklist& blacklist, ErrorTracker& error_tracker,
                         ConnectionPool& connection_pool,
                         std::vector<std::thread>& network_threads,
                         std::vector<std::thread>& html_threads);
