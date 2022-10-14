
file(GLOB libarl_be_sw_SRC
    "*.h"
    "*.cpp")

add_library(arl-be-sw SHARED ${libarl_be_sw_SRC})

target_include_directories(arl-be-sw PRIVATE
    "${PACKAGES_DIR}/libarl/src/include"
    "${PACKAGES_DIR}/libvsc/src/include"
)

