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

// Concurrent queue for URL management
moodycamel::ConcurrentQueue<std::string> url_queue;

// Global shutdown flag
std::atomic<bool> stop_flag{false};

// Performance metrics
std::atomic<long> total_pages_processed{0};
std::atomic<long> total_links_discovered{0};
std::atomic<long> total_network_errors{0};

/**
 * cURL write callback function
 */
static size_t write_callback(char* ptr, size_t size, size_t nmemb, void* userdata) {
    ((std::string*)userdata)->append(ptr, size * nmemb);
    return size * nmemb;
}

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
 * Worker thread function for crawling - optimized version
 */
void crawl_worker(std::atomic<bool>& stop_flag, RobotsTxtCache& robots, RateLimiter& limiter, 
                  bloom_filter& url_filter, std::atomic<int>& active_threads) {
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
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "MyCrawler/1.0");
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 5L);  // Reduced from 8s
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 3L);  // Reduced from 5s
    curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    curl_easy_setopt(curl, CURLOPT_TCP_NODELAY, 1L);
    curl_easy_setopt(curl, CURLOPT_ACCEPT_ENCODING, "gzip,deflate");
    curl_easy_setopt(curl, CURLOPT_BUFFERSIZE, 102400L);
    curl_easy_setopt(curl, CURLOPT_LOW_SPEED_LIMIT, 10240);  // 10KB/s
    curl_easy_setopt(curl, CURLOPT_LOW_SPEED_TIME, 3L);      // for 3s

    // Performance tracking
    auto start_time = std::chrono::steady_clock::now();
    int pages_processed = 0;
    std::string html;
    std::vector<std::string> new_urls;
    
    // Wait for main thread to start
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    while (!stop_flag) {
        std::string url;
        static thread_local int empty_count = 0;
        
        // Get next URL from queue
        if (!url_queue.try_dequeue(url)) {
            // Adaptive sleep based on queue status
            empty_count = std::min(empty_count + 1, 10);
            std::this_thread::sleep_for(std::chrono::milliseconds(10 * empty_count));
            continue;
        }
        empty_count = 0;

        // 1. Apply rate limiting
        std::string domain = extract_domain(url);
        limiter.wait_for_domain(domain);
        
        // 2. Fetch page content
        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &html);
        CURLcode res = curl_easy_perform(curl);
        
        // 3. Process response
        if (res == CURLE_OK) {
            long http_code = 0;
            curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
            
            if (http_code == 200 && !html.empty() && html.size() > 100 && html.size() < 10*1024*1024) {
                pages_processed++;
                total_pages_processed++;
                
                // Save HTML to file (batched)
                file_batch.push_back({url, html});
                if (file_batch.size() >= 10) {  // Increased batch size
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
                        std::vector<std::string> new_links;
                        for (const auto& link : canonicalize_urls(url, new_urls)) {
                            if (link.find("http") == 0) {
                                // First check thread-local cache
                                if (local_seen_urls.find(link) == local_seen_urls.end()) {
                                    local_seen_urls.insert(link);
                                    
                                    // Then check global bloom filter
                                    bool is_new = false;
                                    {
                                        std::lock_guard<std::mutex> lock(log_mutex);
                                        if (!url_filter.contains(link)) {
                                            url_filter.insert(link);
                                            is_new = true;
                                        }
                                    }
                                    
                                    if (is_new) {
                                        new_links.push_back(link);
                                        total_links_discovered++;
                                    }
                                }
                            }
                        }
                        
                        // Enqueue new links
                        for (const auto& link : new_links) {
                            url_queue.enqueue(link);
                        }
                    }
                }
            }
        } else {
            total_network_errors++;
            std::lock_guard<std::mutex> lock(log_mutex);
            log_error(std::string(curl_easy_strerror(res)) + ": " + url);
        }
        
        html.clear();
        
        // Calculate and display crawl rate
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - start_time).count();
        
        if (elapsed >= 10) {  // Reduced frequency of reporting
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

void signal_handler(int) {
    stop_flag = true;
    std::cout << "\nShutting down...\n";
}

int main() {
    // Initialize bloom filter with larger capacity
    bloom_parameters params;
    params.projected_element_count = 2000000;  // Increased to 2 million
    params.false_positive_probability = 0.02;  // Higher false positive rate
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
        url_queue.enqueue(url);
    }

    // Create shared components
    RobotsTxtCache robots;
    RateLimiter limiter;
    
    // Start worker threads
    unsigned num_threads = std::thread::hardware_concurrency() * 2;
    std::cout << "Starting " << num_threads << " worker threads\n";
    
    std::atomic<int> active_threads{0};
    std::vector<std::thread> workers;
    for (unsigned i = 0; i < num_threads; ++i) {
        workers.emplace_back([&]() {
            crawl_worker(std::ref(stop_flag), 
                         std::ref(robots), 
                         std::ref(limiter),
                         std::ref(url_filter),
                         std::ref(active_threads));
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
                      << "\n====================\n";
        }
    }
    
    // Wait for workers
    for (auto& t : workers) {
        if (t.joinable()) t.join();
    }
    
    std::cout << "Crawler shutdown complete\n";
    return 0;
}