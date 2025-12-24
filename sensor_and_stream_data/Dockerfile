# Dockerfile
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Install deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# NOTE: Copy repo code (common_pipelines/, scripts/, etc.)
COPY . /app

# NOTE: install common_pipelines package
RUN pip install --no-cache-dir -e /app

RUN chmod +x /app/scripts/run_apache_beam_batch_raw_events_to_features.py

# NOTE: Default: submit Dataflow job
ENTRYPOINT ["python", "scripts/run_apache_beam_batch_raw_events_to_features.py"]
CMD ["--runner=DataflowRunner"]