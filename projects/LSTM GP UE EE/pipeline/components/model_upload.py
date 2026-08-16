from kfp.dsl import component, Input, Artifact


@component(
    base_image="python:3.10-slim",
    packages_to_install=[
        "google-cloud-aiplatform==1.38.1",
    ],
)
def model_upload(
    project_id: str,
    region: str,
    model_artefacts_bucket: str,
    pipeline_run_id: str,
    # Model artefact inputs
    lstm_model_input: Input[Artifact],
    gp_model_input: Input[Artifact],
):
    """
    Model upload component.

    Registers both LSTM and GP models in Vertex AI Model Registry.
    No serving container specified at registration time — container is
    assigned at deployment time when models are deployed to endpoints.

    Both models tagged with pipeline_run_id for traceability.
    No gating — both models always uploaded.
    """
    from google.cloud import aiplatform

    aiplatform.init(project=project_id, location=region)

    # ------------------------------------------------------------------ #
    # LSTM — register model artifact only
    # ------------------------------------------------------------------ #
    print("Registering LSTM model in Vertex AI Model Registry...")

    lstm_model = aiplatform.Model.upload(
        display_name="lstm-arrival-time",
        artifact_uri=f"gs://{model_artefacts_bucket}/lstm/model/",
        serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/pytorch-cpu.1-13:latest",
        labels={
            "model_type": "lstm",
            "pipeline_run_id": pipeline_run_id,
            "target": "arrival_time",
        },
    )

    print(f"LSTM model registered: {lstm_model.resource_name}")

    # ------------------------------------------------------------------ #
    # GP — register model artifact only
    # ------------------------------------------------------------------ #
    print("Registering GP model in Vertex AI Model Registry...")

    gp_model = aiplatform.Model.upload(
        display_name="gp-arrival-time",
        artifact_uri=f"gs://{model_artefacts_bucket}/gp/model/",
        serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-3:latest",
        labels={
            "model_type": "gaussian_process",
            "pipeline_run_id": pipeline_run_id,
            "target": "arrival_time",
        },
    )

    print(f"GP model registered: {gp_model.resource_name}")
    print("Both models registered in Vertex AI Model Registry.")