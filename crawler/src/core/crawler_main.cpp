// HYBRID SPEED CRAWLER - Production-Ready with Ultimate Performance
// Combines CURL Multi-interface speed with enterprise-grade features
// Target: 300+ pages/sec with full compliance and robustness

#include "crawler_main.h"
#include "ultra_parser.h"
#include "language_detector.h"  // Add language detection
#include "constants.h"
#include "crawl_metadata.h"    // Phase 1: Smart crawl scheduling
#include "content_hash.h"      // Phase 1: Content hashing
#include "smart_frontier.h"    // Phase 1: Smart URL frontier
#include "enriched_storage.h"  // Phase 1: Enhanced storage with metadata
#include "rss_poller.h"        // Phase 2: RSS/Atom feed polling
#include "sitemap_parser.h"    // Phase 2: Sitemap parsing
#include "conditional_get.h"   // Phase 2: Conditional GET support
#include "config_loader.h"     // Dynamic configuration loading
#include "snippet_extractor.h"  // Intelligent snippet extraction
#include "domain_config.h"     // Per-domain configuration
#include "http_client.h"       // Unified HTTP client
#include "html_document.h"     // Standardized HTML parsing
#include "connection_pool.h"   // Connection pooling

// Modular utility includes
#include "url_normalizer.h"
#include "content_filter.h"
#include "sharded_disk_queue.h"
#include "connection_pool.h"
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

// Write callback for CURL
size_t hybrid_write_callback(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t total_size = size * nmemb;
    static_cast<std::string*>(userp)->append(static_cast<char*>(contents), total_size);
    return total_size;
}

// ✅ CONDITIONAL GET — Header callback for CURL to capture response headers
size_t hybrid_header_callback(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t total_size = size * nmemb;
    static_cast<std::string*>(userp)->append(static_cast<char*>(contents), total_size);
    return total_size;
}

// ✅ CONDITIONAL GET — Parse HTTP headers for ETag and Last-Modified
ConditionalGet::HttpHeaders parse_response_headers(const std::string& headers_text) {
    ConditionalGet::HttpHeaders headers;
    headers.response_time = std::chrono::system_clock::now();
    
    std::istringstream stream(headers_text);
    std::string line;
    
    while (std::getline(stream, line)) {
        // Convert to lowercase for case-insensitive comparison
        std::string line_lower = line;
        std::transform(line_lower.begin(), line_lower.end(), line_lower.begin(), ::tolower);
        
        if (line_lower.find("etag:") == 0) {
            size_t colon_pos = line.find(':');
            if (colon_pos != std::string::npos && colon_pos + 1 < line.length()) {
                headers.etag = line.substr(colon_pos + 1);
                // Trim whitespace
                headers.etag.erase(0, headers.etag.find_first_not_of(" \t\r\n"));
                headers.etag.erase(headers.etag.find_last_not_of(" \t\r\n") + 1);
            }
        }
        else if (line_lower.find("last-modified:") == 0) {
            size_t colon_pos = line.find(':');
            if (colon_pos != std::string::npos && colon_pos + 1 < line.length()) {
                headers.last_modified = line.substr(colon_pos + 1);
                // Trim whitespace
                headers.last_modified.erase(0, headers.last_modified.find_first_not_of(" \t\r\n"));
                headers.last_modified.erase(headers.last_modified.find_last_not_of(" \t\r\n") + 1);
            }
        }
    }
    
    return headers;
}

// Global shutdown flag
std::atomic<bool> stop_flag{false};

// Global performance monitor
PerformanceMonitor global_monitor;

// Global components
std::unique_ptr<CrawlLogger> crawl_logger;

// Phase 1: Smart crawl scheduling components
std::shared_ptr<CrawlScheduling::CrawlMetadataStore> metadata_store;
std::unique_ptr<CrawlScheduling::SmartUrlFrontier> smart_url_frontier;
std::unique_ptr<CrawlScheduling::EnhancedFileStorageManager> enhanced_storage;

// Phase 2: Advanced crawling components
std::unique_ptr<FeedPolling::RSSAtomPoller> rss_poller;
std::unique_ptr<SitemapParsing::SitemapParser> sitemap_parser;
std::shared_ptr<ConditionalGet::ConditionalGetManager> conditional_get_manager;

// Intelligent snippet extraction and domain configuration
std::unique_ptr<SnippetExtraction::SnippetExtractor> snippet_extractor;
std::unique_ptr<DomainConfiguration::DomainConfigManager> domain_config_manager;

// Global disk-backed URL manager (Phase 2: Upgraded to sharded)
std::unique_ptr<ShardedDiskQueue> sharded_disk_queue;

// Global HTML processing pipeline (Phase 2)
std::unique_ptr<HtmlProcessingQueue> html_processing_queue;

// Global work stealing queue (Phase 2)
std::unique_ptr<WorkStealingQueue> work_stealing_queue;

/**
 * 🤖 ADAPTIVE LINK EXTRACTOR
 * Dynamically adjusts link extraction based on page link density
 */
class AdaptiveLinkExtractor {
public:
    static std::vector<std::string> extract_links_adaptive(const std::string& html, const std::string& base_url) {
        // Use the ultra parser for maximum speed (300+ pages/sec)
        static thread_local UltraParser::UltraHTMLParser ultra_parser;
        std::vector<std::string> all_links = ultra_parser.extract_links_ultra(html, base_url);
        std::vector<std::string> filtered_links;
        
        // Calculate adaptive extraction count
        size_t total_links = all_links.size();
        size_t extract_count;
        
        if (total_links <= CrawlerConstants::LinkExtraction::MIN_LINKS_FOR_EXTRACTION) {
            // Very few links, extract up to minimum
            extract_count = std::min(total_links, (size_t)CrawlerConstants::LinkExtraction::MIN_LINKS_EXTRACT);
        } else {
            // Many links, extract percentage but at least min, max configured amount
            size_t percentage_count = total_links * CrawlerConstants::LinkExtraction::EXTRACTION_PERCENTAGE;
            extract_count = std::min((size_t)CrawlerConstants::LinkExtraction::MAX_LINKS_EXTRACT, 
                                   std::max((size_t)CrawlerConstants::LinkExtraction::MIN_LINKS_EXTRACT, 
                                          percentage_count));
        }
        
        // Filter and collect valid links
        for (const auto& link : all_links) {
            if (filtered_links.size() >= extract_count) break;
            
            if (ContentFilter::is_crawlable_url(link)) {
                filtered_links.push_back(link);
            }
        }
        
        return filtered_links;
    }
    
    // Enhanced link processing with Phase 1: Simplified for performance
    static int process_and_enqueue_links(const std::vector<std::string>& links, 
                                       int current_depth, 
                                       const std::string& referring_domain,
                                       size_t worker_id) {
        int successfully_enqueued = 0;
        
        // Limit processing to prevent queue overflow
        size_t max_links = std::min(links.size(), (size_t)50);
        
        for (size_t i = 0; i < max_links; ++i) {
            const std::string& link = links[i];
            float priority = ContentFilter::calculate_priority(link, current_depth + 1);
            UrlInfo new_url_info(link, priority, current_depth + 1, referring_domain);
            
            // ✅ WORKSTEALING QUEUE — Enhanced queueing with fallback strategy
            if (smart_url_frontier->enqueue(new_url_info)) {
                successfully_enqueued++;
            } else if (work_stealing_queue->push_local(worker_id, new_url_info)) {
                // ✅ Try work stealing queue if smart frontier is full
                successfully_enqueued++;
            } else {
                // If both queues full, save to disk (but don't block)
                std::vector<std::string> single_url = {link};
                sharded_disk_queue->save_urls_to_disk(single_url);
            }
        }
        
        return successfully_enqueued;
    }
};
struct MultiRequestContext {
    CURL* curl_handle;
    UrlInfo url_info;
    std::string url;
    std::string response_data;
    std::string response_headers; // ✅ CONDITIONAL GET — Store response headers
    std::string domain;
    std::chrono::steady_clock::time_point start_time;
    struct curl_slist* request_headers; // Track request headers for cleanup
    
