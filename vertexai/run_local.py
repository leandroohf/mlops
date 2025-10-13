#!/usr/bin/env python

import os
import shutil
import sys
from pathlib import Path
import json
import os
import joblib
import pandas as pd

from src.executor import train_model, run_preprocess

def publish_local(source_model_path: str, destination_model_dir: str) -> None:
    
    print(f"[validate_and_publish] Selected model path: '{source_model_path}'")
    print(f"[validate_and_publish] Destination (best_model) dir: '{destination_model_dir}'")

    assert source_model_path != destination_model_dir, f"Source ({source_model_path}) and destination ({destination_model_dir}) directories must be different"
    assert os.path.exists(source_model_path), f"Source model path does not exist: {source_model_path}"
    assert os.path.isdir(destination_model_dir) or not os.path.exists(destination_model_dir), f"Destination model directory is not a directory: {destination_model_dir}"

    # NOTE: vertexai model resitry expect that the model file is named 'model.joblib'
    destination_model_path = os.path.join(destination_model_dir, "model.joblib")
    print(f"[validate_and_publish] Best model saved at: '{destination_model_path}'")
    shutil.copy(source_model_path, destination_model_path)
    print(f"[validate_and_publish] Best model saved at: '{destination_model_path}'")


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
    run_preprocess(output_dir=preprocess_dir, n_rows=1000)
    print(f"[preprocess] done -> {preprocess_dir}")

    model_dir = "models/"
    model_name1 = "model1"
    r2_1 = train_model(dataset_dir=str(preprocess_dir), model_dir=str(model_dir), model_name=model_name1)
    print(f"[train] {model_name1}: r2={r2_1:.3f}")

    model_name2 = "model2"
    r2_2 = train_model(dataset_dir=str(preprocess_dir), model_dir=str(model_dir), model_name=model_name2)
    print(f"[train] {model_name2}: r2={r2_2:.3f}")

    winner_model = model_name1 if r2_1 >= r2_2 else model_name2
    winner_path = os.path.join(model_dir, f"{winner_model}.joblib")

    best_model_dir = model_dir
    Path(best_model_dir).mkdir(parents=True, exist_ok=True)
    publish_local(source_model_path=winner_path, destination_model_dir=best_model_dir)
    

if __name__ == "__main__":

    print("Running local pipeline...")
    main()