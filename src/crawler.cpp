#include "utils.h"
#include "concurrentqueue.h"
#include <curl/curl.h>
#include <gumbo.h>
#include <fstream>
#include <atomic>
#include <thread>
#include <csignal>
#include <iostream>
#include <mutex>
#include <stack>
#include <bloom_filter.hpp>
#include <filesystem>
#include <unordered_set>
#include <queue>
#include <sstream>
#include <algorithm>

// Global mutex for thread-safe logging
std::mutex log_mutex;

// Separate mutex for bloom filter operations to reduce contention
std::mutex bloom_mutex;

// Concurrent queue for URL management
moodycamel::ConcurrentQueue<std::pair<std::string, float>> url_queue;  // Changed to store URL + priority

// Global shutdown flag
std::atomic<bool> stop_flag{false};

// Performance metrics
std::atomic<long> total_pages_processed{0};
std::atomic<long> total_links_discovered{0};
std::atomic<long> total_network_errors{0};

// Global domain blacklist
DomainBlacklist global_blacklist;

/**
 * cURL write callback function
 */
static size_t write_callback(char* ptr, size_t size, size_t nmemb, void* userdata) {
    ((std::string*)userdata)->append(ptr, size * nmemb);
    return size * nmemb;
}

// Additional performance optimization - Connection pooling
class ConnectionPool {
private:
    std::queue<CURL*> available_connections;
    std::mutex pool_mutex;
    const size_t max_connections = 50;
    
public:
    ConnectionPool() {
        // Pre-create connections
        for (size_t i = 0; i < max_connections; ++i) {
            CURL* curl = curl_easy_init();
            if (curl) {
                // Set common options
                curl_easy_setopt(curl, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_1_1);
                curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
                curl_easy_setopt(curl, CURLOPT_USERAGENT, "MyCrawler/1.0");
                curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
                curl_easy_setopt(curl, CURLOPT_TIMEOUT, 6L);
                curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 3L);
                curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
                curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
                curl_easy_setopt(curl, CURLOPT_TCP_NODELAY, 1L);
                curl_easy_setopt(curl, CURLOPT_ACCEPT_ENCODING, "gzip,deflate");
                curl_easy_setopt(curl, CURLOPT_BUFFERSIZE, 65536L);
                curl_easy_setopt(curl, CURLOPT_DNS_CACHE_TIMEOUT, 600L);
                available_connections.push(curl);
            }
        }
    }
    
    CURL* get_connection() {
        std::lock_guard<std::mutex> lock(pool_mutex);
        if (!available_connections.empty()) {
            CURL* curl = available_connections.front();
            available_connections.pop();
            return curl;
        }
        return nullptr;
    }
    
    void return_connection(CURL* curl) {
        if (curl) {
            // Reset connection for reuse
            curl_easy_reset(curl);
            std::lock_guard<std::mutex> lock(pool_mutex);
            available_connections.push(curl);
        }
    }
    
    ~ConnectionPool() {
        while (!available_connections.empty()) {
            curl_easy_cleanup(available_connections.front());
            available_connections.pop();
        }
    }
};

// Global connection pool
ConnectionPool global_connection_pool;

/**
 * HTML link extractor using iterative DFS - optimized version
 */
void extract_links_fast(GumboNode* root, std::vector<std::string>& links) {
    if (root->type != GUMBO_NODE_ELEMENT) return;
    
    // Fast path for <a> tags
    if (root->v.element.tag == GUMBO_TAG_A) {
        if (GumboAttribute* href = gumbo_get_attribute(&root->v.element.attributes, "href")) {
            links.push_back(href->value);
        }
        return;
    }
    
    // Process child nodes
    GumboVector* children = &root->v.element.children;
    for (unsigned int i = 0; i < children->length; ++i) {
        GumboNode* child = static_cast<GumboNode*>(children->data[i]);
        if (child->type == GUMBO_NODE_ELEMENT) {
            extract_links_fast(child, links);
        }
    }
}

/**
 * Calculate URL priority score
 */
