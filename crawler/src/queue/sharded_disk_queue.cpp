#include "sharded_disk_queue.h"
#include <fstream>
#include <iostream>

ShardedDiskQueue::ShardedDiskQueue(const std::string& base_path) {
    // Initialize shards
    for (size_t i = 0; i < NUM_SHARDS; ++i) {
        shards_[i] = std::make_unique<DiskShard>(base_path, static_cast<int>(i));
    }
}

ShardedDiskQueue::~ShardedDiskQueue() {
    // Cleanup - close all write streams
    for (auto& shard : shards_) {
        if (shard && shard->write_stream.is_open()) {
            shard->write_stream.close();
        }
    }
}

bool ShardedDiskQueue::save_urls_to_disk(const std::vector<std::string>& urls) {
    if (urls.empty()) return true;
    
    // Distribute URLs across shards
    std::vector<std::vector<std::string>> shard_urls(NUM_SHARDS);
    
    for (const auto& url : urls) {
        size_t shard_index = get_shard_index(url);
        shard_urls[shard_index].push_back(url);
    }
    
    // Write to each shard
    bool success = true;
    for (size_t i = 0; i < NUM_SHARDS; ++i) {
        if (!shard_urls[i].empty()) {
            auto& shard = shards_[i];
            std::lock_guard<std::mutex> lock(shard->mutex);
            
            if (!shard->write_stream.is_open()) {
                shard->write_stream.open(shard->file_path, std::ios::app);
            }
            
            if (shard->write_stream.is_open()) {
                for (const auto& url : shard_urls[i]) {
                    shard->write_stream << url << "\n";
                    shard->size.fetch_add(1);
                }
                shard->write_stream.flush();
            } else {
                success = false;
            }
        }
    }
    
    return success;
}

std::vector<std::string> ShardedDiskQueue::load_urls_from_disk(size_t max_count) {
    std::vector<std::string> urls;
    urls.reserve(max_count);
    
    size_t loaded = 0;
    for (size_t i = 0; i < NUM_SHARDS && loaded < max_count; ++i) {
        auto& shard = shards_[i];
        std::lock_guard<std::mutex> lock(shard->mutex);
        
        std::ifstream file(shard->file_path);
        if (file.is_open()) {
            std::string url;
            while (loaded < max_count && std::getline(file, url)) {
                if (!url.empty()) {
                    urls.push_back(url);
                    loaded++;
                }
            }
            file.close();
            
            // Clear the file after reading
            if (loaded > 0) {
                std::ofstream clear_file(shard->file_path, std::ios::trunc);
                clear_file.close();
                shard->size.store(0);
            }
        }
    }
    
    return urls;
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
        std::lock_guard<std::mutex> lock(shard->mutex);
        
        if (shard->size.load() == 0) {
            if (shard->write_stream.is_open()) {
                shard->write_stream.close();
            }
            
            // Remove empty file
            std::error_code ec;
            std::filesystem::remove(shard->file_path, ec);
        }
    }
}
