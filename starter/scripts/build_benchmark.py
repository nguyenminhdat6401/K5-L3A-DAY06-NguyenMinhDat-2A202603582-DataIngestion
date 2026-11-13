"""Create a benchmark before running retrieval experiments."""

import csv
import hashlib
import json
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]
SOURCE_ID = "openstax-sociology3e"

# Fields:
# question, expected_answer, physical_pdf_page, evidence_quote, filter
DEV = [
    (
        "Xã hội học nghiên cứu những đối tượng nào?",
        "Các nhóm và tương tác nhóm, xã hội và tương tác xã hội, "
        "từ quy mô nhỏ đến quy mô lớn.",
        20,
        "Sociology is the scientific and systematic study of groups "
        "and group interactions, societies and social interactions, "
        "from small and personal groups to very large groups.",
        {},
    ),
    (
        "Khái niệm culture đề cập đến những yếu tố chung nào của một nhóm?",
        "Những thực hành, giá trị và niềm tin được nhóm chia sẻ.",
        21,
        "The term culture refers to the group’s shared practices, "
        "values, and beliefs.",
        {},
    ),
    (
        "Việc coi một khái niệm trừu tượng như có tồn tại vật chất "
        "thực sự được gọi là gì?",
        "Reification.",
        21,
        "The error of treating an abstract concept as though it has "
        "a real, material existence is known as reification (Sahn, 2013).",
        {},
    ),
    (
        "Norbert Elias gọi quá trình phân tích đồng thời hành vi "
        "cá nhân và xã hội định hình hành vi đó là gì?",
        "Figuration.",
        22,
        "German sociologist Norbert Elias called the process of "
        "simultaneously analyzing the behavior of individuals and "
        "the society that shapes that behavior figuration.",
        {},
    ),
    (
        "Comte dùng thuật ngữ nào cho việc nghiên cứu khoa học "
        "các khuôn mẫu xã hội?",
        "Positivism.",
        24,
        "Comte named the scientific study of social patterns positivism.",
        {},
    ),
    (
        "Theo Marx, xã hội phát triển và thay đổi do điều gì?",
        "Do đấu tranh giữa các giai cấp về tư liệu sản xuất.",
        25,
        "He believed that societies grew and changed as a result "
        "of the struggles of different social classes over the "
        "means of production.",
        {},
    ),
    (
        "Trong phạm vi chương 1, Harriet Martineau giúp giới học "
        "thuật nói tiếng Anh tiếp cận xã hội học bằng cách nào?",
        "Dịch các tác phẩm của Comte từ tiếng Pháp sang tiếng Anh.",
        25,
        "Harriet Martineau introduced sociology to English speaking "
        "scholars through her translation of Comte’s writing from "
        "French to English.",
        {"section": "chapter_1"},
    ),
    (
        "Case study là kiểu phân tích như thế nào?",
        "Phân tích chuyên sâu một sự kiện, tình huống hoặc cá nhân.",
        62,
        "A case study is an in-depth analysis of a single event, "
        "situation, or individual.",
        {},
    ),
    (
        "Trong thí nghiệm, nhóm thực nghiệm và nhóm đối chứng "
        "khác nhau như thế nào về biến độc lập?",
        "Nhóm thực nghiệm tiếp xúc với biến độc lập; "
        "nhóm đối chứng không tiếp xúc.",
        63,
        "The experimental group is exposed to the independent "
        "variable(s) and the control group is not.",
        {},
    ),
    (
        "Hiệu ứng nào xảy ra khi người tham gia thay đổi hành vi "
        "vì biết mình đang được quan sát?",
        "Hawthorne effect.",
        63,
        "This is called the Hawthorne effect—which occurs when "
        "people change their behavior because they know they "
        "are being watched as part of a study.",
        {},
    ),
    (
        "Dữ liệu thứ cấp khác dữ liệu thu thập trực tiếp như thế nào?",
        "Dữ liệu thứ cấp là công trình đã hoàn thành của người khác "
        "hoặc dữ liệu do cơ quan, tổ chức thu thập.",
        64,
        "Secondary data does not result from firsthand research "
        "collected from primary sources, but are the already "
        "completed work of other researchers or data collected "
        "by an agency or organization.",
        {},
    ),
    (
        "Trong phạm vi chương 2, vì sao nghiên cứu dùng dữ liệu "
        "thứ cấp có thể được gọi là nonreactive research?",
        "Vì không tiếp xúc trực tiếp với đối tượng và không làm "
        "thay đổi hoặc ảnh hưởng hành vi của họ.",
        64,
        "One of the advantages of secondary data like old movies "
        "or WHO statistics is that it is nonreactive research "
        "(or unobtrusive research), meaning that it does not "
        "involve direct contact with subjects and will not alter "
        "or influence people’s behaviors.",
        {"section": "chapter_2"},
    ),
    (
        "Value neutrality yêu cầu nhà nghiên cứu giữ thái độ "
        "như thế nào trong nghiên cứu và công bố kết quả?",
        "Vô tư, không thiên lệch và không phán xét.",
        65,
        "Sociologists, he stated, must establish value neutrality, "
        "a practice of remaining impartial, without bias or judgment, "
        "during the course of a study and in publishing results "
        "(Weber, 1949).",
        {},
    ),
    (
        "Vấn đề về sự đồng ý trong trường hợp Henrietta Lacks là gì?",
        "Các bác sĩ thu thập và chia sẻ tế bào khi chưa có "
        "sự đồng ý của bà.",
        66,
        "Without her consent, doctors collected and shared her "
        "cells to produce extensive cell lines.",
        {},
    ),
    (
        "Theo mô tả trong sách, thí nghiệm Milgram gây lo ngại "
        "đạo đức nào cho người đóng vai giáo viên?",
        "Họ chịu đau khổ tinh thần nghiêm trọng vì tin rằng "
        "mình đang làm hại người khác.",
        66,
        "The ethical concerns involve the extreme emotional "
        "distress faced by the teachers, who believed they "
        "were hurting other people.",
        {},
    ),
]

