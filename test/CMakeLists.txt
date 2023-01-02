
include(GoogleTest)

find_package(Threads REQUIRED)

include (ExternalProject)

ExternalProject_Add(
  GTEST
  PREFIX gtest
  SOURCE_DIR ${PACKAGES_DIR}/gtest
  CMAKE_CACHE_ARGS
    -DCMAKE_C_COMPILER:STRING=${CMAKE_C_COMPILER}
    -DCMAKE_CXX_COMPILER:STRING=${CMAKE_CXX_COMPILER}
    -DCMAKE_C_FLAGS:STRING=${CMAKE_C_FLAGS}
    -DCMAKE_CXX_FLAGS:STRING=${CMAKE_CXX_FLAGS}
    -DBUILD_SHARED_LIBS:BOOL=${BUILD_SHARED_LIBS}
    -DCMAKE_INSTALL_PREFIX:PATH=${CMAKE_CURRENT_BINARY_DIR}
    -DCMAKE_BUILD_TYPE:STRING=Release
  )
  
ExternalProject_Get_Property(GTEST source_dir binary_dir)

# find_package(Gtest)

add_library(libgtest IMPORTED STATIC GLOBAL)
add_dependencies(libgtest GTEST)

set_target_properties(libgtest PROPERTIES
    "IMPORTED_LOCATION" "${binary_dir}/lib/libgtest.a"
    "IMPORTED_LINK_INTERFACE_LIBRARIES" "${CMAKE_THREAD_LIBS_INIT}"
    )

add_library(libgmock IMPORTED STATIC GLOBAL)
add_dependencies(libgmock gtest)

set_target_properties(libgmock PROPERTIES
    "IMPORTED_LOCATION" "${binary_dir}/lib/libgmock.a"
    "IMPORTED_LINK_INTERFACE_LIBRARIES" "${CMAKE_THREAD_LIBS_INIT}"
    )
    
include_directories(
	"${source_dir}/googletest/include"
	"${source_dir}/googlemock/include"
    "${CMAKE_SOURCE_DIR}/src"
    "${CMAKE_SOURCE_DIR}/src/include"
	"${PACKAGES_DIR}/zuspec-arl-dm/src/include"
	"${PACKAGES_DIR}/libvsc-dm/src/include"
	"${PACKAGES_DIR}/debug-mgr/src/include"
	)

file(GLOB test_zuspec_be_sw_SRC
  "src/*.h"
  "src/*.cpp"
  )

add_executable(test_zuspec_be_sw ${test_zuspec_be_sw_SRC})
target_include_directories(test_zuspec_be_sw PUBLIC
    "${source_dir}/googletest/include"
    )
   
target_link_directories(test_zuspec_be_sw PRIVATE
    ${CMAKE_BINARY_DIR}/lib
    ${CMAKE_BINARY_DIR}/lib64
    ${CMAKE_BINARY_DIR}/zuspec-arl-dm/src/ZuspecArl-DM-build/lib
    ${CMAKE_BINARY_DIR}/zuspec-arl-dm/src/ZuspecArl-DM-build/lib64
    ${CMAKE_BINARY_DIR}/zuspec-arl-dm/src/ZuspecArl-DM-build/src
    )
  
if (CMAKE_BUILD_TYPE STREQUAL "Debug")
	set(libglog glogd)
else()
	set(libglog glog)
endif()

target_link_libraries(test_zuspec_be_sw 
  zuspec-be-sw
  zuspec-arl-dm
  vsc-dm
  debug-mgr
	libgtest 
	libgmock
	)
add_dependencies(test_zuspec_be_sw 
  zuspec-be-sw
  ZuspecArl-DM
  GTEST
  )

gtest_discover_tests(test_zuspec_be_sw)

