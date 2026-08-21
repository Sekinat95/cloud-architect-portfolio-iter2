"""
Deploys the registered FinBERT model to a Vertex AI Endpoint,
runs test predictions with ElevenLabs TTS audio output,
then deletes the endpoint.
"""
import os
from google.cloud import aiplatform
from elevenlabs.client import ElevenLabs
from elevenlabs import save

PROJECT_ID = "inference-pipeline-w-eleventts"
REGION = "europe-west2"
MODEL_ID = "1643844650315808768"

TEST_SENTENCES = [
    "The company reported record profits this quarter.",
    "The firm filed for bankruptcy following years of losses.",
    "The annual general meeting will be held on Friday.",
    "Revenue increased by 40% year on year driven by strong demand.",
    "The CEO resigned amid mounting pressure from shareholders."
]

def main():
    # Init
    aiplatform.init(project=PROJECT_ID, location=REGION)
    el_client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])

    # Deploy
    model = aiplatform.Model(model_name=MODEL_ID)
    print(f"Model: {model.display_name}")

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

    print("Model deployed. Running predictions with TTS...\n")

    # Predict + TTS
    for i, sentence in enumerate(TEST_SENTENCES):
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
        print(f"Audio saved: {output_path}\n")

    # Teardown
    print("Undeploying and deleting endpoint...")
    endpoint.undeploy_all()
    endpoint.delete()
    print("Endpoint deleted.")

if __name__ == "__main__":
    main()
