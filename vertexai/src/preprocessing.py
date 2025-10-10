import os
import numpy as np
import pandas as pd


class Preprocessor():

    def __init__(self, n_rows: int = 1000):

        self._n_rows = n_rows

    def fit_transform(self, raw_data: pd.DataFrame) -> "Preprocessor":

        # NOTE: Fake
        rng = np.random.default_rng(7)
        preprocessed_data = pd.DataFrame({
            "feature_a": rng.normal(0, 1, self._n_rows),
            "feature_b": rng.uniform(-1, 1, self._n_rows),
            "feature_c": rng.integers(0, 5, self._n_rows),
        })

        preprocessed_data["target"] = (
            3 * preprocessed_data["feature_a"]
            - 2 * preprocessed_data["feature_b"]
            + 0.5 * preprocessed_data["feature_c"]
            + rng.normal(0, 0.5, self._n_rows)
        )

        return preprocessed_data
    
    def transform(self, raw_data: pd.DataFrame) -> pd.DataFrame:

        # NOTE: Fake
        preprocessed_data = raw_data.copy()

        return preprocessed_data