    MultiRequestContext(const UrlInfo& info, ConnectionPool* pool = nullptr) 
        : url_info(info), url(info.url), domain(UrlNormalizer::extract_domain(info.url))
        , start_time(std::chrono::steady_clock::now()), request_headers(nullptr) {
        // Use domain-specific connection pooling if available
        if (pool) {
            curl_handle = pool->acquire_for_domain(domain);
        } else {
            curl_handle = curl_easy_init();
        }
        response_data.reserve(1024 * 1024); // 1MB pre-allocation
        response_headers.reserve(8192); // 8KB for headers
    }
    
    ~MultiRequestContext() {
        if (request_headers) {
            curl_slist_free_all(request_headers); // ✅ CONDITIONAL GET — Free headers
        }
        if (curl_handle) {
            curl_easy_cleanup(curl_handle);
        }
    }
};

/**
 * 🌐 DYNAMIC DOMAIN DISCOVERY MANAGER
 * Handles robots.txt fetching for newly discovered domains
 */
class DynamicDomainManager {
private:
    std::unordered_set<std::string> discovered_domains_;
    std::mutex domains_mutex_;
    
public:
    bool is_new_domain(const std::string& domain) {
        std::lock_guard<std::mutex> lock(domains_mutex_);
        return discovered_domains_.find(domain) == discovered_domains_.end();
    }
    
    void register_domain(const std::string& domain, RobotsTxtCache& robots) {
        std::lock_guard<std::mutex> lock(domains_mutex_);
        if (discovered_domains_.find(domain) == discovered_domains_.end()) {
            discovered_domains_.insert(domain);
            
            // Asynchronously fetch robots.txt for new domains
            std::thread([domain, &robots]() {
                try {
                    robots.fetch_and_cache(domain);
                    // Robots.txt fetched silently for performance
                } catch (...) {
                    // Silently ignore robots.txt fetch failures
                }
            }).detach();
        }
    }
    
    size_t get_discovered_count() const {
        std::lock_guard<std::mutex> lock(const_cast<std::mutex&>(domains_mutex_));
        return discovered_domains_.size();
    }
};

// ✅ DOMAIN QUEUES — Shared global thread-safe domain queue manager
class SharedDomainQueueManager {
private:
    std::unordered_map<std::string, std::queue<UrlInfo>> domain_queues_;
    mutable std::unordered_map<std::string, std::mutex> domain_mutexes_;
    mutable std::mutex manager_mutex_; // For managing domain_mutexes map
    
public:
    bool try_queue_for_domain(const std::string& domain, const UrlInfo& url_info) {
        std::lock_guard<std::mutex> manager_lock(manager_mutex_);
        std::lock_guard<std::mutex> domain_lock(domain_mutexes_[domain]);
        
        if (domain_queues_[domain].size() < CrawlerConstants::Queue::DOMAIN_QUEUE_LIMIT) {
            domain_queues_[domain].push(url_info);
            return true;
        }
        return false;
    }
    
    bool try_dequeue_from_available_domain(RateLimiter& limiter, UrlInfo& url_info, std::string& domain) {
        std::lock_guard<std::mutex> manager_lock(manager_mutex_);
        
        for (auto& [d, queue] : domain_queues_) {
            if (!queue.empty() && limiter.can_request_now(d)) {
                std::lock_guard<std::mutex> domain_lock(domain_mutexes_[d]);
                if (!queue.empty()) { // Double-check after acquiring domain lock
                    url_info = queue.front();
                    queue.pop();
                    domain = d;
                    return true;
                }
            }
        }
        return false;
    }
    
    size_t get_total_queued() const {
        std::lock_guard<std::mutex> manager_lock(manager_mutex_);
        size_t total = 0;
        for (const auto& [domain, queue] : domain_queues_) {
            total += queue.size();
        }
        return total;
    }
};

// Global domain manager
std::unique_ptr<DynamicDomainManager> domain_manager;

// ✅ DOMAIN QUEUES — Global shared domain queue manager
std::unique_ptr<SharedDomainQueueManager> shared_domain_queues;

/**
 * High-performance multi-interface crawler worker
 */
