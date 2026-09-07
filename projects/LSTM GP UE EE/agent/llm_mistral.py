# llm.py
import os
import json
import time
from mistralai.client import Mistral

client = Mistral(api_key=os.environ["MISTRALAI_API_KEY"])


def llm_diagnose(logs: list) -> dict:
    time.sleep(3)  # stay safely under free-tier 1 req/sec limit

    prompt = f"""You are diagnosing a failed MLOps pipeline run.
Here are the log entries from the failed job:

{chr(10).join(logs)}

Identify the root cause, quote the specific error line as evidence,
and give a concrete recommendation to fix it.
Respond ONLY with JSON, no other text: {{"root_cause": ..., "evidence": ..., "recommendation": ..., "confidence": ...}}
"""
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}],
    )
    content = response.choices[0].message.content.strip()
    content = content.removeprefix("```json").removesuffix("```").strip()
    return json.loads(content)