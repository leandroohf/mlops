# dags/package_smoke_faker.py
from __future__ import annotations

import os
from airflow.decorators import dag, task
from pendulum import datetime


@dag(
    dag_id="package_smoke_faker_and_write_data_checks",
    description="Smoke test that requires an extra PyPI package (Faker) and can save data into the bucket",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["smoke", "packages", "faker"],
)
def package_smoke_faker():
    @task
    def import_and_version() -> str:
        # NOTE: This will fail if Faker is NOT installed in the Composer env
        import faker  # NOTE: faker is python package to generate fake data for you
        from faker import Faker

        print(f"Imported Faker OK. Version: {getattr(Faker, '__version__', 'unknown')}")
        return "ok"

    @task
    def generate_csv(_: str) -> str:
        """
        Generate a tiny CSV with fake data in the Composer env bucket.
        No extra libs: just stdlib + Faker.
        """
        from faker import Faker
        import csv

        fake = Faker()
        bucket = os.environ.get("GCS_BUCKET")
        if not bucket:
            raise RuntimeError("GCS_BUCKET env var not set; are we in Composer?")

        out_dir = "/home/airflow/gcs/data/faker_smoke"
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "sample.csv")

        rows = [
            {"name": fake.name(), "email": fake.email(), "country": fake.country()}
            for _ in range(10)
        ]
        with open(out_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["name", "email", "country"])
            w.writeheader()
            w.writerows(rows)

        # NOTE: Also checks if we can write to the /home/airflow/gcs/data folder
        print(f"Wrote {len(rows)} rows to {out_path}")
        print(f"(Should sync to gs://{bucket}/data/faker_smoke/sample.csv)")
        return out_path

    ok = import_and_version()
    generate_csv(ok)


dag = package_smoke_faker()
