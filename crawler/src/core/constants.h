#pragma once

/**
 * 🎯 CRAWLER CONFIGURATION CONSTANTS
 * Centralized configuration for all hardcoded values in the crawler
 * Allows easy tuning and optimization without searching through code
 * All constants are inlined for maximum performance
 */

#include <cstddef>

// =============== CRAWLER MODE ENUM ===============
enum class CrawlerMode {
    REGULAR,  // Deep crawling with disk queue
    FRESH     // RSS/Atom polling without disk queue
};
#include <cstdint>

namespace CrawlerConstants {

// =============== PERFORMANCE OPTIMIZATION ===============
namespace Optimization {
    constexpr bool ENABLE_FUNCTION_INLINING = true;     // Enable aggressive inlining
    constexpr bool ENABLE_BRANCH_PREDICTION = true;     // Use likely/unlikely hints
    constexpr bool MINIMIZE_ALLOCATIONS = true;         // Reuse objects
    constexpr size_t STRING_RESERVE_SIZE = 512;         // Reserve string capacity
    constexpr size_t VECTOR_RESERVE_SIZE = 1000;        // Reserve vector capacity
}

// =============== WORKER CONFIGURATION ===============
namespace Workers {
    // REFACTORED: Default to 8 threads to better utilize modern CPUs
    constexpr int DEFAULT_MAX_THREADS = 4;
    constexpr int MIN_THREADS = 1;
    constexpr int MAX_THREADS = 32;
    constexpr int HTML_WORKER_RATIO = 4;
    constexpr int MIN_HTML_WORKERS = 1;
}

// =============== QUEUE CONFIGURATION ===============
namespace Queue {
    constexpr int DEFAULT_MAX_DEPTH = 4;
    constexpr int DEFAULT_MAX_QUEUE_SIZE = 50000;
    constexpr int MAX_WORK_STEALING_QUEUE_SIZE = 3000; // Max size for work stealing queue
    constexpr int MAX_CONCURRENT_REQUESTS = 45;
    constexpr int MAX_QUEUE_DRAIN_ATTEMPTS = 100;
    constexpr int DISK_LOAD_BATCH_SIZE = 20000;
    constexpr int REFILL_THRESHOLD = 5000;
    constexpr int LOW_QUEUE_THRESHOLD = 100;
    constexpr int CRITICAL_QUEUE_THRESHOLD = 10;
    constexpr int DOMAIN_QUEUE_LIMIT = 100;
    constexpr int SHARDED_DISK_LOAD_SIZE = 1250;
    constexpr int HTML_QUEUE_SIZE = 30000;
}

// =============== LINK EXTRACTION ===============
namespace LinkExtraction {
    constexpr int MIN_LINKS_FOR_EXTRACTION = 10;
    constexpr int MIN_LINKS_EXTRACT = 50;
    constexpr int MAX_LINKS_EXTRACT = 200;
    constexpr float EXTRACTION_PERCENTAGE = 0.4f;
}

// =============== NETWORK CONFIGURATION ===============
namespace Network {
    constexpr int MAX_CONNECTIONS = 100;
    constexpr int MAX_HOST_CONNECTIONS = 8;
    constexpr int TIMEOUT_SECONDS = 10;
    constexpr int CONNECT_TIMEOUT_SECONDS = 4;
    constexpr int MAX_REDIRECTS = 3;
    constexpr int BUFFER_SIZE = 131072;
    constexpr int THROTTLE_DURATION_SECONDS = 120;
    constexpr int MAX_CONCURRENT_REQUESTS_PER_WORKER = 45;
    constexpr int MAX_ATTEMPTS_PER_CYCLE = 100;
}

// =============== MONITORING & STATS ===============
namespace Monitoring {
    constexpr int QUEUE_CHECK_INTERVAL_SECONDS = 5;
    constexpr int DETAILED_STATS_INTERVAL_SECONDS = 15;
    constexpr int WORKER_DIAGNOSTICS_INTERVAL_SECONDS = 10;
    constexpr int CLEANUP_INTERVAL_SECONDS = 60;
    constexpr int SAFETY_TIMEOUT_MINUTES = 30;
    constexpr int PROGRESS_REPORT_FREQUENCY = 500;
    constexpr int EMPTY_QUEUE_LOG_FREQUENCY = 1000;
    constexpr int GRACE_PERIOD_SECONDS = 30;
    constexpr int FRESH_GRACE_PERIOD_SECONDS = 5;
    constexpr int REGULAR_MODE_MAX_RUNTIME_MINUTES = 60;
}

// =============== PERFORMANCE TARGETS ===============
namespace Performance {
    constexpr int TARGET_PAGES_PER_SECOND = 300;
    constexpr int HIGH_PERFORMANCE_THRESHOLD = 200;
    constexpr int GOOD_PERFORMANCE_THRESHOLD = 100;
    constexpr int MODERATE_PERFORMANCE_THRESHOLD = 50;
    constexpr int LOW_PERFORMANCE_THRESHOLD = 10;
    constexpr float VERY_LOW_PERFORMANCE_THRESHOLD = 2.0f;
    constexpr float SHUTDOWN_RATE_THRESHOLD = 5.0f;
}

// =============== CONTENT FILTERING ===============
namespace ContentFilter {
    constexpr int MIN_CONTENT_SIZE = 500;
    constexpr int MAX_CONTENT_SIZE = 10 * 1024 * 1024;
    constexpr int MIN_TEXT_CHARACTERS = 200;
    constexpr int QUALITY_CHECK_SIZE = 5000;
    constexpr int QUALITY_MIN_TEXT_CHARS = 300;
    constexpr int QUALITY_MIN_LINKS = 2;
    constexpr int HTML_STRUCTURE_CHECK_SIZE = 500;
}

// =============== SIMD & PARSING ===============
namespace SIMD {
    constexpr size_t CHUNK_SIZE = 32;
    constexpr size_t MIN_SIMD_SIZE = 32;
    constexpr size_t MAX_HTML_SIZE = 51200;
    constexpr size_t HREF_SEARCH_WINDOW = 50;
    constexpr size_t MIN_HREF_SIZE = 6;
    constexpr size_t HREF_PATTERN_SIZE = 4;
    constexpr size_t SIMD_LOOKAHEAD = 35;
    constexpr size_t MEMORY_POOL_SIZE = 1024 * 1024;
}

// =============== FILE STORAGE ===============
namespace Storage {
    // REFACTORED: Increased batch size for more efficient disk I/O
    constexpr int BATCH_SIZE = 100;
    constexpr int MAX_BATCH_SIZE = 250;
    constexpr size_t RESPONSE_BUFFER_RESERVE = 1024 * 1024;
}

// =============== RATE LIMITING ===============
namespace RateLimit {
    constexpr int MIN_CRAWL_DELAY_MS = 10;
    constexpr int DEFAULT_CRAWL_DELAY_MS = 50;
    constexpr int MIN_ROBOTS_DELAY_MS = 200;
    constexpr int BASE_BACKOFF_MS = 2;
    constexpr int MAX_BACKOFF_MS = 20;
    constexpr int BACKOFF_MULTIPLIER = 2;
    constexpr int MAX_FAILURES_FOR_BACKOFF = 18;
    constexpr int NANOSECONDS_PER_MILLISECOND = 1000000;
}

// =============== ERROR HANDLING ===============
namespace ErrorHandling {
    constexpr int LOW_QUEUE_WARNING_THRESHOLD = 2;
    constexpr int SHUTDOWN_WARNING_THRESHOLD = 3;
    constexpr int MAX_EMERGENCY_INJECTIONS = 5;
}

// =============== PRIORITY CALCULATION ===============
namespace Priority {
    constexpr float MIN_PRIORITY = 0.1f;
    constexpr float MAX_PRIORITY = 2.0f;
    constexpr float DEPTH_PENALTY = 0.15f;
    constexpr float EMERGENCY_SEED_PRIORITY = 0.9f;
    constexpr float DISK_URL_PRIORITY = 0.7f;
}

// =============== SSL & SECURITY ===============
namespace Security {
    constexpr int SSL_VERIFY_PEER = 1;
    constexpr int SSL_VERIFY_HOST = 2;
    constexpr int FOLLOW_REDIRECTS = 1;
    constexpr int THREAD_SAFE_MODE = 1;
    constexpr int TCP_NODELAY = 1;
    constexpr int TCP_KEEPALIVE = 1;
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
    constexpr const char* RAW_DATA_PATH = "../../RawHTMLdata";  // Legacy local path (fallback)
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

// =============== FRESH MODE CONFIGURATION ===============
namespace FreshMode {
    constexpr int RSS_POLL_INTERVAL_SECONDS = 5;
    constexpr int HTML_WORKERS = 1;
    constexpr int NETWORK_WORKERS = 1;
    constexpr int MAX_QUEUE_SIZE = 3000;
    constexpr int MAX_CRAWL_DEPTH = 2;
    constexpr int STARTUP_GRACE_SECONDS = 5;
    constexpr int MONITORING_INTERVAL_SECONDS = 10;
    constexpr bool USE_DISK_QUEUE = false;
    constexpr bool LOAD_EXISTING_URLS = false;
    constexpr int FRESH_MODE_MAX_WORK_STEALING_QUEUE_SIZE = 2000; // Increased for RSS bursts
}


} // namespace CrawlerConstants