# dags/hello_dag.py
from __future__ import annotations

from airflow.decorators import dag, task
from pendulum import datetime


@dag(
    dag_id="hello",
    description="Minimal DAG: print hello",
    start_date=datetime(2024, 1, 1),
    schedule=None,          # trigger manually
    catchup=False,
    tags=["example", "hello"],
)
def hello_dag():
    @task
    def say_hello():
        print("Hello from Airflow!")

    say_hello()

dag = hello_dag()
