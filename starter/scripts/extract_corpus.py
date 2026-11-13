"""Extract corpus text and page inventory for manual inspection."""

import csv
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

STARTER_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = STARTER_DIR.parent

sys.path.insert(0, str(STARTER_DIR))

from pypdf import PdfReader
from src.ingestion import load_pdf


def main() -> None:
    pdf_path = REPO_DIR / "data" / "sociology.pdf"
    output_dir = REPO_DIR / "results" / "extraction"
    output_dir.mkdir(parents=True, exist_ok=True)

    errors = []

    print("Extracting PDF. Please wait...")

    pages = load_pdf(
        path=pdf_path,
        document_id="openstax-sociology3e",
        source=(
            "https://assets.openstax.org/oscms-prodcms/media/documents/"
            "IntroductiontoSociology3e-WEB_TZsroiv.pdf"
        ),
        errors=errors,
    )

    with (output_dir / "pages.jsonl").open(
        "w", encoding="utf-8"
    ) as file:
        for page in pages:
            record = asdict(page)
            record["char_count"] = len(page.text)
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    with (output_dir / "page_inventory.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "page",
                "char_count",
                "preview",
                "include",
                "section",
                "exclusion_reason",
            ],
        )
        writer.writeheader()

        for page in pages:
            writer.writerow(
                {
                    "page": page.page,
                    "char_count": len(page.text),
                    "preview": page.text[:180].replace("\n", " "),
                    "include": "",
                    "section": "",
                    "exclusion_reason": "",
                }
            )

    with (output_dir / "pages_preview.txt").open(
        "w", encoding="utf-8"
    ) as file:
        for page in pages:
            file.write(
                f"\n{'=' * 70}\n"
                f"PHYSICAL PDF PAGE {page.page}\n"
                f"{'=' * 70}\n"
            )
            file.write(page.text + "\n")

    (output_dir / "extraction_errors.json").write_text(
        json.dumps(errors, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        "physical_page_count": len(PdfReader(pdf_path).pages),
        "readable_page_count": len(pages),
        "error_page_count": len(errors),
        "total_normalized_characters": sum(
            len(page.text) for page in pages
        ),
    }

    (output_dir / "extraction_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved files to: {output_dir}")


if __name__ == "__main__":
    main()