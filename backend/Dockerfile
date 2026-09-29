FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# uv installs Python wheels substantially faster than pip for this image.
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /bin/uv

# Install the CPU-only Torch wheel first so sentence-transformers does not pull
# a heavier CUDA build.
RUN uv pip install --system torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

COPY . .
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
