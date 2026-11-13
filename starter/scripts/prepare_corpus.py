"""Prepare a proposed corpus and source metadata for inspection."""

import csv
import json
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]
EXTRACTION_DIR = REPO_DIR / "results" / "extraction"


def main() -> None:
    input_path = EXTRACTION_DIR / "pages.jsonl"

    records = [
        json.loads(line)
        for line in input_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    pages_by_number = {record["page"]: record for record in records}

    # Physical PDF page numbers, inclusive.
    chapter_ranges = [
        (19, 37, "chapter_1", "An Introduction to Sociology"),
        (47, 66, "chapter_2", "Sociological Research"),
    ]

    selected = []

    for first, last, section, title in chapter_ranges:
        for page_number in range(first, last + 1):
            if page_number not in pages_by_number:
                raise ValueError(f"Missing extracted page: {page_number}")

            record = pages_by_number[page_number].copy()
            record["metadata"] = {
                **record.get("metadata", {}),
                "section": section,
                "section_title": title,
            }
            record["char_count"] = len(record["text"])
            selected.append(record)

    output_path = EXTRACTION_DIR / "corpus_candidate.jsonl"

    with output_path.open("w", encoding="utf-8") as file:
        for record in selected:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    inventory_path = EXTRACTION_DIR / "corpus_review.csv"

    # Preserve your review labels if you run this script again.
    if not inventory_path.exists():
        with inventory_path.open(
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
                writer.writerow({
                    "page": record["page"],
                    "section": record["metadata"]["section"],
                    "char_count": record["char_count"],
                    "useful_content_verified": "",
                    "notes": "",
                })

    print(f"Candidate pages: {len(selected)}")
    print(f"Total characters: {sum(p['char_count'] for p in selected)}")

    print("\nBOUNDARY CHECK")
    for number in (37, 38, 66, 67):
        record = pages_by_number.get(number)
        if record:
            print(f"\n--- PHYSICAL PDF PAGE {number} ---")
            print(record["text"][:650])

    print("\nLICENSE CHECK")
    found_license = False

    for record in records:
        if record["page"] > 18:
            continue

        text = record["text"]
        lower = text.lower()
        keywords = (
            "creative commons",
            "licensed under",
            "attribution",
        )

        positions = [
            lower.find(keyword)
            for keyword in keywords
            if keyword in lower
        ]

        if positions:
            found_license = True
            start = max(0, min(positions) - 150)
            print(f"\n--- PHYSICAL PDF PAGE {record['page']} ---")
            print(text[start:start + 2200])

    if not found_license:
        print("No license passage found automatically. Check the PDF manually.")

    print(f"\nCandidate corpus: {output_path}")
    print(f"Manual review table: {inventory_path}")
    print("These are proposed pages; verify their content before finalizing.")


if __name__ == "__main__":
    main()