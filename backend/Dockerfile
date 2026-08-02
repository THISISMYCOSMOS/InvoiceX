# The build context is the repository root so the backend can install the sibling
# invoicex-agents package as a normal runtime dependency.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY agent /app/agent
COPY backend /app/backend

RUN pip install --no-cache-dir /app/agent /app/backend

WORKDIR /app/backend
EXPOSE 8080

CMD ["/bin/sh", "-c", "exec uvicorn invoicex_backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
