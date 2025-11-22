import sys
from time import perf_counter
from typing import Tuple
from dotenv import dotenv_values
import pandas as pd

from src.artifact_io import LocalArtifactHandler, GCSArtifactHandler

from loguru import logger
import os

from src.utils import get_env_from_yaml
from src.executor import get_target_and_features

ENV = get_env_from_yaml("latest.yaml")
config = dotenv_values(".env")
BUCKET_NAME = config.get("BUCKET_NAME")


class BatchPredictor():

    def __init__(self, env: str = ENV):

        logger.info(f"Loading => env: {env}")

        self.env = env

        handler =  LocalArtifactHandler() if self.env == "local" else GCSArtifactHandler(
                                bucket_name=os.getenv("BUCKET_NAME", ""),
                                root_path=f"vertexai/{env}")

        self.model = handler.load("models/best.joblib")
        logger.info("Model loaded.")

    def preprocessing(self, raw_data: pd.DataFrame) -> pd.DataFrame:

        preprocessed_data = raw_data.copy()

        X, _ = get_target_and_features(preprocessed_data)

        return X

    def predict(self, X: pd.DataFrame) -> pd.Series:
        y_pred = self.model.predict(X)
        return y_pred