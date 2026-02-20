"""Build script for Hand History De-anonymizer.

Increments version, runs PyInstaller, creates Windows installer, and optionally
creates a GitHub release.
"""

import re
import shutil
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


def find_gh_cli() -> Path | None:
    """Find GitHub CLI executable."""
    # Check if gh is in PATH
    gh_path = shutil.which("gh")
    if gh_path:
        return Path(gh_path)

    # Check common install locations on Windows
    possible_paths = [
        Path(r"C:\Program Files\GitHub CLI\gh.exe"),
        Path(r"C:\Program Files (x86)\GitHub CLI\gh.exe"),
    ]
    for path in possible_paths:
        if path.exists():
            return path
    return None


def create_github_release(version: str, installer_path: Path) -> bool:
    """Create a GitHub release with the installer attached."""
    gh = find_gh_cli()
    if not gh:
        print("Warning: GitHub CLI (gh) not found. Skipping release.")
        print("Install from: https://cli.github.com/")
        return False

    if not installer_path.exists():
        print(f"Error: Installer not found at {installer_path}")
        return False

    tag = f"v{version}"
    title = f"v{version}"
    notes = f"""## Hand History De-anonymizer {tag}

De-anonymize GGPoker/Natural8 hand histories using table screenshots.

### Features
- GUI with drag-and-drop interface
- OCR via Claude Haiku API
- Batch processing of screenshots and hand histories
- OCR dump files for reuse

### Requirements
- Windows 10/11
- Anthropic API key

### Installation
Download and run `{installer_path.name}`
"""

    print(f"\nCreating GitHub release {tag}...")
    result = subprocess.run(
        [str(gh), "release", "create", tag, str(installer_path),
         "--title", title, "--notes", notes],
        cwd=installer_path.parent.parent,
    )

    if result.returncode == 0:
        print(f"GitHub release {tag} created successfully!")
        return True
    else:
        print("Failed to create GitHub release")
        return False


def main() -> int:
    """Main build process."""
    project_root = Path(__file__).parent
    pyproject_path = project_root / "pyproject.toml"
    iss_path = project_root / "installer.iss"
    spec_path = project_root / "HandHistoryDeanonymizer.spec"

    # Parse arguments
    bump_part = "patch"
    skip_version_bump = False
    create_release = False
    release_only = False

    for arg in sys.argv[1:]:
        if arg in ("major", "minor", "patch"):
            bump_part = arg
        elif arg == "--no-bump":
            skip_version_bump = True
        elif arg == "--release":
            create_release = True
        elif arg == "--release-only":
            release_only = True
            create_release = True
        elif arg in ("-h", "--help"):
            print("Usage: python build.py [major|minor|patch] [--no-bump] [--release] [--release-only]")
            print("")
            print("Options:")
            print("  major         Bump major version (1.0.0 -> 2.0.0)")
            print("  minor         Bump minor version (1.0.0 -> 1.1.0)")
            print("  patch         Bump patch version (1.0.0 -> 1.0.1) [default]")
            print("  --no-bump     Skip version bump, use current version")
            print("  --release     Create a GitHub release after building")
            print("  --release-only  Skip build, just create release for current version")
            return 0

    # Get and bump version
    current_version = get_version(pyproject_path)
    print(f"Current version: {current_version}")

    if release_only:
        new_version = current_version
        print("Skipping build, creating release only")
    elif skip_version_bump:
        new_version = current_version
        print("Skipping version bump")
    else:
        new_version = bump_version(current_version, bump_part)
        print(f"New version: {new_version}")

        # Update version in all files
        update_pyproject_version(pyproject_path, new_version)
        update_iss_version(iss_path, new_version)
        update_spec_version(spec_path, new_version)

    if not release_only:
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

    # Create GitHub release if requested
    if create_release:
        installer_path = project_root / "installer_output" / f"HandHistoryDeanonymizer_Setup_{new_version}.exe"
        if not create_github_release(new_version, installer_path):
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
