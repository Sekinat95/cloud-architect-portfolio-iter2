"""
Deploys the registered FinBERT model to a Vertex AI Endpoint,
runs test predictions, then deletes the endpoint.
"""
from google.cloud import aiplatform

PROJECT_ID = "inf-pipelines"
REGION = "europe-west4"
MODEL_ID = "1469890915685367808"

TEST_TEXTS = [
    "The company reported record profits this quarter.",
    "The firm filed for bankruptcy following years of losses.",
    "The annual general meeting will be held on Friday.",
    "Revenue increased by 40% year on year driven by strong demand.",
    "The CEO resigned amid mounting pressure from shareholders."
]

def main():
    aiplatform.init(project=PROJECT_ID, location=REGION)

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

    print("Model deployed. Running test predictions...")
    for text in TEST_TEXTS:
        response = endpoint.predict(instances=[{"text": text}])
        prediction = response.predictions[0]
        print(f"\nInput:  {text}")
        print(f"Output: {prediction}")

    print("\nUndeploying and deleting endpoint...")
    endpoint.undeploy_all()
    endpoint.delete()
    print("Endpoint deleted.")

if __name__ == "__main__":
    main()
