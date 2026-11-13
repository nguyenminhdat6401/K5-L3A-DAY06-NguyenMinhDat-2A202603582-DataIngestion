
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

STARTER_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = STARTER_DIR.parent

sys.path.insert(0, str(STARTER_DIR))

from src.evaluation import summarize


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
    output_dir = REPO_DIR / "results" / "frozen"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "experiment.json"

    if output_path.exists():
        raise FileExistsError(
            "Experiment already frozen. Do not overwrite after test."
        )

    dev_root = REPO_DIR / "results" / "dev"
    dev_runs = sorted(
        path
        for path in dev_root.iterdir()
        if path.is_dir()
        and (path / "traces.jsonl").exists()
        and (path / "run_info.json").exists()
    )

    if not dev_runs:
        raise ValueError("No completed dev run found.")

    dev_dir = dev_runs[-1]
    traces = read_jsonl(dev_dir / "traces.jsonl")

    if any(trace["split"] != "dev" for trace in traces):
        raise ValueError("Selection must use dev traces only.")

    summary = summarize(traces)

    if {row["strategy"] for row in summary} != {"A", "B", "C"}:
        raise ValueError("Need dev results for all three strategies.")

    questions_path = REPO_DIR / "benchmark" / "questions.json"
    protocol_path = REPO_DIR / "benchmark" / "protocol.json"
    info_path = (
        REPO_DIR / "results" / "embeddings"
        / "embedding_info.json"
    )

    protocol = json.loads(
        protocol_path.read_text(encoding="utf-8")
    )
    info = json.loads(info_path.read_text(encoding="utf-8"))
    dev_info = json.loads(
        (dev_dir / "run_info.json").read_text(encoding="utf-8")
    )

    benchmark_hash = file_hash(questions_path)

    if not (
        benchmark_hash
        == protocol["benchmark_sha256"]
        == info["benchmark_sha256"]
        == dev_info["benchmark_sha256"]
    ):
        raise ValueError("Benchmark versions do not match.")

    if file_hash(info_path) != dev_info["embedding_info_sha256"]:
        raise ValueError("Embedding metadata changed after dev.")

    questions = json.loads(
        questions_path.read_text(encoding="utf-8")
    )
    expected_dev_ids = {
        q["id"] for q in questions if q["split"] == "dev"
    }

    for strategy in ("A", "B", "C"):
        ids = [
            trace["question_id"]
            for trace in traces
            if trace["strategy"] == strategy
        ]

        if len(ids) != len(set(ids)) or set(ids) != expected_dev_ids:
            raise ValueError(
                f"{strategy}: missing or duplicate dev traces."
            )

    # Implement the previously recorded tie-breaking rule.
    preference = {"B": 0, "A": 1, "C": 2}

    def ranking(row: dict) -> tuple:
        storage_strategy = (
            "B" if row["strategy"] == "C" else row["strategy"]
        )
        chunk_count = info["strategies"][
            storage_strategy
        ]["chunk_count"]

        return (
            -row["hit3"],
            -row["hit1"],
            chunk_count,
            preference[row["strategy"]],
        )

    selected = min(summary, key=ranking)["strategy"]

    tracked_files = [
        questions_path,
        protocol_path,
        REPO_DIR / "benchmark" / "review.csv",
        REPO_DIR / "data" / "manifest.json",
        REPO_DIR / "data" / "corpus.jsonl",
        REPO_DIR / "data" / "content_review.csv",
        info_path,
        REPO_DIR / "results" / "chunking" / "strategies.json",
        dev_dir / "traces.jsonl",
        dev_dir / "run_info.json",
    ]

    for strategy in ("A", "B"):
        chunk_path = (
            REPO_DIR / "results" / "chunking"
            / f"chunks_{strategy}.jsonl"
        )
        vector_path = (
            REPO_DIR / "results" / "embeddings"
            / f"vectors_{strategy}.jsonl"
        )

        expected = info["strategies"][strategy]

        if file_hash(chunk_path) != expected["chunk_file_sha256"]:
            raise ValueError(f"{strategy}: chunks changed.")

        if file_hash(vector_path) != expected["vector_file_sha256"]:
            raise ValueError(f"{strategy}: vectors changed.")

        tracked_files.extend([chunk_path, vector_path])

    tracked_files.extend(
        sorted((STARTER_DIR / "src").glob("*.py"))
    )

    corpus = read_jsonl(REPO_DIR / "data" / "corpus.jsonl")

    # Fix coherence sample locations before assigning manual scores:
    # first five PDF pages of each chapter, midpoint of each page.
    anchors = []

    for section in ("chapter_1", "chapter_2"):
        section_pages = sorted(
            (
                page for page in corpus
                if page["metadata"]["section"] == section
            ),
            key=lambda page: page["page"],
        )

        if len(section_pages) < 5:
            raise ValueError("Need five sample pages per chapter.")

        for page in section_pages[:5]:
            anchors.append({
                "document_id": page["document_id"],
                "page": page["page"],
                "char_position": len(page["text"]) // 2,
            })

    frozen = {
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "selected_strategy": selected,
        "selection_rule": protocol["selection_rule"],
        "dev_run": str(dev_dir.relative_to(REPO_DIR)),
        "dev_metrics": summary,
        "model": info["model"],
        "revision": info["revision"],
        "dimensions": info["dimensions"],
        "coherence_anchors": anchors,
        "file_hashes": {
            path.relative_to(REPO_DIR).as_posix(): file_hash(path)
            for path in tracked_files
        },
        "test_policy": (
            "Evaluate all A/B/C on test without changing "
            "the recorded dev-based selection."
        ),
    }

    output_path.write_text(
        json.dumps(frozen, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Selected strategy: {selected}")
    print(f"Dev run: {dev_dir.name}")
    print(f"Coherence sample locations: {len(anchors)}")
    print(f"Saved experiment freeze: {output_path}")
    print("Test retrieval has not been run by this script.")


if __name__ == "__main__":
    main()