# INFERENCE PIPELINE FOR FINANCIAL SENTIMENTS ANALYSIS WITH TTS INTEGRATIONS
## Architecture Diagram
[Architectural Diagram](../INF%20PIPELINES/diagram/inference%20pipeline.png)
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

## Brief Description
### Introduction: objectives, definitions, scope
In this project the basic workflow of an inference pipeline for financial sentiments analysis is implemented. <br>
The objective is to execute both batch and online inference using GCP platform tooling and at the end integrate external APIs.<br>
This project is entirely implemented with backend functionalities as such, online inference calls are made from file (``test_endpoint.py``)<br>
### Components
There are 6 components of this pipeline end to end:<br>
1. Data validation: use of twitter financial sentiments data<br>
2. Data pre-processing: mapping sentiments accurrately in the data according to the model's expecttations<br>
3. Model Upload: FinBERT is used and is loaded from Hugginface
4. Bigquery Batch inference: Batch inference is done in GCP bigquery and stored<br>
5. Vertex AI (VA) endpoint online serving (call from file): a script with input query is sent to a provisioned VA endpoint with the model<br>
6. ElevenLabs Text to Speech (TTS) integration: The model inference outputs from the the online inference is parsed through a TTS api first in order to generate audio of the response.
### Results and Conclusions
By the end, we have the models predictions for the entire test set of the data as well as the audio files of an online call (when its a request is made)

## Set-up Instructions

### File structure
![File Structure](../INF%20PIPELINES/diagram/file_structure.png)
The project file structure consists of the components, Infrastructure as Code (IaC) and online inference folders. 
### Infrastructure as code (IaC)
The infrastructure provisioning is done mainly with ``Terraform`` on Google Cloud Platform s(GCP)
### Google Cloud Platform (GCP)
1. Storage bucket<br>
2. Bigquery<br>
3. Vertex AI (now Gemini Agent platform) (model registry, pipelines, endpoint)<br>
4. Cloud build<br>
### Operations
Continuos integration is carried out through a cloud build trigger. Due to cost management deployment to VA endpoints is detached from the pipeline and is instead executed through a script ``test_endpoint.py``

## Replication Instructions: Steps
### GCP console and cloudshell set up
Create all terraform GCP files. create all environments variables. Utilise ``Terraform , gcloud and git``
### Terraform
``terraform init``<br>
``terraform plan``<br>
``terraform apply`` <br>
### Running
create  cloud build trigger on GCP console by attaching ``cloudbuild.yaml`` with pipeline running steps.




