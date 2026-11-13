# Hướng dẫn chạy bài Lab 6

## Môi trường

- Windows, Python 3.11.
- Docker Desktop đang hoạt động.
- PostgreSQL 16 + pgvector theo starter/docker-compose.yml.
- Model local intfloat/multilingual-e5-small, CPU, 384 chiều.
- Không cần API key cho embedding.
- Cần mạng ở lần đầu tải thư viện, Docker image và model.

Phiên bản thư viện đầy đủ: starter/requirements-lock.txt.

## Setup từ thư mục gốc repo

```powershell
cd starter
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
docker compose -p day6_student_starter up -d --wait
python scripts\check_setup.py
```

Nếu PyTorch lỗi nạp DLL trên Windows, kiểm tra Visual C++ Runtime
x64 theo hướng dẫn chính thức của PyTorch/Microsoft.

## Dữ liệu

Nguồn và quyền sử dụng nằm trong data/manifest.json.
Corpus chuẩn hóa: data/corpus.jsonl.
Trang được chọn: PDF 19–37 và 47–67.
Số trang là số vật lý PDF, bắt đầu từ 1.

Model revision:
614241f622f53c4eeff9890bdc4f31cfecc418b3

Không thay corpus, benchmark, model hoặc code đã freeze rồi
coi kết quả test cũ là đánh giá độc lập cho cấu hình mới.

## Chạy lại từ snapshot chunk và vector đã nộp

```powershell
python scripts\ingest_store.py
python -m src.run
python scripts\run_test.py
```

ingest_store.py kiểm tra hash, nạp A/B và nạp lại để kiểm tra
không trùng. C dùng chung dữ liệu B.

src.run chạy dev; run_test.py kiểm tra experiment freeze và chạy
test. Mỗi lần chạy tạo thư mục kết quả mới.

Các hash kiểm tra byte của file; giữ nguyên nội dung và encoding
của các file đã freeze.

## Các bước xây dựng dữ liệu đã thực hiện

Theo thứ tự:
1. scripts/extract_corpus.py
2. scripts/prepare_corpus.py — phạm vi dự kiến ban đầu.
3. scripts/build_corpus.py — phạm vi cuối gồm 40 trang.
4. Kiểm tra data/content_review.csv.
5. scripts/build_chunks.py
6. scripts/build_benchmark.py và kiểm tra benchmark/review.csv.
7. scripts/build_embeddings.py
8. scripts/ingest_store.py
9. python -m src.run
10. scripts/freeze_experiment.py
11. scripts/run_test.py
12. scripts/prepare_manual_audit.py
13. Điền các CSV audit.
14. scripts/summarize_results.py

Các script benchmark, embedding và freeze có chặn ghi đè để
bảo vệ lịch sử thí nghiệm. Không chạy lại các bước tạo đầu vào
trên snapshot đã nộp nếu chỉ muốn tái lập retrieval.

## Kết quả và nhãn

- Báo cáo: report/individual/
- Tổng hợp: results/summary/RESULTS.md
- Dev dùng để chọn cấu hình:
  results/dev/20261113T044849_688540Z/
- Test:
  results/test/20261113T045414_716271Z/
- Audit:
  results/manual/20261113T045414_716271Z/
- Freeze: results/frozen/experiment.json
- Nhật ký cấu hình: artifacts/experiment_log.csv


## Dừng database và giữ dữ liệu

```powershell
docker compose -p day6_student_starter stop
```
