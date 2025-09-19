# dags/gcp_adc_list_projects_smoke.py
from __future__ import annotations
import os

from airflow.decorators import dag, task
from pendulum import datetime


@dag(
    dag_id="gcp_adc_list_projects_smoke",
    start_date=datetime(2021, 1, 1),
    schedule=None,
    catchup=False,
    tags=["gcp", "smoke", "adc"],
)
def gcp_adc_list_projects_smoke():
    @task
    def check_adc_env() -> str:
        path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        if not path:
            raise RuntimeError(
                "GOOGLE_APPLICATION_CREDENTIALS is not set inside the container."
            )
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"GOOGLE_APPLICATION_CREDENTIALS='{path}', but file not found in container."
            )
        print(f"ADC file is visible in container: {path}")
        return path

    @task
    def auth_token_refresh(_: str) -> str:
        import google.auth
        from google.auth.transport.requests import Request

        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        creds, project_id = google.auth.default(scopes=scopes)
        creds.refresh(Request())  # proves the creds can obtain a live token
        who = getattr(creds, "service_account_email", None) or "user ADC"
        print(f"Cred type: {type(creds).__name__} | Principal: {who}")
        print(f"Token expiry (UTC): {creds.expiry}")
        print(f"(Optional) Detected default project_id: {project_id}")
        return "ok"

    @task
    def list_projects(_: str):
        from google.cloud import resourcemanager_v3
        client = resourcemanager_v3.ProjectsClient()

        results = client.search_projects(request=resourcemanager_v3.SearchProjectsRequest(query=""))
        projects = []
        for i, p in enumerate(results, start=1):
            projects.append({"project_id": p.project_id, "display_name": p.display_name, "state": p.state.name})
            if i >= 20:
                break
        print(f"Found {len(projects)} projects (showing up to 20):")
        for p in projects:
            print(f" - {p['project_id']} ({p['display_name']}) | state={p['state']}")
        return projects

    path = check_adc_env()
    token = auth_token_refresh(path)
    list_projects(token)

gcp_adc_list_projects_smoke()
