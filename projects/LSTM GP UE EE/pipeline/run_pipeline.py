"""
run_pipeline.py

Compiles the XR MLOps pipeline and submits it to Vertex AI Pipelines.

Usage:
    python run_pipeline.py

Run from the pipeline/ directory:
    cd ~/cloud-architect-portfolio/projects/06-phd-to-gcp-xr-ml-drx/pipeline
    python run_pipeline.py
"""

import os
import uuid
from datetime import datetime

from kfp import compiler
from google.cloud import aiplatform

from pipeline import xr_mlops_pipeline

# ------------------------------------------------------------------ #
# Config
# ------------------------------------------------------------------ #
PROJECT_ID = "lstm-gp-xr-ue-ee"
REGION = "europe-west4"

RAW_DATA_BUCKET = f"{PROJECT_ID}-raw-data"
PROCESSED_BUCKET = f"{PROJECT_ID}-processed-data"
MODEL_ARTEFACTS_BUCKET = f"{PROJECT_ID}-model-artefacts"
PIPELINE_ROOT_BUCKET = f"{PROJECT_ID}-pipeline-root"

PIPELINE_ROOT = f"gs://{PIPELINE_ROOT_BUCKET}/pipeline-runs"
COMPILED_PIPELINE_PATH = "pipeline.yaml"

SERVICE_ACCOUNT = f"full-mlops-pipeline-sa@{PROJECT_ID}.iam.gserviceaccount.com"

# Unique run ID per submission
RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d%H%M%S")
PIPELINE_RUN_ID = f"run-{RUN_TIMESTAMP}"

# ------------------------------------------------------------------ #
# Step 1 — Compile pipeline
# ------------------------------------------------------------------ #
print(f"Compiling pipeline to {COMPILED_PIPELINE_PATH}...")
compiler.Compiler().compile(
    pipeline_func=xr_mlops_pipeline,
    package_path=COMPILED_PIPELINE_PATH,
)
print("Compilation complete.")

# ------------------------------------------------------------------ #
# Step 2 — Upload compiled pipeline to GCS
# ------------------------------------------------------------------ #
COMPILED_GCS_PATH = f"gs://{PIPELINE_ROOT_BUCKET}/compiled/pipeline.yaml"
os.system(f"gcloud storage cp {COMPILED_PIPELINE_PATH} {COMPILED_GCS_PATH}")
print(f"Pipeline YAML uploaded to {COMPILED_GCS_PATH}")

# ------------------------------------------------------------------ #
# Step 3 — Submit pipeline run to Vertex AI
# ------------------------------------------------------------------ #
print(f"Submitting pipeline run: {PIPELINE_RUN_ID}...")

aiplatform.init(project=PROJECT_ID, location=REGION)

job = aiplatform.PipelineJob(
    display_name=f"xr-mlops-pipeline-{RUN_TIMESTAMP}",
    template_path=COMPILED_PIPELINE_PATH,
    pipeline_root=PIPELINE_ROOT,
    parameter_values={
        "project_id": PROJECT_ID,
        "region": REGION,
        "raw_data_bucket": RAW_DATA_BUCKET,
        "processed_bucket": PROCESSED_BUCKET,
        "model_artefacts_bucket": MODEL_ARTEFACTS_BUCKET,
        "pipeline_root_bucket": PIPELINE_ROOT_BUCKET,
        "train_gcs_path": "xr-traffic/concatenated_df_DN_train.csv",
        "test_gcs_path": "xr-traffic/concatenated_df_DN_test.csv",
        "bq_dataset": "xr_predictions",
        "pipeline_run_id": PIPELINE_RUN_ID,
        "model_version": "v1",
        "lstm_lookback": 1,
        "gp_n_samples": 5000,#10000,
        "gp_train_prop": 0.7,
        "lstm_input_size": 1,
        "lstm_hidden_size": 200,
        "lstm_num_stacked_layers": 1,
        "lstm_batch_size": 128,
        "lstm_num_epochs": 18,#600,
        "lstm_learning_rate": 0.004,
        "gp_n_restarts_optimizer": 10,
        "gp_normalize_y": True,
    },
    enable_caching=True,
)

job.submit(service_account=SERVICE_ACCOUNT)

print(f"Pipeline submitted successfully.")
print(f"Run ID:      {PIPELINE_RUN_ID}")
print(f"Display name: xr-mlops-pipeline-{RUN_TIMESTAMP}")
print(f"Monitor at:  https://console.cloud.google.com/vertex-ai/pipelines/runs?project={PROJECT_ID}")