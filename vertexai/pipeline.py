import os
import sys
from kfp import dsl
from kfp.dsl import component, Input, Output, Dataset, Model, Metrics


from kfp import local
from kfp.dsl import Metrics

from dotenv import dotenv_values
from sklearn.model_selection import train_test_split

from src.artifact_io import LocalArtifactHandler
from src.preprocessing import Preprocessor
from src.training import ModelTrainer

config = dotenv_values(".env")
IMAGE_URI = config.get("IMAGE_URI") # ex: "us-central1-docker.pkg.dev/your-project/ml-images/parallel-models:v1"

def preprocess(output_dir: str, n_rows: int = 1000):

    handler = LocalArtifactHandler()

    preprocessor = Preprocessor(n_rows=n_rows)
    preprocessed_data = preprocessor.fit_transform(raw_data=None)

    parquet_path = os.path.join(output_dir, "preprocessed.parquet")
    print(f"Writing Parquet to {parquet_path}")
    handler.save(preprocessed_data, parquet_path)

    csv_path = "preprocessed/preprocessed.csv"
    print(f"Writing CSV for debug to {csv_path}")
    handler.save(preprocessed_data, csv_path)

    return preprocessed_data


def train_model(dataset_dir: str, model_dir: str, model_name: str) -> float:

    handler = LocalArtifactHandler()
    parquet_path = os.path.join(dataset_dir, "preprocessed.parquet")
    preprocessed_data = handler.load(parquet_path)

    X = preprocessed_data[["feature_a", "feature_b", "feature_c"]]
    y = preprocessed_data["target"]

    X_train, _, y_train, _ = train_test_split(X, y, test_size=0.2)

    model = ModelTrainer(model_name=model_name)
    r2 = model.fit(X_train, y_train)

    model_path = os.path.join(model_dir, f"{model_name}.joblib")
    print(f"Saving model to {model_path}")
    handler.save(model, model_path)

    return r2



@component(base_image=IMAGE_URI)
def preprocess(output_dataset: Output[Dataset], n_rows: int = 1000) -> Dataset:

    from src.preprocessing import Preprocessor
    from src.artifact_io import LocalArtifactHandler
    import sys
    import os
    # NOTE: KFP gives you a directory at output_dataset.path

    print(f"[preprocess] n_rows: {n_rows}")
    print(f"[preprocess] sys.path: {sys.path}")

    # ... write preprocessed.csv / preprocessed.pkl under output_dataset.path ...
    print("[debug] local path:", output_dataset.path)   # container path
    # In Vertex runs, .uri is the GCS artifact destination:
    print("[debug] cloud uri:", output_dataset.uri)
    output_dataset.metadata["files"] = ["preprocessed.csv", "preprocessed.pkl"]
    output_dataset.name = "preprocessed_data"

    preprocessor = Preprocessor(n_rows=n_rows)
    preprocessed_data = preprocessor.fit_transform(raw_data=None)

    handler = LocalArtifactHandler()
    parquet_path = os.path.join(output_dataset.path, "preprocessed.parquet")
    print(f"Writing Parquet to {parquet_path}")
    handler.save(preprocessed_data, parquet_path)

    # preprocessed_data = preprocess_main(output_dir=output_dataset.path, n_rows=n_rows)

    output_dataset.metadata["size"] = preprocessed_data.shape
    print(f"[preprocess] done -> {output_dataset.path} with shape={preprocessed_data.shape}")

    return output_dataset

@component(base_image=IMAGE_URI)
def train_from_uri(
    dataset_uri: str,
    model: Output[Model],
    metrics: Output[Metrics],
    model_name: str = "model1",
    ):

    import os
    from sklearn.model_selection import train_test_split
    from src.training import ModelTrainer
    from src.artifact_io import LocalArtifactHandler
    
    print(f"[train] dataset URI: {dataset_uri}")

    handler = LocalArtifactHandler()
    preprocessed_data = handler.load(dataset_uri)

    X = preprocessed_data[["feature_a", "feature_b", "feature_c"]]
    y = preprocessed_data["target"]

    X_train, _, y_train, _ = train_test_split(X, y, test_size=0.2)

    model_lgr = ModelTrainer(model_name=model_name)
    r2 = model_lgr.fit(X_train, y_train)

    pickle_path = os.path.join(model.path, f"{model_name}.joblib")
    handler.save(model_lgr, pickle_path)

    model.metadata["version"] = "1.0"
    model.framework = "sklearn"
    model.metadata["r2"] = r2

    metrics.log_metric("r2", r2)

    print(f"[train] model saved at: {model.path}")
    print(f"[train] model URI: {model.uri}")
    print(f"[train] model metadata: {model.metadata}")

    print(f"[train] metrics URI: {metrics.uri}")
    print(f"[train] metrics saved at: {metrics.path} with r2={r2:.3f}")
    print(f"[train] metrics metadata: {metrics.metadata}")



