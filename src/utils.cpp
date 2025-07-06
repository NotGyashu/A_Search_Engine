#include "utils.h"
#include <curl/curl.h>
#include <iostream>
#include <fstream>
#include <regex>
#include <algorithm>
#include <thread>
#include <chrono>
#include <filesystem>
#include <queue>
#include <sstream>
#include <iomanip>

namespace fs = std::filesystem;

static size_t write_callback_robots(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t total_size = size * nmemb;
    static_cast<std::string*>(userp)->append(static_cast<char*>(contents), total_size);
    return total_size;
}

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

bool RobotsTxtCache::is_allowed(const std::string& domain) {
    // Simplified robots.txt check - allow all by default
    return true;
}

void RateLimiter::wait_for_domain(const std::string& domain) {
    const std::chrono::milliseconds delay(25); // Faster for production search engine
    std::lock_guard<std::mutex> lock(mutex_);
    auto now = std::chrono::steady_clock::now();
    
    if (last_fetch_.find(domain) != last_fetch_.end()) {
        auto elapsed = now - last_fetch_[domain];
        if (elapsed < delay) {
            std::this_thread::sleep_for(delay - elapsed);
        }
    }
    last_fetch_[domain] = now;
}

std::string extract_domain(const std::string& url) {
    static std::regex domain_regex(R"(^(?:https?:\/\/)?([^\/:]+))");
    std::smatch match;
    if (std::regex_search(url, match, domain_regex) && match.size() > 1) {
        return match[1];
    }
    return "";
}

bool is_useful_url(const std::string& url) {
    // Skip common static file extensions
    static const std::vector<std::string> bad_extensions = {
        ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
        ".mp3", ".mp4", ".avi", ".mov", ".pdf", ".zip", ".gz", ".tar", ".exe", ".dmg", ".bin"
    };
    for (const auto& ext : bad_extensions) {
        if (url.find(ext) != std::string::npos) {
            return false;
        }
    }

    // Skip logout/signout links
    static const std::vector<std::string> bad_keywords = {
        "logout", "signout"
    };
    for (const auto& kw : bad_keywords) {
        if (url.find(kw) != std::string::npos) {
            return false;
        }
    }

    // Skip URLs that are too long
    if (url.length() > 200) {
        return false;
    }

    return true;
}

std::vector<std::string> canonicalize_urls(const std::string& base_url, const std::vector<std::string>& urls) {
    std::vector<std::string> cleaned;
    cleaned.reserve(urls.size());
    
    // Precompute base components
    size_t protocol_end = base_url.find("://");
    if (protocol_end == std::string::npos) {
        return cleaned;
    }
    
    std::string base_protocol = base_url.substr(0, protocol_end + 3);
    size_t domain_end = base_url.find('/', protocol_end + 3);
    std::string base_domain = (domain_end == std::string::npos) 
        ? base_url.substr(protocol_end + 3)
        : base_url.substr(protocol_end + 3, domain_end - protocol_end - 3);
    
    for (const auto& url : urls) {
        if (url.empty()) continue;
        
        std::string clean_url;
        
        // Skip javascript and mailto links
        if (url.find("javascript:") == 0 || url.find("mailto:") == 0) {
            continue;
        }
        
        // Remove fragment
        size_t frag_pos = url.find('#');
        if (frag_pos != std::string::npos) {
            clean_url = url.substr(0, frag_pos);
        } else {
            clean_url = url;
        }
        
        // Handle relative URLs
        if (clean_url.find("://") == std::string::npos) {
            if (clean_url[0] == '/') {
                // Absolute path
                clean_url = base_protocol + base_domain + clean_url;
            } else {
                // Relative path - use base URL directly
                clean_url = base_url + (base_url.back() == '/' ? "" : "/") + clean_url;
            }
        }
        
        // Basic normalization
        if (!clean_url.empty()) {
            // Remove duplicate slashes (except after http:)
            size_t pos = clean_url.find("://");
            if (pos != std::string::npos) {
                std::string protocol = clean_url.substr(0, pos + 3);
                std::string path = clean_url.substr(pos + 3);
                
                size_t dpos = 0;
                while ((dpos = path.find("//", dpos)) != std::string::npos) {
                    path.replace(dpos, 2, "/");
                    dpos += 1;
                }
                clean_url = protocol + path;
            }
            
            // Remove trailing slash
            if (clean_url.size() > 1 && clean_url.back() == '/') {
                clean_url.pop_back();
            }
            
            cleaned.push_back(clean_url);
        }
    }
    return cleaned;
}

void save_batch_as_json(std::vector<std::pair<std::string, std::string>>& batch, 
                        const std::string& output_dir) {
    try {
        fs::create_directories(output_dir);
        
        // Create timestamped batch file
        auto now = std::chrono::system_clock::now();
        auto in_time_t = std::chrono::system_clock::to_time_t(now);
        std::stringstream ss;
        ss << std::put_time(std::localtime(&in_time_t), "%Y%m%d_%H%M%S");
        std::string batch_name = "batch_" + ss.str() + ".json";
        fs::path file_path = fs::path(output_dir) / batch_name;
        
        std::ofstream outfile(file_path);
        if (outfile) {
            outfile << "[\n";
            bool first = true;
            
            for (auto& [url, html] : batch) {
                if (!first) outfile << ",\n";
                first = false;
                
                std::string encoded = base64_encode(html);
                outfile << "  { \"url\": \"" << url << "\", \"html_base64\": \"" << encoded << "\" }";
            }
            
            outfile << "\n]";
        }
    } catch (const std::exception& e) {
        log_error("Error saving batch: " + std::string(e.what()));
    }
}

void log_error(const std::string& message) {
    std::cerr << "[ERROR] " << message << std::endl;
}