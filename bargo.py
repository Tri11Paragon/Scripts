#!/usr/bin/python3

# This script is used for initializing a CLion C++ Project

import requests
import json
import argparse
import os
import subprocess
import create_git_repo as repo

def open_process(command):
    process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = process.communicate()
    exit_code = process.wait()
    #print(stdout, stderr, exit_code)
    return (stdout, stderr, exit_code)

cmake_output, cmake_err, _ = open_process(["cmake", "--version"])

cmake_lines = cmake_output.splitlines()
print(str(cmake_lines[0]).split("version ")[1][0:-1])