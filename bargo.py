#!/usr/bin/python3

# This script is used for initializing a CLion C++ Project

import requests
import json
import argparse
import os
import subprocess
import create_git_repo as repo
import util.color_io as io

git_ignore = """
cmake-build*/
build/
out/
./cmake-build*/
./build/
./out/
"""

cmake_exec_default_text = """"
cmake_minimum_required(VERSION ${CMAKE_MAJOR_VERSION}.${CMAKE_MINOR_VERSION})
project(${PROJECT_NAME})

option(ENABLE_ADDRSAN "Enable the address sanitizer" OFF)
option(ENABLE_UBSAN "Enable the ub sanitizer" OFF)
option(ENABLE_TSAN "Enable the thread data race sanitizer" OFF)

set(CMAKE_CXX_STANDARD ${CMAKE_LANGUAGE_VERSION})

${SUB_DIRS}

include_directories(include/)
file(GLOB_RECURSE PROJECT_BUILD_FILES "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp")

add_executable(${PROJECT_NAME} ${PROJECT_BUILD_FILES})

target_compile_options(${PROJECT_NAME} PRIVATE -Wall -Wextra -Werror -Wpedantic -Wno-comment)
target_link_options(${PROJECT_NAME} PRIVATE -Wall -Wextra -Werror -Wpedantic -Wno-comment)

${LINKS}

if (${ENABLE_ADDRSAN} MATCHES ON)
    target_compile_options(${PROJECT_NAME} PRIVATE -fsanitize=address)
    target_link_options(${PROJECT_NAME} PRIVATE -fsanitize=address)
endif ()

if (${ENABLE_UBSAN} MATCHES ON)
    target_compile_options(${PROJECT_NAME} PRIVATE -fsanitize=undefined)
    target_link_options(${PROJECT_NAME} PRIVATE -fsanitize=undefined)
endif ()

if (${ENABLE_TSAN} MATCHES ON)
    target_compile_options(${PROJECT_NAME} PRIVATE -fsanitize=thread)
    target_link_options(${PROJECT_NAME} PRIVATE -fsanitize=thread)
endif ()
"""

cmake_lib_default_text = """"
cmake_minimum_required(VERSION ${CMAKE_MAJOR_VERSION}.${CMAKE_MINOR_VERSION})
project(${PROJECT_NAME})

option(ENABLE_ADDRSAN "Enable the address sanitizer" OFF)
option(ENABLE_UBSAN "Enable the ub sanitizer" OFF)
option(ENABLE_TSAN "Enable the thread data race sanitizer" OFF)

set(CMAKE_CXX_STANDARD ${CMAKE_LANGUAGE_VERSION})

${SUB_DIRS}

include_directories(include/)
file(GLOB_RECURSE PROJECT_BUILD_FILES "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp")

add_library(${PROJECT_NAME}${CMAKE_LIBRARY_TYPE} ${PROJECT_BUILD_FILES})

target_compile_options(${PROJECT_NAME} PRIVATE -Wall -Wextra -Werror -Wpedantic -Wno-comment)
target_link_options(${PROJECT_NAME} PRIVATE -Wall -Wextra -Werror -Wpedantic -Wno-comment)

${LINKS}

if (${ENABLE_ADDRSAN} MATCHES ON)
    target_compile_options(${PROJECT_NAME} PRIVATE -fsanitize=address)
    target_link_options(${PROJECT_NAME} PRIVATE -fsanitize=address)
endif ()

if (${ENABLE_UBSAN} MATCHES ON)
    target_compile_options(${PROJECT_NAME} PRIVATE -fsanitize=undefined)
    target_link_options(${PROJECT_NAME} PRIVATE -fsanitize=undefined)
endif ()

if (${ENABLE_TSAN} MATCHES ON)
    target_compile_options(${PROJECT_NAME} PRIVATE -fsanitize=thread)
    target_link_options(${PROJECT_NAME} PRIVATE -fsanitize=thread)
endif ()
"""

parser = argparse.ArgumentParser(prog='Bargo', description='Cargo but bad, for C++', epilog='Meow :3')
parser.add_argument("--cmake", "-c", default=None, help="Specify CMake version, defaults to using version installed on the system")
parser.add_argument("--cpp", "-p", default="17", help="C++ Version")
parser.add_argument("--no_git", default=True, action="store_false", help="Disables creating a git repo")
parser.add_argument("--no_blt", default=True, action="store_false", help="Disables init with BLT")
parser.add_argument("--lib", action="store_true", help="Create a lib instead of an exec")
parser.add_argument("--graphics", "-g", default=False, action="store_true", help="Init with graphics in mind, ie use BLT With Graphics")

parser.add_argument("action", help="Type of action to take, currently only 'init' is supported.")
parser.add_argument("name", help="Project Name")

args = parser.parse_args()

def open_process(command):
    process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = process.communicate()
    exit_code = process.wait()
    #print(stdout, stderr, exit_code)
    return (stdout, stderr, exit_code)

def get_cmake_version():
    cmake_output, _, _ = open_process(["cmake", "--version"])

    cmake_lines = cmake_output.splitlines()
    cmake_version = str(cmake_lines[0]).split("version ")[1][0:-1].split('.')

    cmake_major = cmake_version[0]
    cmake_minor = cmake_version[1]
    
    return (cmake_major, cmake_minor)

def setup_dirs():
    open_process(["mkdir", "include", "src", "lib"])
    
def setup_blt(use_git, blt_url):
    if use_git:
        open_process(["git", "submodule", "add", blt_url, "lib/blt"])
        open_process(["git", "submodule", "update", "--remote", "--init", "--recursive"])
    else:
        open_process(["git", "clone", "--recursive", blt_url, "lib/blt"])
    
def create_git_ignore():
    with open(".gitignore", "w") as f:
        f.write(git_ignore)
    
cmake_major, cmake_minor = get_cmake_version()
cpp_version = args.cpp
use_blt = args.no_blt
use_git = args.no_git
blt_url = "https://github.com/Tri11Paragon/BLT.git"
cmake_text = cmake_exec_default_text

if args.lib:
    cmake_text = cmake_lib_default_text

if args.cmake:
    version_arr = args.cmake.split(".")
    if len(version_arr) < 2:
        io.red_print("Must provide at least major.minor CMake version!")
        exit()
    cmake_major = version_arr[0]
    cmake_minor = version_arr[1]

if args.graphics:
    blt_url = "https://git.tpgc.me/tri11paragon/BLT-With-Graphics-Template"

