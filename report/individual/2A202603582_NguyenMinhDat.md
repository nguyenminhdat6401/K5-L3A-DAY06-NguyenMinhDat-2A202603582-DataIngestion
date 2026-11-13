# Báo cáo cá nhân — Day 6
- Họ và tên: Nguyễn Minh Đạt
- MSSV: 2A202603582
- Lớp: L3A

## Dữ liệu và pipeline
- Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:
- Chuẩn hóa, lỗi và giới hạn:
- Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí:
- Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn:

## Dữ liệu và pipeline

- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:**
  - Chủ đề: khái niệm cơ bản và phương pháp nghiên cứu xã hội học.
  - Nguồn: *Introduction to Sociology 3e*, OpenStax và các tác giả đóng góp, ©2021 Rice University.
  - PDF: https://assets.openstax.org/oscms-prodcms/media/documents/IntroductiontoSociology3e-WEB_TZsroiv.pdf
  - Bản PDF sử dụng ghi giấy phép CC BY 4.0 tại trang PDF 4 và 13. Giữ thông tin ghi công: “Access for free at openstax.org.”
  - Corpus gồm 40 trang: PDF 19–37 thuộc chương 1 và PDF 47–67 thuộc chương 2, tổng 123.479 ký tự sau chuẩn hóa.
  - Đếm theo số trang vật lý trong PDF, bắt đầu từ 1, không dùng số in trên sách. Chọn các trang nội dung chính; loại bìa, mục lục và các phần ôn tập/tài liệu tham khảo ngoài phạm vi đã chọn.
  - Nguồn, quyền sử dụng, SHA-256, danh sách trang và số ký tự được lưu trong `data/manifest.json`; bảng kiểm tra trang nằm tại `data/content_review.csv`.

- **Chuẩn hóa, lỗi và giới hạn:**
  - Dùng pypdf đọc từng trang; chuẩn hóa Unicode NFC, xuống dòng và khoảng trắng; loại ký tự soft hyphen và giữ ranh giới đoạn khi có thể.
  - PDF có 669 trang, trích xuất được 667 trang. Trang PDF 1 và 2 không có text trích xuất được, được ghi trong `results/extraction/extraction_errors.json` và không đưa vào corpus.
  - Không thực hiện OCR. Mỗi chunk giữ nguồn, trang và vị trí ký tự trong text đã chuẩn hóa.
  - Giới hạn: trích xuất PDF có thể làm mất cấu trúc đoạn hoặc giữ lại header/footer. Chunk không vượt ranh giới trang nên nội dung liên trang có thể bị tách. Cấu hình chia cố định có thể cắt giữa từ hoặc câu.

- **Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí:**
  - Embedding chạy local trên CPU bằng Sentence Transformers 5.7.0, model `intfloat/multilingual-e5-small`.
  - Model revision: `614241f622f53c4eeff9890bdc4f31cfecc418b3`.
  - Số chiều: 384; vector được chuẩn hóa. Dùng tiền tố `passage: ` cho document và `query: ` cho câu hỏi.
  - Kiểm tra số token trước khi encode, không âm thầm cắt đầu vào vượt giới hạn.
  - Vector store: PostgreSQL 16.16 và pgvector 0.8.7, chạy bằng Docker, lưu bền vững bằng volume.
  - Metric: cosine; tìm kiếm exact, chưa tạo approximate vector index.
  - Lệnh chạy từ thư mục `starter`: `python scripts/build_embeddings.py`, `python scripts/ingest_store.py`, `python -m src.run` cho dev và `python scripts/run_test.py` cho test.
  - Phí API trả tiền: 0 vì chạy local; chưa tính điện, phần cứng và mạng.
  - Thời gian embedding: A 8,984 giây, B 7,351 giây. Lưu DB lần đầu: A 0,098 giây, B 0,072 giây. C dùng chung chunk và vector của B. Đây không phải thời gian end-to-end.
  - Nạp lại hai lần vẫn giữ A ở 290 bản ghi và B ở 196 bản ghi. Pipeline thay snapshot của từng strategy trong transaction, loại chunk cũ khi nạp dữ liệu thay đổi.

