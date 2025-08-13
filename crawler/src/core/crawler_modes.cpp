#include "crawler_modes.h"
#include "crawler_workers.h"
#include "crawler_core.h"
#include "crawler_monitoring.h"
#include "time_utils.h"
#include <iostream>
#include <thread>
#include <vector>
#include <signal.h>
#include <filesystem>
#include <chrono>
#include "tracy/Tracy.hpp"

/**
 * REGULAR mode: Deep, quality crawl with seed URLs and sitemaps
 */
void run_regular_mode(int max_threads, int max_depth, int max_queue_size, int max_runtime_minutes) {
    
    std::cout << "📚 Starting in REGULAR mode (deep, high-quality crawl).\n";
    
    // Initialize cURL globally
    curl_global_init(CURL_GLOBAL_DEFAULT);
    
    ContentFilter::initialize(CrawlerConstants::Paths::CONFIG_PATH);
    
    int network_workers = max_threads;
    int html_workers = std::max(1, max_threads / CrawlerConstants::Workers::HTML_WORKER_RATIO);
    ConnectionPool connection_pool(CrawlerConstants::Network::MAX_CONNECTIONS * network_workers);
    HttpClient http_client(connection_pool);

    std::cout << "Configuration - Regular Mode:\n";
    std::cout << "- Network workers: " << network_workers << "\n";
    std::cout << "- HTML processors: " << html_workers << " (reduced for performance)\n";
    std::cout << "- Max crawl depth: " << max_depth << "\n";
    std::cout << "- Max queue size: " << max_queue_size << "\n";
    
    // Initialize components for regular mode
    initialize_regular_mode_components(max_depth, max_queue_size);
    
    // Initialize other components
    RobotsTxtCache robots(CrawlerConstants::Paths::ROBOTS_TXT_CACHE_PATH);
    RateLimiter limiter(CrawlerConstants::Paths::ROCKSDB_RATE_LIMITER_PATH);
    DomainBlacklist blacklist;
    ErrorTracker error_tracker;
    

    
    // Load seed URLs from configuration
    auto seed_urls = ConfigLoader::load_seed_urls(std::string(CrawlerConstants::Paths::CONFIG_PATH) + "/seeds.json");
    if (seed_urls.empty()) {
        std::cerr << "⚠️  Warning: No seed URLs loaded from " << CrawlerConstants::Paths::CONFIG_PATH << "/seeds.json. Using fallback seeds.\n";
        seed_urls = {
            "https://en.wikipedia.org/wiki/Special:Random",
            "https://stackoverflow.com/questions",
            "https://github.com/trending",
            "https://news.ycombinator.com",
            "https://httpbin.org/stream/100"
        };
    }

    // std::cout << "🌱 Loaded " << seed_urls.size() << " seed URLs from configuration\n";

    // Seed the frontiers
    int successfully_seeded_smart = 0;
    for (const auto& url : seed_urls) {
        float priority = ContentFilter::calculate_priority(url, 0);
        
        if (domain_config_manager) {
            try {
                std::string domain = UrlNormalizer::extract_domain(url);
                auto domain_config = domain_config_manager->get_config_for_domain(domain);
                if (domain_config.priority_multiplier > 0) {
                    priority *= domain_config.priority_multiplier;
                    // std::cout << "📊 Applied domain priority multiplier " << domain_config.priority_multiplier 
                    //           << " for " << domain << " (seed: " << url << ")\n";
                }
            } catch (const std::exception& e) {
                std::cerr << "⚠️  Warning: Failed to apply domain config for seed " << url << ": " << e.what() << std::endl;
            }
        }
        
        UrlInfo seed_info(url, priority, 0);
        if (smart_url_frontier->enqueue(seed_info)) {
            successfully_seeded_smart++;
        }
    }

    std::cout << "✅ Seeded hybrid crawler with " << successfully_seeded_smart << "/" << seed_urls.size() << " URLs\n";
    std::cout << "   Smart frontier: " << successfully_seeded_smart << " URLs\n";

    // Setup RSS poller and sitemap parser
    setup_rss_poller(CrawlerMode::REGULAR, &http_client, network_workers);
    setup_sitemap_parser(&http_client, &robots);
    
    // Add domains to monitor for sitemap discovery from seed URLs
    std::vector<std::string> domains_to_monitor;
    for (const auto& url : seed_urls) {
        try {
            std::string domain = UrlNormalizer::extract_domain(url);
            if (std::find(domains_to_monitor.begin(), domains_to_monitor.end(), domain) == domains_to_monitor.end()) {
                domains_to_monitor.push_back(domain);
            }
        } catch (const std::exception& e) {
            std::cerr << "⚠️  Warning: Failed to extract domain from seed " << url << ": " << e.what() << std::endl;
        }
    }
    
    if (!domains_to_monitor.empty()) {
        sitemap_parser->add_domains_to_monitor(domains_to_monitor);
        std::cout << "   Monitoring " << domains_to_monitor.size() << " domains for sitemap discovery\n";
    }
    
    sitemap_parser->start_parsing();
    std::cout << "   Sitemap parser started\n";

    // Start worker threads
    std::vector<std::thread> network_workers_threads;
    std::vector<std::thread> html_workers_threads;
    
    start_worker_threads(network_workers, html_workers, CrawlerMode::REGULAR,
                        robots, limiter, blacklist, error_tracker, connection_pool,
                        network_workers_threads, html_workers_threads);
    
    // Start enhanced monitoring thread
        std::thread monitor_thread([]() { enhanced_monitoring_thread(CrawlerMode::REGULAR); });
    
    

    // Max Runtime Logic for Regular Mode
    if (max_runtime_minutes > 0) {
        std::cout << "⏰ Crawler will run for a maximum of " << max_runtime_minutes << " minutes." << std::endl;
        auto start_time = std::chrono::steady_clock::now();
        std::thread([start_time, max_runtime_minutes]() {
            while (!stop_flag) {
                auto now = std::chrono::steady_clock::now();
                auto elapsed = std::chrono::duration_cast<std::chrono::minutes>(now - start_time).count();
                if (elapsed >= max_runtime_minutes) {
                    std::cout << "🏁 Maximum runtime of " << max_runtime_minutes << " minutes reached. Triggering graceful shutdown." << std::endl;
                    stop_flag = true;
                    break;
                }
                std::this_thread::sleep_for(std::chrono::seconds(CrawlerConstants::Monitoring::GRACE_PERIOD_SECONDS));
            }
        }).detach();
    }
    
    // 1. Signal all workers to stop (stop_flag is already set by signal handler or timeout)
    // 🛡️ NEW COORDINATED SHUTDOWN SEQUENCE
    // Wait for monitoring thread to complete shutdown coordination
    if (monitor_thread.joinable()) {
        monitor_thread.join();
    }
    
    // 2. Wait for all worker threads to finish (coordinated shutdown handles this)
    std::cout << "⏳ Waiting for network workers to finish..." << std::endl;
    for (auto& worker : network_workers_threads) {
        if (worker.joinable()) {
            worker.join();
        }
    }

    std::cout << "⏳ Waiting for HTML workers to finish..." << std::endl;
    for (auto& worker : html_workers_threads) {
        if (worker.joinable()) {
            worker.join();
        }
    }

    // 3. Gather final statistics BEFORE cleanup
    std::cout << "\n🎯 FINAL REGULAR MODE RESULTS\n";
    std::cout << "===================================\n";
    global_monitor.print_stats(smart_url_frontier ? smart_url_frontier->size() : 0, 0);
    
    UltraParser::UltraHTMLParser ultra_parser;
    ultra_parser.print_performance_stats();
    
    std::cout << "📊 FINAL QUEUE STATS:\n";
    std::cout << "   Smart Queue: " << (smart_url_frontier ? smart_url_frontier->size() : 0) << " URLs remaining\n";
    std::cout << "   Sharded Disk Queue: " << (sharded_disk_queue ? sharded_disk_queue->get_total_disk_queue_size() : 0) << " URLs remaining\n";
    std::cout << "   Work Stealing Queue: " << (work_stealing_queue ? work_stealing_queue->total_size() : 0) << " URLs remaining\n";
    std::cout << "   HTML Processing Queue: " << (html_processing_queue ? html_processing_queue->size() : 0) << " tasks remaining\n";
    std::cout << "   Metadata Store: " << (metadata_store ? metadata_store->size() : 0) << " URLs tracked\n";
    
    double final_rate = global_monitor.get_crawl_rate();
    std::cout << "📊 Performance: " << std::fixed << std::setprecision(1) 
             << final_rate << " pages/sec\n";
    
    // Print component stats before cleanup
    if (rss_poller) rss_poller->print_feed_stats();
    if (sitemap_parser) sitemap_parser->print_sitemap_stats();
    if (conditional_get_manager) conditional_get_manager->print_cache_stats();
    
    // 4. Now safely clean up all components
    std::cout << "🧹 Performing safe component cleanup..." << std::endl;
    cleanup_components_safely();
    
    // Note: cleanup_components_safely() was already called above
    std::cout << "🏁 Regular mode crawler shutdown complete.\n";
}

