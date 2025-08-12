#pragma once

#include "ultra_parser.h"
#include "language_detector.h"
#include "constants.h"
#include "crawl_metadata.h"
#include "content_hash.h"
#include "smart_frontier.h"
#include "enriched_storage.h"
#include "rss_poller.h"
#include "sitemap_parser.h"
#include "conditional_get.h"
#include "config_loader.h"
#include "domain_config.h"
#include "http_client.h"
#include "html_document.h"
#include "connection_pool.h"
#include "robots_txt_cache.h"
#include "url_normalizer.h"
#include "content_filter.h"
#include "sharded_disk_queue.h"
#include "html_processing_queue.h"
#include "work_stealing_queue.h"
#include "url_info.h"
#include "performance_monitor.h"
#include "rate_limiter.h"
#include "domain_blacklist.h"
#include "error_tracker.h"
#include "content_filter.h"
#include "sharded_disk_queue.h"
#include "gdrive_mount_manager.h"
#include "html_processing_queue.h"
#include "work_stealing_queue.h"
#include "url_info.h"

#include <fstream>
#include <atomic>
#include <thread>
#include <csignal>
#include <iostream>
#include <mutex>
#include <algorithm>
#include <filesystem>
#include <unordered_set>
#include <queue>
#include <sstream>
#include <random>
#include <memory>
#include <iomanip>
#include <unordered_map>

// Forward declarations
class RateLimiter;
class DomainBlacklist;
class ErrorTracker;
class ConnectionPool;
class RobotsTxtCache;

/**
 * Core crawler worker functions and utilities
 */

// CURL callback for writing data
size_t hybrid_write_callback(void* contents, size_t size, size_t nmemb, void* userp);

// Request type enum for better clarity
enum class RequestType {
    PAGE,
    ROBOTS_TXT
};

/**
 * 🤖 ADAPTIVE LINK EXTRACTOR
 * Dynamically adjusts link extraction based on page link density
 */
class AdaptiveLinkExtractor {
public:
    static std::vector<std::string> extract_links_adaptive(const std::string& html, const std::string& base_url);
    static int process_and_enqueue_links(const std::vector<std::string>& links, 
                                       int current_depth, 
                                       const std::string& referring_domain,
                                       size_t worker_id);
};

/**
 * Context for multi-request handling
 */
struct MultiRequestContext {
    CURL* curl_handle;
    UrlInfo url_info;
    std::string url;
    std::string response_data;
    std::string response_headers;
    std::string domain;
    std::chrono::steady_clock::time_point start_time;
    struct curl_slist* request_headers;
    RequestType type = RequestType::PAGE;
    int retries = 0;
    
    MultiRequestContext(const UrlInfo& info, ConnectionPool* pool);
    ~MultiRequestContext();
};

/**
 * ✅ DOMAIN QUEUES — Shared global thread-safe domain queue manager
 */
class SharedDomainQueueManager {
private:
    std::unordered_map<std::string, std::queue<UrlInfo>> domain_queues_;
    mutable std::unordered_map<std::string, std::unique_ptr<std::mutex>> domain_mutexes_;
    mutable std::mutex manager_mutex_; 

public:
    bool try_queue_for_domain(const std::string& domain, const UrlInfo& url_info);
    bool try_dequeue_from_available_domain(RateLimiter& limiter, UrlInfo& url_info, std::string& out_domain);
    size_t get_total_queued() const;
};



// Global variables - declared as extern in header
extern std::atomic<bool> stop_flag;
extern PerformanceMonitor global_monitor;

// Phase 1: Smart crawl scheduling components
extern std::shared_ptr<CrawlScheduling::CrawlMetadataStore> metadata_store;
extern std::unique_ptr<CrawlScheduling::SmartUrlFrontier> smart_url_frontier;
extern std::unique_ptr<CrawlScheduling::EnhancedFileStorageManager> enhanced_storage;

// Google Drive mount manager
extern std::shared_ptr<GDriveMountManager> gdrive_mount_manager;

// Phase 2: Advanced crawling components
extern std::unique_ptr<FeedPolling::RSSAtomPoller> rss_poller;
extern std::unique_ptr<SitemapParsing::SitemapParser> sitemap_parser;
extern std::shared_ptr<ConditionalGet::ConditionalGetManager> conditional_get_manager;

// Intelligent and domain configuration
extern std::unique_ptr<DomainConfiguration::DomainConfigManager> domain_config_manager;

// Global disk-backed URL manager
extern std::unique_ptr<ShardedDiskQueue> sharded_disk_queue;

// Global HTML processing pipeline
extern std::unique_ptr<HtmlProcessingQueue> html_processing_queue;

// Global work stealing queue
extern std::unique_ptr<WorkStealingQueue> work_stealing_queue;

// Global shared domain queue manager
extern std::unique_ptr<SharedDomainQueueManager> shared_domain_queues;

// Add new global store for deferred URLs
extern std::unordered_map<std::string, std::vector<UrlInfo>> g_deferred_urls;
extern std::mutex g_deferred_urls_mutex;

// Shutdown coordination infrastructure
extern std::condition_variable shutdown_coordinator_cv;
extern std::mutex shutdown_coordinator_mutex;

// Cleanup functions for proper shutdown order
void cleanup_global_components();
void coordinated_shutdown();
void cleanup_components_safely();
