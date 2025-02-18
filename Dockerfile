FROM python:3.12.1 AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN python -m venv .venv
COPY requirements.txt ./
RUN .venv/bin/pip install --no-cache-dir -r requirements.txt

# Slim final image
FROM python:3.12.1-slim

WORKDIR /app

COPY --from=builder /app/.venv .venv/
COPY . .

RUN chmod +x /app/.venv/bin/uvicorn

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
