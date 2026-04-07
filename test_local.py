"""Local test runner: compare PDFs via the API and save results to output/.

Usage:
  python test_local.py <file_a.pdf> <file_b.pdf>        # compare 2 specific files
  python test_local.py                                   # interactive picker (choose from localPDF/)
  python test_local.py --auto                            # auto-discover *_a / *_b pairs in localPDF/

The script auto-starts the server, runs comparisons through the real API,
then shuts the server down — identical logic to a production HTTP call.
The child server sets COMPAREPDF_SKIP_DB_AUDIT=1 so compare results are not inserted into Postgres.

Interactive mode: localPDF/ must exist; only .pdf files inside; 1 or 2 PDFs (not 0, not >2).
CLI with two paths: both must be .pdf. --auto is unchanged (multiple *_a/_b pairs).
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

API_URL = "http://127.0.0.1:8000/compare-pdf"
HAND_SIG_URL = "http://127.0.0.1:8000/hand_signature_check"
OUTPUT_DIR = Path("output")
LOCAL_PDF_DIR = Path("localPDF")
STARTUP_TIMEOUT = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two PDF files locally via the API.")
    parser.add_argument("file_a", nargs="?", help="Path to first PDF")
    parser.add_argument("file_b", nargs="?", help="Path to second PDF")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-discover *_a.pdf + *_b.pdf pairs in localPDF/ instead of interactive picker.",
    )
    return parser.parse_args()


def _fail(msg: str) -> None:
    print(f"ERROR: {msg}")
    sys.exit(1)


def _require_pdf_suffix(path: Path, label: str) -> None:
    if path.suffix.lower() != ".pdf":
        _fail(f"{label} phải là file PDF (.pdf): {path}")


def _validated_local_pdfs_for_interactive() -> list[Path]:
    """localPDF/: must exist; only .pdf files; count 1 or 2 (not 0, not >2)."""
    if not LOCAL_PDF_DIR.exists():
        _fail(f"Thư mục {LOCAL_PDF_DIR}/ không tồn tại. Hãy tạo thư mục và thêm PDF.")
    if not LOCAL_PDF_DIR.is_dir():
        _fail(f"{LOCAL_PDF_DIR} không phải thư mục.")

    files = [p for p in LOCAL_PDF_DIR.iterdir() if p.is_file()]
    non_pdf = [p for p in files if p.suffix.lower() != ".pdf"]
    if non_pdf:
        names = ", ".join(p.name for p in non_pdf)
        _fail(
            f"Trong {LOCAL_PDF_DIR}/ chỉ được để file PDF. "
            f"Gỡ hoặc đổi chỗ các file không phải PDF: {names}"
        )

    pdfs = sorted(p for p in files if p.suffix.lower() == ".pdf")
    if len(pdfs) == 0:
        _fail(f"Không có file PDF nào trong {LOCAL_PDF_DIR}/.")
    if len(pdfs) > 2:
        names = ", ".join(p.name for p in pdfs)
        _fail(
            f"{LOCAL_PDF_DIR}/ chỉ được có tối đa 2 file PDF (hiện có {len(pdfs)}): {names}"
        )
    return pdfs


def _prompt_pick(files: list[Path], title: str) -> Path:
    print(title)
    for idx, p in enumerate(files, start=1):
        print(f"  {idx:>2}. {p.name}")

    while True:
        raw = input("Chọn số (ví dụ 1): ").strip()
        if raw.isdigit():
            n = int(raw)
            if 1 <= n <= len(files):
                return files[n - 1]
        print("Giá trị không hợp lệ, vui lòng chọn lại.\n")


def interactive_pick() -> tuple[str, Path, Path]:
    files = _validated_local_pdfs_for_interactive()

    file_a = _prompt_pick(files, "\n1) Select original file (A):")
    file_b = _prompt_pick(files, "\n2) Select file edit (B):")

    name = f"{file_a.stem}_vs_{file_b.stem}"
    return name, file_a, file_b


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
                _fail(f"Không tìm thấy file: {p}")
        _require_pdf_suffix(pa, "File A")
        _require_pdf_suffix(pb, "File B")
        name = f"{pa.stem}_vs_{pb.stem}"
        return [(name, pa, pb)]

    if args.auto:
        pairs = discover_pairs()
        if not pairs:
            print(f"No PDF pairs found in {LOCAL_PDF_DIR}/")
            print("Usage:  python test_local.py <file_a.pdf> <file_b.pdf>")
            sys.exit(1)
        return pairs

    name, a, b = interactive_pick()
    return [(name, a, b)]


def _hand_signature_check(path_a: Path, path_b: Path) -> dict:
    """Gọi endpoint hand_signature_check cho cặp PDF (A,B)."""
    with open(path_a, "rb") as fa, open(path_b, "rb") as fb:
        resp = requests.post(
            HAND_SIG_URL,
            files={"file_a": (path_a.name, fa), "file_b": (path_b.name, fb)},
            timeout=60,
        )
    resp.raise_for_status()
    return resp.json()


def run_jobs(jobs: list[tuple[str, Path, Path]]) -> None:
    for name, path_a, path_b in jobs:
        print(f"Comparing: {path_a}  vs  {path_b}")
        result = compare_via_api(path_a, path_b)
        out_path = save_result(name, result)

        diff_count = result["summary"]["total_differences"]
        elapsed = result.get("elapsed_ms", 0)
        status = "SAME" if result["same"] else f"DIFF ({diff_count} change(s))"
        print(f"  Result : {status}")
        print(f"  Time   : {elapsed} ms")
        summary_ai = result.get("ai_summary")
        if summary_ai:
            preview = summary_ai[:400] + ("…" if len(summary_ai) > 400 else "")
            print(f"  AI     : {preview}")
        print(f"  Saved  : {out_path}")

        # Chạy thêm check chữ ký tay cho cùng cặp file.
        try:
            hand = _hand_signature_check(path_a, path_b)
            hand_path = OUTPUT_DIR / f"{name}_hand_signature.json"
            hand_path.write_text(
                json.dumps(hand, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(f"  HandSig: {hand_path}")
        except Exception as exc:
            print(f"  HandSig: ERROR ({exc})")

        print()


def main() -> None:
    args = parse_args()
    jobs = build_job_list(args)

    print(f"Found {len(jobs)} comparison(s) to run.\n")
    print("Starting API server...")

    server_env = {**os.environ, "COMPAREPDF_SKIP_DB_AUDIT": "1"}
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=server_env,
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