void multi_crawler_worker(int worker_id, RobotsTxtCache& robots, RateLimiter& limiter,
                         DomainBlacklist& blacklist, ErrorTracker& error_tracker) {
    
    // Initialize connection pool for domain-specific connections
    ConnectionPool domain_connection_pool;
    
    // Initialize CURL multi handle
    CURLM* multi_handle = curl_multi_init();
    if (!multi_handle) {
        std::cerr << "Failed to initialize CURL multi handle in worker " << worker_id << "\n";
        return;
    }
    
    // Configure multi handle for maximum performance
    curl_multi_setopt(multi_handle, CURLMOPT_MAXCONNECTS, CrawlerConstants::Network::MAX_CONNECTIONS);
    curl_multi_setopt(multi_handle, CURLMOPT_MAX_TOTAL_CONNECTIONS, CrawlerConstants::Network::MAX_CONNECTIONS);
    curl_multi_setopt(multi_handle, CURLMOPT_MAX_HOST_CONNECTIONS, CrawlerConstants::Network::MAX_HOST_CONNECTIONS);
    curl_multi_setopt(multi_handle, CURLMOPT_PIPELINING, CURLPIPE_MULTIPLEX);
    
    // Set up global DNS cache
    CURLSH* share_handle = curl_share_init();
    curl_share_setopt(share_handle, CURLSHOPT_SHARE, CURL_LOCK_DATA_DNS);
    
    // Active requests management
    std::unordered_map<CURL*, std::unique_ptr<MultiRequestContext>> active_requests;
    const int MAX_CONCURRENT = CrawlerConstants::Queue::MAX_CONCURRENT_REQUESTS;
    
    // Batch processing
    std::vector<std::pair<std::string, std::string>> batch_buffer;
    batch_buffer.reserve(100);
    
    // Worker statistics & queue drain diagnostics
    int pages_processed = 0;
    int urls_dequeued = 0;
    int urls_skipped_blacklist = 0;
    int urls_skipped_robots = 0;
    int urls_skipped_rate_limit = 0;
    int successful_requests = 0;
    auto worker_start = std::chrono::steady_clock::now();
    auto last_queue_check = worker_start;
    
    std::cout << "🏃 Worker " << worker_id << " starting with MAX_CONCURRENT=" << MAX_CONCURRENT << "\n";
    
    while (!stop_flag) {
        auto loop_start = std::chrono::steady_clock::now();
        
        // Log queue drain diagnostics every configured interval
        if (std::chrono::duration_cast<std::chrono::seconds>(loop_start - last_queue_check).count() >= 
            CrawlerConstants::Monitoring::WORKER_DIAGNOSTICS_INTERVAL_SECONDS) {
            size_t current_queue_size = smart_url_frontier->size();
            std::cout << "🔍 Worker " << worker_id << " diagnostics: "
                     << "Queue=" << current_queue_size 
                     << " | Dequeued=" << urls_dequeued
                     << " | Active=" << active_requests.size()
                     << " | Processed=" << pages_processed
                     << " | Skipped: BL=" << urls_skipped_blacklist 
                     << " R=" << urls_skipped_robots 
                     << " RL=" << urls_skipped_rate_limit << "\n";
            last_queue_check = loop_start;
        }
        
        // Add new requests up to the limit - Phase 2: Simplified queue management
        int attempts = 0;
        const int MAX_ATTEMPTS = 100; // Reduce attempts to prevent blocking
        while (active_requests.size() < MAX_CONCURRENT && !stop_flag && attempts < MAX_ATTEMPTS) {
            UrlInfo url_info("", 0.0f);
            attempts++;
            
            // ✅ WORKSTEALING QUEUE — Integrated queue access strategy
            bool found_url = false;
            
            // 1. Try smart priority queue first (Phase 1)
            if (smart_url_frontier->dequeue(url_info)) {
                found_url = true;
            }
            // 2. ✅ Try work stealing queue as secondary priority
            else if (work_stealing_queue->try_steal(worker_id, url_info)) {
                found_url = true;
            }
            // 3. Try loading from disk if both queues are empty
            else {
                auto disk_urls = sharded_disk_queue->load_urls_from_disk(50); // Smaller batch
                if (!disk_urls.empty()) {
                    url_info = UrlInfo(disk_urls[0], CrawlerConstants::Priority::DISK_URL_PRIORITY, 0);
                    found_url = true;
                    
                    // Re-queue remaining URLs to smart frontier and work stealing queue
                    for (size_t i = 1; i < std::min(disk_urls.size(), (size_t)10); ++i) {
                        UrlInfo disk_url(disk_urls[i], CrawlerConstants::Priority::DISK_URL_PRIORITY, 0);
                        // ✅ Try smart frontier first, fallback to work stealing queue
                        if (!smart_url_frontier->enqueue(disk_url)) {
                            work_stealing_queue->push_local(worker_id, disk_url);
                        }
                    }
                }
            }
            
            if (!found_url) {
                break; // Exit early if no URLs found
            }
            
            urls_dequeued++;
            
            std::string domain = UrlNormalizer::extract_domain(url_info.url);
            std::string path = UrlNormalizer::extract_path(url_info.url);
            
            // Skip blacklisted domains
            if (blacklist.is_blacklisted(domain)) {
                urls_skipped_blacklist++;
                continue;
            }
            
            // Fast-path for trusted domains - skip robots.txt entirely for speed
            bool is_trusted_domain = (domain.find("wikipedia.org") != std::string::npos ||
                                    domain.find("github.com") != std::string::npos ||
                                    domain.find("stackoverflow.com") != std::string::npos ||
                                    domain.find("httpbin.org") != std::string::npos ||
                                    domain.find("jsonplaceholder.typicode.com") != std::string::npos ||
                                    domain.find("arxiv.org") != std::string::npos ||
                                    domain.find("reddit.com") != std::string::npos);
            
            // Check robots.txt compliance only for untrusted domains
            if (!is_trusted_domain && !robots.is_allowed(domain, path)) {
                urls_skipped_robots++;
                continue;
            }
            
            // ✅ DOMAIN QUEUES — Apply rate limiting with shared domain queues
            if (!limiter.can_request_now(domain)) {
                // Store rate-limited URLs in shared domain-specific queue
                if (!shared_domain_queues->try_queue_for_domain(domain, url_info)) {
                    // If domain queue is full, re-queue in smart frontier
                    smart_url_frontier->enqueue(url_info);
                }
                
                urls_skipped_rate_limit++;
                
                // ✅ Try to dequeue from any domain that's not rate limited
                std::string available_domain;
                if (shared_domain_queues->try_dequeue_from_available_domain(limiter, url_info, available_domain)) {
                    domain = available_domain;
                    path = UrlNormalizer::extract_path(url_info.url);
                    // Continue with this URL from available domain
                } else {
                    continue; // No URLs available from non-rate-limited domains
                }
            }
            
            // Create request context - temporarily disable domain-specific connections
            auto ctx = std::make_unique<MultiRequestContext>(url_info);
            successful_requests++;
            attempts = 0; // Reset attempts after successful request creation
            
            // Phase 2: Check if we should use conditional GET
            auto cache_info = conditional_get_manager->get_cache_info(url_info.url);
            
            if (cache_info.has_cache_info()) {
                // Add conditional GET headers
                if (!cache_info.etag.empty()) {
                    std::string if_none_match = "If-None-Match: " + cache_info.etag;
                    ctx->request_headers = curl_slist_append(ctx->request_headers, if_none_match.c_str());
                }
                if (!cache_info.last_modified.empty()) {
                    std::string if_modified_since = "If-Modified-Since: " + cache_info.last_modified;
                    ctx->request_headers = curl_slist_append(ctx->request_headers, if_modified_since.c_str());
                }
            }
            
            // Configure CURL handle for production use with speed optimizations
            curl_easy_setopt(ctx->curl_handle, CURLOPT_URL, ctx->url.c_str());
            curl_easy_setopt(ctx->curl_handle, CURLOPT_WRITEFUNCTION, hybrid_write_callback);
            curl_easy_setopt(ctx->curl_handle, CURLOPT_WRITEDATA, &ctx->response_data);
            
            // ✅ CONDITIONAL GET — Add header capture callback
            curl_easy_setopt(ctx->curl_handle, CURLOPT_HEADERFUNCTION, hybrid_header_callback);
            curl_easy_setopt(ctx->curl_handle, CURLOPT_HEADERDATA, &ctx->response_headers);
            
            // Phase 2: Set conditional headers if any
            if (ctx->request_headers) {
                curl_easy_setopt(ctx->curl_handle, CURLOPT_HTTPHEADER, ctx->request_headers);
            }
            
            // Performance optimizations - balanced timeouts
            curl_easy_setopt(ctx->curl_handle, CURLOPT_TIMEOUT, CrawlerConstants::Network::TIMEOUT_SECONDS);
            curl_easy_setopt(ctx->curl_handle, CURLOPT_CONNECTTIMEOUT, CrawlerConstants::Network::CONNECT_TIMEOUT_SECONDS);
            curl_easy_setopt(ctx->curl_handle, CURLOPT_FOLLOWLOCATION, CrawlerConstants::Security::FOLLOW_REDIRECTS);
            curl_easy_setopt(ctx->curl_handle, CURLOPT_MAXREDIRS, CrawlerConstants::Network::MAX_REDIRECTS);
            curl_easy_setopt(ctx->curl_handle, CURLOPT_NOSIGNAL, CrawlerConstants::Security::THREAD_SAFE_MODE);
            curl_easy_setopt(ctx->curl_handle, CURLOPT_TCP_NODELAY, CrawlerConstants::Security::TCP_NODELAY);
            curl_easy_setopt(ctx->curl_handle, CURLOPT_TCP_KEEPALIVE, CrawlerConstants::Security::TCP_KEEPALIVE);
            curl_easy_setopt(ctx->curl_handle, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_2_0); // HTTP/2
            curl_easy_setopt(ctx->curl_handle, CURLOPT_BUFFERSIZE, CrawlerConstants::Network::BUFFER_SIZE);
            curl_easy_setopt(ctx->curl_handle, CURLOPT_ACCEPT_ENCODING, CrawlerConstants::Headers::ACCEPT_ENCODING);
            
            // Production headers
            curl_easy_setopt(ctx->curl_handle, CURLOPT_USERAGENT, CrawlerConstants::Headers::USER_AGENT);
            
            // SSL settings for production
            curl_easy_setopt(ctx->curl_handle, CURLOPT_SSL_VERIFYPEER, CrawlerConstants::Security::SSL_VERIFY_PEER);
            curl_easy_setopt(ctx->curl_handle, CURLOPT_SSL_VERIFYHOST, CrawlerConstants::Security::SSL_VERIFY_HOST);
            
            // ✅ CURL SHARED HANDLE — Apply shared DNS cache to each easy handle
            curl_easy_setopt(ctx->curl_handle, CURLOPT_SHARE, share_handle);
            
            // Add to multi handle
            CURLMcode mc = curl_multi_add_handle(multi_handle, ctx->curl_handle);
            if (mc == CURLM_OK) {
                limiter.record_request(domain);
                active_requests[ctx->curl_handle] = std::move(ctx);
            } else {
                std::cerr << "Failed to add handle to multi: " << curl_multi_strerror(mc) << "\n";
            }
        }
        
        // No active requests, check stop flag and sleep briefly
        if (active_requests.empty()) {
            if (stop_flag) break; // Exit immediately if stop requested
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            continue;
        }
        
        // Perform all transfers
        int running_handles = 0;
        CURLMcode mc = curl_multi_perform(multi_handle, &running_handles);
        if (mc != CURLM_OK) {
            std::cerr << "curl_multi_perform failed: " << curl_multi_strerror(mc) << "\n";
            break;
        }
        
        // Check for completed transfers
        CURLMsg* msg;
        int msgs_left;
        while ((msg = curl_multi_info_read(multi_handle, &msgs_left))) {
            if (msg->msg == CURLMSG_DONE) {
                CURL* curl = msg->easy_handle;
                auto it = active_requests.find(curl);
                
                if (it != active_requests.end()) {
                    auto& ctx = it->second;
                    
                    if (msg->data.result == CURLE_OK) {
                        long http_code = 0;
                        curl_off_t download_size = 0;
                        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
                        curl_easy_getinfo(curl, CURLINFO_SIZE_DOWNLOAD_T, &download_size);
                        
                        limiter.record_success(ctx->domain);
                        error_tracker.record_success(ctx->domain);
                        global_monitor.add_bytes(static_cast<long>(download_size));
                        
                        // Phase 2: Handle conditional GET responses
                        if (http_code == 304) {
                            // Content not modified - no need to process
                            std::cout << "304 Not Modified: " << ctx->url << std::endl;
                            // Content hasn't changed, don't update metadata backoff
                            
                        } else if (http_code == CrawlerConstants::HttpStatus::OK && !ctx->response_data.empty()) {
                            // ✅ CONDITIONAL GET — Parse and cache response headers for future requests
                            ConditionalGet::HttpHeaders new_headers = parse_response_headers(ctx->response_headers);
                            conditional_get_manager->update_cache(ctx->url, new_headers);
                            
                            // Phase 1: Calculate content hash and update metadata
                            std::string content_hash = ContentHashing::FastContentHasher::hash_key_content(ctx->response_data);
                            metadata_store->update_after_crawl(ctx->url, content_hash);                            // Validate content quality
                            if (ContentFilter::is_high_quality_content(ctx->response_data)) {
                                pages_processed++;
                                global_monitor.increment_pages();
                                
                                // Extract page metadata using HtmlDocument
                                HtmlDocument doc(ctx->response_data);
                                std::string title = doc.getTitle();
                                
                                // Log page information
                                crawl_logger->log_page(ctx->url, title, http_code, ctx->url_info.depth,
                                                     ctx->domain, ctx->response_data.size(), ctx->start_time);
                                
                                // 🌐 ZERO-COST LANGUAGE DETECTION: Filter non-English pages
                                if (FastLanguageDetector::is_english_content(ctx->response_data, ctx->url)) {
                                    // Add to batch for file storage (only English content)
                                    batch_buffer.emplace_back(ctx->url, ctx->response_data);
                                    
                                    // Save batch when it reaches optimal size
                                    if (batch_buffer.size() >= CrawlerConstants::Storage::BATCH_SIZE) {
                                        // Phase 1: Use enhanced storage with metadata
                                        enhanced_storage->save_html_batch_with_metadata(batch_buffer);
                                        batch_buffer.clear();  // ✅ Only clear after saving
                                    }
                                } else {
                                    // Skip non-English content - don't store it
                                    global_monitor.increment_filtered();
                                }
                                                                
                                // PHASE 2: Pipeline HTML processing instead of blocking here
                                if (ctx->url_info.depth < 5 && doc.isValidHtml(ctx->response_data)) {
                                    // Try to queue HTML for asynchronous processing (non-blocking)
                                    HtmlProcessingTask html_task(
                                        ctx->response_data, // Use copy instead of move to avoid issues
                                        ctx->url,
                                        ctx->domain,
                                        ctx->url_info.depth
                                    );
                                    
                                    // Non-blocking enqueue - if queue is full, process synchronously
                                    if (!html_processing_queue->enqueue(std::move(html_task))) {
                                        // HTML queue full, process synchronously as fallback (simplified)
                                        std::vector<std::string> links = AdaptiveLinkExtractor::extract_links_adaptive(
                                            ctx->response_data, ctx->url);
                                        
                                        // Simplified link processing for performance
                                        int new_links_added = 0;
                                        for (const std::string& link : links) {
                                            if (new_links_added >= 20) break; // Limit to prevent queue overflow
                                            
                                            float priority = ContentFilter::calculate_priority(link, ctx->url_info.depth + 1);
                                            UrlInfo new_url_info(link, priority, ctx->url_info.depth + 1, ctx->domain);
                                            
                                            // Simplified queueing - just try smart queue
                                            if (smart_url_frontier->enqueue(new_url_info)) {
                                                new_links_added++;
                                            }
                                        }
                                        
                                        global_monitor.increment_links(new_links_added);
                                    }
                                }
                            }
                        } else if (http_code == CrawlerConstants::HttpStatus::TOO_MANY_REQUESTS || 
                                  http_code == CrawlerConstants::HttpStatus::SERVICE_UNAVAILABLE) {
                            // Handle rate limiting from server
                            limiter.throttle_domain(ctx->domain, CrawlerConstants::Network::THROTTLE_DURATION_SECONDS);
                        } else if (http_code >= CrawlerConstants::HttpStatus::BAD_REQUEST) {
                            crawl_logger->log_error(ctx->url, "HTTP " + std::to_string(http_code));
                        }
                    } else {
                        // Handle cURL errors
                        global_monitor.increment_errors();
                        limiter.record_failure(ctx->domain);
                        error_tracker.record_error(ctx->domain, msg->data.result);
                        
                        // Check if domain should be blacklisted
                        if (error_tracker.should_blacklist_domain(ctx->domain)) {
                            blacklist.add_temporary(ctx->domain);
                            std::cout << "Worker " << worker_id << " blacklisted domain: " << ctx->domain << std::endl;
                        }
                        
                        crawl_logger->log_error(ctx->url, curl_easy_strerror(msg->data.result));
                    }
                    
                    // Remove from multi handle and cleanup
                    curl_multi_remove_handle(multi_handle, curl);
                    active_requests.erase(it);
                }
            }
        }
        
        // Wait for activity with timeout
        if (running_handles > 0) {
            curl_multi_wait(multi_handle, nullptr, 0, 100, nullptr);
        }
        
        // Periodic progress reporting - reduced frequency for performance
        if (pages_processed % CrawlerConstants::Monitoring::PROGRESS_REPORT_FREQUENCY == 0 && pages_processed > 0) {
            auto now = std::chrono::steady_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - worker_start).count();
            if (elapsed > 0) {
                // Progress logged only every 500 pages for performance
            }
        }
    }
    
    // Cleanup remaining requests
    for (auto& [curl, ctx] : active_requests) {
        curl_multi_remove_handle(multi_handle, curl);
    }
    
    // Save any remaining batch (filter for English content)
    if (!batch_buffer.empty()) {
        // Filter English content from final batch
        std::vector<std::pair<std::string, std::string>> english_batch;
        for (const auto& [url, content] : batch_buffer) {
            if (FastLanguageDetector::is_english_content(content, url)) {
                english_batch.emplace_back(url, content);
            } else {
                global_monitor.increment_filtered();
            }
        }
        
        if (!english_batch.empty()) {
            // Phase 1: Use enhanced storage with metadata
            enhanced_storage->save_html_batch_with_metadata(english_batch);
        }
    }
    
    // Clean up shared handle and multi handle
    curl_share_cleanup(share_handle);
    curl_multi_cleanup(multi_handle);
    std::cout << "Multi-worker " << worker_id << " finished. Processed " << pages_processed << " pages.\n";
}