TEST = [
    (
        "Một nhóm người cần có những đặc điểm nào để được gọi "
        "là society theo định nghĩa trong sách?",
        "Sống trong một khu vực địa lý xác định, tương tác "
        "với nhau và chia sẻ một nền văn hóa chung.",
        20,
        "A group of people who live in a defined geographic area, "
        "who interact with one another, and who share a common "
        "culture is what sociologists call a society.",
        {},
    ),
    (
        "Theo C. Wright Mills, sociological imagination giúp "
        "nhận biết mối liên hệ nào?",
        "Mối liên hệ giữa hành vi, trải nghiệm cá nhân và "
        "nền văn hóa rộng hơn định hình lựa chọn, nhận thức.",
        21,
        "Sociologists often study culture using the sociological "
        "imagination, which pioneer sociologist C. Wright Mills "
        "described as an awareness of the relationship between "
        "a person’s behavior and experience and the wider culture "
        "that shaped the person’s choices and perceptions.",
        {},
    ),
    (
        "Ai đặt ra thuật ngữ sociology đầu tiên, vào năm nào, "
        "và ai đưa thuật ngữ này trở lại vào năm 1838?",
        "Emmanuel-Joseph Sieyès đặt ra năm 1780; "
        "Auguste Comte đưa thuật ngữ trở lại năm 1838.",
        24,
        "The term sociology was first coined in 1780 by the "
        "French essayist Emmanuel-Joseph Sieyès (1748–1836) "
        "in an unpublished manuscript (Fauré et al. 1999). "
        "In 1838, the term was reintroduced by Auguste Comte "
        "(1798–1857).",
        {},
    ),
    (
        "Trong phạm vi chương 2, vì sao case study có hạn chế "
        "khi dùng để đưa ra kết luận khái quát?",
        "Nghiên cứu một trường hợp cung cấp chiều sâu nhưng "
        "không đủ bằng chứng để đưa ra kết luận khái quát.",
        62,
        "However, a major criticism of the case study as a method "
        "is that while offering depth on a topic, it does not "
        "provide enough evidence to form a generalized conclusion.",
        {"section": "chapter_2"},
    ),
    (
        "Nếu kết quả trái với quan điểm cá nhân hoặc dự đoán "
        "ban đầu, nhà nghiên cứu có nghĩa vụ gì?",
        "Vẫn phải báo cáo kết quả.",
        65,
        "Investigators are ethically obligated to report results, "
        "even when they contradict personal views, predicted "
        "outcomes, or widely accepted beliefs.",
        {},
    ),
]


