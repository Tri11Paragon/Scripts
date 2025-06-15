import os
import sys
import re
from pathlib import Path

def safe_var_name(path):
    return re.sub("__+", "_", ''.join(c if c.isalnum() else '_' for c in str(path)))

def safe_namespace_name(path):
    return re.sub(":::+", "::", ''.join(c if (c.isalnum() or c == '_') else '::' for c in str(path)))

def embed(input_path, output_path, namespace, var_name):
    with open(input_path, "rt") as f:
        contents = f.read()
    out = (
        f"// Generated from {input_path}\n"
        f"#pragma once\n\n"
        f"namespace {safe_namespace_name(namespace)}" "\n{\n"
        f"\tinline constexpr char {safe_var_name(var_name)}_str[] = R\"(\"{contents}\")\";\n""}"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path.with_suffix(output_path.suffix + ".h"), "w") as f:
        f.write(out)

def main(input_dir, output_dir):
    input_path = Path(input_dir)

    for root, _, files in os.walk(input_dir):
        for file in files:
            print(f"Processing file: %{file}%")
            file_path = Path(root) / file

            parent_path = file_path.relative_to(input_dir)

            output_path = Path(output_dir) / parent_path

            embed(file_path, output_path, parent_path, file_path.name)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Expected two arguments: input_dir output_dir")
        exit(1)
    main(sys.argv[1], sys.argv[2])
