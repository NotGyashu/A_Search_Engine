#include "conditional_get.h"
#include "http_client.h"
#include "connection_pool.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <cctype>

namespace ConditionalGet {

bool ConditionalGetManager::should_download(const std::string& url) {
    std::lock_guard<std::mutex> lock(cache_mutex_);
    auto it = url_cache_.find(url);
    
    if (it == url_cache_.end()) {
        return true; // No cache info, should download
    }
    
    const auto& headers = it->second;
    
    // If we have cache info, we can try conditional GET
    return headers.has_cache_info();
}

ConditionalGetManager::ConditionalGetResult ConditionalGetManager::conditional_get(const std::string& url) {
    ConditionalGetResult result;
    
    // Get cached headers
    HttpHeaders cached_headers;
    {
        std::lock_guard<std::mutex> lock(cache_mutex_);
        auto it = url_cache_.find(url);
        if (it != url_cache_.end()) {
            cached_headers = it->second;
        }
    }
    
    try {
        // Create a temporary connection pool for this request
        ConnectionPool pool;
        HttpClient client(pool);
        HttpClient::HttpResponse response;
        
        if (cached_headers.has_cache_info()) {
            // Build conditional headers using RequestOptions
            HttpClient::RequestOptions options;
            
            if (!cached_headers.etag.empty()) {
                options.if_none_match = cached_headers.etag;
            }
            
            if (!cached_headers.last_modified.empty()) {
                options.if_modified_since = cached_headers.last_modified;
            }
            
            // Perform conditional GET request
            response = client.get(url, options);
            
            // Check if content was not modified
            if (response.not_modified) {
                result.content_changed = false;
                result.http_status = 304;
                result.headers = cached_headers;
                std::cout << "Conditional GET: Content not modified for " << url << std::endl;
                return result;
            }
        } else {
            // No cache info, perform regular GET
            response = client.get(url);
        }
        
        // Parse response headers - convert HttpClient::HttpHeaders to our HttpHeaders
        result.headers.etag = response.headers.etag;
        result.headers.last_modified = response.headers.last_modified;
        result.headers.response_time = std::chrono::system_clock::now();
        
        result.content = response.body;
        result.content_changed = true;
        result.http_status = response.headers.status_code;
        
        // Update cache
        update_cache(url, result.headers);
        
        std::cout << "Conditional GET: Content downloaded for " << url 
                  << " (status: " << result.http_status << ")" << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "Error in conditional GET for " << url << ": " << e.what() << std::endl;
        result.content_changed = true; // Assume changed on error
        result.http_status = 0;
    }
    
    return result;
}

void ConditionalGetManager::update_cache(const std::string& url, const HttpHeaders& headers) {
    std::lock_guard<std::mutex> lock(cache_mutex_);
    url_cache_[url] = headers;
}

HttpHeaders ConditionalGetManager::get_cache_info(const std::string& url) {
    std::lock_guard<std::mutex> lock(cache_mutex_);
    auto it = url_cache_.find(url);
    if (it != url_cache_.end()) {
        return it->second;
    }
    return HttpHeaders();
}

void ConditionalGetManager::clear_cache(const std::string& url) {
    std::lock_guard<std::mutex> lock(cache_mutex_);
    url_cache_.erase(url);
}

size_t ConditionalGetManager::get_cache_size() const {
    std::lock_guard<std::mutex> lock(const_cast<std::mutex&>(cache_mutex_));
    return url_cache_.size();
}

void ConditionalGetManager::print_cache_stats() const {
    std::lock_guard<std::mutex> lock(const_cast<std::mutex&>(cache_mutex_));
    std::cout << "\n=== Conditional GET Cache Statistics ===" << std::endl;
    std::cout << "Cached URLs: " << url_cache_.size() << std::endl;
    
    int etag_count = 0;
    int lastmod_count = 0;
    
    for (const auto& pair : url_cache_) {
        if (!pair.second.etag.empty()) etag_count++;
        if (!pair.second.last_modified.empty()) lastmod_count++;
    }
    
    std::cout << "URLs with ETag: " << etag_count << std::endl;
    std::cout << "URLs with Last-Modified: " << lastmod_count << std::endl;
    std::cout << "========================================\n" << std::endl;
}

bool ConditionalGetManager::save_cache_to_file(const std::string& cache_file_path) {
    std::lock_guard<std::mutex> lock(cache_mutex_);
    
    std::ofstream file(cache_file_path);
    if (!file.is_open()) {
        std::cerr << "Error: Could not open cache file for writing: " << cache_file_path << std::endl;
        return false;
    }
    
    // Simple format: URL|ETag|Last-Modified|ResponseTime
    for (const auto& pair : url_cache_) {
        const auto& url = pair.first;
        const auto& headers = pair.second;
        
        auto time_t = std::chrono::system_clock::to_time_t(headers.response_time);
        
        file << url << "|" 
             << headers.etag << "|" 
             << headers.last_modified << "|" 
             << time_t << std::endl;
    }
    
    std::cout << "Saved " << url_cache_.size() << " cache entries to " << cache_file_path << std::endl;
    return true;
}

bool ConditionalGetManager::load_cache_from_file(const std::string& cache_file_path) {
    std::ifstream file(cache_file_path);
    if (!file.is_open()) {
        std::cout << "No existing cache file found: " << cache_file_path << std::endl;
        return false;
    }
    
    std::lock_guard<std::mutex> lock(cache_mutex_);
    url_cache_.clear();
    
    std::string line;
    int loaded_count = 0;
    
    while (std::getline(file, line)) {
        if (line.empty()) continue;
        
        // Parse: URL|ETag|Last-Modified|ResponseTime
        std::vector<std::string> parts;
        std::stringstream ss(line);
        std::string part;
        
        while (std::getline(ss, part, '|')) {
            parts.push_back(part);
        }
        
        if (parts.size() >= 4) {
            HttpHeaders headers;
            headers.etag = parts[1];
            headers.last_modified = parts[2];
            
            try {
                std::time_t time_t = std::stoll(parts[3]);
                headers.response_time = std::chrono::system_clock::from_time_t(time_t);
            } catch (...) {
                headers.response_time = std::chrono::system_clock::now();
            }
            
            url_cache_[parts[0]] = headers;
            loaded_count++;
        }
    }
    
    std::cout << "Loaded " << loaded_count << " cache entries from " << cache_file_path << std::endl;
    return true;
}

} // namespace ConditionalGet
