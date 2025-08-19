cmake_minimum_required(VERSION 3.10)
project(mini_search_engine_crawler)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_compile_options(-Wno-stringop-overflow)
include_directories(${CMAKE_SOURCE_DIR}/include)
include_directories(${CMAKE_SOURCE_DIR}/third_party/tracy/public)
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0 -rdynamic")
set(CMAKE_C_FLAGS_DEBUG "-g -O0 -rdynamic")

# Aggressive optimization flags for maximum performance (Phase 1 Ultra)
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -march=native -mtune=native -DNDEBUG -funroll-loops -ffast-math")
set(CMAKE_C_FLAGS_RELEASE "-O3 -march=native -mtune=native -DNDEBUG")

# Ultra-performance specific flags for Phase 1
set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -mavx2 -mfma")
set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -fno-stack-protector")

# Link-time optimization
set(CMAKE_EXE_LINKER_FLAGS_RELEASE "-Wl,--gc-sections")

# Debug flags
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0 -DDEBUG -fsanitize=address -mavx2 -mfma")

# --- MODIFICATION START: Cross-platform dependency resolution ---

# Dependencies
find_package(CURL REQUIRED)
find_package(PkgConfig REQUIRED)

# --- Find RocksDB in a cross-platform way ---
# Give precedence to a user-defined environment variable as an override
IF(DEFINED ENV{ROCKSDB_ROOT})
    LIST(APPEND CMAKE_PREFIX_PATH "$ENV{ROCKSDB_ROOT}")
ENDIF()

# Add platform-specific hints for standard installation locations
IF(UNIX AND NOT APPLE) # For Linux systems (including WSL)
    # Standard path for librocksdb-dev on Ubuntu/Debian
    IF(EXISTS "/usr/lib/x86_64-linux-gnu/cmake/RocksDB")
        LIST(APPEND CMAKE_PREFIX_PATH "/usr/lib/x86_64-linux-gnu/cmake/RocksDB")
    ENDIF()
ELSEIF(APPLE) # For macOS systems
    # Standard paths for RocksDB installed via Homebrew
    IF(EXISTS "/opt/homebrew/opt/rocksdb/lib/cmake/rocksdb")
        LIST(APPEND CMAKE_PREFIX_PATH "/opt/homebrew/opt/rocksdb/lib/cmake/rocksdb")
    ENDIF()
    IF(EXISTS "/usr/local/opt/rocksdb/lib/cmake/rocksdb")
        LIST(APPEND CMAKE_PREFIX_PATH "/usr/local/opt/rocksdb/lib/cmake/rocksdb")
    ENDIF()
ENDIF()

# Now, find the package using the hints we've provided
find_package(RocksDB REQUIRED)
# --- MODIFICATION END ---

pkg_check_modules(RE2 REQUIRED re2)

# Load submodule include helper
include(${CMAKE_SOURCE_DIR}/cmake/IncludeGitSubmodule.cmake)

# TinyXML2 dependency for XML parsing
pkg_check_modules(TINYXML2 REQUIRED tinyxml2)

# Include additional Git submodules (header-only)
# This will make the 'concurrentqueue' target available
include_git_submodule(third_party/concurrentqueue)

# Compiler warnings
add_compile_options(-Wall -Wextra -Wpedantic -Wno-unused-parameter)

# Thread safety
add_compile_options(-pthread)

# Set output directory for executables to crawler build directory
if(CMAKE_RUNTIME_OUTPUT_DIRECTORY)
    set(OUTPUT_DIR ${CMAKE_RUNTIME_OUTPUT_DIRECTORY})
else()
    set(OUTPUT_DIR ${PROJECT_SOURCE_DIR}/build)
endif()

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${OUTPUT_DIR})

