
file(GLOB zuspec_be_sw_SRC
    "*.h"
    "*.cpp")

add_library(zuspec-be-sw SHARED ${zuspec_be_sw_SRC})

target_include_directories(zuspec-be-sw PRIVATE
    "${PACKAGES_DIR}/debug-mgr/src/include"
    "${PACKAGES_DIR}/libvsc-dm/src/include"
    "${PACKAGES_DIR}/zuspec-arl-dm/src/include"
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
)

