#pragma once

#include <string>
#include <chrono>
#include <fstream>
#include <mutex>
#include <queue>
#include <condition_variable>
#include <thread>
#include <atomic>
#include <sqlite3.h>

// Asynchronous batch logger to reduce blocking
class CrawlLogger {
private:
    struct LogEntry {
        std::string url;
        std::string title;
        int status_code;
        int depth;
        std::string domain;
        size_t content_size;
        std::chrono::steady_clock::time_point timestamp;
        std::string error_message;
        bool is_error;
    };
    
    sqlite3* db_;
    std::mutex db_mutex_;
    std::ofstream csv_log_;
    std::mutex csv_mutex_;
    std::string db_path_;
    std::string csv_path_;
    
    // Async logging
    std::queue<LogEntry> log_queue_;
    std::mutex queue_mutex_;
    std::condition_variable queue_cv_;
    std::thread logger_thread_;
    std::atomic<bool> shutdown_{false};
    
    void logger_worker();

public:
    CrawlLogger(const std::string& db_path, const std::string& csv_path);
    ~CrawlLogger();
    
    void log_page(const std::string& url, const std::string& title, int status_code, 
                  int depth, const std::string& domain, size_t content_size,
                  const std::chrono::steady_clock::time_point& timestamp);
    void log_error(const std::string& url, const std::string& error_message);
    void flush();
    bool initialize();
};
