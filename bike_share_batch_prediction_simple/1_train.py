import pandas as pd
import numpy as np
from pathlib import Path
import typer
import pendulum


from common.utils import check_env_compliance
from common.artifact_store import LocalArtifactStore, GCPArtifactStore

app = typer.Typer()

# NOTE: triggering the pipeline with a fake model training

@app.command()
def fake_train(
    env: str = typer.Option("local", 
    help="Environment to run in (e.g., local, dev, prod)")
    ):
    """
    Train a fake model and save artifacts to the specified environment.
    """

    assert check_env_compliance(env), f"Not valid enviroment {env}"  

    model = {"coef": np.random.rand(5).tolist(), "intercept": np.random.rand()}
    metadata = {
        "env": env,
        "trained_at": pendulum.now().to_iso8601_string(),
        "validation_date": pendulum.yesterday().to_date_string(),
        "decription": "mvp models"
        }

    artifact_store = GCPArtifactStore(env) if env != "local" else LocalArtifactStore()

    artifact_store.save(model, Path("models") / "fake_model.pkl")
    artifact_store.save(metadata, Path("models") / "fake_model_metadata.json")

    typer.echo(f"Artifacts saved using environment: {env}")

if __name__ == "__main__":
    app()
