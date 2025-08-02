#pragma once

#include "crawler_core.h"

/**
 * Multi-threaded crawler worker implementations
 * Handles the actual crawling, HTML processing, and URL management
 */

/**
 * High-performance multi-interface crawler worker
 * Handles HTTP requests, robots.txt compliance, and rate limiting
 */
void multi_crawler_worker(int worker_id, RobotsTxtCache& robots, RateLimiter& limiter,
                         DomainBlacklist& blacklist, ErrorTracker& error_tracker, 
                         ConnectionPool& connection_pool, CrawlerMode mode);

/**
 * 🔧 DEDICATED HTML PROCESSING WORKER
 * Separates HTML parsing from network I/O for better pipeline efficiency
 */
void html_processing_worker(int worker_id, RobotsTxtCache& robots, CrawlerMode mode);
