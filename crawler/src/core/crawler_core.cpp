#include "crawler_core.h"
#include "tracy/Tracy.hpp"

// Global shutdown flag
std::atomic<bool> stop_flag{false};

// Global performance monitor
PerformanceMonitor global_monitor;



// Phase 1: Smart crawl scheduling components
std::shared_ptr<CrawlScheduling::CrawlMetadataStore> metadata_store;
std::unique_ptr<CrawlScheduling::SmartUrlFrontier> smart_url_frontier;
std::unique_ptr<CrawlScheduling::EnhancedFileStorageManager> enhanced_storage;

// Phase 2: Advanced crawling components
std::unique_ptr<FeedPolling::RSSAtomPoller> rss_poller;
std::unique_ptr<SitemapParsing::SitemapParser> sitemap_parser;
std::shared_ptr<ConditionalGet::ConditionalGetManager> conditional_get_manager;

// Intelligent  domain configuration
std::unique_ptr<DomainConfiguration::DomainConfigManager> domain_config_manager;

// Global disk-backed URL manager
std::unique_ptr<ShardedDiskQueue> sharded_disk_queue;

// Global HTML processing pipeline
std::unique_ptr<HtmlProcessingQueue> html_processing_queue;

// Global work stealing queue
std::unique_ptr<WorkStealingQueue> work_stealing_queue;

// Global shared domain queue manager
std::unique_ptr<SharedDomainQueueManager> shared_domain_queues;

// Add new global store for deferred URLs
std::unordered_map<std::string, std::vector<UrlInfo>> g_deferred_urls;
std::mutex g_deferred_urls_mutex;

// Shutdown coordination infrastructure
std::condition_variable shutdown_coordinator_cv;
std::mutex shutdown_coordinator_mutex;

// Write callback for CURL
size_t hybrid_write_callback(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t total_size = size * nmemb;
    static_cast<std::string*>(userp)->append(static_cast<char*>(contents), total_size);
    return total_size;
}

// AdaptiveLinkExtractor implementation
std::vector<std::string> AdaptiveLinkExtractor::extract_links_adaptive(const std::string& html, const std::string& base_url) {
    // Use the ultra parser for maximum speed (300+ pages/sec)
    static thread_local UltraParser::UltraHTMLParser ultra_parser;
    std::vector<std::string> all_links = ultra_parser.extract_links_ultra(html, base_url);
    std::vector<std::string> filtered_links;
    filtered_links.reserve(all_links.size()); 
    if(all_links.empty()) {
        // std::cout<<"no links extracted "<<base_url<<"\n"; // Return empty if no links found
    }
   // Filter and collect all valid links
    for (const auto& link : all_links) {
        if (ContentFilter::is_crawlable_url(link)) {
            filtered_links.push_back(link);
        }
    }

    return filtered_links;
}

int AdaptiveLinkExtractor::process_and_enqueue_links(const std::vector<std::string>& links, 
                                   int current_depth, 
                                   const std::string& referring_domain,
                                   size_t worker_id) {
    ZoneScopedN("Process and Enqueue Links");

    if (links.empty()) {
        return 0;
    }

    std::vector<UrlInfo> url_info_batch;
    url_info_batch.reserve(links.size());
    for (const std::string& link : links) {
        float priority = ContentFilter::calculate_priority(link, current_depth + 1);
        url_info_batch.emplace_back(link, priority, current_depth + 1, referring_domain);
    }

    // FIXED: The batch function returns a vector of the URLs that were NOT enqueued.
    std::vector<UrlInfo> remaining_urls;
    {
        ZoneScopedN("Enqueue Batch Smart Frontier");
        // Pass the batch by value (move) as the function signature now takes it that way
        remaining_urls = smart_url_frontier->enqueue_batch(std::move(url_info_batch));
    }
    
    int successfully_enqueued = links.size() - remaining_urls.size();
    
    std::vector<std::string> disk_urls;
    disk_urls.reserve(remaining_urls.size());

    for (const auto& url_info : remaining_urls) {
        if (work_stealing_queue->push_local(worker_id, url_info)) {
            successfully_enqueued++;
        } else {
            disk_urls.push_back(url_info.url);
        }
    }

    if (!disk_urls.empty() && sharded_disk_queue != nullptr) {
        ZoneScopedN("Save URLs to Disk");
        sharded_disk_queue->save_urls_to_disk(disk_urls);
    }
    
    return successfully_enqueued;
}



// MultiRequestContext implementation
MultiRequestContext::MultiRequestContext(const UrlInfo& info, ConnectionPool* pool) 
    : url_info(info), url(info.url), domain(UrlNormalizer::extract_domain(info.url))
    , start_time(std::chrono::steady_clock::now()), request_headers(nullptr) {
    
    curl_handle = pool->acquire_connection();
    if (!curl_handle) {
        curl_handle = curl_easy_init(); 
    }
    response_data.reserve(1024 * 1024);
    response_headers.reserve(8192);
}

MultiRequestContext::~MultiRequestContext() {
    if (request_headers) {
        curl_slist_free_all(request_headers);
    }
    // Do not cleanup handle; it will be returned to the pool.
}

