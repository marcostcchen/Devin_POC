FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATA_DIR=/data

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Runs as a non-root user with a read-only root filesystem wherever it is
# deployed; $DATA_DIR is the only path it writes to.
RUN mkdir -p /data && chown 10001:10001 /data
USER 10001
EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
