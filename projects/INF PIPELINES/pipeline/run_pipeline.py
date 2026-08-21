from kfp import compiler
from google.cloud import aiplatform, storage
import uuid
import sys
import os

sys.path.append(os.path.dirname(__file__))
from pipeline import finbert_pipeline

PROJECT_ID = "inf-pipelines"
REGION = "europe-west4"
PIPELINE_ROOT = f"gs://{PROJECT_ID}-pipeline-root"
SERVICE_ACCOUNT = f"mlops-pipeline-sa@{PROJECT_ID}.iam.gserviceaccount.com"
COMPILED_LOCAL_PATH = "pipeline.yaml"
COMPILED_GCS_BLOB = "compiled/pipeline.yaml"

RUN_ID = f"run-{uuid.uuid4().hex[:8]}"


def compile_pipeline():
    compiler.Compiler().compile(
        pipeline_func=finbert_pipeline,
        package_path=COMPILED_LOCAL_PATH
    )
    print(f"Pipeline compiled to {COMPILED_LOCAL_PATH}")


def upload_to_gcs():
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(f"{PROJECT_ID}-pipeline-root")
    blob = bucket.blob(COMPILED_GCS_BLOB)
    blob.upload_from_filename(COMPILED_LOCAL_PATH)
    print(f"Uploaded {COMPILED_LOCAL_PATH} to gs://{PROJECT_ID}-pipeline-root/{COMPILED_GCS_BLOB}")


def submit_pipeline():
    aiplatform.init(project=PROJECT_ID, location=REGION)

    job = aiplatform.PipelineJob(
        display_name=f"finbert-inference-{RUN_ID}",
        template_path=f"gs://{PROJECT_ID}-pipeline-root/{COMPILED_GCS_BLOB}",
        pipeline_root=PIPELINE_ROOT,
        parameter_values={"pipeline_run_id": RUN_ID},
        enable_caching=False
    )

    print(f"Submitting pipeline run: {RUN_ID}")
    job.submit(service_account=SERVICE_ACCOUNT)
    print(f"Pipeline submitted: {RUN_ID}")
    job.wait()  # blocks until pipeline job completes
    print("Pipeline run completed.")
    #print(f"Pipeline submitted: {RUN_ID}")
    print(f"Monitor: https://console.cloud.google.com/vertex-ai/pipelines?project={PROJECT_ID}")


def main():
    compile_pipeline()
    upload_to_gcs()
    submit_pipeline()


if __name__ == "__main__":
    main()