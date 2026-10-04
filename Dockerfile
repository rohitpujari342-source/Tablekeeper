FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONTZPATH="" \
    PORT=8080

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt
COPY stage-1 /app/stage-1
EXPOSE 8080

CMD ["python", "/app/stage-1/server.py"]