from kfp.dsl import component, Input, Output, Artifact, Metrics


@component(
    base_image="python:3.10-slim",
    packages_to_install=[
        "numpy==1.26.4",
        "scikit-learn==1.3.2",
        "google-cloud-storage==2.14.0",
    ],
)
def gp_training(
    project_id: str,
    model_artefacts_bucket: str,
    # Inputs from preprocessing
    gp_train_input: Input[Artifact],
    gp_test_input: Input[Artifact],
    # Outputs
    gp_model_output: Output[Artifact],
    gp_metrics: Output[Metrics],
    # Hyperparameters
    n_restarts_optimizer: int = 10,
    normalize_y: bool = True,
):
    """
    GP Regressor training component.

    Replicates PhD GP exactly:
    - Kernel: WhiteKernel + ConstantKernel * Matern(nu=1.5)
    - n_restarts_optimizer=10
    - normalize_y=True
    - alpha=0.0
    - Feature X: Time(t-1), Target y: Time(t)
    - n=50000 rows, 70/30 split (done in preprocessing)

    Saves:
    - model.pkl → GCS model-artefacts/gp/model/
    - Metrics: train R2, test R2, train MAE, test MAE, test RMSE
    """
    import io
    import pickle
    import numpy as np
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import (
        WhiteKernel,
        ConstantKernel,
        Matern,
    )
    from sklearn.metrics import mean_absolute_error
    from google.cloud import storage

    gcs_client = storage.Client(project=project_id)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def download_bytes(bucket_name: str, blob_path: str) -> bytes:
        bucket = gcs_client.bucket(bucket_name)
        return bucket.blob(blob_path).download_as_bytes()

    def load_npy(bucket_name: str, blob_path: str) -> np.ndarray:
        data = download_bytes(bucket_name, blob_path)
        return np.load(io.BytesIO(data), allow_pickle=False)

    def upload_bytes(bucket_name: str, blob_path: str, data: bytes):
        bucket = gcs_client.bucket(bucket_name)
        bucket.blob(blob_path).upload_from_string(data)
        print(f"Uploaded to gs://{bucket_name}/{blob_path}")

    # ------------------------------------------------------------------ #
    # Step 1 — Load preprocessed arrays from GCS
    # ------------------------------------------------------------------ #
    train_uri = gp_train_input.uri.replace("gs://", "")
    test_uri = gp_test_input.uri.replace("gs://", "")

    train_bucket = train_uri.split("/")[0]
    train_prefix = "/".join(train_uri.split("/")[1:])
    test_prefix = "/".join(test_uri.split("/")[1:])

    print("Loading GP training arrays...")
    X_train = load_npy(train_bucket, f"{train_prefix}/X_train.npy")
    y_train = load_npy(train_bucket, f"{train_prefix}/y_train.npy")
    X_test = load_npy(train_bucket, f"{test_prefix}/X_test.npy")
    y_test = load_npy(train_bucket, f"{test_prefix}/y_test.npy")

    print(f"X_train: {X_train.shape}, y_train: {y_train.shape}")
    print(f"X_test:  {X_test.shape},  y_test:  {y_test.shape}")

    # ------------------------------------------------------------------ #
    # Step 2 — Define kernel (exact PhD configuration)
    # ------------------------------------------------------------------ #
    k0 = WhiteKernel(
        noise_level=0.3 ** 2,
        noise_level_bounds=(0.1 ** 2, 0.5 ** 2),
    )
    k1 = ConstantKernel(constant_value=2) * Matern(length_scale=1.0, nu=1.5)
    kernel = k0 + k1

    gp = GaussianProcessRegressor(
        kernel=kernel,
        n_restarts_optimizer=n_restarts_optimizer,
        normalize_y=normalize_y,
        alpha=0.0,
    )

    # ------------------------------------------------------------------ #
    # Step 3 — Fit
    # ------------------------------------------------------------------ #
    print("Fitting GP regressor...")
    gp.fit(X_train, y_train)
    print(f"Optimised kernel: {gp.kernel_}")

    # ------------------------------------------------------------------ #
    # Step 4 — Evaluate
    # ------------------------------------------------------------------ #
    print("Evaluating...")

    train_r2 = float(gp.score(X_train, y_train))
    test_r2 = float(gp.score(X_test, y_test))

    y_train_pred = gp.predict(X_train)
    y_test_pred = gp.predict(X_test)

    train_mae = float(mean_absolute_error(y_train, y_train_pred))
    test_mae = float(mean_absolute_error(y_test, y_test_pred))

    train_rmse = float(np.sqrt(np.mean((y_train.flatten() - y_train_pred.flatten()) ** 2)))
    test_rmse = float(np.sqrt(np.mean((y_test.flatten() - y_test_pred.flatten()) ** 2)))

    print(f"Train R2:   {train_r2:.4f}")
    print(f"Test  R2:   {test_r2:.4f}")
    print(f"Train MAE:  {train_mae:.6f}")
    print(f"Test  MAE:  {test_mae:.6f}")
    print(f"Train RMSE: {train_rmse:.6f}")
    print(f"Test  RMSE: {test_rmse:.6f}")

    # Log metrics to KFP
    gp_metrics.log_metric("train_r2", train_r2)
    gp_metrics.log_metric("test_r2", test_r2)
    gp_metrics.log_metric("train_mae", train_mae)
    gp_metrics.log_metric("test_mae", test_mae)
    gp_metrics.log_metric("train_rmse", train_rmse)
    gp_metrics.log_metric("test_rmse", test_rmse)

    # ------------------------------------------------------------------ #
    # Step 5 — Save model to GCS
    # ------------------------------------------------------------------ #
    upload_bytes(
        model_artefacts_bucket,
        "gp/model/model.pkl",
        pickle.dumps(gp),
    )

    gp_model_output.uri = f"gs://{model_artefacts_bucket}/gp/model/model.pkl"
    print("GP model saved to GCS.")