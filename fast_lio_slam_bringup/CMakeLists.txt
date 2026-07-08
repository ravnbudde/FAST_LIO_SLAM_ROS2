cmake_minimum_required(VERSION 3.16)
project(fast_lio_slam_bringup)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
