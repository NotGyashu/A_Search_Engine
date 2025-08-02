#include "crawler_monitoring.h"
#include "crawler_core.h"
#include <iostream>
#include <iomanip>
#include <chrono>
#include <thread>
#include <fstream>
#include <sstream>
#include <signal.h>
#include "tracy/Tracy.hpp"

/**
 * 📊 ENHANCED MONITORING THREAD with Always-On Queue & Speed Logging
 */
void enhanced_monitoring_thread(CrawlerMode mode) {
    std::cout << "📊 Starting continuous queue & speed monitoring...\n";
    auto last_stats = std::chrono::steady_clock::now();
    auto last_cleanup = std::chrono::steady_clock::now();
    auto monitoring_start = std::chrono::steady_clock::now();
    
    static int emergency_injection_count = 0;
    static int low_queue_warnings = 0;
    
    // FRESH mode grace period - wait for RSS poller to complete first cycle
    const int FRESH_MODE_GRACE_PERIOD_SECONDS = (mode == CrawlerMode::FRESH) ? 60 : 0;
    bool grace_period_active = (mode == CrawlerMode::FRESH);
    
    if (grace_period_active) {
        std::cout << "🕐 FRESH mode: Grace period of " << FRESH_MODE_GRACE_PERIOD_SECONDS 
                 << " seconds for RSS poller to populate queues..." << std::endl;
    }
    
    // Initial queue status - log immediately at startup
    size_t initial_smart_size = smart_url_frontier->size();
    size_t initial_disk_queue_size = (mode == CrawlerMode::REGULAR && sharded_disk_queue) ? sharded_disk_queue->get_total_disk_queue_size() : 0;
    size_t initial_work_stealing_size = work_stealing_queue->total_size();
    std::cout << "🔍 STARTUP QUEUE STATUS:\n";
    std::cout << "   Smart Queue: " << initial_smart_size << " URLs\n";
    if (mode == CrawlerMode::REGULAR) {
        std::cout << "   Sharded Disk Queue: " << initial_disk_queue_size << " URLs\n";
    } else {
        std::cout << "   Disk Queue: DISABLED (FRESH mode)\n"; 
    }
    std::cout << "   Work Stealing Queue: " << initial_work_stealing_size << " URLs\n";
    std::cout << "   HTML Processing Queue: " << html_processing_queue->size() << " tasks\n";
    std::cout << "   Total Available: " << (initial_smart_size + initial_disk_queue_size + initial_work_stealing_size) << " URLs\n\n";
    
    while (!stop_flag) {
        std::this_thread::sleep_for(std::chrono::seconds(CrawlerConstants::Monitoring::QUEUE_CHECK_INTERVAL_SECONDS));
        
        auto now = std::chrono::steady_clock::now();
        auto elapsed_seconds = std::chrono::duration_cast<std::chrono::seconds>(now - monitoring_start).count();

        // If a pointer is null during shutdown, we treat its size as 0.
        // This prevents the race condition and the subsequent crash.
        if (!smart_url_frontier || !work_stealing_queue || !html_processing_queue) {
            // One of the core components has been destroyed, so we should exit.
            break;
        }
        
        // Check if disk queue is available (not used in FRESH mode)
        bool has_disk_queue = (mode == CrawlerMode::REGULAR && sharded_disk_queue != nullptr);

        size_t smart_queue_size = smart_url_frontier->size();
        size_t disk_queue_size = has_disk_queue ? sharded_disk_queue->get_total_disk_queue_size() : 0;
        size_t work_stealing_size = work_stealing_queue->total_size();
        size_t html_queue_size = html_processing_queue->size();
        
        // Calculate current crawl rate
        double current_rate = global_monitor.get_crawl_rate();
        size_t total_processed = global_monitor.get_total_pages();
        
        // ALWAYS LOG QUEUE STATUS & SPEED (every 5 seconds) - Mode aware logging
        if (mode == CrawlerMode::FRESH) {
            std::cout << "[" << std::setw(4) << elapsed_seconds << "s] FRESH | "
                     << "Smart: " << std::setw(4) << smart_queue_size
                     << " | Work: " << std::setw(3) << work_stealing_size
                     << " | HTML: " << std::setw(3) << html_queue_size
                     << " | Speed: " << std::fixed << std::setprecision(1) << std::setw(6) << current_rate << " p/s"
                     << " | Total: " << std::setw(6) << total_processed << "\n";
        } else {
            std::cout << "[" << std::setw(4) << elapsed_seconds << "s] "
                     << "Smart: " << std::setw(4) << smart_queue_size
                     << " | Disk: " << std::setw(4) << disk_queue_size
                     << " | Work: " << std::setw(3) << work_stealing_size
                     << " | HTML: " << std::setw(3) << html_queue_size
                     << " | Speed: " << std::fixed << std::setprecision(1) << std::setw(6) << current_rate << " p/s"
                     << " | Total: " << std::setw(6) << total_processed << "\n";
        }
        
        // Print detailed statistics every configured interval
        if (std::chrono::duration_cast<std::chrono::seconds>(now - last_stats).count() >= 
            CrawlerConstants::Monitoring::DETAILED_STATS_INTERVAL_SECONDS) {
            std::cout << "\n📊 DETAILED STATS (15s interval):\n";
            global_monitor.print_stats(smart_queue_size, 0);
            
            // Performance indicators with more granular feedback
            if (current_rate >= CrawlerConstants::Performance::TARGET_PAGES_PER_SECOND) {
                std::cout << "🚀 TARGET ACHIEVED: " << std::fixed << std::setprecision(1) 
                         << current_rate << " pages/sec\n";
            } else if (current_rate >= CrawlerConstants::Performance::HIGH_PERFORMANCE_THRESHOLD) {
                std::cout << "⚡ High Performance: " << std::fixed << std::setprecision(1) 
                         << current_rate << " pages/sec\n";
            } else if (current_rate >= CrawlerConstants::Performance::GOOD_PERFORMANCE_THRESHOLD) {
                std::cout << "🔥 Good Performance: " << std::fixed << std::setprecision(1) 
                         << current_rate << " pages/sec\n";
            } else if (current_rate >= CrawlerConstants::Performance::MODERATE_PERFORMANCE_THRESHOLD) {
                std::cout << "⚠️ Moderate Performance: " << std::fixed << std::setprecision(1) 
                         << current_rate << " pages/sec\n";
            } else if (current_rate >= CrawlerConstants::Performance::LOW_PERFORMANCE_THRESHOLD) {
                std::cout << "🐌 Low Performance: " << std::fixed << std::setprecision(1) 
                         << current_rate << " pages/sec\n";
            } else {
                std::cout << "🔴 Very Low Performance: " << std::fixed << std::setprecision(1) 
                         << current_rate << " pages/sec\n";
            }
            
            std::cout << "\n";
            std::cout.flush();
            last_stats = now;
        }
        
        // 🔄 PHASE 2: ENHANCED QUEUE MANAGEMENT with sharded disk and work stealing
        // Skip disk operations in FRESH mode
        if (mode == CrawlerMode::REGULAR && has_disk_queue) {
            // 1. Refill from sharded disk when smart queue gets low
            if (smart_queue_size < CrawlerConstants::Queue::REFILL_THRESHOLD && disk_queue_size > 0) {
                auto loaded_urls = sharded_disk_queue->load_urls_from_disk(CrawlerConstants::Queue::REFILL_THRESHOLD);
                int refilled = 0;
                
                for (const auto& url : loaded_urls) {
                    float priority = CrawlerConstants::Priority::DISK_URL_PRIORITY;
                    UrlInfo url_info(url, priority, 0);
                    if (smart_url_frontier->enqueue(url_info)) {
                        refilled++;
                    }
                }
                
                if (refilled > 0) {
                    std::cout << "✅ Loaded " << refilled << " URLs from sharded disk (Smart queue was " << smart_queue_size << ")\n";
                }
            }
            
            // 2. Periodic cleanup of empty disk shards and aggressive disk queue management
            if (elapsed_seconds % CrawlerConstants::Monitoring::CLEANUP_INTERVAL_SECONDS == 0) { // Every minute
                sharded_disk_queue->cleanup_empty_shards();
            }
        } else if (mode == CrawlerMode::FRESH) {
            // In FRESH mode, only rely on RSS/Atom feeds - no disk queue management
            if (smart_queue_size < 10) {
                std::cout << "ℹ️ FRESH mode: Low queue size (" << smart_queue_size << "), relying on RSS feeds\n";
            }
        }
        
        // 🗃️ AGGRESSIVE DISK QUEUE USAGE - Only in REGULAR mode
        if (mode == CrawlerMode::REGULAR && has_disk_queue) {
            size_t smart_queue_capacity = 1000; // Assuming max queue size set to 1000
            size_t work_stealing_capacity = work_stealing_queue->get_max_size();
            
            // Calculate memory usage percentages
            double smart_usage = static_cast<double>(smart_queue_size) / smart_queue_capacity;
            double work_usage = static_cast<double>(work_stealing_size) / work_stealing_capacity;
            
            // If memory queues are more than 80% full, aggressively move URLs to disk
            if (smart_usage > 0.8 || work_usage > 0.8) {
                std::vector<std::string> overflow_urls;
                
                // Try to extract URLs from work-stealing queue when it's getting full
                if (work_usage > 0.8) {
                    for (size_t worker_id = 0; worker_id < 8 && overflow_urls.size() < 200; ++worker_id) {
                        UrlInfo url_info("", 0.0f);
                        if (work_stealing_queue->pop_local(worker_id, url_info)) {
                            overflow_urls.push_back(url_info.url);
                        }
                    }
                }
                
                if (!overflow_urls.empty()) {
                    sharded_disk_queue->save_urls_to_disk(overflow_urls);
                    std::cout << "💾 AGGRESSIVE: Moved " << overflow_urls.size() 
                             << " URLs to disk (Smart: " << std::fixed << std::setprecision(1) << (smart_usage * 100) 
                             << "%, Work: " << (work_usage * 100) << "% full)\n";
                }
            }
        }
        
        // 2. Emergency seed injection when critically low - more aggressive (REGULAR mode only)
        if (mode == CrawlerMode::REGULAR){
            if(smart_queue_size < CrawlerConstants::Queue::LOW_QUEUE_THRESHOLD && 
            current_rate < CrawlerConstants::Performance::SHUTDOWN_RATE_THRESHOLD) {
            low_queue_warnings++;
            
            if (low_queue_warnings >= CrawlerConstants::ErrorHandling::LOW_QUEUE_WARNING_THRESHOLD) {
                if (EmergencySeedInjector::inject_emergency_seeds(emergency_injection_count)) {
                    low_queue_warnings = 0; // Reset warnings after injection
                }
            }
        } else {
            low_queue_warnings = 0; // Reset warnings when queue recovers
        }
        
        // 3. Auto-shutdown conditions - Phase 1 & 2 enhanced
        size_t total_urls_available = smart_queue_size + disk_queue_size + work_stealing_size;
        
        // Check if grace period is still active (FRESH mode only)
        if (grace_period_active) {
            auto grace_elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - monitoring_start).count();
            if (grace_elapsed >= FRESH_MODE_GRACE_PERIOD_SECONDS) {
                grace_period_active = false;
                std::cout << "✅ FRESH mode: Grace period completed. Normal monitoring active." << std::endl;
            } else {
                // During grace period, just report status but don't trigger shutdown
                if (total_urls_available == 0) {
                    std::cout << "⏳ FRESH mode grace period: " << (FRESH_MODE_GRACE_PERIOD_SECONDS - grace_elapsed) 
                             << "s remaining for RSS feeds to populate queues..." << std::endl;
                }
                continue; // Skip shutdown checks during grace period
            }
        }
        
        if (total_urls_available < CrawlerConstants::Queue::CRITICAL_QUEUE_THRESHOLD && 
            current_rate < CrawlerConstants::Performance::VERY_LOW_PERFORMANCE_THRESHOLD) {
            static int shutdown_warnings = 0;
            shutdown_warnings++;
            
            std::cout << "🛑 Shutdown condition detected: Total URLs=" << total_urls_available
                     << " (Smart=" << smart_queue_size << ", Disk=" << disk_queue_size 
                     << ", Work=" << work_stealing_size << "), Rate=" << current_rate 
                     << " (warning #" << shutdown_warnings << "/" 
                     << CrawlerConstants::ErrorHandling::SHUTDOWN_WARNING_THRESHOLD << ")\n";
            
            if (shutdown_warnings >= CrawlerConstants::ErrorHandling::SHUTDOWN_WARNING_THRESHOLD) {
                std::cout << "🏁 Triggering graceful shutdown - no more URLs to crawl\n";
                stop_flag = true;
            }
        }
    }
        
        // Safety timeout (configurable)
        auto total_elapsed = std::chrono::duration_cast<std::chrono::minutes>(now - last_cleanup).count();
        if (total_elapsed >= CrawlerConstants::Monitoring::SAFETY_TIMEOUT_MINUTES) {
            std::cout << "⏰ Safety timeout reached (" << CrawlerConstants::Monitoring::SAFETY_TIMEOUT_MINUTES 
                     << " minutes). Shutting down...\n";
            stop_flag = true;
        }
    }
}