// Call curl_global_cleanup() at the very end, after all run mode functions return
void shutdown_curl_global() {
    curl_global_cleanup();
}

/**
 * FRESH mode: 24/7 real-time polling of RSS/Atom feeds
 */
void run_fresh_mode(int max_runtime_minutes) {
    std::cout << "🔥 Starting in FRESH mode (24/7 real-time polling).\n";
    
    // Initialize cURL globally
    curl_global_init(CURL_GLOBAL_DEFAULT);
    
    ContentFilter::initialize(CrawlerConstants::Paths::CONFIG_PATH);
    
    int network_workers = CrawlerConstants::FreshMode::NETWORK_WORKERS;
    int html_workers = CrawlerConstants::FreshMode::HTML_WORKERS;
    ConnectionPool connection_pool(CrawlerConstants::Network::MAX_CONNECTIONS * network_workers);
    HttpClient http_client(connection_pool);

    std::cout << "Configuration - Fresh Mode:\n";
    std::cout << "- Network workers: " << network_workers << "\n";
    std::cout << "- HTML processors: " << html_workers << "\n";
    std::cout << "- Max crawl depth: 2 (shallow for fresh content)\n";
    std::cout << "- Max queue size: 5000 (smaller for fresh mode)\n";
    std::cout << "- RSS poll interval: " << CrawlerConstants::FreshMode::RSS_POLL_INTERVAL_SECONDS << " seconds\n";
    std::cout << "- Mode: 24/7 continuous operation\n";
    std::cout << "================================================================\n\n";
    
    // Initialize components for fresh mode
    initialize_fresh_mode_components();
    
    // Initialize other components
    RobotsTxtCache robots(CrawlerConstants::Paths::ROBOTS_TXT_CACHE_PATH);
    RateLimiter limiter(CrawlerConstants::Paths::ROCKSDB_RATE_LIMITER_PATH);
    DomainBlacklist blacklist;
    ErrorTracker error_tracker;
    

    
    std::cout << "🚫 Skipping seed URLs and sitemaps in FRESH mode.\n";
    
    // Setup RSS poller (but not sitemap parser for fresh mode)
    setup_rss_poller(CrawlerMode::FRESH, &http_client, network_workers);
    
    // Start worker threads
    std::vector<std::thread> network_workers_threads;
    std::vector<std::thread> html_workers_threads;
    
    start_worker_threads(network_workers, html_workers, CrawlerMode::FRESH,
                        robots, limiter, blacklist, error_tracker, connection_pool,
                        network_workers_threads, html_workers_threads);
    
    // Start enhanced monitoring thread
    std::thread monitor_thread([]() { enhanced_monitoring_thread(CrawlerMode::FRESH); });
    
    // Fresh mode runs indefinitely unless max_runtime_minutes is set
    if (max_runtime_minutes > 0) {
        std::cout << "⏰ Fresh mode will run for a maximum of " << max_runtime_minutes << " minutes." << std::endl;
        auto start_time = std::chrono::steady_clock::now();
        std::thread([start_time, max_runtime_minutes]() {
            while (!stop_flag) {
                auto now = std::chrono::steady_clock::now();
                auto elapsed = std::chrono::duration_cast<std::chrono::minutes>(now - start_time).count();
                if (elapsed >= max_runtime_minutes) {
                    std::cout << "🏁 Maximum runtime of " << max_runtime_minutes << " minutes reached. Triggering graceful shutdown." << std::endl;
                    stop_flag = true;
                    break;
                }
                std::this_thread::sleep_for(std::chrono::seconds(CrawlerConstants::Monitoring::FRESH_GRACE_PERIOD_SECONDS));
            }
        }).detach();
    } else {
        std::cout << "🔄 Fresh mode running indefinitely (24/7). Use Ctrl+C to stop.\n";
    }
    
    // Wait for worker completion
    for (auto& worker : network_workers_threads) {
        if (worker.joinable()) {
            worker.join();
        }
    }
    
    // 🛡️ NEW COORDINATED SHUTDOWN SEQUENCE FOR FRESH MODE
    // Wait for monitoring thread to complete shutdown coordination
    if (monitor_thread.joinable()) {
        monitor_thread.join();
    }
    
    // Wait for all worker threads to finish
    std::cout << "⏳ Waiting for network workers to finish..." << std::endl;
    for (auto& worker : network_workers_threads) {
        if (worker.joinable()) {
            worker.join();
        }
    }

    std::cout << "⏳ Waiting for HTML workers to finish..." << std::endl;
    for (auto& worker : html_workers_threads) {
        if (worker.joinable()) {
            worker.join();
        }
    }
    
    // Gather final statistics BEFORE cleanup
    std::cout << "\n🎯 FINAL FRESH MODE RESULTS\n";
    std::cout << "===================================\n";
    global_monitor.print_stats(smart_url_frontier ? smart_url_frontier->size() : 0, 0);
    
    std::cout << "📊 FINAL QUEUE STATS:\n";
    std::cout << "   Smart Queue: " << (smart_url_frontier ? smart_url_frontier->size() : 0) << " URLs remaining\n";
    std::cout << "   Work Stealing Queue: " << (work_stealing_queue ? work_stealing_queue->total_size() : 0) << " URLs remaining\n";
    std::cout << "   HTML Processing Queue: " << (html_processing_queue ? html_processing_queue->size() : 0) << " tasks remaining\n";
    std::cout << "   Metadata Store: " << (metadata_store ? metadata_store->size() : 0) << " URLs tracked\n";
    std::cout << "   NOTE: Disk queue disabled in FRESH mode\n";
    
    double final_rate = global_monitor.get_crawl_rate();
    std::cout << "📊 Fresh Mode Performance: " << std::fixed << std::setprecision(1) 
             << final_rate << " pages/sec\n";
    
    // Print component stats before cleanup
    if (rss_poller) rss_poller->print_feed_stats();
    if (conditional_get_manager) conditional_get_manager->print_cache_stats();
    
    // Now safely clean up all components
    std::cout << "🧹 Performing safe component cleanup..." << std::endl;
    cleanup_components_safely();
    
    // Note: cleanup_components_safely() was already called above
    std::cout << "🏁 Fresh mode crawler shutdown complete.\n";
}

