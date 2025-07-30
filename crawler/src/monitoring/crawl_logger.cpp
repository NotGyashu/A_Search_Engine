#include "crawl_logger.h"
#include <iostream>
#include <filesystem>

CrawlLogger::CrawlLogger(const std::string& db_path, const std::string& csv_path) 
    : db_(nullptr), db_path_(db_path), csv_path_(csv_path) {
    
    if (!initialize()) {
        // If initialization fails, we cannot log, so this is a critical error.
        throw std::runtime_error("Failed to initialize CrawlLogger. Check file paths and permissions for '" + db_path + "' and '" + csv_path + "'.");
    }
    
    // Start logger thread only after successful initialization
    logger_thread_ = std::thread(&CrawlLogger::logger_worker, this);
}

CrawlLogger::~CrawlLogger() {
    shutdown_.store(true);
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
    // Create directories if they don't exist
    try {
        std::filesystem::create_directories(std::filesystem::path(db_path_).parent_path());
        std::filesystem::create_directories(std::filesystem::path(csv_path_).parent_path());
    } catch (const std::filesystem::filesystem_error& e) {
        std::cerr << "Error creating logger directories: " << e.what() << std::endl;
        return false;
    }

    // Initialize SQLite database
    if (sqlite3_open(db_path_.c_str(), &db_) != SQLITE_OK) {
        std::cerr << "Cannot open database: " << sqlite3_errmsg(db_) << std::endl;
        return false;
    }
    
    // Create table if it doesn't exist
    const char* sql = R"(
        CREATE TABLE IF NOT EXISTS crawl_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            title TEXT,
            status_code INTEGER,
            depth INTEGER,
            domain TEXT,
            content_size INTEGER,
            timestamp INTEGER,
            error_message TEXT
        );
    )";
    
    char* err_msg = nullptr;
    if (sqlite3_exec(db_, sql, nullptr, nullptr, &err_msg) != SQLITE_OK) {
        std::cerr << "SQL error creating table: " << err_msg << std::endl;
        sqlite3_free(err_msg);
        return false;
    }
    
    // Open CSV file
    csv_log_.open(csv_path_, std::ios::app);
    if (!csv_log_.is_open()) {
        std::cerr << "Cannot open CSV log file: " << csv_path_ << std::endl;
        return false;
    }
    
    // Write CSV header if file is empty
    csv_log_.seekp(0, std::ios::end);
    if (csv_log_.tellp() == 0) {
        csv_log_ << "timestamp,url,title,status_code,depth,domain,content_size,error_message\n";
    }
    
    return true;
}

void CrawlLogger::log_page(const std::string& url, const std::string& title, int status_code, 
                          int depth, const std::string& domain, size_t content_size,
                          const std::chrono::steady_clock::time_point& timestamp) {
    LogEntry entry;
    entry.url = url;
    entry.title = title;
    entry.status_code = status_code;
    entry.depth = depth;
    entry.domain = domain;
    entry.content_size = content_size;
    entry.timestamp = timestamp;
    entry.is_error = false;
    
    {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        log_queue_.push(std::move(entry));
    }
    queue_cv_.notify_one();
}

void CrawlLogger::log_error(const std::string& url, const std::string& error_message) {
    LogEntry entry;
    entry.url = url;
    entry.error_message = error_message;
    entry.timestamp = std::chrono::steady_clock::now();
    entry.is_error = true;
    
    {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        log_queue_.push(std::move(entry));
    }
    queue_cv_.notify_one();
}

void CrawlLogger::flush() {
    // This function ensures any buffered data is written to the file.
    std::lock_guard<std::mutex> csv_lock(csv_mutex_);
    if (csv_log_.is_open()) {
        csv_log_.flush();
    }
}

void CrawlLogger::logger_worker() {
    while (!shutdown_.load()) {
        std::unique_lock<std::mutex> lock(queue_mutex_);
        queue_cv_.wait(lock, [this] { return !log_queue_.empty() || shutdown_.load(); });
        
        while (!log_queue_.empty()) {
            LogEntry entry = std::move(log_queue_.front());
            log_queue_.pop();
            lock.unlock(); // Release lock while writing to disk
            
            // Get current time for logging
            auto now_sys = std::chrono::system_clock::now();
            auto time_t = std::chrono::system_clock::to_time_t(now_sys);

            // Process the log entry
            if (entry.is_error) {
                std::lock_guard<std::mutex> csv_lock(csv_mutex_);
                if (csv_log_.is_open()) {
                    csv_log_ << time_t << ",\"" << entry.url << "\",ERROR,0,0,," << ",\"" << entry.error_message << "\"\n";
                }
            } else {
                // Log page to CSV
                {
                    std::lock_guard<std::mutex> csv_lock(csv_mutex_);
                    if (csv_log_.is_open()) {
                        csv_log_ << time_t << ",\"" << entry.url << "\",\"" << entry.title << "\"," 
                                 << entry.status_code << "," << entry.depth << ",\"" << entry.domain 
                                 << "\"," << entry.content_size << ",\n";
                    }
                }
                // Log page to database
                {
                    std::lock_guard<std::mutex> db_lock(db_mutex_);
                    const char* sql = "INSERT OR IGNORE INTO crawl_log (url, title, status_code, depth, domain, content_size, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?);";
                    sqlite3_stmt* stmt;
                    if (sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr) == SQLITE_OK) {
                        sqlite3_bind_text(stmt, 1, entry.url.c_str(), -1, SQLITE_STATIC);
                        sqlite3_bind_text(stmt, 2, entry.title.c_str(), -1, SQLITE_STATIC);
                        sqlite3_bind_int(stmt, 3, entry.status_code);
                        sqlite3_bind_int(stmt, 4, entry.depth);
                        sqlite3_bind_text(stmt, 5, entry.domain.c_str(), -1, SQLITE_STATIC);
                        sqlite3_bind_int64(stmt, 6, entry.content_size);
                        sqlite3_bind_int64(stmt, 7, time_t);
                        sqlite3_step(stmt);
                        sqlite3_finalize(stmt);
                    }
                }
            }
            
            lock.lock(); // Re-acquire lock for the loop condition
        }
    }
}
