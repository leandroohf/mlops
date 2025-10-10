import os
from kfp import compiler
from google.cloud import aiplatform


PROJECT_ID = os.environ.get("PROJECT_ID")
REGION = os.environ.get("REGION", "us-central1")
BUCKET = os.environ.get("BUCKET") # gs://bucket for staging

from pipeline import pipeline
compiler.Compiler().compile(pipeline_func=pipeline, package_path="pipeline.json")

aiplatform.init(project=PROJECT_ID, location=REGION, staging_bucket=BUCKET)

job = aiplatform.PipelineJob(
    display_name="parallel-two-models-custom-image",
    template_path="pipeline.json",
    location=REGION,
    enable_caching=True,
    parameter_values={"n_rows": 1500},
)

#job.run(sync=True) # NOTE: sync=True blocks until done
job.run(sync=False) # NOTE: sync=False returns immediately
print("Submitted. Check Vertex AI -> Pipelines for DAG + artifacts.")
print(f"Job details: {job.resource_name}")