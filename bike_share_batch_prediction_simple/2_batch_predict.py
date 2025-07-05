import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import typer
import pendulum

from common.utils import check_env_compliance
from common.artifact_store import LocalArtifactStore, GCPArtifactStore

app = typer.Typer()

# NA di=uvida desista

@app.command()
def fake_predict(
    env: str = typer.Option("local", 
    help="Environment to run in (e.g., local, dev, prod)")
    ):
    """
    Batch predict for fake model
    """

    assert check_env_compliance(env), f"Not valid enviroment {env}"    

    now = pendulum.now()
    station_ids = [f"station_{i}" for i in range(10)]

    predictions = pd.DataFrame({
        "station_id": station_ids,
        "net_change": np.random.randint(-5, 6, size=10),
        "prediction_time": now.to_iso8601_string()
    })

    avro_schema = {
        "doc": "MVP: Fake bike share prediction",
        "name": "BikePrediction",
        "namespace": "ml.model.BikePrediction.batch",
        "type": "record",
        "fields": [
            {"name": "station_id", "type": "string"},
            {"name": "net_change", "type": "int"},
            {"name": "prediction_time", "type": "string"}
        ]
    }

    artifact_store = GCPArtifactStore(env) if env != "local" else LocalArtifactStore()

    pred_path = f"{now.format('YYYYMMDDHHmm')}_preds.avro"
    artifact_store.save(predictions, Path("inference") / pred_path, 
                        avro_schema)
    
    typer.echo(f"Saved predictions to {pred_path} using enviroment: {env}")

if __name__ == "__main__":
    app()
