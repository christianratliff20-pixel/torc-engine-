FROM python:3.11-slim

# Explicit 3.11-slim, not 3.13 or "latest" — see requirements.txt comment.
# This is the exact class of issue (missing prebuilt pydantic-core wheel
# forcing a source compile with no Rust toolchain present) that broke the
# Sharp Edge deploy on Railway/Render.

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
