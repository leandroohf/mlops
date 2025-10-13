import yaml
import pandas as pd
import numpy as np

def get_env_from_yaml(yaml_file: str) -> str:

    with open(yaml_file, "r") as f:
        cfg = yaml.safe_load(f)
        env = cfg.get("env", "dev")

    return env


def generate_fake_data(n_rows: int = 100) -> pd.DataFrame:
   
    rng = np.random.default_rng(7)
    fake_data = pd.DataFrame({
        "feature_a": rng.normal(0, 1, n_rows),
        "feature_b": rng.uniform(-1, 1, n_rows),
        "feature_c": rng.integers(0, 5, n_rows),
    })

    fake_data["target"] = (
        3 * fake_data["feature_a"]
        - 2 * fake_data["feature_b"]
        + 0.5 * fake_data["feature_c"]
        + rng.normal(0, 0.5, n_rows)
    )

    return fake_data