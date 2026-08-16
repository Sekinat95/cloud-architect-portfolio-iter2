from kfp.dsl import component, Output, Artifact


@component(
    base_image="python:3.10-slim",
    packages_to_install=[
        "pandas==2.1.4",
        "numpy==1.26.4",
        "scikit-learn==1.3.2",
        "google-cloud-storage==2.14.0",
        "google-cloud-bigquery==3.14.1",
    ],
)
# def preprocessing(
#     project_id: str,
#     raw_data_bucket: str,
#     train_gcs_path: str,
#     test_gcs_path: str,
#     processed_bucket: str,
#     # LSTM outputs
#     lstm_train_output: Output[Artifact],
#     lstm_test_output: Output[Artifact],
#     lstm_scaler_output: Output[Artifact],
#     # GP outputs
#     gp_train_output: Output[Artifact],
#     gp_test_output: Output[Artifact],
#     # Config
#     lstm_lookback: int = 1,
#     gp_n_samples: int = 5000,#50000,
#     gp_train_prop: float = 0.7,
# ):
def preprocessing(
    project_id: str,
    raw_data_bucket: str,
    train_gcs_path: str,
    test_gcs_path: str,
    processed_bucket: str,
    bq_dataset: str,
    pipeline_run_id: str,
    # LSTM outputs
    lstm_train_output: Output[Artifact],
    lstm_test_output: Output[Artifact],
    lstm_scaler_output: Output[Artifact],
    # GP outputs
    gp_train_output: Output[Artifact],
    gp_test_output: Output[Artifact],
    # Config
    lstm_lookback: int = 1,
    gp_n_samples: int = 5000,
    gp_train_prop: float = 0.7,
):
    """
    Preprocessing component for LSTM and GP branches.

    Shared:
    - Reads train and test CSVs from GCS
    - Drops Unnamed: 0
    - Selects Time and App columns

    App is stored as a separate array alongside X and y in GCS.
    Training components (lstm_training, gp_training) only use X and y.
    App is used in batch_inference to annotate BigQuery rows.

    LSTM branch:
    - Builds sliding window dataset (lookback=1)
    - Feature: Time(t-1), Target: Time(t)
    - Fits MinMaxScaler(-1,1) on train only, applies to both
    - Saves X_train, y_train, app_train, X_test, y_test, app_test, scaler to GCS

    GP branch:
    - Subsets to n=50000 rows from train CSV
    - Feature X: Time(t-1), Target y: Time(t)
    - 70/30 internal split
    - Saves X_train, y_train, app_train, X_test, y_test, app_test to GCS
    """
    # import io
    # import pickle
    # import numpy as np
    # import pandas as pd
    # from copy import deepcopy as dc
    # from sklearn.preprocessing import MinMaxScaler
    # from google.cloud import storage

    # gcs_client = storage.Client(project=project_id)
    #########
    import io
    import pickle
    import numpy as np
    import pandas as pd
    from copy import deepcopy as dc
    from sklearn.preprocessing import MinMaxScaler
    from google.cloud import storage, bigquery
    from datetime import datetime, timezone

    gcs_client = storage.Client(project=project_id)
    bq_client = bigquery.Client(project=project_id)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def read_csv_from_gcs(bucket_name: str, blob_path: str) -> pd.DataFrame:
        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        content = blob.download_as_bytes()
        return pd.read_csv(io.BytesIO(content))

    def upload_bytes_to_gcs(bucket_name: str, blob_path: str, data: bytes):
        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        blob.upload_from_string(data)
        print(f"Uploaded to gs://{bucket_name}/{blob_path}")

    def upload_pickle_to_gcs(bucket_name: str, blob_path: str, obj):
        upload_bytes_to_gcs(bucket_name, blob_path, pickle.dumps(obj))

    def upload_numpy_to_gcs(bucket_name: str, blob_path: str, arr: np.ndarray):
        buf = io.BytesIO()
        np.save(buf, arr)
        upload_bytes_to_gcs(bucket_name, blob_path, buf.getvalue())

    # ------------------------------------------------------------------ #
    # Step 1 — Read raw CSVs from GCS
    # ------------------------------------------------------------------ #
    print("Reading train CSV from GCS...")
    train_df = read_csv_from_gcs(raw_data_bucket, train_gcs_path)
    print(f"Train shape: {train_df.shape}")

    print("Reading test CSV from GCS...")
    test_df = read_csv_from_gcs(raw_data_bucket, test_gcs_path)
    print(f"Test shape: {test_df.shape}")

    # ------------------------------------------------------------------ #
    # Step 2 — Shared cleaning: keep Time and App
    # ------------------------------------------------------------------ #
    def clean(df: pd.DataFrame) -> pd.DataFrame:
        if "Unnamed: 0" in df.columns:
            df.drop("Unnamed: 0", axis=1, inplace=True)
        df = df[["Time", "App"]].copy()
        assert df["Time"].isnull().sum() == 0, "Nulls found in Time column"
        print(f"Clean shape: {df.shape}")
        return df

    train_df = clean(train_df)
    test_df = clean(test_df)
    def check_data_drift(bq_client, project_id, bq_dataset, current_series, tolerance=0.2):
        table_id = f"{project_id}.{bq_dataset}.feature_baseline_stats"
        query = f"""
            SELECT mean, std
            FROM `{table_id}`
            WHERE feature_name = 'Time'
            ORDER BY created_at ASC
            LIMIT 1
        """
        result = list(bq_client.query(query).result())

        current_mean = current_series.mean()
        current_std = current_series.std()

        if not result:
            # No baseline yet — this run becomes the baseline
            row = {
                "run_id": pipeline_run_id,
                "feature_name": "Time",
                "mean": float(current_mean),
                "std": float(current_std),
                "min": float(current_series.min()),
                "max": float(current_series.max()),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            bq_client.insert_rows_json(table_id, [row])
            print("No baseline found — this run set as baseline.")
            return "SUCCESS"

        baseline_mean, baseline_std = result[0].mean, result[0].std
        mean_shift = abs(current_mean - baseline_mean) / abs(baseline_mean) if baseline_mean != 0 else 0
        std_shift = abs(current_std - baseline_std) / abs(baseline_std) if baseline_std != 0 else 0

        if mean_shift > tolerance or std_shift > tolerance:
            print(f"DATA_DRIFT_DETECTED: Time distribution shifted — mean_shift={mean_shift:.1%}, std_shift={std_shift:.1%} (baseline mean={baseline_mean:.4f}, current mean={current_mean:.4f})")
            return "DATA_DRIFT"

        return "SUCCESS"

    drift_status = check_data_drift(bq_client, project_id, bq_dataset, train_df["Time"])

    # ------------------------------------------------------------------ #
    # Step 3 — LSTM branch
    # ------------------------------------------------------------------ #
    print("=== LSTM Preprocessing ===")

    def build_lstm_dataset(df: pd.DataFrame, lookback: int):
        data = dc(df)
        for i in range(1, lookback + 1):
            data[f"Time(t-{i})"] = data["Time"].shift(i)
        data.dropna(inplace=True)

        app = data["App"].values                # keep App separate
        arr = data.drop("App", axis=1).to_numpy()
        y = arr[:, 0]                           # Time(t) — target
        X = arr[:, 1:]                          # Time(t-1) — feature
        X = np.flip(X, axis=1)                  # mirror as per PhD code
        return X, y, app

    X_train_lstm, y_train_lstm, app_train_lstm = build_lstm_dataset(train_df, lstm_lookback)
    X_test_lstm, y_test_lstm, app_test_lstm = build_lstm_dataset(test_df, lstm_lookback)

    print(f"LSTM train X: {X_train_lstm.shape}, y: {y_train_lstm.shape}, app: {app_train_lstm.shape}")
    print(f"LSTM test  X: {X_test_lstm.shape}, y: {y_test_lstm.shape}, app: {app_test_lstm.shape}")

    # Fit scaler on train only — stack X and y as per PhD approach
    train_combined = np.hstack([y_train_lstm.reshape(-1, 1), X_train_lstm])
    test_combined = np.hstack([y_test_lstm.reshape(-1, 1), X_test_lstm])

    scaler = MinMaxScaler(feature_range=(-1, 1))
    train_scaled = scaler.fit_transform(train_combined)
    test_scaled = scaler.transform(test_combined)

    X_train_lstm_scaled = train_scaled[:, 1:].reshape(-1, lstm_lookback, 1)
    y_train_lstm_scaled = train_scaled[:, 0].reshape(-1, 1)
    X_test_lstm_scaled = test_scaled[:, 1:].reshape(-1, lstm_lookback, 1)
    y_test_lstm_scaled = test_scaled[:, 0].reshape(-1, 1)

    print(f"LSTM train scaled X: {X_train_lstm_scaled.shape}, y: {y_train_lstm_scaled.shape}")

    # Upload LSTM artefacts — X, y, app stored separately
    upload_pickle_to_gcs(processed_bucket, "lstm/scaler/lstm_scaler.pkl", scaler)
    upload_numpy_to_gcs(processed_bucket, "lstm/train/X_train.npy", X_train_lstm_scaled)
    upload_numpy_to_gcs(processed_bucket, "lstm/train/y_train.npy", y_train_lstm_scaled)
    upload_numpy_to_gcs(processed_bucket, "lstm/train/app_train.npy", app_train_lstm)
    upload_numpy_to_gcs(processed_bucket, "lstm/test/X_test.npy", X_test_lstm_scaled)
    upload_numpy_to_gcs(processed_bucket, "lstm/test/y_test.npy", y_test_lstm_scaled)
    upload_numpy_to_gcs(processed_bucket, "lstm/test/app_test.npy", app_test_lstm)

    lstm_train_output.uri = f"gs://{processed_bucket}/lstm/train"
    lstm_test_output.uri = f"gs://{processed_bucket}/lstm/test"
    lstm_scaler_output.uri = f"gs://{processed_bucket}/lstm/scaler/lstm_scaler.pkl"

    print("LSTM preprocessing complete.")

    # ------------------------------------------------------------------ #
    # Step 4 — GP branch
    # ------------------------------------------------------------------ #
    print("=== GP Preprocessing ===")

    gp_df = train_df.iloc[:gp_n_samples].copy()
    gp_df["Time_prev"] = gp_df["Time"].shift(1)
    gp_df.dropna(inplace=True)

    X_gp = gp_df["Time_prev"].values.reshape(-1, 1)
    y_gp = gp_df["Time"].values.reshape(-1, 1)
    app_gp = gp_df["App"].values

    n_train_gp = round(gp_train_prop * len(X_gp))
    X_train_gp = X_gp[:n_train_gp]
    y_train_gp = y_gp[:n_train_gp]
    app_train_gp = app_gp[:n_train_gp]
    X_test_gp = X_gp[n_train_gp:]
    y_test_gp = y_gp[n_train_gp:]
    app_test_gp = app_gp[n_train_gp:]

    print(f"GP train X: {X_train_gp.shape}, y: {y_train_gp.shape}, app: {app_train_gp.shape}")
    print(f"GP test  X: {X_test_gp.shape}, y: {y_test_gp.shape}, app: {app_test_gp.shape}")

    upload_numpy_to_gcs(processed_bucket, "gp/train/X_train.npy", X_train_gp)
    upload_numpy_to_gcs(processed_bucket, "gp/train/y_train.npy", y_train_gp)
    upload_numpy_to_gcs(processed_bucket, "gp/train/app_train.npy", app_train_gp)
    upload_numpy_to_gcs(processed_bucket, "gp/test/X_test.npy", X_test_gp)
    upload_numpy_to_gcs(processed_bucket, "gp/test/y_test.npy", y_test_gp)
    upload_numpy_to_gcs(processed_bucket, "gp/test/app_test.npy", app_test_gp)

    gp_train_output.uri = f"gs://{processed_bucket}/gp/train"
    gp_test_output.uri = f"gs://{processed_bucket}/gp/test"

    print("GP preprocessing complete.")
    print("=== Preprocessing done ===")