- **Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn:**
  - Metadata truy vết gồm `document_id`, `source` và `page`; `page` là số trang vật lý PDF, kiểu số nguyên.
  - `char_start` và `char_end` là vị trí ký tự trong text trang đã chuẩn hóa, giúp đối chiếu chunk với nguồn.
  - Trường lọc bổ sung là `section`, kiểu chuỗi: `chapter_1` cho PDF 19–37 và `chapter_2` cho PDF 47–67. Giá trị lấy từ chương thực tế của tài liệu, không suy đoán.
  - `section_title` lưu tên chương; `language=en` và `document_type=textbook` mô tả corpus; `attribution` lưu thông tin ghi công.
  - Chọn `section` vì corpus có hai phạm vi phân biệt được. Cấu hình C áp dụng filter chương do câu hỏi cung cấp trước khi truy xuất.
  - Giới hạn: filter chương khá rộng; `language` và `document_type` có cùng giá trị trên toàn corpus nên không giúp phân biệt các phần nội dung trong thí nghiệm này.

## Cấu hình và benchmark
- A / B / C (tham số cụ thể, khác biệt duy nhất B–C):
- ≥20 câu: phân chia ≥15 dev / ≥5 test, câu metadata filter và cách kiểm chứng evidence:
- Tiêu chí chọn chiến lược đã chốt trước khi xem test:


## Cấu hình và benchmark

- **A / B / C:**
  - A: chia cửa sổ cố định 500 ký tự, overlap 50 ký tự, không filter; tạo 290 chunk.
  - B: ưu tiên ngắt theo đoạn, sau đó theo câu hoặc khoảng trắng, tối đa 900 ký tự, không overlap, không filter; tạo 196 chunk.
  - C: dùng chính chunk và vector của B; chỉ thêm metadata filter khi câu hỏi cung cấp filter. Câu không có filter được truy xuất như B.
  - B–C chỉ khác việc áp dụng filter; cùng corpus, chunk, model, vector store và cosine metric.
  - A–B khác cả phương pháp ngắt, kích thước và overlap, nên không quy toàn bộ chênh lệch cho riêng cách ngắt theo đoạn.
  - Các cấu hình không tạo chunk vượt ranh giới trang PDF.

- **Benchmark và kiểm chứng evidence:**
  - Tổng cộng 20 câu hỏi tiếng Việt trên corpus tiếng Anh, chia trước khi thử retrieval: 15 câu dev (`q01–q15`) và 5 câu test (`q16–q20`).
  - Có 3 câu metadata filter: `q07`, `q12` thuộc dev và `q19` thuộc test.
  - Mỗi câu có `expected_answer`, `gold_source_id`, `gold_page`, `evidence_quote` và `filter` nếu có.
  - Evidence được kiểm tra tồn tại trong text trang sau chuẩn hóa và được học viên đánh dấu xác minh trong `benchmark/review.csv`.
  - Filter dựa trên phạm vi chương nêu trong câu hỏi, được cung cấp trước truy xuất. Không đưa gold answer, gold page hoặc evidence vào query.
  - Hit tự động yêu cầu chunk đúng nguồn/trang và chứa đủ đoạn evidence sau chuẩn hóa. Evidence bị tách qua nhiều chunk không được tính là hit theo metric chính.
  - Hai split cùng bao phủ hai chương và có khái niệm liên quan; nguy cơ rò rỉ theo chủ đề là một giới hạn của benchmark.

- **Tiêu chí chọn chiến lược trước khi xem test:**
  1. Ưu tiên dev Evidence Hit@3 cao nhất.
  2. Nếu hòa, ưu tiên dev Hit@1 cao hơn.
  3. Nếu vẫn hòa, chọn cấu hình có ít chunk hơn.
  4. Nếu tiếp tục hòa, ưu tiên B, rồi A, rồi C.
  - B được chọn trên dev. Lựa chọn, revision model và hash các file được lưu trong `results/frozen/experiment.json` trước khi chạy test.
  - Giữ lựa chọn B sau khi xem test, không điều chỉnh cấu hình theo kết quả test.

## Kết quả

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---|---|---:|---|---|
| A | dev | 6/15 (40,0%) | 10/15 (66,7%) | 290 | Embedding 8,984 s; lưu DB 0,098 s | Phí API: 0 |
| B | dev | 9/15 (60,0%) | 12/15 (80,0%) | 196 | Embedding 7,351 s; lưu DB 0,072 s | Phí API: 0 |
| C | dev | 9/15 (60,0%) | 12/15 (80,0%) | 196, dùng chung B | Dùng chung bước embedding/lưu DB của B | Phí API: 0 |
| A | test | 2/5 (40,0%) | 2/5 (40,0%) | 290 | Dùng lại index đã tạo | Phí API: 0 |
| B | test | 2/5 (40,0%) | 4/5 (80,0%) | 196 | Dùng lại index đã tạo | Phí API: 0 |
| C | test | 2/5 (40,0%) | 4/5 (80,0%) | 196, dùng chung B | Dùng lại index B và áp dụng filter | Phí API: 0 |

