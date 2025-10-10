import json
import os
import shutil

def publish(source_model_path: str, destination_model_dir: str) -> None:
    
    print(f"[validate_and_publish] Selected model path: '{source_model_path}'")
    print(f"[validate_and_publish] Destination (best_model) dir: '{destination_model_dir}'")

    assert source_model_path != destination_model_dir, f"Source ({source_model_path}) and destination ({destination_model_dir}) directories must be different"
    assert os.path.exists(source_model_path), f"Source model path does not exist: {source_model_path}"
    assert os.path.isdir(destination_model_dir) or not os.path.exists(destination_model_dir), f"Destination model directory is not a directory: {destination_model_dir}"

    destination_model_path = os.path.join(destination_model_dir, "winner.joblib")
    print(f"[validate_and_publish] Best model saved at: '{destination_model_path}'")
    shutil.copy(source_model_path, destination_model_path)
    print(f"[validate_and_publish] Best model saved at: '{destination_model_path}'")


def _read_r2(metrics_path: str) -> float:
    with open(metrics_path, "r") as f:
        data = json.load(f)

    return float(data["r2"])

def main(model1_path: str, metrics1_path: str, model2_path: str, metrics2_path: str, out_model_dir: str) -> None:

    r2_1, r2_2 = _read_r2(metrics1_path), _read_r2(metrics2_path)

    winner_path = model1_path if r2_1 >= r2_2 else model2_path

    # NOTE: create the output directory if it doesn't exist and publish the winner model there
    os.makedirs(out_model_dir, exist_ok=True)
    publish(winner_path, out_model_dir)