// SharedDomainQueueManager implementation
bool SharedDomainQueueManager::try_queue_for_domain(const std::string& domain, const UrlInfo& url_info) {
    std::lock_guard<std::mutex> manager_lock(manager_mutex_);
    
    // Safely ensure mutex exists for this domain (idempotent operation)
    if (domain_mutexes_.find(domain) == domain_mutexes_.end()) {
        // Double-check pattern: even if another thread created it between our check and lock,
        // the map insert will be idempotent and safe
        domain_mutexes_.emplace(domain, std::make_unique<std::mutex>());
    }
    
    // Lock the domain-specific mutex
    std::lock_guard<std::mutex> domain_lock(*(domain_mutexes_[domain]));
    
    if (domain_queues_[domain].size() < CrawlerConstants::Queue::DOMAIN_QUEUE_LIMIT) {
        domain_queues_[domain].push(url_info);
        return true;
    }
    return false;
}

bool SharedDomainQueueManager::try_dequeue_from_available_domain(RateLimiter& limiter, UrlInfo& url_info, std::string& out_domain) {
    std::lock_guard<std::mutex> manager_lock(manager_mutex_);
    
    for (auto& [domain, queue] : domain_queues_) {
        if (!queue.empty() && limiter.can_request_now(domain)) {
            // Lock the pointed-to mutex object.
            std::lock_guard<std::mutex> domain_lock(*(domain_mutexes_[domain]));
            if (!queue.empty()) {
                url_info = queue.front();
                queue.pop();
                out_domain = domain;
                return true;
            }
        }
    }
  
    return false;
}

size_t SharedDomainQueueManager::get_total_queued() const {
    std::lock_guard<std::mutex> manager_lock(manager_mutex_);
    size_t total = 0;
    for (const auto& [domain, queue] : domain_queues_) {
        total += queue.size();
    }
    return total;
}


/**
 * 🛡️ Coordinated Shutdown: Wait for all worker threads before cleanup
 */
void coordinated_shutdown() {
    std::cout << "🛑 Beginning coordinated shutdown sequence..." << std::endl;
    
    // Phase 1: Stop feed sources first (no new work)
    std::cout << "⏹️  Stopping RSS/Sitemap feed sources..." << std::endl;
    if (rss_poller) {
        rss_poller->stop();  // Sets shutdown flag, notifies worker
    }
    
    if (sitemap_parser) {
        sitemap_parser->stop();  // Sets shutdown flag, notifies worker
    }
    
    // Phase 2: Signal immediate shutdown to queues
    std::cout << "🚫 Interrupting queue operations..." << std::endl;
    if (html_processing_queue) {
        html_processing_queue->interrupt_waits();
    }
    
    std::cout << "✅ Feed sources stopped, ready for worker termination" << std::endl;
}

/**
 * 🧹 Safe Component Cleanup: Only called after all workers terminated
 */
void cleanup_components_safely() {
    std::cout << "🧹 Beginning component cleanup..." << std::endl;
    
    // 1. Clean up feed sources (no dependencies)
    if (rss_poller) {
        rss_poller->stop();  // Explicit stop before reset
        rss_poller.reset();
        std::cout << "✅ RSS poller cleaned up" << std::endl;
    }
    
    if (sitemap_parser) {
        sitemap_parser->stop();  // Explicit stop before reset
        sitemap_parser.reset();
        std::cout << "✅ Sitemap parser cleaned up" << std::endl;
    }
    
    // 2. Clean up queues (no more workers accessing them)
    if (html_processing_queue) {
        html_processing_queue.reset();
        std::cout << "✅ HTML processing queue cleaned up" << std::endl;
    }
    
    if (work_stealing_queue) {
        work_stealing_queue.reset();
        std::cout << "✅ Work stealing queue cleaned up" << std::endl;
    }
    
    if (shared_domain_queues) {
        shared_domain_queues.reset();
        std::cout << "✅ Shared domain queues cleaned up" << std::endl;
    }
    
    // 3. Flush and clean storage (critical data safety)
    if (enhanced_storage) {
        std::cout << "💾 Flushing storage buffers..." << std::endl;
        enhanced_storage->flush();
        enhanced_storage.reset();
        std::cout << "✅ Enhanced storage cleaned up" << std::endl;
    }
    
    if (sharded_disk_queue) {
        sharded_disk_queue.reset();
        std::cout << "✅ Sharded disk queue cleaned up" << std::endl;
    }
    
    // 4. Clean up URL management
    if (smart_url_frontier) {
        smart_url_frontier.reset();
        std::cout << "✅ Smart URL frontier cleaned up" << std::endl;
    }
    
    if (metadata_store) {
        metadata_store.reset();
        std::cout << "✅ Metadata store cleaned up" << std::endl;
    }
    
    // 5. Clean up databases
    if (conditional_get_manager) {
        conditional_get_manager.reset();
        std::cout << "✅ Conditional GET manager cleaned up" << std::endl;
    }
    
    if (domain_config_manager) {
        domain_config_manager.reset();
        std::cout << "✅ Domain config manager cleaned up" << std::endl;
    }
    
    // 7. Clear shared data
    {
        std::lock_guard<std::mutex> lock(g_deferred_urls_mutex);
        g_deferred_urls.clear();
    }
    
    std::cout << "✅ All components cleaned up safely" << std::endl;
}
