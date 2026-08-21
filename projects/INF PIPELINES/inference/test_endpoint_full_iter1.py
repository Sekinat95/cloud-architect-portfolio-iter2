"""
Deploys the registered FinBERT model to a Vertex AI Endpoint,
runs test predictions with ElevenLabs TTS audio output,
then deletes the endpoint.
"""
import os
from google.cloud import aiplatform
from elevenlabs.client import ElevenLabs

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
    aiplatform.init(project=PROJECT_ID, location=REGION)
    el_client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])

    # Get existing deployed endpoint — reuse from previous run
    endpoint = aiplatform.Endpoint(
        endpoint_name="projects/680489318177/locations/europe-west2/endpoints/4442187504912695296"
    )
    print("Reusing existing endpoint")

    print("Running predictions with TTS...\n")

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

        # New ElevenLabs API
        audio = el_client.text_to_speech.convert(
            text=tts_text,
            voice_id="pNInz6obpgDQGcFmaJgB",  # Rachel voice ID
            model_id="eleven_turbo_v2_5",
            output_format="mp3_44100_128"
        )

        output_path = f"output_{i}_{label}.mp3"
        with open(output_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        print(f"Audio saved: {output_path}\n")

    # Teardown
    print("Undeploying and deleting endpoint...")
    endpoint.undeploy_all()
    endpoint.delete()
    print("Endpoint deleted.")

if __name__ == "__main__":
    main()
