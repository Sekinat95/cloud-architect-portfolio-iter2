"""
One-off script: downloads twitter financial news sentiment
from the zip file and uploads to GCS as CSV.
"""

import pandas as pd
from google.cloud import storage
import io


PROJECT_ID = "inf-pipelines"
BUCKET_NAME = f"{PROJECT_ID}-raw-data"
DESTINATION_BLOB = "twitter-financial-sentiment/sent_valid.csv"


URL = "https://huggingface.co/datasets/zeroshot/twitter-financial-news-sentiment/resolve/main/sent_valid.csv"


def download_and_parse(csv: str) -> pd.DataFrame:
    LABEL_MAP = {0: "negative", 1: "positive", 2: "neutral"} # {0: "bearish", 1: "bullish", 2: "neutral"}
    raw_df = pd.read_csv(csv)
    rows = [
        {"text": row["text"], "label": LABEL_MAP[row["label"]]}
        for _, row in raw_df.iterrows()
    ]
    df = pd.DataFrame(rows)
    return df

def upload_to_gcs(df: pd.DataFrame, bucket_name: str, blob_name: str):
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    blob.upload_from_file(buffer, content_type="text/csv")
    print(f"Uploaded {len(df)} rows to gs://{bucket_name}/{blob_name}")

def main():
    df = download_and_parse(URL)
    print(f"Shape: {df.shape}")
    print(f"Label distribution:\n{df['label'].value_counts()}")
    print(f"Sample:\n{df.head(3)}")
    upload_to_gcs(df, BUCKET_NAME, DESTINATION_BLOB)

if __name__ == "__main__":
    main()
