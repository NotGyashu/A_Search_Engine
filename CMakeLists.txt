    cmake_minimum_required(VERSION 3.10)
    project(mini_search_engine)

    # Dependencies
    find_package(CURL REQUIRED)

    # Gumbo configuration
    find_path(GUMBO_INCLUDE_DIR gumbo.h)
    find_library(GUMBO_LIBRARY NAMES gumbo gumbo_static)

    if(GUMBO_INCLUDE_DIR AND GUMBO_LIBRARY)
        add_library(Gumbo::Gumbo UNKNOWN IMPORTED)
        set_target_properties(Gumbo::Gumbo PROPERTIES
            IMPORTED_LOCATION "${GUMBO_LIBRARY}"
            INTERFACE_INCLUDE_DIRECTORIES "${GUMBO_INCLUDE_DIR}"
        )
    else()
        message(FATAL_ERROR "Gumbo library not found")
    endif()

    # Set C++ standard
    set(CMAKE_CXX_STANDARD 17)
    set(CMAKE_CXX_STANDARD_REQUIRED ON)

    add_compile_options(-fstack-protector-strong)
    add_compile_options(-Wstack-usage=8192) # 8KB stack limit warning
    # Add third-party libraries
    # Include directories
    include_directories(
         ${PROJECT_SOURCE_DIR}/third_party  # Add this line
        ${PROJECT_SOURCE_DIR}/third_party/concurrentqueue
        ${GUMBO_INCLUDE_DIR}
    )

    # Executable
    add_executable(crawler 
        src/crawler.cpp 
        src/utils.cpp
    )

    # Linking
    target_link_libraries(crawler 
        ${CURL_LIBRARIES}
        pthread
        Gumbo::Gumbo
        stdc++fs
    )

    # Install third-party deps script
    add_custom_target(get_deps 
        COMMAND ./scripts/install_deps.sh
    )