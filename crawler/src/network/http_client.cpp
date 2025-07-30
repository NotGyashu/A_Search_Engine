#include "http_client.h"
#include <sstream>
#include <algorithm>
#include <iomanip>
#include <ctime>

HttpClient::HttpClient(ConnectionPool& pool) : connection_pool_(pool) {}

size_t HttpClient::write_callback(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t total_size = size * nmemb;
    std::string* response_data = static_cast<std::string*>(userp);
    response_data->append(static_cast<char*>(contents), total_size);
    return total_size;
}

size_t HttpClient::header_callback(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t total_size = size * nmemb;
    std::string header(static_cast<char*>(contents), total_size);
    HttpHeaders* headers = static_cast<HttpHeaders*>(userp);
    
    // Remove trailing CRLF
    if (header.size() >= 2 && header.substr(header.size() - 2) == "\r\n") {
        header.erase(header.size() - 2);
    }
    
    HttpClient::parse_header_line_static(header, *headers);
    return total_size;
}

void HttpClient::parse_header_line(const std::string& header, HttpHeaders& headers) {
    if (header.empty()) return;
    
    // Handle status line
    if (header.substr(0, 4) == "HTTP") {
        size_t space_pos = header.find(' ');
        if (space_pos != std::string::npos) {
            size_t code_end = header.find(' ', space_pos + 1);
            if (code_end != std::string::npos) {
                try {
                    headers.status_code = std::stoi(header.substr(space_pos + 1, code_end - space_pos - 1));
                } catch (...) {
                    headers.status_code = 0;
                }
            }
        }
        return;
    }
    
    // Parse header fields
    size_t colon_pos = header.find(':');
    if (colon_pos == std::string::npos) return;
    
    std::string name = header.substr(0, colon_pos);
    std::string value = header.substr(colon_pos + 1);
    
    // Trim whitespace
    name.erase(0, name.find_first_not_of(" \t"));
    name.erase(name.find_last_not_of(" \t") + 1);
    value.erase(0, value.find_first_not_of(" \t"));
    value.erase(value.find_last_not_of(" \t") + 1);
    
    // Convert header name to lowercase for comparison
    std::transform(name.begin(), name.end(), name.begin(), ::tolower);
    
    if (name == "last-modified") {
        headers.last_modified = value;
    } else if (name == "etag") {
        headers.etag = value;
    } else if (name == "content-type") {
        headers.content_type = value;
    } else if (name == "cache-control") {
        headers.cache_control = value;
    }
}

void HttpClient::parse_header_line_static(const std::string& header, HttpHeaders& headers) {
    // Create a temporary instance to call the non-static method
    // This is a workaround since the actual logic doesn't need instance data
    if (header.empty()) return;
    
    // Handle status line
    if (header.substr(0, 4) == "HTTP") {
        size_t space_pos = header.find(' ');
        if (space_pos != std::string::npos) {
            size_t code_end = header.find(' ', space_pos + 1);
            if (code_end != std::string::npos) {
                try {
                    headers.status_code = std::stoi(header.substr(space_pos + 1, code_end - space_pos - 1));
                } catch (...) {
                    headers.status_code = 0;
                }
            }
        }
        return;
    }
    
    // Parse header fields
    size_t colon_pos = header.find(':');
    if (colon_pos == std::string::npos) return;
    
    std::string name = header.substr(0, colon_pos);
    std::string value = header.substr(colon_pos + 1);
    
    // Trim whitespace
    name.erase(0, name.find_first_not_of(" \t"));
    name.erase(name.find_last_not_of(" \t") + 1);
    value.erase(0, value.find_first_not_of(" \t"));
    value.erase(value.find_last_not_of(" \t") + 1);
    
    // Convert header name to lowercase for comparison
    std::transform(name.begin(), name.end(), name.begin(), ::tolower);
    
    if (name == "last-modified") {
        headers.last_modified = value;
    } else if (name == "etag") {
        headers.etag = value;
    } else if (name == "content-type") {
        headers.content_type = value;
    } else if (name == "cache-control") {
        headers.cache_control = value;
    }
}