Thời gian trong bảng là thời gian embedding document và lưu DB lần đầu,
không phải thời gian retrieval hoặc end-to-end. Các bước này không được
thực hiện lại cho test. Chưa tính điện, phần cứng và mạng. Thời gian
retrieval từng truy vấn được lưu trong trace.

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| A | 1,00/2 (10) | 15/15 | 1/1 câu | 0: 1 câu; 1: 2 câu; 2: 2 câu. Trung bình 1,20/2 |
| B | 1,80/2 (10) | 15/15 | 0/1 câu | 0: 1 câu; 1: 0 câu; 2: 4 câu. Trung bình 1,60/2 |
| C | 1,80/2 (10) | 15/15 | 1/1 câu | 0: 1 câu; 1: 0 câu; 2: 4 câu. Trung bình 1,60/2 |

Filter tuân thủ được tính theo số câu có toàn bộ top-3 đúng phạm vi
trên tổng số câu test yêu cầu filter. Test chỉ có một câu như vậy,
là q19. A không áp dụng filter nhưng tình cờ trả về đúng phạm vi.
Metadata đúng không đồng nghĩa chunk chứa đáp án đúng.

**Đường dẫn trace, nhãn và cách chọn mẫu:**

- Trace dev: `results/dev/20261113T044849_688540Z/traces.jsonl`.
- Trace test: `results/test/20261113T045414_716271Z/traces.jsonl`.
- Nhãn coherence: `results/manual/20261113T045414_716271Z/coherence.csv`.
- Nhãn metadata: `results/manual/20261113T045414_716271Z/metadata.csv`.
- Nhãn grounding: `results/manual/20261113T045414_716271Z/grounding.csv`.
- Bảng tổng hợp: `results/summary/RESULTS.md`.

Coherence dùng 10 vị trí nguồn cố định trước khi chấm: trung điểm text
của năm trang đầu mỗi chương, tương ứng PDF 19–23 và 47–51.
Nếu nhiều chunk bao phủ cùng vị trí, chọn chunk có char_start nhỏ nhất,
sau đó theo chunk_id. Mỗi strategy có 10 mẫu; B và C có cùng nội dung
chunk nên dùng cùng nhãn coherence.

Metadata được đối chiếu trên 5 câu test × top-3 = 15 bản ghi mỗi strategy.
Grounding đánh giá cả top-3 của từng câu test, thang 0–2; đây là độ đủ
của bằng chứng truy xuất, không phải độ chính xác câu trả lời LLM.



## Phân tích và kết luận
- So sánh A–B và B–C; 2 ví dụ sai có ID câu và nguồn:
- Chiến lược chọn, đánh đổi, điều kiện áp dụng:
- Hạn chế của dữ liệu, nhãn, test nhỏ, đo thời gian/chi phí:
- Nếu làm lại hoặc mở rộng, cải tiến gì?


- **So sánh A–B và B–C; ví dụ sai có ID câu và nguồn:**
  - A–B: B tăng Evidence Hit@3 từ 10/15 lên 12/15 trên dev và từ 2/5 lên 4/5 trên test. Coherence tăng từ 1,00 lên 1,80/2; grounding test tăng từ 1,20 lên 1,60/2.
  - B tạo 196 chunk so với 290 của A, giảm khoảng 32,4%. Trong lần đo này, thời gian embedding B là 7,351 giây, thấp hơn A là 8,984 giây.
  - B ưu tiên ranh giới đoạn/câu nên giữ ngữ cảnh tốt hơn trong các mẫu đã chấm. Tuy nhiên, A–B thay cả cách ngắt, kích thước và overlap, nên chưa tách riêng ảnh hưởng của từng yếu tố.
  - B–C: hai cấu hình bằng Hit@1, Evidence Hit@3 và grounding. Với q19, C cải thiện tỷ lệ câu có toàn bộ top-3 đúng phạm vi từ 0/1 lên 1/1. Evidence Hit@3 không tăng vì rank 2 của B đã chứa đủ bằng chứng.
  - **Ví dụ lỗi 1 — A/q16:** nguồn OpenStax, trang PDF 20. Chunk rank 2 bị cắt trước điều kiện “chia sẻ văn hóa chung”, nên top-3 chưa đủ định nghĩa society. Grounding đạt 1/2. B và C lấy được định nghĩa đầy đủ tại rank 3.
  - **Ví dụ lỗi 2 — B/q19:** rank 3 đến từ trang PDF 35, thuộc chapter_1, trong khi câu hỏi yêu cầu chapter_2. Metadata của chunk vẫn chính xác nhưng kết quả không đáp ứng phạm vi. C áp dụng filter và thay kết quả này bằng chunk thuộc chapter_2.
  - **Lỗi chung — q20:** evidence gold nằm ở trang PDF 65, nhưng cả A/B/C không truy xuất được bằng chứng về nghĩa vụ báo cáo kết quả trái quan điểm hoặc dự đoán. Grounding đều bằng 0.

