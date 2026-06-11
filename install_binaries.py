import os
import platform
import subprocess
import sys
from pathlib import Path

if platform.system() == "Windows":
    import winreg

DOWNLOADS_DIR = Path(__file__).parent / "downloads"

PLATFORM_PATTERNS = {
    ("Windows", "AMD64"): "claude-*-win32-x64.exe",
    ("Darwin", "arm64"): "claude-*-darwin-arm64",
    ("Darwin", "x86_64"): "claude-*-darwin-x64",
    ("Linux", "x86_64"): "claude-*-linux-x64",
    ("Linux", "aarch64"): "claude-*-linux-arm64",
}


def add_to_path() -> None:
    system = platform.system()

    if system == "Windows":
        bin_dir = Path(os.environ["USERPROFILE"]) / ".local" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        bin_str = str(bin_dir)

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS
        )
        try:
            current, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current = ""

        entries = [e for e in current.split(";") if e]
        if bin_str not in entries:
            entries.append(bin_str)
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, ";".join(entries))
            print(f"Added to user PATH: {bin_str}")
            print("  Restart your terminal for the change to take effect.")
        else:
            print(f"Already on PATH: {bin_str}")
        winreg.CloseKey(key)

        os.environ["PATH"] = os.environ.get("PATH", "") + ";" + bin_str

    elif system == "Darwin":
        bin_dir = Path.home() / ".local" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        bin_str = str(bin_dir)

        shell = Path(os.environ.get("SHELL", "/bin/zsh")).name
        rc_file = Path.home() / (".zshrc" if shell == "zsh" else ".bash_profile")

        export_line = f'export PATH="$PATH:{bin_str}"'
        rc_contents = rc_file.read_text() if rc_file.exists() else ""

        if bin_str not in rc_contents:
            with open(rc_file, "a") as f:
                f.write(f"\n{export_line}\n")
            print(f"Added to PATH in {rc_file}: {bin_str}")
            print("  Restart your terminal or run: source " + str(rc_file))
        else:
            print(f"Already on PATH in {rc_file}: {bin_str}")

        os.environ["PATH"] = os.environ.get("PATH", "") + ":" + bin_str


def detect_pattern() -> str:
    system = platform.system()
    machine = platform.machine()
    key = (system, machine)

    if key not in PLATFORM_PATTERNS:
        print(f"ERROR: Unsupported platform: {system} {machine}", file=sys.stderr)
        sys.exit(1)

    return PLATFORM_PATTERNS[key]


def find_binary(pattern: str) -> Path:
    matches = list(DOWNLOADS_DIR.glob(pattern))
    if not matches:
        print(
            f"ERROR: No binary found in {DOWNLOADS_DIR}/ matching {pattern}",
            file=sys.stderr,
        )
        print("Run fetch_binaries.py first.", file=sys.stderr)
        sys.exit(1)

    return matches[0]


def main():
    pattern = detect_pattern()
    binary = find_binary(pattern)

    if platform.system() != "Windows":
        binary.chmod(binary.stat().st_mode | 0o755)

    env = os.environ.copy()
    cert_path = env.get("NODE_EXTRA_CA_CERTS")
    if cert_path and Path(cert_path).is_file():
        print(f"Using CA bundle: {cert_path}")
    else:
        if cert_path:
            print(
                f"WARNING: NODE_EXTRA_CA_CERTS is set but file not found: {cert_path}",
                file=sys.stderr,
            )
        env.pop("NODE_EXTRA_CA_CERTS", None)

    print(f"Installing from {binary}...")
    result = subprocess.run([str(binary), "install"], env=env)

    if result.returncode != 0:
        print(
            f"ERROR: Installation failed (exit code {result.returncode})",
            file=sys.stderr,
        )
        sys.exit(result.returncode)

    add_to_path()
    print("Installation complete!")


if __name__ == "__main__":
    main()