/**
 * 🚨 EMERGENCY SEED INJECTOR
 * Provides high-quality URLs when crawl queue gets too low
 */
std::vector<std::string> EmergencySeedInjector::get_emergency_seeds() {
    // ✅ EMERGENCY SEEDS — Load from JSON configuration instead of hardcoded
    try {
        std::string config_path = std::string(CrawlerConstants::Paths::CONFIG_PATH) + "/emergency_seeds.json";
        std::ifstream file(config_path);
        if (!file.is_open()) {
            std::cerr << "⚠️  Warning: Could not open emergency seeds config: " << config_path << "\n";
            return {}; // Return empty vector if config can't be loaded
        }
        
        std::string json_content((std::istreambuf_iterator<char>(file)),
                               std::istreambuf_iterator<char>());
        file.close();
        
        // Simple JSON parsing for emergency_seeds array
        std::vector<std::string> seeds;
        size_t start = json_content.find("\"emergency_seeds\"");
        if (start == std::string::npos) {
            std::cerr << "⚠️  Warning: 'emergency_seeds' field not found in config\n";
            return {};
        }
        
        start = json_content.find("[", start);
        size_t end = json_content.find("]", start);
        if (start == std::string::npos || end == std::string::npos) {
            std::cerr << "⚠️  Warning: Invalid JSON format in emergency seeds config\n";
            return {};
        }
        
        std::string urls_section = json_content.substr(start + 1, end - start - 1);
        std::istringstream iss(urls_section);
        std::string line;
        
        while (std::getline(iss, line, ',')) {
            // Extract URL from JSON string format "url"
            size_t first_quote = line.find('"');
            size_t last_quote = line.rfind('"');
            if (first_quote != std::string::npos && last_quote != std::string::npos && first_quote != last_quote) {
                std::string url = line.substr(first_quote + 1, last_quote - first_quote - 1);
                if (!url.empty() && url.find("http") == 0) {
                    seeds.push_back(url);
                }
            }
        }
        
        return seeds;
        
    } catch (const std::exception& e) {
        std::cerr << "⚠️  Warning: Error loading emergency seeds: " << e.what() << "\n";
        return {}; // Return empty vector on error
    }
}

