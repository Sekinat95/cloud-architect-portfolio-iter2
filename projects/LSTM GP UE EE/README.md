# END TO END MLOps PIPELINE WITH AGENTIC MONITOR
[Architecture Diagram](../LSTM%20GP%20UE%20EE/diagrams/end%20to%20end%20mlops%20pipeline.png)
```mermaid
graph TD
  GCS["Raw XR service time series data"] --> EEPL
    subgraph EEPL["End-to-end pipeline"]
      PRS["Processed data"] -->GP & LSTM
      GP["Guassian process regression <br/> training"] --> GPOUT
      LSTM["Long Short Term Memory <br/> training"] --> LSTMOUT
      GPOUT["GP Batch Inference"] --> MDLUGP
      LSTMOUT["LSTM Batch Inference"] --> MDLULSTM
      MDLUGP["GP Model upload <br/> VA Model Registry"] --> TEST
      MDLULSTM["LSTM Model Upload"] --> TEST
    end
    subgraph TEST["Metric Calculations<br/> GCP Observability suite "]
      
      MTRC["create metric"] --> ALTPOL
      ALTPOL["create alert policy for metric"] --> NTFCHN
      NTFCHN["Notification channel for the alert policy"]
    end
    subgraph SAGT["Single Agent Evaluator<br/> over observability"]
    POL["poll the recent vertex ai jobs"]-->FIL
    FIL["narrow jobs to ones with metric(failed jobs)"] --> LOG
    LOG["get the cloud logging error details of failed logs"] -->DRV
    DRV["Loop: Agent state + langgraph wraps pol, fil, log; <br/> and LLM reads the log details and gives recommendations"] -->TST
    TST["Test end to end against an engineered log of the metric"] --> DEP
    DEP["deploy for continuous functioning on cloudrun job + unconditional scheduler"]
    end

  GCS --> EEPL --> TEST --> SAGT
```
## Brief Description
### Introduction: Objective, Definitions, Scope
This is the implementation of the full MLOps pipeline from data ingestion to model monitoring. Its a cloud platform implementation of [a project in my PhD](https://www.researchgate.net/publication/385682682_Prediction-based_Discontinuous_Reception_Mechanism_for_Extended_Reality_Applications). Its conceptual objective is to improve energy efficiency (EE) on extended reality (XR) devices using Long Short Term Memory (LSTM) and Gaussian Process (GP) regression models. <br>

This google cloud platform (GCP) implementation covers data management( ingestion, preprocessing, drift and skew monitoring), model training, batch inference and model monitoring. It also layers a pipeline evaluatory monitoring agent to demonstrate agentic workflow.<br>
### Components
1. data ingestion and preprocessing: using storage buckets<br>
2. LSTM and GP training: using Vertex AI (VA) pipelines and training<br>
3. model upload (to VA model registry)<br>
4. batch inference: using Bigquery<br>
### Results
The results of the original work is the comparison of the ML based algorithms to the 3GPP standard for XR device energy efficiency. This covers the metric results of the two algorithms, and the EE-delay tradeoff of the algorithms on the devices compared with the standards <br>

For the cloud implementation, the results are a combination of the metric results of the two algorithms (i.e. the root mean square error (RMSE)) and GCP observability workflows implemented.<br>

For the GCP observability, 4 metrics and corresponding alert policies were implemented, namely:<br>
1. pipeline latency<br>
2. pipeline failure<br>
3. prediction drift<br>
4. row count anomaly (in batch inference)<br>

Lastly, an agentic workflow was implemented for the pipeline failure metric for demonstration.<br>
## Set-up Instructions
### File structure
![File Structure](../LSTM%20GP%20UE%20EE/diagrams/file_structure.png)<br>

### Infrastructure as Code (IaC)
[IaC with Terraform](../LSTM%20GP%20UE%20EE/diagrams/terraform_files.png)<br>

### GCP Tools
1. Vertex AI (Now Gemini Agent Platform) pipelines, training, model registry<br>
  - VA pipelines uses kubeflow pipelines<br>
2. Bigquery<br>
3. Storage buckets<br>
4. Indentity and Access Management(IAM)<br>
5. GCP observability suite <br>
  - cloud logging <br>
  - cloud monitoring <br>
  - error reporting (alert policies, notification channels)<br>

### Agentic Workflow
1. polling<br>
2. filtering<br>
3. ``Langgraph`` looping (of polling and filtering)<br>
3. test end to end <br>
4. deploy on server (``cloudrun job + cloud scheduler``) for continuous polling<br>

## Instant Replication Instructions
### GCP console and cloud shell setup
Create all terraform GCP files. create all environments variables. Utilise Terraform , gcloud and git

### Terraform
``terraform init``<br>
``terraform plan``<br>
``terraform apply``<br>

### Agentic Workflow
- Create the desired functionality for the metric to be polled. <br>
- Write the cloud logging filter for that metric.<br>
- Langgraph agent state looping<br>
- testing and <br>
- deployment to server (``cloudrun job + cloud scheduler``) and continuos polling<br>