import os
import numpy as np
import pandas as pd

from src.utils import generate_fake_data

class Preprocessor():

    def __init__(self, n_rows: int = 1000):

        self._n_rows = n_rows

    def fit_transform(self, raw_data: pd.DataFrame) -> "Preprocessor":

        # NOTE: Fake
        preprocessed_data = generate_fake_data(n_rows=self._n_rows)
  
        return preprocessed_data
    
    def transform(self, raw_data: pd.DataFrame) -> pd.DataFrame:

        # NOTE: Fake
        preprocessed_data = raw_data.copy()

        return preprocessed_data