float url_priority(const std::string& url) {
    // Higher priority for known important domains
    if (url.find("wikipedia.org") != std::string::npos) return 1.0f;
    if (url.find("nytimes.com") != std::string::npos) return 0.9f;
    if (url.find("github.com") != std::string::npos) return 0.9f;
    if (url.find("stackoverflow.com") != std::string::npos) return 0.9f;
    if (url.find("bbc.com") != std::string::npos) return 0.8f;
    if (url.find("cnn.com") != std::string::npos) return 0.8f;
    
    // Higher priority for shorter URLs (often more important)
    if (url.length() < 60) return 0.7f;
    
    // Default priority
    return 0.5f;
}

/**
 * Queue management function - optimized for high-speed crawling
 */
void manage_queue_size() {
    static auto last_trim = std::chrono::steady_clock::now();
    auto now = std::chrono::steady_clock::now();
    
    // Check every 60 seconds (less frequent)
    if (std::chrono::duration_cast<std::chrono::seconds>(now - last_trim).count() > 60) {
        size_t queue_size = url_queue.size_approx();
        
        // Allow much larger queues before trimming (2M URLs)
        if (queue_size > 2000000) {
            std::cout << "Queue very large (" << queue_size << "), trimming...\n";
            std::pair<std::string, float> dummy_pair;
            int drained = 0;
            
            // Drain only a small percentage
            while (url_queue.try_dequeue(dummy_pair) && drained < 100000) {
                drained++;
            }
            std::cout << "Drained " << drained << " URLs from queue\n";
        }
        
        last_trim = now;
    }
}

/**
 * Worker thread function for crawling - optimized version
 */
