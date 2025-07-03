#!/usr/bin/env python

import subprocess
import typer
from common.utils import check_env_compliance

app = typer.Typer()

@app.command()
def main(env: str = typer.Option("local")):

    #env = 'exp/lhof/1.0.0-exp'

    assert check_env_compliance(env), f"Not valid enviroment {env}"  

    subprocess.run(["python", "1_train.py", f"--env={env}"], check=True)
    subprocess.run(["python", "2_batch_predict.py", f"--env={env}"], check=True)

if __name__ == "__main__":
    app()