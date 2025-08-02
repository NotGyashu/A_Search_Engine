#include "crawler_workers.h"
#include "crawler_core.h"
#include <curl/curl.h>
#include <chrono>
#include <iostream>
#include <iomanip>
#include <tracy/Tracy.hpp>

/**
 * 🌐 MULTI-THREADED SPEED-OPTIMIZED CRAWLER WORKER
 * Handles HTTP requests using curl_multi for maximum parallelism
 */
void multi_crawler_worker(int worker_id, RobotsTxtCache& robots, RateLimiter& limiter,
                         DomainBlacklist& blacklist, ErrorTracker& error_tracker,
                         ConnectionPool& connection_pool, CrawlerMode mode) {
    std::cout << "Starting multi-worker " << worker_id << " for " <<
              (mode == CrawlerMode::FRESH ? "FRESH" : "REGULAR") << " mode.\n";
    ZoneScopedN("MultiCrawlerWorker");
    auto worker_start = std::chrono::steady_clock::now();
    int pages_processed = 0;
    int successful_requests = 0;
    int urls_skipped_rate_limit = 0;
    
    // Initialize curl multi handle for this worker
    CURLM* multi_handle = curl_multi_init();
    if (!multi_handle) {
        std::cerr << "Failed to initialize curl multi handle for worker " << worker_id << "\n";
        return;
    }
    // Configure multi handle for maximum performance
    curl_multi_setopt(multi_handle, CURLMOPT_MAXCONNECTS, CrawlerConstants::Network::MAX_CONNECTIONS);
    curl_multi_setopt(multi_handle, CURLMOPT_MAX_TOTAL_CONNECTIONS, CrawlerConstants::Network::MAX_CONNECTIONS);
    curl_multi_setopt(multi_handle, CURLMOPT_MAX_HOST_CONNECTIONS, CrawlerConstants::Network::MAX_HOST_CONNECTIONS);
    curl_multi_setopt(multi_handle, CURLMOPT_PIPELINING, CURLPIPE_MULTIPLEX);
    // ✅ CURL SHARED HANDLE — Create shared handle for DNS cache and connection pooling
    CURLSH* share_handle = curl_share_init();
    curl_share_setopt(share_handle, CURLSHOPT_SHARE, CURL_LOCK_DATA_DNS);
    curl_share_setopt(share_handle, CURLSHOPT_SHARE, CURL_LOCK_DATA_SSL_SESSION);
    curl_share_setopt(share_handle, CURLSHOPT_SHARE, CURL_LOCK_DATA_CONNECT);
    
    // Storage for active requests - using smart pointers for automatic cleanup
    std::unordered_map<CURL*, std::unique_ptr<MultiRequestContext>> active_requests;
    
    // Main worker loop
    while (!stop_flag) {
        {
            ZoneScopedN("URL Acquisition and Request Setup");
            int attempts = 0;
            const int max_attempts = CrawlerConstants::Network::MAX_ATTEMPTS_PER_CYCLE;
            
            // Phase 2: Keep adding requests until we reach optimal concurrent level
            while (active_requests.size() < CrawlerConstants::Network::MAX_CONCURRENT_REQUESTS_PER_WORKER && 
                   attempts < max_attempts && !stop_flag) {
                
                UrlInfo url_info("", 0.0f);
                attempts++;
                
                bool found_url = false;
    std::string domain;

    // ---> ADD PROFILING ZONES FOR EACH 'if' BLOCK <---

    // Priority 1: Ready Domains
    {
        ZoneScopedN("Dequeue DomainQ"); // <--- ADD THIS
        if (shared_domain_queues->try_dequeue_from_available_domain(limiter, url_info, domain)) {
            found_url = true;
        }
    }
    // Priority 2: Main smart queue
    if(!found_url) { // use if(!found_url) to avoid nesting zones
        ZoneScopedN("Dequeue SmartQ"); // <--- ADD THIS
        if (smart_url_frontier->dequeue(url_info)) {
            found_url = true;
        }
    }
    // Priority 3: Work stealing
    if(!found_url) {
        ZoneScopedN("Steal WorkQ"); // <--- ADD THIS
        if (work_stealing_queue->try_steal(worker_id, url_info)) {
            found_url = true;
        }
    }
    // Priority 4: Load from disk
    if(!found_url) {
        ZoneScopedN("Load from Disk"); // <--- ADD THIS
                // Priority 4: Load from disk (REGULAR MODE ONLY)
                 if (mode == CrawlerMode::REGULAR && sharded_disk_queue) {
                    auto disk_urls = sharded_disk_queue->load_urls_from_disk(50);
                    if (!disk_urls.empty()) {
                        url_info = UrlInfo(disk_urls[0], CrawlerConstants::Priority::DISK_URL_PRIORITY, 0);
                        found_url = true;
                        
                        // Re-queue remaining URLs to smart frontier and work stealing queue
                        for (size_t i = 1; i < std::min(disk_urls.size(), (size_t)10); ++i) {
                            UrlInfo disk_url(disk_urls[i], CrawlerConstants::Priority::DISK_URL_PRIORITY, 0);
                            if (!smart_url_frontier->enqueue(disk_url)) {
                                work_stealing_queue->push_local(worker_id, disk_url);
                            }
                        }
                    }
                }
            }
                if (!found_url) {
                    break; // No URLs available, exit inner loop
                }
                
                // Extract domain if not already set by ready domain queue
                if (domain.empty()) {
                    domain = UrlNormalizer::extract_domain(url_info.url);
                }
                std::string path = UrlNormalizer::extract_path(url_info.url);
                
                // Check domain blacklist
                if (blacklist.is_blacklisted(domain)) {
                    continue;
                }
                
                // ✅ ROBOTS.TXT COMPLIANCE — Check robots.txt before every request
              // ROBOTS.TXT COMPLIANCE
                RobotsCheckResult robots_result;
                {
                    ZoneScopedN("Check Robots"); // <--- ADD THIS
                    robots_result = robots.is_allowed(domain, path);
                }
                
                switch (robots_result) {
                    case RobotsCheckResult::ALLOWED:
                        // Continue with the request
                        break;
                    case RobotsCheckResult::DISALLOWED:
                        continue; // Skip this URL
                    case RobotsCheckResult::DEFERRED_FETCH_STARTED:
                        {
                            std::lock_guard<std::mutex> lock(g_deferred_urls_mutex);
                            g_deferred_urls[domain].push_back(url_info);
                        }
                        
                        std::string robots_url = "https://" + domain + "/robots.txt";
                        UrlInfo robots_info(robots_url, 1.0f, 0, domain);
    
                        auto ctx = std::make_unique<MultiRequestContext>(robots_info, &connection_pool);
                        ctx->type = RequestType::ROBOTS_TXT;
    
                        curl_easy_setopt(ctx->curl_handle, CURLOPT_URL, ctx->url.c_str());
                        curl_easy_setopt(ctx->curl_handle, CURLOPT_WRITEFUNCTION, hybrid_write_callback);
                        curl_easy_setopt(ctx->curl_handle, CURLOPT_WRITEDATA, &ctx->response_data);
                        curl_easy_setopt(ctx->curl_handle, CURLOPT_TIMEOUT, CrawlerConstants::Network::TIMEOUT_SECONDS);
                        curl_easy_setopt(ctx->curl_handle, CURLOPT_CONNECTTIMEOUT, CrawlerConstants::Network::CONNECT_TIMEOUT_SECONDS);
                        curl_easy_setopt(ctx->curl_handle, CURLOPT_FOLLOWLOCATION, 1L);
                        curl_easy_setopt(ctx->curl_handle, CURLOPT_USERAGENT, CrawlerConstants::Headers::USER_AGENT);
                        curl_easy_setopt(ctx->curl_handle, CURLOPT_SSL_VERIFYPEER, 0L); 
                        curl_easy_setopt(ctx->curl_handle, CURLOPT_SSL_VERIFYHOST, 0L);
                        curl_easy_setopt(ctx->curl_handle, CURLOPT_SHARE, share_handle);
                        
                        curl_multi_add_handle(multi_handle, ctx->curl_handle);
                        active_requests[ctx->curl_handle] = std::move(ctx);
                        continue; 
                }
    
                
                // ✅ DOMAIN QUEUES — Apply rate limiting with shared domain queues
                {
                    ZoneScopedN("Check RateLimit");
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
            }
                
                // Create request context - temporarily disable domain-specific connections
                auto ctx = std::make_unique<MultiRequestContext>(url_info, &connection_pool);
                ctx->type = RequestType::PAGE;
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
                curl_easy_setopt(ctx->curl_handle, CURLOPT_HEADERFUNCTION, hybrid_write_callback);
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
        }
        
        // No active requests, check stop flag and sleep briefly
        if (active_requests.empty()) {
            if (stop_flag) break; // Exit immediately if stop requested
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            continue;
        }
        
        int running_handles = 0;
        // Perform all transfers
        {
            ZoneScopedN("Network Perform");
            CURLMcode mc = curl_multi_perform(multi_handle, &running_handles);
            if (mc != CURLM_OK) {
                std::cerr << "curl_multi_perform failed: " << curl_multi_strerror(mc) << "\n";
                break;
            }
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

                    if (ctx->type == RequestType::ROBOTS_TXT) {
                        // This was a robots.txt download
                        long http_code = 0;
                        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
                        
                        // Update the cache with the result
                        robots.update_cache(ctx->domain, ctx->response_data, static_cast<int>(http_code));
                        
                        // Now, re-queue the URLs that were waiting for this file
                        std::vector<UrlInfo> urls_to_requeue;
                        {
                            std::lock_guard<std::mutex> lock(g_deferred_urls_mutex);
                            auto deferred_it = g_deferred_urls.find(ctx->domain);
                            if (deferred_it != g_deferred_urls.end()) {
                                urls_to_requeue = std::move(deferred_it->second);
                                g_deferred_urls.erase(deferred_it);
                            }
                        }
    
                        for (const auto& requeued_url : urls_to_requeue) {
                            // Push back to the work-stealing queue for immediate processing
                            work_stealing_queue->push_local(worker_id, requeued_url);
                        }
                    } else {
                        if (msg->data.result == CURLE_OK) {
                            long http_code = 0;
                            curl_off_t download_size = 0;
                            curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
                            curl_easy_getinfo(curl, CURLINFO_SIZE_DOWNLOAD_T, &download_size);
                            
                            limiter.record_success(ctx->domain);
                            error_tracker.record_success(ctx->domain);
                            global_monitor.add_bytes(static_cast<long>(download_size));
                            
                            // Handle conditional GET responses
                            if (http_code == 304) {
                                // Content not modified - no need to process
                                std::cout << "304 Not Modified: " << ctx->url << std::endl;
                                // Content hasn't changed, don't update metadata backoff
                                
                            } else if (http_code == CrawlerConstants::HttpStatus::OK && !ctx->response_data.empty()) {
                                ZoneScopedN("Handle Successful Page");
                                
                                // ✅ CONDITIONAL GET — Parse and cache response headers
                                ConditionalGet::HttpHeaders new_headers;
                                {
                                    ZoneScopedN("Parse Headers");
                                    new_headers = ConditionalGet::ConditionalGetManager::parse_response_headers(ctx->response_headers);
                                }
                                {
                                    ZoneScopedN("Update Conditional GET Cache");
                                    conditional_get_manager->update_cache(ctx->url, new_headers);
                                }
                                
                                // Calculate content hash and update metadata
                                std::string content_hash;
                                {
                                    ZoneScopedN("Hash Content");
                                    content_hash = ContentHashing::FastContentHasher::hash_key_content(ctx->response_data);
                                }
                                {
                                    ZoneScopedN("Update Crawl Metadata");
                                    metadata_store->update_after_crawl(ctx->url, content_hash);
                                }
                                
                                // Check content quality
                                bool is_quality = false;
                                {
                                    ZoneScopedN("Check Content Quality");
                                    is_quality = ContentFilter::is_high_quality_content(ctx->response_data);
                                }
                                
                                if (is_quality) {
                                    pages_processed++;
                                    global_monitor.increment_pages();
                                    
                                    // Create task for HTML processing
                                    HtmlProcessingTask html_task(
                                        std::move(ctx->response_data),
                                        ctx->url,
                                        ctx->domain,
                                        ctx->url_info.depth
                                    );
                                    
                                    if (!html_processing_queue->enqueue(std::move(html_task))) {
                                        std::cout << "⚠️  HTML queue full, dropping task for " << ctx->url << std::endl;
                                    }
                                }
                            } else if (http_code == CrawlerConstants::HttpStatus::TOO_MANY_REQUESTS || 
                                    http_code == CrawlerConstants::HttpStatus::SERVICE_UNAVAILABLE) {
                                std::cout << "⏳ Server busy (" << http_code << "): " << ctx->url << ". Applying backoff.\n";
                                metadata_store->record_temporary_failure(ctx->url);
                            }
                        } else {
                            bool is_ssl_error = (msg->data.result == CURLE_SSL_CONNECT_ERROR || 
                                                     msg->data.result == CURLE_PEER_FAILED_VERIFICATION);
                            if (is_ssl_error && ctx->retries == 0 && ctx->url.rfind("https://", 0) == 0) {
                                    
                                    std::cout << "ℹ️  HTTPS failed for " << ctx->domain << ", falling back to HTTP.\n";
                                    
                                    std::string http_url = "http://" + ctx->url.substr(8);
                                    UrlInfo fallback_info(http_url, ctx->url_info.priority, ctx->url_info.depth, ctx->url_info.referring_domain);
                                    
                                    auto fallback_ctx = std::make_unique<MultiRequestContext>(fallback_info, &connection_pool);
                                    fallback_ctx->retries = 1; // Mark as a retry to prevent loops
        
                                    // Configure and add the new handle
                                    curl_easy_setopt(fallback_ctx->curl_handle, CURLOPT_URL, fallback_ctx->url.c_str());
                                    curl_easy_setopt(fallback_ctx->curl_handle, CURLOPT_WRITEFUNCTION, hybrid_write_callback);
                                    curl_easy_setopt(fallback_ctx->curl_handle, CURLOPT_WRITEDATA, &fallback_ctx->response_data);
                                    curl_easy_setopt(fallback_ctx->curl_handle, CURLOPT_HEADERFUNCTION, hybrid_write_callback);
                                    curl_easy_setopt(fallback_ctx->curl_handle, CURLOPT_HEADERDATA, &fallback_ctx->response_headers);
                                    curl_easy_setopt(fallback_ctx->curl_handle, CURLOPT_TIMEOUT, CrawlerConstants::Network::TIMEOUT_SECONDS);
                                    curl_easy_setopt(fallback_ctx->curl_handle, CURLOPT_CONNECTTIMEOUT, CrawlerConstants::Network::CONNECT_TIMEOUT_SECONDS);
                                    curl_easy_setopt(fallback_ctx->curl_handle, CURLOPT_SHARE, share_handle);
                                    
                                    curl_multi_add_handle(multi_handle, fallback_ctx->curl_handle);
                                    active_requests[fallback_ctx->curl_handle] = std::move(fallback_ctx);
        
                            } else {
                                // ORIGINAL ERROR HANDLING for non-fallback cases
                                global_monitor.increment_errors();
                                limiter.record_failure(ctx->domain);
                                error_tracker.record_error(ctx->domain, msg->data.result);
                                
                                if (error_tracker.should_blacklist_domain(ctx->domain)) {
                                    blacklist.add_temporary(ctx->domain);
                                    std::cout << "Worker " << worker_id << " blacklisted domain: " << ctx->domain << std::endl;
                                }
                            }
                        }
                    }
                    
                    // Remove from multi handle and cleanup
                    curl_multi_remove_handle(multi_handle, curl);
                    connection_pool.release_connection(ctx->curl_handle); // Return handle to the pool
                    active_requests.erase(it);
                }
            }
        }
        
        // Wait for activity with timeout
        if (running_handles > 0) {
            curl_multi_wait(multi_handle, nullptr, 0, 100, nullptr);
        }
        
        // Periodic progress reporting
        if (pages_processed % CrawlerConstants::Monitoring::PROGRESS_REPORT_FREQUENCY == 0 && pages_processed > 0) {
            auto now = std::chrono::steady_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - worker_start).count();
            if (elapsed > 0) {
                double rate = static_cast<double>(pages_processed) / elapsed;
                std::cout << "🌐 Worker " << worker_id << ": " 
                         << pages_processed << " pages (" 
                         << std::fixed << std::setprecision(1) << rate << " pages/s)\n";
            }
        }
    }
    
    // Cleanup remaining requests
    for (auto& [curl, ctx] : active_requests) {
        curl_multi_remove_handle(multi_handle, curl);
    }
    
    // Clean up shared handle and multi handle
    curl_share_cleanup(share_handle);
    curl_multi_cleanup(multi_handle);
    std::cout << "Multi-worker " << worker_id << " finished. Processed " << pages_processed << " pages.\n";
}

