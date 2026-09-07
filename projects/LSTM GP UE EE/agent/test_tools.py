# test_tools.py

from tools import get_pipeline_run_status, get_logs, get_recent_metrics

from tools import _resolve_job_id_and_timestamp
print(_resolve_job_id_and_timestamp("run-20260906155007"))

RUN_ID = "run-20260906155007"
JOB_ID = "8027070469205131264"  # numeric Vertex AI custom-training job id, from the console

print("=== get_pipeline_run_status ===")
print(get_pipeline_run_status(RUN_ID))  # expect {}

print("\n=== get_logs (job_id filtered) ===")
logs = get_logs(RUN_ID, job_id=JOB_ID)
for line in logs:
    print(line)

print("\n=== get_recent_metrics ===")
print(get_recent_metrics(RUN_ID))