import unittest
from pathlib import Path
import importlib.metadata

_REQUIREMENTS_PATH = Path(__file__).parent.with_name("requirements.txt")

class TestRequirements(unittest.TestCase):
    """Test that required packages (and versions) are installed."""

    def test_requirements(self):
        with _REQUIREMENTS_PATH.open(encoding="utf-16") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if '==' in line:
                    package, expected_version = line.split('==')
                else:
                    package, expected_version = line, None

                package = package.strip().lower()

                with self.subTest(requirement=line):
                    try:
                        installed_version = importlib.metadata.version(package)
                        if expected_version and installed_version != expected_version:
                            self.fail(f"Version mismatch for '{package}': expected {expected_version}, got {installed_version}")
                        else:
                            print(f"Package '{package}' is installed (version {installed_version})")
                    except importlib.metadata.PackageNotFoundError:
                        self.fail(f"Package '{package}' is not installed")

if __name__ == "__main__":
    unittest.main()
