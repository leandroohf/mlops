from kfp import dsl
from kfp.dsl import component, Input, Output, Dataset, Model, Metrics
from kfp.dsl import Metrics

from dotenv import dotenv_values
from src.utils import get_env_from_yaml

config = dotenv_values(".env")
IMAGE_URI = config.get("IMAGE_URI")     # ex: "us-central1-docker.pkg.dev/your-project/ml-images/parallel-models:v1"
BUCKET_NAME = config.get("BUCKET_NAME") # bucket for staging
BUCKET_URI = config.get("BUCKET_URI")   # gs://bucket for staging

ENV = get_env_from_yaml("latest.yaml")

IMAGE = f"{IMAGE_URI}:{ENV}"

print(f"Using environment: {ENV}")
print(f"Using image: {IMAGE_URI}")
print(f"Using image with tag: {IMAGE}")
print(f"Using bucket: {BUCKET_NAME}")
print(f"Using bucket URI: {BUCKET_URI}")

@component(base_image=IMAGE_URI)
def preprocess(preprocessed_dataset: Output[Dataset], n_rows: int = 1000) -> Dataset:

    from src.executor import run_preprocess
    import sys
    # NOTE: KFP gives you a directory at output_dataset.path

    print(f"[preprocess] n_rows: {n_rows}")
    print(f"[preprocess] sys.path: {sys.path}")

    # ... write preprocessed.csv / preprocessed.pkl under output_dataset.path ...
    print("[debug] local path:", preprocessed_dataset.path)   # container path
    # In Vertex runs, .uri is the GCS artifact destination:
    print("[debug] cloud uri:", preprocessed_dataset.uri)
    preprocessed_dataset.metadata["files"] = ["preprocessed.csv", "preprocessed.pkl"]
    preprocessed_dataset.metadata["label"] = "preprocessed_data" 

    preprocessed_data = run_preprocess(output_dir=preprocessed_dataset.path, n_rows=n_rows)

    preprocessed_dataset.metadata["size"] = preprocessed_data.shape
    print(f"[preprocess] done -> {preprocessed_dataset.path} with shape={preprocessed_data.shape}")
    print(f"[preprocess] dataset name: {preprocessed_dataset.name}")
    print(f"[preprocess] dataset uri: {preprocessed_dataset.uri}")
    print(f"[preprocess] dataset metadata: {preprocessed_dataset.metadata}")


@component(base_image=IMAGE_URI)
def train(
    preprocessed_dataset: Input[Dataset],
    model: Output[Model],
    metrics: Output[Metrics],
    model_name: str = "m1",
    ):

    from src.executor import train_model
    
    print(f"[train] dataset URI: {preprocessed_dataset.uri}")

    r2 = train_model(dataset_dir=preprocessed_dataset.uri, model_dir=model.path, model_name=model_name)
    print(f"[train] {model_name}: r2={r2:.3f}")

    model.metadata["version"] = "1.0"
    model.framework = "sklearn"
    model.metadata["r2"] = r2
    model.metadata["label"] = model_name

    print(f"[train] model name: {model.name}")
    print(f"[train] model saved at: {model.path}")
    print(f"[train] model URI: {model.uri}")
    print(f"[train] model metadata: {model.metadata}")

    print(f"[train] metrics URI: {metrics.uri}")
    print(f"[train] metrics saved at: {metrics.path} with r2={r2:.3f}")
    print(f"[train] metrics metadata: {metrics.metadata}")

    metrics.log_metric(f"{model_name}_r2", r2)


@component(
    base_image=IMAGE_URI,
)
def publish_best_model(
    preprocessed_dataset: Input[Dataset],
    model1: Input[Model],
    model2: Input[Model]):

    from src.artifact_io import LocalArtifactHandler, GCSArtifactHandler
    from src.executor import validate_model, get_target_and_features
    from sklearn.model_selection import train_test_split
    import os
    import subprocess, shlex   

    # NOTE: VertexAI mount the vertexai bucket at /gcs/
    # This is what allows to save on disk and have it in GCS
    # VertexAI does not allow ls /gcs/ folder
    print("debug: VertexAI mount the vertexai bucket at /gcs/")
    for p in [preprocessed_dataset.path, model1.path, model2.path]:
        print(f"\n--- du for {p} ---")
        print(subprocess.check_output(["bash","-lc", f"du -sh {shlex.quote(p)} || true"], text=True))
        print(subprocess.check_output(["bash","-lc", f"du -sh {shlex.quote(p)}/* 2>/dev/null || true"], text=True))

    print(f"[validate] dataset URI: {preprocessed_dataset.path}")

    handler = LocalArtifactHandler()
   
    parquet_path = os.path.join(preprocessed_dataset.path, "preprocessed.parquet")
    print(f"[validate] loading preprocessed data from {parquet_path}")
    preprocessed_data = handler.load(parquet_path)

    X, y = get_target_and_features(preprocessed_data)

    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2)

    print(f"[validate] model1 URI: {model1.uri}")
    print(f"[validate] model1 PATH: {model1.path}")
    print(f"[validate] model1 METADATA: {model1.metadata}")
    model_path1 = os.path.join(model1.path, model1.metadata.get("label") + ".joblib")
    print(f"[validate] loading model1 from {model_path1}")
    m1_reg = handler.load(model_path1)

    model_path2 = os.path.join(model2.path, model2.metadata.get("label") + ".joblib")
    print(f"[validate] loading model2 from {model_path2}")
    m2_reg = handler.load(model_path2)

    r2_model1 = validate_model(X_test,y_test, m1_reg)
    r2_model2 = validate_model(X_test,y_test, m2_reg)

    winner_model = model1 if r2_model1 >= r2_model2 else model2
    best_model = m1_reg if r2_model1 >= r2_model2 else m2_reg
    print(f"[validate] winner: {winner_model.metadata.get('label')} with r2={max(r2_model1, r2_model2):.3f}")

    bucket_name = os.environ.get("BUCKET_NAME")
    print(f"[validate] publishing to bucket: {bucket_name}")

    # NOTE: publish to GCS bucket
    publisher = GCSArtifactHandler(
        bucket_name=bucket_name,
        root_path="vertexai/prod/models")
    
    publish_path = "best.joblib"
    publisher.save(best_model, publish_path)

@dsl.pipeline(
            name="vertexai-demo-pipeline",
            description="Preprocess -> Train x2 -> Publish best"
              )
def pipeline(n_rows: int = 1000, model1_name: str = "model1", model2_name: str = "model2"):

    pre = preprocess(n_rows=n_rows)
    pre.set_cpu_limit("4")
    pre.set_memory_limit("16G")

    m1 = train(preprocessed_dataset=pre.outputs["preprocessed_dataset"], model_name=model1_name)
    m1.set_cpu_limit("4")
    m1.set_memory_limit("16G")

    m2 = train(preprocessed_dataset=pre.outputs["preprocessed_dataset"], model_name=model2_name)
    m2.set_cpu_limit("4")
    m2.set_memory_limit("16G")

    p = publish_best_model(
        preprocessed_dataset=pre.outputs["preprocessed_dataset"],
        model1=m1.outputs["model"], 
        model2=m2.outputs["model"],
    )
    p.set_cpu_limit("4")
    p.set_memory_limit("16G")
    p.set_env_variable("BUCKET_NAME", BUCKET_NAME) # NOTE: setting env var inside an componet
    p.set_env_variable("env", ENV) # NOTE: setting env var inside an componet