void crawl_worker(std::atomic<bool>& stop_flag, RobotsTxtCache& robots, RateLimiter& limiter, 
                  bloom_filter& url_filter, std::atomic<int>& active_threads,
                  DomainBlacklist& blacklist, ErrorTracker& error_tracker) {
    // Thread-local resources
    thread_local CURL* curl = curl_easy_init();
    thread_local std::unordered_set<std::string> local_seen_urls;
    thread_local std::vector<std::pair<std::string, std::string>> file_batch;
    thread_local GumboOutput* output = nullptr;
    
    // Track that this worker is active
    active_threads++;
    
    if (!curl) {
        log_error("cURL initialization failed");
        active_threads--;
        return;
    }

    // Optimized cURL settings
    curl_easy_setopt(curl, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_1_1);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "MyCrawler/1.0");
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 8L); // Increased timeout
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 4L); // Increased connect timeout
    curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    curl_easy_setopt(curl, CURLOPT_TCP_NODELAY, 1L);
    curl_easy_setopt(curl, CURLOPT_ACCEPT_ENCODING, "gzip,deflate");
    curl_easy_setopt(curl, CURLOPT_BUFFERSIZE, 102400L);
    curl_easy_setopt(curl, CURLOPT_LOW_SPEED_LIMIT, 10240);
    curl_easy_setopt(curl, CURLOPT_LOW_SPEED_TIME, 3L);
    curl_easy_setopt(curl, CURLOPT_DNS_CACHE_TIMEOUT, 300L);

    // Performance tracking
    auto start_time = std::chrono::steady_clock::now();
    int pages_processed = 0;
    std::string html;
    std::vector<std::string> new_urls;
    
    // Wait for main thread to start
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    while (!stop_flag) {
        std::pair<std::string, float> url_priority_pair;
        static thread_local int empty_count = 0;
        
        // Get next URL from queue
        if (!url_queue.try_dequeue(url_priority_pair)) {
            // Reduced sleep time for better responsiveness
            empty_count = std::min(empty_count + 1, 5);
            std::this_thread::sleep_for(std::chrono::milliseconds(2 * empty_count));
            continue;
        }
        empty_count = 0;

        std::string url = url_priority_pair.first;

        // 1. Check if domain is blacklisted
        std::string domain = extract_domain(url);
        if (blacklist.is_blacklisted(domain)) {
            continue;  // Skip blacklisted domains
        }
        
        // 2. Apply rate limiting
        limiter.wait_for_domain(domain);
        
        // 3. Fetch page content
        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &html);
        CURLcode res = curl_easy_perform(curl);
        
        // 4. Process response
        if (res == CURLE_OK) {
            long http_code = 0;
            curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
            
            if (http_code == 200 && !html.empty() && html.size() > 100 && html.size() < 10*1024*1024) {
                pages_processed++;
                total_pages_processed++;
                
                // Save HTML to file (batched)
                file_batch.push_back({url, html});
                if (file_batch.size() >= 50) {  // Increased batch size for better I/O performance
                    save_batch_as_json(file_batch, "../data/raw");
                    file_batch.clear();
                }
                
                // Parse HTML and extract links only for HTML content
                if (html.find("</html>") != std::string::npos || 
                    html.find("<html") != std::string::npos) {
                    if (output) gumbo_destroy_output(&kGumboDefaultOptions, output);
                    output = gumbo_parse(html.c_str());
                    
                    if (output && output->root) {
                        new_urls.clear();
                        extract_links_fast(output->root, new_urls);
                        
                        // Process and deduplicate found URLs
                        std::vector<std::pair<std::string, float>> new_links;
                        for (const auto& link : canonicalize_urls(url, new_urls)) {
                            // Filter out non-useful URLs
                            if (!is_useful_url(link)) continue;
                            
                            if (link.find("http") == 0) {
                                // First check thread-local cache
                                if (local_seen_urls.find(link) == local_seen_urls.end()) {
                                    local_seen_urls.insert(link);
                                    
                                    // Then check global bloom filter
                                    bool is_new = false;
                                    {
                                        std::lock_guard<std::mutex> lock(bloom_mutex);
                                        if (!url_filter.contains(link)) {
                                            url_filter.insert(link);
                                            is_new = true;
                                        }
                                    }
                                    
                                    if (is_new) {
                                        float priority = url_priority(link);
                                        new_links.push_back({link, priority});
                                        total_links_discovered++;
                                    }
                                }
                            }
                        }
                        
                        // Enqueue new links with priority filtering
                        const size_t queue_size = url_queue.size_approx();
                        for (const auto& link_pair : new_links) {
                            if (queue_size < 500000) {
                                url_queue.enqueue(link_pair);
                            } else {
                                // Apply priority filtering when queue is full
                                if (link_pair.second > 0.7f) {
                                    url_queue.enqueue(link_pair);
                                }
                            }
                        }
                    }
                }
            }
        } else {
            // Handle errors
            total_network_errors++;
            error_tracker.record_error(domain, res);
            
            // Blacklist domains with repeated timeouts
            if (res == CURLE_OPERATION_TIMEDOUT) {
                static thread_local std::unordered_map<std::string, int> timeout_counts;
                if (++timeout_counts[domain] > 3) {
                    blacklist.add(domain);
                    timeout_counts[domain] = 0;
                }
            }
            
            std::lock_guard<std::mutex> lock(log_mutex);
            log_error(std::string(curl_easy_strerror(res)) + ": " + url);
        }
        
        html.clear();
        
        // Clear thread-local cache periodically
        if (pages_processed % 100 == 0) {
            local_seen_urls.clear();
        }
        
        // Calculate and display crawl rate
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - start_time).count();
        
        if (elapsed >= 10) {
            double pages_per_sec = pages_processed / static_cast<double>(elapsed);
            if (pages_per_sec > 0) {
                std::lock_guard<std::mutex> lock(log_mutex);
                std::cout << "Crawl rate: " << pages_per_sec << " pages/sec (worker) "
                          << " | Total: " << total_pages_processed
                          << " | Queue: " << url_queue.size_approx()
                          << " | Errors: " << total_network_errors << "\n";
            }
            start_time = now;
            pages_processed = 0;
        }
    }
    
    // Save any remaining batch
    if (!file_batch.empty()) {
        save_batch_as_json(file_batch, "../data/raw");
    }
    
    // Cleanup
    if (output) gumbo_destroy_output(&kGumboDefaultOptions, output);
    curl_easy_cleanup(curl);
    active_threads--;
}

