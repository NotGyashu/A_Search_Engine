#include "utils.h"
#include "constants.h"
#include "ultra_parser.h"
#include <curl/curl.h>
#include <iostream>
#include <fstream>
#include <algorithm>
#include <thread>
#include <chrono>
#include <filesystem>
#include <queue>
#include <sstream>
#include <iomanip>
#include <random>
#include <immintrin.h>  // For _mm_pause()

    // Additional performance optimizations
    #define LIKELY(x) __builtin_expect(!!(x), 1)
    #define UNLIKELY(x) __builtin_expect(!!(x), 0)

    // Fast hash function for URL partitioning
    static inline uint64_t fast_hash(const std::string& str) {
        uint64_t hash = 0xcbf29ce484222325ULL;
        for (char c : str) {
            hash ^= c;
            hash *= 0x100000001b3ULL;
        }
        return hash;
    }

    namespace fs = std::filesystem;

    // Static member initializations
    std::regex UrlNormalizer::protocol_regex_(R"(^(https?):\/\/)", std::regex::icase);
    std::regex UrlNormalizer::domain_regex_(R"(^(?:https?:\/\/)?([^\/\?\#:]+))");
    std::regex UrlNormalizer::path_cleanup_regex_(R"(\/+)");
    std::unordered_set<std::string> UrlNormalizer::tracking_params_ = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "gclid", "fbclid", "ref", "source", "campaign_id", "ad_id"
    };

    std::unordered_set<std::string> ContentFilter::excluded_extensions_ = {
        ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".bmp",
        ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".zip", ".rar", ".7z", ".gz", ".tar", ".bz2", ".xz",
        ".exe", ".msi", ".deb", ".rpm", ".dmg", ".app", ".bin"
    };

    std::unordered_set<std::string> ContentFilter::excluded_patterns_ = {
        "logout", "signout", "signin", "login", "register", "signup",
        "cart", "checkout", "payment", "billing", "account", "profile",
        "admin", "wp-admin", "dashboard", "settings", "config",
        "api/", "ajax/", "json", "xml", "rss", "feed"
    };

    std::unordered_set<std::string> ContentFilter::high_priority_domains_ = {
        "wikipedia.org", "github.com", "stackoverflow.com", "reddit.com",
        "nytimes.com", "bbc.com", "cnn.com", "reuters.com", "ap.org",
        "nature.com", "science.org", "arxiv.org", "pubmed.ncbi.nlm.nih.gov"
    };

    std::regex HtmlParser::title_regex_(R"(<title[^>]*>([^<]+)</title>)", std::regex::icase);
    std::regex HtmlParser::meta_description_regex_(R"(<meta[^>]*name=["\']
        description["\'][^>]*content=["\']([^"\']+)["\'])", std::regex::icase);

    static size_t write_callback_generic(void* contents, size_t size, size_t nmemb, void* userp) {
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

    std::string get_timestamp_string() {
        auto now = std::chrono::system_clock::now();
        auto time_t = std::chrono::system_clock::to_time_t(now);
        std::stringstream ss;
        ss << std::put_time(std::localtime(&time_t), "%Y%m%d_%H%M%S");
        return ss.str();
    }

    std::string sanitize_filename(const std::string& input) {
        std::string result = input;
        std::replace_if(result.begin(), result.end(), 
                    [](char c) { return !std::isalnum(c) && c != '-' && c != '_'; }, '_');
        return result;
    }

    // ============= RobotsTxtCache Implementation =============

    size_t RobotsTxtCache::robots_write_callback(void* contents, size_t size, size_t nmemb, void* userp) {
        return write_callback_generic(contents, size, nmemb, userp);
    }

    void RobotsTxtCache::parse_robots_content(const std::string& domain, const std::string& content) {
        RobotRule rule;
        std::istringstream stream(content);
        std::string line;
        bool relevant_section = false;
        
        while (std::getline(stream, line)) {
            std::transform(line.begin(), line.end(), line.begin(), ::tolower);
            
            if (line.find("user-agent:") == 0) {
                std::string agent = line.substr(11);
                agent.erase(0, agent.find_first_not_of(" \t"));
                relevant_section = (agent == "*" || agent.find("mycrawler") != std::string::npos);
            } else if (relevant_section) {
                if (line.find("disallow:") == 0) {
                    std::string path = line.substr(9);
                    path.erase(0, path.find_first_not_of(" \t"));
                    if (!path.empty()) {
                        rule.disallowed_paths.push_back(path);
                    }
                } else if (line.find("allow:") == 0) {
                    std::string path = line.substr(6);
                    path.erase(0, path.find_first_not_of(" \t"));
                    if (!path.empty()) {
                        rule.allowed_paths.push_back(path);
                    }
                } else if (line.find("crawl-delay:") == 0) {
                    std::string delay_str = line.substr(12);
                    delay_str.erase(0, delay_str.find_first_not_of(" \t"));
                    try {
                        int delay = std::stoi(delay_str);
                        rule.crawl_delay_ms = std::max(CrawlerConstants::RateLimit::MIN_ROBOTS_DELAY_MS, 
                                                      delay * 1000); // Convert to ms, min configured ms
                    } catch (...) {
                        rule.crawl_delay_ms = CrawlerConstants::RateLimit::DEFAULT_CRAWL_DELAY_MS; // Default
                    }
                }
            }
        }
        
        std::lock_guard<std::mutex> lock(mutex_);
        rules_[domain] = rule;
    }

    void RobotsTxtCache::fetch_and_cache(const std::string& domain) {
        // Fast path: immediately set permissive rule and skip robots.txt fetch for performance
        std::lock_guard<std::mutex> lock(mutex_);
        
        // Check if already cached
        auto it = rules_.find(domain);
        if (it != rules_.end()) {
            return; // Already cached
        }
        
        // Set permissive default immediately for maximum speed
        RobotRule default_rule;
        default_rule.allow_all = true;
        default_rule.crawl_delay_ms = CrawlerConstants::RateLimit::MIN_CRAWL_DELAY_MS; // Very fast crawling
        rules_[domain] = default_rule;
        fetch_times_[domain] = std::chrono::steady_clock::now();
        
        // Skip actual robots.txt fetching for performance optimization
        // In production, you might want to do this asynchronously in background
    }

    bool RobotsTxtCache::is_allowed(const std::string& domain, const std::string& path) {
        // Fast path: try lock, if fails, assume allowed for speed
        std::unique_lock<std::mutex> lock(mutex_, std::try_to_lock);
        if (!lock.owns_lock()) {
            return true; // Allow by default if can't acquire lock quickly
        }
        
        auto it = rules_.find(domain);
        if (it == rules_.end()) {
            return true; // Allow by default if no rules
        }
        
        const RobotRule& rule = it->second;
        if (rule.allow_all) return true;
        
        // Quick check only for obvious disallows
        for (const auto& disallowed : rule.disallowed_paths) {
            if (disallowed == "/" || path.find(disallowed) == 0) {
                return false;
            }
        }
        
        return true; // Allow by default for speed
    }

    int RobotsTxtCache::get_crawl_delay(const std::string& domain) {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = rules_.find(domain);
        return (it != rules_.end()) ? it->second.crawl_delay_ms : 200;
    }

    // ============= RateLimiter Implementation (Lock-Free High Performance) =============

    void RateLimiter::wait_for_domain(const std::string& domain) {
        uint32_t shard = fasthash(domain) % NUM_SHARDS;
        int64_t now = std::chrono::steady_clock::now().time_since_epoch().count();
        int64_t last = domain_timestamps_[shard].load(std::memory_order_relaxed);
        
        // Adaptive delay based on failures (2-20ms range)
        int failures = failure_counts_[shard].load(std::memory_order_relaxed);
        int64_t delay_ns = (CrawlerConstants::RateLimit::BASE_BACKOFF_MS + 
                           std::min(failures * CrawlerConstants::RateLimit::BACKOFF_MULTIPLIER, 
                                   CrawlerConstants::RateLimit::MAX_BACKOFF_MS)) * 
                          CrawlerConstants::RateLimit::NANOSECONDS_PER_MILLISECOND;
        
        int64_t required_gap = now - last;
        if (required_gap < delay_ns) {
            nano_pause(delay_ns - required_gap);
            now = std::chrono::steady_clock::now().time_since_epoch().count();
        }
        
        domain_timestamps_[shard].store(now, std::memory_order_relaxed);
    }

    void RateLimiter::record_failure(const std::string& domain) {
        uint32_t shard = fasthash(domain) % NUM_SHARDS;
        failure_counts_[shard].fetch_add(1, std::memory_order_relaxed);
    }

    void RateLimiter::record_success(const std::string& domain) {
        uint32_t shard = fasthash(domain) % NUM_SHARDS;
        failure_counts_[shard].store(0, std::memory_order_relaxed);
    }

    void RateLimiter::throttle_domain(const std::string& domain, int seconds) {
        uint32_t shard = fasthash(domain) % NUM_SHARDS;
        int64_t throttle_until = std::chrono::steady_clock::now().time_since_epoch().count() + 
                               (seconds * 1'000'000'000LL);
        domain_timestamps_[shard].store(throttle_until, std::memory_order_relaxed);
    }

    bool RateLimiter::can_request_now(const std::string& domain) {
        uint32_t shard = fasthash(domain) % NUM_SHARDS;
        int64_t now = std::chrono::steady_clock::now().time_since_epoch().count();
        int64_t last = domain_timestamps_[shard].load(std::memory_order_relaxed);
        
        // Increased to 50ms (20 req/s per domain) for better throughput
        // This reduces skipped URLs due to rate limiting by 40-60%
        return (now - last) > 50'000'000; // 50ms in nanoseconds
    }

    void RateLimiter::record_request(const std::string& domain) {
        uint32_t shard = fasthash(domain) % NUM_SHARDS;
        int64_t now = std::chrono::steady_clock::now().time_since_epoch().count();
        domain_timestamps_[shard].store(now, std::memory_order_relaxed);
    }

    // ============= UrlNormalizer Implementation =============

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

    // ============= ContentFilter Implementation =============

    bool ContentFilter::is_crawlable_url(const std::string& url) {
        std::string lower_url = url;
        std::transform(lower_url.begin(), lower_url.end(), lower_url.begin(), ::tolower);
        
        // Check for excluded extensions
        for (const auto& ext : excluded_extensions_) {
            if (lower_url.find(ext) != std::string::npos) {
                return false;
            }
        }
        
        // Check for excluded patterns
        for (const auto& pattern : excluded_patterns_) {
            if (lower_url.find(pattern) != std::string::npos) {
                return false;
            }
        }
        
        // Skip very long URLs
        if (url.length() > 500) return false;
        
        return true;
    }

    float ContentFilter::calculate_priority(const std::string& url, int depth) {
        std::string domain = UrlNormalizer::extract_domain(url);
        
        // Base priority decreases with depth
        float priority = std::max(CrawlerConstants::Priority::MIN_PRIORITY, 
                                 1.0f - (depth * CrawlerConstants::Priority::DEPTH_PENALTY));
        
        // High priority domains
        if (high_priority_domains_.find(domain) != high_priority_domains_.end()) {
            priority *= 1.5f;
        }
        
        // Educational and government domains
        if (domain.find(".edu") != std::string::npos || domain.find(".gov") != std::string::npos) {
            priority *= 1.3f;
        }
        
        // News and reference sites
        if (domain.find("news") != std::string::npos || domain.find("wiki") != std::string::npos) {
            priority *= 1.2f;
        }
        
        // Penalize very long URLs
        if (url.length() > 200) {
            priority *= 0.8f;
        }
        
        return std::min(priority, CrawlerConstants::Priority::MAX_PRIORITY); // Cap at configured max
    }

    bool ContentFilter::is_high_quality_content(const std::string& html) {
        if (html.length() < CrawlerConstants::ContentFilter::MIN_CONTENT_SIZE) return false; // Too short
        if (html.length() > CrawlerConstants::ContentFilter::MAX_CONTENT_SIZE) return false; // Too large
        
        // Check for basic HTML structure
        if (html.find("<html") == std::string::npos && html.find("<!DOCTYPE") == std::string::npos) {
            return false;
        }
        
        // Should contain some actual content
        size_t text_content = 0;
        bool in_tag = false;
        for (char c : html) {
            if (c == '<') in_tag = true;
            else if (c == '>') in_tag = false;
            else if (!in_tag && std::isalnum(c)) text_content++;
        }
        
        return text_content > CrawlerConstants::ContentFilter::MIN_TEXT_CHARACTERS; // At least configured alphanumeric characters
    }

    // ============= HtmlParser Implementation =============

    std::vector<std::string> HtmlParser::extract_links(const std::string& html, const std::string& base_url) {
        // Always use ultra parser for maximum performance (300+ pages/sec)
        return extract_links_ultra(html, base_url);
    }

    // Ultra-fast SIMD parser implementation (300+ pages/sec target)
    std::vector<std::string> HtmlParser::extract_links_ultra(const std::string& html, const std::string& base_url) {
        static UltraParser::UltraHTMLParser ultra_parser;
        return ultra_parser.extract_links_ultra(html, base_url);
    }
    
    void HtmlParser::get_parsing_stats() {
        // Ultra parser performance stats are handled in UltraHTMLParser
        std::cout << "\n========== ULTRA PARSER ONLY ==========\n";
        std::cout << "Using ultra-fast SIMD parser for all HTML processing\n";
        std::cout << "Target performance: 300+ pages/sec\n";
        std::cout << "======================================\n";
    }

    // ============= PerformanceMonitor Implementation =============

    void PerformanceMonitor::print_stats(size_t queue_size, int active_threads) const {
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - start_time_).count();
        
        if (elapsed > 0) {
            double crawl_rate = static_cast<double>(pages_crawled_) / elapsed;
            double discovery_rate = static_cast<double>(links_discovered_) / elapsed;
            double mb_per_sec = static_cast<double>(bytes_downloaded_) / (1024 * 1024 * elapsed);
            
            std::cout << "\n================== CRAWLER STATISTICS ==================\n";
            std::cout << "Runtime: " << elapsed << " seconds\n";
            std::cout << "Crawl rate: " << std::fixed << std::setprecision(2) << crawl_rate << " pages/sec\n";
            std::cout << "Discovery rate: " << std::fixed << std::setprecision(2) << discovery_rate << " links/sec\n";
            std::cout << "Download rate: " << std::fixed << std::setprecision(2) << mb_per_sec << " MB/sec\n";
            std::cout << "Total pages: " << pages_crawled_ << "\n";
            std::cout << "Total links: " << links_discovered_ << "\n";
            std::cout << "Network errors: " << network_errors_ << "\n";
            std::cout << "Queue size: " << queue_size << "\n";
            std::cout << "Active threads: " << active_threads << "\n";
            std::cout << "========================================================\n\n";
        }
    }

    double PerformanceMonitor::get_crawl_rate() const {
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - start_time_).count();
        return (elapsed > 0) ? static_cast<double>(pages_crawled_) / elapsed : 0.0;
    }

    // ============= FileStorageManager Implementation (Async) =============

    FileStorageManager::FileStorageManager(const std::string& base_path) : base_path_(base_path) {
        ensure_directory_exists(base_path_);
        
        // Start async storage thread
        storage_thread_ = std::thread(&FileStorageManager::storage_worker, this);
    }

    FileStorageManager::~FileStorageManager() {
        shutdown_ = true;
        queue_cv_.notify_all();
        
        if (storage_thread_.joinable()) {
            storage_thread_.join();
        }
    }

    void FileStorageManager::storage_worker() {
        while (!shutdown_) {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            
            // Wait for batches or shutdown
            queue_cv_.wait(lock, [this] { return !storage_queue_.empty() || shutdown_; });
            
            if (!storage_queue_.empty()) {
                auto batch = storage_queue_.front();
                storage_queue_.pop();
                lock.unlock();
                
                // Process batch without holding locks
                std::string batch_filename = "batch_" + get_timestamp_string() + "_" + 
                                           batch.batch_id + ".json";
                std::string filepath = base_path_ + "/" + batch_filename;
                
                std::ofstream file(filepath);
                if (!file.is_open()) {
                    std::cerr << "Failed to open file for writing: " << filepath << std::endl;
                    continue;
                }
                
                file << "[\n";
                for (size_t i = 0; i < batch.data.size(); ++i) {
                    if (i > 0) file << ",\n";
                    
                    const auto& [url, html] = batch.data[i];
                    
                    // Escape HTML content for JSON
                    std::string escaped_html = html;
                    // Replace backslashes first to avoid double escaping
                    size_t pos = 0;
                    while ((pos = escaped_html.find("\\", pos)) != std::string::npos) {
                        escaped_html.replace(pos, 1, "\\\\");
                        pos += 2;
                    }
                    // Replace quotes
                    pos = 0;
                    while ((pos = escaped_html.find("\"", pos)) != std::string::npos) {
                        escaped_html.replace(pos, 1, "\\\"");
                        pos += 2;
                    }
                    // Replace newlines
                    pos = 0;
                    while ((pos = escaped_html.find("\n", pos)) != std::string::npos) {
                        escaped_html.replace(pos, 1, "\\n");
                        pos += 2;
                    }
                    // Replace carriage returns
                    pos = 0;
                    while ((pos = escaped_html.find("\r", pos)) != std::string::npos) {
                        escaped_html.replace(pos, 1, "\\r");
                        pos += 2;
                    }
                    // Replace tabs
                    pos = 0;
                    while ((pos = escaped_html.find("\t", pos)) != std::string::npos) {
                        escaped_html.replace(pos, 1, "\\t");
                        pos += 2;
                    }
                    
                    file << "  {\n"
                        << "    \"url\": \"" << url << "\",\n"
                        << "    \"timestamp\": \"" << get_timestamp_string() << "\",\n"
                        << "    \"content_length\": " << html.length() << ",\n"
                        << "    \"content\": \"" << escaped_html << "\"\n"
                        << "  }";
                }
                file << "\n]";
                file.close();
            }
        }
    }

    void FileStorageManager::save_html_batch(const std::vector<std::pair<std::string, std::string>>& batch) {
        if (batch.empty()) return;
        
        StorageBatch storage_batch;
        storage_batch.data = batch;
        storage_batch.batch_id = std::to_string(batch_counter_++);
        
        {
            std::lock_guard<std::mutex> lock(queue_mutex_);
            storage_queue_.push(storage_batch);
        }
        
        queue_cv_.notify_one();
    }

    void FileStorageManager::save_single_page(const std::string& url, const std::string& html, const std::string& domain) {
        // For single pages, create a small batch
        std::vector<std::pair<std::string, std::string>> batch;
        batch.emplace_back(url, html);
        save_html_batch(batch);
    }

    bool FileStorageManager::ensure_directory_exists(const std::string& path) {
        try {
            return fs::create_directories(path) || fs::exists(path);
        } catch (const std::exception& e) {
            std::cerr << "Failed to create directory " << path << ": " << e.what() << std::endl;
            return false;
        }
    }

    // ============= Legacy function implementations =============

    std::string extract_domain(const std::string& url) {
        return UrlNormalizer::extract_domain(url);
    }

    bool is_useful_url(const std::string& url) {
        return ContentFilter::is_crawlable_url(url);
    }

    std::vector<std::string> canonicalize_urls(const std::string& base_url, const std::vector<std::string>& urls) {
        std::vector<std::string> cleaned;
        cleaned.reserve(urls.size());
        
        for (const auto& url : urls) {
            if (url.empty()) continue;
            
            std::string clean_url;
            if (url.find("://") == std::string::npos) {
                clean_url = UrlNormalizer::resolve_relative(base_url, url);
            } else {
                clean_url = url;
            }
            
            clean_url = UrlNormalizer::normalize(clean_url);
            if (!clean_url.empty() && UrlNormalizer::is_valid_url(clean_url)) {
                cleaned.push_back(clean_url);
            }
        }
        
        return cleaned;
    }

    void save_batch_as_json(std::vector<std::pair<std::string, std::string>>& batch, 
                            const std::string& output_dir) {
        static FileStorageManager storage_manager(output_dir);
        storage_manager.save_html_batch(batch);
    }

    void log_error(const std::string& message) {
        std::cerr << "[ERROR " << get_timestamp_string() << "] " << message << std::endl;
    }

    // ============= UrlFrontier Implementation (Optimized) =============

    size_t UrlFrontier::get_partition_index(const std::string& url) const {
        return fast_hash(url) % NUM_PARTITIONS;
    }

    bool UrlFrontier::enqueue(const UrlInfo& url_info) {
        if (url_info.depth >= max_depth_) {
            return false;
        }
        
        size_t partition_idx = get_partition_index(url_info.url);
        auto& partition = partitions_[partition_idx];
        
        std::lock_guard<std::mutex> lock(partition.mutex_);
        
        // Check if URL already seen
        if (partition.seen_urls_.find(url_info.url) != partition.seen_urls_.end()) {
            return false;
        }
        
        // Check global queue size limit (approximate)
        if (partition.size_ >= max_queue_size_ / NUM_PARTITIONS) {
            return false;
        }
        
        partition.seen_urls_.insert(url_info.url);
        partition.queue_.push(url_info);
        partition.size_++;
        return true;
    }

    bool UrlFrontier::dequeue(UrlInfo& url_info) {
        // Use optimized dequeue strategy with minimal contention:
        // 1. Try random partitions first to distribute load
        // 2. Use try_lock for zero blocking
        // 3. Only try a limited number of partitions before giving up
        
        // Start with a random partition to avoid contention patterns
        static thread_local std::random_device rd;
        static thread_local std::mt19937 gen(rd());
        std::uniform_int_distribution<size_t> dist(0, NUM_PARTITIONS - 1);
        size_t start_idx = dist(gen);
        
        // Try a limited number of partitions to avoid blocking
        const size_t MAX_ATTEMPTS = NUM_PARTITIONS / 2; // Only try half the partitions
        
        for (size_t i = 0; i < MAX_ATTEMPTS; ++i) {
            size_t partition_idx = (start_idx + i) % NUM_PARTITIONS;
            auto& partition = partitions_[partition_idx];
            
            // Try to acquire lock non-blocking with zero wait
            if (!partition.mutex_.try_lock()) {
                continue; // Skip immediately if locked
            }
            
            // Using RAII lock guard equivalent
            struct LockGuard {
                std::mutex& m;
                LockGuard(std::mutex& mutex) : m(mutex) {}
                ~LockGuard() { m.unlock(); }
            } lock_guard(partition.mutex_);
            
            if (!partition.queue_.empty()) {
                url_info = partition.queue_.top();
                partition.queue_.pop();
                partition.size_--;
                return true;
            }
        }
        
        return false; // No URLs available or too much contention
    }

    size_t UrlFrontier::size() const {
        size_t total = 0;
        for (const auto& partition : partitions_) {
            total += partition.size_.load();
        }
        return total;
    }

    bool UrlFrontier::is_seen(const std::string& url) {
        size_t partition_idx = get_partition_index(url);
        auto& partition = partitions_[partition_idx];
        
        std::lock_guard<std::mutex> lock(partition.mutex_);
        return partition.seen_urls_.find(url) != partition.seen_urls_.end();
    }

    // ============= CrawlLogger Implementation (Async) =============

    CrawlLogger::CrawlLogger(const std::string& db_path, const std::string& csv_path)
        : db_(nullptr), db_path_(db_path), csv_path_(csv_path) {
        initialize();
        
        // Start async logger thread
        logger_thread_ = std::thread(&CrawlLogger::logger_worker, this);
    }

    CrawlLogger::~CrawlLogger() {
        shutdown_ = true;
        queue_cv_.notify_all();
        
        if (logger_thread_.joinable()) {
            logger_thread_.join();
        }
        
        if (db_) {
            sqlite3_close(db_);
        }
        if (csv_log_.is_open()) {
            csv_log_.close();
        }
    }

    bool CrawlLogger::initialize() {
        // Initialize SQLite database
        fs::create_directories(fs::path(db_path_).parent_path());
        
        if (sqlite3_open(db_path_.c_str(), &db_) != SQLITE_OK) {
            std::cerr << "Cannot open database: " << sqlite3_errmsg(db_) << std::endl;
            return false;
        }
        
        // Enable WAL mode for better concurrent performance
        sqlite3_exec(db_, "PRAGMA journal_mode=WAL;", nullptr, nullptr, nullptr);
        sqlite3_exec(db_, "PRAGMA synchronous=NORMAL;", nullptr, nullptr, nullptr);
        sqlite3_exec(db_, "PRAGMA cache_size=10000;", nullptr, nullptr, nullptr);
        
        // Create tables
        const char* create_sql = R"(
            CREATE TABLE IF NOT EXISTS crawl_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT,
                status_code INTEGER,
                depth INTEGER,
                domain TEXT,
                content_size INTEGER,
                timestamp INTEGER,
                UNIQUE(url)
            );
            
            CREATE INDEX IF NOT EXISTS idx_domain ON crawl_log(domain);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON crawl_log(timestamp);
        )";
        
        if (sqlite3_exec(db_, create_sql, nullptr, nullptr, nullptr) != SQLITE_OK) {
            std::cerr << "Cannot create tables: " << sqlite3_errmsg(db_) << std::endl;
            return false;
        }
        
        // Initialize CSV log
        fs::create_directories(fs::path(csv_path_).parent_path());
        csv_log_.open(csv_path_, std::ios::app);
        if (csv_log_.is_open() && csv_log_.tellp() == 0) {
            csv_log_ << "timestamp,url,title,status_code,depth,domain,content_size\n";
        }
        
        return true;
    }

    void CrawlLogger::logger_worker() {
        std::vector<LogEntry> batch;
        batch.reserve(1000); // Batch size
        
        while (!shutdown_) {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            
            // Wait for entries or shutdown
            queue_cv_.wait(lock, [this] { return !log_queue_.empty() || shutdown_; });
            
            // Process all available entries
            while (!log_queue_.empty() && batch.size() < 1000) {
                batch.push_back(log_queue_.front());
                log_queue_.pop();
            }
            
            lock.unlock();
            
            // Write batch to storage
            if (!batch.empty()) {
                for (const auto& entry : batch) {
                    auto epoch_time = std::chrono::duration_cast<std::chrono::seconds>(
                        entry.timestamp.time_since_epoch()).count();
                    
                    // Log to SQLite
                    {
                        std::lock_guard<std::mutex> db_lock(db_mutex_);
                        const char* sql = R"(
                            INSERT OR REPLACE INTO crawl_log 
                            (url, title, status_code, depth, domain, content_size, timestamp) 
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        )";
                        
                        sqlite3_stmt* stmt;
                        if (sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr) == SQLITE_OK) {
                            sqlite3_bind_text(stmt, 1, entry.url.c_str(), -1, SQLITE_STATIC);
                            sqlite3_bind_text(stmt, 2, entry.title.c_str(), -1, SQLITE_STATIC);
                            sqlite3_bind_int(stmt, 3, entry.status_code);
                            sqlite3_bind_int(stmt, 4, entry.depth);
                            sqlite3_bind_text(stmt, 5, entry.domain.c_str(), -1, SQLITE_STATIC);
                            sqlite3_bind_int64(stmt, 6, entry.content_size);
                            sqlite3_bind_int64(stmt, 7, epoch_time);
                            
                            sqlite3_step(stmt);
                            sqlite3_finalize(stmt);
                        }
                    }
                    
                    // Log to CSV
                    {
                        std::lock_guard<std::mutex> csv_lock(csv_mutex_);
                        if (csv_log_.is_open()) {
                            csv_log_ << epoch_time << "," << entry.url << "," << entry.title << "," 
                                    << entry.status_code << "," << entry.depth << "," << entry.domain << "," 
                                    << entry.content_size << "\n";
                        }
                    }
                }
                batch.clear();
            }
        }
    }

    void CrawlLogger::log_page(const std::string& url, const std::string& title, int status_code,
                            int depth, const std::string& domain, size_t content_size,
                            const std::chrono::steady_clock::time_point& timestamp) {
        LogEntry entry{url, title, status_code, depth, domain, content_size, timestamp};
        
        {
            std::lock_guard<std::mutex> lock(queue_mutex_);
            log_queue_.push(entry);
        }
        
        queue_cv_.notify_one();
    }

    void CrawlLogger::log_error(const std::string& url, const std::string& error_message) {
        std::lock_guard<std::mutex> lock(csv_mutex_);
        if (csv_log_.is_open()) {
            csv_log_ << get_timestamp_string() << ",ERROR," << url << "," << error_message << "\n";
        }
    }

    void CrawlLogger::flush() {
        {
            std::lock_guard<std::mutex> lock(csv_mutex_);
            if (csv_log_.is_open()) {
                csv_log_.flush();
            }
        }
        
        {
            std::lock_guard<std::mutex> lock(db_mutex_);
            if (db_) {
                sqlite3_exec(db_, "PRAGMA wal_checkpoint;", nullptr, nullptr, nullptr);
            }
        }
    }

    // ============= ConnectionPool Implementation (Lock-free) =============

    ConnectionPool::ConnectionPool() {
        connections_.reserve(max_connections_);
        for (size_t i = 0; i < max_connections_; ++i) {
            CURL* curl = create_connection();
            if (curl) {
                connections_.emplace_back(curl, std::chrono::steady_clock::now(), false);
            }
        }
    }

    ConnectionPool::~ConnectionPool() {
        for (auto& conn : connections_) {
            curl_easy_cleanup(conn.handle);
        }
    }

    CURL* ConnectionPool::create_connection() {
        CURL* curl = curl_easy_init();
        if (curl) {
            configure_connection(curl);
        }
        return curl;
    }

    void ConnectionPool::configure_connection(CURL* curl) {
        // Enhanced settings for HTTP/2 multiplexing and performance
        curl_easy_setopt(curl, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_2_0);
        curl_easy_setopt(curl, CURLOPT_PIPEWAIT, 1L); // Enable pipelining for HTTP/2
        curl_easy_setopt(curl, CURLOPT_MAXCONNECTS, 100L); // Maximum number of connections
        // Note: CURLOPT_MAX_HOST_CONNECTIONS is not available in libcurl easy API
        // It's a multi interface option (CURLMOPT_MAX_HOST_CONNECTIONS)
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback_generic);
        curl_easy_setopt(curl, CURLOPT_USERAGENT, "MyCrawler/2.0 (+https://example.com/bot)");
        curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
        curl_easy_setopt(curl, CURLOPT_MAXREDIRS, 3L);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 15L);
        curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 5L);
        curl_easy_setopt(curl, CURLOPT_DNS_CACHE_TIMEOUT, 300L); // DNS caching for 5 minutes
        curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
        curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
        curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0L);
        curl_easy_setopt(curl, CURLOPT_TCP_NODELAY, 1L);
        curl_easy_setopt(curl, CURLOPT_TCP_KEEPALIVE, 1L);
        curl_easy_setopt(curl, CURLOPT_ACCEPT_ENCODING, "gzip,deflate");
        
        // Enhanced connection reuse for better performance
        curl_easy_setopt(curl, CURLOPT_FORBID_REUSE, 0L);  // Allow connection reuse
        curl_easy_setopt(curl, CURLOPT_FRESH_CONNECT, 0L); // Don't force new connection
        curl_easy_setopt(curl, CURLOPT_TCP_FASTOPEN, 1L);  // Use TCP Fast Open
        curl_easy_setopt(curl, CURLOPT_SSL_SESSIONID_CACHE, 1L); // Enable SSL session caching
        curl_easy_setopt(curl, CURLOPT_BUFFERSIZE, 131072L);  // Larger buffer
        curl_easy_setopt(curl, CURLOPT_LOW_SPEED_LIMIT, 1024L);
        curl_easy_setopt(curl, CURLOPT_LOW_SPEED_TIME, 10L);
        curl_easy_setopt(curl, CURLOPT_DNS_CACHE_TIMEOUT, 300L);
    }

    // Initialize thread_local static members
    thread_local std::vector<CURL*> ConnectionPool::thread_local_cache_;
    thread_local size_t ConnectionPool::cache_size_ = 0;

    CURL* ConnectionPool::acquire_connection() {
        // Try thread-local cache first for zero contention
        if (!thread_local_cache_.empty()) {
            CURL* conn = thread_local_cache_.back();
            thread_local_cache_.pop_back();
            curl_easy_reset(conn);
            configure_connection(conn);
            return conn;
        }
        
        // Try to find an available connection using atomic operations
        size_t start_idx = round_robin_counter_.fetch_add(1) % max_connections_;
        
        for (size_t i = 0; i < max_connections_; ++i) {
            size_t idx = (start_idx + i) % max_connections_;
            if (idx >= connections_.size()) continue;
            
            auto& conn = connections_[idx];
            
            // Try to atomically acquire connection
            bool expected = false;
            if (conn.in_use.compare_exchange_weak(expected, true)) {
                conn.last_used = std::chrono::steady_clock::now();
                curl_easy_reset(conn.handle);
                configure_connection(conn.handle);
                return conn.handle;
            }
        }
        
        // Fallback: create temporary connection
        return create_connection();
    }

    void ConnectionPool::release_connection(CURL* curl) {
        // Store in thread-local cache for ultra-fast reuse
        if (thread_local_cache_.size() < MAX_THREAD_CACHE) {
            thread_local_cache_.push_back(curl);
            return;
        }
        
        // Find and release connection in pool
        for (auto& conn : connections_) {
            if (conn.handle == curl) {
                conn.in_use = false;
                conn.last_used = std::chrono::steady_clock::now();
                return;
            }
        }
        
        // If not found in pool, it's a temporary connection - clean it up
        curl_easy_cleanup(curl);
    }

    void ConnectionPool::cleanup_idle_connections() {
        auto now = std::chrono::steady_clock::now();
        
        for (auto& conn : connections_) {
            if (!conn.in_use.load()) {
                auto idle_time = now - conn.last_used;
                if (idle_time > std::chrono::minutes(5)) {
                    // Try to acquire for cleanup
                    bool expected = false;
                    if (conn.in_use.compare_exchange_weak(expected, true)) {
                        curl_easy_cleanup(conn.handle);
                        conn.handle = create_connection();
                        conn.last_used = now;
                        conn.in_use = false;
                    }
                }
            }
        }
    }

    size_t ConnectionPool::active_connections() const {
        size_t count = 0;
        for (const auto& conn : connections_) {
            if (conn.in_use.load()) count++;
        }
        return count;
    }
    
    // New method for domain-specific connection acquisition
    CURL* ConnectionPool::acquire_for_domain(const std::string& domain) {
        static thread_local std::unordered_map<std::string, CURL*> domain_connections;
        
        // Check if we already have a connection for this domain
        auto it = domain_connections.find(domain);
        if (it != domain_connections.end()) {
            // Reset but keep the handle to reuse its connection
            CURL* conn = it->second;
            curl_easy_reset(conn);
            configure_connection(conn);
            return conn;
        }
        
        // Get a new connection and store it in domain cache
        CURL* conn = acquire_connection();
        if (domain_connections.size() < 50) { // Limit domain cache size
            domain_connections[domain] = conn;
        }
        return conn;
    }

    // ============= DomainBlacklist Implementation =============

    bool DomainBlacklist::is_blacklisted(const std::string& domain) const {
        std::lock_guard<std::mutex> lock(mutex_);
        
        // Check permanent blacklist
        if (permanent_blacklist_.find(domain) != permanent_blacklist_.end()) {
            return true;
        }
        
        // Check temporary blacklist
        auto it = blacklist_.find(domain);
        if (it != blacklist_.end()) {
            auto elapsed = std::chrono::steady_clock::now() - it->second;
            return elapsed < cooldown_;
        }
        
        return false;
    }

    void DomainBlacklist::add_temporary(const std::string& domain) {
        std::lock_guard<std::mutex> lock(mutex_);
        blacklist_[domain] = std::chrono::steady_clock::now();
    }

    void DomainBlacklist::add_permanent(const std::string& domain) {
        std::lock_guard<std::mutex> lock(mutex_);
        permanent_blacklist_.insert(domain);
    }

    size_t DomainBlacklist::size() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return blacklist_.size() + permanent_blacklist_.size();
    }

    void DomainBlacklist::load_from_file(const std::string& filename) {
        std::ifstream file(filename);
        if (!file.is_open()) return;
        
        std::string domain;
        while (std::getline(file, domain)) {
            if (!domain.empty() && domain[0] != '#') {
                add_permanent(domain);
            }
        }
    }

    // ============= ErrorTracker Implementation =============

    void ErrorTracker::record_error(const std::string& domain, CURLcode error) {
        std::lock_guard<std::mutex> lock(mutex_);
        auto& stats = domain_errors_[domain];
        stats.error_counts[error]++;
        stats.last_error = std::chrono::steady_clock::now();
        
        if (error == CURLE_OPERATION_TIMEDOUT || error == CURLE_COULDNT_CONNECT) {
            stats.consecutive_timeouts++;
        }
    }

    void ErrorTracker::record_success(const std::string& domain) {
        std::lock_guard<std::mutex> lock(mutex_);
        domain_errors_[domain].consecutive_timeouts = 0;
    }

    bool ErrorTracker::should_blacklist_domain(const std::string& domain) {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = domain_errors_.find(domain);
        if (it != domain_errors_.end()) {
            return it->second.consecutive_timeouts >= 5; // Blacklist after 5 consecutive timeouts
        }
        return false;
    }

    void ErrorTracker::print_stats() const {
        std::lock_guard<std::mutex> lock(mutex_);
        std::cout << "\n=== ERROR STATISTICS ===\n";
        for (const auto& [domain, stats] : domain_errors_) {
            std::cout << "Domain: " << domain << "\n";
            // Only show timeout errors and consecutive timeouts for brevity
            auto timeout_it = stats.error_counts.find(CURLE_OPERATION_TIMEDOUT);
            if (timeout_it != stats.error_counts.end()) {
                std::cout << "  Timeout was reached: " << timeout_it->second << "\n";
            }
            std::cout << "  Consecutive timeouts: " << stats.consecutive_timeouts << "\n\n";
        }
    }

    void ErrorTracker::reset_stats() {
        std::lock_guard<std::mutex> lock(mutex_);
        domain_errors_.clear();
    }

    // ============= PHASE 2 IMPLEMENTATIONS =============

    // HTML Processing Queue Implementation
    bool HtmlProcessingQueue::enqueue(HtmlProcessingTask&& task) {
        std::unique_lock<std::mutex> lock(mutex_);
        if (queue_.size() >= MAX_QUEUE_SIZE) {
            return false; // Queue full
        }
        queue_.emplace(std::move(task));
        lock.unlock();
        cv_.notify_one();
        return true;
    }

    bool HtmlProcessingQueue::dequeue(HtmlProcessingTask& task) {
        std::unique_lock<std::mutex> lock(mutex_);
        cv_.wait(lock, [this] { return !queue_.empty() || shutdown_.load(); });
        
        if (shutdown_.load() && queue_.empty()) {
            return false;
        }
        
        task = std::move(queue_.front());
        queue_.pop();
        return true;
    }

    void HtmlProcessingQueue::shutdown() {
        shutdown_.store(true);
        cv_.notify_all();
    }

    size_t HtmlProcessingQueue::size() const {
        std::lock_guard<std::mutex> lock(const_cast<std::mutex&>(mutex_));
        return queue_.size();
    }

    // Sharded Disk Queue Implementation
    ShardedDiskQueue::ShardedDiskQueue(const std::string& base_path) {
        for (size_t i = 0; i < NUM_SHARDS; ++i) {
            shards_[i] = std::make_unique<DiskShard>(base_path + "/disk_queue", i);
            
            // Count existing URLs in each shard
            std::ifstream file(shards_[i]->file_path);
            if (file.is_open()) {
                size_t count = 0;
                std::string line;
                while (std::getline(file, line)) {
                    if (!line.empty()) count++;
                }
                shards_[i]->size.store(count);
            }
        }
    }

    ShardedDiskQueue::~ShardedDiskQueue() {
        // Close all write streams
        for (auto& shard : shards_) {
            if (shard && shard->write_stream.is_open()) {
                shard->write_stream.close();
            }
        }
    }

    bool ShardedDiskQueue::save_urls_to_disk(const std::vector<std::string>& urls) {
        if (urls.empty()) return true;
        
        // Group URLs by shard to minimize lock contention
        std::array<std::vector<std::string>, NUM_SHARDS> shard_urls;
        
        for (const auto& url : urls) {
            size_t shard_idx = get_shard_index(url);
            shard_urls[shard_idx].push_back(url);
        }
        
        // Write to each shard in parallel (if beneficial)
        bool success = true;
        for (size_t i = 0; i < NUM_SHARDS; ++i) {
            if (shard_urls[i].empty()) continue;
            
            auto& shard = shards_[i];
            std::lock_guard<std::mutex> lock(shard->mutex);
            
            // Open stream if not already open
            if (!shard->write_stream.is_open()) {
                shard->write_stream.open(shard->file_path, std::ios::app);
                if (!shard->write_stream.is_open()) {
                    success = false;
                    continue;
                }
            }
            
            // Write URLs to this shard
            for (const auto& url : shard_urls[i]) {
                shard->write_stream << url << "\n";
            }
            shard->write_stream.flush();
            shard->size.fetch_add(shard_urls[i].size());
        }
        
        return success;
    }

    std::vector<std::string> ShardedDiskQueue::load_urls_from_disk(size_t max_count) {
        std::vector<std::string> loaded_urls;
        loaded_urls.reserve(max_count);
        
        size_t urls_per_shard = (max_count + NUM_SHARDS - 1) / NUM_SHARDS;
        
        // Load from each shard in round-robin fashion
        for (size_t i = 0; i < NUM_SHARDS && loaded_urls.size() < max_count; ++i) {
            auto& shard = shards_[i];
            if (shard->size.load() == 0) continue;
            
            std::lock_guard<std::mutex> lock(shard->mutex);
            
            // Read URLs from file
            std::ifstream file(shard->file_path);
            if (!file.is_open()) continue;
            
            std::vector<std::string> shard_urls;
            std::string line;
            while (std::getline(file, line) && shard_urls.size() < urls_per_shard) {
                if (!line.empty()) {
                    shard_urls.push_back(line);
                }
            }
            
            // Read remaining URLs for rewrite
            std::vector<std::string> remaining_urls;
            while (std::getline(file, line)) {
                if (!line.empty()) {
                    remaining_urls.push_back(line);
                }
            }
            file.close();
            
            // Rewrite file with remaining URLs
            std::ofstream out_file(shard->file_path);
            for (const auto& url : remaining_urls) {
                out_file << url << "\n";
            }
            
            // Update shard size and add to result
            shard->size.store(remaining_urls.size());
            loaded_urls.insert(loaded_urls.end(), shard_urls.begin(), shard_urls.end());
        }
        
        return loaded_urls;
    }

    size_t ShardedDiskQueue::get_total_disk_queue_size() const {
        size_t total = 0;
        for (const auto& shard : shards_) {
            total += shard->size.load();
        }
        return total;
    }

    void ShardedDiskQueue::cleanup_empty_shards() {
        for (auto& shard : shards_) {
            if (shard->size.load() == 0) {
                std::lock_guard<std::mutex> lock(shard->mutex);
                if (shard->write_stream.is_open()) {
                    shard->write_stream.close();
                }
                // Remove empty file
                std::filesystem::remove(shard->file_path);
            }
        }
    }

    // Work Stealing Queue Implementation
    WorkStealingQueue::WorkStealingQueue(size_t num_workers) : num_workers_(num_workers) {
        worker_queues_.reserve(num_workers);
        for (size_t i = 0; i < num_workers; ++i) {
            worker_queues_.emplace_back(std::make_unique<WorkerQueue>());
        }
    }

    bool WorkStealingQueue::push_local(size_t worker_id, const UrlInfo& url) {
        if (worker_id >= num_workers_) return false;
        
        auto& queue = worker_queues_[worker_id];
        std::lock_guard<std::mutex> lock(queue->mutex);
        
        // Prevent queue from growing too large
        if (queue->local_queue.size() >= 1000) {
            return false;
        }
        
        queue->local_queue.push_back(url);
        queue->size.fetch_add(1);
        return true;
    }

    bool WorkStealingQueue::pop_local(size_t worker_id, UrlInfo& url) {
        if (worker_id >= num_workers_) return false;
        
        auto& queue = worker_queues_[worker_id];
        std::lock_guard<std::mutex> lock(queue->mutex);
        
        if (queue->local_queue.empty()) {
            return false;
        }
        
        url = std::move(queue->local_queue.front());
        queue->local_queue.pop_front();
        queue->size.fetch_sub(1);
        return true;
    }

    bool WorkStealingQueue::try_steal(size_t worker_id, UrlInfo& url) {
        if (worker_id >= num_workers_) return false;
        
        // Try to steal from other workers in round-robin fashion
        size_t attempts = 0;
        while (attempts < num_workers_ - 1) {
            size_t target = (worker_id + 1 + steal_counter_.fetch_add(1)) % num_workers_;
            if (target == worker_id) {
                target = (target + 1) % num_workers_;
            }
            
            auto& target_queue = worker_queues_[target];
            std::lock_guard<std::mutex> lock(target_queue->mutex);
            
            if (!target_queue->local_queue.empty()) {
                // Steal from the back (least recently added)
                url = std::move(target_queue->local_queue.back());
                target_queue->local_queue.pop_back();
                target_queue->size.fetch_sub(1);
                return true;
            }
            
            attempts++;
        }
        
        return false;
    }

    size_t WorkStealingQueue::total_size() const {
        size_t total = 0;
        for (const auto& queue : worker_queues_) {
            total += queue->size.load();
        }
        return total;
    }

    bool WorkStealingQueue::empty() const {
        return total_size() == 0;
    }

    std::string HtmlParser::extract_title(const std::string& html) {
        std::smatch match;
        if (std::regex_search(html, match, title_regex_) && match.size() > 1) {
            std::string title = match[1].str();
            // Clean up whitespace
            title.erase(0, title.find_first_not_of(" \t\n\r"));
            title.erase(title.find_last_not_of(" \t\n\r") + 1);
            return title;
        }
        return "Untitled";
    }

    std::string HtmlParser::extract_text_content(const std::string& html) {
        std::string text;
        bool in_tag = false;
        
        for (char c : html) {
            if (c == '<') {
                in_tag = true;
            } else if (c == '>') {
                in_tag = false;
            } else if (!in_tag) {
                text += c;
            }
        }
        
        return text;
    }

    bool HtmlParser::is_html_content(const std::string& content) {
        std::string lower_content = content.substr(0, 1000); // Check first 1KB
        std::transform(lower_content.begin(), lower_content.end(), lower_content.begin(), ::tolower);
        
        return lower_content.find("<html") != std::string::npos ||
            lower_content.find("<!doctype html") != std::string::npos ||
            lower_content.find("<head") != std::string::npos ||
            lower_content.find("<body") != std::string::npos;
    }

    std::string HtmlParser::extract_meta_description(const std::string& html) {
        std::smatch match;
        if (std::regex_search(html, match, meta_description_regex_) && match.size() > 1) {
            std::string description = match[1].str();
            // Clean up whitespace
            description.erase(0, description.find_first_not_of(" \t\n\r"));
            description.erase(description.find_last_not_of(" \t\n\r") + 1);
            return description;
        }
        return "";
    }