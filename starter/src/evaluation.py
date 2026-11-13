"""TODO: evaluate retrieved evidence and preserve per-query traces."""

import unicodedata
from collections import defaultdict


def comparable(text: str) -> str:
    """Normalize Unicode and whitespace for evidence matching."""
    return " ".join(
        unicodedata.normalize("NFC", text).split()
    )


def gold_candidates(question: dict) -> list[dict]:
    primary = {
        "gold_source_id": question["gold_source_id"],
        "gold_page": question["gold_page"],
        "evidence_quote": question["evidence_quote"],
    }

    return [
        primary,
        *question.get("alternative_gold", []),
    ]


def evidence_hit(question: dict, hit: dict) -> bool:
    for gold in gold_candidates(question):
        quote = comparable(gold["evidence_quote"])

        if not quote:
            raise ValueError("Gold evidence cannot be empty.")

        if (
            hit["document_id"] == gold["gold_source_id"]
            and hit["page"] == gold["gold_page"]
            and quote in comparable(hit["text"])
        ):
            return True

    return False


def evaluate_query(
    question: dict,
    hits: list[dict],
) -> dict:
    labels = [
        evidence_hit(question, hit)
        for hit in hits[:3]
    ]

    return {
        "question_id": question["id"],
        "split": question["split"],
        "question": question,
        "hits": hits[:3],
        "hit_labels": labels,
        "hit1": bool(labels and labels[0]),
        "hit3": any(labels),
        "evaluation_method": (
            "Source/page plus complete normalized exact evidence. "
            "Equivalent evidence requires separate human review."
        ),
    }


def summarize(traces: list[dict]) -> list[dict]:
    groups = defaultdict(list)

    for trace in traces:
        groups[
            (trace["strategy"], trace["split"])
        ].append(trace)

    rows = []

    for (strategy, split), items in sorted(groups.items()):
        count = len(items)
        hit1_count = sum(item["hit1"] for item in items)
        hit3_count = sum(item["hit3"] for item in items)

        rows.append({
            "strategy": strategy,
            "split": split,
            "n": count,
            "hit1_n": hit1_count,
            "hit3_n": hit3_count,
            "hit1": hit1_count / count,
            "hit3": hit3_count / count,
        })

    return rows