// Helper functions implementation

void initialize_regular_mode_components(int max_depth, int max_queue_size) {
    // Initialize Phase 2 global components for regular mode
    
    // Phase 1: Initialize smart crawl scheduling components
    metadata_store = std::make_shared<CrawlScheduling::CrawlMetadataStore>(
        CrawlerConstants::Paths::ROCKSDB_METADATA_PATH
    );
    smart_url_frontier = std::make_unique<CrawlScheduling::SmartUrlFrontier>(metadata_store);
    smart_url_frontier->set_max_depth(max_depth);
    smart_url_frontier->set_max_queue_size(max_queue_size);
    
    // Phase 1: Initialize enhanced storage with local path
    std::cout << "📁 Using local storage for REGULAR mode" << std::endl;
    enhanced_storage = std::make_unique<CrawlScheduling::EnhancedFileStorageManager>(
        CrawlerConstants::Paths::RAW_DATA_PATH, metadata_store);
    std::cout << "📁 Storage path: " << CrawlerConstants::Paths::RAW_DATA_PATH << std::endl;
    
    // Remove crawl_logger initialization - no longer needed
    // crawl_logger = std::make_unique<CrawlLogger>(
    //     CrawlerConstants::Paths::DB_PATH,
    //     CrawlerConstants::Paths::LOG_PATH
    // );
    
    // Phase 2: Initialize enhanced components with size limits for proper disk queue usage
    sharded_disk_queue = std::make_unique<ShardedDiskQueue>(CrawlerConstants::Paths::SHARDED_DISK_PATH);
    html_processing_queue = std::make_unique<HtmlProcessingQueue>();
    
    // Initialize work-stealing queue with size limits to force disk queue usage
    size_t work_queue_per_worker = CrawlerConstants::Queue::MAX_WORK_STEALING_QUEUE_SIZE; // Limit each worker to 500 URLs max
    work_stealing_queue = std::make_unique<WorkStealingQueue>(
        std::min(CrawlerConstants::Workers::DEFAULT_MAX_THREADS, 
                (int)std::thread::hardware_concurrency()), 
        work_queue_per_worker);

    
    shared_domain_queues = std::make_unique<SharedDomainQueueManager>();
    
    std::cout << "📊 Regular Mode Queue Configuration:\n";
    std::cout << "   Smart Queue: max " << max_queue_size << " URLs\n";
    std::cout << "   Work Stealing: max " << work_stealing_queue->get_max_size() << " URLs (" << work_queue_per_worker << " per worker)\n";
    std::cout << "   Disk Queue: unlimited (persistent storage)\n";
    
    // Initialize intelligent  extraction and domain configuration
    try {
        domain_config_manager = std::make_unique<DomainConfiguration::DomainConfigManager>();
        domain_config_manager->load_config(std::string(CrawlerConstants::Paths::CONFIG_PATH) + "/domain_configs.json");
        std::cout << "✅ Initialized  extraction and domain configuration\n";
    } catch (const std::exception& e) {
        std::cerr << "⚠️  Warning: Failed to initialize /domain config: " << e.what() << std::endl;
        // Continue without  extraction
    }
    
    // ✅ DIRECTORY CREATION — Ensure all paths exist before reading/writing
    std::filesystem::create_directories(CrawlerConstants::Paths::CONFIG_PATH);
    std::filesystem::create_directories(std::filesystem::path(CrawlerConstants::Paths::LOG_PATH).parent_path());
    
    // Phase 2: Initialize conditional GET manager
    try {
        conditional_get_manager = std::make_shared<ConditionalGet::ConditionalGetManager>(
            CrawlerConstants::Paths::CONDITIONAL_GET_CACHE_PATH
        );
    } catch (const std::exception& e) {
        std::cerr << "FATAL ERROR during initialization: " << e.what() << std::endl;
        std::exit(1);
    }
}