void HttpClient::configure_request(CURL* curl, const std::string& url, const RequestOptions& options,
                                  std::string* response_body, HttpHeaders* headers) {
    // Reset the connection for reuse
    curl_easy_reset(curl);
    
    // Basic options
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, response_body);
    curl_easy_setopt(curl, CURLOPT_HEADERFUNCTION, header_callback);
    curl_easy_setopt(curl, CURLOPT_HEADERDATA, headers);
    
    // Timeout settings
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, static_cast<long>(options.timeout_seconds));
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, static_cast<long>(options.connect_timeout_seconds));
    
    // User agent
    curl_easy_setopt(curl, CURLOPT_USERAGENT, options.user_agent.c_str());
    
    // Redirect settings
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, options.follow_redirects ? 1L : 0L);
    curl_easy_setopt(curl, CURLOPT_MAXREDIRS, static_cast<long>(options.max_redirects));
    
    // Performance and connection settings
    curl_easy_setopt(curl, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_2_0);
    curl_easy_setopt(curl, CURLOPT_PIPEWAIT, 1L);
    curl_easy_setopt(curl, CURLOPT_TCP_NODELAY, 1L);
    curl_easy_setopt(curl, CURLOPT_TCP_KEEPALIVE, 1L);
    curl_easy_setopt(curl, CURLOPT_ACCEPT_ENCODING, "gzip,deflate");
    curl_easy_setopt(curl, CURLOPT_BUFFERSIZE, 131072L);
    curl_easy_setopt(curl, CURLOPT_LOW_SPEED_LIMIT, 1024L);
    curl_easy_setopt(curl, CURLOPT_LOW_SPEED_TIME, 10L);
    curl_easy_setopt(curl, CURLOPT_DNS_CACHE_TIMEOUT, 300L);
    
    // SSL settings
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0L);
    curl_easy_setopt(curl, CURLOPT_SSL_SESSIONID_CACHE, 1L);
    
    // Connection reuse
    curl_easy_setopt(curl, CURLOPT_FORBID_REUSE, 0L);
    curl_easy_setopt(curl, CURLOPT_FRESH_CONNECT, 0L);
    curl_easy_setopt(curl, CURLOPT_TCP_FASTOPEN, 1L);
    
    // Signals
    curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
    
    // Custom headers
    struct curl_slist* headers_list = nullptr;
    
    // Add conditional GET headers if specified
    if (!options.if_modified_since.empty()) {
        std::string header = "If-Modified-Since: " + options.if_modified_since;
        headers_list = curl_slist_append(headers_list, header.c_str());
    }
    
    if (!options.if_none_match.empty()) {
        std::string header = "If-None-Match: " + options.if_none_match;
        headers_list = curl_slist_append(headers_list, header.c_str());
    }
    
    // Add extra headers
    for (const auto& [name, value] : options.extra_headers) {
        std::string header = name + ": " + value;
        headers_list = curl_slist_append(headers_list, header.c_str());
    }
    
    if (headers_list) {
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers_list);
    }
}

HttpClient::HttpResponse HttpClient::get(const std::string& url) {
    RequestOptions default_options;
    return get(url, default_options);
}

HttpClient::HttpResponse HttpClient::get(const std::string& url, const RequestOptions& options) {
    HttpResponse response;
    CURL* curl = nullptr;
    
    try {
        // Extract domain for connection pooling
        std::string domain;
        size_t start = url.find("://");
        if (start != std::string::npos) {
            start += 3;
            size_t end = url.find('/', start);
            domain = url.substr(start, end == std::string::npos ? url.length() : end);
        }
        
        curl = connection_pool_.acquire_connection();
        if (!curl) {
            response.curl_code = CURLE_FAILED_INIT;
            response.success = false;
            return response;
        }
        
        configure_request(curl, url, options, &response.body, &response.headers);
        
        response.curl_code = curl_easy_perform(curl);
        // It must be returned AFTER all info is gathered from the handle.
        if (response.curl_code == CURLE_OK) {
            response.success = true;
            long http_code = 0;
            curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
            response.headers.status_code = static_cast<int>(http_code);

            response.not_modified = (response.headers.status_code == 304);
            response.success = (response.headers.status_code >= 200 && response.headers.status_code < 400);
        } else {
             response.success = false;
        }
        
    } catch (const std::exception& e) {
        response.curl_code = CURLE_FAILED_INIT;
        response.success = false;
    }
    
    if (curl) {
        connection_pool_.release_connection(curl);
    }
    
    return response;
}

