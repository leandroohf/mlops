import os
import re
import tempfile
from google.cloud import storage
import joblib
from sklearn import datasets
from sklearn.linear_model import LogisticRegression


# TODO: duplicated. fixed this later
def parse_gs_uri(uri: str):
    m = re.match(r"^gs://([^/]+)(?:/(.*))?$", uri)
    if not m:
        raise ValueError(f"Invalid GCS URI: {uri}")
    bucket, obj = m.group(1), m.group(2) or ""
    return bucket, obj

def upload_blob(gcs_path, source_file_name):
    """Uploads a file to the bucket."""

    if not gcs_path.startswith("gs://"):
        raise ValueError(f"gcs_path must start with gs://. passed: {gcs_path}")

    bucket_name, object_name = parse_gs_uri(gcs_path)

    # Initialize a storage client
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(object_name)

    blob.upload_from_filename(source_file_name)

    print(f"File {source_file_name} uploaded to {gcs_path}.")

def main():

    # NOTE: reference: https://scikit-learn.org/1.5/auto_examples/linear_model/plot_iris_logistic.html#sphx-glr-auto-examples-linear-model-plot-iris-logistic-py
    iris = datasets.load_iris()

    X = iris.data[:, :2]  # we only take the first two features.
    Y = iris.target

    logreg = LogisticRegression(C=1e5)
    logreg.fit(X, Y)

    env = os.environ.get("ENV", "unknown")

    print(f"Trained LogisticRegression model in env {env}")
    print(f"n_iter_: {logreg.n_iter_}")
    print(f"n_features_in_int_: {logreg.n_features_in_}")
    print(f"coef_: {logreg.coef_}")
    print(f"intercept_: {logreg.intercept_}")
    print(f"classes_: {logreg.classes_}")

    # TODO: save model to GCS
    gcs_path = os.environ.get("MODEL_ARTIFACTS")  # e.g. gs://my-bucket/model/model.pkl
   
    print(f"Saving model artifacts to: {gcs_path}")

    # Save the model to GCS
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        joblib.dump(logreg, tmp.name)
        tmp.close()
        upload_blob(gcs_path, tmp.name) 

if __name__ == "__main__":
    main()