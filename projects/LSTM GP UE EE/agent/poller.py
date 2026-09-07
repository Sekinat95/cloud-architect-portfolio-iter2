# poller.py
import os
import re
from datetime import datetime, timedelta, timezone
# poller.py — add this import
from google.cloud import logging as cloud_logging

from google.cloud import aiplatform
from google.cloud.aiplatform_v1.types import PipelineState

PROJECT_ID = os.environ.get("PROJECT_ID", "lstm-gp-xr-ue-ee")
REGION = os.environ.get("REGION", "europe-west4")





def resolve_ml_job_id(run_id: str) -> str:
    """
    Given a run_id (e.g. "run-20260906155007"), finds the underlying
    ml_job's numeric job_id by searching Cloud Logging for the
    executor_input JSON that references it (logged by the KFP executor
    on job startup).
    """
    client = cloud_logging.Client(project=PROJECT_ID)
    filter_str = f'resource.type="ml_job" AND jsonPayload.message:"{run_id}"'
    entries = list(client.list_entries(filter_=filter_str, max_results=1))
    if entries:
        return entries[0].resource.labels.get("job_id")
    return None


def find_failed_jobs(jobs: list) -> list:
    failed = []
    for job in jobs:
        if job.state == PipelineState.PIPELINE_STATE_FAILED:
            match = re.search(r"(\d{14})$", job.display_name or "")
            run_id_suffix = match.group(1) if match else None
            run_id = f"run-{run_id_suffix}" if run_id_suffix else job.display_name

            resolved_job_id = resolve_ml_job_id(run_id)

            failed.append({
                "run_id": run_id,
                "job_id": resolved_job_id,
                "create_time": job.create_time,
                "display_name": job.display_name,
                "resource_name": job.resource_name,
            })
    return failed

def list_recent_pipeline_jobs(hours: int = 24) -> list:
    """
    Returns all Vertex AI PipelineJob objects created within the last N hours.
    """
    aiplatform.init(project=PROJECT_ID, location=REGION)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    jobs = aiplatform.PipelineJob.list()
    recent = [job for job in jobs if job.create_time >= cutoff]
    return recent