bool EmergencySeedInjector::inject_emergency_seeds(int& injection_count, const int max_injections) {
    if (injection_count >= max_injections) {
        return false;
    }
    
    auto seeds = get_emergency_seeds();
    int injected = 0;
    
    for (const auto& seed : seeds) {
        float priority = CrawlerConstants::Priority::EMERGENCY_SEED_PRIORITY; // Very high priority for emergency seeds
        UrlInfo seed_info(seed, priority, 0);
        if (smart_url_frontier->enqueue(seed_info)) {
            injected++;
        }
    }
    
    injection_count++;
    std::cout << "🚨 Emergency injection #" << injection_count << ": Added " 
             << injected << "/" << seeds.size() << " emergency seeds\n";
    
    return true;
}

void signal_handler(int signal) {
    static std::atomic<int> shutdown_count{0};
    int count = shutdown_count.fetch_add(1);
    
    if (count == 0) {
        std::cout << "\nReceived shutdown signal (" << signal << "). Gracefully shutting down hybrid crawler...\n";
        stop_flag = true;
        
        // Give threads a chance to shut down gracefully
        std::thread([]{
            std::this_thread::sleep_for(std::chrono::seconds(5));
            if (stop_flag) {
                std::cout << "Forcing shutdown after 5 seconds...\n";
                std::quick_exit(0);
            }
        }).detach();
    } else if (count == 1) {
        std::cout << "\nSecond shutdown signal received. Force shutdown in 2 seconds...\n";
        std::thread([]{
            std::this_thread::sleep_for(std::chrono::seconds(2));
            std::cout << "Force shutdown now!\n";
            std::quick_exit(1);
        }).detach();
    } else {
        std::cout << "\nImmediate shutdown!\n";
        std::quick_exit(2);
    }
}
