import os
from typing import Any
import pandas as pd
from sklearn.metrics import r2_score

from src.artifact_io import LocalArtifactHandler
from src.preprocessing import Preprocessor

from sklearn.model_selection import train_test_split
from src.training import ModelTrainer

def run_preprocess(output_dir: str, n_rows: int = 1000) -> pd.DataFrame:

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


def get_target_and_features(df: pd.DataFrame):
    X = df[["feature_a", "feature_b", "feature_c"]]
    y = df["target"]
    return X, y

def train_model(dataset_dir: str, model_dir: str, model_name: str) -> float:

    handler = LocalArtifactHandler()
    parquet_path = os.path.join(dataset_dir, "preprocessed.parquet")
    preprocessed_data = handler.load(parquet_path)

    X, y = get_target_and_features(preprocessed_data)

    X_train, _, y_train, _ = train_test_split(X, y, test_size=0.2)

    model = ModelTrainer(model_name=model_name)
    r2 = model.fit(X_train, y_train)

    model_path = os.path.join(model_dir, f"{model_name}.joblib")
    print(f"Saving model to {model_path}")
    handler.save(model, model_path)

    return r2

def validate_model(X: pd.DataFrame, y: pd.Series, model: Any) -> float:

    y_pred = model.predict(X)
    r2 = float(r2_score(y, y_pred))
    print(f"Model R2 on test set: {r2:.3f}")

    return r2

def publish_model(model_path: str, model_name: str):
    """Placeholder for model publishing logic."""
    print(f"Publishing model {model_name} from {model_path}")
    # Implement actual publishing logic here (e.g., upload to a model registry or cloud service)
    pass