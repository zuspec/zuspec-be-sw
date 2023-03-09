
cmake_minimum_required(VERSION 3.10)

project(libarl-be-sw)

include (ExternalProject)

set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED True)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

if (NOT PACKAGES_DIR)
  set(PACKAGES_DIR ${CMAKE_SOURCE_DIR}/packages)
  set(ENABLE_TESTING True)
endif()

if (WIN32)
  set(PYTHON ${PACKAGES_DIR}/python/Scripts/python.exe)
else()
  set(PYTHON ${PACKAGES_DIR}/python/bin/python)
endif()

execute_process(COMMAND ${PYTHON} -m ivpm share cmake OUTPUT_VARIABLE IVPM_CMAKE_PATH)
list(APPEND CMAKE_MODULE_PATH ${IVPM_CMAKE_PATH})
message("IVPM_CMAKE_PATH: ${IVPM_CMAKE_PATH} ${CMAKE_MODULE_PATH}")

include(ivpm)

Ivpm_AddPythonExtProject(debug-mgr debug_mgr)
Ivpm_AddPythonExtProject(vsc-dm vsc_dm)
Ivpm_AddPythonExtProject(zuspec-arl-dm zsp_arl_dm)

if(NOT WIN32)
  add_compile_options(-fPIC)
endif()


set(CMAKE_CXX_FLAGS_RELEASE "-O3")
set(CMAKE_CXX_FLAGS_DEBUG "-O0 -g")

add_subdirectory(src)

if (ENABLE_TESTING)
  # Testing is only enabled when libarl-be-sw is the top-level project
  enable_testing()

  add_subdirectory(test)
endif()


