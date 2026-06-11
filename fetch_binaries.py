import hashlib
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from pathlib import Path

DOWNLOAD_BASE_URL = "https://downloads.claude.ai/claude-code-releases"
PLATFORMS = {
    "win32-x64": "claude.exe",
    "linux-x64": "claude",
    "darwin-x64": "claude",
    "linux-arm64": "claude",
    "darwin-arm64": "claude",
}


def fetch(url: str) -> bytes:
    try:
        with urlopen(url) as resp:
            return resp.read()
    except HTTPError as e:
        print(f"ERROR: HTTP {e.code} fetching {url}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"ERROR: Failed to reach {url}: {e.reason}", file=sys.stderr)
        sys.exit(1)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    download_dir = Path(__file__).parent / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)

    print("Fetching latest version...")
    version = fetch(f"{DOWNLOAD_BASE_URL}/latest").decode().strip()

    if not re.match(r"^\d+\.\d+\.\d+", version):
        print(f"ERROR: Got unexpected version content: {version!r}", file=sys.stderr)
        sys.exit(1)

    print(f"Latest version: {version}")

    print("Fetching manifest...")
    manifest = json.loads(fetch(f"{DOWNLOAD_BASE_URL}/{version}/manifest.json"))

    for platform, binary_name in PLATFORMS.items():
        print(f"\n--- {platform} ---")

        platform_info = manifest.get("platforms", {}).get(platform)
        if not platform_info:
            print(
                f"  ERROR: Platform {platform} not found in manifest", file=sys.stderr
            )
            continue

        expected_checksum = platform_info.get("checksum", "")
        if not re.match(r"^[a-f0-9]{64}$", expected_checksum):
            print(
                f"  ERROR: Invalid checksum in manifest for {platform}", file=sys.stderr
            )
            continue

        output_path = (
            download_dir
            / f"claude-{version}-{platform}{'.exe' if 'win32' in platform else ''}"
        )

        print(f"  Downloading {binary_name}...")
        url = f"{DOWNLOAD_BASE_URL}/{version}/{platform}/{binary_name}"
        data = fetch(url)

        output_path.write_bytes(data)

        print("  Verifying checksum...")
        actual_checksum = sha256_file(output_path)

        if actual_checksum != expected_checksum:
            print("  ERROR: Checksum mismatch!", file=sys.stderr)
            print(f"    Expected: {expected_checksum}", file=sys.stderr)
            print(f"    Actual:   {actual_checksum}", file=sys.stderr)
            output_path.unlink()
            continue

        checksum_path = output_path.with_suffix(output_path.suffix + ".sha256")
        checksum_path.write_text(f"{actual_checksum}  {output_path.name}\n")

        print("  Checksum verified OK")
        print(f"  Saved to: {output_path}")
        print(f"  Checksum: {checksum_path}")

    print("\nDone. Binaries are ready in the downloads/ directory.")


if __name__ == "__main__":
    main()