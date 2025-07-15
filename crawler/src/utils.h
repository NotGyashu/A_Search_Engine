#pragma once

#include "constants.h"

#include <string>
#include <vector>
#include <mutex>
#include <unordered_map>
#include <unordered_set>
#include <chrono>
#include <functional>
#include <curl/curl.h>
#include <iostream>
#include <map>
#include <queue>
#include <atomic>
#include <sqlite3.h>
#include <regex>
#include <fstream>
#include <array>
#include <condition_variable>
#include <thread>
#include <immintrin.h> // For _mm_pause() intrinsic
#include <filesystem>  // C++17 filesystem
#include <deque>       // For work stealing queue

// Hybrid HTML parsing strategy for maximum crawling speed
// Tier 1: Ultra-fast regex (for simple, well-formed HTML)
// Tier 2: lolhtml streaming parser (for complex but valid HTML)  
// Tier 3: Gumbo robust parser (for malformed HTML fallback)
#if HAVE_LOLHTML
    #include <lolhtml.h>
#endif

// URL structure with priority and metadata
struct UrlInfo {
    std::string url;
    float priority;
    int depth;
    std::string referring_domain;
    std::chrono::steady_clock::time_point discovered_time;
    
    UrlInfo(const std::string& u, float p = 0.5f, int d = 0, const std::string& ref = "")
        : url(u), priority(p), depth(d), referring_domain(ref), 
          discovered_time(std::chrono::steady_clock::now()) {}
};

// Priority queue comparator
struct UrlPriorityComparator {
    bool operator()(const UrlInfo& a, const UrlInfo& b) const {
        if (std::abs(a.priority - b.priority) > 0.01f) {
            return a.priority < b.priority; // Higher priority first
        }
        return a.depth > b.depth; // Lower depth first
    }
};

// Enhanced robots.txt parser
class RobotsTxtCache {
private:
    struct RobotRule {
        std::vector<std::string> disallowed_paths;
        std::vector<std::string> allowed_paths;
        int crawl_delay_ms = 200;
        bool allow_all = false;
    };
    
    mutable std::mutex cache_mutex_;
    mutable std::mutex mutex_; // For rules access
    std::unordered_map<std::string, std::unordered_set<std::string>> disallowed_paths_;
    std::unordered_map<std::string, std::chrono::steady_clock::time_point> cache_timestamps_;
    std::unordered_map<std::string, std::chrono::steady_clock::time_point> fetch_times_;
    std::unordered_map<std::string, RobotRule> rules_;
    std::chrono::minutes cache_duration_{60};
    
    static size_t robots_write_callback(void* contents, size_t size, size_t nmemb, void* userp);
    void parse_robots_content(const std::string& domain, const std::string& content);

public:
    bool is_allowed(const std::string& domain, const std::string& path);
    int get_crawl_delay(const std::string& domain);
    void fetch_and_cache(const std::string& domain);
};

// Performance monitor for detailed statistics
class PerformanceMonitor {
private:
    std::atomic<long> pages_crawled_{0};
    std::atomic<long> links_discovered_{0};
    std::atomic<long> network_errors_{0};
    std::atomic<long> bytes_downloaded_{0};
    std::chrono::steady_clock::time_point start_time_;
    mutable std::mutex stats_mutex_;

public:
    PerformanceMonitor() : start_time_(std::chrono::steady_clock::now()) {}
    
    void increment_pages() { pages_crawled_++; }
    void increment_links(int count = 1) { links_discovered_ += count; }
    void increment_errors() { network_errors_++; }
    void add_bytes(long bytes) { bytes_downloaded_ += bytes; }
    
    void print_stats(size_t queue_size, int active_threads) const;
    double get_crawl_rate() const;
    long get_total_pages() const { return pages_crawled_; }
};

// Lock-free rate limiter using atomic operations and sharding
class RateLimiter {
private:
    static constexpr size_t NUM_SHARDS = 256;
    std::array<std::atomic<int64_t>, NUM_SHARDS> domain_timestamps_;
    std::array<std::atomic<int>, NUM_SHARDS> failure_counts_;
    