/**
 * High-performance worker thread with async operations
 */
void crawl_worker_async(std::atomic<bool>& stop_flag, RobotsTxtCache& robots, RateLimiter& limiter, 
                       bloom_filter& url_filter, std::atomic<int>& active_threads,
                       DomainBlacklist& blacklist, ErrorTracker& error_tracker) {
    
    // Thread-local batch processing
    thread_local std::unordered_set<std::string> local_seen_urls;
    thread_local std::vector<std::pair<std::string, std::string>> file_batch;
    thread_local std::vector<std::string> url_batch;
    
    active_threads++;
    
    // Connection pooling with fallback
    CURL* curl = global_connection_pool.get_connection();
    if (!curl) {
        curl = curl_easy_init();
        if (!curl) {
            log_error("cURL initialization failed");
            active_threads--;
            return;
        }
        // Set optimized options for new connection
        curl_easy_setopt(curl, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_1_1);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
        curl_easy_setopt(curl, CURLOPT_USERAGENT, "MyCrawler/1.0");
        curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 5L); // Reduced timeout for faster failures
        curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 2L);
        curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
        curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
        curl_easy_setopt(curl, CURLOPT_TCP_NODELAY, 1L);
        curl_easy_setopt(curl, CURLOPT_ACCEPT_ENCODING, "gzip,deflate");
        curl_easy_setopt(curl, CURLOPT_BUFFERSIZE, 65536L);
        curl_easy_setopt(curl, CURLOPT_DNS_CACHE_TIMEOUT, 600L);
    }
    
    auto start_time = std::chrono::steady_clock::now();
    int pages_processed = 0;
    std::string html;
    std::vector<std::string> new_urls;
    
    while (!stop_flag) {
        // Batch URL processing - adaptive batch size based on queue
        url_batch.clear();
        std::pair<std::string, float> url_priority_pair;
        
        // Adaptive batch size to maximize throughput
        const size_t queue_size = url_queue.size_approx();
        int batch_size = 8; // Increased default
        if (queue_size > 1000000) {
            batch_size = 15; // Large batches for huge queues
        } else if (queue_size > 500000) {
            batch_size = 12; // Medium-large batches
        } else if (queue_size > 100000) {
            batch_size = 10; // Medium batches
        }
        
        // Collect a batch of URLs
        for (int i = 0; i < batch_size && url_queue.try_dequeue(url_priority_pair); ++i) {
            url_batch.push_back(url_priority_pair.first);
        }
        
        if (url_batch.empty()) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1)); // Minimal sleep
            continue;
        }
        
        // Process each URL in the batch
        for (const std::string& url : url_batch) {
            std::string domain = extract_domain(url);
            
            // Skip blacklisted domains
            if (blacklist.is_blacklisted(domain)) continue;
            
            // Reduced rate limiting for maximum speed
            if (domain != "") {
                static thread_local std::unordered_map<std::string, std::chrono::steady_clock::time_point> last_requests;
                auto now = std::chrono::steady_clock::now();
                auto& last_time = last_requests[domain];
                auto elapsed = now - last_time;
                
                if (elapsed < std::chrono::milliseconds(15)) { // Very fast - only 15ms delay
                    std::this_thread::sleep_for(std::chrono::milliseconds(15) - elapsed);
                }
                last_requests[domain] = std::chrono::steady_clock::now();
            }
            
            // Fetch page content
            html.clear();
            curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
            curl_easy_setopt(curl, CURLOPT_WRITEDATA, &html);
            CURLcode res = curl_easy_perform(curl);
            
            if (res == CURLE_OK) {
                long http_code = 0;
                curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
                
                if (http_code == 200 && !html.empty() && html.size() > 100 && html.size() < 5*1024*1024) {
                    pages_processed++;
                    total_pages_processed++;
                    
                    // High-performance file batching
                    file_batch.push_back({url, html});
                    
                    // Larger batch sizes for better I/O performance
                    size_t target_batch_size = 150; // Increased default
                    if (url_queue.size_approx() > 1000000) {
                        target_batch_size = 200; // Even larger for huge queues
                    } else if (url_queue.size_approx() > 500000) {
                        target_batch_size = 175; // Medium-large batches
                    }
                    
                    if (file_batch.size() >= target_batch_size) {
                        save_batch_as_json(file_batch, "../data/raw");
                        file_batch.clear();
                        // Only shrink occasionally to avoid overhead
                        if (pages_processed % 500 == 0) {
                            file_batch.shrink_to_fit();
                        }
                    }
                    
                    // Fast HTML parsing and link extraction
                    if (html.find("</html>") != std::string::npos || html.find("<html") != std::string::npos) {
                        GumboOutput* output = gumbo_parse(html.c_str());
                        if (output && output->root) {
                            new_urls.clear();
                            extract_links_fast(output->root, new_urls);
                            
                            // Batch URL processing
                            std::vector<std::pair<std::string, float>> new_links;
                            for (const auto& link : canonicalize_urls(url, new_urls)) {
                                if (!is_useful_url(link)) continue;
                                if (link.find("http") != 0) continue;
                                
                                // Thread-local deduplication
                                if (local_seen_urls.find(link) == local_seen_urls.end()) {
                                    local_seen_urls.insert(link);
                                    
                                    // Batch bloom filter operations
                                    bool is_new = false;
                                    {
                                        std::lock_guard<std::mutex> lock(bloom_mutex);
                                        if (!url_filter.contains(link)) {
                                            url_filter.insert(link);
                                            is_new = true;
                                        }
                                    }
                                    
                                    if (is_new) {
                                        float priority = url_priority(link);
                                        new_links.push_back({link, priority});
                                        total_links_discovered++;
                                    }
                                }
                            }
                            
                            // High-speed queue management - prioritize throughput
                            const size_t queue_size = url_queue.size_approx();
                            
                            // More permissive queue filtering for maximum URL discovery
                            if (queue_size > 1500000) {
                                // Only filter very aggressively when approaching limits
                                for (const auto& link_pair : new_links) {
                                    if (link_pair.second > 0.7f) {
                                        url_queue.enqueue(link_pair);
                                    }
                                }
                            } else if (queue_size > 800000) {
                                // Moderate filtering
                                for (const auto& link_pair : new_links) {
                                    if (link_pair.second > 0.5f) {
                                        url_queue.enqueue(link_pair);
                                    }
                                }
                            } else {
                                // Accept most URLs for better coverage
                                for (const auto& link_pair : new_links) {
                                    if (link_pair.second > 0.3f) { // Very permissive
                                        url_queue.enqueue(link_pair);
                                    }
                                }
                            }
                            
                            gumbo_destroy_output(&kGumboDefaultOptions, output);
                        }
                    }
                }
            } else {
                total_network_errors++;
                error_tracker.record_error(domain, res);
                
                // Quick blacklisting for repeated failures
                if (res == CURLE_OPERATION_TIMEDOUT || res == CURLE_COULDNT_CONNECT) {
                    static thread_local std::unordered_map<std::string, int> failure_counts;
                    if (++failure_counts[domain] > 2) { // Reduced threshold
                        blacklist.add(domain);
                        failure_counts[domain] = 0;
                    }
                }
            }
        }
        
        // Optimized memory management - less frequent clearing for speed
        if (pages_processed % 75 == 0) { // Less frequent clearing
            local_seen_urls.clear();
            
            // Only shrink vectors occasionally
            if (pages_processed % 300 == 0) {
                url_batch.clear();
                url_batch.shrink_to_fit();
            }
        }
        
        // Memory cleanup only when really needed
        if (pages_processed % 500 == 0) {
            file_batch.shrink_to_fit();
        }
        
        // Performance reporting
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - start_time).count();
        
        if (elapsed >= 10) {
            double pages_per_sec = pages_processed / static_cast<double>(elapsed);
            if (pages_per_sec > 0) {
                std::lock_guard<std::mutex> lock(log_mutex);
                std::cout << "Worker rate: " << pages_per_sec << " pages/sec"
                          << " | Queue: " << url_queue.size_approx() << "\n";
            }
            start_time = now;
            pages_processed = 0;
            
            // Manage queue size to prevent degradation
            manage_queue_size();
        }
    }
    
    // Cleanup
    if (!file_batch.empty()) {
        save_batch_as_json(file_batch, "../data/raw");
    }
    
    global_connection_pool.return_connection(curl);
    active_threads--;
}

