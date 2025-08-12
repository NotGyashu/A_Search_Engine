#pragma once

#include "crawl_metadata.h"
#include "time_utils.h"
#include <string>
#include <chrono>
#include <sstream>
#include <iomanip>
#include <ctime>
#include <vector>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <thread>
#include <atomic>
#include <memory>

/**
 * Enhanced page data structure that includes both content and metadata
 * for Phase 1 persistent storage
 */

namespace CrawlScheduling {

struct EnrichedPageData {
    // Basic page data
    std::string url;
    std::string content;
    std::string domain;
    int depth;
    
    // Phase 1: Crawl scheduling metadata
    std::string content_hash;
    std::chrono::system_clock::time_point last_crawl_time;
    std::chrono::system_clock::time_point previous_change_time;
    std::chrono::system_clock::time_point expected_next_crawl;
    int backoff_multiplier;
    int crawl_count;
    float change_frequency;
    
    // HTTP response metadata
    int http_status_code;
    size_t content_length;
    std::chrono::steady_clock::time_point fetch_start_time;
    
    EnrichedPageData() : depth(0), backoff_multiplier(1), crawl_count(0), 
                         change_frequency(0.0f), http_status_code(0), content_length(0) {
        auto now = std::chrono::system_clock::now();
        last_crawl_time = now;
        previous_change_time = now;
        expected_next_crawl = now;
        fetch_start_time = std::chrono::steady_clock::now();
    }
    
    EnrichedPageData(const std::string& url, const std::string& content, const UrlMetadata* metadata)
        : url(url), content(content), depth(0), backoff_multiplier(1), crawl_count(0),
          change_frequency(0.0f), http_status_code(200), content_length(content.length()) {
        
        fetch_start_time = std::chrono::steady_clock::now();
        
        if (metadata) {
            content_hash = metadata->content_hash;
            last_crawl_time = metadata->last_crawl_time;
            previous_change_time = metadata->previous_change_time;
            expected_next_crawl = metadata->expected_next_crawl;
            backoff_multiplier = metadata->backoff_multiplier;
            crawl_count = metadata->crawl_count;
            change_frequency = metadata->change_frequency;
        } else {
            auto now = std::chrono::system_clock::now();
            last_crawl_time = now;
            previous_change_time = now;
            expected_next_crawl = now;
        }
    }
    
    // Generate JSON representation with metadata
    std::string to_json() const {
        std::ostringstream json;
        json << "  {\n";
        json << "    \"url\": \"" << escape_json_string(url) << "\",\n";
        json << "    \"domain\": \"" << escape_json_string(domain) << "\",\n";
        json << "    \"timestamp\": \"" << TimeUtils::time_to_iso_string(last_crawl_time) << "\",\n";
        json << "    \"depth\": " << depth << ",\n";
        json << "    \"http_status_code\": " << http_status_code << ",\n";
        json << "    \"content_length\": " << content_length << ",\n";
        
        // Phase 1: Crawl scheduling metadata (flattened)
        json << "    \"content_hash\": \"" << content_hash << "\",\n";
        json << "    \"last_crawl_time\": \"" << TimeUtils::time_to_iso_string(last_crawl_time) << "\",\n";
        json << "    \"previous_change_time\": \"" << TimeUtils::time_to_iso_string(previous_change_time) << "\",\n";
        json << "    \"expected_next_crawl\": \"" << TimeUtils::time_to_iso_string(expected_next_crawl) << "\",\n";
        json << "    \"backoff_multiplier\": " << backoff_multiplier << ",\n";
        json << "    \"crawl_count\": " << crawl_count << ",\n";
        json << "    \"change_frequency\": " << change_frequency << ",\n";
        
        json << "    \"content\": \"" << escape_json_string(content) << "\"\n";
        json << "  }";
        
        return json.str();
    }
    
private:
    static std::string escape_json_string(const std::string& input) {
        std::string escaped = input;
        
        // Replace backslashes first to avoid double escaping
        size_t pos = 0;
        while ((pos = escaped.find("\\", pos)) != std::string::npos) {
            escaped.replace(pos, 1, "\\\\");
            pos += 2;
        }
        
        // Replace quotes
        pos = 0;
        while ((pos = escaped.find("\"", pos)) != std::string::npos) {
            escaped.replace(pos, 1, "\\\"");
            pos += 2;
        }
        
        // Replace newlines and other control characters
        pos = 0;
        while ((pos = escaped.find("\n", pos)) != std::string::npos) {
            escaped.replace(pos, 1, "\\n");
            pos += 2;
        }
        
        pos = 0;
        while ((pos = escaped.find("\r", pos)) != std::string::npos) {
            escaped.replace(pos, 1, "\\r");
            pos += 2;
        }
        
        pos = 0;
        while ((pos = escaped.find("\t", pos)) != std::string::npos) {
            escaped.replace(pos, 1, "\\t");
            pos += 2;
        }
        
        return escaped;
    }
};

/**
 * Enhanced File Storage Manager for Phase 1
 * Stores enriched page data with crawl scheduling metadata
 */
class EnhancedFileStorageManager {
private:
    std::string base_path_;
    std::atomic<int> batch_counter_{0};
    
    // Async storage
    struct EnrichedStorageBatch {
        std::vector<EnrichedPageData> data;
        std::string batch_id;
    };
    
    std::queue<EnrichedStorageBatch> storage_queue_;
    std::mutex queue_mutex_;
    std::condition_variable queue_cv_;
    std::condition_variable flush_cv_;  // ✅ Add flush completion signal
    std::thread storage_thread_;
    std::atomic<bool> shutdown_{false};
    std::atomic<bool> flush_requested_{false};  // ✅ Add flush request flag
    
    // Reference to metadata store for enriching data
    std::shared_ptr<CrawlMetadataStore> metadata_store_;
    
    void enhanced_storage_worker();
    bool ensure_directory_exists(const std::string& path);

public:
    explicit EnhancedFileStorageManager(const std::string& base_path, 
                                       std::shared_ptr<CrawlMetadataStore> metadata_store);
    ~EnhancedFileStorageManager();
    
    // Enhanced batch saving with metadata
    void save_enriched_batch(const std::vector<EnrichedPageData>& batch);
    
    // Convert simple page data to enriched data
    void save_html_batch_with_metadata(const std::vector<std::pair<std::string, std::string>>& simple_batch);
    
    // Create enriched page data from basic info
    EnrichedPageData create_enriched_data(const std::string& url, const std::string& content,
                                         int depth = 0,
                                         int http_status = 200);
    
    void flush();
};

} // namespace CrawlScheduling
