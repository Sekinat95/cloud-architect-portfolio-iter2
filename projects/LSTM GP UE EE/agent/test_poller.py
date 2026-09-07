# test_poller.py — scratch script, same pattern as test_tools.py
from poller import list_recent_pipeline_jobs, find_failed_jobs

jobs = list_recent_pipeline_jobs(hours=48)  # widen window since your test run was a few days back
print(f"Found {len(jobs)} recent jobs")

failed = find_failed_jobs(jobs)
print(f"Found {len(failed)} failed jobs")
for f in failed:
    print(f)