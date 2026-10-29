cmake_minimum_required(VERSION 3.16)
project(pruefstand CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

find_package(Threads REQUIRED)

add_executable(pruefstand
  src/main.cpp
  src/konfiguration.cpp
  src/gpio.cpp
  src/hardware_pi.cpp
  src/hardware_sim.cpp
  src/motor.cpp
  src/waegezelle.cpp
  src/messprotokoll.cpp
  src/usb_export.cpp
  src/zustandsmaschine.cpp
  src/befehlsserver.cpp
)
target_compile_options(pruefstand PRIVATE -Wall -Wextra)
target_link_libraries(pruefstand PRIVATE Threads::Threads)
