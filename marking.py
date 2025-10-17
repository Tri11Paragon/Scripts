#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import shutil
import re
import subprocess

def process_zip(path):
    print(f"Processing file: '{path}'")
    folder = path.parent / Path(path.stem)
    folder.mkdir(exist_ok=True)
    shutil.unpack_archive(path, folder)
    print(f"Unpacked to '{folder}'")

    kate = False
    for file in folder.glob("**/*.java"):
        if "__MACOSX" in str(file.parent):
            continue
        subprocess.run(["kate", file])
        kate = True

    bluej = False
    for file in folder.glob("**/*.bluej"):
        if "__MACOSX" in str(file.parent):
            continue
        subprocess.run(["bluej", str(file)])
        bluej = True

    if not bluej:
        print("No .bluej files found?")
    if not kate:
        print("No .java files found?")
    if not bluej or not kate:
        subprocess.run(["dolphin", folder])

def process_java(path):
    pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("zip", help="The zip file to mark.")
    args = parser.parse_args()

    zip_file = args.zip

    path = Path(zip_file)
    name = path.suffix

    if name == ".zip":
        process_zip(path)
    else:
        process_zip(Path(str(path) + ".zip"))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit(0)