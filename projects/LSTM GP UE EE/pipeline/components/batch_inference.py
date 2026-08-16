from kfp.dsl import component, Input, Output, Artifact


@component(
    base_image="python:3.10-slim",
    packages_to_install=[
        "numpy==1.26.4",
        "pandas==2.1.4",
        "torch==2.1.2",
        "scikit-learn==1.3.2",
        "google-cloud-storage==2.14.0",
        "google-cloud-bigquery==3.14.1",
        "pyarrow==14.0.2",
    ],
)
def batch_inference(
    project_id: str,
    processed_bucket: str,
    model_artefacts_bucket: str,
    bq_dataset: str,
    pipeline_run_id: str,
    model_version: str,
    # Model artefact inputs
    lstm_model_input: Input[Artifact],
    gp_model_input: Input[Artifact],
    # Outputs
    lstm_inference_output: Output[Artifact],
    gp_inference_output: Output[Artifact],
    # Config
    lstm_lookback: int = 1,
):
    """
    Batch inference component.

    Runs batch prediction for both LSTM and GP models on the test set.
    Loads X_test, y_test, and app_test from processed_bucket — all
    produced by the preprocessing component, no index alignment needed.

    Writes predictions + actuals + residuals to BigQuery:
    - xr_predictions.lstm_predictions
    - xr_predictions.gp_predictions
    """
    import io
    import pickle
    import numpy as np
    import pandas as pd
    import torch
    from google.cloud import storage, bigquery
    from datetime import datetime, timezone

    gcs_client = storage.Client(project=project_id)
    bq_client = bigquery.Client(project=project_id)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def download_bytes(bucket_name: str, blob_path: str) -> bytes:
        return gcs_client.bucket(bucket_name).blob(blob_path).download_as_bytes()

    def load_npy(bucket_name: str, blob_path: str) -> np.ndarray:
        return np.load(io.BytesIO(download_bytes(bucket_name, blob_path)), allow_pickle=False)

    def load_npy_str(bucket_name: str, blob_path: str) -> np.ndarray:
        # App arrays contain strings — allow_pickle required
        return np.load(io.BytesIO(download_bytes(bucket_name, blob_path)), allow_pickle=True)

    def write_to_bigquery(df: pd.DataFrame, table_id: str):
        table_ref = f"{project_id}.{bq_dataset}.{table_id}"
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )
        job = bq_client.load_table_from_dataframe(df, table_ref, job_config=job_config)
        job.result()
        print(f"Written {len(df)} rows to {table_ref}")

    run_timestamp = datetime.now(timezone.utc)

    # ------------------------------------------------------------------ #
    # Step 1 — LSTM batch inference
    # ------------------------------------------------------------------ #
    print("=== LSTM Batch Inference ===")

    X_test_lstm = load_npy(processed_bucket, "lstm/test/X_test.npy")
    y_test_lstm = load_npy(processed_bucket, "lstm/test/y_test.npy")
    app_test_lstm = load_npy_str(processed_bucket, "lstm/test/app_test.npy")

    scaler = pickle.loads(download_bytes(model_artefacts_bucket, "lstm/model/lstm_scaler.pkl"))

    model_bytes = download_bytes(model_artefacts_bucket, "lstm/model/model.pt")
    lstm_model = torch.jit.load(io.BytesIO(model_bytes))
    lstm_model.eval()

    X_test_t = torch.tensor(X_test_lstm).float()
    with torch.no_grad():
        preds_scaled = lstm_model(X_test_t).numpy().flatten()

    def inverse_transform(vals_scaled: np.ndarray, scaler, lookback: int) -> np.ndarray:
        dummies = np.zeros((len(vals_scaled), lookback + 1))
        dummies[:, 0] = vals_scaled
        return scaler.inverse_transform(dummies)[:, 0]

    lstm_preds = inverse_transform(preds_scaled, scaler, lstm_lookback)
    lstm_actuals = inverse_transform(y_test_lstm.flatten(), scaler, lstm_lookback)
    lstm_features = inverse_transform(X_test_lstm.reshape(-1), scaler, lstm_lookback)

    residuals_lstm = lstm_actuals - lstm_preds
    squared_errors_lstm = residuals_lstm ** 2

    lstm_df = pd.DataFrame({
        "sample_index":     np.arange(len(lstm_preds)),
        "time_t_minus_1":   lstm_features,
        "actual_time_t":    lstm_actuals,
        "predicted_time_t": lstm_preds,
        "residual":         residuals_lstm,
        "squared_error":    squared_errors_lstm,
        "app":              app_test_lstm,
        "run_id":           pipeline_run_id,
        "run_timestamp":    pd.to_datetime(run_timestamp, utc=True),
        "model_version":    model_version,
    })

    print(f"LSTM predictions shape: {lstm_df.shape}")
    print(f"LSTM test RMSE: {np.sqrt(squared_errors_lstm.mean()):.6f}")

    write_to_bigquery(lstm_df, "lstm_predictions")
    lstm_inference_output.uri = f"gs://{model_artefacts_bucket}/lstm/inference/"

    # ------------------------------------------------------------------ #
    # Step 2 — GP batch inference
    # ------------------------------------------------------------------ #
    print("=== GP Batch Inference ===")

    X_test_gp = load_npy(processed_bucket, "gp/test/X_test.npy")
    y_test_gp = load_npy(processed_bucket, "gp/test/y_test.npy")
    app_test_gp = load_npy_str(processed_bucket, "gp/test/app_test.npy")

    gp_model = pickle.loads(download_bytes(model_artefacts_bucket, "gp/model/model.pkl"))

    gp_preds = gp_model.predict(X_test_gp).flatten()
    gp_actuals = y_test_gp.flatten()

    residuals_gp = gp_actuals - gp_preds
    squared_errors_gp = residuals_gp ** 2

    gp_df = pd.DataFrame({
        "sample_index":     np.arange(len(gp_preds)),
        "time_t_minus_1":   X_test_gp.flatten(),
        "actual_time_t":    gp_actuals,
        "predicted_time_t": gp_preds,
        "residual":         residuals_gp,
        "squared_error":    squared_errors_gp,
        "app":              app_test_gp,
        "run_id":           pipeline_run_id,
        "run_timestamp":    pd.to_datetime(run_timestamp, utc=True),
        "model_version":    model_version,
    })

    print(f"GP predictions shape: {gp_df.shape}")
    print(f"GP test RMSE: {np.sqrt(squared_errors_gp.mean()):.6f}")

    write_to_bigquery(gp_df, "gp_predictions")
    gp_inference_output.uri = f"gs://{model_artefacts_bucket}/gp/inference/"

    print("=== Batch inference complete ===")