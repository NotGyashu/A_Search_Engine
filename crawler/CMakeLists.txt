cmake_minimum_required(VERSION 3.10)
project(mini_search_engine_crawler)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Aggressive optimization flags for maximum performance
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -march=native -mtune=native -flto -DNDEBUG -funroll-loops")
set(CMAKE_C_FLAGS_RELEASE "-O3 -march=native -mtune=native -flto -DNDEBUG")

# Debug flags
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0 -DDEBUG -fsanitize=address")

# Dependencies
find_package(CURL REQUIRED)
find_package(PkgConfig REQUIRED)

# Load submodule include helper
include(${CMAKE_SOURCE_DIR}/cmake/IncludeGitSubmodule.cmake)

# SQLite3 dependency
pkg_check_modules(SQLITE3 REQUIRED sqlite3)

# We're using lolhtml for streaming parsing - add as dependency
find_path(LOLHTML_INCLUDE_DIR lolhtml.h PATHS
    /usr/include
    /usr/local/include
    ${PROJECT_SOURCE_DIR}/third_party/lolhtml/include
)

find_library(LOLHTML_LIBRARY NAMES lolhtml PATHS
    /usr/lib
    /usr/local/lib
    ${PROJECT_SOURCE_DIR}/third_party/lolhtml/target/release
)

if(LOLHTML_INCLUDE_DIR AND LOLHTML_LIBRARY)
    add_library(Lolhtml::Lolhtml UNKNOWN IMPORTED)
    set_target_properties(Lolhtml::Lolhtml PROPERTIES
        IMPORTED_LOCATION "${LOLHTML_LIBRARY}"
        INTERFACE_INCLUDE_DIRECTORIES "${LOLHTML_INCLUDE_DIR}"
    )
    message(STATUS "Lolhtml found: ${LOLHTML_LIBRARY}")
else()
    message(STATUS "Lolhtml not found. Using regex-based streaming parser fallback.")
endif()

# Gumbo HTML parser configuration
find_path(GUMBO_INCLUDE_DIR gumbo.h PATHS
    /usr/include
    /usr/local/include
    ${PROJECT_SOURCE_DIR}/third_party/gumbo-parser/src
)

find_library(GUMBO_LIBRARY NAMES gumbo gumbo_static PATHS
    /usr/lib
    /usr/local/lib
    ${PROJECT_SOURCE_DIR}/third_party/gumbo-parser/.libs
)

if(GUMBO_INCLUDE_DIR AND GUMBO_LIBRARY)
    add_library(Gumbo::Gumbo UNKNOWN IMPORTED)
    set_target_properties(Gumbo::Gumbo PROPERTIES
        IMPORTED_LOCATION "${GUMBO_LIBRARY}"
        INTERFACE_INCLUDE_DIRECTORIES "${GUMBO_INCLUDE_DIR}"
    )
    message(STATUS "Gumbo found: ${GUMBO_LIBRARY}")
else()
    # Try to build from source if available
    if(EXISTS "${PROJECT_SOURCE_DIR}/third_party/gumbo-parser")
        message(STATUS "Building Gumbo from source...")
        add_subdirectory(${PROJECT_SOURCE_DIR}/third_party/gumbo-parser)
        set(GUMBO_LIBRARY gumbo)
    else()
        message(FATAL_ERROR "Gumbo library not found. Please install libgumbo-dev or ensure third_party/gumbo-parser exists")
    endif()
endif()

# Include additional Git submodules (header-only)
include_git_submodule(third_party/concurrentqueue)

# Include directories
include_directories(
    ${PROJECT_SOURCE_DIR}/third_party
    ${GUMBO_INCLUDE_DIR}
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
file(MAKE_DIRECTORY ${PROJECT_SOURCE_DIR}/../data/raw)
file(MAKE_DIRECTORY ${PROJECT_SOURCE_DIR}/../data/processed)
file(MAKE_DIRECTORY ${PROJECT_SOURCE_DIR}/../data/disk_queue)

# Executable
add_executable(crawler 
    src/crawler_main.cpp 
    src/utils.cpp
)

# Linking
target_link_libraries(crawler 
    ${CURL_LIBRARIES}
    ${SQLITE3_LIBRARIES}
    ${GUMBO_LIBRARY}
    pthread
    stdc++fs
)

# Install target
install(TARGETS crawler DESTINATION bin)

# Custom targets for development
add_custom_target(clean-data
    COMMAND rm -rf ${PROJECT_SOURCE_DIR}/../data/raw/*
    COMMAND rm -rf ${PROJECT_SOURCE_DIR}/../data/processed/*
    COMMENT "Cleaning crawled data"
)

add_custom_target(debug-build
    COMMAND ${CMAKE_COMMAND} -DCMAKE_BUILD_TYPE=Debug ${CMAKE_SOURCE_DIR}
    COMMAND ${CMAKE_COMMAND} --build . --target crawler
    COMMENT "Building debug version"
)