@component(base_image=IMAGE_URI)
def train(
    preprocessed_dataset: Input[Dataset],
    model: Output[Model],
    metrics: Output[Metrics],
    model_name: str = "model1",
    ):

    import os
    from sklearn.model_selection import train_test_split
    from src.training import ModelTrainer
    from src.artifact_io import LocalArtifactHandler
    
    print(f"[train] dataset URI: {preprocessed_dataset.uri}")

    handler = LocalArtifactHandler()
    preprocessed_data = handler.load(preprocessed_dataset.uri)

    X = preprocessed_data[["feature_a", "feature_b", "feature_c"]]
    y = preprocessed_data["target"]

    X_train, _, y_train, _ = train_test_split(X, y, test_size=0.2)

    model_lgr = ModelTrainer(model_name=model_name)
    r2 = model_lgr.fit(X_train, y_train)

    pickle_path = os.path.join(model.path, f"{model_name}.joblib")
    handler.save(model_lgr, pickle_path)

    model.metadata["version"] = "1.0"
    model.framework = "sklearn"
    model.metadata["r2"] = r2

    metrics.log_metric("r2", r2)

    print(f"[train] model saved at: {model.path}")
    print(f"[train] model URI: {model.uri}")
    print(f"[train] model metadata: {model.metadata}")

    print(f"[train] metrics URI: {metrics.uri}")
    print(f"[train] metrics saved at: {metrics.path} with r2={r2:.3f}")
    print(f"[train] metrics metadata: {metrics.metadata}")


@component(
    base_image=IMAGE_URI,
)
def validate_and_publish_from_uris(
    model1_uri: str,
    model2_uri: str,
    best_model: Output[Model],
) -> None:


    from src.training import ModelTrainer
    from src.artifact_io import LocalArtifactHandler

    print(f"[validation] model1 URI: {model1_uri}")
    print(f"[validation] model2 URI: {model2_uri}")

    handler = LocalArtifactHandler()

    model1 = handler.load(model1_uri)
    model2 = handler.load(model2_uri)




    # validate_main(
    #     model1_path=model1_uri,
    #     model2_path=model2_uri,
    #     out_model_dir=best_model.path,
    # )


# @dsl.pipeline(name="vertexai-pipeline-with-parrallel-components")
# def pipeline(n_rows: int = 1000):

#     prep = preprocess(n_rows=n_rows)

#     # NOTE: parallel fan-out (two independent tasks)
#     m1 = train(dataset=prep.outputs["output_dataset"], model_name="model1")
#     m2 = train(dataset=prep.outputs["output_dataset"], model_name="model2")

#     # NOTE: converge; DO NOT pass outputs into Output params (they are auto-created)
#     vp = validate_and_publish(
#         model1=m1.outputs["model"], metrics1=m1.outputs["metrics"],
#         model2=m2.outputs["model"], metrics2=m2.outputs["metrics"],
#     )

# @dsl.pipeline(name="local-pipe")
# def local_pipeline(n_rows: int = 500):

#     preprocessed_dataset = preprocess(n_rows=n_rows)

#     print(f"Preprocessed data name: {preprocessed_dataset.outputs['output_dataset'].name}")
#     print(f"Preprocessed data at: {preprocessed_dataset.outputs['output_dataset'].path}")
#     print(f"Preprocessed data URI: {preprocessed_dataset.outputs['output_dataset'].uri}")
#     print(f"Preprocessed data metadata: {preprocessed_dataset.outputs['output_dataset'].metadata}")

    # m1 = train(dataset=preprocessed_dataset.outputs["output_dataset"], model_name="model1")
    # m2 = train(dataset=preprocessed_dataset.outputs["output_dataset"], model_name="model2")

    # print("Model 1 R2:", m1.outputs["metrics"])
    # print("Model 2 R2:", m2.outputs["metrics"])

# NOTE: smoke test
def run_local():

    local.init(runner=local.DockerRunner())
    preprocess_task = preprocess(n_rows=500)
    preprocessed_dataset = preprocess_task.outputs["output_dataset"]

    print(f"Preprocessed data name: {preprocessed_dataset.name}")
    print(f"Preprocessed data at: {preprocessed_dataset.path}")
    print(f"Preprocessed data URI: {preprocessed_dataset.uri}")
    print(f"Preprocessed data metadata: {preprocessed_dataset.metadata}")

    m1  = train(preprocessed_dataset=preprocessed_dataset, model_name="model1")
    m2  = train(preprocessed_dataset=preprocessed_dataset, model_name="model2")

    model = m1.outputs["model"]
    metrics = m1.outputs["metrics"]

    print(f"Trained model at: {model.path}")
    print(f"Trained model URI: {model.uri}")
    print(f"Model metadata: {model.metadata}")
    
    print(f"Metrics at: {metrics.path}")
    print(f"Metrics URI: {metrics.uri}")
    print(f"Metrics metadata: {metrics.metadata}")


if __name__ == "__main__":

    print("Running local smoke test...")
    run_local()
    print("Done.")