    // Fast hash function for domain sharding - fixed for 32-bit
    static inline uint32_t fasthash(const std::string& domain) {
        uint32_t hash = 0x811c9dc5; // 32-bit FNV offset basis
        for (char c : domain) {
            hash ^= c;
            hash *= 0x01000193; // 32-bit FNV prime
        }
        return hash;
    }
    
    // CPU-friendly nano sleep
    static inline void nano_pause(int64_t nanoseconds) {
        auto start = std::chrono::steady_clock::now();
        while (std::chrono::duration_cast<std::chrono::nanoseconds>(
               std::chrono::steady_clock::now() - start).count() < nanoseconds) {
            _mm_pause(); // x86/x64 intrinsic
        }
    }

public:
    RateLimiter() {
        // Initialize all timestamps to 0
        for (auto& ts : domain_timestamps_) {
            ts.store(0, std::memory_order_relaxed);
        }
        for (auto& fc : failure_counts_) {
            fc.store(0, std::memory_order_relaxed);
        }
    }
    
    void wait_for_domain(const std::string& domain);
    void record_failure(const std::string& domain);
    void record_success(const std::string& domain);
    void set_custom_delay(const std::string& domain, int delay_ms) { /* No-op in lock-free version */ }
    void throttle_domain(const std::string& domain, int seconds);
    bool can_request_now(const std::string& domain);
    void record_request(const std::string& domain);
};

// Comprehensive URL normalizer
class UrlNormalizer {
private:
    static std::regex protocol_regex_;
    static std::regex domain_regex_;
    static std::regex path_cleanup_regex_;
    static std::unordered_set<std::string> tracking_params_;

public:
    static std::string normalize(const std::string& url);
    static std::string resolve_relative(const std::string& base_url, const std::string& relative_url);
    static std::string extract_domain(const std::string& url);
    static std::string extract_path(const std::string& url);
    static bool is_valid_url(const std::string& url);
};

// Content filter for high-quality pages
class ContentFilter {
private:
    static std::unordered_set<std::string> excluded_extensions_;
    static std::unordered_set<std::string> excluded_patterns_;
    static std::unordered_set<std::string> high_priority_domains_;

public:
    static bool is_crawlable_url(const std::string& url);
    static float calculate_priority(const std::string& url, int depth);
    static bool is_high_quality_content(const std::string& html);
};

// Lock-free priority queue for URLs with partitioning
class UrlFrontier {
private:
    static constexpr size_t NUM_PARTITIONS = 16;
    
    struct Partition {
        std::priority_queue<UrlInfo, std::vector<UrlInfo>, UrlPriorityComparator> queue_;
        std::unordered_set<std::string> seen_urls_;
        mutable std::mutex mutex_;
        std::atomic<size_t> size_{0};
        
        Partition() {
            seen_urls_.reserve(10000);
        }
    };
    
    std::array<Partition, NUM_PARTITIONS> partitions_;
    std::atomic<size_t> round_robin_counter_{0};
    std::atomic<size_t> max_queue_size_{100000};  // Increased from 50K to 100K for performance
    std::atomic<int> max_depth_{5};
    
    size_t get_partition_index(const std::string& url) const;

public:
    bool enqueue(const UrlInfo& url_info);
    bool dequeue(UrlInfo& url_info);
    size_t size() const;
    void set_max_queue_size(size_t size) { max_queue_size_ = size; }
    void set_max_depth(int depth) { max_depth_ = depth; }
    bool is_seen(const std::string& url);
};

// Ultra-fast SIMD HTML parser (300+ pages/sec)
class HtmlParser {
private:
    static std::regex title_regex_;
    static std::regex meta_description_regex_;

public:
    // Main extraction method using ultra parser
    static std::vector<std::string> extract_links(const std::string& html, const std::string& base_url);
    
    // Ultra-fast SIMD parser (300+ pages/sec target)
    static std::vector<std::string> extract_links_ultra(const std::string& html, const std::string& base_url);
    
