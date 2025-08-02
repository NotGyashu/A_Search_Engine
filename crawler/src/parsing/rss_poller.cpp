#include "rss_poller.h"
// #include "utils.h"  // Commented out - no specific utils needed
#include "config_loader.h"
#include "utility_functions.h"
#include "http_client.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <ctime>
#include <iomanip>
#include <tinyxml2.h>

using namespace tinyxml2;
namespace FeedPolling {

RSSAtomPoller::RSSAtomPoller(std::function<void(const std::vector<FeedEntry>&)> callback, HttpClient* client)
    : url_callback_(std::move(callback)), http_client_(client) {
}

RSSAtomPoller::~RSSAtomPoller() {
    shutdown_ = true;
    if (poller_thread_.joinable()) {
        poller_thread_.join();
    }
}

bool RSSAtomPoller::load_feeds_from_file(const std::string& feeds_file_path) {
    std::ifstream file(feeds_file_path);
    if (!file.is_open()) {
        std::cerr << "Warning: Could not open feeds file: " << feeds_file_path << std::endl;
        return false;
    }
    
    std::lock_guard<std::mutex> lock(feeds_mutex_);
    std::string line;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') continue; // Skip comments and empty lines
        
        // Format: feed_url poll_interval_minutes
        std::istringstream iss(line);
        std::string feed_url;
        int interval = 10; // Default
        
        iss >> feed_url >> interval;
        if (!feed_url.empty()) {
            FeedInfo feed(feed_url);
            feed.poll_interval_minutes = interval;
            feeds_.push_back(feed);
        }
    }
    
    std::cout << "Loaded " << feeds_.size() << " RSS/Atom feeds from " << feeds_file_path << std::endl;
    return true;
}

bool RSSAtomPoller::load_feeds_from_json(const std::string& json_file_path) {
    auto feed_configs = ConfigLoader::load_feed_configs(json_file_path);
    if (feed_configs.empty()) {
        std::cerr << "Warning: No feeds loaded from " << json_file_path << std::endl;
        return false;
    }
    
    std::lock_guard<std::mutex> lock(feeds_mutex_);
    for (const auto& config : feed_configs) {
        FeedInfo feed(config.url);
        feed.poll_interval_minutes = 10; // Default interval
        // Use priority as a hint for polling frequency if needed
        if (config.priority >= 9) {
            feed.poll_interval_minutes = 5;  // High priority: poll every 5 minutes
        } else if (config.priority <= 6) {
            feed.poll_interval_minutes = 30; // Low priority: poll every 30 minutes
        }
        feeds_.push_back(feed);
    }
    
    std::cout << "📡 Loaded " << feeds_.size() << " RSS/Atom feeds from " << json_file_path << std::endl;
    return true;
}

void RSSAtomPoller::add_feed(const std::string& feed_url, int poll_interval_minutes) {
    std::lock_guard<std::mutex> lock(feeds_mutex_);
    FeedInfo feed(feed_url);
    feed.poll_interval_minutes = poll_interval_minutes;
    feeds_.push_back(feed);
    std::cout << "Added RSS/Atom feed: " << feed_url << std::endl;
}

void RSSAtomPoller::start_polling() {
    poller_thread_ = std::thread(&RSSAtomPoller::poller_worker, this);
    std::cout << "RSS/Atom poller started" << std::endl;
}

void RSSAtomPoller::stop() {
    std::cout << "Stopping RSS/Atom poller..." << std::endl;
    shutdown_ = true;
    
    // Notify the worker thread to wake up and check shutdown flag
    {
        std::lock_guard<std::mutex> lock(shutdown_mutex_);
        shutdown_cv_.notify_one();
    }
    
    // Wait for the thread to finish
    if (poller_thread_.joinable()) {
        poller_thread_.join();
    }
    
    std::cout << "RSS/Atom poller stopped gracefully" << std::endl;
}

void RSSAtomPoller::set_poll_interval(int seconds) {
    poll_interval_ = std::chrono::seconds(seconds);
    std::cout << "✅ RSS Poller interval set to " << seconds << " seconds for fresh mode." << std::endl;
}


