#pragma once

#include "crawler_core.h"

/**
 * Enhanced monitoring thread for continuous queue & speed logging
 */
void enhanced_monitoring_thread(CrawlerMode mode);

/**
 * Emergency seed injector class for handling low queue situations
 */
class EmergencySeedInjector {
private:
    static std::vector<std::string> get_emergency_seeds();
    
public:
    static bool inject_emergency_seeds(int& injection_count, 
                                       const int max_injections = CrawlerConstants::ErrorHandling::MAX_EMERGENCY_INJECTIONS);
};

/**
 * Signal handler for graceful shutdown
 */
void signal_handler(int signal);
