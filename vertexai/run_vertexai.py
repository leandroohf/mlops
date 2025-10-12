import os
import subprocess
from time import time
from kfp import compiler
from google.cloud import aiplatform
from dotenv import dotenv_values
from pipeline import IMAGE_URI, pipeline
from src.utils import get_env_from_yaml

config = dotenv_values(".env")

PROJECT_ID = config.get("PROJECT_ID") # ex: "your-project"
REGION = config.get("REGION", "us-central1") # ex: "us-central1"
BUCKET = config.get("BUCKET_URI") # gs://bucket for staging

class VertexAiRunner:
    def __init__(self, env: str = None):

        self.env = env or get_env_from_yaml("latest.yaml")
        print(f"Using env: {self.env}")

    def build(self):

        print(f"Building image: {IMAGE_URI}")
        cmd = f'docker buildx build --platform linux/amd64 -t "{IMAGE_URI}" -f Dockerfile . --push'
        subprocess.check_call(["bash", "-lc", cmd])
        print("Pushed:", IMAGE_URI)

    def compile_pipeline(self):
        compiler.Compiler().compile(pipeline_func=pipeline, package_path="pipeline.json")

    def submit_pipeline(self):

        aiplatform.init(project=PROJECT_ID, location=REGION, staging_bucket=BUCKET)

        job = aiplatform.PipelineJob(
            display_name="parallel-two-models-custom-image",
            template_path="pipeline.json",
            location=REGION,
            enable_caching=True,
            parameter_values={"n_rows": 1500},
        )

        # NOTE: runs sync. Allows to print job details after submission
        # job.run(sync=True) # NOTE: sync=True blocks until done
        # print("Submitted. Check Vertex AI -> Pipelines for DAG + artifacts.")
        # print(f"Job details: {job.resource_name}")

        # NOTE: to run async
        # cannot print right away because job is not created until run() is called and finishes
        job.run(sync=False)

if __name__ == "__main__":

    runner = VertexAiRunner()
    runner.build()
    runner.compile_pipeline()
    runner.submit_pipeline()
    print("Submitted. Check Vertex AI -> Pipelines for DAG + artifacts.")