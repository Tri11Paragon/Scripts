#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import shutil
import re
import subprocess

BROCK_JAR_PATH = "/home/brett/Documents/Brock/Teaching/1P02 Fall 2025/Assignment Marking/Assignment 3/brock-v-1-0-17.jar"
RUNNER_COMMAND = ["java", "-jar", Path(__file__).resolve().parent / "RunBlueJ.jar", BROCK_JAR_PATH]
OPEN_IN_BLUEJ = False
FILE_BROWSER = ["dolphin"]
EDITOR = ["kate"]

def open_folder(folder):
    run_command = FILE_BROWSER
    run_command.append(folder.absolute())
    subprocess.run(run_command)

def open_editor(file):
    run_command = EDITOR
    run_command.append(file.absolute())
    subprocess.run(run_command)

def run_java_file(file):
    run_command = RUNNER_COMMAND
    run_command.append(file.absolute())
    subprocess.run(run_command, cwd=file.parent)

def process_zip(path, allow_duplicates):
    print(f"Processing file: '{path}'")
    folder = path.parent / Path(path.stem)
    if not folder.exists() or allow_duplicates:
        folder.mkdir(exist_ok=True)
        shutil.unpack_archive(path, folder)
        print(f"Unpacked to '{folder}'")

    kate = False
    for file in folder.glob("**/*.java"):
        if "__MACOSX" in str(file.parent):
            continue
        open_editor(file)
        kate = True
        if BROCK_JAR_PATH:
            class_path = file.with_suffix(".class")
            if class_path.exists():
                print(f"Removing old class file: {class_path}")
                class_path.unlink()
            subprocess.run(["javac", "-cp", BROCK_JAR_PATH, str(file)])
            if not OPEN_IN_BLUEJ:
                run_java_file(class_path)

    if OPEN_IN_BLUEJ:
        bluej = False
        for file in folder.glob("**/*.bluej"):
            if "__MACOSX" in str(file.parent):
                continue
            subprocess.run(["bluej", str(file)])
            bluej = True

        if not bluej:
            print("No .bluej files found?")
            open_folder(folder)
    if not kate:
        print("No .java files found?")
        open_folder(folder)

def process_java(path):
    pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--allow-duplicates", dest="d", action="store_true", default=False,
                        help="Providing this flag will cause the program to unzip the archive even if the corresponding folder exists")
    parser.add_argument("zip", help="The zip file to mark.")
    args = parser.parse_args()

    zip_file = args.zip

    path = Path(zip_file)
    name = path.suffix

    if name == ".zip":
        process_zip(path, args.d)
    else:
        process_zip(Path(str(path) + ".zip"), args.d)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit(0)