void RSSAtomPoller::poller_worker() {
    while (!shutdown_) {
        try {
            std::vector<FeedEntry> new_entries;
            
            {
                std::lock_guard<std::mutex> lock(feeds_mutex_);
                for (auto& feed : feeds_) {
                    if (feed.is_ready_for_poll()) {
                        std::cout << "Polling feed: " << feed.feed_url << std::endl;
                        
                        std::string content = download_feed(feed.feed_url);
                        if (!content.empty()) {
                            // Try RSS first, then Atom
                            std::vector<FeedEntry> entries = parse_rss_feed(content);
                            if (entries.empty()) {
                                entries = parse_atom_feed(content);
                            }
                            
                            // Filter for recent entries and count per feed
                            int recent_count_this_feed = 0;
                            int filtered_count_this_feed = 0;
                            for (const auto& entry : entries) {
                                // For fresh mode, use a more lenient time threshold (48 hours instead of 24)
                                bool is_recent = is_recent_entry(entry.pub_date, 48);
                                if (is_recent) {
                                    new_entries.push_back(entry);
                                    recent_count_this_feed++;
                                } else {
                                    filtered_count_this_feed++;
                                }
                            }
                            
                            if (filtered_count_this_feed > 0) {
                                std::cout << "🕒 Filtered out " << filtered_count_this_feed 
                                         << " older entries (>48h)" << std::endl;
                            }
                            
                            feed.record_success();
                            std::cout << "Found " << entries.size() << " entries in feed, " 
                                      << recent_count_this_feed << " are recent" << std::endl;
                        } else {
                            feed.record_failure();
                            std::cout << "Failed to download feed: " << feed.feed_url << std::endl;
                        }
                    }
                }
            }
            
            // Forward new URLs to crawler
            if (!new_entries.empty() && url_callback_) {
                std::cout << "📡 RSS Poller: Forwarding " << new_entries.size() 
                         << " total recent URLs to crawler callback..." << std::endl;
                try {
                    url_callback_(new_entries);
                    std::cout << "✅ RSS Poller: Successfully called callback with " 
                             << new_entries.size() << " URLs" << std::endl;
                } catch (const std::exception& e) {
                    std::cerr << "❌ Error in RSS callback: " << e.what() << std::endl;
                } catch (...) {
                    std::cerr << "❌ Unknown error in RSS callback" << std::endl;
                }
            }
            
            // Sleep for the configured interval, but wake up immediately on shutdown
            std::unique_lock<std::mutex> lock(shutdown_mutex_);
            if (!shutdown_cv_.wait_for(lock, poll_interval_, [this] { return shutdown_.load(); })) {
                // Timeout occurred, continue with next iteration
            }
            // If shutdown flag is set, the loop will exit on next iteration
            
        } catch (const std::exception& e) {
            std::cerr << "Error in RSS poller worker: " << e.what() << std::endl;
            // Short sleep before retry, but allow immediate shutdown
            std::unique_lock<std::mutex> lock(shutdown_mutex_);
            shutdown_cv_.wait_for(lock, std::chrono::seconds(10), [this] { return shutdown_.load(); });
        } catch (...) {
            std::cerr << "Unknown error in RSS poller worker" << std::endl;
            // Short sleep before retry, but allow immediate shutdown
            std::unique_lock<std::mutex> lock(shutdown_mutex_);
            shutdown_cv_.wait_for(lock, std::chrono::seconds(10), [this] { return shutdown_.load(); });
        }
    }
}

std::string RSSAtomPoller::download_feed(const std::string& feed_url) {
    if (!http_client_) {
        std::cerr << "No HTTP client available for feed download: " << feed_url << std::endl;
        return "";
    }
    
    try {
        auto response = http_client_->download_feed(feed_url);
        
        if (!response.success) {
            std::cerr << "Failed to download feed " << feed_url << ": " 
                      << HttpClient::curl_error_string(response.curl_code) << std::endl;
            return "";
        }
        
        if (response.headers.status_code != 200) {
            std::cerr << "HTTP error " << response.headers.status_code 
                      << " downloading feed: " << feed_url << std::endl;
            return "";
        }
        
        // std::cout << "Successfully downloaded feed: " << feed_url 
        //           << " (" << response.body.size() << " bytes)" << std::endl;
        return response.body;
        
    } catch (const std::exception& e) {
        std::cerr << "Exception downloading feed " << feed_url << ": " << e.what() << std::endl;
        return "";
    }
}

