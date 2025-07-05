#include "utils.h"
#include <curl/curl.h>
#include <iostream>
#include <fstream>
#include <regex>
#include <algorithm>
#include <thread>
#include <chrono>
#include <filesystem>

namespace fs = std::filesystem;

/**
 * cURL write callback for robots.txt content
 * 
 * @param contents Pointer to the data buffer
 * @param size     Size of each data element
 * @param nmemb    Number of elements
 * @param userp    Pointer to target string
 * @return         Number of bytes processed
 */
static size_t write_callback_robots(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t total_size = size * nmemb;
    static_cast<std::string*>(userp)->append(static_cast<char*>(contents), total_size);
    return total_size;
}

// Simple base64 encoder
std::string base64_encode(const std::string& in) {
    static const char* base64_chars =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789+/";
    
    std::string out;
    int val = 0, valb = -6;
    for (unsigned char c : in) {
        val = (val << 8) + c;
        valb += 8;
        while (valb >= 0) {
            out.push_back(base64_chars[(val >> valb) & 0x3F]);
            valb -= 6;
        }
    }
    if (valb > -6) out.push_back(base64_chars[((val << 8) >> (valb + 8)) & 0x3F]);
    while (out.size() % 4) out.push_back('=');
    return out;
}

bool RobotsTxtCache::is_allowed(const std::string& url, const std::string& user_agent) {
    std::string domain = extract_domain(url);
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (rules_.find(domain) == rules_.end()) {
            CURL* curl = curl_easy_init();
            std::string robots_url = "http://" + domain + "/robots.txt";
            std::string response;
            curl_easy_setopt(curl, CURLOPT_URL, robots_url.c_str());
            curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback_robots);
            curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
            curl_easy_setopt(curl, CURLOPT_USERAGENT, user_agent.c_str());
            curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
            curl_easy_setopt(curl, CURLOPT_TIMEOUT, 5L);
            CURLcode res = curl_easy_perform(curl);
            if (res == CURLE_OK) {
                parse(domain, response);
            }
            curl_easy_cleanup(curl);
        }
    }
    return true; // Simplified for initial version
}

void RobotsTxtCache::parse(const std::string& domain, const std::string& content) {
    rules_[domain] = content; // Basic implementation
}

void RateLimiter::wait_for_domain(const std::string& domain) {
    const std::chrono::milliseconds delay(100);  // Reduce from 1000ms to 100ms
    std::lock_guard<std::mutex> lock(mutex_);
    auto now = std::chrono::steady_clock::now();
    
    // Only wait if we've fetched from this domain recently
    if (last_fetch_.find(domain) != last_fetch_.end()) {
        auto elapsed = now - last_fetch_[domain];
        if (elapsed < delay) {
            std::this_thread::sleep_for(delay - elapsed);
        }
    }
    last_fetch_[domain] = now;
}

std::string extract_domain(const std::string& url) {
    std::regex domain_regex(R"(^(?:https?:\/\/)?([^\/:]+))");
    std::smatch match;
    if (std::regex_search(url, match, domain_regex)) {
        return match[1];
    }
    return "";
}

std::vector<std::string> canonicalize_urls(const std::string& base_url, const std::vector<std::string>& urls) {
    std::vector<std::string> cleaned;
    for (const auto& url : urls) {
        std::string clean_url = url;
        
        // Remove fragment identifiers
        size_t pos = clean_url.find('#');
        if (pos != std::string::npos) {
            clean_url = clean_url.substr(0, pos);
        }
        
        // Normalize relative URLs
        if (clean_url.find("://") == std::string::npos) {
            // Handle relative paths properly
            if (clean_url[0] == '/') {
                // Absolute path
                std::string protocol = base_url.substr(0, base_url.find("://") + 3);
                std::string domain = extract_domain(base_url);
                clean_url = protocol + domain + clean_url;
            } else {
                // Relative path
                std::string base = base_url.substr(0, base_url.find_last_of('/') + 1);
                clean_url = base + clean_url;
            }
        }
        
        // Remove duplicate slashes
        std::string::size_type n = 0;
        while ((n = clean_url.find("//", n)) != std::string::npos) {
            if (n > 0 && clean_url[n-1] != ':' && n < clean_url.length()-2) {
                clean_url.replace(n, 2, "/");
            } else {
                n += 2;
            }
        }
        
        // Remove trailing slashes
        if (clean_url.size() > 1 && clean_url.back() == '/') {
            clean_url.pop_back();
        }
        
        cleaned.push_back(clean_url);
    }
    return cleaned;
}

// utils.cpp - updated save_as_json function
void save_as_json(const std::string& url, const std::string& html, const std::string& output_dir) {
    try {
        fs::create_directories(output_dir);
        
        // Generate safe filename (hash + truncate)
        std::string hash = std::to_string(std::hash<std::string>{}(url));
        std::string safe_filename = hash.substr(0, 16) + ".json";
        
        fs::path file_path = fs::path(output_dir) / safe_filename;
        std::ofstream outfile(file_path);
        
        if (outfile) {
            std::string encoded = base64_encode(html);
            outfile << "{ \"url\": \"" << url << "\", \"html_base64\": \"" << encoded << "\" }";
            std::cout << "Saved: " << file_path << std::endl;
        } else {
            log_error("Failed to open file: " + file_path.string());
        }
    } catch (const std::exception& e) {
        log_error("Error saving file: " + std::string(e.what()));
    }
}

void log_error(const std::string& message) {
    std::cerr << "[ERROR] " << message << std::endl;
}