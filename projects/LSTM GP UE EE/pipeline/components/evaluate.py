from kfp.dsl import component, Input, Output, Metrics


@component(
    base_image="python:3.10-slim",
    packages_to_install=[],
)
def evaluate(
    lstm_metrics_input: Input[Metrics],
    gp_metrics_input: Input[Metrics],
    combined_metrics: Output[Metrics],
):
    """
    Evaluation component.

    Reads train and test RMSE from both LSTM and GP training components
    and logs them together in one KFP Metrics output for side-by-side
    visibility in the Vertex AI Pipelines UI.

    No gating. No comparison logic. Both models always proceed to upload.
    """

    lstm_train_rmse = lstm_metrics_input.metadata.get("train_rmse")
    lstm_test_rmse = lstm_metrics_input.metadata.get("test_rmse")
    gp_train_rmse = gp_metrics_input.metadata.get("train_rmse")
    gp_test_rmse = gp_metrics_input.metadata.get("test_rmse")

    combined_metrics.log_metric("lstm_train_rmse", lstm_train_rmse)
    combined_metrics.log_metric("lstm_test_rmse", lstm_test_rmse)
    combined_metrics.log_metric("gp_train_rmse", gp_train_rmse)
    combined_metrics.log_metric("gp_test_rmse", gp_test_rmse)

    print("=== Model RMSE Comparison ===")
    print(f"LSTM  | Train RMSE: {lstm_train_rmse:.6f} | Test RMSE: {lstm_test_rmse:.6f}")
    print(f"GP    | Train RMSE: {gp_train_rmse:.6f} | Test RMSE: {gp_test_rmse:.6f}")
    print("==============================")