#pragma once

#include "connection_pool.h"
#include <curl/curl.h>
#include <string>
#include <unordered_map>
#include <chrono>
#include <functional>

/**
 * Unified HTTP Client for all crawler components
 * Uses ConnectionPool for efficient connection reuse
 * Provides consistent error handling and response processing
 */
class HttpClient {
public:
    struct HttpHeaders {
        std::string last_modified;
        std::string etag;
        std::string content_type;
        std::string cache_control;
        int status_code = 0;
        
        bool has_cache_info() const {
            return !last_modified.empty() || !etag.empty();
        }
    };

    struct HttpResponse {
        std::string body;
        HttpHeaders headers;
        CURLcode curl_code = CURLE_OK;
        bool success = false;
        bool not_modified = false; // For conditional GET (304 responses)
        
        HttpResponse() = default;
        HttpResponse(const std::string& content, int status = 200) 
            : body(content), success(true) {
            headers.status_code = status;
        }
    };

    struct RequestOptions {
        int timeout_seconds = 15;
        int connect_timeout_seconds = 5;
        bool follow_redirects = true;
        int max_redirects = 3;
        std::string user_agent = "MyCrawler/2.0 (+https://example.com/bot)";
        std::unordered_map<std::string, std::string> extra_headers;
        
        // For conditional GET
        std::string if_modified_since;
        std::string if_none_match;
        
        RequestOptions() = default;
    };

private:
    ConnectionPool& connection_pool_;
    
    // Callback functions for CURL
    static size_t write_callback(void* contents, size_t size, size_t nmemb, void* userp);
    static size_t header_callback(void* contents, size_t size, size_t nmemb, void* userp);
    
    // Helper methods
    void configure_request(CURL* curl, const std::string& url, const RequestOptions& options,
                          std::string* response_body, HttpHeaders* headers);
    void parse_header_line(const std::string& header, HttpHeaders& headers);
    static void parse_header_line_static(const std::string& header, HttpHeaders& headers);

public:
    explicit HttpClient(ConnectionPool& pool);
    ~HttpClient() = default;

    // Main HTTP GET method
    HttpResponse get(const std::string& url);
    HttpResponse get(const std::string& url, const RequestOptions& options);
    
    // Conditional GET for cache-aware requests
    HttpResponse conditional_get(const std::string& url, const HttpHeaders& cached_headers);
    HttpResponse conditional_get(const std::string& url, const HttpHeaders& cached_headers,
                                const RequestOptions& options);
    
    // Specialized methods for different content types
    HttpResponse download_feed(const std::string& feed_url);
    HttpResponse download_feed(const std::string& feed_url, const RequestOptions& options);
    HttpResponse download_sitemap(const std::string& sitemap_url);
    HttpResponse download_sitemap(const std::string& sitemap_url, const RequestOptions& options);
    HttpResponse download_robots_txt(const std::string& domain);
    HttpResponse download_robots_txt(const std::string& domain, const RequestOptions& options);
    
    // Utility methods
    static std::string format_http_date(const std::chrono::system_clock::time_point& time);
    static std::chrono::system_clock::time_point parse_http_date(const std::string& date_str);
    
    // Error handling
    static std::string curl_error_string(CURLcode code);
};
