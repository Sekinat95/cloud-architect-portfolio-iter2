from kfp import dsl, compiler
from components.data_validation import data_validation
from components.preprocessing import preprocessing
from components.batch_inference import batch_inference
from components.output_writer import output_writer
from components.model_upload import model_upload

PROJECT_ID = "inf-pipelines"
REGION = "europe-west4"
PIPELINE_ROOT = f"gs://{PROJECT_ID}-pipeline-root"
RAW_DATA_BUCKET = f"{PROJECT_ID}-raw-data"
BLOB_NAME = "twitter-financial-sentiment/sent_valid.csv"
BQ_DATASET = "mlops_predictions"
BQ_TABLE = "finbert_predictions"
MODEL_BUCKET = f"{PROJECT_ID}-model-artefacts"

@dsl.pipeline(
    name="finbert-inference-pipeline",
    description="FinBERT financial sentiment inference pipeline on twitter financial sentiments data",
    pipeline_root=PIPELINE_ROOT
)
def finbert_pipeline(
    project_id: str = PROJECT_ID,
    region: str = REGION,
    raw_data_bucket: str = RAW_DATA_BUCKET,
    blob_name: str = BLOB_NAME,
    bq_dataset: str = BQ_DATASET,
    bq_table: str = BQ_TABLE,
    pipeline_run_id: str = "manual-run-001",
    model_bucket: str =MODEL_BUCKET
):
    validation_step = data_validation(
        project_id=project_id,
        raw_data_bucket=raw_data_bucket,
        blob_name=blob_name
    )

    preprocess_step = preprocessing(
        validated_dataset=validation_step.outputs["validated_dataset"]
    )

    inference_step = batch_inference(
        preprocessed_dataset=preprocess_step.outputs["preprocessed_dataset"],
        pipeline_run_id=pipeline_run_id
    )

    writer_step = output_writer(
        predictions_dataset=inference_step.outputs["predictions_dataset"],
        project_id=project_id,
        bq_dataset=bq_dataset,
        bq_table=bq_table
    )

    upload_step = model_upload(
        project_id=project_id,
        region=region,
        model_bucket=model_bucket,
        pipeline_run_id=pipeline_run_id
    )
    upload_step.after(inference_step)


if __name__ == "__main__":
    compiler.Compiler().compile(
        pipeline_func=finbert_pipeline,
        package_path="pipeline.yaml"
    )
    print("Pipeline compiled to pipeline.yaml")
