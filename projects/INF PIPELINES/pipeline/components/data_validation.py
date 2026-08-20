from kfp.dsl import component, Output, Dataset

@component(
    base_image="python:3.10",
    packages_to_install=["pandas", "google-cloud-storage"]
)
def data_validation(
    project_id: str,
    raw_data_bucket: str,
    blob_name: str,
    validated_dataset: Output[Dataset]
):
    """
    Reads twitter sentiments CSV from GCS.
    Validates schema, row count, label set, and null values.
    Fails fast if any check fails.
    """
    import pandas as pd
    from google.cloud import storage
    import io

    # Download from GCS
    client = storage.Client(project=project_id)
    bucket = client.bucket(raw_data_bucket)
    blob = bucket.blob(blob_name)
    content = blob.download_as_bytes()
    df = pd.read_csv(io.BytesIO(content))

    print(f"Downloaded {len(df)} rows from gs://{raw_data_bucket}/{blob_name}")
    print(f"Columns: {df.columns.tolist()}")

    # Check 1: required columns
    required_cols = {"text", "label"}
    assert required_cols.issubset(df.columns), \
        f"Missing columns. Expected {required_cols}, got {set(df.columns)}"

    # Check 2: row count
    assert 100 < len(df) < 3000, \
        f"Row count {len(df)} out of expected range (100, 3000)"

    # Check 3: valid label values
    valid_labels = {"positive", "negative", "neutral"}
    actual_labels = set(df["label"].unique())
    assert actual_labels.issubset(valid_labels), \
        f"Unexpected labels: {actual_labels - valid_labels}"

    # Check 4: no nulls in text column
    null_count = df["text"].isnull().sum()
    assert null_count == 0, \
        f"Found {null_count} null values in text column"

    print("All validation checks passed.")
    print(f"Label distribution:\n{df['label'].value_counts().to_string()}")

    # Write validated dataset as artifact
    df.to_csv(validated_dataset.path, index=False)
    print(f"Validated dataset written to {validated_dataset.path}")
