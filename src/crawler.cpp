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
    #include <filesystem>  // For directory creation

    // Global mutex for thread-safe logging
    std::mutex log_mutex;

    // Concurrent queue for URL management
    moodycamel::ConcurrentQueue<std::string> url_queue;

    // Global shutdown flag
    std::atomic<bool> stop_flag{false};

    /**
     * cURL write callback function
     * Appends received data to a string
     * 
     * @param ptr    Pointer to the data buffer
     * @param size   Size of each data element
     * @param nmemb  Number of elements
     * @param userdata Pointer to target string
     * @return       Number of bytes processed
     */
    static size_t write_callback(char* ptr, size_t size, size_t nmemb, void* userdata) {
        ((std::string*)userdata)->append(ptr, size * nmemb);
        return size * nmemb;
    }

    /**
     * HTML link extractor using iterative DFS
     * 
     * @param root   Root node of parsed HTML
     * @param links  Output vector for found URLs
     */
    void extract_links_safe(GumboNode* root, std::vector<std::string>& links) {
        std::stack<GumboNode*> node_stack;
        node_stack.push(root);
        
        while (!node_stack.empty()) {
            GumboNode* node = node_stack.top();
            node_stack.pop();
            
            // Skip non-element nodes
            if (node->type != GUMBO_NODE_ELEMENT) continue;
            
            // Extract links from <a> tags
            if (node->v.element.tag == GUMBO_TAG_A) {
                if (GumboAttribute* href = gumbo_get_attribute(&node->v.element.attributes, "href")) {
                    links.push_back(href->value);
                }
            }
            
            // Process child nodes in reverse order (DFS)
            GumboVector* children = &node->v.element.children;
            for (int i = children->length - 1; i >= 0; --i) {
                node_stack.push(static_cast<GumboNode*>(children->data[i]));
            }
        }
    }

    /**
     * Worker thread function for crawling
     * 
     * @param stop_flag Atomic flag for graceful shutdown
     * @param robots    Robots.txt cache
     * @param limiter   Rate limiter
     * @param url_filter Bloom filter for URL deduplication
     */
    void crawl_worker(std::atomic<bool>& stop_flag, RobotsTxtCache& robots, RateLimiter& limiter, bloom_filter& url_filter) {
        std::cout << "Worker started\n";
        
        // Create thread-local cURL handle
        CURL* curl = curl_easy_init();
        if (!curl) {
            log_error("cURL initialization failed");
            return;
        }

        // Set cURL options
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
        curl_easy_setopt(curl, CURLOPT_USERAGENT, "MyCrawler/1.0");
        curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 10L);
        curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);  // Important for multithreading

        // Performance tracking
        auto start_time = std::chrono::steady_clock::now();
        int pages_processed = 0;
        std::string html;
        std::vector<std::string> new_urls;

        while (!stop_flag) {
            std::string url;
            
            // Get next URL from queue
            if (!url_queue.try_dequeue(url)) {
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
                continue;
            }

            std::cout << "Processing: " << url << "\n";
            
            // 1. Check robots.txt compliance
            if (!robots.is_allowed(url, "MyCrawler/1.0")) {
                continue;
            }
            
            // 2. Apply rate limiting
            std::string domain = extract_domain(url);
            limiter.wait_for_domain(domain);
            
            // 3. Fetch page content
            curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
            curl_easy_setopt(curl, CURLOPT_WRITEDATA, &html);
            CURLcode res = curl_easy_perform(curl);
            
            // 4. Process response
            if (res == CURLE_OK && !html.empty()) {
                pages_processed++;
                
                // Validate HTML size
                const size_t MIN_HTML_SIZE = 100;
                const size_t MAX_HTML_SIZE = 10 * 1024 * 1024;  // 10MB
                if (html.size() < MIN_HTML_SIZE) {
                    log_error("Skipping small HTML: " + url);
                    continue;
                }
                if (html.size() > MAX_HTML_SIZE) {
                    log_error("Oversized HTML: " + url);
                    continue;
                }
                
                // Save HTML to file
                save_as_json(url, html, "../data/raw");
                
                // Parse HTML and extract links
                GumboOutput* output = nullptr;
                try {
                    output = gumbo_parse(html.c_str());
                    
                    if (output && output->root) {
                        new_urls.clear();
                        extract_links_safe(output->root, new_urls);
                        
                        // Process and deduplicate found URLs
                        for (const auto& link : canonicalize_urls(url, new_urls)) {
                            if (link.find("http") == 0) {  // Validate URL scheme
                                // Thread-safe bloom filter check
                                bool is_new = false;
                                {
                                    std::lock_guard<std::mutex> lock(log_mutex);
                                    if (!url_filter.contains(link)) {
                                        url_filter.insert(link);
                                        is_new = true;
                                    }
                                }
                                
                                if (is_new) {
                                    url_queue.enqueue(link);
                                }
                            }
                        }
                    }
                } catch (...) {
                    log_error("Parser exception on: " + url);
                }
                
                // Clean up parser
                if (output) {
                    gumbo_destroy_output(&kGumboDefaultOptions, output);
                }
                
                // Calculate and display crawl rate
                auto now = std::chrono::steady_clock::now();
                auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - start_time).count();
                
                if (elapsed >= 5) {  // Update every 5 seconds
                    double pages_per_sec = pages_processed / static_cast<double>(elapsed);
                    {
                        std::lock_guard<std::mutex> lock(log_mutex);
                        std::cout << "Crawl rate: " << pages_per_sec << " pages/sec\n";
                    }
                    start_time = now;
                    pages_processed = 0;
                }
            } else if (res != CURLE_OK) {
                // Error handling
                std::lock_guard<std::mutex> lock(log_mutex);
                log_error(std::string(curl_easy_strerror(res)) + ": " + url);
            }
            
            html.clear();
        }
        
        // Cleanup cURL resources
        curl_easy_cleanup(curl);
    }

    /**
     * Signal handler for graceful shutdown
     */
    void signal_handler(int) {
        stop_flag = true;
        std::cout << "\nShutting down...\n";
    }

    /**
     * Main application entry point
     */
    int main() {
        // Initialize bloom filter
        bloom_parameters params;
        params.projected_element_count = 1000000;
        params.false_positive_probability = 0.001;
        params.compute_optimal_parameters();
        bloom_filter url_filter(params);
        
        // Seed URLs
        url_queue.enqueue("https://news.ycombinator.com");
        
        // Create shared components
        RobotsTxtCache robots;
        RateLimiter limiter;
        
        // Start worker threads
        unsigned num_threads = std::thread::hardware_concurrency();
        std::cout << "Starting " << num_threads << " worker threads\n";
        std::vector<std::thread> workers;
        for (unsigned i = 0; i < num_threads; ++i) {
            workers.emplace_back(crawl_worker, 
                                std::ref(stop_flag), 
                                std::ref(robots), 
                                std::ref(limiter),      
                                std::ref(url_filter));  // Pass the bloom filter
        }
        
        // Register signal handler for Ctrl+C
        std::signal(SIGINT, signal_handler);
        
        // Wait for all workers to finish
        for (auto& t : workers) {
            t.join();
        }
        
        std::cout << "Crawler shutdown complete\n";
        return 0;
    }