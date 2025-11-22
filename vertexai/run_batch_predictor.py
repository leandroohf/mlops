from src.predictor import BatchPredictor
from src.utils import generate_fake_data, get_env_from_yaml


def main(env: str):

    test_data = generate_fake_data(n_rows=100)
    test_data.drop(columns=["target"], inplace=True)

    predictor = BatchPredictor(env=env)
    predictions = predictor.predict(test_data)
    print(f"Predictions shape: {predictions.shape}")

if __name__ == "__main__":

    env = get_env_from_yaml("latest.yaml")
    print(f"Running in env: {env}")
    main(env=env)
