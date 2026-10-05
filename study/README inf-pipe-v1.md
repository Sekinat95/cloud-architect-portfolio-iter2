# INFERENCE PIPELINE FOR FINANCIAL SENTIMENTS ANALYSIS WITH TTS INTEGRATIONS

## VERSIONS
This project is divided into versions: 
 - v1-pipeline : end to end inference pipeline of financial sentiments analysis using twitter financial dataset with manual pipeline launch and batch inference.
 - v2-req-endpoint: end to end inference pipeline of financial sentiments analysis using twitter financial dataset with manual pipeline launch and batch inference and live request vertex ai endpoint for single inference requests
 - v3-ci-cd: end to end inference pipeline of financial sentiments analysis using twitter financial dataset with CI/CD and  batch inference and live request vertex ai endpoint for single inference requests
 - v4-tts-api: end to end inference pipeline of financial sentiments analysis using twitter financial dataset with CI/CD and  batch inference and live request vertex ai endpoint for single inference requests and elevenlabs text to speech api

```mermaid
graph TD
  GCS["Raw Financial Data"] --> VAPL
    subgraph VAPL["the pipeline"]
      DV["Data validation component"] --> PPR
      PPR["Preprocessing component"] --> BINF["FinBERT predictions"] --> OUT
      OUT["Bigquery <br/> Batch results"] --> MDLU
      MDLU["Model Upload <br/> VA Model Registry"] --> DP
      DP["VA endpoint <br/> online serving"]
    end
    subgraph TEST["send live requests <br/> test_endpoint.py"]
    end
    subgraph TTS["ElevenLabs <br/> TTS API"]
    end
    subgraph TRDWN["Tear down"]
    end
   VAPL --> TEST --> TTS --> TRDWN
```