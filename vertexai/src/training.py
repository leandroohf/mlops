import os
import joblib
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split


class ModelTrainer():
    
    def __init__(self, model_name: str = "model1"):

        self._model_name = model_name
        self._model = None

    def fit(self,X: pd.DataFrame, y: pd.Series) -> float:

        self._model = LinearRegression().fit(X, y)
        y_pred = self._model.predict(X)
        r2 = float(r2_score(y, y_pred))

        return r2

    def predict(self, X: pd.DataFrame) -> pd.Series:

        assert self._model is not None, "Model is not trained yet. Call fit() first."

        return self._model.predict(X)