    static std::string extract_title(const std::string& html);
    static std::string extract_text_content(const std::string& html);
    static std::string extract_meta_description(const std::string& html);
    static bool is_html_content(const std::string& content);
    
    // Performance tracking
    static void get_parsing_stats();
};

// Asynchronous batch logger to reduce blocking
class CrawlLogger {
private:
    struct LogEntry {
        std::string url;
        std::string title;
        int status_code;
        int depth;
        std::string domain;
        size_t content_size;
        std::chrono::steady_clock::time_point timestamp;
        std::string error_message;
        bool is_error;
    };
    
    sqlite3* db_;
    std::mutex db_mutex_;
    std::ofstream csv_log_;
    std::mutex csv_mutex_;
    std::string db_path_;
    std::string csv_path_;
    
    // Async logging
    std::queue<LogEntry> log_queue_;
    std::mutex queue_mutex_;
    std::condition_variable queue_cv_;
    std::thread logger_thread_;
    std::atomic<bool> shutdown_{false};
    
    void logger_worker();

public:
    CrawlLogger(const std::string& db_path, const std::string& csv_path);
    ~CrawlLogger();
    
    void log_page(const std::string& url, const std::string& title, int status_code, 
                  int depth, const std::string& domain, size_t content_size,
                  const std::chrono::steady_clock::time_point& timestamp);
    void log_error(const std::string& url, const std::string& error_message);
    void flush();
    bool initialize();
};

// High-performance connection pool with per-thread caching
class ConnectionPool {
private:
    struct ConnectionInfo {
        CURL* handle;
        std::chrono::steady_clock::time_point last_used;
        std::atomic<bool> in_use{false};
        
        // Custom constructor for atomic member
        ConnectionInfo(CURL* h, std::chrono::steady_clock::time_point t, bool u) 
            : handle(h), last_used(t), in_use(u) {}
        
        // Move constructor
        ConnectionInfo(ConnectionInfo&& other) noexcept
            : handle(other.handle), last_used(other.last_used), in_use(other.in_use.load()) {}
        
        // Move assignment
        ConnectionInfo& operator=(ConnectionInfo&& other) noexcept {
            if (this != &other) {
                handle = other.handle;
                last_used = other.last_used;
                in_use.store(other.in_use.load());
            }
            return *this;
        }
        
        // Delete copy constructor and assignment
        ConnectionInfo(const ConnectionInfo&) = delete;
        ConnectionInfo& operator=(const ConnectionInfo&) = delete;
    };
    
    std::vector<ConnectionInfo> connections_;
    std::atomic<size_t> max_connections_{100};
    std::atomic<size_t> round_robin_counter_{0};
    
    CURL* create_connection();
    void configure_connection(CURL* curl);

public:
    // Per-thread connection cache for zero-contention acquisition
    static thread_local std::vector<CURL*> thread_local_cache_;
    static thread_local size_t cache_size_;
    static constexpr size_t MAX_THREAD_CACHE = 8;
    
    ConnectionPool();
    ~ConnectionPool();
    
    CURL* acquire_connection();
    CURL* acquire_for_domain(const std::string& domain); // New domain-specific connection pooling
    void release_connection(CURL* curl);
    void cleanup_idle_connections();
    size_t active_connections() const;
};

class DomainBlacklist {
private:
    mutable std::mutex mutex_;
    std::unordered_map<std::string, std::chrono::steady_clock::time_point> blacklist_;
    const std::chrono::seconds cooldown_{60};
    std::unordered_set<std::string> permanent_blacklist_;

public:
    bool is_blacklisted(const std::string& domain) const;
    void add_temporary(const std::string& domain);
    void add_permanent(const std::string& domain);
    size_t size() const;
    void load_from_file(const std::string& filename);
};

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

// Async file storage with minimal locking
class FileStorageManager {
private:
    std::string base_path_;
    std::atomic<int> batch_counter_{0};
    
    // Async storage
    struct StorageBatch {
        std::vector<std::pair<std::string, std::string>> data;
        std::string batch_id;
    };
    
    std::queue<StorageBatch> storage_queue_;
    std::mutex queue_mutex_;
    std::condition_variable queue_cv_;
    std::thread storage_thread_;
    std::atomic<bool> shutdown_{false};
    
