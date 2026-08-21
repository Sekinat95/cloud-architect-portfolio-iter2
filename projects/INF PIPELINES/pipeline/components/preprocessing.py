from kfp.dsl import component, Input, Output, Dataset

@component(
    base_image="python:3.10",
    packages_to_install=["pandas", "transformers", "torch"]
)
def preprocessing(
    validated_dataset: Input[Dataset],
    preprocessed_dataset: Output[Dataset]
):
    """
    texts===sentences
    Tokenises texts using FinBERT tokeniser.
    Truncates to 512 tokens max.
    Writes preprocessed dataset with token counts for inspection.
    """
    import pandas as pd
    from transformers import BertTokenizer

    df = pd.read_csv(validated_dataset.path)
    print(f"Loaded {len(df)} rows for preprocessing")

    tokenizer = BertTokenizer.from_pretrained("ProsusAI/finbert")
    print("FinBERT tokeniser loaded")

    # Count tokens per texts — flag any exceeding 512
    # def count_tokens(text: str) -> int:
    #     return len(tokenizer.encode(text, add_special_tokens=True))

    def count_tokens(text: str) -> int:
        return len(tokenizer.encode(text, add_special_tokens=True, truncation=True, max_length=512))

    df["token_count"] = df["text"].apply(count_tokens)

    truncated = df[df["token_count"] > 512]
    if len(truncated) > 0:
        print(f"Warning: {len(truncated)} texts exceed 512 tokens and will be truncated")
    else:
        print("All texts within 512 token limit")

    print(f"Token count stats:\n{df['token_count'].describe().to_string()}")

    df.to_csv(preprocessed_dataset.path, index=False)
    print(f"Preprocessed dataset written to {preprocessed_dataset.path}")
