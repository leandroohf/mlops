#!/usr/bin/env python

import os
import sys
from pathlib import Path
import json
import os
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split

from src.preprocessing import Preprocessor
from src.training import ModelTrainer
from src.artifact_io import LocalArtifactHandler

def main():

    import numpy as _np
    np_ver = _np.__version__
    import pandas as _pd
    pd_ver = _pd.__version__

    print(f"[debug] Python exec : {sys.executable}")
    print(f"[debug] Python ver  : {sys.version}")
    print(f"[debug] pandas      : {pd_ver}")
    print(f"[debug] numpy       : {np_ver}")

    preprocess_dir =  "preprocessed/"
    preprocess(output_dir=preprocess_dir, n_rows=1000)
    print(f"[preprocess] done -> {preprocess_dir}")

    model_dir = "models/"
    model_name = "model1"
    r2_1 = float(train_model(dataset_dir=str(preprocess_dir), model_dir=str(model_dir), model_name=model_name))
    print(f"[train] {model_name}: r2={r2_1:.3f}")

    model_name = "model2"
    r2_2 = float(train_model(dataset_dir=str(preprocess_dir), model_dir=str(model_dir), model_name=model_name))
    print(f"[train] {model_name}: r2={r2_2:.3f}")

    # Save metrics to JSON files
    with open(model_dir + "metrics_model1.json", "w") as f:
        json.dump({"r2": r2_1}, f)

    with open(model_dir + "metrics_model2.json", "w") as f:
        json.dump({"r2": r2_2}, f)

    from src.validation import main as validate_main
    best_model_dir = "models/"
    model_path1 = model_dir + "model1.joblib"
    model_path2 = model_dir + "model2.joblib"
    Path(best_model_dir).mkdir(parents=True, exist_ok=True)
    validate_main(
        model1_path=model_path1, metrics1_path=model_dir + "metrics_model1.json",
        model2_path=model_path2, metrics2_path=model_dir + "metrics_model2.json",
        out_model_dir=best_model_dir
    )
    print(f"[validate] done -> {best_model_dir}")

if __name__ == "__main__":

    print("Running local pipeline...")
    main()