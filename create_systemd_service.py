#!/bin/python3

import argparse
import subprocess
import util.color_io as color_io
import sys

parser = argparse.ArgumentParser(prog='SystemD Service Generator', description='SystemD Service Unit File Generator', epilog='Meow')

parser.add_argument("-i", "--install", nargs='?', const="/etc/systemd/system/", default=None)
parser.add_argument("-r", "--restart", default="on-failure")
parser.add_argument("-w", "--wanted", default="multi-user.target")
parser.add_argument("-d", "--working_dir", default=None)
parser.add_argument("-u", "--user", default=None)
parser.add_argument('-g', "--group", default=None)
if "--install" in sys.argv or "-i" in sys.argv:
    parser.add_argument("service_name", default=None)

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
    description = color_io.input_print("Please enter description")
    exec_string = color_io.input_print("Please enter execution string")
    bprint("[Unit]")
    bprint("Description=" + description)
    bprint()
    bprint("[Service]")
    bprint("Type=exec")
    if args.working_dir is not None:
        bprint("WorkingDirectory=" + args.working_dir)
    if args.user is not None:
        bprint("User=" + args.user)
    if args.group is not None:
        bprint("Group=" + args.group)
    bprint("ExecStart=" + exec_string)
    bprint("RestartSec=1s")
    bprint("Restart=" + args.restart)
    bprint("OOMPolicy=stop")
    bprint()
    bprint("[Install]")
    bprint("WantedBy=" + args.wanted)