def comparable(text: str) -> str:
    return " ".join(text.split())


def main() -> None:
    corpus_path = REPO_DIR / "data" / "corpus.jsonl"

    pages = {
        record["page"]: record
        for line in corpus_path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
        for record in [json.loads(line)]
    }

    questions = []

    for split, items in (("dev", DEV), ("test", TEST)):
        for question, answer, page_number, evidence, filters in items:
            page = pages[page_number]

            if page["document_id"] != SOURCE_ID:
                raise ValueError("Unexpected source ID.")

            if comparable(evidence) not in comparable(page["text"]):
                raise ValueError(
                    f"Evidence not found on PDF page {page_number}:\n"
                    f"{evidence}"
                )

            for key, value in filters.items():
                if page["metadata"].get(key) != value:
                    raise ValueError(
                        f"Filter does not match page {page_number}."
                    )

            questions.append({
                "id": f"q{len(questions) + 1:02d}",
                "split": split,
                "question": question,
                "expected_answer": answer,
                "gold_source_id": SOURCE_ID,
                "gold_page": page_number,
                "evidence_quote": evidence,
                "filter": filters,
                "alternative_gold": [],
            })

    benchmark_dir = REPO_DIR / "benchmark"
    benchmark_dir.mkdir(parents=True, exist_ok=True)

    questions_path = benchmark_dir / "questions.json"

    # Avoid accidentally replacing a benchmark after experiments.
    if questions_path.exists():
        raise FileExistsError(
            "benchmark/questions.json already exists. "
            "Do not overwrite a benchmark after running retrieval."
        )

    questions_text = json.dumps(
        questions, ensure_ascii=False, indent=2
    )

    protocol = {
        "dev_count": len(DEV),
        "test_count": len(TEST),
        "filter_question_ids": [
            q["id"] for q in questions if q["filter"]
        ],
        "selection_rule": (
            "Choose highest dev Evidence Hit@3, then highest "
            "dev Hit@1, then fewer chunks. If still tied, "
            "prefer B, then A, then C."
        ),
        "filter_policy": (
            "Only C applies the question's supplied filter. "
            "A and B ignore filters. C uses no filter when absent."
        ),
        "test_policy": (
            "Finalize configurations and select a strategy on dev "
            "before running test. Report test for all strategies "
            "without tuning against test results."
        ),
        "split_method": (
            "Manual split: dev q01-q15, test q16-q20. "
            "Both splits cover both chapters. Related concepts "
            "may overlap, so topic leakage is a limitation."
        ),
        "manual_review_status": "Pending",
        "benchmark_sha256": hashlib.sha256(
            questions_text.encode("utf-8")
        ).hexdigest(),
        "ai_assistance": (
            "Questions and code drafted with AI assistance; "
            "evidence checked against extracted text. "
            "Student must verify answer support against the PDF."
        ),
    }

    questions_path.write_text(questions_text, encoding="utf-8")

    (benchmark_dir / "protocol.json").write_text(
        json.dumps(protocol, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (benchmark_dir / "review.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "split",
                "gold_page",
                "question",
                "expected_answer",
                "evidence_quote",
                "verified",
                "notes",
            ],
        )
        writer.writeheader()

        for q in questions:
            writer.writerow({
                key: q.get(key, "")
                for key in writer.fieldnames
            })

    print(f"Questions: {len(questions)}")
    print(f"Dev: {len(DEV)}")
    print(f"Test: {len(TEST)}")
    print(
        "Filter questions:",
        ", ".join(protocol["filter_question_ids"]),
    )
    print("Evidence text checks: passed")
    print("Manual evidence/answer review: pending")
    print(f"Saved to: {benchmark_dir}")


if __name__ == "__main__":
    main()