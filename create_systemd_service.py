#!/bin/python3

import argparse
import subprocess
import util.color_io as color_io
import sys

parser = argparse.ArgumentParser(prog='SystemD Service Generator', description='SystemD Service Unit File Generator', epilog='Meow')

parser.add_argument("-i", "--install", nargs='?', const="/etc/systemd/system/", default=None)
parser.add_argument("service_name", required=("--install" in sys.argv or "-i" in sys.argv), default=None)

args = parser.parse_args()

f = sys.stdout

if args.install:
    path = args.install
    if not args.install.endswith("/"):
        path += "/"
    path += args.service_name
    if not args.service_name.endswith(".service"):
        path += ".service"
    f = open(path, "wt")

def bprint(*args, **kwargs):
    print(*args, file=f, **kwargs)

if __name__ == "__main__":
    bprint("[Unit]")
    description = color_io.input_print("Please enter description: ")
    bprint("")