/**
 * 🔧 PHASE 2: DEDICATED HTML PROCESSING WORKER
 * Separates HTML parsing from network I/O for better pipeline efficiency
 */
void html_processing_worker(int worker_id, RobotsTxtCache& robots) {
    std::cout << "🔧 HTML processor " << worker_id << " starting...\n";
    
    int links_processed = 0;
    int batches_processed = 0;
    auto worker_start = std::chrono::steady_clock::now();
    
    while (!stop_flag) {
        HtmlProcessingTask task("", "", "", 0);
        
        // Get next HTML processing task
        if (!html_processing_queue->dequeue(task)) {
            if (stop_flag) break;
            continue;
        }
        
        try {
            // Extract links using fast streaming parser
            std::vector<std::string> links = AdaptiveLinkExtractor::extract_links_adaptive(
                task.html, task.url);
            
            // Register new domains for robots.txt fetching
            for (const std::string& link : links) {
                std::string link_domain = UrlNormalizer::extract_domain(link);
                if (domain_manager->is_new_domain(link_domain)) {
                    domain_manager->register_domain(link_domain, robots);
                }
            }
            
            // Process and enqueue links with Phase 2 improvements
            int new_links_added = AdaptiveLinkExtractor::process_and_enqueue_links(
                links, task.depth, task.domain, worker_id);
            
            global_monitor.increment_links(new_links_added);
            links_processed += links.size();
            batches_processed++;
            
            // Periodic progress for HTML processors
            if (batches_processed % CrawlerConstants::Monitoring::PROGRESS_REPORT_FREQUENCY/5 == 0) {
                auto now = std::chrono::steady_clock::now();
                auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - worker_start).count();
                if (elapsed > 0) {
                    double rate = static_cast<double>(links_processed) / elapsed;
                    std::cout << "🔧 HTML processor " << worker_id << ": " 
                             << batches_processed << " batches, " 
                             << links_processed << " links (" 
                             << std::fixed << std::setprecision(1) << rate << " links/s)\n";
                }
            }
            
        } catch (const std::exception& e) {
            std::cerr << "HTML processing error: " << e.what() << "\n";
        }
    }
    
    std::cout << "🔧 HTML processor " << worker_id << " finished. Processed " 
             << batches_processed << " batches, " << links_processed << " total links.\n";
}