void initialize_fresh_mode_components() {
    // Initialize Phase 2 global components for fresh mode (lightweight configuration)
    std::cout << "🚀 Initializing FRESH mode components (no disk queue)...\n";
    
    // Phase 1: Initialize smart crawl scheduling components
    metadata_store = std::make_shared<CrawlScheduling::CrawlMetadataStore>(
        CrawlerConstants::Paths::ROCKSDB_METADATA_PATH
    );
    smart_url_frontier = std::make_unique<CrawlScheduling::SmartUrlFrontier>(metadata_store);
    smart_url_frontier->set_max_depth(CrawlerConstants::FreshMode::MAX_CRAWL_DEPTH);
    smart_url_frontier->set_max_queue_size(CrawlerConstants::FreshMode::MAX_QUEUE_SIZE);
    
    // Phase 1: Initialize enhanced storage with local Live path
    std::cout << "📁 Using local storage for FRESH mode" << std::endl;
    enhanced_storage = std::make_unique<CrawlScheduling::EnhancedFileStorageManager>(
        std::string(CrawlerConstants::Paths::RAW_DATA_PATH), metadata_store);
    std::cout << "📁 Live storage path: " << std::string(CrawlerConstants::Paths::RAW_DATA_PATH)  << std::endl;
    
    // Remove crawl_logger initialization - no longer needed for fresh mode
    // crawl_logger = std::make_unique<CrawlLogger>(
    //     CrawlerConstants::Paths::DB_PATH,
    //     CrawlerConstants::Paths::LOG_PATH
    // );
    
    // ❌ NO DISK QUEUE IN FRESH MODE - Only for RSS/Atom fresh content
    // sharded_disk_queue = nullptr; (Skip disk queue initialization)
    
    html_processing_queue = std::make_unique<HtmlProcessingQueue>();
    
    // Initialize work-stealing queue for fresh mode (smaller)
    size_t work_queue_per_worker = CrawlerConstants::FreshMode::FRESH_MODE_MAX_WORK_STEALING_QUEUE_SIZE; // Smaller per-worker queue for fresh mode
    work_stealing_queue = std::make_unique<WorkStealingQueue>(
        CrawlerConstants::FreshMode::NETWORK_WORKERS, work_queue_per_worker);
    
    shared_domain_queues = std::make_unique<SharedDomainQueueManager>();
    
    std::cout << "📊 Fresh Mode Queue Configuration:\n";
    std::cout << "   Smart Queue: max " << CrawlerConstants::FreshMode::MAX_QUEUE_SIZE << " URLs\n";
    std::cout << "   Work Stealing: max " << work_stealing_queue->get_max_size() << " URLs (" << work_queue_per_worker << " per worker)\n";
    std::cout << "   Disk Queue: DISABLED (fresh content only)\n";
    
    // ✅ DIRECTORY CREATION — Ensure all paths exist before reading/writing
    std::filesystem::create_directories(CrawlerConstants::Paths::CONFIG_PATH);
    std::filesystem::create_directories(std::filesystem::path(CrawlerConstants::Paths::LOG_PATH).parent_path());
    
    // Phase 2: Initialize conditional GET manager
    try {
        conditional_get_manager = std::make_shared<ConditionalGet::ConditionalGetManager>(
            CrawlerConstants::Paths::CONDITIONAL_GET_CACHE_PATH
        );
    } catch (const std::exception& e) {
        std::cerr << "FATAL ERROR during initialization: " << e.what() << std::endl;
        std::exit(1);
    }
    
    std::cout << "✅ FRESH mode components initialized (fast startup)\n";
}

