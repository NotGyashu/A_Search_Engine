#include "url_normalizer.h"
#include <algorithm>
#include <sstream>

// Static member initializations
std::regex UrlNormalizer::protocol_regex_(R"(^(https?):\/\/)", std::regex::icase);
std::regex UrlNormalizer::domain_regex_(R"(^(?:https?:\/\/)?([^\/\?\#:]+))");
std::regex UrlNormalizer::path_cleanup_regex_(R"(\/+)");
std::unordered_set<std::string> UrlNormalizer::tracking_params_ = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "ref", "source", "campaign_id", "ad_id"
};

std::string UrlNormalizer::normalize(const std::string& url) {
    if (url.empty()) return "";
    
    std::string result = url;
    
    // Convert to lowercase for scheme and host
    std::smatch protocol_match;
    if (std::regex_search(result, protocol_match, protocol_regex_)) {
        std::string scheme = protocol_match[1].str();
        std::transform(scheme.begin(), scheme.end(), scheme.begin(), ::tolower);
        result = scheme + result.substr(protocol_match[0].length() - 3);
    }
    
    // Extract and normalize domain
    std::smatch domain_match;
    if (std::regex_search(result, domain_match, domain_regex_)) {
        std::string domain = domain_match[1].str();
        std::transform(domain.begin(), domain.end(), domain.begin(), ::tolower);
        
        // Remove www. prefix
        if (domain.substr(0, 4) == "www.") {
            domain = domain.substr(4);
        }
        
        size_t domain_start = result.find(domain_match[1].str());
        result.replace(domain_start, domain_match[1].length(), domain);
    }
    
    // Remove fragment
    size_t fragment_pos = result.find('#');
    if (fragment_pos != std::string::npos) {
        result = result.substr(0, fragment_pos);
    }
    
    // Remove tracking parameters
    size_t query_pos = result.find('?');
    if (query_pos != std::string::npos) {
        std::string base = result.substr(0, query_pos);
        std::string query = result.substr(query_pos + 1);
        std::string cleaned_query;
        
        std::istringstream query_stream(query);
        std::string param;
        bool first = true;
        
        while (std::getline(query_stream, param, '&')) {
            size_t eq_pos = param.find('=');
            if (eq_pos != std::string::npos) {
                std::string key = param.substr(0, eq_pos);
                if (tracking_params_.find(key) == tracking_params_.end()) {
                    if (!first) cleaned_query += "&";
                    cleaned_query += param;
                    first = false;
                }
            }
        }
        
        result = base + (cleaned_query.empty() ? "" : "?" + cleaned_query);
    }
    
    // Clean up path - remove multiple slashes
    size_t path_start = result.find('/', result.find("://") + 3);
    if (path_start != std::string::npos) {
        std::string path_part = result.substr(path_start);
        path_part = std::regex_replace(path_part, path_cleanup_regex_, "/");
        result = result.substr(0, path_start) + path_part;
    }
    
    // Remove trailing slash (except for root)
    if (result.length() > 1 && result.back() == '/') {
        result.pop_back();
    }
    
    return result;
}

std::string UrlNormalizer::resolve_relative(const std::string& base_url, const std::string& relative_url) {
    if (relative_url.empty()) return "";
    if (relative_url.find("://") != std::string::npos) return relative_url; // Already absolute
    
    if (relative_url[0] == '/') {
        // Absolute path
        size_t protocol_end = base_url.find("://");
        if (protocol_end == std::string::npos) return "";
        
        size_t domain_end = base_url.find('/', protocol_end + 3);
        std::string base_domain = (domain_end == std::string::npos) 
            ? base_url : base_url.substr(0, domain_end);
        
        return base_domain + relative_url;
    } else {
        // Relative path
        std::string base = base_url;
        if (base.back() != '/') {
            size_t last_slash = base.find_last_of('/');
            if (last_slash != std::string::npos && last_slash > base.find("://") + 2) {
                base = base.substr(0, last_slash + 1);
            } else {
                base += "/";
            }
        }
        return base + relative_url;
    }
}

std::string UrlNormalizer::extract_domain(const std::string& url) {
    std::smatch match;
    if (std::regex_search(url, match, domain_regex_) && match.size() > 1) {
        std::string domain = match[1].str();
        std::transform(domain.begin(), domain.end(), domain.begin(), ::tolower);
        return domain;
    }
    return "";
}

std::string UrlNormalizer::extract_path(const std::string& url) {
    size_t protocol_end = url.find("://");
    if (protocol_end == std::string::npos) return "/";
    
    size_t domain_end = url.find('/', protocol_end + 3);
    return (domain_end == std::string::npos) ? "/" : url.substr(domain_end);
}

bool UrlNormalizer::is_valid_url(const std::string& url) {
    if (url.length() < 10 || url.length() > 2048) return false;
    return url.find("http://") == 0 || url.find("https://") == 0;
}
