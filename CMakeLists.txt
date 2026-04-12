cmake_minimum_required(VERSION 3.15)
project(bowed_physics LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

# ---------------------------------------------------------------------------
# STK (Synthesis Toolkit) — vendored as a git submodule under external/stk
#
# We build our own static `stk` target from STK's source tree instead
# of calling add_subdirectory(external/stk). STK's upstream CMakeLists
# does `find_package(CoreAudio)` which fails on stock macOS, and we
# don't need its real-time audio / MIDI backends at all (we use
# FileWvOut). So we glob STK's source files, exclude the Rt*/socket
# files that depend on platform audio backends, and build the minimal
# subset we actually need.
# ---------------------------------------------------------------------------
set(STK_ROOT "${CMAKE_SOURCE_DIR}/external/stk")

if(NOT EXISTS "${STK_ROOT}/src/Stk.cpp")
    message(FATAL_ERROR
        "STK submodule not found at ${STK_ROOT}. "
        "Run: git submodule update --init --recursive")
endif()

file(GLOB STK_ALL_SRC CONFIGURE_DEPENDS "${STK_ROOT}/src/*.cpp")
set(STK_EXCLUDE
    "${STK_ROOT}/src/RtAudio.cpp"
    "${STK_ROOT}/src/RtMidi.cpp"
    "${STK_ROOT}/src/RtWvIn.cpp"
    "${STK_ROOT}/src/RtWvOut.cpp"
    "${STK_ROOT}/src/Socket.cpp"
    "${STK_ROOT}/src/UdpSocket.cpp"
    "${STK_ROOT}/src/TcpClient.cpp"
    "${STK_ROOT}/src/TcpServer.cpp"
    "${STK_ROOT}/src/Thread.cpp"
    "${STK_ROOT}/src/Mutex.cpp"
    "${STK_ROOT}/src/InetWvIn.cpp"
    "${STK_ROOT}/src/InetWvOut.cpp"
    "${STK_ROOT}/src/Messager.cpp"
    "${STK_ROOT}/src/MidiFileIn.cpp"
    "${STK_ROOT}/src/Skini.cpp"
)
list(REMOVE_ITEM STK_ALL_SRC ${STK_EXCLUDE})

add_library(stk STATIC ${STK_ALL_SRC})
target_include_directories(stk PUBLIC "${STK_ROOT}/include")
target_compile_definitions(stk PUBLIC
    _USE_MATH_DEFINES
    __LITTLE_ENDIAN__
)

# Runtime path STK uses for its .raw wavetable files.  Baked in at
# compile time so the binary is relocatable within a source checkout.
set(BP_STK_RAWWAVES_PATH "${STK_ROOT}/rawwaves/")

# ---------------------------------------------------------------------------
# bowed_physics C++ library (currently just BowedProbe)
# ---------------------------------------------------------------------------
add_library(bowed_physics STATIC
    cpp/src/BowedProbe.cpp
)
target_include_directories(bowed_physics
    PUBLIC  cpp/include
    PRIVATE ${STK_ROOT}/include
)
target_link_libraries(bowed_physics PUBLIC stk)

# ---------------------------------------------------------------------------
# Experiment binaries
# ---------------------------------------------------------------------------
add_executable(seestr cpp/src/seestr.cpp)
target_include_directories(seestr PRIVATE ${STK_ROOT}/include)
target_link_libraries(seestr PRIVATE bowed_physics stk)
target_compile_definitions(seestr PRIVATE
    BP_STK_RAWWAVES_PATH="${BP_STK_RAWWAVES_PATH}"
    _USE_MATH_DEFINES
    __LITTLE_ENDIAN__
)

# No CoreAudio / ALSA / pthread linkage required: we only use STK's
# file I/O (FileWvOut), not real-time audio / MIDI backends.
