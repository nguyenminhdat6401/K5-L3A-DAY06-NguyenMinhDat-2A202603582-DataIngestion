

import csv
import hashlib
import json
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]


def write_csv(path: Path, rows: list[dict]) -> None:
    # Never overwrite existing manual labels.
    if path.exists():
        raise FileExistsError(
            f"Review file already exists: {path}"
        )

    with path.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0]),
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    freeze_path = (
        REPO_DIR / "results" / "frozen" / "experiment.json"
    )
    frozen = json.loads(
        freeze_path.read_text(encoding="utf-8")
    )

    test_root = REPO_DIR / "results" / "test"
    runs = sorted(
        path
        for path in test_root.iterdir()
        if path.is_dir()
        and (path / "traces.jsonl").exists()
        and (path / "run_info.json").exists()
    )

    if not runs:
        raise ValueError("No completed test run found.")

    test_dir = runs[-1]
    run_info = json.loads(
        (test_dir / "run_info.json").read_text(
            encoding="utf-8"
        )
    )

    freeze_hash = hashlib.sha256(
        freeze_path.read_bytes()
    ).hexdigest()

    if run_info["freeze_file_sha256"] != freeze_hash:
        raise ValueError("Test run uses another experiment freeze.")

    traces = read_jsonl(test_dir / "traces.jsonl")

    if len(traces) != 15:
        raise ValueError("Expected 5 test questions x 3 strategies.")

    output_dir = (
        REPO_DIR / "results" / "manual" / test_dir.name
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    form_names = (
        "coherence.csv",
        "metadata.csv",
        "grounding.csv",
    )

    if any((output_dir / name).exists() for name in form_names):
        raise FileExistsError(
            "Audit forms already exist. Open the existing forms "
            "instead of overwriting manual work."
        )

    corpus = {
        (page["document_id"], page["page"]): page
        for page in read_jsonl(
            REPO_DIR / "data" / "corpus.jsonl"
        )
    }

    chunk_dir = REPO_DIR / "results" / "chunking"

    chunks_by_strategy = {
        strategy: read_jsonl(
            chunk_dir / f"chunks_{strategy}.jsonl"
        )
        for strategy in ("A", "B")
    }

    # C has exactly the same chunks as B.
    chunks_by_strategy["C"] = chunks_by_strategy["B"]

    coherence_rows = []

    for strategy in ("A", "B", "C"):
        for index, anchor in enumerate(
            frozen["coherence_anchors"], start=1
        ):
            position = anchor["char_position"]

            candidates = [
                chunk
                for chunk in chunks_by_strategy[strategy]
                if (
                    chunk["document_id"] == anchor["document_id"]
                    and chunk["page"] == anchor["page"]
                    and chunk["metadata"]["char_start"]
                    <= position
                    < chunk["metadata"]["char_end"]
                )
            ]

            if not candidates:
                raise ValueError("No chunk covers a sample anchor.")

            # Deterministic choice when overlap covers the same anchor:
            # use the covering chunk with earliest start offset.
            chosen = min(
                candidates,
                key=lambda chunk: (
                    chunk["metadata"]["char_start"],
                    chunk["chunk_id"],
                ),
            )

            page = corpus[
                (anchor["document_id"], anchor["page"])
            ]

            coherence_rows.append({
                "strategy": strategy,
                "anchor_id": f"a{index:02d}",
                "page": anchor["page"],
                "char_position": position,
                "chunk_id": chosen["chunk_id"],
                "chunk_text": chosen["text"],
                "source_context": page["text"][
                    max(0, position - 500):position + 500
                ],
                "score_0_1_2": "",
                "reason": "",
            })

    metadata_rows = []
    grounding_rows = []

    for trace in sorted(
        traces,
        key=lambda row: (
            row["strategy"], row["question_id"]
        ),
    ):
        question = trace["question"]
        top3_parts = []

        for rank, hit in enumerate(trace["hits"], start=1):
            source_page = corpus.get(
                (hit["document_id"], hit["page"])
            )

            metadata_rows.append({
                "strategy": trace["strategy"],
                "question_id": trace["question_id"],
                "rank": rank,
                "chunk_id": hit["chunk_id"],
                "document_id": hit["document_id"],
                "source": hit["source"],
                "page": hit["page"],
                "section": hit["metadata"].get("section", ""),
                "requested_filter": json.dumps(
                    trace["requested_filter"],
                    ensure_ascii=False,
                ),
                "applied_filter": json.dumps(
                    trace["applied_filter"],
                    ensure_ascii=False,
                ),
                "chunk_text": hit["text"],
                "source_page_text": (
                    source_page["text"] if source_page else ""
                ),
                "metadata_complete_and_correct_yes_no": "",
                "requested_filter_satisfied_yes_no_na": "",
                "reason": "",
            })

            top3_parts.append(
                f"RANK {rank} | PDF PAGE {hit['page']} "
                f"| SECTION {hit['metadata'].get('section', '')}\n"
                f"{hit['text']}"
            )

        grounding_rows.append({
            "strategy": trace["strategy"],
            "question_id": trace["question_id"],
            "question": question["question"],
            "expected_answer": question["expected_answer"],
            "gold_page": question["gold_page"],
            "gold_evidence": question["evidence_quote"],
            "top3_text": "\n\n".join(top3_parts),
            "auto_hit1": trace["hit1"],
            "auto_hit3": trace["hit3"],
            "score_0_1_2": "",
            "reason": "",
        })

    write_csv(output_dir / "coherence.csv", coherence_rows)
    write_csv(output_dir / "metadata.csv", metadata_rows)
    write_csv(output_dir / "grounding.csv", grounding_rows)

    method = {
        "test_run": test_dir.name,
        "freeze_file_sha256": freeze_hash,
        "coherence_sample": (
            "10 frozen source anchors per strategy; choose covering "
            "chunk with earliest char_start, then chunk_id."
        ),
        "coherence_rows": len(coherence_rows),
        "metadata_rows": len(metadata_rows),
        "grounding_rows": len(grounding_rows),
        "human_labels": "Blank; to be entered by the student.",
        "C_coherence": (
            "Same chunk text as B; equal coherence labels are expected "
            "when judged by the same criteria."
        ),
    }

    (output_dir / "audit_method.json").write_text(
        json.dumps(method, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Coherence rows: {len(coherence_rows)}")
    print(f"Metadata rows: {len(metadata_rows)}")
    print(f"Grounding rows: {len(grounding_rows)}")
    print(f"Audit directory: {output_dir}")


if __name__ == "__main__":
    main()