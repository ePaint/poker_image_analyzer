"""Build script for Hand History De-anonymizer.

Increments version, runs PyInstaller, and creates Windows installer.
"""

import re
import subprocess
import sys
from pathlib import Path


def get_version(pyproject_path: Path) -> str:
    """Get current version from pyproject.toml."""
    content = pyproject_path.read_text()
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def bump_version(version: str, part: str = "patch") -> str:
    """Bump version string. Part can be 'major', 'minor', or 'patch'."""
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version}")

    major, minor, patch = map(int, parts)

    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid part: {part}")

    return f"{major}.{minor}.{patch}"


def update_pyproject_version(pyproject_path: Path, new_version: str) -> None:
    """Update version in pyproject.toml."""
    content = pyproject_path.read_text()
    updated = re.sub(
        r'(version\s*=\s*)"[^"]+"',
        f'\\1"{new_version}"',
        content,
    )
    pyproject_path.write_text(updated)
    print(f"Updated pyproject.toml to version {new_version}")


def update_iss_version(iss_path: Path, new_version: str) -> None:
    """Update version in installer.iss."""
    content = iss_path.read_text()
    updated = re.sub(
        r'(#define MyAppVersion\s+)"[^"]+"',
        f'\\1"{new_version}"',
        content,
    )
    iss_path.write_text(updated)
    print(f"Updated installer.iss to version {new_version}")


def update_spec_version(spec_path: Path, new_version: str) -> None:
    """Update version in PyInstaller spec file (macOS bundle info)."""
    content = spec_path.read_text()
    # Update CFBundleShortVersionString
    updated = re.sub(
        r"('CFBundleShortVersionString':\s*)'[^']+'",
        f"\\1'{new_version}'",
        content,
    )
    # Update CFBundleVersion
    updated = re.sub(
        r"('CFBundleVersion':\s*)'[^']+'",
        f"\\1'{new_version}'",
        updated,
    )
    spec_path.write_text(updated)
    print(f"Updated spec file to version {new_version}")


def run_pyinstaller(spec_path: Path) -> bool:
    """Run PyInstaller with the spec file."""
    print("\nRunning PyInstaller...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec_path), "--noconfirm"],
        cwd=spec_path.parent,
    )
    return result.returncode == 0


def find_inno_setup() -> Path | None:
    """Find Inno Setup compiler (iscc.exe) on Windows."""
    possible_paths = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 5\ISCC.exe"),
    ]
    for path in possible_paths:
        if path.exists():
            return path
    return None


def run_inno_setup(iss_path: Path) -> bool:
    """Run Inno Setup compiler."""
    if sys.platform != "win32":
        print("Skipping Inno Setup (not on Windows)")
        return True

    iscc = find_inno_setup()
    if not iscc:
        print("Warning: Inno Setup not found. Skipping installer creation.")
        print("Install from: https://jrsoftware.org/isdl.php")
        return False

    print(f"\nRunning Inno Setup ({iscc})...")
    result = subprocess.run([str(iscc), str(iss_path)], cwd=iss_path.parent)
    return result.returncode == 0


def main() -> int:
    """Main build process."""
    project_root = Path(__file__).parent
    pyproject_path = project_root / "pyproject.toml"
    iss_path = project_root / "installer.iss"
    spec_path = project_root / "HandHistoryDeanonymizer.spec"

    # Parse arguments
    bump_part = "patch"
    skip_version_bump = False

    for arg in sys.argv[1:]:
        if arg in ("major", "minor", "patch"):
            bump_part = arg
        elif arg == "--no-bump":
            skip_version_bump = True
        elif arg in ("-h", "--help"):
            print("Usage: python build.py [major|minor|patch] [--no-bump]")
            print("")
            print("Options:")
            print("  major      Bump major version (1.0.0 -> 2.0.0)")
            print("  minor      Bump minor version (1.0.0 -> 1.1.0)")
            print("  patch      Bump patch version (1.0.0 -> 1.0.1) [default]")
            print("  --no-bump  Skip version bump, use current version")
            return 0

    # Get and bump version
    current_version = get_version(pyproject_path)
    print(f"Current version: {current_version}")

    if skip_version_bump:
        new_version = current_version
        print("Skipping version bump")
    else:
        new_version = bump_version(current_version, bump_part)
        print(f"New version: {new_version}")

        # Update version in all files
        update_pyproject_version(pyproject_path, new_version)
        update_iss_version(iss_path, new_version)
        update_spec_version(spec_path, new_version)

    # Run PyInstaller
    if not run_pyinstaller(spec_path):
        print("\nPyInstaller failed!")
        return 1

    print("\nPyInstaller completed successfully!")

    # Run Inno Setup (Windows only)
    if sys.platform == "win32":
        if run_inno_setup(iss_path):
            installer_dir = project_root / "installer_output"
            print(f"\nInstaller created in: {installer_dir}")
        else:
            print("\nInno Setup failed or not available")
            return 1

    print(f"\nBuild completed! Version: {new_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
