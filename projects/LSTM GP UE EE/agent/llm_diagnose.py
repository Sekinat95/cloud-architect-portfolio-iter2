# llm.py
import json
from google import genai

PROJECT_ID = "lstm-gp-xr-ue-ee"
REGION = "europe-west4"

client = genai.Client(vertexai=True, project=PROJECT_ID, location=REGION)


def llm_diagnose(logs: list) -> dict:
    prompt = f"""You are diagnosing a failed MLOps pipeline run.
Here are the log entries from the failed job:

{chr(10).join(logs)}

Identify the root cause, quote the specific error line as evidence,
and give a concrete recommendation to fix it.
Respond ONLY with JSON, no other text: {{"root_cause": ..., "evidence": ..., "recommendation": ..., "confidence": ...}}
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    content = response.text.strip()
    content = content.removeprefix("```json").removesuffix("```").strip()
    return json.loads(content)