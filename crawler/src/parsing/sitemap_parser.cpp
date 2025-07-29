#include "sitemap_parser.h"
// #include "utils.h"  // Commented out - no specific utils needed
#include "config_loader.h"
#include "http_client.h"
#include "utility_functions.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <ctime>
#include <iomanip>
#include <tinyxml2.h>

using namespace tinyxml2;

namespace SitemapParsing {

SitemapParser::SitemapParser(std::function<void(const std::vector<SitemapUrl>&)> callback, HttpClient* client)
    : url_callback_(std::move(callback)), http_client_(client) {
}

SitemapParser::~SitemapParser() {
    shutdown_ = true;
    if (parser_thread_.joinable()) {
        parser_thread_.join();
    }
}

bool SitemapParser::load_sitemaps_from_file(const std::string& sitemaps_file_path) {
    std::ifstream file(sitemaps_file_path);
    if (!file.is_open()) {
        std::cerr << "Warning: Could not open sitemaps file: " << sitemaps_file_path << std::endl;
        return false;
    }
    
    std::lock_guard<std::mutex> lock(sitemaps_mutex_);
    std::string line;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') continue; // Skip comments and empty lines
        
        // Format: sitemap_url parse_interval_hours
        std::istringstream iss(line);
        std::string sitemap_url;
        int interval = 24; // Default
        
        iss >> sitemap_url >> interval;
        if (!sitemap_url.empty()) {
            SitemapInfo sitemap(sitemap_url);
            sitemap.parse_interval_hours = interval;
            sitemaps_.push_back(sitemap);
        }
    }
    
    std::cout << "Loaded " << sitemaps_.size() << " sitemaps from " << sitemaps_file_path << std::endl;
    return true;
}

bool SitemapParser::load_sitemaps_from_json(const std::string& json_file_path) {
    auto sitemap_configs = ConfigLoader::load_sitemap_configs(json_file_path);
    if (sitemap_configs.empty()) {
        std::cerr << "Warning: No sitemaps loaded from " << json_file_path << std::endl;
        return false;
    }
    
    std::lock_guard<std::mutex> lock(sitemaps_mutex_);
    for (const auto& config : sitemap_configs) {
        SitemapInfo sitemap(config.url);
        sitemap.parse_interval_hours = 24; // Default interval
        // Use priority as a hint for parsing frequency if needed
        if (config.priority >= 9) {
            sitemap.parse_interval_hours = 12; // High priority: parse twice daily
        } else if (config.priority <= 6) {
            sitemap.parse_interval_hours = 48; // Low priority: parse every 2 days
        }
        sitemaps_.push_back(sitemap);
    }
    
    std::cout << "🗺️  Loaded " << sitemaps_.size() << " sitemaps from " << json_file_path << std::endl;
    return true;
}

void SitemapParser::add_sitemap(const std::string& sitemap_url, int parse_interval_hours) {
    std::lock_guard<std::mutex> lock(sitemaps_mutex_);
    SitemapInfo sitemap(sitemap_url);
    sitemap.parse_interval_hours = parse_interval_hours;
    sitemaps_.push_back(sitemap);
    std::cout << "Added sitemap: " << sitemap_url << std::endl;
}

void SitemapParser::auto_discover_sitemaps(const std::vector<std::string>& domains) {
    for (const auto& domain : domains) {
        discover_sitemap_from_robots_txt(domain);
    }
}

