
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

STARTER_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = STARTER_DIR.parent

sys.path.insert(0, str(STARTER_DIR))

from src.models import Chunk
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


def main() -> None:
    load_dotenv(STARTER_DIR / ".env")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL missing in starter/.env.")

    chunk_dir = REPO_DIR / "results" / "chunking"
    embedding_dir = REPO_DIR / "results" / "embeddings"

    info_path = embedding_dir / "embedding_info.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))

    datasets = {}

    # Validate both strategies before changing database contents.
    for strategy in ("A", "B"):
        chunk_path = chunk_dir / f"chunks_{strategy}.jsonl"
        vector_path = embedding_dir / f"vectors_{strategy}.jsonl"
        expected = info["strategies"][strategy]

        if file_hash(chunk_path) != expected["chunk_file_sha256"]:
            raise ValueError(f"{strategy}: chunk file changed.")

        if file_hash(vector_path) != expected["vector_file_sha256"]:
            raise ValueError(f"{strategy}: vector file changed.")

        chunk_records = read_jsonl(chunk_path)
        vector_records = read_jsonl(vector_path)

        if len(chunk_records) != len(vector_records):
            raise ValueError(f"{strategy}: count mismatch.")

        if len(chunk_records) != expected["chunk_count"]:
            raise ValueError(f"{strategy}: unexpected chunk count.")

        chunks = []
        vectors = []

        for chunk_record, vector_record in zip(
            chunk_records, vector_records
        ):
            if (
                chunk_record["chunk_id"]
                != vector_record["chunk_id"]
            ):
                raise ValueError(f"{strategy}: chunk ID mismatch.")

            chunks.append(Chunk(**chunk_record))
            vectors.append(vector_record["vector"])

        datasets[strategy] = (chunks, vectors)

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

    results = []

    try:
        store.create_schema()

        for strategy, (chunks, vectors) in datasets.items():
            first_started = time.perf_counter()
            store.upsert(strategy, chunks, vectors)
            first_seconds = time.perf_counter() - first_started
            first_count = store.count(strategy)

            second_started = time.perf_counter()
            store.upsert(strategy, chunks, vectors)
            second_seconds = time.perf_counter() - second_started
            second_count = store.count(strategy)

            if first_count != len(chunks) or second_count != len(chunks):
                raise ValueError(
                    f"{strategy}: repeated ingestion count mismatch."
                )

            results.append({
                "strategy": strategy,
                "expected_count": len(chunks),
                "first_count": first_count,
                "second_count": second_count,
                "first_store_seconds": round(first_seconds, 3),
                "second_store_seconds": round(second_seconds, 3),
                "embedding_seconds": info["strategies"][
                    strategy
                ]["embedding_seconds"],
                "repeat_ingestion_passed": True,
            })

            print(
                f"{strategy}: first={first_count}, "
                f"second={second_count}, "
                "duplicate check passed"
            )

        report = {
            "run_at_utc": datetime.now(timezone.utc).isoformat(),
            "versions": store.versions(),
            "model_signature": signature,
            "embedding_info_sha256": file_hash(info_path),
            "metric": "cosine",
            "search": "exact; no approximate vector index",
            "update_policy": (
                "Atomic full replacement per strategy; "
                "obsolete chunks are removed."
            ),
            "results": results,
            "C": "Shares stored B chunks and vectors.",
        }

        output_dir = REPO_DIR / "results" / "storage"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Keep a separate log for each run.
        run_id = datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%S_%fZ"
        )
        output_path = output_dir / f"ingestion_{run_id}.json"

        output_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print("C: reuses B storage.")
        print(f"Saved ingestion evidence: {output_path}")

    finally:
        store.close()


if __name__ == "__main__":
    main()