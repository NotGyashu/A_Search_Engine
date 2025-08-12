#include "crawler_core.h"
#include "crawler_modes.h"
#include "crawler_monitoring.h"
#include <iostream>
#include <signal.h>
#include <thread>

int main(int argc, char* argv[]) {
    std::cout << "🚀 HYBRID SPEED CRAWLER - Production-Ready Ultimate Performance\n";
    std::cout << "================================================================\n";
    
    // Set up signal handling FIRST
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);

    // Default configuration values
    CrawlerMode mode = CrawlerMode::REGULAR;
    // REFACTORED: Default to more threads for better performance.
    int max_threads = std::min(CrawlerConstants::Workers::DEFAULT_MAX_THREADS, 
                               (int)std::thread::hardware_concurrency());
    int max_depth = CrawlerConstants::Queue::DEFAULT_MAX_DEPTH;
    int max_queue_size = CrawlerConstants::Queue::DEFAULT_MAX_QUEUE_SIZE;
    int max_runtime_minutes = CrawlerConstants::Monitoring::REGULAR_MODE_MAX_RUNTIME_MINUTES; // Default for regular mode

    // --- Command-line argument parsing ---
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--mode" && i + 1 < argc) {
            std::string mode_str = argv[++i];
            if (mode_str == "fresh") {
                mode = CrawlerMode::FRESH;
            } else if (mode_str != "regular") {
                std::cerr << "Warning: Unknown mode '" << mode_str << "'. Defaulting to regular." << std::endl;
            }
        } else if (arg == "FRESH" || arg == "fresh") {
            mode = CrawlerMode::FRESH;
        } else if (arg == "REGULAR" || arg == "regular") {
            mode = CrawlerMode::REGULAR;
        } else if (arg == "--max-runtime" && i + 1 < argc) {
            max_runtime_minutes = std::atoi(argv[++i]);
        } else if (arg.find("--") == 0) {
            continue;
        } else if (i == 1 && mode == CrawlerMode::REGULAR) { 
            max_threads = std::atoi(argv[i]);
        } else if (i == 2) {
            max_depth = std::atoi(argv[i]);
        } else if (i == 3) {
            max_queue_size = std::atoi(argv[i]);
        }
    }

    // --- Configure based on mode ---
    if (mode == CrawlerMode::FRESH) {
        max_runtime_minutes = 0; // Run indefinitely by default in fresh mode
    }

    // Run the appropriate mode
    try {
        if (mode == CrawlerMode::FRESH) {
            run_fresh_mode(max_runtime_minutes);
        } else {
            run_regular_mode(max_threads, max_depth, max_queue_size, max_runtime_minutes);
        }
    } catch (const std::exception& e) {
        std::cerr << "FATAL ERROR: " << e.what() << std::endl;
        return 1;
    }

    std::cout << "🏁 Crawler shutdown complete.\n";
    shutdown_curl_global();
    return 0;
}