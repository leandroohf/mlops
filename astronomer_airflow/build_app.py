#!/usr/bin/env python3

import os
import subprocess
from typing import  List

from dotenv import dotenv_values

config = dotenv_values(".env")

IMAGE_NAME = config.get("TRAINING_IMAGE")

def build_command() -> List[str]:

    print(f"Building Docker image: {IMAGE_NAME}")
    docker_cmd = [
        "docker", "buildx", "build",
        "--platform", "linux/amd64",
        "-t", f"{IMAGE_NAME}",
        "-f", "Dockerfile_vertexai_image",
        "--push",
        "." # context
    ]

    print(f"Running command: {' '.join(docker_cmd)}")

    return docker_cmd

def main():

    docker_cmd = build_command()
    subprocess.run(docker_cmd, check=True)
    
if __name__ == "__main__":
    main()
