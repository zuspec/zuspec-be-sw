
file(GLOB libarl_be_sw_SRC
    "*.h"
    "*.cpp")

add_library(libarl-be-sw ${libarl_be_sw_SRC})

target_include_directories(libarl-be-sw PRIVATE
    "${PACKAGES_DIR}/libarl/src/include"
    "${PACKAGES_DIR}/libvsc/src/include"
)

