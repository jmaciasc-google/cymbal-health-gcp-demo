FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    ENFORCE_ZERO_STATIC_KEYS=true \
    CM_PLAIN=true

RUN groupadd --gid 10001 appuser && \
    useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend
COPY docs/clinical-protocols /app/docs/clinical-protocols
COPY CONTEXT.md /app/CONTEXT.md

RUN chown -R 10001:10001 /app

USER 10001:10001

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3)" || exit 1

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]