std::vector<FeedEntry> RSSAtomPoller::parse_rss_feed(const std::string& feed_content) {
    std::vector<FeedEntry> entries;
    XMLDocument doc;
    
    if (doc.Parse(feed_content.c_str())) {
        return entries; // Return empty if parse fails
    }
    
    XMLElement* rss = doc.FirstChildElement("rss");
    if (!rss) return entries;
    
    XMLElement* channel = rss->FirstChildElement("channel");
    if (!channel) return entries;
    
    for (XMLElement* item = channel->FirstChildElement("item"); item; item = item->NextSiblingElement("item")) {
        FeedEntry entry;
        
        if (XMLElement* link = item->FirstChildElement("link")) {
            entry.url = link->GetText() ? link->GetText() : "";
        }
        
        if (XMLElement* title = item->FirstChildElement("title")) {
            entry.title = title->GetText() ? title->GetText() : "";
        }
        
        if (XMLElement* desc = item->FirstChildElement("description")) {
            entry.description = desc->GetText() ? desc->GetText() : "";
        }
        
        // Try to parse pubDate if available
        if (XMLElement* pubDate = item->FirstChildElement("pubDate")) {
            if (pubDate->GetText()) {
                // Use helper function to parse RFC 2822 date
                entry.pub_date = parse_rfc2822_date(pubDate->GetText());
            }
        }
        
        // Fallback to current time if no valid date
        if (entry.pub_date == std::chrono::system_clock::time_point{}) {
            entry.pub_date = std::chrono::system_clock::now();
        }
        
        if (!entry.url.empty()) {
            entries.push_back(entry);
        }
    }
    
    return entries;
}

std::vector<FeedEntry> RSSAtomPoller::parse_atom_feed(const std::string& feed_content) {
    std::vector<FeedEntry> entries;
    XMLDocument doc;
    
    if (doc.Parse(feed_content.c_str())) {
        return entries; // Return empty if parse fails
    }
    
    XMLElement* feed = doc.FirstChildElement("feed");
    if (!feed) return entries;
    
    for (XMLElement* entry = feed->FirstChildElement("entry"); entry; entry = entry->NextSiblingElement("entry")) {
        FeedEntry feed_entry;
        
        // Find primary link
        for (XMLElement* link = entry->FirstChildElement("link"); link; link = link->NextSiblingElement("link")) {
            const char* rel = link->Attribute("rel");
            if (!rel || strcmp(rel, "alternate") == 0) {
                const char* href = link->Attribute("href");
                if (href) {
                    feed_entry.url = href;
                    break;
                }
            }
        }
        
        if (XMLElement* title = entry->FirstChildElement("title")) {
            feed_entry.title = title->GetText() ? title->GetText() : "";
        }
        
        // Try summary first, then content
        if (XMLElement* summary = entry->FirstChildElement("summary")) {
            feed_entry.description = summary->GetText() ? summary->GetText() : "";
        } 
        else if (XMLElement* content = entry->FirstChildElement("content")) {
            feed_entry.description = content->GetText() ? content->GetText() : "";
        }
        
        // Try updated first, then published
        if (XMLElement* updated = entry->FirstChildElement("updated")) {
            if (updated->GetText()) {
                feed_entry.pub_date = parse_iso8601_date(updated->GetText());
            }
        } 
        else if (XMLElement* published = entry->FirstChildElement("published")) {
            if (published->GetText()) {
                feed_entry.pub_date = parse_iso8601_date(published->GetText());
            }
        }
        
        // Fallback to current time if no valid date
        if (feed_entry.pub_date == std::chrono::system_clock::time_point{}) {
            feed_entry.pub_date = std::chrono::system_clock::now();
        }
        
        if (!feed_entry.url.empty()) {
            entries.push_back(feed_entry);
        }
    }
    
    return entries;
}
bool RSSAtomPoller::is_recent_entry(const std::chrono::system_clock::time_point& pub_date, int hours_threshold) {
    auto now = std::chrono::system_clock::now();
    auto threshold = now - std::chrono::hours(hours_threshold);
    return pub_date >= threshold;
}

size_t RSSAtomPoller::get_active_feeds_count() const {
    std::lock_guard<std::mutex> lock(const_cast<std::mutex&>(feeds_mutex_));
    return std::count_if(feeds_.begin(), feeds_.end(), 
                        [](const FeedInfo& feed) { return feed.enabled; });
}

void RSSAtomPoller::print_feed_stats() const {
    std::lock_guard<std::mutex> lock(const_cast<std::mutex&>(feeds_mutex_));
    std::cout << "\n=== RSS/Atom Feed Statistics ===" << std::endl;
    std::cout << "Total feeds: " << feeds_.size() << std::endl;
    std::cout << "Active feeds: " << get_active_feeds_count() << std::endl;
    
    for (const auto& feed : feeds_) {
        std::cout << "Feed: " << feed.feed_url 
                  << " | Interval: " << feed.poll_interval_minutes << "min"
                  << " | Failures: " << feed.consecutive_failures
                  << " | Enabled: " << (feed.enabled ? "Yes" : "No") << std::endl;
    }
    std::cout << "================================\n" << std::endl;
}

} // namespace FeedPolling