void SitemapParser::discover_sitemap_from_robots_txt(const std::string& domain) {
    std::cout << "Checking robots.txt for sitemaps: " << domain << std::endl;
    
    if (!http_client_) {
        std::cerr << "No HTTP client available for robots.txt discovery" << std::endl;
        return;
    }
    
    try {
        auto response = http_client_->download_robots_txt(domain);
        
        if (!response.success || response.body.empty()) {
            std::cout << "Could not retrieve robots.txt from " << domain << std::endl;
        } else {
            // Parse robots.txt for sitemap entries
            std::istringstream stream(response.body);
            std::string line;
            
            while (std::getline(stream, line)) {
                // Convert to lowercase for comparison
                std::string lower_line = line;
                std::transform(lower_line.begin(), lower_line.end(), lower_line.begin(), ::tolower);
                
                if (lower_line.find("sitemap:") == 0) {
                    // Extract sitemap URL
                    size_t url_start = line.find(':', 0) + 1;
                    std::string sitemap_url = line.substr(url_start);
                    
                    // Trim whitespace
                    sitemap_url.erase(0, sitemap_url.find_first_not_of(" \t"));
                    sitemap_url.erase(sitemap_url.find_last_not_of(" \t\r\n") + 1);
                    
                    if (!sitemap_url.empty()) {
                        add_sitemap(sitemap_url, 24); // Parse daily
                        std::cout << "Discovered sitemap from robots.txt: " << sitemap_url << std::endl;
                    }
                }
            }
        }
        
        // Try common sitemap locations as fallback
        std::vector<std::string> common_paths = {"/sitemap.xml", "/sitemap_index.xml", "/sitemaps.xml"};
        for (const auto& path : common_paths) {
            std::string test_url = domain;
            if (test_url.find("://") == std::string::npos) {
                test_url = "https://" + test_url;
            }
            if (test_url.back() != '/') {
                test_url += "/";
            }
            test_url += path.substr(1); // Remove leading slash
            
            try {
                auto test_response = http_client_->download_sitemap(test_url);
                if (test_response.success && !test_response.body.empty() && 
                    (test_response.body.find("<urlset") != std::string::npos || 
                     test_response.body.find("<sitemapindex") != std::string::npos)) {
                    std::cout << "Found sitemap at common location: " << test_url << std::endl;
                    add_sitemap(test_url, 24); // Parse daily
                }
            } catch (...) {
                // Ignore failures for common path tests
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception discovering sitemaps from robots.txt for " << domain << ": " << e.what() << std::endl;
    }
}

void SitemapParser::start_parsing() {
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
            std::vector<SitemapUrl> new_urls;
        
        {
            std::lock_guard<std::mutex> lock(sitemaps_mutex_);
            for (auto& sitemap : sitemaps_) {
                if (sitemap.is_ready_for_parse()) {
                    // std::cout << "Parsing sitemap: " << sitemap.sitemap_url << std::endl;
                    
                    std::string content = download_sitemap(sitemap.sitemap_url);
                    if (!content.empty()) {
                        // Check if this is a sitemap index
                        if (content.find("<sitemapindex") != std::string::npos) {
                            sitemap.is_index = true;
                            std::vector<std::string> child_sitemaps = parse_sitemap_index(content);
                            
                            // Add child sitemaps to our list
                            std::vector<SitemapInfo> new_child_sitemaps;

for (const auto& child_url : child_sitemaps) {
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
        new_child_sitemaps.push_back(child_sitemap);
        // std::cout << "Prepared child sitemap: " << child_url << std::endl;
    }
}

sitemaps_.insert(sitemaps_.end(), new_child_sitemaps.begin(), new_child_sitemaps.end());

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
                        std::cout << "Failed to download sitemap: " << sitemap.sitemap_url << std::endl;
                    }
                }
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
        }
        // If shutdown flag is set, the loop will exit on next iteration
        
        } catch (const std::exception& e) {
            std::cerr << "Error in sitemap parser worker: " << e.what() << std::endl;
            // Short sleep before retry, but allow immediate shutdown
            std::unique_lock<std::mutex> lock(shutdown_mutex_);
            shutdown_cv_.wait_for(lock, std::chrono::seconds(10), [this] { return shutdown_.load(); });
        } catch (...) {
            std::cerr << "Unknown error in sitemap parser worker" << std::endl;
            // Short sleep before retry, but allow immediate shutdown
            std::unique_lock<std::mutex> lock(shutdown_mutex_);
            shutdown_cv_.wait_for(lock, std::chrono::seconds(10), [this] { return shutdown_.load(); });
        }
    }
}

} // namespace SitemapParsing

namespace SitemapParsing {

std::string SitemapParser::download_sitemap(const std::string& sitemap_url) {
    if (!http_client_) {
        std::cerr << "No HTTP client available for sitemap download: " << sitemap_url << std::endl;
        return "";
    }
    
    try {
        auto response = http_client_->download_sitemap(sitemap_url);
        
        // *** IMPROVED ERROR CHECKING AND LOGGING ***
        
        // Check for cURL-level errors first (e.g., connection timed out)
        if (!response.success) {
            std::cerr << "Failed to download sitemap " << sitemap_url << " (cURL Error): " 
                      << HttpClient::curl_error_string(response.curl_code) << std::endl;
            return "";
        }
        
        // Check for HTTP-level errors (e.g., 404 Not Found, 403 Forbidden)
        if (response.headers.status_code != 200) {
            std::cerr << "Failed to download sitemap " << sitemap_url 
                      << " (HTTP Status: " << response.headers.status_code << ")" << std::endl;
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
    std::lock_guard<std::mutex> lock(sitemaps_mutex_);
    std::cout << "\n=== Sitemap Parser Statistics ===" << std::endl;
    std::cout << "Total sitemaps: " << sitemaps_.size() << std::endl;
    std::cout << "Active sitemaps: " << get_active_sitemaps_count() << std::endl;
    
    {
        std::lock_guard<std::mutex> disc_lock(discovered_mutex_);
        std::cout << "Discovered URLs: " << discovered_urls_.size() << std::endl;
    }
    
    for (const auto& sitemap : sitemaps_) {
        std::cout << "Sitemap: " << sitemap.sitemap_url 
                  << " | Interval: " << sitemap.parse_interval_hours << "h"
                  << " | Failures: " << sitemap.consecutive_failures
                  << " | Index: " << (sitemap.is_index ? "Yes" : "No")
                  << " | Enabled: " << (sitemap.enabled ? "Yes" : "No") << std::endl;
    }
    std::cout << "==================================\n" << std::endl;
}

} // namespace SitemapParsing
