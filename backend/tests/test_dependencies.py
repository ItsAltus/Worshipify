import re
import sys
from pathlib import Path

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version

def extract_requirement_names(requirements_path: Path) -> list[str]:
    """
    Extract distribution names from requirements.txt.

    Supports lines like:
      - pkg==1.2.3
      - pkg>=1.2
      - pkg[extra]==1.2
      - pkg ; python_version < "3.12"
      - -r other.txt (ignored)
      - --extra-index-url ... (ignored)
      - git+https://... (ignored)

    Returns normalized distribution names (keeps original case if present).
    """
    names: list[str] = []

    for raw in requirements_path.read_text(encoding="utf-8", errors="strict").splitlines():
        line = raw.strip()

        if not line or line.startswith("#"):
            continue

        # Ignore pip options / includes / editable installs / direct URLs
        if line.startswith(("-", "--")):
            # -r, -e, --index-url, etc.
            continue
        if "://" in line or line.startswith("git+"):
            continue

        # Strip environment markers
        line = line.split(";", 1)[0].strip()
        if not line:
            continue

        # Strip extras: "pkg[extra1,extra2]" -> "pkg"
        line = re.sub(r"\[.*\]$", "", line).strip()

        # Strip version specifiers and spaces
        # Split on first occurrence of one of these operators
        name = re.split(r"\s*(==|>=|<=|!=|~=|>|<)\s*", line, maxsplit=1)[0].strip()

        if name:
            names.append(name)

    return names

def dist_is_installed(dist_name: str) -> tuple[bool, str | None]:
    """
    Returns (installed?, version_str_if_installed).
    Uses importlib.metadata which checks installed distributions,
    not import module names.
    """
    try:
        return True, version(dist_name)
    except PackageNotFoundError:
        return False, None
    except Exception:
        # If metadata is broken for a dist, treat as not ok
        return False, None

# Optional: import smoke-test for key runtime libs.
# Keep this small to avoid constant maintenance.
RUNTIME_IMPORT_SMOKE_TESTS: dict[str, str] = {
    "fastapi": "fastapi",
    "starlette": "starlette",
    "uvicorn": "uvicorn",
    "sqlalchemy": "sqlalchemy",
    "alembic": "alembic",
    "asyncpg": "asyncpg",
    "psycopg2": "psycopg2",
    "redis": "redis",
    "httpx": "httpx",
    # Add more if you *actually* import them at runtime.
}

def main() -> int:
    print(f"Python version: {sys.version}")

    requirements_path = Path("backend/requirements.txt")
    if not requirements_path.exists():
        print("Could not find backend/requirements.txt")
        return 1

    reqs = extract_requirement_names(requirements_path)
    if not reqs:
        print("No requirements found in backend/requirements.txt")
        return 1

    missing: list[str] = []

    # 1) Verify distributions are installed
    for dist in reqs:
        ok, ver = dist_is_installed(dist)
        if ok:
            print(f"✔ Installed {dist} ({ver})")
        else:
            print(f"✘ Missing distribution {dist}")
            missing.append(dist)

    if missing:
        print("\nMissing distributions detected:")
        for m in missing:
            print(f" - {m}")
        return 1

    # 2) Optional runtime import smoke-test (small curated list)
    import_failures: list[tuple[str, str]] = []
    for label, module_name in RUNTIME_IMPORT_SMOKE_TESTS.items():
        try:
            import_module(module_name)
            print(f"✔ Imported runtime module {label} ({module_name})")
        except Exception as e:
            print(f"✘ Failed to import runtime module {label} ({module_name}): {e}")
            import_failures.append((label, module_name))

    if import_failures:
        print("\nRuntime import failures detected:")
        for label, module_name in import_failures:
            print(f" - {label} -> {module_name}")
        return 1

    print("\nAll dependency checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