HttpClient::HttpResponse HttpClient::conditional_get(const std::string& url, const HttpHeaders& cached_headers) {
    RequestOptions default_options;
    return conditional_get(url, cached_headers, default_options);
}

HttpClient::HttpResponse HttpClient::conditional_get(const std::string& url, const HttpHeaders& cached_headers,
                                         const RequestOptions& base_options) {
    RequestOptions options = base_options;
    
    // Add conditional headers
    if (!cached_headers.last_modified.empty()) {
        options.if_modified_since = cached_headers.last_modified;
    }
    
    if (!cached_headers.etag.empty()) {
        options.if_none_match = cached_headers.etag;
    }
    
    return get(url, options);
}

HttpClient::HttpResponse HttpClient::download_feed(const std::string& feed_url) {
    RequestOptions default_options;
    return download_feed(feed_url, default_options);
}

HttpClient::HttpResponse HttpClient::download_feed(const std::string& feed_url, const RequestOptions& options) {
    RequestOptions feed_options = options;
    feed_options.extra_headers["Accept"] = "application/rss+xml, application/atom+xml, application/xml, text/xml";
    return get(feed_url, feed_options);
}

HttpClient::HttpResponse HttpClient::download_sitemap(const std::string& sitemap_url) {
    RequestOptions default_options;
    return download_sitemap(sitemap_url, default_options);
}

HttpClient::HttpResponse HttpClient::download_sitemap(const std::string& sitemap_url, const RequestOptions& options) {
    RequestOptions sitemap_options = options;
    sitemap_options.extra_headers["Accept"] = "application/xml, text/xml, application/gzip";
    return get(sitemap_url, sitemap_options);
}

HttpClient::HttpResponse HttpClient::download_robots_txt(const std::string& domain) {
    RequestOptions default_options;
    return download_robots_txt(domain, default_options);
}

HttpClient::HttpResponse HttpClient::download_robots_txt(const std::string& domain, const RequestOptions& options) {
    std::string robots_url = domain;
    if (robots_url.find("://") == std::string::npos) {
        robots_url = "https://" + robots_url;
    }
    if (robots_url.back() != '/') {
        robots_url += "/";
    }
    robots_url += "robots.txt";
    
    RequestOptions robots_options = options;
    robots_options.extra_headers["Accept"] = "text/plain";
    robots_options.timeout_seconds = 10; // Shorter timeout for robots.txt
    
    return get(robots_url, robots_options);
}

std::string HttpClient::format_http_date(const std::chrono::system_clock::time_point& time) {
    auto time_t = std::chrono::system_clock::to_time_t(time);
    std::stringstream ss;
    ss << std::put_time(std::gmtime(&time_t), "%a, %d %b %Y %H:%M:%S GMT");
    return ss.str();
}

std::chrono::system_clock::time_point HttpClient::parse_http_date(const std::string& date_str) {
    std::tm tm = {};
    std::istringstream ss(date_str);
    
    // Try RFC 2822 format first (used by HTTP)
    ss >> std::get_time(&tm, "%a, %d %b %Y %H:%M:%S");
    if (!ss.fail()) {
        return std::chrono::system_clock::from_time_t(timegm(&tm));
    }
    
    // Try alternative format
    ss.clear();
    ss.str(date_str);
    ss >> std::get_time(&tm, "%d %b %Y %H:%M:%S");
    if (!ss.fail()) {
        return std::chrono::system_clock::from_time_t(timegm(&tm));
    }
    
    // Fallback to current time
    return std::chrono::system_clock::now();
}

std::string HttpClient::curl_error_string(CURLcode code) {
    switch (code) {
        case CURLE_OK: return "Success";
        case CURLE_UNSUPPORTED_PROTOCOL: return "Unsupported protocol";
        case CURLE_FAILED_INIT: return "Failed to initialize";
        case CURLE_URL_MALFORMAT: return "Malformed URL";
        case CURLE_COULDNT_RESOLVE_PROXY: return "Couldn't resolve proxy";
        case CURLE_COULDNT_RESOLVE_HOST: return "Couldn't resolve host";
        case CURLE_COULDNT_CONNECT: return "Couldn't connect";
        case CURLE_OPERATION_TIMEDOUT: return "Operation timed out";
        case CURLE_SSL_CONNECT_ERROR: return "SSL connection error";
        case CURLE_TOO_MANY_REDIRECTS: return "Too many redirects";
        default: return curl_easy_strerror(code);
    }
}
