
import csv
import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

STARTER_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = STARTER_DIR.parent

sys.path.insert(0, str(STARTER_DIR))

from src.embeddings import MyEmbedder
from src.evaluation import evaluate_query, summarize
from src.store import PgVectorStore


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]


def verify_database(
    store: PgVectorStore,
    strategy: str,
) -> None:
    """Compare live database rows with frozen chunk/vector files."""
    chunk_path = (
        REPO_DIR / "results" / "chunking"
        / f"chunks_{strategy}.jsonl"
    )
    vector_path = (
        REPO_DIR / "results" / "embeddings"
        / f"vectors_{strategy}.jsonl"
    )

    chunks = {
        row["chunk_id"]: row
        for row in read_jsonl(chunk_path)
    }
    vectors = {
        row["chunk_id"]: row["vector"]
        for row in read_jsonl(vector_path)
    }

    rows = store.connection.execute(
        """
        SELECT
            chunk_id, document_id, source, page,
            text, metadata, embedding::text
        FROM day6_chunks
        WHERE strategy = %s
        """,
        (strategy,),
    ).fetchall()

    if len(rows) != len(chunks):
        raise ValueError(
            f"{strategy}: database row count differs."
        )

    fields = (
        "chunk_id",
        "document_id",
        "source",
        "page",
        "text",
        "metadata",
    )

    for row in rows:
        chunk_id = row[0]

        if dict(zip(fields, row[:6])) != chunks.get(chunk_id):
            raise ValueError(
                f"{strategy}: stored chunk differs: {chunk_id}"
            )

        actual_vector = json.loads(row[6])
        expected_vector = vectors[chunk_id]

        if len(actual_vector) != len(expected_vector):
            raise ValueError("Stored vector dimension mismatch.")

        # pgvector stores float32, so allow rounding differences.
        if not all(
            math.isclose(
                actual,
                expected,
                rel_tol=1e-5,
                abs_tol=1e-7,
            )
            for actual, expected in zip(
                actual_vector, expected_vector
            )
        ):
            raise ValueError(
                f"{strategy}: stored vector differs: {chunk_id}"
            )


def main() -> None:
    freeze_path = (
        REPO_DIR / "results" / "frozen" / "experiment.json"
    )
    frozen = json.loads(
        freeze_path.read_text(encoding="utf-8")
    )

    # Stop if any tracked input/code has changed.
    for relative_path, expected_hash in frozen["file_hashes"].items():
        path = REPO_DIR / relative_path

        if not path.is_file():
            raise FileNotFoundError(
                f"Frozen file missing: {relative_path}"
            )

        if file_hash(path) != expected_hash:
            raise ValueError(
                f"Frozen file changed: {relative_path}. "
                "Review the change before evaluating test."
            )

    print("Frozen file checks: passed")

    questions = json.loads(
        (REPO_DIR / "benchmark" / "questions.json").read_text(
            encoding="utf-8"
        )
    )
    test_questions = [
        q for q in questions if q["split"] == "test"
    ]

    if len(test_questions) < 5:
        raise ValueError("Need at least five test questions.")

    if len({q["id"] for q in test_questions}) != len(test_questions):
        raise ValueError("Duplicate test question IDs.")

    if not any(q.get("filter") for q in test_questions):
        raise ValueError("Test must include a filter question.")

    info_path = (
        REPO_DIR / "results" / "embeddings"
        / "embedding_info.json"
    )
    info = json.loads(info_path.read_text(encoding="utf-8"))

    signature = (
        f"{info['model']}@{info['revision']}"
        f"|dimensions={info['dimensions']}"
        f"|prefix={info['document_prefix']}"
        f"|normalized={info['normalized_embeddings']}"
    )

    load_dotenv(STARTER_DIR / ".env")
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL missing.")

    store = PgVectorStore(
        database_url=database_url,
        dimensions=info["dimensions"],
        model_signature=signature,
    )

    try:
        store.create_schema()

        for strategy in ("A", "B"):
            verify_database(store, strategy)

        print("Database checks: passed")

        embedder = MyEmbedder(
            model_name=frozen["model"],
            revision=frozen["revision"],
        )

        if (
            embedder.revision != frozen["revision"]
            or embedder.dimensions != frozen["dimensions"]
        ):
            raise ValueError("Model snapshot/dimension mismatch.")

        traces = []
        query_embedding_seconds = 0.0

        for number, question in enumerate(test_questions, start=1):
            started = time.perf_counter()

            # Do not include gold answers/evidence in model input.
            query_vector = embedder.embed_query(
                question["question"]
            )

            query_embedding_seconds += (
                time.perf_counter() - started
            )

            for strategy in ("A", "B", "C"):
                applied_filter = (
                    question.get("filter", {})
                    if strategy == "C"
                    else {}
                )

                started = time.perf_counter()

                hits = store.search(
                    strategy=strategy,
                    query_vector=query_vector,
                    top_k=3,
                    filters=applied_filter,
                )

                elapsed = time.perf_counter() - started

                trace = evaluate_query(question, hits)
                trace.update({
                    "strategy": strategy,
                    "requested_filter": question.get(
                        "filter", {}
                    ),
                    "applied_filter": applied_filter,
                    "retrieval_seconds": elapsed,
                })
                traces.append(trace)

            print(
                f"Test {number}/{len(test_questions)}: "
                f"{question['id']} completed"
            )

        summary = summarize(traces)

        run_id = datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%S_%fZ"
        )
        output_dir = (
            REPO_DIR / "results" / "test" / run_id
        )
        output_dir.mkdir(parents=True, exist_ok=False)

        with (output_dir / "traces.jsonl").open(
            "w", encoding="utf-8"
        ) as file:
            for trace in traces:
                file.write(
                    json.dumps(
                        trace,
                        ensure_ascii=False,
                        allow_nan=False,
                    ) + "\n"
                )

        with (output_dir / "metrics.csv").open(
            "w", encoding="utf-8-sig", newline=""
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=list(summary[0]),
            )
            writer.writeheader()
            writer.writerows(summary)

        run_info = {
            "run_id": run_id,
            "split": "test",
            "question_count": len(test_questions),
            "trace_count": len(traces),
            "selected_strategy_from_dev": frozen[
                "selected_strategy"
            ],
            "freeze_file_sha256": file_hash(freeze_path),
            "model": frozen["model"],
            "revision": frozen["revision"],
            "dimensions": frozen["dimensions"],
            "metric": "cosine",
            "search": "exact",
            "top_k": 3,
            "query_embedding_seconds": round(
                query_embedding_seconds, 3
            ),
            "database_versions": store.versions(),
            "selection_changed_using_test": False,
        }

        (output_dir / "run_info.json").write_text(
            json.dumps(run_info, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print("\nTEST RESULTS")

        for row in summary:
            print(
                f"{row['strategy']}: "
                f"Hit@1 = {row['hit1_n']}/{row['n']} "
                f"({row['hit1']:.1%}); "
                f"Evidence Hit@3 = {row['hit3_n']}/{row['n']} "
                f"({row['hit3']:.1%})"
            )

        print(
            "\nSelected strategy remains:",
            frozen["selected_strategy"],
        )
        print(f"Saved to: {output_dir}")

    finally:
        store.close()


if __name__ == "__main__":
    main()