#pragma once

/**
 * 🎯 CRAWLER CONFIGURATION CONSTANTS
 * Centralized configuration for all hardcoded values in the crawler
 * Allows easy tuning and optimization without searching through code
 */

#include <cstddef>
#include <cstdint>

namespace CrawlerConstants {

// =============== WORKER CONFIGURATION ===============
namespace Workers {
    constexpr int DEFAULT_MAX_THREADS = 4;              // Default network workers
    constexpr int MIN_THREADS = 1;                      // Minimum worker threads
    constexpr int MAX_THREADS = 32;                     // Maximum worker threads
    constexpr int HTML_WORKER_RATIO = 3;                // Network workers / HTML workers
    constexpr int MIN_HTML_WORKERS = 1;                 // Minimum HTML processors
}

// =============== QUEUE CONFIGURATION ===============
namespace Queue {
    constexpr int DEFAULT_MAX_DEPTH = 4;                // Default crawl depth
    constexpr int DEFAULT_MAX_QUEUE_SIZE = 50000;      // Default main queue size
    constexpr int DEFAULT_WORK_STEALING_QUEUE_SIZE = 50000;      // Default work stealing queue size
    constexpr int MAX_CONCURRENT_REQUESTS = 45;         // Max concurrent requests per worker
    constexpr int MAX_QUEUE_DRAIN_ATTEMPTS = 100;       // Max attempts to drain queue
    constexpr int DISK_LOAD_BATCH_SIZE = 1000;           // URLs loaded from disk per batch
    constexpr int REFILL_THRESHOLD = 1000;               // Refill main queue when below this
    constexpr int LOW_QUEUE_THRESHOLD = 100;            // Trigger emergency seeds
    constexpr int CRITICAL_QUEUE_THRESHOLD = 10;        // Auto-shutdown threshold
    constexpr int DOMAIN_QUEUE_LIMIT = 100;             // Per-domain queue size limit
    constexpr int SHARDED_DISK_LOAD_SIZE = 1000;          // Sharded disk load batch size
}

// =============== LINK EXTRACTION ===============
namespace LinkExtraction {
    constexpr int MIN_LINKS_FOR_EXTRACTION = 10;        // Threshold for adaptive extraction
    constexpr int MIN_LINKS_EXTRACT = 50;               // Minimum links to extract
    constexpr int MAX_LINKS_EXTRACT = 200;              // Maximum links to extract
    constexpr float EXTRACTION_PERCENTAGE = 0.4f;       // 40% of available links
}

// =============== NETWORK CONFIGURATION ===============
namespace Network {
    constexpr int MAX_CONNECTIONS = 100;                // CURL multi max connections
    constexpr int MAX_HOST_CONNECTIONS = 8;             // Max connections per host
    constexpr int TIMEOUT_SECONDS = 10;                 // Request timeout
    constexpr int CONNECT_TIMEOUT_SECONDS = 4;          // Connection timeout
    constexpr int MAX_REDIRECTS = 3;                    // Maximum redirects to follow
    constexpr int BUFFER_SIZE = 131072;                 // 128KB network buffer
    constexpr int THROTTLE_DURATION_SECONDS = 120;      // Rate limit throttle duration
}

// =============== MONITORING & STATS ===============
namespace Monitoring {
    constexpr int QUEUE_CHECK_INTERVAL_SECONDS = 5;     // Queue monitoring frequency
    constexpr int DETAILED_STATS_INTERVAL_SECONDS = 15; // Detailed stats frequency
    constexpr int WORKER_DIAGNOSTICS_INTERVAL_SECONDS = 10; // Worker diagnostic frequency
    constexpr int CLEANUP_INTERVAL_SECONDS = 60;        // Disk cleanup frequency
    constexpr int SAFETY_TIMEOUT_MINUTES = 30;          // Safety shutdown timeout
    constexpr int PROGRESS_REPORT_FREQUENCY = 500;      // Progress report every N pages
    constexpr int EMPTY_QUEUE_LOG_FREQUENCY = 1000;     // Log empty queue every N attempts
}

// =============== PERFORMANCE TARGETS ===============
namespace Performance {
    constexpr int TARGET_PAGES_PER_SECOND = 300;        // Target crawl speed
    constexpr int HIGH_PERFORMANCE_THRESHOLD = 200;     // High performance marker
    constexpr int GOOD_PERFORMANCE_THRESHOLD = 100;     // Good performance marker
    constexpr int MODERATE_PERFORMANCE_THRESHOLD = 50;  // Moderate performance marker
    constexpr int LOW_PERFORMANCE_THRESHOLD = 10;       // Low performance marker
    constexpr float VERY_LOW_PERFORMANCE_THRESHOLD = 2.0f; // Very low performance
    constexpr float SHUTDOWN_RATE_THRESHOLD = 5.0f;     // Auto-shutdown rate threshold
}

// =============== CONTENT FILTERING ===============
namespace ContentFilter {
    constexpr int MIN_CONTENT_SIZE = 500;               // Minimum page size (bytes)
    constexpr int MAX_CONTENT_SIZE = 10 * 1024 * 1024;  // Maximum page size (10MB)
    constexpr int MIN_TEXT_CHARACTERS = 200;            // Minimum text content
    constexpr int QUALITY_CHECK_SIZE = 5000;            // Size to check for quality (5KB)
    constexpr int QUALITY_MIN_TEXT_CHARS = 300;         // Min text chars for quality
    constexpr int QUALITY_MIN_LINKS = 2;                // Min links for quality
    constexpr int HTML_STRUCTURE_CHECK_SIZE = 500;      // Size to check for HTML structure
}

// =============== SIMD & PARSING ===============
namespace SIMD {
    constexpr size_t CHUNK_SIZE = 32;                   // AVX2 256-bit chunks
    constexpr size_t MIN_SIMD_SIZE = 32;                // Minimum size for SIMD processing
    constexpr size_t MAX_HTML_SIZE = 51200;             // 50KB default max HTML size
    constexpr size_t HREF_SEARCH_WINDOW = 50;           // Window size for href search
    constexpr size_t MIN_HREF_SIZE = 6;                 // Minimum size for "<a href"
    constexpr size_t HREF_PATTERN_SIZE = 4;             // Size of "href" pattern
    constexpr size_t SIMD_LOOKAHEAD = 35;               // SIMD lookahead buffer
    constexpr size_t MEMORY_POOL_SIZE = 1024 * 1024;    // 1MB memory pool
}

// =============== FILE STORAGE ===============
namespace Storage {
    constexpr int BATCH_SIZE = 25;                      // File storage batch size
    constexpr int MAX_BATCH_SIZE = 100;                 // Maximum batch size
    constexpr size_t RESPONSE_BUFFER_RESERVE = 1024 * 1024; // 1MB response buffer
}

// =============== RATE LIMITING ===============
namespace RateLimit {
    constexpr int MIN_CRAWL_DELAY_MS = 10;              // Very fast crawling default
    constexpr int DEFAULT_CRAWL_DELAY_MS = 50;         // Default crawl delay
    constexpr int MIN_ROBOTS_DELAY_MS = 200;            // Minimum robots.txt delay
    constexpr int BASE_BACKOFF_MS = 2;                  // Base backoff delay
    constexpr int MAX_BACKOFF_MS = 20;                  // Maximum backoff delay
    constexpr int BACKOFF_MULTIPLIER = 2;               // Backoff multiplier
    constexpr int MAX_FAILURES_FOR_BACKOFF = 18;        // Max failures for backoff calc
    constexpr int NANOSECONDS_PER_MILLISECOND = 1000000; // NS to MS conversion
}

// =============== ERROR HANDLING ===============
namespace ErrorHandling {
    constexpr int LOW_QUEUE_WARNING_THRESHOLD = 2;      // Warnings before emergency seeds
    constexpr int SHUTDOWN_WARNING_THRESHOLD = 3;       // Warnings before shutdown
    constexpr int MAX_EMERGENCY_INJECTIONS = 5;         // Max emergency seed injections
}

// =============== PRIORITY CALCULATION ===============
namespace Priority {
    constexpr float MIN_PRIORITY = 0.1f;                // Minimum URL priority
    constexpr float MAX_PRIORITY = 2.0f;                // Maximum URL priority cap
    constexpr float DEPTH_PENALTY = 0.15f;              // Priority reduction per depth level
    constexpr float EMERGENCY_SEED_PRIORITY = 0.9f;     // Priority for emergency seeds
    constexpr float DISK_URL_PRIORITY = 0.7f;           // Priority for disk-loaded URLs
}

// =============== SSL & SECURITY ===============
namespace Security {
    constexpr int SSL_VERIFY_PEER = 1;                  // Verify SSL peer
    constexpr int SSL_VERIFY_HOST = 2;                  // Verify SSL host
    constexpr int FOLLOW_REDIRECTS = 1;                 // Follow HTTP redirects
    constexpr int THREAD_SAFE_MODE = 1;                 // Thread-safe CURL
    constexpr int TCP_NODELAY = 1;                      // Disable Nagle algorithm
    constexpr int TCP_KEEPALIVE = 1;                    // Keep TCP connections alive
}

// =============== USER AGENT & HEADERS ===============
namespace Headers {
    constexpr const char* USER_AGENT = "AISearchBot/1.0 (+https://example.com/bot)";
    constexpr const char* ACCEPT_ENCODING = "gzip, deflate";
}

// =============== PATH CONSTANTS ===============
namespace Paths {
    constexpr const char* DB_PATH = "../data/processed/hybrid_crawl_metadata.db";
    constexpr const char* LOG_PATH = "../data/processed/hybrid_crawl_log.csv";
    constexpr const char* RAW_DATA_PATH = "../../RawHTMLdata";
    constexpr const char* BLACKLIST_PATH = "../data/blacklist.txt";
    constexpr const char* SHARDED_DISK_PATH = "../data/sharded";
    constexpr const char* CONFIG_PATH = "../config";
    constexpr const char* CONDITIONAL_GET_CACHE_PATH = "../cache/rocksdb_conditional_get_cache";
    constexpr const char* ROBOTS_TXT_CACHE_PATH = "../cache/rocksdb_robots_txt_cache";
    constexpr const char* ROCKSDB_RATE_LIMITER_PATH = "../cache/rocksdb_rate_limiter_cache";
    constexpr const char* ROCKSDB_METADATA_PATH = "../cache/rocksdb_metadata_store";
}

// =============== HTTP STATUS CODES ===============
namespace HttpStatus {
    constexpr int OK = 200;
    constexpr int TOO_MANY_REQUESTS = 429;
    constexpr int SERVICE_UNAVAILABLE = 503;
    constexpr int BAD_REQUEST = 400;
}

} // namespace CrawlerConstants
