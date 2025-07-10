# crawler/cmake/IncludeGitSubmodule.cmake

function(include_git_submodule submodule_path)
    if(NOT EXISTS "${PROJECT_SOURCE_DIR}/${submodule_path}")
        message(FATAL_ERROR "Submodule '${submodule_path}' does not exist. Did you forget to init it?")
    endif()

    if(EXISTS "${PROJECT_SOURCE_DIR}/${submodule_path}/CMakeLists.txt")
        message(STATUS "Adding submodule '${submodule_path}' using add_subdirectory()")
        add_subdirectory(${PROJECT_SOURCE_DIR}/${submodule_path})
    else()
        message(STATUS "Adding submodule '${submodule_path}' as header-only with include_directories()")
        include_directories(${PROJECT_SOURCE_DIR}/${submodule_path})
    endif()
endfunction()
