#pragma once

#include <array>
#include <memory>
#include <string>
#include <vector>
#include <mutex>
#include <atomic>
#include <fstream>
#include <functional>
#include <filesystem>

/**
 * Sharded Disk Queue Manager - eliminates global mutex contention
 */
class ShardedDiskQueue {
private:
    struct DiskShard {
        std::string file_path;
        std::mutex mutex;
        std::atomic<size_t> size{0};
        std::ofstream write_stream;
        
        DiskShard(const std::string& base_path, int shard_id) 
            : file_path(base_path + "/shard_" + std::to_string(shard_id) + ".txt") {
            // Create directories using C++17 filesystem
            std::error_code ec;
            std::filesystem::create_directories(std::filesystem::path(file_path).parent_path(), ec);
            // Ignore error if directory already exists
        }
    };
    
    static constexpr size_t NUM_SHARDS = 16;
    std::array<std::unique_ptr<DiskShard>, NUM_SHARDS> shards_;
    std::hash<std::string> url_hasher_;
    
    size_t get_shard_index(const std::string& url) const {
        return url_hasher_(url) % NUM_SHARDS;
    }

public:
    ShardedDiskQueue(const std::string& base_path);
    ~ShardedDiskQueue();
    
    bool save_urls_to_disk(const std::vector<std::string>& urls);
    std::vector<std::string> load_urls_from_disk(size_t max_count);
    size_t get_total_disk_queue_size() const;
    void cleanup_empty_shards();
};
