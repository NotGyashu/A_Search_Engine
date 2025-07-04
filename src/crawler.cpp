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
std::mutex log_mutex;

// Concurrent queue for URLs
moodycamel::ConcurrentQueue<std::string> url_queue;

// CURL write callback
static size_t write_callback(char* ptr, size_t size, size_t nmemb, void* userdata) {
    ((std::string*)userdata)->append(ptr, size * nmemb);
    return size * nmemb;
}

// HTML parser
void extract_links(GumboNode* node, std::vector<std::string>& links) {
    if (!node) return;  // Critical null check
    
    if (node->type != GUMBO_NODE_ELEMENT) return;
    
    if (node->v.element.tag == GUMBO_TAG_A) {
        if (GumboAttribute* href = gumbo_get_attribute(&node->v.element.attributes, "href")) {
            links.push_back(href->value);
        }
    }
    
    GumboVector* children = &node->v.element.children;
    for (unsigned int i = 0; i < children->length; ++i) {
        extract_links(static_cast<GumboNode*>(children->data[i]), links);
    }
}

// Worker thread
void crawl_worker(std::atomic<bool>& stop_flag, RobotsTxtCache& robots, RateLimiter& limiter) {
    std::cout << "Worker started\n";
    
    while (!stop_flag) {
        CURL* curl = curl_easy_init();
        if (!curl) {
            log_error("cURL handle initialization failed");
            continue;
        }

        std::string html;
        std::vector<std::string> new_urls;
        std::string url;
        
        if (!url_queue.try_dequeue(url)) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            curl_easy_cleanup(curl);
            continue;
        }

        // Reset cURL handle for new request
        curl_easy_reset(curl);
        
        // 1. Check robots.txt
        if (!robots.is_allowed(url, "MyCrawler/1.0")) {
            curl_easy_cleanup(curl);
            continue;
        }
        
        // 2. Rate limit
        std::string domain = extract_domain(url);
        limiter.wait_for_domain(domain);
        
        // 3. Fetch page
        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &html);
        curl_easy_setopt(curl, CURLOPT_USERAGENT, "MyCrawler/1.0");
        curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
        
        CURLcode res = curl_easy_perform(curl);
        
        // 4. Process response
        if (res == CURLE_OK) {
            save_as_json(url, html, "data/raw");
            
            // Safe Gumbo parsing
            GumboOutput* output = gumbo_parse(html.c_str());
            if (output) {
                if (output->root) {
                    extract_links(output->root, new_urls);
                }
                gumbo_destroy_output(nullptr, output);
            } else {
                log_error("Gumbo parse failed for: " + url);
            }
            
            for (const auto& link : canonicalize_urls(url, new_urls)) {
                url_queue.enqueue(link);
            }
        } else {
            std::lock_guard<std::mutex> lock(log_mutex);
            log_error(std::string(curl_easy_strerror(res)) + std::string(": ") + url);
        }
        
        curl_easy_cleanup(curl);
        html.clear();
    }
}

std::atomic<bool> stop_flag{false};

void signal_handler(int) {
    stop_flag = true;
}

int main() {
    // Seed URLs
    url_queue.enqueue("https://example.com");
    
    RobotsTxtCache robots;
    RateLimiter limiter;
    
    // Start workers
    unsigned num_threads = 1;
    std::vector<std::thread> workers;
    for (unsigned i = 0; i < num_threads; ++i) {
        workers.emplace_back(crawl_worker, std::ref(stop_flag), 
                            std::ref(robots), std::ref(limiter));
    }
    
    // Handle Ctrl+C
    std::signal(SIGINT, signal_handler);
    
    // Wait for workers
    for (auto& t : workers) t.join();
    return 0;
}