from kfp.dsl import component, Input, Output, Dataset

@component(
    base_image="python:3.10",
    packages_to_install=["pandas", "transformers", "torch"]
)
def batch_inference(
    preprocessed_dataset: Input[Dataset],
    pipeline_run_id: str,
    predictions_dataset: Output[Dataset]
):
    """
    Loads ProsusAI/finbert from Hugging Face.
    Runs batch inference on all texts.
    Outputs predictions with confidence scores.
    Label mapping: 0=negative, 1=neutral, 2=positive
    """
    import pandas as pd
    import torch
    from transformers import BertTokenizer, BertForSequenceClassification
    from datetime import datetime, timezone

    # Label mapping per dataset README
    LABEL_MAP = {0: "positive", 1: "negative", 2: "neutral"}
    BATCH_SIZE = 32

    df = pd.read_csv(preprocessed_dataset.path)
    print(f"Running inference on {len(df)} texts")

    tokenizer = BertTokenizer.from_pretrained("ProsusAI/finbert")
    model = BertForSequenceClassification.from_pretrained("ProsusAI/finbert")
    model.eval()
    print("FinBERT model loaded")

    all_labels = []
    all_confidences = []

    for i in range(0, len(df), BATCH_SIZE):
        batch = df["text"].iloc[i:i+BATCH_SIZE].tolist()
        inputs = tokenizer(
            batch,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding=True
        )
        with torch.no_grad():
            outputs = model(**inputs)

        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        predicted_indices = torch.argmax(probs, dim=-1).tolist()
        confidences = probs.max(dim=-1).values.tolist()

        all_labels.extend([LABEL_MAP[idx] for idx in predicted_indices])
        all_confidences.extend(confidences)

        if (i // BATCH_SIZE) % 5 == 0:
            print(f"Processed {min(i + BATCH_SIZE, len(df))}/{len(df)} texts")

    run_timestamp = datetime.now(timezone.utc).isoformat()

    df["predicted_label"] = all_labels
    df["confidence"] = all_confidences
    df["correct"] = df["predicted_label"] == df["label"]
    df["run_id"] = pipeline_run_id
    df["run_timestamp"] = run_timestamp

    accuracy = df["correct"].mean()
    print(f"Inference complete. Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"Prediction distribution:\n{df['predicted_label'].value_counts().to_string()}")

    df.to_csv(predictions_dataset.path, index=False)
    print(f"Predictions written to {predictions_dataset.path}")
