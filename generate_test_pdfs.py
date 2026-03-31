"""Generate sample PDF pairs in localPDF/ for local testing."""

import fitz

LOCAL_PDF_DIR = "localPDF"


def create_pdf(path: str, pages: list[str]) -> None:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=12)
    doc.save(path)
    doc.close()
    print(f"  Created: {path}")


def main() -> None:
    print("Generating test PDFs...\n")

    # Pair 1: minor text differences on page 2
    create_pdf(f"{LOCAL_PDF_DIR}/sample1_a.pdf", [
        "Introduction\nWelcome to the PDF Compare tool.\nVersion 1.0",
        "Chapter 1\nThis chapter covers the basics.\nAll content is identical.",
        "Summary\nThank you for reading.",
    ])
    create_pdf(f"{LOCAL_PDF_DIR}/sample1_b.pdf", [
        "Introduction\nWelcome to the PDF Compare tool.\nVersion 1.0",
        "Chapter 1\nThis chapter covers the fundamentals.\nAll content is identical.",
        "Summary\nThank you for reading.",
    ])
    print("  -> Pair 1: same page count, diff on page 2\n")

    # Pair 2: file B has an extra page
    create_pdf(f"{LOCAL_PDF_DIR}/sample2_a.pdf", [
        "Report Title\nQuarterly Revenue Report\nQ1 2025",
        "Revenue: $1,000,000\nExpenses: $750,000\nProfit: $250,000",
    ])
    create_pdf(f"{LOCAL_PDF_DIR}/sample2_b.pdf", [
        "Report Title\nQuarterly Revenue Report\nQ1 2025",
        "Revenue: $1,200,000\nExpenses: $800,000\nProfit: $400,000",
        "Appendix\nDetailed breakdown attached.",
    ])
    print("  -> Pair 2: different page count + content diff\n")

    # Pair 3: identical files
    create_pdf(f"{LOCAL_PDF_DIR}/sample3_a.pdf", [
        "Identical Document\nLine one\nLine two\nLine three",
    ])
    create_pdf(f"{LOCAL_PDF_DIR}/sample3_b.pdf", [
        "Identical Document\nLine one\nLine two\nLine three",
    ])
    print("  -> Pair 3: identical files\n")

    print("Done! PDFs are in localPDF/")


if __name__ == "__main__":
    main()
