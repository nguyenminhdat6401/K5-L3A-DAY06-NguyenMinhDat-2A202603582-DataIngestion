"""Build the selected corpus and its provenance manifest."""

import csv
import hashlib
import json
from datetime import date
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]

SOURCE_URL = (
    "https://assets.openstax.org/oscms-prodcms/media/documents/"
    "IntroductiontoSociology3e-WEB_TZsroiv.pdf"
)

ATTRIBUTION = (
    "Introduction to Sociology 3e. OpenStax and its content contributors. "
    "Copyright 2021 Rice University. Licensed under CC BY 4.0. "
    "Access for free at openstax.org."
)

PAGE_RANGES = [
    (19, 37, "chapter_1", "An Introduction to Sociology"),
    (47, 67, "chapter_2", "Sociological Research"),
]


def save_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    data_dir = REPO_DIR / "data"
    extraction_dir = REPO_DIR / "results" / "extraction"

    pdf_path = data_dir / "sociology.pdf"

    records = [
        json.loads(line)
        for line in (
            extraction_dir / "pages.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    pages_by_number = {record["page"]: record for record in records}

    # Ensure the source PDF has not changed since extraction.
    extraction_summary = json.loads(
        (extraction_dir / "extraction_summary.json").read_text(
            encoding="utf-8"
        )
    )

    pdf_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()

    if pdf_hash != extraction_summary["sha256"]:
        raise ValueError(
            "PDF changed after extraction. Run extract_corpus.py again."
        )

    accessed_at = input(
        "Actual PDF download date (YYYY-MM-DD): "
    ).strip()
    date.fromisoformat(accessed_at)

    selected = []

    for first, last, section, title in PAGE_RANGES:
        for page_number in range(first, last + 1):
            if page_number not in pages_by_number:
                raise ValueError(f"Missing page: {page_number}")

            record = pages_by_number[page_number].copy()

            if not record["text"].strip():
                raise ValueError(f"Empty selected page: {page_number}")

            record["metadata"] = {
                **record.get("metadata", {}),
                "section": section,
                "section_title": title,
                "attribution": ATTRIBUTION,
            }
            record["char_count"] = len(record["text"])
            selected.append(record)

    included_pages = [record["page"] for record in selected]

    if len(included_pages) != len(set(included_pages)):
        raise ValueError("Duplicate selected pages.")

    if len(selected) < 30:
        raise ValueError("At least 30 content pages are required.")

    corpus_path = data_dir / "corpus.jsonl"

    with corpus_path.open("w", encoding="utf-8") as file:
        for record in selected:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    manifest = {
        "documents": [
            {
                "source_id": "openstax-sociology3e",
                "title": "Introduction to Sociology 3e",
                "path": "data/sociology.pdf",
                "source_path_or_url": SOURCE_URL,
                "license_or_permission": "CC BY 4.0",
                "license_url": (
                    "https://creativecommons.org/licenses/by/4.0/"
                ),
                "license_evidence_physical_pages": [4, 13],
                "attribution": ATTRIBUTION,
                "accessed_at": accessed_at,
                "sha256": pdf_hash,
                "physical_page_count": extraction_summary[
                    "physical_page_count"
                ],
                "included_pages": included_pages,
                "selected_page_count": len(selected),
                "counting_rule": (
                    "Physical PDF pages, numbered from 1. "
                    "Selected main-text ranges: 19-37 and 47-67. "
                    "Cover, contents and chapter-end review/reference "
                    "material outside these ranges are excluded."
                ),
                "metadata": {
                    "language": "en",
                    "document_type": "textbook",
                    "attribution": ATTRIBUTION,
                },
                "page_metadata": {
                    str(record["page"]): {
                        "section": record["metadata"]["section"],
                        "section_title": record["metadata"][
                            "section_title"
                        ],
                    }
                    for record in selected
                },
                "pages": [
                    {
                        "page": record["page"],
                        "char_count": record["char_count"],
                    }
                    for record in selected
                ],
                "manual_content_review": (
                    "Pending: see data/content_review.csv"
                ),
            }
        ]
    }

    save_json(data_dir / "manifest.json", manifest)

    review_path = data_dir / "content_review.csv"

    # Keep existing manual labels when rerunning.
    previous = {}
    if review_path.exists():
        with review_path.open(
            encoding="utf-8-sig", newline=""
        ) as file:
            previous = {
                int(row["page"]): row
                for row in csv.DictReader(file)
            }

    with review_path.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "page",
                "section",
                "char_count",
                "useful_content_verified",
                "notes",
            ],
        )
        writer.writeheader()

        for record in selected:
            old = previous.get(record["page"], {})
            writer.writerow({
                "page": record["page"],
                "section": record["metadata"]["section"],
                "char_count": record["char_count"],
                "useful_content_verified": old.get(
                    "useful_content_verified", ""
                ),
                "notes": old.get("notes", ""),
            })

    (data_dir / "ATTRIBUTION.txt").write_text(
        ATTRIBUTION + "\n\nSource: " + SOURCE_URL + "\n",
        encoding="utf-8",
    )

    print(f"\nSelected pages: {len(selected)}")
    print(
        "Normalized characters:",
        sum(record["char_count"] for record in selected),
    )

    for _, _, section, _ in PAGE_RANGES:
        count = sum(
            record["metadata"]["section"] == section
            for record in selected
        )
        print(f"{section}: {count} pages")

    print("\nCreated:")
    print("data/corpus.jsonl")
    print("data/manifest.json")
    print("data/content_review.csv")
    print("data/ATTRIBUTION.txt")
    print("\nManual content review is still pending.")


if __name__ == "__main__":
    main()