void signal_handler(int) {
    stop_flag = true;
    std::cout << "\nShutting down...\n";
}

int main() {
    // Initialize bloom filter with larger capacity
    bloom_parameters params;
    params.projected_element_count = 2000000;
    params.false_positive_probability = 0.02;
    params.compute_optimal_parameters();
    bloom_filter url_filter(params);
    
    // Quality seed URLs
    const std::vector<std::string> seed_urls = {
        "https://news.ycombinator.com",
        "https://en.wikipedia.org/wiki/Main_Page",
        "https://www.reddit.com/r/programming",
        "https://github.com/trending",
        "https://stackoverflow.com",
        "https://www.bbc.com/news",
        "https://www.cnn.com",
        "https://www.nytimes.com"
    };
    
    for (const auto& url : seed_urls) {
        url_queue.enqueue({url, url_priority(url)});
    }

    // Create shared components
    RobotsTxtCache robots;
    RateLimiter limiter;
    DomainBlacklist blacklist;
    ErrorTracker error_tracker;
    
    // Start worker threads - optimized for maximum crawling speed
    unsigned num_threads = std::thread::hardware_concurrency() * 3; // Increased multiplier
    std::cout << "Starting " << num_threads << " worker threads for high-speed crawling\n";
    
    std::atomic<int> active_threads{0};
    std::vector<std::thread> workers;
    for (unsigned i = 0; i < num_threads; ++i) {
        workers.emplace_back([&]() {
            crawl_worker_async(std::ref(stop_flag), 
                         std::ref(robots), 
                         std::ref(limiter),
                         std::ref(url_filter),
                         std::ref(active_threads),
                         std::ref(blacklist),
                         std::ref(error_tracker));
        });
    }
    
    // Register signal handler
    std::signal(SIGINT, signal_handler);
    
    // Wait for all workers to initialize
    while (active_threads < num_threads) {
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    
    auto start_time = std::chrono::steady_clock::now();
    
    // Monitor queue size and global performance
    while (!stop_flag) {
        std::this_thread::sleep_for(std::chrono::seconds(15));
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - start_time).count();
        
        if (elapsed > 0) {
            double global_rate = total_pages_processed / static_cast<double>(elapsed);
            std::cout << "\n=== GLOBAL STATS ==="
                      << "\nCrawl rate: " << global_rate << " pages/sec"
                      << "\nActive workers: " << active_threads << "/" << num_threads
                      << "\nTotal pages: " << total_pages_processed
                      << "\nTotal links: " << total_links_discovered
                      << "\nQueue size: " << url_queue.size_approx()
                      << "\nNetwork errors: " << total_network_errors
                      << "\nBlacklisted domains: " << blacklist.size()
                      << "\n====================\n";
            
            // Periodically log error stats
            error_tracker.print_stats();
            
            // Reset bloom filter less frequently (every 2 hours)
            static int reset_counter = 0;
            if (++reset_counter >= 480) { // 480 * 15 seconds = 2 hours
                std::lock_guard<std::mutex> lock(bloom_mutex);
                url_filter.clear();
                std::cout << "Reset bloom filter to prevent false positive buildup\n";
                reset_counter = 0;
            }
        }
    }
    
    // Wait for workers
    for (auto& t : workers) {
        if (t.joinable()) t.join();
    }
    
    std::cout << "Crawler shutdown complete\n";
    return 0;
}