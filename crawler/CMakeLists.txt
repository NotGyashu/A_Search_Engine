cmake_minimum_required(VERSION 3.10)
project(mini_search_engine_crawler)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Add include directory for configuration headers
include_directories(${CMAKE_SOURCE_DIR}/include)

# Aggressive optimization flags for maximum performance (Phase 1 Ultra)
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -march=native -mtune=native -flto -DNDEBUG -funroll-loops -ffast-math")
set(CMAKE_C_FLAGS_RELEASE "-O3 -march=native -mtune=native -flto -DNDEBUG")

# Ultra-performance specific flags for Phase 1
set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -mavx2 -mfma")
set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -fno-stack-protector")  # Remove for production

# Link-time optimization
set(CMAKE_EXE_LINKER_FLAGS_RELEASE "-flto -Wl,--gc-sections")

# Debug flags
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0 -DDEBUG -fsanitize=address")

# Dependencies
find_package(CURL REQUIRED)
find_package(PkgConfig REQUIRED)

# Load submodule include helper
include(${CMAKE_SOURCE_DIR}/cmake/IncludeGitSubmodule.cmake)

# SQLite3 dependency
pkg_check_modules(SQLITE3 REQUIRED sqlite3)

# Ultra-fast SIMD HTML parser only (300+ pages/sec performance)
# Using custom implementation with AVX2 acceleration

# Hyperscan for ultra-fast pattern matching (optional for ultra_parser)
find_path(HYPERSCAN_INCLUDE_DIR hs/hs.h PATHS
    /usr/include
    /usr/local/include
)

find_library(HYPERSCAN_LIBRARY NAMES hs PATHS
    /usr/lib
    /usr/local/lib
    /usr/lib/x86_64-linux-gnu
)

if(HYPERSCAN_INCLUDE_DIR AND HYPERSCAN_LIBRARY)
    add_library(Hyperscan::Hyperscan UNKNOWN IMPORTED)
    set_target_properties(Hyperscan::Hyperscan PROPERTIES
        IMPORTED_LOCATION "${HYPERSCAN_LIBRARY}"
        INTERFACE_INCLUDE_DIRECTORIES "${HYPERSCAN_INCLUDE_DIR}"
    )
    message(STATUS "Hyperscan found: ${HYPERSCAN_LIBRARY}")
    add_compile_definitions(HAVE_HYPERSCAN=1)
else()
    message(STATUS "Hyperscan not found. Ultra parser will use fallback pattern matching.")
    add_compile_definitions(HAVE_HYPERSCAN=0)
endif()

# Include additional Git submodules (header-only)
include_git_submodule(third_party/concurrentqueue)

# Include directories
include_directories(
    ${PROJECT_SOURCE_DIR}/third_party
    ${SQLITE3_INCLUDE_DIRS}
)

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
file(MAKE_DIRECTORY ${PROJECT_SOURCE_DIR}/data/raw)
file(MAKE_DIRECTORY ${PROJECT_SOURCE_DIR}/data/processed)
file(MAKE_DIRECTORY ${PROJECT_SOURCE_DIR}/data/disk_queue)

# Define source files that actually exist
set(MODULAR_SOURCES
    # Main crawler entry point
    src/crawler_main.cpp
    
    # Utilities
    src/utils.cpp
    
    # Language Detection
    src/language_detector.cpp
    
    # Ultra-fast SIMD parser
    src/ultra_parser.cpp
)

# Modular executable
add_executable(crawler ${MODULAR_SOURCES})

# Include directories for modular design
target_include_directories(crawler PRIVATE
    ${PROJECT_SOURCE_DIR}/src
    ${PROJECT_SOURCE_DIR}/include
)

# Linking for modular crawler
target_link_libraries(crawler 
    ${CURL_LIBRARIES}
    ${SQLITE3_LIBRARIES}
    pthread
    stdc++fs
)

# Link optional high-performance libraries
if(HYPERSCAN_LIBRARY)
    target_link_libraries(crawler ${HYPERSCAN_LIBRARY})
endif()

# Install targets
install(TARGETS crawler DESTINATION bin)

# Custom targets for development
add_custom_target(clean-data
    COMMAND rm -rf ${PROJECT_SOURCE_DIR}/data/raw/*
    COMMAND rm -rf ${PROJECT_SOURCE_DIR}/data/processed/*
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
