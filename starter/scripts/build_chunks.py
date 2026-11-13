"""Build A/B chunks and record their configurations and statistics."""

import csv
import json
import statistics
import sys
from dataclasses import asdict
from pathlib import Path

STARTER_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = STARTER_DIR.parent

sys.path.insert(0, str(STARTER_DIR))

from src.chunking import by_paragraph, fixed_size
from src.models import DocumentPage


def main() -> None:
    data_dir = REPO_DIR / "data"
    output_dir = REPO_DIR / "results" / "chunking"
    output_dir.mkdir(parents=True, exist_ok=True)

    records = [
        json.loads(line)
        for line in (
            data_dir / "corpus.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    # Require real review labels before processing the corpus.
    with (data_dir / "content_review.csv").open(
        encoding="utf-8-sig", newline=""
    ) as file:
        reviews = list(csv.DictReader(file))

    review_by_page = {
        int(row["page"]): row for row in reviews
    }

    for record in records:
        review = review_by_page.get(record["page"], {})

        if review.get(
            "useful_content_verified", ""
        ).strip().lower() != "yes":
            raise ValueError(
                f"Page {record['page']} has not been verified."
            )

    pages = [
        DocumentPage(
            document_id=record["document_id"],
            source=record["source"],
            page=record["page"],
            text=record["text"],
            metadata=record["metadata"],
        )
        for record in records
    ]

    if len(pages) < 30:
        raise ValueError("Need at least 30 verified pages.")

    strategies = {
        "A": {
            "method": "fixed_size",
            "size": 500,
            "overlap": 50,
            "filter_enabled": False,
        },
        "B": {
            "method": "by_paragraph",
            "max_size": 900,
            "filter_enabled": False,
        },
        "C": {
            "same_chunks_as": "B",
            "filter_enabled": True,
        },
    }

    statistics_rows = []

    for strategy in ("A", "B"):
        chunks = []

        for page in pages:
            if strategy == "A":
                page_chunks = fixed_size(
                    page,
                    size=strategies["A"]["size"],
                    overlap=strategies["A"]["overlap"],
                )
                limit = strategies["A"]["size"]

            else:
                page_chunks = by_paragraph(
                    page,
                    max_size=strategies["B"]["max_size"],
                )
                limit = strategies["B"]["max_size"]

                if "".join(
                    chunk.text for chunk in page_chunks
                ) != page.text:
                    raise ValueError(
                        f"B lost text on page {page.page}."
                    )

            for chunk in page_chunks:
                start = chunk.metadata["char_start"]
                end = chunk.metadata["char_end"]

                if chunk.text != page.text[start:end]:
                    raise ValueError("Source offset mismatch.")

                if not 0 < len(chunk.text) <= limit:
                    raise ValueError("Invalid chunk length.")

            chunks.extend(page_chunks)

        if len({c.chunk_id for c in chunks}) != len(chunks):
            raise ValueError("Duplicate chunk IDs.")

        output_path = output_dir / f"chunks_{strategy}.jsonl"

        with output_path.open("w", encoding="utf-8") as file:
            for chunk in chunks:
                file.write(
                    json.dumps(
                        asdict(chunk), ensure_ascii=False
                    ) + "\n"
                )

        lengths = [len(chunk.text) for chunk in chunks]

        row = {
            "strategy": strategy,
            "page_count": len(pages),
            "chunk_count": len(chunks),
            "min_chars": min(lengths),
            "median_chars": statistics.median(lengths),
            "mean_chars": round(statistics.mean(lengths), 2),
            "max_chars": max(lengths),
            "total_chunk_chars": sum(lengths),
        }

        statistics_rows.append(row)
        print(json.dumps(row, ensure_ascii=False, indent=2))

    with (output_dir / "chunk_stats.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(statistics_rows[0]),
        )
        writer.writeheader()
        writer.writerows(statistics_rows)

    (output_dir / "strategies.json").write_text(
        json.dumps(strategies, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\nC will reuse B chunks; only retrieval filtering changes.")
    print(f"Saved to: {output_dir}")


if __name__ == "__main__":
    main()