import importlib
import sys
import re
from pathlib import Path

def extract_package_names(requirements_path: Path):
    """
    Extract top-level package names from requirements.txt.
    Strips version pins and environment markers.
    """
    packages = []

    for line in requirements_path.read_text().splitlines():
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith("#"):
            continue

        # Remove environment markers (e.g. platform_system=="Windows")
        line = line.split(";")[0].strip()

        # Remove version specifiers (==, >=, etc.)
        package = re.split(r"[<>=!~]", line)[0].strip()

        if package:
            packages.append(package)

    return packages


def main():
    print(f"Python version: {sys.version}")

    requirements_path = Path("backend/requirements.txt")

    if not requirements_path.exists():
        print("Could not find backend/requirements.txt")
        sys.exit(1)

    packages = extract_package_names(requirements_path)

    failures = []

    for package in packages:
        try:
            importlib.import_module(package.replace("-", "_"))
            print(f"✔ Imported {package}")
        except Exception as e:
            print(f"✘ Failed to import {package}: {e}")
            failures.append(package)

    if failures:
        print("\nDependency import failures detected:")
        for fail in failures:
            print(f" - {fail}")
        sys.exit(1)

    print("\nAll dependencies imported successfully.")
    sys.exit(0)

if __name__ == "__main__":
    main()
