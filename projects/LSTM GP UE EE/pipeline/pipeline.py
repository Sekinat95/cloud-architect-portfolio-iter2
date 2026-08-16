from kfp import dsl
from kfp.dsl import pipeline

from components.preprocessing import preprocessing
from components.lstm_training import lstm_training
from components.gp_training import gp_training
from components.evaluate import evaluate
from components.model_upload import model_upload
from components.batch_inference import batch_inference


@pipeline(
    name="xr-traffic-mlops-pipeline",
    description="Full MLOps pipeline for XR network traffic arrival time prediction. "
                "Trains LSTM and GP Regressor models in parallel, evaluates RMSE, "
                "registers both models in Vertex AI Model Registry, runs batch inference, "
                "and writes predictions to BigQuery.",
)
def xr_mlops_pipeline(
    # GCP config
    project_id: str,
    region: str,
    # Buckets
    raw_data_bucket: str,
    processed_bucket: str,
    model_artefacts_bucket: str,
    pipeline_root_bucket: str,
    # Data paths (relative to raw_data_bucket)
    train_gcs_path: str = "xr-traffic/concatenated_df_DN_train.csv",
    test_gcs_path: str = "xr-traffic/concatenated_df_DN_test.csv",
    # BigQuery
    bq_dataset: str = "xr_predictions",
    # Pipeline run metadata
    pipeline_run_id: str = "run-001",
    model_version: str = "v1",
    # Preprocessing config
    lstm_lookback: int = 1,
    gp_n_samples: int = 1000, #50000,
    gp_train_prop: float = 0.7,
    # LSTM hyperparameters
    lstm_input_size: int = 1,
    lstm_hidden_size: int = 200,
    lstm_num_stacked_layers: int = 1,
    lstm_batch_size: int = 128,
    lstm_num_epochs: int = 18,#600,
    lstm_learning_rate: float = 0.004,
    # GP hyperparameters
    gp_n_restarts_optimizer: int = 10,
    gp_normalize_y: bool = True,
):
    # ------------------------------------------------------------------ #
    # Stage 1 — Preprocessing
    # ------------------------------------------------------------------ #
    # preprocess_task = preprocessing(
    #     project_id=project_id,
    #     raw_data_bucket=raw_data_bucket,
    #     train_gcs_path=train_gcs_path,
    #     test_gcs_path=test_gcs_path,
    #     processed_bucket=processed_bucket,
    #     lstm_lookback=lstm_lookback,
    #     gp_n_samples=gp_n_samples,
    #     gp_train_prop=gp_train_prop,
    # )
    ####
    preprocess_task = preprocessing(
    project_id=project_id,
    raw_data_bucket=raw_data_bucket,
    train_gcs_path=train_gcs_path,
    test_gcs_path=test_gcs_path,
    processed_bucket=processed_bucket,
    bq_dataset=bq_dataset,
    pipeline_run_id=pipeline_run_id,
)

    # ------------------------------------------------------------------ #
    # Stage 2 — Parallel training (LSTM and GP run independently)
    # ------------------------------------------------------------------ #
    lstm_train_task = lstm_training(
        project_id=project_id,
        model_artefacts_bucket=model_artefacts_bucket,
        lstm_train_input=preprocess_task.outputs["lstm_train_output"],
        lstm_test_input=preprocess_task.outputs["lstm_test_output"],
        lstm_scaler_input=preprocess_task.outputs["lstm_scaler_output"],
        input_size=lstm_input_size,
        hidden_size=lstm_hidden_size,
        num_stacked_layers=lstm_num_stacked_layers,
        batch_size=lstm_batch_size,
        num_epochs=lstm_num_epochs,
        learning_rate=lstm_learning_rate,
        lookback=lstm_lookback,
    )#.set_accelerator_type("NVIDIA_TESLA_T4").set_accelerator_limit(1)

    gp_train_task = gp_training(
        project_id=project_id,
        model_artefacts_bucket=model_artefacts_bucket,
        gp_train_input=preprocess_task.outputs["gp_train_output"],
        gp_test_input=preprocess_task.outputs["gp_test_output"],
        n_restarts_optimizer=gp_n_restarts_optimizer,
        normalize_y=gp_normalize_y,
    ).set_memory_request("40G").set_memory_limit("52G").set_cpu_request("7").set_cpu_limit("8")

    # ------------------------------------------------------------------ #
    # Stage 3 — Evaluate: log RMSE for both models side by side
    # ------------------------------------------------------------------ #
    evaluate_task = evaluate(
        lstm_metrics_input=lstm_train_task.outputs["lstm_metrics"],
        gp_metrics_input=gp_train_task.outputs["gp_metrics"],
    )

    # ------------------------------------------------------------------ #
    # Stage 4 — Model upload: register both models in Vertex AI Registry
    # ------------------------------------------------------------------ #
    upload_task = model_upload(
        project_id=project_id,
        region=region,
        model_artefacts_bucket=model_artefacts_bucket,
        pipeline_run_id=pipeline_run_id,
        lstm_model_input=lstm_train_task.outputs["lstm_model_output"],
        gp_model_input=gp_train_task.outputs["gp_model_output"],
    )
    # Ensure evaluate runs before upload — upload depends on evaluate
    upload_task.after(evaluate_task)

    # ------------------------------------------------------------------ #
    # Stage 5 — Batch inference: predictions written to BigQuery
    # ------------------------------------------------------------------ #
    batch_task = batch_inference(
        project_id=project_id,
        processed_bucket=processed_bucket,
        model_artefacts_bucket=model_artefacts_bucket,
        bq_dataset=bq_dataset,
        pipeline_run_id=pipeline_run_id,
        model_version=model_version,
        lstm_model_input=lstm_train_task.outputs["lstm_model_output"],
        gp_model_input=gp_train_task.outputs["gp_model_output"],
        lstm_lookback=lstm_lookback,
    )
    # Batch inference runs after upload is complete
    batch_task.after(upload_task)