from kfp.dsl import component

@component(
    base_image="python:3.10",
    packages_to_install=["google-cloud-aiplatform", "google-cloud-storage", "huggingface_hub"]
)
def model_upload(
    project_id: str,
    region: str,
    model_bucket: str,
    pipeline_run_id: str
) -> str:
    """
    Downloads ProsusAI/finbert raw files from HuggingFace Hub,
    uploads them to GCS, then registers the model in Vertex AI
    Model Registry pointing at the GCS artifact_uri (no HF Hub
    dependency at serving time).
    """
    import os
    from huggingface_hub import snapshot_download
    from google.cloud import storage
    from google.cloud import aiplatform

    CONTAINER_URI = "us-docker.pkg.dev/deeplearning-platform-release/gcr.io/huggingface-pytorch-inference-cu121.2-2.transformers.4-44.ubuntu2204.py311"
    GCS_PREFIX = f"finbert/{pipeline_run_id}"

    # Download raw HF model files locally
    local_dir = snapshot_download(repo_id="ProsusAI/finbert", local_dir="/tmp/finbert")
    print(f"Downloaded FinBERT files to {local_dir}")

    # Upload to GCS
    client = storage.Client(project=project_id)
    bucket = client.bucket(model_bucket)

    for filename in os.listdir(local_dir):
        local_path = os.path.join(local_dir, filename)
        if os.path.isfile(local_path):
            blob = bucket.blob(f"{GCS_PREFIX}/{filename}")
            blob.upload_from_filename(local_path)
            print(f"Uploaded {filename} to gs://{model_bucket}/{GCS_PREFIX}/{filename}")

    artifact_uri = f"gs://{model_bucket}/{GCS_PREFIX}"

    aiplatform.init(project=project_id, location=region)

    uploaded_model = aiplatform.Model.upload(
        display_name=f"finbert-inference-{pipeline_run_id}",
        artifact_uri=artifact_uri,
        serving_container_image_uri=CONTAINER_URI,
        serving_container_environment_variables={
            "HF_TASK": "text-classification",
        },
        serving_container_ports=[8080],
        description="ProsusAI/finbert financial sentiment classifier, GCS-backed artifact.",
        labels={
            "model": "finbert",
            "framework": "pytorch",
        }
    )

    print(f"Model registered: {uploaded_model.resource_name}")
    print(f"Artifact URI: {artifact_uri}")
    return uploaded_model.resource_name