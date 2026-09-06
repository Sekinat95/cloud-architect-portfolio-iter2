# test_tools.py — scratch script, not part of the final agent

from tools import get_pipeline_run_status, get_logs, get_recent_metrics

RUN_ID = "c8979d0d-1048-4de3-9ced-29719a7eeadb"

print("=== get_pipeline_run_status ===")
status = get_pipeline_run_status(RUN_ID)
print(status)

print("\n=== get_logs ===")
logs = get_logs(RUN_ID)
for line in logs:
    print(line)

print("\n=== get_recent_metrics ===")
metrics = get_recent_metrics(RUN_ID)
print(metrics)