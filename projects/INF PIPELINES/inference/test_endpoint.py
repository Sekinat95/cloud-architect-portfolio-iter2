"""
Deploys the registered FinBERT model to a Vertex AI Endpoint,
runs test predictions, then deletes the endpoint.
"""
import os
from google.cloud import aiplatform, storage
from elevenlabs.client import ElevenLabs
from elevenlabs import save

PROJECT_ID = "inf-pipelines"
REGION = "europe-west4"
AUDIO_BUCKET = f"{PROJECT_ID}-audio-output"

TEST_TEXTS = [
    "The company reported record profits this quarter.",
    "The firm filed for bankruptcy following years of losses.",
    "The annual general meeting will be held on Friday.",
    "Revenue increased by 40% year on year driven by strong demand.",
    "The CEO resigned amid mounting pressure from shareholders."
]

def upload_audio_to_gcs(local_path: str, run_id: str, storage_client: storage.Client):
    bucket = storage_client.bucket(AUDIO_BUCKET)
    blob = bucket.blob(f"{run_id}/{local_path}")
    blob.upload_from_filename(local_path)
    print(f"Uploaded {local_path} to gs://{AUDIO_BUCKET}/{run_id}/{local_path}")

def main():
    #init
    aiplatform.init(project=PROJECT_ID, location=REGION)
    el_client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
    storage_client = storage.Client(project=PROJECT_ID)
    

    #deploy
    models = aiplatform.Model.list(order_by="create_time desc")
    model = models[0]  # most recently registered
    print(f"Model: {model.display_name}")
    run_id = model.display_name.replace("finbert-inference-", "")

    print("Creating endpoint...")
    endpoint = aiplatform.Endpoint.create(
        display_name="finbert-inference-endpoint",
        project=PROJECT_ID,
        location=REGION
    )

    print("Deploying model — this takes ~10 minutes...")
    model.deploy(
        endpoint=endpoint,
        deployed_model_display_name="finbert-deployed",
        machine_type="n1-standard-4",
        min_replica_count=1,
        max_replica_count=1,
        sync=True
    )

    print("Model deployed. Running test predictions...")
    #predict + tts
    for i, sentence in enumerate(TEST_TEXTS):
            response = endpoint.predict(instances=[{"text": sentence}])
            prediction = response.predictions[0]
            label = prediction["label"]
            confidence = round(prediction["score"] * 100, 1)

            print(f"Input:  {sentence}")
            print(f"Output: {label} ({confidence}%)")

            tts_text = (
                f"Sentence: {sentence}. "
                f"Sentiment: {label}. "
                f"Confidence: {confidence} percent."
            )

            audio = el_client.generate(
                text=tts_text,
                voice="Rachel",
                model="eleven_monolingual_v1"
            )

            output_path = f"output_{i}_{label}.mp3"
            save(audio, output_path)
            print(f"Audio saved: {output_path}")

            upload_audio_to_gcs(output_path, run_id, storage_client)
            print()

    #teardown
    print("\nUndeploying and deleting endpoint...")
    endpoint.undeploy_all()
    endpoint.delete()
    print("Endpoint deleted.")

if __name__ == "__main__":
    main()