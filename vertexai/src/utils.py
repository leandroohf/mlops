import yaml

def get_env_from_yaml(yaml_file: str) -> str:

    with open(yaml_file, "r") as f:
        cfg = yaml.safe_load(f)
        env = cfg.get("env", "dev")

    return env