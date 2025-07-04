#include "utils.h"
#include <curl/curl.h>
#include <iostream>
#include <fstream>
#include <regex>
#include <algorithm>
#include <thread>       // For std::this_thread
#include <chrono> 

// Helper: write callback for robots.txt
static size_t write_callback_robots(void* contents, size_t size, size_t nmemb, void* userp) {
    ((std::string*)userp)->append((char*)contents, size * nmemb);
    return size * nmemb;
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
    const std::chrono::milliseconds delay(1000); // 1s delay
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = last_fetch_.find(domain);
    auto now = std::chrono::steady_clock::now();
    if (it != last_fetch_.end() && (now - it->second) < delay) {
        std::this_thread::sleep_for(delay - (now - it->second));
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
        if (url.find("://") == std::string::npos) {
            // Relative URL resolution
            std::string abs_url = base_url.substr(0, base_url.find_last_of('/') + 1) + url;
            cleaned.push_back(abs_url);
        } else if (url.find("http://") == 0 || url.find("https://") == 0) {
            // Remove fragments
            size_t pos = url.find('#');
            cleaned.push_back(pos == std::string::npos ? url : url.substr(0, pos));
        }
    }
    return cleaned;
}

void save_as_json(const std::string& url, const std::string& html, const std::string& output_dir) {
    // Create filename-safe version of URL
    std::string safe_filename = std::to_string(std::hash<std::string>{}(url)) + ".json";
    std::ofstream outfile(output_dir + "/" + safe_filename);
    if (outfile.is_open()) {
        outfile << "{ \"url\": \"" << url << "\", \"html\": \"";
        // Basic JSON escaping
        for (char c : html) {
            if (c == '\"') outfile << "\\\"";
            else if (c == '\\') outfile << "\\\\";
            else if (c == '\n') outfile << "\\n";
            else outfile << c;
        }
        outfile << "\" }";
    }
}

void log_error(const std::string& message) {
    std::cerr << "[ERROR] " << message << std::endl;
}