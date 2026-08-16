from kfp.dsl import component, Input, Output, Artifact, Metrics


@component(
    base_image="python:3.10-slim",
    packages_to_install=[
        "numpy==1.26.4",
        "torch==2.1.2",
        "scikit-learn==1.3.2",
        "google-cloud-storage==2.14.0",
        "torch-model-archiver==0.9.0",
    ],
)
def lstm_training(
    project_id: str,
    model_artefacts_bucket: str,
    # Inputs from preprocessing
    lstm_train_input: Input[Artifact],
    lstm_test_input: Input[Artifact],
    lstm_scaler_input: Input[Artifact],
    # Output
    lstm_model_output: Output[Artifact],
    lstm_metrics: Output[Metrics],
    # Hyperparameters
    input_size: int = 1,
    hidden_size: int = 200,
    num_stacked_layers: int = 1,
    batch_size: int = 128,
    num_epochs: int = 18,#600,
    learning_rate: float = 0.004,
    lookback: int = 1,
):
    """
    LSTM training component.

    Replicates PhD LSTM exactly:
    - Architecture: LSTM(1, 200, 1) + Linear(200, 1)
    - Loss: MSELoss
    - Optimizer: Adam lr=0.004
    - Epochs: 600
    - Input: scaled Time(t-1), Target: scaled Time(t)

    Saves:
    - model.mar (TorchServe archive bundling model.pt + lstm_scaler.pkl + handler.py)
      → GCS model-artefacts/lstm/model/
    - train RMSE and val RMSE logged to KFP Metrics
    """
    import io
    import os
    import pickle
    import subprocess
    import tempfile
    import numpy as np
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
    from google.cloud import storage

    gcs_client = storage.Client(project=project_id)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def download_bytes(bucket_name: str, blob_path: str) -> bytes:
        return gcs_client.bucket(bucket_name).blob(blob_path).download_as_bytes()

    def load_npy(bucket_name: str, blob_path: str) -> np.ndarray:
        return np.load(io.BytesIO(download_bytes(bucket_name, blob_path)), allow_pickle=False)

    def upload_bytes(bucket_name: str, blob_path: str, data: bytes):
        gcs_client.bucket(bucket_name).blob(blob_path).upload_from_string(data)
        print(f"Uploaded to gs://{bucket_name}/{blob_path}")

    def upload_file(bucket_name: str, blob_path: str, local_path: str):
        gcs_client.bucket(bucket_name).blob(blob_path).upload_from_filename(local_path)
        print(f"Uploaded to gs://{bucket_name}/{blob_path}")

    # ------------------------------------------------------------------ #
    # Step 1 — Load preprocessed arrays from GCS
    # ------------------------------------------------------------------ #
    train_uri = lstm_train_input.uri.replace("gs://", "")
    test_uri = lstm_test_input.uri.replace("gs://", "")

    train_bucket = train_uri.split("/")[0]
    train_prefix = "/".join(train_uri.split("/")[1:])
    test_prefix = "/".join(test_uri.split("/")[1:])

    print("Loading LSTM training arrays...")
    X_train = load_npy(train_bucket, f"{train_prefix}/X_train.npy")
    y_train = load_npy(train_bucket, f"{train_prefix}/y_train.npy")
    X_test = load_npy(train_bucket, f"{test_prefix}/X_test.npy")
    y_test = load_npy(train_bucket, f"{test_prefix}/y_test.npy")

    print(f"X_train: {X_train.shape}, y_train: {y_train.shape}")
    print(f"X_test:  {X_test.shape},  y_test:  {y_test.shape}")

    # ------------------------------------------------------------------ #
    # Step 2 — Tensors and DataLoaders
    # ------------------------------------------------------------------ #
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    X_train_t = torch.tensor(X_train).float()
    y_train_t = torch.tensor(y_train).float()
    X_test_t = torch.tensor(X_test).float()
    y_test_t = torch.tensor(y_test).float()

    class TimeSeriesDataset(Dataset):
        def __init__(self, X, y):
            self.X = X
            self.y = y

        def __len__(self):
            return len(self.X)

        def __getitem__(self, idx):
            return self.X[idx], self.y[idx]

    train_loader = DataLoader(
        TimeSeriesDataset(X_train_t, y_train_t),
        batch_size=batch_size,
        shuffle=True,
    )
    test_loader = DataLoader(
        TimeSeriesDataset(X_test_t, y_test_t),
        batch_size=batch_size,
        shuffle=False,
    )

    # ------------------------------------------------------------------ #
    # Step 3 — Model definition (exact PhD architecture)
    # ------------------------------------------------------------------ #
    class LSTMModel(nn.Module):
        def __init__(self, input_size, hidden_size, num_stacked_layers):
            super().__init__()
            self.hidden_size = hidden_size
            self.num_stacked_layers = num_stacked_layers
            self.lstm = nn.LSTM(
                input_size, hidden_size, num_stacked_layers, batch_first=True
            )
            self.fc = nn.Linear(hidden_size, 1)

        def forward(self, x):
            batch_size = x.size(0)
            h0 = torch.zeros(self.num_stacked_layers, batch_size, self.hidden_size).to(device)
            c0 = torch.zeros(self.num_stacked_layers, batch_size, self.hidden_size).to(device)
            out, _ = self.lstm(x, (h0, c0))
            out = self.fc(out[:, -1, :])
            return out

    model = LSTMModel(input_size, hidden_size, num_stacked_layers).to(device)
    loss_fn = nn.MSELoss()
    optimiser = torch.optim.Adam(model.parameters(), lr=learning_rate)

    # ------------------------------------------------------------------ #
    # Step 4 — Training loop
    # ------------------------------------------------------------------ #
    print("Starting training...")
    best_val_loss = float("inf")
    best_model_state = None

    for epoch in range(num_epochs):
        model.train()
        train_loss = 0.0
        for x_batch, y_batch in train_loader:
            x_batch, y_batch = x_batch.to(device), y_batch.to(device)
            output = model(x_batch)
            loss = loss_fn(output, y_batch)
            optimiser.zero_grad()
            loss.backward()
            optimiser.step()
            train_loss += loss.item()

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for x_batch, y_batch in test_loader:
                x_batch, y_batch = x_batch.to(device), y_batch.to(device)
                output = model(x_batch)
                val_loss += loss_fn(output, y_batch).item()

        avg_train_loss = train_loss / len(train_loader)
        avg_val_loss = val_loss / len(test_loader)

        if (epoch + 1) % 50 == 0:
            print(f"Epoch {epoch+1}/{num_epochs} | Train Loss: {avg_train_loss:.6f} | Val Loss: {avg_val_loss:.6f}")

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_model_state = {k: v.clone() for k, v in model.state_dict().items()}

    print("Training complete.")

    # ------------------------------------------------------------------ #
    # Step 5 — Compute RMSE on unscaled predictions
    # ------------------------------------------------------------------ #
    scaler_bucket = lstm_scaler_input.uri.replace("gs://", "").split("/")[0]
    scaler_blob = "/".join(lstm_scaler_input.uri.replace("gs://", "").split("/")[1:])
    scaler = pickle.loads(download_bytes(scaler_bucket, scaler_blob))

    model.load_state_dict(best_model_state)
    model.eval()
    model.to(device)

    with torch.no_grad():
        train_preds_scaled = model(X_train_t.to(device)).cpu().numpy().flatten()
        test_preds_scaled = model(X_test_t.to(device)).cpu().numpy().flatten()

    def inverse_transform_preds(preds_scaled, actuals_scaled, scaler, lookback):
        dummies = np.zeros((len(preds_scaled), lookback + 1))
        dummies[:, 0] = preds_scaled
        preds_unscaled = scaler.inverse_transform(dummies)[:, 0]
        dummies[:, 0] = actuals_scaled.flatten()
        actuals_unscaled = scaler.inverse_transform(dummies)[:, 0]
        return preds_unscaled, actuals_unscaled

    train_preds, train_actuals = inverse_transform_preds(train_preds_scaled, y_train, scaler, lookback)
    test_preds, test_actuals = inverse_transform_preds(test_preds_scaled, y_test, scaler, lookback)

    train_rmse = float(np.sqrt(np.mean((train_actuals - train_preds) ** 2)))
    test_rmse = float(np.sqrt(np.mean((test_actuals - test_preds) ** 2)))

    print(f"Train RMSE: {train_rmse:.6f}")
    print(f"Test  RMSE: {test_rmse:.6f}")

    lstm_metrics.log_metric("train_rmse", train_rmse)
    lstm_metrics.log_metric("test_rmse", test_rmse)
    lstm_metrics.log_metric("best_val_loss", best_val_loss)
    lstm_metrics.log_metric("epochs", num_epochs)

    # ------------------------------------------------------------------ #
    # Step 6 — Export as TorchScript + package as model.mar
    # ------------------------------------------------------------------ #
    model.load_state_dict(best_model_state)
    model.eval()
    model.to("cpu")

    with tempfile.TemporaryDirectory() as tmpdir:

        # 6a — Save TorchScript model
        model_pt_path = os.path.join(tmpdir, "model.pt")
        example_input = torch.zeros(1, lookback, 1)
        scripted_model = torch.jit.trace(model, example_input)
        torch.jit.save(scripted_model, model_pt_path)
        print("TorchScript model saved.")

        # 6b — Save scaler as extra file
        scaler_path = os.path.join(tmpdir, "lstm_scaler.pkl")
        with open(scaler_path, "wb") as f:
            pickle.dump(scaler, f)
        print("Scaler saved.")

        # 6c — Write TorchServe handler
        handler_path = os.path.join(tmpdir, "handler.py")
        handler_code = '''
import io
import os
import pickle
import numpy as np
import torch
from ts.torch_handler.base_handler import BaseHandler

class LSTMHandler(BaseHandler):
    """
    TorchServe handler for LSTM arrival time prediction.
    Expects input: {"instances": [[time_t_minus_1_value]]}
    Returns: {"predictions": [predicted_time_t]}
    """

    def initialize(self, context):
        super().initialize(context)
        # Load scaler from model archive extra files
        model_dir = context.system_properties.get("model_dir")
        scaler_path = os.path.join(model_dir, "lstm_scaler.pkl")
        with open(scaler_path, "rb") as f:
            self.scaler = pickle.load(f)
        self.lookback = 1
        self.initialized = True

    def preprocess(self, data):
        """Scale input using fitted scaler."""
        instances = data[0].get("body", {}).get("instances", [])
        inputs = np.array(instances, dtype=np.float32)  # shape (n, 1)
        # Reconstruct combined array for scaler: [y_placeholder, X]
        combined = np.hstack([np.zeros((len(inputs), 1)), inputs])
        scaled = self.scaler.transform(combined)
        X_scaled = scaled[:, 1:].reshape(-1, self.lookback, 1)
        return torch.tensor(X_scaled).float()

    def inference(self, inputs):
        with torch.no_grad():
            return self.model(inputs)

    def postprocess(self, outputs):
        """Inverse transform predictions back to original scale."""
        preds_scaled = outputs.numpy().flatten()
        dummies = np.zeros((len(preds_scaled), self.lookback + 1))
        dummies[:, 0] = preds_scaled
        preds_unscaled = self.scaler.inverse_transform(dummies)[:, 0]
        return [{"predictions": preds_unscaled.tolist()}]
'''
        with open(handler_path, "w") as f:
            f.write(handler_code)
        print("Handler written.")

        # 6d — Run torch-model-archiver
        mar_output_dir = os.path.join(tmpdir, "mar_output")
        os.makedirs(mar_output_dir, exist_ok=True)

        cmd = [
            "torch-model-archiver",
            "--model-name", "lstm_arrival_time",
            "--version", "1.0",
            "--serialized-file", model_pt_path,
            "--handler", handler_path,
            "--extra-files", scaler_path,
            "--export-path", mar_output_dir,
            "--f",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"torch-model-archiver failed:\n{result.stderr}")
        print("model.mar created.")

        # 6e — Upload model.mar to GCS (for online serving via Vertex AI endpoint)
        mar_path = os.path.join(mar_output_dir, "lstm_arrival_time.mar")
        # Rename to model.mar for Vertex AI PyTorch container
        model_mar_path = os.path.join(mar_output_dir, "model.mar")
        os.rename(mar_path, model_mar_path)
        upload_file(model_artefacts_bucket, "lstm/model/model.mar", model_mar_path)

        # 6f — Upload model.pt and lstm_scaler.pkl separately for batch inference
        # batch_inference.py loads these directly from GCS — it does not unpack the .mar
        upload_file(model_artefacts_bucket, "lstm/model/model.pt", model_pt_path)
        upload_file(model_artefacts_bucket, "lstm/model/lstm_scaler.pkl", scaler_path)

    lstm_model_output.uri = f"gs://{model_artefacts_bucket}/lstm/model/"
    print("LSTM model.mar, model.pt and lstm_scaler.pkl uploaded to GCS.")