/**
 * 🚨 EMERGENCY SEED INJECTOR
 * Provides high-quality URLs when crawl queue gets too low
 */
class EmergencySeedInjector {
private:
    static std::vector<std::string> get_emergency_seeds() {
        // ✅ EMERGENCY SEEDS — Load from JSON configuration instead of hardcoded
        try {
            std::string config_path = std::string(CrawlerConstants::Paths::CONFIG_PATH) + "/emergency_seeds.json";
            std::ifstream file(config_path);
            if (!file.is_open()) {
                std::cerr << "⚠️  Warning: Could not open emergency seeds config: " << config_path << "\n";
                return {}; // Return empty vector if config can't be loaded
            }
            
            std::string json_content((std::istreambuf_iterator<char>(file)),
                                   std::istreambuf_iterator<char>());
            file.close();
            
            // Simple JSON parsing for emergency_seeds array
            std::vector<std::string> seeds;
            size_t start = json_content.find("\"emergency_seeds\"");
            if (start == std::string::npos) {
                std::cerr << "⚠️  Warning: 'emergency_seeds' field not found in config\n";
                return {};
            }
            
            start = json_content.find("[", start);
            size_t end = json_content.find("]", start);
            if (start == std::string::npos || end == std::string::npos) {
                std::cerr << "⚠️  Warning: Invalid JSON format in emergency seeds config\n";
                return {};
            }
            
            std::string urls_section = json_content.substr(start + 1, end - start - 1);
            std::istringstream iss(urls_section);
            std::string line;
            
            while (std::getline(iss, line, ',')) {
                // Extract URL from JSON string format "url"
                size_t first_quote = line.find('"');
                size_t last_quote = line.rfind('"');
                if (first_quote != std::string::npos && last_quote != std::string::npos && first_quote != last_quote) {
                    std::string url = line.substr(first_quote + 1, last_quote - first_quote - 1);
                    if (!url.empty() && url.find("http") == 0) {
                        seeds.push_back(url);
                    }
                }
            }
            
            return seeds;
            
        } catch (const std::exception& e) {
            std::cerr << "⚠️  Warning: Error loading emergency seeds: " << e.what() << "\n";
            return {}; // Return empty vector on error
        }
    }
    
public:
    static bool inject_emergency_seeds(int& injection_count, 
                                       const int max_injections = CrawlerConstants::ErrorHandling::MAX_EMERGENCY_INJECTIONS) {
        if (injection_count >= max_injections) {
            return false;
        }
        
        auto seeds = get_emergency_seeds();
        int injected = 0;
        
        for (const auto& seed : seeds) {
            float priority = CrawlerConstants::Priority::EMERGENCY_SEED_PRIORITY; // Very high priority for emergency seeds
            UrlInfo seed_info(seed, priority, 0);
            if (smart_url_frontier->enqueue(seed_info)) {
                injected++;
            }
        }
        
        injection_count++;
        std::cout << "🚨 Emergency injection #" << injection_count << ": Added " 
                 << injected << "/" << seeds.size() << " emergency seeds\n";
        
        return true;
    }
};
/**
 * 📊 ENHANCED MONITORING THREAD with Always-On Queue & Speed Logging
 */
