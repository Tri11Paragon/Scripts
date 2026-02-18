#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import shutil
import re
import subprocess

BROCK_JAR_PATH = "/home/brett/Documents/Brock/Teaching/brock-v-1-0-28.jar"
RUNNER_COMMAND = ["java", "-jar", Path(__file__).resolve().parent / "RunBlueJ.jar", BROCK_JAR_PATH]
OPEN_IN_BLUEJ = False
OPEN_IMAGES = True
OPEN_EDITOR = True
FILE_BROWSER = ["dolphin"]
EDITOR = ["kate"]

def open_folder(folder):
    run_command = FILE_BROWSER.copy()
    run_command.append(folder.absolute())
    subprocess.Popen(run_command)

def open_image_pdf(file):
    run = ["xdg-open", file.absolute()]
    subprocess.Popen(run)

def open_editor(files):
    run_command = EDITOR.copy()
    for file in files:
        run_command.append(file.absolute())
    subprocess.Popen(run_command)

def run_java_file(file, files):
    run_command = RUNNER_COMMAND.copy()
    run_command.append(file.absolute())
    run_command.extend(files)
    subprocess.Popen(run_command, cwd=file.parent)

def glob_picture(folder, pattern):
    found = False
    for file in folder.glob(pattern):
        if "__MACOSX" in str(file.parent):
            continue
        open_image_pdf(file)
        found = True
    return found

def process_zip(path, allow_duplicates):
    print(f"Processing file: '{path}'")
    folder = path.parent / Path(path.stem)
    if not folder.exists() or allow_duplicates:
        folder.mkdir(exist_ok=True)
        shutil.unpack_archive(path, folder)
        print(f"Unpacked to '{folder}'")

    kate = False
    files = []
    cp = []
    for file in folder.glob("**/*.java"):
        if "__MACOSX" in str(file.parent):
            continue
#        open_editor(file)
        kate = True
        if BROCK_JAR_PATH:
            files.append(file)
            class_path = file.with_suffix(".class")
            if class_path.exists():
                print(f"Removing old class file: {class_path}")
                class_path.unlink()
            cp.append(class_path)
            print(f"Classpath found {class_path} from file {file}")

    if OPEN_IMAGES:
        found = False
        found |= glob_picture(folder, "**/*.png")
        found |= glob_picture(folder, "**/*.jpg")
        found |= glob_picture(folder, "**/*.jpeg")
        found |= glob_picture(folder, "**/*.pdf")

        if not found:
            print("Unable to find any pseudocode pictures")
            open_folder(folder)

    print("Compiling Java Files")
    subprocess.run(["javac", "-cp", BROCK_JAR_PATH] + [str(file) for file in files])
    print("Running Java Files")
    if OPEN_EDITOR:
        open_editor(files)
    if not OPEN_IN_BLUEJ:
        for file in files:
            print(f"Trying to run file {file}")
            class_path = file.with_suffix(".class")
            run_java_file(class_path, [str(file.parent) + "/"])

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
    parser.add_argument("-i", "--no_images", dest="i", action="store_true", default=False)
    parser.add_argument("-e", "--no_editor", dest="e", action="store_true", default=False)
    parser.add_argument("-c", "--compile_only", dest="c", action="store_true", default=False)
    args = parser.parse_args()

    zip_file = args.zip

    if args.c:
        args.i = True
        args.e = True

    if args.i:
        global OPEN_IMAGES
        OPEN_IMAGES = False

    if args.e:
        global OPEN_EDITOR
        OPEN_EDITOR = False

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
