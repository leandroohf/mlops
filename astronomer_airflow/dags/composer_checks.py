# dags/google_composer_checks.py
from __future__ import annotations

import os
from airflow.configuration import conf
from airflow.decorators import dag, task
from pendulum import datetime


@dag(
    dag_id="google_composer_checks",
    description="Print hello + show key config + ADC + GCS smoke checks",
    start_date=datetime(2024, 1, 1),
    schedule=None,          # trigger manually
    catchup=False,
    tags=["hello", "checks", "composer"],
)
def google_composer_checks():
    @task
    def say_hello():
        print("Hello from Airflow!")

    @task
    def show_config():
        # Environment variables commonly available in Composer
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        bucket = os.environ.get("GCS_BUCKET")  # Composer mounts this bucket at /home/airflow/gcs
        location = os.environ.get("COMPOSER_LOCATION") or os.environ.get("CLOUDSDK_COMPUTE_REGION")
        composer_env = os.environ.get("COMPOSER_ENVIRONMENT")

        # Airflow config values
        dags_folder = conf.get("core", "dags_folder", fallback=None)
        executor = conf.get("core", "executor", fallback=None)
        web_base_url = conf.get("webserver", "base_url", fallback=None)
        base_log_folder = (
            conf.get("logging", "base_log_folder", fallback=None)
            or conf.get("core", "base_log_folder", fallback=None)
        )

        dags_gcs_prefix = f"gs://{bucket}/dags" if bucket else None

        print("Important configuration values:")
        print({
            "project_id": project,
            "location": location,
            "composer_environment": composer_env,
            "gcs_bucket": bucket,
            "dags_gcs_prefix": dags_gcs_prefix,
            "dags_folder": dags_folder,
            "executor": executor,
            "webserver_base_url": web_base_url,
            "base_log_folder": base_log_folder,
        })

    @task
    def adc_token_info():
        """
        Smoke test for ADC (Application Default Credentials).
        Fetches a live access token and prints non-sensitive details.
        """
        import google.auth
        from google.auth.transport.requests import Request

        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        creds, project_id = google.auth.default(scopes=scopes)
        creds.refresh(Request())  # proves we can obtain a live token from metadata server

        principal = getattr(creds, "service_account_email", None) or "user ADC / unknown"
        expiry = getattr(creds, "expiry", None)
        print({
            "principal": principal,
            "default_project_id": project_id,
            "token_expiry_utc": str(expiry) if expiry else None,
            "credential_type": type(creds).__name__,
        })
        return "ok"

    @task
    def list_env_bucket_objects():
        """
        Lists a few objects from the Composer environment bucket.
        This bucket is the safest target because Composer grants
        the env service account access to it.
        """
        from airflow.providers.google.cloud.hooks.gcs import GCSHook

        bucket = os.environ.get("GCS_BUCKET")
        if not bucket:
            raise RuntimeError("GCS_BUCKET env var not found; are you running in Composer?")

        hook = GCSHook()
        # List objects under DAGs prefix (change prefix if you want to check another folder)
        objs = hook.list(bucket_name=bucket, prefix="dags/") or []
        sample = objs[:20]
        print(f"Bucket: {bucket}")
        print(f"Found {len(objs)} objects under 'dags/' (showing up to 20):")
        for o in sample:
            print(f" - {o}")
        return {"bucket": bucket, "count_under_dags": len(objs)}

    # OPTIONAL: enable this if you really want a projects listing smoke test.
    # It may require extra IAM (e.g., Viewer) and can be noisy in orgs.
    @task
    def list_accessible_projects_soft():
        try:
            from airflow.providers.google.cloud.hooks.cloud_resource_manager import CloudResourceManagerHook
            from google.cloud import resourcemanager_v3
    
            hook = CloudResourceManagerHook(api_version=3)
            client: resourcemanager_v3.ProjectsClient = hook.get_conn()
            results = client.search_projects(request=resourcemanager_v3.SearchProjectsRequest(query=""))
            projects = []
            for i, p in enumerate(results, start=1):
                projects.append({"project_id": p.project_id, "display_name": p.display_name, "state": p.state.name})
                if i >= 20:
                    break
            print(f"Found {len(projects)} accessible projects (showing up to 20):")
            for p in projects:
                print(f" - {p['project_id']} ({p['display_name']}) | state={p['state']}")
            return projects
        except Exception as e:
            print(f"[SKIP] Could not list projects (likely missing permission or API): {e}")
            return "skipped"

    # Order of execution
    h = say_hello()
    c = show_config()
    t = adc_token_info()
    g = list_env_bucket_objects()
    p = list_accessible_projects_soft() 

    h >> c >> t >> g >> p
    # To include optional projects test:
    # p = list_accessible_projects_soft()
    # t >> p  # after token check

    # end dag

dag = google_composer_checks()
