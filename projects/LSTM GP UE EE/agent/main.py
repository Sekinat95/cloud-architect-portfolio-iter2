from poller import list_recent_pipeline_jobs, find_failed_jobs
from graph import app


from poller import list_recent_pipeline_jobs, find_failed_jobs
from graph import app

def run_once():
    failed = find_failed_jobs(list_recent_pipeline_jobs(hours=48))
    for job in failed:
        result = app.invoke({
            "run_id": job["run_id"], "job_id": job.get("job_id"),
            "logs": None, "diagnosis": None, "recommendation": None,
            "confidence": None, "next_action": None, "iteration": 0,
        })
        print(result["diagnosis"], result["recommendation"])

if __name__ == "__main__":
    run_once()  # later: loop with sleep, or trigger via scheduler
