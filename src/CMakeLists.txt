
file(GLOB zsp_be_sw_SRC
    "*.h"
    "*.cpp")

file(GLOB zsp_be_sw_rt_SRC
    "rt/*.h"
    "rt/*.cpp"
    "rt/*.c")

add_library(zsp-be-sw SHARED ${zsp_be_sw_SRC})

target_include_directories(zsp-be-sw PRIVATE
    "${debug_mgr_INCDIR}"
    "${vsc_dm_INCDIR}"
    "${zsp_arl_dm_INCDIR}"
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
)

add_library(zsp-be-sw-rt SHARED ${zsp_be_sw_rt_SRC})

target_include_directories(zsp-be-sw-rt PRIVATE
    "${debug_mgr_INCDIR}"
    "${vsc_dm_INCDIR}"
    "${zsp_arl_dm_INCDIR}"
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
)

install(TARGETS zsp-be-sw 
    DESTINATION lib
    EXPORT zsp-be-sw-targets)

install(TARGETS zsp-be-sw-rt
    DESTINATION lib
    EXPORT zsp-be-sw-targets)