- **Chiến lược chọn, đánh đổi, điều kiện áp dụng:**
  - Chọn B theo quy tắc đã công bố trước khi xem test: ưu tiên dev Evidence Hit@3, sau đó Hit@1, số chunk và thứ tự phá hòa.
  - B đạt kết quả retrieval cao hơn A trong thí nghiệm này, đồng thời có ít chunk hơn và coherence tốt hơn trên mẫu đã chấm.
  - Đánh đổi: B vẫn có thể thiếu ngữ cảnh ở đầu chunk hoặc bị ngắt do giới hạn kích thước/trang; không bảo đảm mọi chunk đều trọn ý.
  - Với ứng dụng yêu cầu giới hạn chương rõ ràng và có metadata đáng tin cậy, cách lọc như C giúp tuân thủ phạm vi. Nếu filter sai, hệ thống có thể loại bỏ bằng chứng phù hợp.
  - Giữ lựa chọn B sau test. Nhận xét về giá trị của C không được dùng để thay đổi hồi cứu lựa chọn đã chốt.

- **Hạn chế của dữ liệu, nhãn, test nhỏ, đo thời gian/chi phí:**
  - Corpus chỉ gồm 40 trang của hai chương trong một sách, chưa đại diện cho tài liệu đa nguồn hoặc các lĩnh vực khác.
  - Câu hỏi tiếng Việt trên corpus tiếng Anh khiến kết quả phụ thuộc khả năng đa ngữ của model.
  - Dev và test có khái niệm liên quan, nên vẫn có nguy cơ rò rỉ theo chủ đề.
  - Test chỉ có 5 câu, trong đó 1 câu yêu cầu filter. Mỗi câu làm tỷ lệ test thay đổi 20 điểm phần trăm; chưa đủ để kết luận ưu thế tổng quát.
  - Coherence chỉ dùng 10 vị trí nguồn mỗi strategy.
  - Exact-evidence matching có thể bỏ sót bằng chứng tương đương. Ngược lại, tìm thấy một đoạn gold không thay thế việc kiểm tra độ đủ ngữ cảnh.
  - Thời gian đo chưa được lặp nhiều lần hoặc hoán đổi thứ tự A/B. Thời gian embedding và lưu DB không phải thời gian end-to-end, chưa gồm đọc PDF, chunking, tải model và ghi file.
  - Phí API bằng 0 vì chạy local; điện, phần cứng và mạng chưa được định giá.
  - Kết quả grounding đánh giá bằng chứng truy xuất, không phải độ chính xác câu trả lời được LLM sinh ra.

- **Nếu làm lại hoặc mở rộng:**
  - Mở rộng corpus và benchmark, bổ sung câu diễn đạt lại, điều kiện, ngoại lệ và nhiều câu metadata filter hơn.
  - Chia dev/test theo chủ đề hoặc tài liệu khi khả thi; tạo tập test mới cho vòng phát triển tiếp theo.
  - Thiết kế thí nghiệm chỉ thay một yếu tố mỗi lần để phân biệt tác động của kích thước, overlap và cách ngắt.
  - Cải thiện xử lý header/footer và nội dung liên trang, đồng thời giữ khả năng truy vết chính xác.
  - Thử hybrid retrieval hoặc reranking, chọn tham số trên dev và ghi cả trường hợp làm kết quả xấu đi.
  - Bổ sung người chấm độc lập, che tên strategy và kết quả retrieval khi chấm; ghi cách giải quyết bất đồng.
  - Đo lặp thời gian, tách tải model, embedding, lưu trữ và truy xuất để so sánh tài nguyên rõ hơn.