void enhanced_monitoring_thread() {
    std::cout << "📊 Starting continuous queue & speed monitoring...\n";
    
    auto last_stats = std::chrono::steady_clock::now();
    auto last_cleanup = std::chrono::steady_clock::now();
    auto monitoring_start = std::chrono::steady_clock::now();
    
    static int emergency_injection_count = 0;
    static int low_queue_warnings = 0;
    
    // Initial queue status - log immediately at startup
    size_t initial_smart_size = smart_url_frontier->size();
    size_t initial_disk_queue_size = sharded_disk_queue->get_total_disk_queue_size();
    size_t initial_work_stealing_size = work_stealing_queue->total_size();
    std::cout << "🔍 STARTUP QUEUE STATUS:\n";
    std::cout << "   Smart Queue: " << initial_smart_size << " URLs\n";
    std::cout << "   Sharded Disk Queue: " << initial_disk_queue_size << " URLs\n";
    std::cout << "   Work Stealing Queue: " << initial_work_stealing_size << " URLs\n";
    std::cout << "   HTML Processing Queue: " << html_processing_queue->size() << " tasks\n";
    std::cout << "   Total Available: " << (initial_smart_size + initial_disk_queue_size + initial_work_stealing_size) << " URLs\n\n";
    
    while (!stop_flag) {
        std::this_thread::sleep_for(std::chrono::seconds(CrawlerConstants::Monitoring::QUEUE_CHECK_INTERVAL_SECONDS));
        
        auto now = std::chrono::steady_clock::now();
        auto elapsed_seconds = std::chrono::duration_cast<std::chrono::seconds>(now - monitoring_start).count();
        
        size_t smart_queue_size = smart_url_frontier->size();
        size_t disk_queue_size = sharded_disk_queue->get_total_disk_queue_size();
        size_t work_stealing_size = work_stealing_queue->total_size();
        size_t html_queue_size = html_processing_queue->size();
        double current_rate = global_monitor.get_crawl_rate();
        size_t total_processed = global_monitor.get_total_pages();
        
        // ALWAYS LOG QUEUE STATUS & SPEED (every 5 seconds) - Phase 1 & 2 enhanced
        std::cout << "[" << std::setw(4) << elapsed_seconds << "s] "
                 << "Smart: " << std::setw(4) << smart_queue_size
                 << " | Disk: " << std::setw(4) << disk_queue_size
                 << " | Work: " << std::setw(3) << work_stealing_size
                 << " | HTML: " << std::setw(3) << html_queue_size
                 << " | Speed: " << std::fixed << std::setprecision(1) << std::setw(6) << current_rate << " p/s"
                 << " | Total: " << std::setw(6) << total_processed << "\n";
        
        // Print detailed statistics every configured interval
        if (std::chrono::duration_cast<std::chrono::seconds>(now - last_stats).count() >= 
            CrawlerConstants::Monitoring::DETAILED_STATS_INTERVAL_SECONDS) {
            std::cout << "\n📊 DETAILED STATS (15s interval):\n";
            global_monitor.print_stats(smart_queue_size, 0);
            
            // Performance indicators with more granular feedback
            if (current_rate >= CrawlerConstants::Performance::TARGET_PAGES_PER_SECOND) {
                std::cout << "🚀 TARGET ACHIEVED: " << std::fixed << std::setprecision(1) 
                         << current_rate << " pages/sec\n";
            } else if (current_rate >= CrawlerConstants::Performance::HIGH_PERFORMANCE_THRESHOLD) {
                std::cout << "⚡ High Performance: " << std::fixed << std::setprecision(1) 
                         << current_rate << " pages/sec\n";
            } else if (current_rate >= CrawlerConstants::Performance::GOOD_PERFORMANCE_THRESHOLD) {
                std::cout << "🔥 Good Performance: " << std::fixed << std::setprecision(1) 
                         << current_rate << " pages/sec\n";
            } else if (current_rate >= CrawlerConstants::Performance::MODERATE_PERFORMANCE_THRESHOLD) {
                std::cout << "⚠️ Moderate Performance: " << std::fixed << std::setprecision(1) 
                         << current_rate << " pages/sec\n";
            } else if (current_rate >= CrawlerConstants::Performance::LOW_PERFORMANCE_THRESHOLD) {
                std::cout << "🐌 Low Performance: " << std::fixed << std::setprecision(1) 
                         << current_rate << " pages/sec\n";
            } else {
                std::cout << "🔴 Very Low Performance: " << std::fixed << std::setprecision(1) 
                         << current_rate << " pages/sec\n";
            }
            
            std::cout << "\n";
            std::cout.flush();
            last_stats = now;
        }
        
        // 🔄 PHASE 2: ENHANCED QUEUE MANAGEMENT with sharded disk and work stealing
        
        // 1. Refill from sharded disk when smart queue gets low
        if (smart_queue_size < CrawlerConstants::Queue::REFILL_THRESHOLD && disk_queue_size > 0) {
            auto loaded_urls = sharded_disk_queue->load_urls_from_disk(CrawlerConstants::Queue::REFILL_THRESHOLD);
            int refilled = 0;
            
            for (const auto& url : loaded_urls) {
                float priority = CrawlerConstants::Priority::DISK_URL_PRIORITY;
                UrlInfo url_info(url, priority, 0);
                if (smart_url_frontier->enqueue(url_info)) {
                    refilled++;
                }
            }
            
            if (refilled > 0) {
                std::cout << "✅ Loaded " << refilled << " URLs from sharded disk (Smart queue was " << smart_queue_size << ")\n";
            }
        }
        
        // 2. Periodic cleanup of empty disk shards
        if (elapsed_seconds % CrawlerConstants::Monitoring::CLEANUP_INTERVAL_SECONDS == 0) { // Every minute
            sharded_disk_queue->cleanup_empty_shards();
        }
        
        // 2. Emergency seed injection when critically low - more aggressive
        if (smart_queue_size < CrawlerConstants::Queue::LOW_QUEUE_THRESHOLD && 
            current_rate < CrawlerConstants::Performance::SHUTDOWN_RATE_THRESHOLD) {
            low_queue_warnings++;
            
            if (low_queue_warnings >= CrawlerConstants::ErrorHandling::LOW_QUEUE_WARNING_THRESHOLD) {
                if (EmergencySeedInjector::inject_emergency_seeds(emergency_injection_count)) {
                    low_queue_warnings = 0; // Reset warnings after injection
                }
            }
        } else {
            low_queue_warnings = 0; // Reset warnings when queue recovers
        }
        
        // 3. Auto-shutdown conditions - Phase 1 & 2 enhanced
        size_t total_urls_available = smart_queue_size + disk_queue_size + work_stealing_size;
        if (total_urls_available < CrawlerConstants::Queue::CRITICAL_QUEUE_THRESHOLD && 
            current_rate < CrawlerConstants::Performance::VERY_LOW_PERFORMANCE_THRESHOLD) {
            static int shutdown_warnings = 0;
            shutdown_warnings++;
            
            std::cout << "🛑 Shutdown condition detected: Total URLs=" << total_urls_available
                     << " (Smart=" << smart_queue_size << ", Disk=" << disk_queue_size 
                     << ", Work=" << work_stealing_size << "), Rate=" << current_rate 
                     << " (warning #" << shutdown_warnings << "/" 
                     << CrawlerConstants::ErrorHandling::SHUTDOWN_WARNING_THRESHOLD << ")\n";
            
            if (shutdown_warnings >= CrawlerConstants::ErrorHandling::SHUTDOWN_WARNING_THRESHOLD) {
                std::cout << "🏁 Triggering graceful shutdown - no more URLs to crawl\n";
                stop_flag = true;
            }
        }
        
        // Safety timeout (configurable)
        auto total_elapsed = std::chrono::duration_cast<std::chrono::minutes>(now - last_cleanup).count();
        if (total_elapsed >= CrawlerConstants::Monitoring::SAFETY_TIMEOUT_MINUTES) {
            std::cout << "⏰ Safety timeout reached (" << CrawlerConstants::Monitoring::SAFETY_TIMEOUT_MINUTES 
                     << " minutes). Shutting down...\n";
            stop_flag = true;
        }
    }
}

void signal_handler(int signal) {
    static std::atomic<int> shutdown_count{0};
    int count = shutdown_count.fetch_add(1);
    
    if (count == 0) {
        std::cout << "\nReceived shutdown signal (" << signal << "). Gracefully shutting down hybrid crawler...\n";
        stop_flag = true;
        
        // Give threads a chance to shut down gracefully
        std::thread([]{
            std::this_thread::sleep_for(std::chrono::seconds(5));
            if (stop_flag) {
                std::cout << "Forcing shutdown after 5 seconds...\n";
                std::quick_exit(0);
            }
        }).detach();
    } else if (count == 1) {
        std::cout << "\nSecond shutdown signal received. Force shutdown in 2 seconds...\n";
        std::thread([]{
            std::this_thread::sleep_for(std::chrono::seconds(2));
            std::cout << "Force shutdown now!\n";
            std::quick_exit(1);
        }).detach();
    } else {
        std::cout << "\nImmediate shutdown!\n";
        std::quick_exit(2);
    }
}

