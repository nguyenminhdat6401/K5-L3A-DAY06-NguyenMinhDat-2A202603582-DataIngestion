"""Suggested pipeline entry point; TODO: implement the orchestration."""


import csv
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from .embeddings import MyEmbedder
from .evaluation import evaluate_query, summarize
from .store import PgVectorStore

STARTER_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = STARTER_DIR.parent


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


def main() -> None:
    load_dotenv(STARTER_DIR / ".env")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is missing.")

    benchmark_dir = REPO_DIR / "benchmark"
    questions_path = benchmark_dir / "questions.json"

    all_questions = json.loads(
        questions_path.read_text(encoding="utf-8")
    )

    info_path = (
        REPO_DIR
        / "results"
        / "embeddings"
        / "embedding_info.json"
    )
    info = json.loads(info_path.read_text(encoding="utf-8"))

    if file_hash(questions_path) != info["benchmark_sha256"]:
        raise ValueError(
            "Benchmark changed after embedding preparation."
        )

    # Run dev only. Test retrieval is intentionally excluded here.
    questions = [
        question
        for question in all_questions
        if question["split"] == "dev"
    ]

    if len(questions) < 15:
        raise ValueError("Need at least 15 dev questions.")

    if len({q["id"] for q in questions}) != len(questions):
        raise ValueError("Duplicate dev question IDs.")

    signature = (
        f"{info['model']}@{info['revision']}"
        f"|dimensions={info['dimensions']}"
        f"|prefix={info['document_prefix']}"
        f"|normalized={info['normalized_embeddings']}"
    )

    store = PgVectorStore(
        database_url=database_url,
        dimensions=info["dimensions"],
        model_signature=signature,
    )

    try:
        store.create_schema()

        # Verify current chunks and stored source text/metadata.
        for strategy in ("A", "B"):
            chunk_path = (
                REPO_DIR
                / "results"
                / "chunking"
                / f"chunks_{strategy}.jsonl"
            )

            expected = info["strategies"][strategy]

            if file_hash(chunk_path) != expected["chunk_file_sha256"]:
                raise ValueError(
                    f"{strategy}: chunk file changed."
                )

            chunks = read_jsonl(chunk_path)

            rows = store.connection.execute(
                """
                SELECT
                    chunk_id, document_id, source,
                    page, text, metadata
                FROM day6_chunks
                WHERE strategy = %s
                """,
                (strategy,),
            ).fetchall()

            fields = (
                "chunk_id",
                "document_id",
                "source",
                "page",
                "text",
                "metadata",
            )

            stored = {
                row[0]: dict(zip(fields, row))
                for row in rows
            }

            expected_chunks = {
                chunk["chunk_id"]: chunk
                for chunk in chunks
            }

            if stored != expected_chunks:
                raise ValueError(
                    f"{strategy}: database differs from chunk files. "
                    "Check ingestion before retrieval."
                )

        print("Loading the recorded model snapshot...")

        embedder = MyEmbedder(
            model_name=info["model"],
            revision=info["revision"],
        )

        if embedder.revision != info["revision"]:
            raise ValueError("Model snapshot mismatch.")

        traces = []
        query_embedding_seconds = 0.0

        for number, question in enumerate(questions, start=1):
            started = time.perf_counter()

            # Only question text enters the embedding model.
            # Gold answer, page and evidence are not query inputs.
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

                retrieval_seconds = (
                    time.perf_counter() - started
                )

                trace = evaluate_query(question, hits)

                trace.update({
                    "strategy": strategy,
                    "requested_filter": question.get(
                        "filter", {}
                    ),
                    "applied_filter": applied_filter,
                    "retrieval_seconds": retrieval_seconds,
                })

                traces.append(trace)

            print(
                f"Dev {number}/{len(questions)}: "
                f"{question['id']} completed"
            )

        summary = summarize(traces)

        run_id = datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%S_%fZ"
        )
        output_dir = (
            REPO_DIR / "results" / "dev" / run_id
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

        protocol = json.loads(
            (benchmark_dir / "protocol.json").read_text(
                encoding="utf-8"
            )
        )

        run_info = {
            "run_id": run_id,
            "split": "dev",
            "question_count": len(questions),
            "trace_count": len(traces),
            "model": info["model"],
            "revision": info["revision"],
            "dimensions": info["dimensions"],
            "metric": "cosine",
            "search": "exact",
            "top_k": 3,
            "query_embedding_seconds": round(
                query_embedding_seconds, 3
            ),
            "benchmark_sha256": file_hash(questions_path),
            "embedding_info_sha256": file_hash(info_path),
            "selection_rule": protocol["selection_rule"],
            "test_retrieval_executed": False,
        }

        (output_dir / "run_info.json").write_text(
            json.dumps(run_info, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print("\nDEV RESULTS")

        for row in summary:
            print(
                f"{row['strategy']}: "
                f"Hit@1 = {row['hit1_n']}/{row['n']} "
                f"({row['hit1']:.1%}); "
                f"Evidence Hit@3 = {row['hit3_n']}/{row['n']} "
                f"({row['hit3']:.1%})"
            )

        print(f"\nSaved to: {output_dir}")
        print("Test retrieval has not been run.")

    finally:
        store.close()


if __name__ == "__main__":
    main()