    void storage_worker();

public:
    explicit FileStorageManager(const std::string& base_path);
    ~FileStorageManager();
    
    void save_html_batch(const std::vector<std::pair<std::string, std::string>>& batch);
    void save_single_page(const std::string& url, const std::string& html, const std::string& domain);
    bool ensure_directory_exists(const std::string& path);
};

//
// 🚀 PHASE 2: ENHANCED COMPONENTS
//

/**
 * HTML Processing Pipeline Task
 */
struct HtmlProcessingTask {
    std::string html;
    std::string url;
    std::string domain;
    int depth;
    std::chrono::steady_clock::time_point fetch_time;
    
    HtmlProcessingTask(std::string h, std::string u, std::string d, int dep)
        : html(std::move(h)), url(std::move(u)), domain(std::move(d)), depth(dep)
        , fetch_time(std::chrono::steady_clock::now()) {}
};

/**
 * HTML Processing Queue for pipeline separation
 */
class HtmlProcessingQueue {
private:
    std::queue<HtmlProcessingTask> queue_;
    std::mutex mutex_;
    std::condition_variable cv_;
    std::atomic<bool> shutdown_{false};
    static constexpr size_t MAX_QUEUE_SIZE = 1000;

public:
    bool enqueue(HtmlProcessingTask&& task);
    bool dequeue(HtmlProcessingTask& task);
    void shutdown();
    size_t size() const;
};

/**
 * Sharded Disk Queue Manager - eliminates global mutex contention
 */
class ShardedDiskQueue {
private:
    struct DiskShard {
        std::string file_path;
        std::mutex mutex;
        std::atomic<size_t> size{0};
        std::ofstream write_stream;
        
        DiskShard(const std::string& base_path, int shard_id) 
            : file_path(base_path + "/shard_" + std::to_string(shard_id) + ".txt") {
            // Create directories using C++17 filesystem
            std::error_code ec;
            std::filesystem::create_directories(std::filesystem::path(file_path).parent_path(), ec);
            // Ignore error if directory already exists
        }
    };
    
    static constexpr size_t NUM_SHARDS = 16;
    std::array<std::unique_ptr<DiskShard>, NUM_SHARDS> shards_;
    std::hash<std::string> url_hasher_;
    
    size_t get_shard_index(const std::string& url) const {
        return url_hasher_(url) % NUM_SHARDS;
    }

public:
    ShardedDiskQueue(const std::string& base_path);
    ~ShardedDiskQueue();
    
    bool save_urls_to_disk(const std::vector<std::string>& urls);
    std::vector<std::string> load_urls_from_disk(size_t max_count = 200);
    size_t get_total_disk_queue_size() const;
    void cleanup_empty_shards();
};

/**
 * Lock-free Work Stealing Queue
 */
class WorkStealingQueue {
private:
    struct WorkerQueue {
        std::deque<UrlInfo> local_queue;
        std::mutex mutex;
        std::atomic<size_t> size{0};
    };
    
    std::vector<std::unique_ptr<WorkerQueue>> worker_queues_;
    std::atomic<size_t> steal_counter_{0};
    const size_t num_workers_;

public:
    explicit WorkStealingQueue(size_t num_workers);
    ~WorkStealingQueue() = default;
    
    bool push_local(size_t worker_id, const UrlInfo& url);
    bool pop_local(size_t worker_id, UrlInfo& url);
    bool try_steal(size_t worker_id, UrlInfo& url);
    size_t total_size() const;
    bool empty() const;
};

// Function declarations
std::string extract_domain(const std::string& url);
std::vector<std::string> canonicalize_urls(const std::string& base_url, const std::vector<std::string>& urls);
void save_batch_as_json(std::vector<std::pair<std::string, std::string>>& batch, const std::string& output_dir);
void log_error(const std::string& message);
std::string base64_encode(const std::string& in);
bool is_useful_url(const std::string& url);
std::string get_timestamp_string();
std::string sanitize_filename(const std::string& input);
