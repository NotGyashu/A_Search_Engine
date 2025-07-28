#include "robots_txt_cache.h"
#include "http_client.h"
#include <algorithm>
#include <sstream>
#include <iostream>
#include <thread>

RobotsTxtCache::RobotsTxtCache(HttpClient* client) : http_client_(client) {}

bool RobotsTxtCache::is_allowed(const std::string& domain, const std::string& path, const std::string& user_agent) {
    std::unique_lock<std::mutex> lock(mutex_);
    
    auto it = cache_.find(domain);
    if (it == cache_.end()) {
        // Domain not in cache - we must fetch robots.txt and wait for completion
        std::cout << "Domain " << domain << " not in robots.txt cache. Fetching..." << std::endl;
        
        // Create entry with fetch promise
        RobotsInfo info;
        info.is_fetching = true;
        info.fetch_promise = std::make_shared<std::promise<void>>();
        auto future = info.fetch_promise->get_future();
        
        cache_[domain] = std::move(info);
        lock.unlock(); // Release lock before async operation
        
        // Start async fetch (this could be improved to avoid blocking here)
        std::thread([this, domain]() {
            this->fetch_and_cache_async(domain);
        }).detach();
        
        // Wait for fetch to complete
        std::cout << "Waiting for robots.txt fetch for domain: " << domain << std::endl;
        future.wait();
        
        // Re-acquire lock and check result
        lock.lock();
        it = cache_.find(domain);
        if (it == cache_.end()) {
            std::cerr << "Failed to fetch robots.txt for domain: " << domain << std::endl;
            return false; // Deny access if fetch failed
        }
    }
    
    const auto& info = it->second;
    
    // Check if cache is expired
    auto now = std::chrono::steady_clock::now();
    if (now - info.timestamp > cache_expiry_) {
        cache_.erase(it);
        // Recursively call is_allowed to trigger fresh fetch
        lock.unlock();
        return is_allowed(domain, path, user_agent);
    }
    
    if (!info.is_valid) {
        return true; // Allow if robots.txt was invalid/empty
    }
    
    // Simple parsing - check for disallowed patterns
    std::istringstream stream(info.content);
    std::string line;
    bool in_relevant_section = false;
    
    while (std::getline(stream, line)) {
        // Convert to lowercase for comparison
        std::transform(line.begin(), line.end(), line.begin(), ::tolower);
        
        if (line.find("user-agent:") == 0) {
            std::string agent = line.substr(11);
            agent.erase(0, agent.find_first_not_of(" \t"));
            in_relevant_section = (agent == "*" || agent == user_agent);
        }
        else if (in_relevant_section && line.find("disallow:") == 0) {
            std::string disallowed = line.substr(9);
            disallowed.erase(0, disallowed.find_first_not_of(" \t"));
            
            if (disallowed == "/" || path.find(disallowed) == 0) {
                return false;
            }
        }
    }
    
    return true; // Allow by default
}

void RobotsTxtCache::add_robots_txt(const std::string& domain, const std::string& content) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    RobotsInfo info;
    info.content = content;
    info.timestamp = std::chrono::steady_clock::now();
    info.is_valid = !content.empty();
    
    cache_[domain] = std::move(info);
}

void RobotsTxtCache::fetch_and_cache(const std::string& domain) {
    // Public method - for external use, just trigger async fetch without waiting
    std::lock_guard<std::mutex> lock(mutex_);
    
    auto it = cache_.find(domain);
    if (it != cache_.end() && !it->second.is_fetching) {
        return; // Already cached and not currently fetching
    }
    
    if (it == cache_.end()) {
        // Create entry for async fetch
        RobotsInfo info;
        info.is_fetching = true;
        info.fetch_promise = std::make_shared<std::promise<void>>();
        cache_[domain] = std::move(info);
        
        // Start async fetch
        std::thread([this, domain]() {
            this->fetch_and_cache_async(domain);
        }).detach();
    }
}

void RobotsTxtCache::fetch_and_cache_async(const std::string& domain) {
    std::cout << "Fetching robots.txt for domain: " << domain << std::endl;
    
    std::string robots_content;
    bool fetch_successful = false;
    
    if (http_client_) {
        try {
            auto response = http_client_->download_robots_txt(domain);
            
            if (response.success && response.headers.status_code == 200) {
                robots_content = response.body;
                fetch_successful = true;
                std::cout << "Successfully fetched robots.txt for " << domain 
                          << " (" << robots_content.size() << " bytes)" << std::endl;
            } else {
                std::cout << "Failed to fetch robots.txt for " << domain 
                          << " (status: " << response.headers.status_code << ")" << std::endl;
                // Empty robots.txt means allow all
                robots_content = "";
                fetch_successful = true;
            }
        } catch (const std::exception& e) {
            std::cerr << "Exception fetching robots.txt for " << domain << ": " << e.what() << std::endl;
            robots_content = ""; // Allow all on error
            fetch_successful = true;
        }
    } else {
        std::cerr << "No HTTP client available for robots.txt fetch" << std::endl;
        robots_content = ""; // Allow all if no client
        fetch_successful = true;
    }
    
    // Update cache with result
    {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = cache_.find(domain);
        if (it != cache_.end()) {
            it->second.content = robots_content;
            it->second.timestamp = std::chrono::steady_clock::now();
            it->second.is_valid = fetch_successful;
            it->second.is_fetching = false;
            
            // Notify waiting threads
            if (it->second.fetch_promise) {
                it->second.fetch_promise->set_value();
                it->second.fetch_promise.reset();
            }
        }
    }
}

void RobotsTxtCache::clear_expired() {
    std::lock_guard<std::mutex> lock(mutex_);
    
    auto now = std::chrono::steady_clock::now();
    auto it = cache_.begin();
    
    while (it != cache_.end()) {
        if (now - it->second.timestamp > cache_expiry_) {
            it = cache_.erase(it);
        } else {
            ++it;
        }
    }
}

size_t RobotsTxtCache::size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return cache_.size();
}
