#include "sitemap_parser.h"
#include "http_client.h"
#include "robots_txt_cache.h"
#include "utility_functions.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <ctime>
#include <iomanip>
#include <thread>
#include <tinyxml2.h>

using namespace tinyxml2;

namespace SitemapParsing {

SitemapParser::SitemapParser(std::function<void(const std::vector<SitemapUrl>&)> callback, HttpClient* client, RobotsTxtCache* robots_cache)
    : url_callback_(std::move(callback)), http_client_(client), robots_cache_(robots_cache) {
    if (!robots_cache_) {
        throw std::invalid_argument("RobotsTxtCache is required for SitemapParser");
    }
}

SitemapParser::~SitemapParser() {
    shutdown_ = true;
    
    // Notify the worker thread to wake up and check shutdown flag
    {
        std::lock_guard<std::mutex> lock(shutdown_mutex_);
        shutdown_cv_.notify_one();
    }
    
    if (parser_thread_.joinable()) {
        parser_thread_.join();
    }
}

void SitemapParser::add_domains_to_monitor(const std::vector<std::string>& domains) {
    std::lock_guard<std::mutex> lock(domains_mutex_);
    for (const auto& domain : domains) {
        if (std::find(monitored_domains_.begin(), monitored_domains_.end(), domain) == monitored_domains_.end()) {
            monitored_domains_.push_back(domain);
            // std::cout << "🌐 Added domain to monitor: " << domain << std::endl;
        }
    }
}


void SitemapParser::refresh_sitemaps_from_robots_cache() {
    // Early exit if shutdown was requested
    if (shutdown_) {
        return;
    }
    
    std::vector<std::string> domains_copy;
    {
        std::lock_guard<std::mutex> lock(domains_mutex_);
        domains_copy = monitored_domains_;
    }
    
    std::cout << "🔍 Refreshing sitemaps for " << domains_copy.size() << " monitored domains" << std::endl;
    
    for (const auto& domain : domains_copy) {
        // Check shutdown flag during each domain processing
        if (shutdown_) {
            std::cout << "🛑 Sitemap refresh interrupted by shutdown request" << std::endl;
            return;
        }
        
        // Get sitemaps from robots cache (with error handling)
        std::vector<::SitemapInfo> cached_sitemaps;
        try {
            cached_sitemaps = robots_cache_->get_sitemaps_for_domain(domain);
        } catch (const std::exception& e) {
            std::cerr << "⚠️  ERROR: Failed to get sitemaps from robots cache for domain " << domain 
                     << ": " << e.what() << std::endl;
            continue; // Skip this domain and continue with others
        } catch (...) {
            std::cerr << "⚠️  ERROR: Unknown error getting sitemaps from robots cache for domain " << domain << std::endl;
            continue; // Skip this domain and continue with others
        }
        
        // std::cout << "📋 Domain " << domain << " has " << cached_sitemaps.size() << " cached sitemaps" << std::endl;
        
        if (cached_sitemaps.empty()) {
            // No sitemaps in cache, robots.txt will be fetched by the crawler
            // when it encounters this domain
            // std::cout << "⚠️  No sitemaps in cache for domain: " << domain << std::endl;
            continue;
        }
        
        std::lock_guard<std::mutex> lock(sitemaps_mutex_);
        for (const auto& cached_sitemap : cached_sitemaps) {
            // Validate sitemap URL before processing
            if (cached_sitemap.url.empty()) {
                // std::cerr << "⚠️  WARNING: Empty sitemap URL found for domain " << domain << std::endl;
                continue;
            }
            
            // Check if we already have this sitemap
            bool already_exists = false;
            for (const auto& existing : sitemaps_) {
                if (existing.sitemap_url == cached_sitemap.url) {
                    already_exists = true;
                    break;
                }
            }
            
            if (!already_exists) {
                // Double-check URL validation before creating SitemapInfo
                if (cached_sitemap.url.empty()) {
                    std::cerr << "⚠️  CRITICAL: Empty sitemap URL from robots cache for domain " << domain << ", skipping creation" << std::endl;
                    continue;
                }
                
                if (cached_sitemap.url.find("http://") != 0 && cached_sitemap.url.find("https://") != 0) {
                    std::cerr << "⚠️  CRITICAL: Invalid sitemap URL from robots cache: " << cached_sitemap.url << std::endl;
                    continue;
                }
                
                SitemapInfo sitemap(cached_sitemap.url, cached_sitemap.priority);
                sitemap.parse_interval_hours = cached_sitemap.parse_interval_hours;
                
                // Final validation before adding to vector
                if (!sitemap.enabled || sitemap.sitemap_url.empty()) {
                    std::cerr << "⚠️  CRITICAL: Created SitemapInfo is invalid, not adding to vector" << std::endl;
                    continue;
                }
                
                sitemaps_.push_back(sitemap);
                // std::cout << "🗺️  Added sitemap from robots cache: " << cached_sitemap.url 
                //          << " (priority: " << cached_sitemap.priority << ")" << std::endl;
            } else {
                std::cout << "🔄 Sitemap already exists: " << cached_sitemap.url << std::endl;
            }
        }
    }
}

void SitemapParser::start_parsing() {
    // Validate and recover from any corrupted cache state before starting
    // if (!validate_and_recover_cache()) {
    //     std::cout << "⚠️  WARNING: Cache validation failed, but continuing with limited functionality" << std::endl;
    // }
    
    parser_thread_ = std::thread(&SitemapParser::parser_worker, this);
    std::cout << "Sitemap parser started" << std::endl;
}

void SitemapParser::stop() {
    std::cout << "Stopping sitemap parser..." << std::endl;
    shutdown_ = true;
    
    // Notify the worker thread to wake up and check shutdown flag
    {
        std::lock_guard<std::mutex> lock(shutdown_mutex_);
        shutdown_cv_.notify_one();
    }
    
    // Wait for the thread to finish
    if (parser_thread_.joinable()) {
        parser_thread_.join();
    }
    
    std::cout << "Sitemap parser stopped gracefully" << std::endl;
}

void SitemapParser::parser_worker() {
    while (!shutdown_) {
        try {
            // Check shutdown flag before expensive operations
            if (shutdown_) {
                break;
            }
            
            // First, refresh sitemaps from robots cache
            refresh_sitemaps_from_robots_cache();
            
            // Check shutdown flag again after DB operations
            if (shutdown_) {
                break;
            }
            
            std::vector<SitemapUrl> new_urls;
        
        {
            std::lock_guard<std::mutex> lock(sitemaps_mutex_);
            std::vector<SitemapInfo> new_sitemaps_to_add; // Collect new sitemaps here
            
            for (auto& sitemap : sitemaps_) {
                // Check shutdown flag during sitemap processing
                if (shutdown_) {
                    std::cout << "🛑 Sitemap processing interrupted by shutdown request" << std::endl;
                    return;
                }
                
                if (!sitemap.enabled) {
                    continue; // Skip disabled sitemaps
                }
                
                if (sitemap.is_ready_for_parse()) {
                    // std::cout << "Parsing sitemap: " << sitemap.sitemap_url << std::endl;
                    
                    std::string content = download_sitemap(sitemap.sitemap_url);
                    if (!content.empty()) {
                        // Check shutdown again after network operation
                        if (shutdown_) {
                            std::cout << "🛑 Sitemap download interrupted by shutdown request" << std::endl;
                            return;
                        }
                        
                        // Check if this is a sitemap index
                        if (content.find("<sitemapindex") != std::string::npos) {
                            sitemap.is_index = true;
                            std::vector<std::string> child_sitemaps = parse_sitemap_index(content);
                            
                            // Collect child sitemaps to add after loop completes
                            for (const auto& child_url : child_sitemaps) {
                                // Validate child URL before processing
                                if (child_url.empty()) {
                                    std::cerr << "⚠️  WARNING: Empty child sitemap URL from index, skipping..." << std::endl;
                                    continue;
                                }
                                
                                if (child_url.find("http://") != 0 && child_url.find("https://") != 0) {
                                    std::cerr << "⚠️  WARNING: Invalid child sitemap URL: " << child_url << std::endl;
                                    continue;
                                }
                                
                                bool already_exists = false;
                                for (const auto& existing : sitemaps_) {
                                    if (existing.sitemap_url == child_url) {
                                        already_exists = true;
                                        break;
                                    }
                                }
                                if (!already_exists) {
                                    SitemapInfo child_sitemap(child_url);
                                    child_sitemap.parse_interval_hours = sitemap.parse_interval_hours;
                                    new_sitemaps_to_add.push_back(child_sitemap);
                                    // std::cout << "Prepared child sitemap: " << child_url << std::endl;
                                }
                            }
                        } else {
                            // Regular sitemap
                            std::vector<SitemapUrl> urls = parse_sitemap_xml(content);
                            
                            // Filter for new URLs and recently modified ones
                            for (const auto& url : urls) {
                                bool is_new = false;
                                {
                                    std::lock_guard<std::mutex> disc_lock(discovered_mutex_);
                                    if (discovered_urls_.find(url.url) == discovered_urls_.end()) {
                                        discovered_urls_.insert(url.url);
                                        is_new = true;
                                    }
                                }
                                
                                if (is_new || is_recently_modified(url.last_modified)) {
                                    new_urls.push_back(url);
                                }
                            }
                        }
                        
                        sitemap.record_success();
                        // std::cout << "Parsed sitemap successfully, found " << new_urls.size() << " new/updated URLs" << std::endl;
                    } else {
                        sitemap.record_failure();
                        // std::cout << "Failed to download sitemap: " << sitemap.sitemap_url << std::endl;
                    }
                }
            }
            
            // Now safely add all new sitemaps after iteration is complete
            if (!new_sitemaps_to_add.empty()) {
                sitemaps_.insert(sitemaps_.end(), new_sitemaps_to_add.begin(), new_sitemaps_to_add.end());
                std::cout << "Added " << new_sitemaps_to_add.size() << " new child sitemaps for processing" << std::endl;
            }
        }
        
        // Forward new URLs to crawler
        if (!new_urls.empty() && url_callback_) {
            try {
                url_callback_(new_urls);
            } catch (const std::exception& e) {
                std::cerr << "Error in sitemap callback: " << e.what() << std::endl;
            } catch (...) {
                std::cerr << "Unknown error in sitemap callback" << std::endl;
            }
        }
        
        // Sleep for 1 hour before next check, but wake up immediately on shutdown
        std::unique_lock<std::mutex> lock(shutdown_mutex_);
        if (!shutdown_cv_.wait_for(lock, std::chrono::hours(1), [this] { return shutdown_.load(); })) {
            // Timeout occurred (1 hour passed), continue with next iteration
            if (shutdown_) {
                break; // Double-check shutdown flag after timeout
            }
        }
        // If shutdown flag is set, the loop will exit on next iteration
        
        } catch (const std::exception& e) {
            std::cerr << "Error in sitemap parser worker: " << e.what() << std::endl;
            
            // Check shutdown before retrying
            if (shutdown_) {
                break;
            }
            
            // Short sleep before retry, but allow immediate shutdown
            std::unique_lock<std::mutex> lock(shutdown_mutex_);
            shutdown_cv_.wait_for(lock, std::chrono::seconds(10), [this] { return shutdown_.load(); });
        } catch (...) {
            std::cerr << "Unknown error in sitemap parser worker" << std::endl;
            
            // Check shutdown before retrying
            if (shutdown_) {
                break;
            }
            
            // Short sleep before retry, but allow immediate shutdown
            std::unique_lock<std::mutex> lock(shutdown_mutex_);
            shutdown_cv_.wait_for(lock, std::chrono::seconds(10), [this] { return shutdown_.load(); });
        }
    }
}

std::string SitemapParser::download_sitemap(const std::string& sitemap_url) {
    // Validate URL is not empty
    if (sitemap_url.empty()) {
        std::cerr << "Error: Empty sitemap URL provided to download_sitemap" << std::endl;
        return "";
    }
    
    // Basic URL validation
    if (sitemap_url.find("http://") != 0 && sitemap_url.find("https://") != 0) {
        std::cerr << "Error: Invalid sitemap URL (missing protocol): " << sitemap_url << std::endl;
        return "";
    }
    
    if (!http_client_) {
        std::cerr << "No HTTP client available for sitemap download: " << sitemap_url << std::endl;
        return "";
    }
    
    try {
        auto response = http_client_->download_sitemap(sitemap_url);
        
        // *** IMPROVED ERROR CHECKING AND LOGGING ***
        
        // Check for cURL-level errors first (e.g., connection timed out)
        if (!response.success) {
            // std::cerr << "Failed to download sitemap " << sitemap_url << " (cURL Error): " 
            //           << HttpClient::curl_error_string(response.curl_code) << std::endl;
            return "";
        }
        
        // Check for HTTP-level errors (e.g., 404 Not Found, 403 Forbidden)
        if (response.headers.status_code != 200) {
            // std::cerr << "Failed to download sitemap " << sitemap_url 
            //           << " (HTTP Status: " << response.headers.status_code << ")" << std::endl;
            return "";
        }
        
        // std::cout << "✅ Successfully downloaded sitemap: " << sitemap_url 
        //           << " (" << response.body.size() << " bytes)" << std::endl;
        return response.body;
        
    } catch (const std::exception& e) {
        std::cerr << "Exception during sitemap download for " << sitemap_url << ": " << e.what() << std::endl;
        return "";
    }
}

std::vector<std::string> SitemapParser::parse_sitemap_index(const std::string& index_content) {
    std::vector<std::string> sitemap_urls;
    
    XMLDocument doc;
    XMLError result = doc.Parse(index_content.c_str());
    
    if (result != XML_SUCCESS) {
        std::cerr << "Failed to parse sitemap index XML: " << result << std::endl;
        return sitemap_urls;
    }
    
    // Find the sitemapindex root element
    XMLElement* sitemapindex = doc.FirstChildElement("sitemapindex");
    if (!sitemapindex) {
        std::cerr << "No sitemapindex element found in XML" << std::endl;
        return sitemap_urls;
    }
    
    // Iterate through all <sitemap> elements
    for (XMLElement* sitemap = sitemapindex->FirstChildElement("sitemap");
         sitemap != nullptr;
         sitemap = sitemap->NextSiblingElement("sitemap")) {
        
        XMLElement* loc = sitemap->FirstChildElement("loc");
        if (loc && loc->GetText()) {
            sitemap_urls.push_back(loc->GetText());
        }
    }
    
    return sitemap_urls;
}

std::vector<SitemapUrl> SitemapParser::parse_sitemap_xml(const std::string& sitemap_content) {
    std::vector<SitemapUrl> urls;
    
    XMLDocument doc;
    XMLError result = doc.Parse(sitemap_content.c_str());
    
    if (result != XML_SUCCESS) {
        std::cerr << "Failed to parse sitemap XML: " << result << std::endl;
        return urls;
    }
    
    // Find the urlset root element
    XMLElement* urlset = doc.FirstChildElement("urlset");
    if (!urlset) {
        std::cerr << "No urlset element found in sitemap XML" << std::endl;
        return urls;
    }
    
    // Iterate through all <url> elements
    for (XMLElement* url_elem = urlset->FirstChildElement("url");
         url_elem != nullptr;
         url_elem = url_elem->NextSiblingElement("url")) {
        
        SitemapUrl sitemap_url;
        
        // Extract location (required)
        XMLElement* loc = url_elem->FirstChildElement("loc");
        if (!loc || !loc->GetText()) {
            continue; // Skip if no URL
        }
        sitemap_url.url = loc->GetText();
        
        // Extract last modified date
        XMLElement* lastmod = url_elem->FirstChildElement("lastmod");
        if (lastmod && lastmod->GetText()) {
            // Parse ISO 8601 date format
            sitemap_url.last_modified = parse_iso8601_date(lastmod->GetText());
        }
        
        // Extract change frequency
        XMLElement* changefreq = url_elem->FirstChildElement("changefreq");
        if (changefreq && changefreq->GetText()) {
            sitemap_url.change_frequency = changefreq->GetText();
        }
        
        // Extract priority
        XMLElement* priority = url_elem->FirstChildElement("priority");
        if (priority && priority->GetText()) {
            try {
                sitemap_url.priority = std::stof(priority->GetText());
                // Clamp priority between 0.0 and 1.0
                sitemap_url.priority = std::max(0.0f, std::min(1.0f, sitemap_url.priority));
            } catch (...) {
                sitemap_url.priority = 0.5f; // Default
            }
        }
        
        urls.push_back(sitemap_url);
    }
    
    return urls;
}

bool SitemapParser::is_recently_modified(const std::chrono::system_clock::time_point& last_mod, int hours_threshold) {
    auto now = std::chrono::system_clock::now();
    auto threshold = now - std::chrono::hours(hours_threshold);
    return last_mod >= threshold;
}

size_t SitemapParser::get_active_sitemaps_count() const {
    std::lock_guard<std::mutex> lock(sitemaps_mutex_);
    return std::count_if(sitemaps_.begin(), sitemaps_.end(), 
                        [](const SitemapInfo& sitemap) { return sitemap.enabled; });
}

void SitemapParser::print_sitemap_stats() const {
    size_t total_sitemaps;
    size_t active_sitemaps;
    size_t discovered_urls_count;
    std::vector<SitemapInfo> sitemap_copy;
    
    // Get all data while holding locks, then print without locks
    {
        std::lock_guard<std::mutex> lock(sitemaps_mutex_);
        total_sitemaps = sitemaps_.size();
        active_sitemaps = std::count_if(sitemaps_.begin(), sitemaps_.end(), 
                                      [](const SitemapInfo& sitemap) { return sitemap.enabled; });
        sitemap_copy = sitemaps_; // Copy for printing later
    }
    
    {
        std::lock_guard<std::mutex> disc_lock(discovered_mutex_);
        discovered_urls_count = discovered_urls_.size();
    }
    
    // Now print without holding any locks
    std::cout << "\n=== Sitemap Parser Statistics ===" << std::endl;
    std::cout << "Total sitemaps: " << total_sitemaps << std::endl;
    std::cout << "Active sitemaps: " << active_sitemaps << std::endl;
    std::cout << "Discovered URLs: " << discovered_urls_count << std::endl;
    
    // for (const auto& sitemap : sitemap_copy) {
    //     std::cout << "Sitemap: " << sitemap.sitemap_url 
    //               << " | Interval: " << sitemap.parse_interval_hours << "h"
    //               << " | Failures: " << sitemap.consecutive_failures
    //               << " | Index: " << (sitemap.is_index ? "Yes" : "No")
    //               << " | Enabled: " << (sitemap.enabled ? "Yes" : "No") << std::endl;
    // }
    std::cout << "==================================\n" << std::endl;
}

bool SitemapParser::validate_and_recover_cache() {
    std::cout << "🔍 Validating sitemap cache integrity..." << std::endl;
    
    // Get a sample of domains to test cache health
    std::vector<std::string> test_domains;
    {
        std::lock_guard<std::mutex> lock(domains_mutex_);
        // Test up to 3 domains to avoid slow startup
        size_t test_count = std::min(static_cast<size_t>(3), monitored_domains_.size());
        for (size_t i = 0; i < test_count; ++i) {
            test_domains.push_back(monitored_domains_[i]);
        }
    }
    
    bool cache_healthy = true;
    size_t successful_tests = 0;
    
    for (const auto& domain : test_domains) {
        try {
            // Test if we can read from the robots cache without exceptions
            auto sitemaps = robots_cache_->get_sitemaps_for_domain(domain);
            successful_tests++;
            
            // Log the test result
            std::cout << "✅ Cache test passed for domain: " << domain 
                     << " (" << sitemaps.size() << " sitemaps)" << std::endl;
                     
        } catch (const std::exception& e) {
            std::cerr << "❌ Cache test failed for domain " << domain << ": " << e.what() << std::endl;
            cache_healthy = false;
        } catch (...) {
            std::cerr << "❌ Cache test failed for domain " << domain << ": Unknown error" << std::endl;
            cache_healthy = false;
        }
        
        // Avoid spamming during startup
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    
    if (cache_healthy && successful_tests > 0) {
        std::cout << "✅ Cache validation passed (" << successful_tests << "/" << test_domains.size() << " tests successful)" << std::endl;
        return true;
    } else if (successful_tests == 0 && !test_domains.empty()) {
        std::cout << "⚠️  WARNING: All cache tests failed - cache may be corrupted. Continuing with degraded performance." << std::endl;
        std::cout << "💡 TIP: If problems persist, clear the cache directory and restart the crawler" << std::endl;
        return false;
    } else {
        std::cout << "✅ Cache validation completed with partial success (" << successful_tests << "/" << test_domains.size() << " tests)" << std::endl;
        return true;
    }
}

} // namespace SitemapParsing
