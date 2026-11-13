

import csv
import hashlib
import json
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        first_line = file.readline()
        file.seek(0)

        dialect = csv.Sniffer().sniff(
            first_line, delimiters=",;\t"
        )
        return list(csv.DictReader(file, dialect=dialect))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=list(rows[0])
        )
        writer.writeheader()
        writer.writerows(rows)


def validate_scores(rows: list[dict], name: str) -> None:
    for row in rows:
        score = row["score_0_1_2"].strip()

        if score not in {"0", "1", "2"}:
            raise ValueError(
                f"{name}: invalid or missing score: "
                f"{row['strategy']} / "
                f"{row.get('anchor_id', row.get('question_id'))}"
            )

        if not row["reason"].strip():
            raise ValueError(f"{name}: missing reason.")


def validate_keys(
    rows: list[dict],
    columns: tuple,
    expected: set,
    name: str,
) -> None:
    keys = [
        tuple(row[column] for column in columns)
        for row in rows
    ]

    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError(
            f"{name}: missing, duplicate or unexpected rows."
        )


def main() -> None:
    frozen_path = (
        REPO_DIR / "results" / "frozen" / "experiment.json"
    )
    frozen = json.loads(
        frozen_path.read_text(encoding="utf-8")
    )

    test_runs = sorted(
        path
        for path in (REPO_DIR / "results" / "test").iterdir()
        if path.is_dir()
        and (path / "run_info.json").exists()
        and (path / "metrics.csv").exists()
    )

    if not test_runs:
        raise ValueError("No completed test run.")

    test_dir = test_runs[-1]
    test_info = json.loads(
        (test_dir / "run_info.json").read_text(
            encoding="utf-8"
        )
    )

    freeze_hash = hashlib.sha256(
        frozen_path.read_bytes()
    ).hexdigest()

    if test_info["freeze_file_sha256"] != freeze_hash:
        raise ValueError("Test and frozen experiment differ.")

    manual_dir = (
        REPO_DIR / "results" / "manual" / test_dir.name
    )

    coherence = read_csv(manual_dir / "coherence.csv")
    metadata = read_csv(manual_dir / "metadata.csv")
    grounding = read_csv(manual_dir / "grounding.csv")

    questions = json.loads(
        (REPO_DIR / "benchmark" / "questions.json").read_text(
            encoding="utf-8"
        )
    )
    test_questions = {
        q["id"]: q
        for q in questions
        if q["split"] == "test"
    }

    strategies = ("A", "B", "C")
    anchor_ids = {
        f"a{index:02d}"
        for index in range(
            1, len(frozen["coherence_anchors"]) + 1
        )
    }

    validate_keys(
        coherence,
        ("strategy", "anchor_id"),
        {
            (strategy, anchor)
            for strategy in strategies
            for anchor in anchor_ids
        },
        "coherence",
    )

    validate_keys(
        grounding,
        ("strategy", "question_id"),
        {
            (strategy, question_id)
            for strategy in strategies
            for question_id in test_questions
        },
        "grounding",
    )

    validate_keys(
        metadata,
        ("strategy", "question_id", "rank"),
        {
            (strategy, question_id, str(rank))
            for strategy in strategies
            for question_id in test_questions
            for rank in (1, 2, 3)
        },
        "metadata",
    )

    validate_scores(coherence, "coherence")
    validate_scores(grounding, "grounding")

    for row in metadata:
        correct = row[
            "metadata_complete_and_correct_yes_no"
        ].strip().lower()

        satisfied = row[
            "requested_filter_satisfied_yes_no_na"
        ].strip().lower()

        if correct not in {"yes", "no"}:
            raise ValueError("Invalid metadata correctness label.")

        has_filter = bool(
            test_questions[row["question_id"]].get("filter")
        )

        allowed = {"yes", "no"} if has_filter else {"na"}

        if satisfied not in allowed:
            raise ValueError(
                "Invalid filter label for "
                f"{row['strategy']}/{row['question_id']}/"
                f"{row['rank']}"
            )

        if not row["reason"].strip():
            raise ValueError("Metadata reason is missing.")

    audit_summary = []

    filter_ids = [
        question_id
        for question_id, question in test_questions.items()
        if question.get("filter")
    ]

    for strategy in strategies:
        coherence_scores = [
            int(row["score_0_1_2"])
            for row in coherence
            if row["strategy"] == strategy
        ]

        grounding_scores = [
            int(row["score_0_1_2"])
            for row in grounding
            if row["strategy"] == strategy
        ]

        metadata_rows = [
            row for row in metadata
            if row["strategy"] == strategy
        ]

        correct_count = sum(
            row["metadata_complete_and_correct_yes_no"]
            .strip().lower() == "yes"
            for row in metadata_rows
        )

        # Count QUESTIONS whose entire top-3 satisfies the filter.
        filter_pass_count = 0

        for question_id in filter_ids:
            hits = [
                row for row in metadata_rows
                if row["question_id"] == question_id
            ]

            if len(hits) == 3 and all(
                row["requested_filter_satisfied_yes_no_na"]
                .strip().lower() == "yes"
                for row in hits
            ):
                filter_pass_count += 1

        audit_summary.append({
            "strategy": strategy,
            "coherence_mean_out_of_2": round(
                sum(coherence_scores) / len(coherence_scores), 3
            ),
            "coherence_n": len(coherence_scores),
            "metadata_correct_n": correct_count,
            "metadata_checked_n": len(metadata_rows),
            "filter_questions_pass_n": filter_pass_count,
            "filter_questions_n": len(filter_ids),
            "grounding_score_0_n": grounding_scores.count(0),
            "grounding_score_1_n": grounding_scores.count(1),
            "grounding_score_2_n": grounding_scores.count(2),
            "grounding_mean_out_of_2": round(
                sum(grounding_scores) / len(grounding_scores), 3
            ),
            "grounding_n": len(grounding_scores),
        })

    dev_metrics = frozen["dev_metrics"]
    test_metrics = read_csv(test_dir / "metrics.csv")
    retrieval_summary = []

    for row in [*dev_metrics, *test_metrics]:
        n = int(row["n"])
        hit1 = int(row["hit1_n"])
        hit3 = int(row["hit3_n"])

        retrieval_summary.append({
            "strategy": row["strategy"],
            "split": row["split"],
            "hit1_n": hit1,
            "hit3_n": hit3,
            "n": n,
            "hit1_percent": round(100 * hit1 / n, 2),
            "hit3_percent": round(100 * hit3 / n, 2),
        })

    chunk_stats = read_csv(
        REPO_DIR / "results" / "chunking" / "chunk_stats.csv"
    )
    stats_by_strategy = {
        row["strategy"]: row for row in chunk_stats
    }

    output_dir = REPO_DIR / "results" / "summary"
    output_dir.mkdir(parents=True, exist_ok=True)

    write_csv(
        output_dir / "retrieval_summary.csv",
        retrieval_summary,
    )
    write_csv(
        output_dir / "audit_summary.csv",
        audit_summary,
    )

    lines = [
        "# Experiment results",
        "",
        f"Selected on dev: **{frozen['selected_strategy']}**",
        "",
        "## Retrieval",
        "",
        "| Strategy | Split | Hit@1 | Evidence Hit@3 |",
        "|---|---|---|---|",
    ]

    for row in retrieval_summary:
        lines.append(
            f"| {row['strategy']} | {row['split']} | "
            f"{row['hit1_n']}/{row['n']} "
            f"({row['hit1_percent']:.1f}%) | "
            f"{row['hit3_n']}/{row['n']} "
            f"({row['hit3_percent']:.1f}%) |"
        )

    lines.extend([
        "",
        "## Reviewed audit labels",
        "",
        "| Strategy | Coherence /2 | Metadata correct | "
        "Filter questions passed | Grounding 0/1/2 counts | "
        "Grounding /2 | Chunks |",
        "|---|---|---|---|---|---|---|",
    ])

    for row in audit_summary:
        strategy = row["strategy"]
        stored_strategy = "B" if strategy == "C" else strategy

        filter_result = (
            f"{row['filter_questions_pass_n']}/"
            f"{row['filter_questions_n']}"
            if row["filter_questions_n"]
            else "N/A"
        )

        lines.append(
            f"| {strategy} | "
            f"{row['coherence_mean_out_of_2']:.2f} | "
            f"{row['metadata_correct_n']}/"
            f"{row['metadata_checked_n']} | "
            f"{filter_result} | "
            f"{row['grounding_score_0_n']}/"
            f"{row['grounding_score_1_n']}/"
            f"{row['grounding_score_2_n']} | "
            f"{row['grounding_mean_out_of_2']:.2f} | "
            f"{stats_by_strategy[stored_strategy]['chunk_count']} |"
        )

    lines.extend([
        "",
        "## Assessment provenance and limits",
        "",
        "- B and C share chunks; coherence labels refer to "
        "identical chunk content.",
        "- Filter compliance counts questions whose entire "
        "top-3 satisfies the requested scope.",
        "- A can return in-scope results without applying a filter.",
        "- Grounding measures retrieved evidence, not generated "
        "LLM answer accuracy.",
        "- Test contains only five questions and one filter "
        "question; results do not establish general superiority.",
        "",
        f"Dev run: {frozen['dev_run']}",
        f"Test run: results/test/{test_dir.name}",
        f"Audit files: results/manual/{test_dir.name}",
    ])

    report_path = output_dir / "RESULTS.md"
    report_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    for row in audit_summary:
        print(
            f"{row['strategy']}: "
            f"coherence={row['coherence_mean_out_of_2']:.2f}/2, "
            f"metadata={row['metadata_correct_n']}/"
            f"{row['metadata_checked_n']}, "
            f"filter={row['filter_questions_pass_n']}/"
            f"{row['filter_questions_n']}, "
            f"grounding={row['grounding_mean_out_of_2']:.2f}/2"
        )

    print(f"\nSaved summary: {report_path}")


if __name__ == "__main__":
    main()