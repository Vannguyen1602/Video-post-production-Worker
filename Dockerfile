FROM python:3.11-slim

WORKDIR /app

# Cài đặt các thư viện cần thiết (Thư viện google-genai mới nhất)
RUN pip install --no-cache-dir google-genai requests

# Copy mã nguồn vào container
COPY . .

# Không buffer log để hiển thị realtime trong Docker logs
ENV PYTHONUNBUFFERED=1

# Chạy script Video Worker
CMD ["python3", "auto_video_worker.py"]
