"""Local test runner: compare PDFs via the API and save results to output/.

Usage:
  python test_local.py <file_a.pdf> <file_b.pdf>        # compare 2 specific files
  python test_local.py                                   # auto-discover *_a / *_b pairs

The script auto-starts the server, runs comparisons through the real API,
then shuts the server down — identical logic to a production HTTP call.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

API_URL = "http://127.0.0.1:8000/compare-pdf"
OUTPUT_DIR = Path("output")
LOCAL_PDF_DIR = Path("localPDF")
STARTUP_TIMEOUT = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two PDF files locally via the API.")
    parser.add_argument("file_a", nargs="?", help="Path to first PDF")
    parser.add_argument("file_b", nargs="?", help="Path to second PDF")
    return parser.parse_args()


def discover_pairs() -> list[tuple[str, Path, Path]]:
    """Find all <name>_a.pdf / <name>_b.pdf pairs in localPDF/."""
    a_files = sorted(LOCAL_PDF_DIR.glob("*_a.pdf"))
    pairs = []
    for a_path in a_files:
        name = a_path.stem.removesuffix("_a")
        b_path = LOCAL_PDF_DIR / f"{name}_b.pdf"
        if b_path.exists():
            pairs.append((name, a_path, b_path))
        else:
            print(f"[WARN] No matching _b file for {a_path.name}, skipping.")
    return pairs


def wait_for_server() -> bool:
    for _ in range(STARTUP_TIMEOUT * 5):
        try:
            requests.get("http://127.0.0.1:8000/docs", timeout=1)
            return True
        except requests.ConnectionError:
            time.sleep(0.2)
    return False


def compare_via_api(path_a: Path, path_b: Path) -> dict:
    """Send two PDFs to the real API endpoint — same logic as production."""
    with open(path_a, "rb") as fa, open(path_b, "rb") as fb:
        resp = requests.post(
            API_URL,
            files={"file_a": (path_a.name, fa), "file_b": (path_b.name, fb)},
            timeout=30,
        )
    resp.raise_for_status()
    return resp.json()


def save_result(name: str, result: dict) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"{name}_result.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def build_job_list(args: argparse.Namespace) -> list[tuple[str, Path, Path]]:
    if args.file_a and args.file_b:
        pa, pb = Path(args.file_a), Path(args.file_b)
        for p in (pa, pb):
            if not p.exists():
                print(f"ERROR: File not found: {p}")
                sys.exit(1)
        name = f"{pa.stem}_vs_{pb.stem}"
        return [(name, pa, pb)]

    pairs = discover_pairs()
    if not pairs:
        print(f"No PDF pairs found in {LOCAL_PDF_DIR}/")
        print("Usage:  python test_local.py <file_a.pdf> <file_b.pdf>")
        sys.exit(1)
    return pairs


def run_jobs(jobs: list[tuple[str, Path, Path]]) -> None:
    for name, path_a, path_b in jobs:
        print(f"Comparing: {path_a}  vs  {path_b}")
        result = compare_via_api(path_a, path_b)
        out_path = save_result(name, result)

        diff_count = result["summary"]["different_pages"]
        status = "SAME" if result["same"] else f"DIFF ({diff_count} page(s))"
        print(f"  Result : {status}")
        print(f"  Saved  : {out_path}\n")


def main() -> None:
    args = parse_args()
    jobs = build_job_list(args)

    print(f"Found {len(jobs)} comparison(s) to run.\n")
    print("Starting API server...")

    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        if not wait_for_server():
            print("ERROR: Server failed to start.")
            server.terminate()
            sys.exit(1)
        print("Server ready.\n")

        run_jobs(jobs)
        print("All comparisons complete. Results in output/")
    finally:
        server.terminate()
        server.wait()
        print("Server stopped.")


if __name__ == "__main__":
    main()
