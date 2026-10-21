# END TO END MLOps PIPELINE WITH AGENTIC MONITOR
[Architecture Diagram](../LSTM%20GP%20UE%20EE/diagrams/end%20to%20end%20mlops%20pipeline.png)

<img src="../LSTM%20GP%20UE%20EE/diagrams/end%20to%20end%20mlops%20pipeline.png" width="500" height="300">

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

### Agentic Workflow
1. polling: Create the desired functionality for the metric to be polled.<br>
2. filtering: Write the cloud logging filter for that metric.<br>
3. ``Langgraph`` agent state looping (of polling and filtering)<br>
3. test end to end <br>
4. deploy on server (``cloudrun job + cloud scheduler``) for continuous polling<br>

# INFRASTRUCTURE ARCHITECTURE DETAILS
## APIs
1. AI platform ``aiplatform.googleapis.com`` <br>
2. Bigquery ``bigquery.googleapis.com`` <br>
3. BigQuery Storage ``bigquerystorage.googleapis.com`` <br>
4. CloudBuild ``cloudbuild.googleapis.com`` <br>
5. Cloud Scheduler ``cloudscheduler.googleapis.com`` <br>
6. Compute ``compute.googleapis.com`` <br>
7. IAM ``iam.googleapis.com`` <br>
8. Cloud Resource Manager ``cloudresourcemanager.googleapis.com``<br>
9. Storage ``storage.googleapis.com`` <br>
10. Artifact Registry ``artifactregistry.googleapis.com`` <br>
## BigQuery
1. One ``google_bigquery_dataset`` called ``xr_predictions`` <br>
2. Two ``google_bigquery_table``s:<br>
  - ``lstm_predictions``<br>
  - ``gp_predictions`` <br>
## IAM
1. Set up a service account for the workflow pipeline ``pipeline_sa``<br>
2. ``pipeline_sa`` is granted the following roles and access levels under ``google_project_iam_member``<br>
  - ``roles/aiplatform.user`` <br>
  - ``roles/bigquery.dataEditor`` <br>
  - ``roles/bigquery.jobUser`` <br>
  - ``roles/logging.logWriter`` <br>
  - ``roles/storage.admin``  <br>
3. ``pipeline_sa`` set to self impersonate under ``google_service_account_iam_member`` with roles
  - ``roles/iam.serviceAccountUser`` <br>
  - ``roles/iam.serviceAccountUser`` <br>
4. cloudbuild service account is granted roles<br>
  -``cloudbuild_sa_storage`` is granted  ``roles/storage.admin``  <br>
  - ``cloudbuild_sa_vertex`` is granted ``roles/aiplatform.user`` <br>
## Storage
1. 5 storage buckets are used in this project:
  - ``lstm-gp-xr-ue-ee-terraform-state`` for storing Terraform state <br>
  - ``raw-data`` bucket <br>
  - ``model artefact`` bucket <br>
  - ``pipeline_root`` bucket <br>
  - ``processed_data`` bucket <br>
## Operations
### CI/CD
1. Pipeline deployement automations are defined in ``cloudbuild.yaml`` <br>
  - Dependencies installation, compilation and submition of ``xr_mlops_pipeline`` to Vertex AI pipeline via ``run_pipeline`` <br>
  - Pipeline yaml (compile pipeline) is uploaded to GCS bucket ``pipeline_root`` <br>
  - Cloud Logging is enabled <br>
2. Git triggered build are set against the project repository. <br>
### Observability: Monitoring, Alerts, Notification Channels
1. Cloud Logging is enabled for pipeline workflow <br>
2. Custom metrics are defined with alerts and notigication channels <br>
  - Pipeline latency <br>
  - Pipeline failure <br>
  - Prediction Drift <br>
  - Row count anomalies during batch prediction <br>
### Agentic Monitor
1. polling: Create the desired functionality for the metric to be polled.<br>
2. filtering: Write the cloud logging filter for that metric.<br>
3. ``Langgraph`` agent state looping (of polling and filtering)<br>
3. test end to end <br>
4. deploy on server (``cloudrun job + cloud scheduler``) for continuous polling<br>
## Pipeline
1. Data Preprocessing <br>
2. Parallel training LSTM and GP <br>
3. Evaluate: RMSE for both models <br>
4. Model Upload: of both models in VA model registry <br>
5. Batch Inference in Bigquery <br>