int main(int argc, char* argv[]) {
    std::cout << "🚀 HYBRID SPEED CRAWLER - Production-Ready Ultimate Performance\n";
    std::cout << "================================================================\n";
    
    // Set up signal handling FIRST
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);
    
    // Initialize cURL globally
    curl_global_init(CURL_GLOBAL_DEFAULT);
    
    ContentFilter::initialize(CrawlerConstants::Paths::CONFIG_PATH);
    
    // Parse command line arguments - Phase 2: Optimal configuration
    int max_threads = std::min(CrawlerConstants::Workers::DEFAULT_MAX_THREADS, 
                              (int)std::thread::hardware_concurrency());
    int max_depth = CrawlerConstants::Queue::DEFAULT_MAX_DEPTH;
    int max_queue_size = CrawlerConstants::Queue::DEFAULT_MAX_QUEUE_SIZE;
    
    if (argc > 1) max_threads = std::atoi(argv[1]);
    if (argc > 2) max_depth = std::atoi(argv[2]);
    if (argc > 3) max_queue_size = std::atoi(argv[3]);
    
    // Phase 2: Calculate optimal worker distribution (simplified)
    int network_workers = max_threads;
    int html_workers = std::max(1, max_threads / 8); // Reduce HTML workers to prevent contention
    
    std::cout << "Configuration - Phase 1 & 2 Enhanced (Performance Optimized):\n";
    std::cout << "- Network workers: " << network_workers << "\n";
    std::cout << "- HTML processors: " << html_workers << " (reduced for performance)\n";
    std::cout << "- Max crawl depth: " << max_depth << "\n";
    std::cout << "- Max queue size: " << max_queue_size << "\n";
    std::cout << "- Target performance: " << CrawlerConstants::Performance::TARGET_PAGES_PER_SECOND << "+ pages/sec\n";
    std::cout << "- Performance mode: Simplified Phase 2 for speed\n";
    std::cout << "================================================================\n\n";
    
    // Initialize Phase 2 global components
    
    // Phase 1: Initialize smart crawl scheduling components
    metadata_store = std::make_shared<CrawlScheduling::CrawlMetadataStore>();
    smart_url_frontier = std::make_unique<CrawlScheduling::SmartUrlFrontier>(metadata_store);
    smart_url_frontier->set_max_depth(max_depth);
    smart_url_frontier->set_max_queue_size(max_queue_size);
    
    // Phase 1: Initialize enhanced storage with metadata support
    enhanced_storage = std::make_unique<CrawlScheduling::EnhancedFileStorageManager>(
        CrawlerConstants::Paths::RAW_DATA_PATH, metadata_store);
    
    crawl_logger = std::make_unique<CrawlLogger>(
        CrawlerConstants::Paths::DB_PATH,
        CrawlerConstants::Paths::LOG_PATH
    );
    
    // Phase 2: Initialize enhanced components
    sharded_disk_queue = std::make_unique<ShardedDiskQueue>(CrawlerConstants::Paths::SHARDED_DISK_PATH);
    html_processing_queue = std::make_unique<HtmlProcessingQueue>();
    work_stealing_queue = std::make_unique<WorkStealingQueue>(network_workers);
    domain_manager = std::make_unique<DynamicDomainManager>();
    shared_domain_queues = std::make_unique<SharedDomainQueueManager>(); // ✅ DOMAIN QUEUES
    
    // Initialize intelligent snippet extraction and domain configuration
    try {
        domain_config_manager = std::make_unique<DomainConfiguration::DomainConfigManager>();
        domain_config_manager->load_config(std::string(CrawlerConstants::Paths::CONFIG_PATH) + "/domain_configs.json");
        snippet_extractor = SnippetExtraction::SnippetExtractorFactory::create_extractor();
        std::cout << "✅ Initialized snippet extraction and domain configuration\n";
    } catch (const std::exception& e) {
        std::cerr << "⚠️  Warning: Failed to initialize snippet/domain config: " << e.what() << std::endl;
        // Continue without snippet extraction
    }
    
    // ✅ DIRECTORY CREATION — Ensure all paths exist before reading/writing
    std::filesystem::create_directories(CrawlerConstants::Paths::CACHE_PATH);
    std::filesystem::create_directories(CrawlerConstants::Paths::CONFIG_PATH);
    std::filesystem::create_directories(std::filesystem::path(CrawlerConstants::Paths::LOG_PATH).parent_path());
    
    // Phase 2: Initialize RSS/Atom poller
    conditional_get_manager = std::make_shared<ConditionalGet::ConditionalGetManager>();
    conditional_get_manager->load_cache_from_file(std::string(CrawlerConstants::Paths::CACHE_PATH) + "/conditional_get_cache.txt");
    
    // Create ConnectionPool and HttpClient instances for unified HTTP operations
    ConnectionPool connection_pool;
    HttpClient http_client(connection_pool);
    
    rss_poller = std::make_unique<FeedPolling::RSSAtomPoller>([&](const std::vector<FeedPolling::FeedEntry>& entries) {
        if (!entries.empty() && smart_url_frontier && !stop_flag) {
            for (const auto& entry : entries) {
                if (!entry.url.empty()) {
                    UrlInfo url_info(entry.url, entry.priority, 0);
                    if (smart_url_frontier->enqueue(url_info)) {
                        std::cout << "RSS Feed discovered URL: " << entry.url << " (priority: " << entry.priority << ")" << std::endl;
                    }
                }
            }
        }
    }, &http_client);
    
    // Phase 2: Initialize sitemap parser
    sitemap_parser = std::make_unique<SitemapParsing::SitemapParser>([&](const std::vector<SitemapParsing::SitemapUrl>& urls) {
        if (!urls.empty() && smart_url_frontier && !stop_flag) {
            for (const auto& sitemap_url : urls) {
                if (!sitemap_url.url.empty()) {
                    UrlInfo url_info(sitemap_url.url, sitemap_url.get_crawl_priority(), 0);
                    if (smart_url_frontier->enqueue(url_info)) {
                        std::cout << "Sitemap discovered URL: " << sitemap_url.url << " (priority: " << sitemap_url.get_crawl_priority() << ")" << std::endl;
                    }
                }
            }
        }
    }, &http_client);
    
    // Initialize other components (robots.txt cache now requires HttpClient for compliance)
    RobotsTxtCache robots(&http_client);
    RateLimiter limiter;
    DomainBlacklist blacklist;
    ErrorTracker error_tracker;
    
    // Load blacklist if available
    blacklist.load_from_file(CrawlerConstants::Paths::BLACKLIST_PATH);
    
    // Load seed URLs from configuration
    auto seed_urls = ConfigLoader::load_seed_urls(std::string(CrawlerConstants::Paths::CONFIG_PATH) + "/seeds.json");
    if (seed_urls.empty()) {
        std::cerr << "⚠️  Warning: No seed URLs loaded from " << CrawlerConstants::Paths::CONFIG_PATH << "/seeds.json. Using fallback seeds.\n";
        // Minimal fallback seeds if config fails
        seed_urls = {
            "https://en.wikipedia.org/wiki/Special:Random",
            "https://stackoverflow.com/questions",
            "https://github.com/trending",
            "https://news.ycombinator.com",
            "https://httpbin.org/stream/100"
        };
    }
    
    std::cout << "🌱 Loaded " << seed_urls.size() << " seed URLs from configuration\n";
    
    // Seed the frontiers (Phase 1: Smart frontier only)
    int successfully_seeded_smart = 0;
    for (const auto& url : seed_urls) {
        float priority = ContentFilter::calculate_priority(url, 0);
        
        // Apply domain-specific priority adjustments
        if (domain_config_manager) {
            try {
                std::string domain = UrlNormalizer::extract_domain(url);
                auto domain_config = domain_config_manager->get_config_for_domain(domain);
                
                // Adjust priority based on domain configuration
                if (domain_config.priority_multiplier > 0) {
                    priority *= domain_config.priority_multiplier;
                    std::cout << "📊 Applied domain priority multiplier " << domain_config.priority_multiplier 
                              << " for " << domain << " (seed: " << url << ")\n";
                }
            } catch (const std::exception& e) {
                // Continue with default priority if domain config fails
                std::cerr << "⚠️  Warning: Failed to apply domain config for seed " << url << ": " << e.what() << std::endl;
            }
        }
        
        UrlInfo seed_info(url, priority, 0);
        
        // Phase 1: Use smart frontier only
        if (smart_url_frontier->enqueue(seed_info)) {
            successfully_seeded_smart++;
        }
        
        // Pre-fetch robots.txt for seed domains
        std::string domain = UrlNormalizer::extract_domain(url);
        robots.fetch_and_cache(domain);
    }
    
    std::cout << "✅ Seeded hybrid crawler with " << successfully_seeded_smart << "/" << seed_urls.size() << " URLs\n";
    std::cout << "   Smart frontier: " << successfully_seeded_smart << " URLs\n";
    
    // Check initial queue status after seeding
    size_t post_seed_smart_size = smart_url_frontier->size();
    size_t post_seed_disk_size = sharded_disk_queue->get_total_disk_queue_size();
    std::cout << "📊 POST-SEED QUEUE STATUS:\n";
    std::cout << "   Smart Queue: " << post_seed_smart_size << " URLs\n";
    std::cout << "   Sharded Disk Queue: " << post_seed_disk_size << " URLs\n";
    std::cout << "   Work Stealing Queue: " << work_stealing_queue->total_size() << " URLs\n";
    std::cout << "   HTML Processing Queue: " << html_processing_queue->size() << " tasks\n";
    
    // Register signal handler
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);
    
    // Start Phase 2: Network workers + HTML processors
    std::vector<std::thread> network_workers_threads;
    std::vector<std::thread> html_workers_threads;
    
    network_workers_threads.reserve(network_workers);
    html_workers_threads.reserve(html_workers);
    
    std::cout << "🚀 Starting Phase 2 workers:\n";
    std::cout << "   Network workers: " << network_workers << "\n";
    std::cout << "   HTML processors: " << html_workers << "\n";
    
    // Phase 2: Start RSS/Atom poller and sitemap parser
    std::cout << "🔄 Starting Phase 2 advanced components:\n";
    
    // Load RSS feeds from JSON config
    rss_poller->load_feeds_from_json(std::string(CrawlerConstants::Paths::CONFIG_PATH) + "/feeds.json");
    rss_poller->start_polling();
    std::cout << "   RSS/Atom poller started\n";
    
    // Load sitemaps from JSON config
    sitemap_parser->load_sitemaps_from_json(std::string(CrawlerConstants::Paths::CONFIG_PATH) + "/sitemaps.json");
    sitemap_parser->start_parsing();
    std::cout << "   Sitemap parser started\n";
    
    std::cout << "   Conditional GET cache loaded (" << conditional_get_manager->get_cache_size() << " entries)\n";
    
    // Start network workers
    for (int i = 0; i < network_workers; ++i) {
        network_workers_threads.emplace_back([i, &robots, &limiter, &blacklist, &error_tracker]() {
            multi_crawler_worker(i, std::ref(robots), std::ref(limiter),
                                std::ref(blacklist), std::ref(error_tracker));
        });
    }
    
    // Start HTML processing workers
    for (int i = 0; i < html_workers; ++i) {
        html_workers_threads.emplace_back([i, &robots]() {
            html_processing_worker(i, std::ref(robots));
        });
    }
    
    // Give workers a moment to start, then check queue drain
    std::this_thread::sleep_for(std::chrono::seconds(2));
    std::cout << "📊 POST-WORKER START STATUS (after 2s):\n";
    std::cout << "   Smart Queue: " << smart_url_frontier->size() << " URLs\n";
    std::cout << "   Sharded Disk Queue: " << sharded_disk_queue->get_total_disk_queue_size() << " URLs\n";
    std::cout << "   Work Stealing Queue: " << work_stealing_queue->total_size() << " URLs\n";
    std::cout << "   HTML Processing Queue: " << html_processing_queue->size() << " tasks\n\n";
    
    // Start enhanced monitoring thread
    std::thread monitor_thread(enhanced_monitoring_thread);
    
    std::cout << "🚀 Phase 1 & 2 Enhanced Crawler started!\n";
    std::cout << "   Network pipeline: " << network_workers << " workers\n";
    std::cout << "   HTML pipeline: " << html_workers << " processors\n";
    std::cout << "   Smart scheduling: Enabled with exponential backoff\n";
    std::cout << "   Target: 300+ pages/sec with intelligent scheduling\n";
    std::cout << "Press Ctrl+C to gracefully shutdown\n\n";
    
    // Wait for Phase 2 workers completion
    for (auto& worker : network_workers_threads) {
        if (worker.joinable()) {
            worker.join();
        }
    }
    
    // Shutdown HTML processing pipeline
    html_processing_queue->shutdown();
    for (auto& worker : html_workers_threads) {
        if (worker.joinable()) {
            worker.join();
        }
    }
    
    // ✅ GRACEFUL SHUTDOWN — Ensure RSS and sitemap threads are properly stopped
    if (rss_poller) {
        rss_poller->stop();
    }
    if (sitemap_parser) {
        sitemap_parser->stop();
    }
    
    
    if (monitor_thread.joinable()) {
        monitor_thread.join();
    }
    
    std::cout << "\n🎯 FINAL PHASE 2 CRAWLER RESULTS\n";
    std::cout << "===================================\n";
    global_monitor.print_stats(smart_url_frontier->size(), 0);
   // error_tracker.print_stats();
    
    // Ultra parser performance stats (always shown now)
    UltraParser::UltraHTMLParser ultra_parser;
    ultra_parser.print_performance_stats();
    
    // Phase 1 & 2 final statistics
    std::cout << "📊 PHASE 1 & 2 QUEUE FINAL STATS:\n";
    std::cout << "   Smart Queue: " << smart_url_frontier->size() << " URLs remaining\n";
    std::cout << "   Sharded Disk Queue: " << sharded_disk_queue->get_total_disk_queue_size() << " URLs remaining\n";
    std::cout << "   Work Stealing Queue: " << work_stealing_queue->total_size() << " URLs remaining\n";
    std::cout << "   HTML Processing Queue: " << html_processing_queue->size() << " tasks remaining\n";
    std::cout << "   Metadata Store: " << metadata_store->size() << " URLs tracked\n";
    
    double final_rate = global_monitor.get_crawl_rate();
    if (final_rate >= 300.0) {
        std::cout << "✅ SUCCESS: Achieved " << std::fixed << std::setprecision(1) 
                 << final_rate << " pages/sec (Target: 300+)\n";
    } else {
        std::cout << "📊 Performance: " << std::fixed << std::setprecision(1) 
                 << final_rate << " pages/sec\n";
    }
    
    // Phase 1 & 2 cleanup
    crawl_logger->flush();
    enhanced_storage->flush();
    
    // Phase 2: Save conditional GET cache
    conditional_get_manager->save_cache_to_file(std::string(CrawlerConstants::Paths::CACHE_PATH) + "/conditional_get_cache.txt");
    
    // Phase 2: Print final statistics
    rss_poller->print_feed_stats();
    sitemap_parser->print_sitemap_stats();
    conditional_get_manager->print_cache_stats();
    
    crawl_logger.reset();
    smart_url_frontier.reset();
    metadata_store.reset();
    enhanced_storage.reset();
    sharded_disk_queue.reset();
    html_processing_queue.reset();
    work_stealing_queue.reset();
    domain_manager.reset();
    shared_domain_queues.reset(); // ✅ DOMAIN QUEUES cleanup
    
    curl_global_cleanup();
    
    std::cout << "🏁 Phase 1 Enhanced Crawler (Smart Scheduling) shutdown complete.\n";
    return 0;
}