void setup_rss_poller(CrawlerMode mode, HttpClient* http_client, int network_workers) {
    rss_poller = std::make_unique<FeedPolling::RSSAtomPoller>([&,mode,network_workers](const std::vector<FeedPolling::FeedEntry>& entries) {
        std::cout << "🔄 RSS Callback triggered with " << entries.size() << " entries" << std::endl;
        
        if (!entries.empty() && !stop_flag) {
            int urls_added = 0;
            for (const auto& entry : entries) {
                if (!entry.url.empty()) {
                    UrlInfo url_info(entry.url, entry.priority, 0);
                    
                    // In FRESH mode, push directly to the work-stealing queue
                    if (mode == CrawlerMode::FRESH) {
                        // Distribute URLs evenly among workers (with safety check for division by zero)
                        if (network_workers <= 0) {
                            std::cerr << "❌ ERROR: network_workers is " << network_workers << ", cannot distribute URLs. Skipping URL: " << entry.url << std::endl;
                            continue;
                        }
                        size_t worker_id = std::hash<std::string>{}(entry.url) % static_cast<size_t>(network_workers);
                        if (work_stealing_queue->push_local(worker_id, url_info)) {
                            urls_added++;
                            std::cout << "✅ FRESH mode: RSS Feed URL added to queue: " << entry.url << " (worker " << worker_id << "/" << network_workers << ")" << std::endl;
                        } else {
                            std::cout << "❌ FRESH mode: Failed to add RSS URL to queue: " << entry.url << " (worker " << worker_id << "/" << network_workers << ")" << std::endl;
                        }
                    } else {
                        // REGULAR mode behavior
                        if (smart_url_frontier && smart_url_frontier->enqueue(url_info)) {
                            urls_added++;
                            // std::cout << "✅ REGULAR mode: RSS Feed URL added to queue: " << entry.url << std::endl;
                        } else {
                            std::cout << "❌ REGULAR mode: Failed to add RSS URL to queue: " << entry.url << std::endl;
                        }
                    }
                } else {
                    std::cout << "⚠️  RSS Entry has empty URL, skipping..." << std::endl;
                }
            }
            std::cout << "📊 RSS Callback summary: Added " << urls_added << "/" << entries.size() << " URLs to queues" << std::endl;
        } else {
            if (entries.empty()) {
                std::cout << "⚠️  RSS Callback called with empty entries list" << std::endl;
            }
            if (stop_flag) {
                std::cout << "⚠️  RSS Callback called but stop_flag is set" << std::endl;
            }
        }
    }, http_client);
    
    // Load RSS feeds from JSON config
    rss_poller->load_feeds_from_json(std::string(CrawlerConstants::Paths::CONFIG_PATH) + "/feeds.json");
    if (mode == CrawlerMode::FRESH) {
        rss_poller->set_poll_interval(CrawlerConstants::FreshMode::RSS_POLL_INTERVAL_SECONDS);
    }
    rss_poller->start_polling();
    std::cout << "   RSS/Atom poller started\n";
}



void setup_sitemap_parser(HttpClient* http_client, RobotsTxtCache* robots_cache) {
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
    }, http_client, robots_cache);
}
void start_worker_threads(int network_workers, int html_workers, CrawlerMode mode,
                         RobotsTxtCache& robots, RateLimiter& limiter,
                         DomainBlacklist& blacklist, ErrorTracker& error_tracker,
                         ConnectionPool& connection_pool,
                         std::vector<std::thread>& network_threads,
                         std::vector<std::thread>& html_threads) {
    
    // Start network workers
    network_threads.reserve(network_workers);
    for (int i = 0; i < network_workers; ++i) {
        network_threads.emplace_back(multi_crawler_worker, i, std::ref(robots), std::ref(limiter),
                                   std::ref(blacklist), std::ref(error_tracker), std::ref(connection_pool), mode);
    }
    
    // Start HTML processing workers
    html_threads.reserve(html_workers);
    for (int i = 0; i < html_workers; ++i) {
        html_threads.emplace_back([i, &robots, mode]() {
            html_processing_worker(i, std::ref(robots), mode);
        });
    }
}
