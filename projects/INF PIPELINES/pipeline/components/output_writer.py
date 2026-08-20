from kfp.dsl import component, Input, Dataset

@component(
    base_image="python:3.10",
    packages_to_install=["pandas", "google-cloud-bigquery", "pyarrow", "db-dtypes"]
)
def output_writer(
    predictions_dataset: Input[Dataset],
    project_id: str,
    bq_dataset: str,
    bq_table: str
):
    import pandas as pd
    from google.cloud import bigquery
    from datetime import datetime, timezone

    df = pd.read_csv(predictions_dataset.path)
    print(f"Writing {len(df)} predictions to BigQuery")
    print(f"Columns: {df.columns.tolist()}")

    # Rename ground truth column
    df = df.rename(columns={"label": "ground_truth_label"})

    # Explicit type casting
    df["text"] = df["text"].astype(str)
    df["predicted_label"] = df["predicted_label"].astype(str)
    df["confidence"] = df["confidence"].astype(float)
    df["ground_truth_label"] = df["ground_truth_label"].astype(str)
    df["correct"] = df["correct"].astype(bool)
    df["run_id"] = df["run_id"].astype(str)

    # Parse run_timestamp as proper datetime for BigQuery TIMESTAMP field
    df["run_timestamp"] = pd.to_datetime(df["run_timestamp"], utc=True)

    bq_df = df[[
        "text",
        "predicted_label",
        "confidence",
        "ground_truth_label",
        "correct",
        "run_id",
        "run_timestamp"
    ]]

    client = bigquery.Client(project=project_id)
    table_ref = f"{project_id}.{bq_dataset}.{bq_table}"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        schema=[
            bigquery.SchemaField("text", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("predicted_label", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("confidence", "FLOAT64", mode="REQUIRED"),
            bigquery.SchemaField("ground_truth_label", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("correct", "BOOL", mode="REQUIRED"),
            bigquery.SchemaField("run_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("run_timestamp", "TIMESTAMP", mode="REQUIRED"),
        ]
    )

    job = client.load_table_from_dataframe(bq_df, table_ref, job_config=job_config)
    job.result()

    accuracy = df["correct"].mean()
    print(f"Written to {table_ref}")
    print(f"Total rows: {len(bq_df)}")
    print(f"Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
