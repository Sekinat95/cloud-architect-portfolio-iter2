# tools.py

import os
from datetime import datetime, timedelta, timezone

from google.cloud import bigquery
from google.cloud import logging as cloud_logging
from google.cloud import monitoring_v3
from google.cloud import aiplatform

PROJECT_ID = os.environ.get("PROJECT_ID", "lstm-gp-xr-ue-ee")
REGION = os.environ.get("REGION", "europe-west4")
BQ_DATASET = os.environ.get("BQ_DATASET", "xr_predictions")


def get_pipeline_run_status(run_id: str) -> dict:
    """
    Queries the pipeline_runs table for a single run's metadata.
    Returns {} if the run never reached batch_inference.py (e.g. crashed earlier).
    """
    client = bigquery.Client(project=PROJECT_ID, location=REGION)
    query = f"""
        SELECT run_id, run_timestamp, pipeline_job_id, input_row_count,
               lstm_output_row_count, gp_output_row_count, status
        FROM `{PROJECT_ID}.{BQ_DATASET}.pipeline_runs`
        WHERE run_id = @run_id
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("run_id", "STRING", run_id)],
        maximum_bytes_billed=10 ** 8,
    )
    result = list(client.query(query, job_config=job_config).result())

    if not result:
        return {}

    row = result[0]
    return {
        "run_id": row.run_id,
        "run_timestamp": row.run_timestamp.isoformat() if row.run_timestamp else None,
        "pipeline_job_id": row.pipeline_job_id,
        "input_row_count": row.input_row_count,
        "lstm_output_row_count": row.lstm_output_row_count,
        "gp_output_row_count": row.gp_output_row_count,
        "status": row.status,
    }

def _resolve_job_id_and_timestamp(run_id: str, override_job_id: str = None,
                                   override_timestamp: datetime = None):
    if override_job_id or override_timestamp:
        return override_job_id, override_timestamp

    run_info = get_pipeline_run_status(run_id)
    run_ts = datetime.fromisoformat(run_info["run_timestamp"]) if run_info.get("run_timestamp") else None

    if run_ts:
        return None, run_ts

    # match on the trailing timestamp suffix, not the full run_id string
    suffix = run_id.split("-")[-1]  # e.g. "20260906155007"

    aiplatform.init(project=PROJECT_ID, location=REGION)
    for job in aiplatform.PipelineJob.list():
        display = job.display_name or ""
        resource = job.resource_name or ""
        if suffix in display or suffix in resource:
            return None, job.create_time

    return None, None

def get_logs(run_id: str, job_id: str = None, window_minutes: int = 10,
             override_timestamp: datetime = None) -> list:
    """
    Fetches ERROR/WARNING severity log entries for a run.
    If job_id is known (the numeric Vertex AI custom-training job id, e.g.
    from the console/API — NOT the KFP pipeline_job_id string), filters
    precisely by resource.labels.job_id. Otherwise falls back to a
    timestamp window, which may include unrelated jobs' log lines.
    """
    if job_id:
        filter_str = f'resource.type="ml_job" AND resource.labels.job_id="{job_id}"'
    else:
        _, run_ts = _resolve_job_id_and_timestamp(run_id, override_timestamp=override_timestamp)
        if not run_ts:
            return []
        start = (run_ts - timedelta(minutes=1)).isoformat()
        end = (run_ts + timedelta(minutes=window_minutes)).isoformat()
        filter_str = (
            f'resource.type="ml_job" '
            f'AND severity>=WARNING '
            f'AND timestamp>="{start}" AND timestamp<="{end}"'
        )

    client = cloud_logging.Client(project=PROJECT_ID)
    entries = client.list_entries(filter_=filter_str, order_by=cloud_logging.ASCENDING)

    lines = []
    for entry in entries:
        payload = entry.payload
        if isinstance(payload, dict):
            payload = payload.get("message", str(payload))
        lines.append(f"[{entry.severity}] {entry.timestamp.isoformat()} {payload}")

    return lines


def get_recent_metrics(run_id: str, override_timestamp: datetime = None) -> dict:
    job_id, run_ts = _resolve_job_id_and_timestamp(run_id, override_timestamp=override_timestamp)
    if not run_ts:
        return {}

    # resolve the actual pipeline_job_id string to filter on
    aiplatform.init(project=PROJECT_ID, location=REGION)
    suffix = run_id.split("-")[-1]
    pipeline_job_id = None
    for job in aiplatform.PipelineJob.list():
        if suffix in (job.display_name or "") or suffix in (job.resource_name or ""):
            pipeline_job_id = job.display_name
            break

    if not pipeline_job_id:
        return {}

    start_time = run_ts - timedelta(minutes=5)
    end_time = run_ts + timedelta(minutes=15)

    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{PROJECT_ID}"

    interval = monitoring_v3.TimeInterval({
        "start_time": {"seconds": int(start_time.timestamp())},
        "end_time": {"seconds": int(end_time.timestamp())},
    })

    filter_str = (
        f'metric.type="aiplatform.googleapis.com/pipelinejob/duration" '
        f'AND resource.labels.pipeline_job_id="{pipeline_job_id}"'
    )

    results = client.list_time_series(
        request={
            "name": project_name,
            "filter": filter_str,
            "interval": interval,
            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        }
    )

    for series in results:
        for point in series.points:
            return {
                "duration_seconds": point.value.int64_value,
                "resource_labels": dict(series.resource.labels),
            }

    return {}