from poller import list_recent_pipeline_jobs, find_failed_jobs
from tools import get_logs

failed = find_failed_jobs(list_recent_pipeline_jobs(hours=48))
for job in failed:
    logs = get_logs(job["run_id"], job_id=job["job_id"])
    print(f"--- {job['run_id']} ---")
    for line in logs:
        print(line)