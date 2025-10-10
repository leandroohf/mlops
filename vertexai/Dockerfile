FROM python:3.11-slim

# NOTE: Prevents Python from writing .pyc files and buffering logs
ENV PYTHONDONTWRITEBYTECODE=1 \
PYTHONUNBUFFERED=1 \
PIP_NO_CACHE_DIR=1 \
PYTHONPATH="/app"

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY src/ ./src/