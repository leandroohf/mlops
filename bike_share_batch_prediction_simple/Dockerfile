FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# NOTE: How to use 
# docker build -t job-image .
# docker run job-image --env=dev
ENTRYPOINT ["python", "run.py"]
CMD ["--env=dev"] # NOTE: default is dev