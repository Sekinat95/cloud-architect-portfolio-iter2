# tools.py

import os
from datetime import datetime, timedelta, timezone

from google.cloud import bigquery
from google.cloud import logging as cloud_logging
from google.cloud import monitoring_v3

PROJECT_ID = os.environ.get("PROJECT_ID", "lstm-gp-xr-ue-ee")
BQ_DATASET = os.environ.get("BQ_DATASET", "xr_predictions")


def get_pipeline_run_status(run_id: str) -> dict:
    """
    Queries the pipeline_runs table for a single run's metadata.
    Returns a dict with fixed keys, or {} if run_id not found.
    """
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT run_id, run_timestamp, pipeline_job_id, input_row_count,
               lstm_output_row_count, gp_output_row_count, status
        FROM `{PROJECT_ID}.{BQ_DATASET}.pipeline_runs`
        WHERE run_id = @run_id
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("run_id", "STRING", run_id)],
        maximum_bytes_billed=10 ** 8,  # 100MB cap, cost control
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


def get_logs(run_id: str, window_minutes: int = 10) -> list:
    """
    Fetches ERROR + WARNING severity log entries around a run's timestamp.
    Requires the run's timestamp already resolved via get_pipeline_run_status
    (job_id filtering is more precise, but timestamp windowing works standalone).
    Returns a list of plain-text log lines, empty list if none found.
    """
    run_info = get_pipeline_run_status(run_id)
    if not run_info or not run_info.get("run_timestamp"):
        return []

    run_ts = datetime.fromisoformat(run_info["run_timestamp"])
    start = (run_ts - timedelta(minutes=1)).isoformat()
    end = (run_ts + timedelta(minutes=window_minutes)).isoformat()

    client = cloud_logging.Client(project=PROJECT_ID)
    filter_str = (
        f'resource.type="ml_job" '
        f'AND severity>=WARNING '
        f'AND timestamp>="{start}" AND timestamp<="{end}"'
    )
    entries = client.list_entries(filter_=filter_str, order_by=cloud_logging.ASCENDING)

    lines = []
    for entry in entries:
        payload = entry.payload
        if isinstance(payload, dict):
            payload = payload.get("message", str(payload))
        lines.append(f"[{entry.severity}] {entry.timestamp.isoformat()} {payload}")

    return lines


def get_recent_metrics(run_id: str) -> dict:
    """
    Queries Cloud Monitoring for pipelinejob/duration around the run's timestamp.
    Returns a dict with duration_seconds if found, {} otherwise.
    """
    run_info = get_pipeline_run_status(run_id)
    if not run_info or not run_info.get("run_timestamp"):
        return {}

    run_ts = datetime.fromisoformat(run_info["run_timestamp"])
    start_time = run_ts - timedelta(minutes=5)
    end_time = run_ts + timedelta(minutes=15)

    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{PROJECT_ID}"

    interval = monitoring_v3.TimeInterval(
        {
            "start_time": {"seconds": int(start_time.timestamp())},
            "end_time": {"seconds": int(end_time.timestamp())},
        }
    )

    results = client.list_time_series(
        request={
            "name": project_name,
            "filter": 'metric.type="aiplatform.googleapis.com/pipelinejob/duration"',
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