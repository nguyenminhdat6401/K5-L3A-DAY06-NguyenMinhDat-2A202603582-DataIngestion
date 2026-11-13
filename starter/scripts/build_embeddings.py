"""Embed A/B chunks with one model snapshot and record run metadata."""

import csv
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

STARTER_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = STARTER_DIR.parent

sys.path.insert(0, str(STARTER_DIR))

from src.embeddings import MyEmbedder


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    benchmark_dir = REPO_DIR / "benchmark"

    questions_path = benchmark_dir / "questions.json"
    questions = json.loads(
        questions_path.read_text(encoding="utf-8")
    )

    with (benchmark_dir / "review.csv").open(
        encoding="utf-8-sig", newline=""
    ) as file:
        reviews = list(csv.DictReader(file))

    if len(reviews) != len(questions):
        raise ValueError("Review row count does not match benchmark.")

    review_by_id = {row["id"]: row for row in reviews}

    if len(review_by_id) != len(reviews):
        raise ValueError("Duplicate IDs in review.csv.")

    for question in questions:
        review = review_by_id.get(question["id"], {})

        if review.get("verified", "").strip().lower() != "yes":
            raise ValueError(
                f"Question {question['id']} is not verified."
            )

    protocol_path = benchmark_dir / "protocol.json"
    protocol = json.loads(
        protocol_path.read_text(encoding="utf-8")
    )

    if file_hash(questions_path) != protocol["benchmark_sha256"]:
        raise ValueError(
            "Benchmark changed after protocol creation. "
            "Review the change before continuing."
        )

    chunk_dir = REPO_DIR / "results" / "chunking"
    output_dir = REPO_DIR / "results" / "embeddings"
    output_dir.mkdir(parents=True, exist_ok=True)

    info_path = output_dir / "embedding_info.json"

    if info_path.exists():
        raise FileExistsError(
            "Embedding results already exist. "
            "Keep them for reproducibility; do not overwrite casually."
        )

    started_at = datetime.now(timezone.utc).isoformat()

    print("Loading model. The first run downloads model files...")
    load_started = time.perf_counter()

    embedder = MyEmbedder()

    if not embedder.revision:
        raise RuntimeError(
            "Cannot identify the downloaded model snapshot revision."
        )

    model_load_seconds = time.perf_counter() - load_started

    strategy_results = {}

    for strategy in ("A", "B"):
        chunk_path = chunk_dir / f"chunks_{strategy}.jsonl"

        chunks = [
            json.loads(line)
            for line in chunk_path.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]

        if not chunks:
            raise ValueError(f"No chunks for strategy {strategy}.")

        print(f"\nEmbedding {strategy}: {len(chunks)} chunks")

        started = time.perf_counter()

        vectors = embedder.embed_documents(
            [chunk["text"] for chunk in chunks]
        )

        elapsed = time.perf_counter() - started

        if len(vectors) != len(chunks):
            raise ValueError("Vector count does not match chunk count.")

        vector_path = output_dir / f"vectors_{strategy}.jsonl"
        temporary_path = vector_path.with_suffix(".jsonl.tmp")

        with temporary_path.open("w", encoding="utf-8") as file:
            for chunk, vector in zip(chunks, vectors):
                if len(vector) != embedder.dimensions:
                    raise ValueError("Incorrect vector dimension.")

                file.write(
                    json.dumps(
                        {
                            "chunk_id": chunk["chunk_id"],
                            "vector": vector,
                        },
                        ensure_ascii=False,
                        allow_nan=False,
                    ) + "\n"
                )

        temporary_path.replace(vector_path)

        strategy_results[strategy] = {
            "chunk_count": len(chunks),
            "embedding_seconds": round(elapsed, 3),
            "chunk_file_sha256": file_hash(chunk_path),
            "vector_file_sha256": file_hash(vector_path),
        }

        print(
            f"{strategy}: {len(vectors)} vectors, "
            f"{embedder.dimensions} dimensions, "
            f"{elapsed:.2f} seconds"
        )

    info = {
        "started_at_utc": started_at,
        "provider": "local sentence-transformers",
        "model": embedder.model_name,
        "revision": embedder.revision,
        "dimensions": embedder.dimensions,
        "device": "cpu",
        "document_prefix": "passage: ",
        "query_prefix": "query: ",
        "normalized_embeddings": True,
        "model_load_seconds": round(model_load_seconds, 3),
        "paid_api_cost": 0,
        "cost_note": "Local execution; electricity/hardware not priced.",
        "sentence_transformers_version": version(
            "sentence-transformers"
        ),
        "torch_version": version("torch"),
        "benchmark_sha256": file_hash(questions_path),
        "strategies": strategy_results,
        "C": "Reuse B chunks and vectors; apply query filters later.",
    }

    info_path.write_text(
        json.dumps(info, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\nEmbedding completed.")
    print(f"Model revision: {embedder.revision}")
    print(f"Metadata saved to: {info_path}")


if __name__ == "__main__":
    main()