# Create directories for output
file(MAKE_DIRECTORY ${PROJECT_SOURCE_DIR}/data/processed)
file(MAKE_DIRECTORY ${PROJECT_SOURCE_DIR}/data/disk_queue)
file(MAKE_DIRECTORY ${PROJECT_SOURCE_DIR}/config/cache)
file(MAKE_DIRECTORY ${PROJECT_SOURCE_DIR}/../RawHTMLdata)

# Define source files organized in modular structure
set(SOURCES
    # Core crawler components - UPDATED FOR NEW MODULAR STRUCTURE
    src/core/crawler_main_new.cpp
    src/core/crawler_core.cpp
    src/core/crawler_workers.cpp
    src/core/crawler_modes.cpp
    src/core/crawler_monitoring.cpp

    # Configuration management
    src/config/config_loader.cpp
    src/config/domain_config.cpp
    src/config/domain_blacklist.cpp

    # Network layer
    src/network/http_client.cpp
    src/network/connection_pool.cpp
    src/network/rate_limiter.cpp
    src/network/robots_txt_cache.cpp
    src/network/conditional_get.cpp

    # Queue management
    src/queue/sharded_disk_queue.cpp
    src/queue/work_stealing_queue.cpp
    src/queue/html_processing_queue.cpp
    src/queue/smart_frontier.cpp

    # Parsing and content processing
    src/parsing/ultra_parser.cpp
    src/parsing/language_detector.cpp
    src/parsing/content_filter.cpp
    src/parsing/html_document.cpp
    src/parsing/rss_poller.cpp
    src/parsing/sitemap_parser.cpp

    # Storage layer
    src/storage/enhanced_storage.cpp

    # Monitoring and logging
    src/monitoring/performance_monitor.cpp
    src/monitoring/error_tracker.cpp
    src/storage/crawl_metadata.cpp

    # Utility functions
    src/utils/url_normalizer.cpp
    src/utils/utility_functions.cpp

    third_party/tracy/public/TracyClient.cpp
)
# Replace Tracy definitions with:
add_definitions(-DTRACY_ENABLE)
# Modular executable
add_executable(crawler ${SOURCES})
target_link_options(crawler PRIVATE -rdynamic)
# Include directories for modular design
target_include_directories(crawler PRIVATE
    ${PROJECT_SOURCE_DIR}/src
    ${PROJECT_SOURCE_DIR}/src/core
    ${PROJECT_SOURCE_DIR}/src/config
    ${PROJECT_SOURCE_DIR}/src/network
    ${PROJECT_SOURCE_DIR}/src/queue
    ${PROJECT_SOURCE_DIR}/src/parsing
    ${PROJECT_SOURCE_DIR}/src/storage
    ${PROJECT_SOURCE_DIR}/src/monitoring
    ${PROJECT_SOURCE_DIR}/src/utils
    ${PROJECT_SOURCE_DIR}/include
    ${CMAKE_SOURCE_DIR}/third_party/tracy/public
    ${RE2_INCLUDE_DIRS}
)

# Linking for modular crawler
target_link_libraries(crawler PRIVATE
    # FIX: Link the concurrentqueue library. This automatically adds its include directory.
    concurrentqueue
    ${CURL_LIBRARIES}
    ${TINYXML2_LIBRARIES}
    pthread
    stdc++fs
    RocksDB::rocksdb
    ${RE2_LIBRARIES}
)

# Install targets
install(TARGETS crawler DESTINATION bin)

# Custom targets for development
add_custom_target(clean-data
    COMMAND rm -rf ${PROJECT_SOURCE_DIR}/data/*
    COMMENT "Cleaning crawled data"
)

add_custom_target(debug-build
    COMMAND ${CMAKE_COMMAND} -DCMAKE_BUILD_TYPE=Debug ${CMAKE_SOURCE_DIR}
    COMMAND ${CMAKE_COMMAND} --build . --target crawler
    COMMENT "Building debug version"
)

# Production build target
add_custom_target(build-crawler
    COMMAND ${CMAKE_COMMAND} --build . --target crawler
    COMMENT "Building modular crawler"
)