/**
 * 🔧 DEDICATED HTML PROCESSING WORKER
 * Separates HTML parsing from network I/O for better pipeline efficiency
 */
void html_processing_worker(int worker_id, RobotsTxtCache& robots, CrawlerMode mode) {
    std::cout << "🔧 HTML processor " << worker_id << " starting...\n";
    ZoneScopedN("HtmlWorker Loop");
    int links_processed = 0;
    int batches_processed = 0;
    auto worker_start = std::chrono::steady_clock::now();
    
    // Batch storage for improved I/O efficiency
    std::vector<std::pair<std::string, std::string>> batch_buffer;
    batch_buffer.reserve(CrawlerConstants::Storage::BATCH_SIZE);
    
    while (!stop_flag) {
        HtmlProcessingTask task("", "", "", 0);
        
        bool dequeued = false;
        {
            ZoneScopedN("HTML Worker Dequeue Wait"); // <--- Add this zone
            dequeued = html_processing_queue->dequeue(task);
        }

        if (!dequeued) {
            if (stop_flag) break;
            continue;
        }
        
        try {
            ZoneScopedN("Process HTML"); 
            
            // 1. Construct the HtmlDocument from raw HTML
            HtmlDocument doc(task.html);
            
            // 2. Extract clean text for language detection
            const std::string& clean_text = doc.getCleanText();
            
            // 3. Language detection: filter non-English pages
            bool is_english = false;
            {
                ZoneScopedN("Detect Language");
                is_english = FastLanguageDetector::is_english_content(clean_text, task.url);
            }
            
            if (!is_english) {
                global_monitor.increment_filtered();
                continue; // Skip non-English content
            }
            
            // 4. Save raw HTML to batch buffer
            batch_buffer.emplace_back(task.url, task.html);
            
            // 5. Save batch immediately in FRESH mode or when batch size reached
            if (mode == CrawlerMode::FRESH) {
                enhanced_storage->save_html_batch_with_metadata(batch_buffer);
                batch_buffer.clear();
            } else {
                if (batch_buffer.size() >= CrawlerConstants::Storage::BATCH_SIZE) {
                    enhanced_storage->save_html_batch_with_metadata(batch_buffer);
                    batch_buffer.clear();
                }
            }
            
            // 6. Link extraction for queueing (only in REGULAR mode and depth < 5)
            if (mode != CrawlerMode::FRESH && task.depth < 5) {
                // Check if HTML is valid before link extraction
                bool is_valid_html = false;
                {
                    ZoneScopedN("Validate HTML");
                    is_valid_html = doc.isValidHtml(task.html);
                }
                
                if (is_valid_html) {
                    std::vector<std::string> links;
                    {
                        ZoneScopedN("Extract Links");
                        links = AdaptiveLinkExtractor::extract_links_adaptive(
                            task.html, task.url);
                    }
                    
                    int new_links_added = 0;
                    {
                        ZoneScopedN("Process Links");
                        new_links_added = AdaptiveLinkExtractor::process_and_enqueue_links(
                            links, task.depth, task.domain, worker_id);
                    }
                    
                    global_monitor.increment_links(new_links_added);
                    links_processed += links.size();
                }
            }
            
            batches_processed++;
            
            // Periodic progress for HTML processors
            if (batches_processed % (CrawlerConstants::Monitoring::PROGRESS_REPORT_FREQUENCY/5) == 0) {
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
            global_monitor.increment_errors();
        }
    }
    
    // Save any remaining batch at shutdown
    if (!batch_buffer.empty()) {
        enhanced_storage->save_html_batch_with_metadata(batch_buffer);
    }
    
    std::cout << "🔧 HTML processor " << worker_id << " finished. Processed " 
             << batches_processed << " batches, " << links_processed << " total links.\n";
}