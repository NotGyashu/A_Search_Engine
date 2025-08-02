#include "url_normalizer.h"
#include <algorithm>
#include <sstream>

std::unordered_set<std::string> UrlNormalizer::tracking_params_ = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "ref", "source", "campaign_id", "ad_id"
};

// === REGEX-FREE IMPLEMENTATION ===

std::string UrlNormalizer::normalize_domain_case(std::string_view domain) {
    std::string result;
    result.reserve(domain.size());
    for (char c : domain) {
        result += std::tolower(c);
    }
    return result;
}

std::string UrlNormalizer::clean_path_slashes(std::string_view path) {
    std::string result;
    result.reserve(path.size());
    bool prev_slash = false;
    
    for (char c : path) {
        if (c == '/') {
            if (!prev_slash) result += c;
            prev_slash = true;
        } else {
            result += c;
            prev_slash = false;
        }
    }
    return result;
}

std::string UrlNormalizer::remove_tracking_params(std::string_view query) {
    std::string result;
    std::string param;
    bool first = true;
    
    size_t start = 0;
    while (start < query.size()) {
        size_t end = query.find('&', start);
        if (end == std::string_view::npos) end = query.size();
        
        std::string_view param_view = query.substr(start, end - start);
        size_t eq_pos = param_view.find('=');
        
        if (eq_pos != std::string_view::npos) {
            std::string key(param_view.substr(0, eq_pos));
            if (tracking_params_.find(key) == tracking_params_.end()) {
                if (!first) result += "&";
                result += param_view;
                first = false;
            }
        }
        
        start = (end == query.size()) ? end : end + 1;
    }
    
    return result;
}

std::string UrlNormalizer::normalize(const std::string& url) {
    if (url.empty() || url.length() > 2048) return "";

    std::string result = url;

    // Extract protocol (http:// or https://)
    size_t protocol_end = result.find("://");
    if (protocol_end == std::string::npos) {
        // If no protocol, assume http
        result = "http://" + result;
        protocol_end = 6; // length of "http://"
    } else {
        // Normalize protocol to lowercase
        std::string protocol = result.substr(0, protocol_end);
        std::transform(protocol.begin(), protocol.end(), protocol.begin(), ::tolower);
        result = protocol + result.substr(protocol_end);
        protocol_end += 3; // Skip "://"
    }

    // Find domain boundaries
    size_t domain_start = protocol_end;
    size_t domain_end = result.find_first_of("/?#", domain_start);
    if (domain_end == std::string::npos) domain_end = result.length();

    // Extract and normalize domain
    std::string domain = result.substr(domain_start, domain_end - domain_start);
    domain = normalize_domain_case(domain);
    result = result.substr(0, domain_start) + domain + result.substr(domain_end);

    // Remove fragment (#...)
    size_t fragment_pos = result.find('#');
    if (fragment_pos != std::string::npos) {
        result = result.substr(0, fragment_pos);
    }

    // Clean query parameters
    size_t query_pos = result.find('?');
    if (query_pos != std::string::npos) {
        std::string base = result.substr(0, query_pos);
        std::string query = result.substr(query_pos + 1);
        std::string cleaned_query = remove_tracking_params(query);
        result = base + (cleaned_query.empty() ? "" : "?" + cleaned_query);
    }

    // Clean up path - remove multiple slashes
    size_t path_start = result.find('/', domain_start + domain.length());
    if (path_start != std::string::npos) {
        size_t path_end = result.find_first_of("?#", path_start);
        if (path_end == std::string::npos) path_end = result.length();
        
        std::string path_part = result.substr(path_start, path_end - path_start);
        path_part = clean_path_slashes(path_part);
        result = result.substr(0, path_start) + path_part + result.substr(path_end);
    }

    // Remove trailing slash unless it's the root
    if (result.length() > 1 && result.back() == '/') {
        size_t slash_pos = result.find('/', protocol_end);
        if (slash_pos != result.length() - 1) { // Not just domain/
            result.pop_back();
        }
    }

    return result;
}

std::string UrlNormalizer::resolve_relative(const std::string& base_url, const std::string& relative_url) {
    if (relative_url.empty()) return "";
    
    // If it's already absolute, return as-is
    if (relative_url.find("://") != std::string::npos) {
        return normalize(relative_url);
    }
    
    // If starts with //, it's protocol-relative
    if (relative_url.length() >= 2 && relative_url.substr(0, 2) == "//") {
        size_t protocol_end = base_url.find("://");
        if (protocol_end != std::string::npos) {
            return normalize(base_url.substr(0, protocol_end + 1) + relative_url);
        }
        return normalize("http:" + relative_url);
    }
    
    // If starts with /, it's absolute path
    if (!relative_url.empty() && relative_url[0] == '/') {
        size_t protocol_end = base_url.find("://");
        if (protocol_end != std::string::npos) {
            size_t domain_end = base_url.find('/', protocol_end + 3);
            if (domain_end == std::string::npos) domain_end = base_url.length();
            return normalize(base_url.substr(0, domain_end) + relative_url);
        }
        return normalize(base_url + relative_url);
    }
    
    // It's a relative path - append to base directory
    std::string base = base_url;
    size_t last_slash = base.find_last_of('/');
    if (last_slash != std::string::npos) {
        base = base.substr(0, last_slash + 1);
    } else {
        base += "/";
    }
    
    return normalize(base + relative_url);
}

std::string UrlNormalizer::extract_domain(const std::string& url) {
    size_t start = url.find("://");
    if (start == std::string::npos) return "";
    start += 3;
    
    size_t end = url.find_first_of("/?#", start);
    if (end == std::string::npos) end = url.length();
    
    std::string domain = url.substr(start, end - start);
    return normalize_domain_case(domain);
}

std::string UrlNormalizer::extract_path(const std::string& url) {
    size_t protocol_pos = url.find("://");
    if (protocol_pos == std::string::npos) return "/";
    
    size_t path_start = url.find('/', protocol_pos + 3);
    if (path_start == std::string::npos) return "/";
    
    size_t query_pos = url.find('?', path_start);
    size_t fragment_pos = url.find('#', path_start);
    
    size_t end = std::min(query_pos, fragment_pos);
    if (end == std::string::npos) end = url.length();
    
    return url.substr(path_start, end - path_start);
}

bool UrlNormalizer::is_valid_url(const std::string& url) {
    if (url.empty() || url.length() > 2048) return false;
    
    // Must have protocol
    size_t protocol_pos = url.find("://");
    if (protocol_pos == std::string::npos) return false;
    
    // Must have domain after protocol
    if (protocol_pos + 3 >= url.length()) return false;
    
    // Domain must contain at least one character
    size_t domain_start = protocol_pos + 3;
    size_t domain_end = url.find_first_of("/?#", domain_start);
    if (domain_end == std::string::npos) domain_end = url.length();
    
    return (domain_end > domain_start);
}
