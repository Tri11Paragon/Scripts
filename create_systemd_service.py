#!/bin/python3

import argparse
import subprocess
import color_io

parser = argparse.ArgumentParser(prog='SystemD Service Generator', description='SystemD Service Unit File Generator', epilog='Meow')

parser.add_argument("-i", "--install", nargs='?', const="/etc/systemd/system/", default=None)

args = parser.parse_args()



if __name__ == "__main__":
    